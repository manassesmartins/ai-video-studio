#!/usr/bin/env python3
import os
import sys
import json
import random
import asyncio
import threading
import time
from pathlib import Path

os.environ.setdefault("GI_TYPELIB_PATH", "/usr/lib/girepository-1.0:/usr/lib64/girepository-1.0")

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT / 'backend'))

from dotenv import load_dotenv
load_dotenv(ROOT / '.env')

from agents.orchestrator import Orchestrator
from agents.news_gatherer import NewsGatherer
from agents.script_writer import ScriptWriter
from agents.voice_artist import VoiceArtist
from agents.image_designer import ImageDesigner
from agents.video_editor import VideoEditor
from agents.config import AGENT_PROVIDER_SCHEMA, default_config_for_role
from settings_manager import SettingsManager
from openrouter_client import fetch_models

NEW_AGENT_TEMPLATES = [
    {"name": "Analista de Dados", "emoji": "📊", "skills": ["Analise", "Metricas", "Relatorios"]},
    {"name": "Social Media", "emoji": "📱", "skills": ["Marketing", "Redes Sociais", "Engajamento"]},
    {"name": "Pesquisador", "emoji": "🔬", "skills": ["Tendencias", "Inovacao", "Mercado"]},
    {"name": "Designer de Thumbnails", "emoji": "🖼️", "skills": ["Thumbnails", "Branding"]},
    {"name": "Analista de SEO", "emoji": "🔍", "skills": ["SEO", "Titulos", "Descricoes"]},
]

AGENT_KEY_MAP = {
    "Jornalista de Tecnologia": "reporter",
    "Roteirista Criativo": "script",
    "Artista de Voz": "voice",
    "Designer de Imagens": "designer",
    "Editor de Vídeo": "editor",
}

AGENT_THINK_MSGS = [
    "Analisando informacoes...", "Processando dados...", "Quase la...",
    "Deixe-me verificar...", "Encontrando padroes...", "Organizando ideias...",
    "Validando fontes...", "Cruzando referencias...",
]


class Company:
    def __init__(self, api, agents, settings):
        self.api = api
        self._agents = agents
        self._settings = settings
        self.level = settings.get("company_level", 1)
        self.xp = settings.get("company_xp", 0)
        self.videos = settings.get("company_videos", 0)
        self.revenue = settings.get("company_revenue", 0)
        self.quality = settings.get("company_quality", 30)
        self._hired_roles = set(settings.get("hired_roles", []))
        if self._hired_roles:
            for a in self._agents:
                if a.role in self._hired_roles:
                    a.hired = True
        self._hire_event = threading.Event()
        self._hire_approved = False
        self._cycle_count = 0
        self._producing = False
        self._news_count = settings.get("news_count", 5)
        self._seen_news = set()
        self._rss_feeds = list(settings.get("rss_feeds", []))

    def xp_next(self):
        levels = [100, 250, 500, 800, 1200, 1800, 2500, 3500, 5000, 7500,
                  10000, 15000, 20000, 30000, 50000, 75000, 100000]
        return levels[min(self.level - 1, len(levels) - 1)]

    def _save_company_state(self):
        self._settings.set("company_level", self.level)
        self._settings.set("company_xp", self.xp)
        self._settings.set("company_videos", self.videos)
        self._settings.set("company_revenue", self.revenue)
        self._settings.set("company_quality", self.quality)

    def add_xp(self, amount):
        self.xp += amount
        while self.xp >= self.xp_next() and self.level < 25:
            self.xp -= self.xp_next()
            self.level += 1
            unlocks = {1: "Equipe inicial", 3: "Producao em massa", 5: "Novos agentes",
                       7: "Qualidade 4K", 10: "Automacao total", 15: "Multiplos videos", 20: "Imperio de midia"}
            self.api._broadcast({"type": "level_up", "level": self.level, "unlock": unlocks.get(self.level, "Melhorias gerais")})
        self._save_company_state()
        self._broadcast_state()

    def _broadcast_state(self):
        self.api._broadcast({
            "type": "company_update",
            "level": self.level, "xp": self.xp, "xpNext": self.xp_next(),
            "videos": self.videos, "revenue": self.revenue,
            "agents": len(self._hired_roles), "quality": self.quality
        })

    def set_news_count(self, count):
        self._news_count = max(1, min(20, count))
        self._settings.set("news_count", self._news_count)

    def get_rss_feeds(self):
        return list(self._rss_feeds)

    def add_rss_feed(self, url: str):
        if url and url not in self._rss_feeds:
            self._rss_feeds.append(url)
            self._settings.set("rss_feeds", list(self._rss_feeds))
            self.api._sync_rss_feeds()
            return True
        return False

    def remove_rss_feed(self, url: str):
        if url in self._rss_feeds:
            self._rss_feeds.remove(url)
            self._settings.set("rss_feeds", list(self._rss_feeds))
            self.api._sync_rss_feeds()
            return True
        return False

    def start_hiring(self):
        if self._hired_roles:
            self.api._log("Equipe ja contratada! Pronta para produzir.", "hire")
            self.api._broadcast({"type": "hiring_complete"})
            self.api._board("Time completo! Quando quiser, clique em Iniciar Producao.")
            return
        threading.Thread(target=self._hiring_flow, daemon=True).start()
        self.api._log("Orquestrador vai montar o time. Fique de olho nas solicitacoes!", "hire")

    def _hiring_flow(self):
        time.sleep(1)
        self.api._log("Orquestrador: Chefe, vamos montar a equipe? Preciso da sua autorizacao.", "agent-orchestrator")
        self.api._board("Orquestrador aguarda permissao para contratar...")

        for agent_class in [None] + self._agents:
            if not self._hiring_active():
                return
            role = "CEO / Coordenador" if agent_class is None else agent_class.role
            name = "Orquestrador" if agent_class is None else agent_class.name
            self._request_hire(role, name, agent_class)

        self.api._broadcast({"type": "hiring_complete"})
        self.api._board("Time completo! Pronto para produzir!")
        self.api._log("Equipe formada! Quando quiser, clique em 'Iniciar Producao'.", "hire")

    def _hiring_active(self):
        return True

    def _request_hire(self, role, name, agent_obj):
        time.sleep(2)
        emojis = {"CEO / Coordenador": "👔", "Jornalista de Tecnologia": "📰",
                  "Roteirista Criativo": "✍️", "Artista de Voz": "🎙️",
                  "Designer de Imagens": "🎨", "Editor de Vídeo": "🎬"}
        msgs = {
            "CEO / Coordenador": "Chefe, posso liderar esta equipe? Prometo resultados extraordinarios!",
            "Jornalista de Tecnologia": "Encontrei uma jornalista excelente! Ela vai trazer as melhores noticias.",
            "Roteirista Criativo": "Este roteirista e um artista das palavras! Ideal para nossos videos.",
            "Artista de Voz": "A voz dele e perfeita para narracoes! Vai dar vida aos nossos roteiros.",
            "Designer de Imagens": "Esta designer tem um olhar unico para imagens. Vai elevar nossa qualidade.",
            "Editor de Vídeo": "Este editor e um mago da montagem! Videos incriveis pela frente.",
        }
        candidate = {
            "name": name, "emoji": emojis.get(role, "🤖"), "role": role,
            "desc": f"Especialista em {role}. Experiencia em producao de conteudo com IA.",
            "skills": [role.split()[0], "Criatividade", "Inovacao"],
            "msg": msgs.get(role, "Podemos contratar?")
        }
        self.api._broadcast({"type": "hire_request", "candidate": candidate})
        self._hire_event.clear()
        self._hire_event.wait(timeout=120)
        if self._hire_approved:
            self._hired_roles.add(role)
            if agent_obj:
                agent_obj.hired = True
            self._settings.set("hired_roles", list(self._hired_roles))
            self.api._broadcast({"type": "hire_result", "hired": True, "name": name, "role": role})
            self.add_xp(20)
        else:
            self.api._broadcast({"type": "hire_result", "hired": False, "name": name, "role": role})
            time.sleep(2)

    def start_production(self):
        if self._producing:
            self.api._log("Ja esta produzindo! Aguarde o ciclo atual terminar.", "error")
            return
        if len(self._hired_roles) < 2:
            self.api._log("Time ainda nao formado! Deixe o Orquestrador contratar primeiro.", "error")
            return
        threading.Thread(target=self._production_cycle, daemon=True).start()

    def _production_cycle(self):
        self._producing = True
        self._cycle_count += 1
        hired = {a.role: a for a in self._agents if a.hired}
        count = self._news_count
        fmt = self._settings.to_dict()

        self.api._broadcast({"type": "pipeline_start"})
        self.api._log(f"Iniciando ciclo de producao #{self._cycle_count}", "hire")

        # Orquestrador: cérebro da operação
        orquestrador = Orchestrator(dict(self._settings.get("agent_configs", {}).get("CEO / Coordenador", {})))
        orquestrador.set_global_api_key(self._settings.get("openrouter_api_key", ""))

        # 1. Jornalista: busca notícias dos feeds (Python puro, sem LLM)
        raw_news = []
        na = hired.get("Jornalista de Tecnologia")
        if na:
            try:
                self.api._broadcast({"type": "stage_update", "stage": f"📰 {na.name}: buscando notícias nos feeds RSS...", "agent": na.name})
                na._report("Vasculhando feeds RSS...", 10)
                raw_news = asyncio.run(na.gather_full_news(count=count, exclude_urls=self._seen_news))
                for item in raw_news:
                    self._seen_news.add(item.get("url", ""))
                self.api._log(f"📰 {len(raw_news)} notícias encontradas nos feeds", "agent-reporter")
                self.api._broadcast({"type": "news_collected", "count": len(raw_news)})
            except Exception as e:
                self.api._log(f"Erro ao buscar notícias: {e}", "error")

        # 2. Orquestrador: analisa notícias, seleciona as melhores e dá ordens a cada agente
        plano = {"selected_indices": [], "instructions": {}, "goal": "Produzir vídeo", "focus": "qualidade", "message": "Vamos nessa!"}
        if raw_news:
            try:
                self.api._broadcast({"type": "stage_update", "stage": "🧠 Orquestrador analisando notícias e planejando produção...", "agent": "Orquestrador"})
                orquestrador._report("Selecionando melhores notícias e definindo tarefas...", 20)
                plano = asyncio.run(orquestrador.plan_production(raw_news, count, self.level, self.videos))
                orquestrador._report("Plano definido", 100)
            except Exception as e:
                self.api._log(f"Erro no planejamento: {e}", "error")

        meta = plano.get("goal", "Produzir com qualidade")
        mensagem = plano.get("message", "Vamos produzir!")
        self.api._board(f"Meta: {meta}")
        self.api._log(f'Orquestrador: "{mensagem}"', "agent-orchestrator")
        self.api._broadcast({"type": "agent_speaks", "role": "CEO / Coordenador", "text": mensagem, "duration": 4000})

        selected_indices = plano.get("selected_indices", [])
        instrucoes = plano.get("instructions", {})

        news_selecionadas = []
        if raw_news and selected_indices:
            for i in selected_indices:
                idx = i - 1
                if 0 <= idx < len(raw_news):
                    news_selecionadas.append(raw_news[idx])
        if not news_selecionadas:
            news_selecionadas = raw_news[:max(count, 1)]

        # 3. Jornalista: enriquece cada notícia selecionada (LLM) seguindo a instrução do orquestrador
        news_items = []
        if na and news_selecionadas:
            try:
                instr = instrucoes.get("Jornalista de Tecnologia", "")
                self.api._broadcast({"type": "stage_update", "stage": f"📰 {na.name}: detalhando notícias selecionadas...", "agent": na.name})
                na._report("Resumindo e detalhando cada notícia...", 20)
                news_items = asyncio.run(na.enrich_news(news_selecionadas, instr))
                self.api._broadcast({"type": "agent_xp", "key": "reporter", "pct": 100})
                self.api._log(f"📚 Notícias enriquecidas: {len(news_items)}", "hire")
            except Exception as e:
                self.api._log(f"Erro ao enriquecer notícias: {e}", "error")

        # 4. Roteirista: cria roteiro seguindo a instrução do orquestrador
        segments = []
        sa = hired.get("Roteirista Criativo")
        if sa and news_items:
            try:
                instr = instrucoes.get("Roteirista Criativo", "")
                self.api._broadcast({"type": "stage_update", "stage": f"✍️ {sa.name}: criando roteiro...", "agent": sa.name})
                sa._report("Escrevendo roteiro com as notícias...", 10)
                script = asyncio.run(sa.create_script(news_items, instr))
                segments = asyncio.run(sa.extract_segments(script))
                self.api._broadcast({"type": "script_created", "segments_count": len(segments)})
                self.api._broadcast({"type": "agent_xp", "key": "script", "pct": 100})
            except Exception as e:
                self.api._log(f"Erro ao criar roteiro: {e}", "error")

        # Fallback: se não houver segmentos, cria um segmento genérico
        if not segments and news_items:
            segments = [{"title": n.get("title", "Notícia"), "narration": n.get("summary", n.get("title", "")), "image_desc": n.get("title", ""), "credit": n.get("source", "")} for n in news_items]
            self.api._log("⚠️ Usando segmentos genéricos (roteiro não gerou segmentos)", "error")

        # 5. Designer: busca imagens seguindo a instrução do orquestrador
        images = []
        ia = hired.get("Designer de Imagens")
        if ia and segments:
            for attempt in range(2):
                try:
                    instr = instrucoes.get("Designer de Imagens", "")
                    self.api._broadcast({"type": "stage_update", "stage": f"🎨 {ia.name}: buscando imagens...", "agent": ia.name})
                    ia._report("Buscando imagens para cada notícia...", 10)
                    images = asyncio.run(ia.prepare_images(segments, news_items, instr))
                    if images:
                        break
                    self.api._log(f"Tentativa {attempt+1}: nenhuma imagem, tentando de novo...", "error")
                    time.sleep(2)
                except Exception as e:
                    self.api._log(f"Tentativa {attempt+1}: {e}", "error")
                    time.sleep(2)

        # 6. Locutor: grava narração
        audio_files = {}
        va = hired.get("Artista de Voz")
        if va and segments:
            try:
                self.api._broadcast({"type": "stage_update", "stage": f"🎙️ {va.name}: gravando narração...", "agent": va.name})
                va._report("Gerando áudio da narração...", 10)
                audio_files = asyncio.run(va.generate_narration(segments))
                self.api._broadcast({"type": "audio_generated", "files_count": len(audio_files)})
                self.api._broadcast({"type": "agent_xp", "key": "voice", "pct": 100})
            except Exception as e:
                self.api._log(f"Erro ao gerar áudio: {e}", "error")

        # 7. Editor: monta o vídeo final
        try:
            ea = hired.get("Editor de Vídeo")
            if ea:
                instr = instrucoes.get("Editor de Vídeo", "")
                self.api._broadcast({"type": "stage_update", "stage": f"🎬 {ea.name}: editando vídeo final...", "agent": ea.name})
                ea._report("Compondo vídeo com imagens e áudio...", 10)
                main_audio = audio_files.get("full", "")
                if main_audio and os.path.exists(main_audio):
                    ea._report("Renderizando vídeo...", 50)
                    video_path = asyncio.run(ea.compose_video(main_audio, images, fmt, segments=segments))
                else:
                    # Vídeo sem áudio (fallback)
                    ea._report("Renderizando vídeo sem áudio...", 50)
                    video_path = asyncio.run(ea.compose_video(None, images, fmt, segments=segments))
                if video_path:
                    self.videos += 1
                    self.revenue += random.randint(10, 100)
                    self.quality = min(100, self.quality + random.randint(1, 3))
                    self.add_xp(random.randint(15, 40))
                self.api._broadcast({"type": "video_complete", "video_path": video_path,
                    "output_dir": str(ROOT / "output" / "videos"),
                    "message": f"Vídeo #{self.videos} finalizado!" if video_path else "Erro na edição"})
                self.api._broadcast({"type": "agent_xp", "key": "editor", "pct": 100})
        except Exception as e:
            self.api._log(f"Erro ao editar vídeo: {e}", "error")

        # 8. Orquestrador: avalia o ciclo
        eval_result = asyncio.run(orquestrador.evaluate_cycle(
            f"Ciclo #{self._cycle_count}: {len(news_items)} notícias, {len(segments)} segmentos, "
            f"{len(images)} imagens, {len(audio_files)} áudios"
        ))
        feedback = eval_result.get("feedback", "Bom trabalho!")
        score = eval_result.get("score", 7)
        self.api._log(f'Orquestrador: "{feedback}" (Nota: {score}/10)', "agent-orchestrator")

        self.api._broadcast({"type": "pipeline_complete",
            "message": f"Ciclo #{self._cycle_count} concluído! Nota: {score}/10"})
        self.api._board(f"Vídeo #{self.videos} | Nv.{self.level} | Próximo ciclo quando quiser!")
        self.api._broadcast({"type": "agent_speaks", "role": "CEO / Coordenador",
                           "text": f"Produção concluída! Nota {score}/10!", "duration": 3000})

        if self.level >= 5 and random.random() < 0.3 and len(self._hired_roles) < 8:
            self._try_hire_new()
        self._producing = False

    def _try_hire_new(self):
        hired_names = {a.name for a in self._agents if a.hired}
        available = [t for t in NEW_AGENT_TEMPLATES if t["name"] not in hired_names and t["name"] not in self._hired_roles]
        if not available:
            return
        t = random.choice(available)
        candidate = {
            "name": t["name"], "emoji": t["emoji"], "role": t["name"],
            "desc": f"Candidato a {t['name']}. Habilidades: {', '.join(t['skills'])}.",
            "skills": t["skills"],
            "msg": f"Chefe, encontrei um {t['name']} talentoso! Podemos contratar?"
        }
        self.api._broadcast({"type": "hire_request", "candidate": candidate})
        self._hire_event.clear()
        self._hire_event.wait(timeout=120)
        if self._hire_approved:
            self._hired_roles.add(t["name"])
            self.api._broadcast({"type": "hire_result", "hired": True, "name": t["name"], "role": t["name"]})
            self.add_xp(50)
        else:
            self.api._broadcast({"type": "hire_result", "hired": False, "name": t["name"], "role": t["name"]})


class Api:
    def __init__(self):
        self.window = None
        self._settings = SettingsManager()
        self._settings.apply_env_api_keys()
        self._agents = [
            NewsGatherer(default_config_for_role("Jornalista de Tecnologia")),
            ScriptWriter(default_config_for_role("Roteirista Criativo")),
            VoiceArtist(default_config_for_role("Artista de Voz")),
            ImageDesigner(default_config_for_role("Designer de Imagens")),
            VideoEditor(default_config_for_role("Editor de Vídeo")),
        ]
        self._company = Company(self, self._agents, self._settings)

        for a in self._agents:
            a.on_action = self._on_agent_action

        self._apply_saved_agent_configs()
        self._propagate_api_key()
        self._sync_rss_feeds()

    def _propagate_api_key(self):
        key = self._settings.get("openrouter_api_key", "")
        for a in self._agents:
            a.set_global_api_key(key)

    def _apply_saved_agent_configs(self):
        saved = self._settings.get("agent_configs", {})
        for a in self._agents:
            if a.role in saved:
                a.update_config(saved[a.role])

    def _on_agent_action(self, role, action, progress):
        key = AGENT_KEY_MAP.get(role)
        if key:
            self._js(f"""
                (()=>{{
                    var el=document.getElementById('action-{key}');
                    if(el)el.textContent={json.dumps(action[:60])};
                    var bar=document.getElementById('prog-{key}');
                    if(bar)bar.style.width='{progress}%';
                }})();
            """)

    def _js(self, code):
        if self.window:
            try:
                self.window.evaluate_js(code)
            except Exception:
                pass

    def _log(self, msg, cls=""):
        self._js(f"addLog({json.dumps(msg)}, {json.dumps(cls)})")

    def _board(self, msg):
        self._js(f"document.getElementById('boardStatus').textContent={json.dumps(msg)}")

    def _broadcast(self, msg):
        try:
            self._js(f"window.handleMessage({json.dumps(msg)})")
        except Exception:
            pass

    def get_agents_status(self):
        states = [a.get_state() for a in self._agents]
        states.append({
            "name": "Orquestrador", "role": "CEO / Coordenador",
            "status": "working" if self._company._producing else "idle",
            "hired": "CEO / Coordenador" in self._company._hired_roles,
            "current_action": "Gerenciando producao" if self._company._producing else "Disponivel",
            "action_progress": 0,
            "config": {"provider": "openrouter", "model": self._settings.get("agent_configs", {}).get("CEO / Coordenador", {}).get("model", "openai/gpt-4o-mini")}
        })
        return states

    def fetch_available_models(self):
        key = self._settings.get("openrouter_api_key", "")
        if not key:
            return []
        models = fetch_models(key)
        if models:
            self._settings.set("cached_models", models)
        return models

    def get_settings_full(self):
        return self._settings.to_dict()

    def get_providers_schema(self):
        schema = dict(AGENT_PROVIDER_SCHEMA)
        stg = self._settings.to_dict()
        cached = stg.get("cached_models", [])
        schema["_meta"] = {
            "news_count": self._company._news_count,
            "rss_feeds": list(self._company._rss_feeds),
            "openrouter_api_key": stg.get("openrouter_api_key", ""),
            "available_models": [m["id"] for m in cached],
            "video": dict(stg.get("video", {})),
            "audio": dict(stg.get("audio", {})),
            "image": dict(stg.get("image", {})),
            "theme": stg.get("theme", "default"),
            "font_scale": stg.get("font_scale", 1.0),
            "layout_scale": stg.get("layout_scale", 1.0),
        }
        for role, cfg in schema.items():
            if role.startswith("_"):
                continue
            saved = stg.get("agent_configs", {}).get(role, {})
            if saved.get("model"):
                cfg["saved_model"] = saved["model"]
            for key in saved:
                if key not in ("model", "provider", "temperature", "api_key"):
                    cfg[key] = saved[key]
        return schema

    def update_settings_full(self, payload: dict):
        for key in ["news_count", "rss_feeds", "theme", "font_scale", "layout_scale"]:
            if key in payload:
                if key == "news_count":
                    self._company.set_news_count(payload[key])
                elif key == "rss_feeds":
                    self._company._rss_feeds = list(payload[key])
                    self._settings.set("rss_feeds", list(payload[key]))
                    self._sync_rss_feeds()
                else:
                    self._settings.set(key, payload[key])
        if "openrouter_api_key" in payload:
            self._settings.set("openrouter_api_key", payload["openrouter_api_key"])
            self._propagate_api_key()
        for key in ["video", "audio", "image"]:
            if key in payload:
                for sub, val in payload[key].items():
                    self._settings.update(key, sub, val)
        return True

    def update_agent_config(self, role: str, new_config: dict):
        if role == "_meta":
            return self.update_settings_full(new_config)
        for a in self._agents:
            if a.role == role:
                a.update_config(new_config)
                self._log(f"{a.name}: config atualizada (modelo: {new_config.get('model','')})")
                configs = self._settings.get("agent_configs", {})
                configs[role] = dict(new_config)
                self._settings.set("agent_configs", configs)
                return True
        return False

    def approve_hire(self, data):
        self._company._hire_approved = True
        self._company._hire_event.set()

    def reject_hire(self, data):
        self._company._hire_approved = False
        self._company._hire_event.set()

    def start_hiring(self):
        self._company.start_hiring()

    def start_production(self):
        self._company.start_production()

    def _sync_rss_feeds(self):
        for a in self._agents:
            if isinstance(a, NewsGatherer):
                a.rss_feeds = list(self._company._rss_feeds)

    def get_rss_feeds(self):
        return self._company.get_rss_feeds()

    def add_rss_feed(self, url: str):
        ok = self._company.add_rss_feed(url)
        if ok:
            self._log(f"Feed RSS adicionado: {url}")
        return ok

    def remove_rss_feed(self, url: str):
        ok = self._company.remove_rss_feed(url)
        if ok:
            self._log(f"Feed RSS removido: {url}")
        return ok

    def fire_agent(self, data: dict):
        role = data.get("role", "")
        if role in self._company._hired_roles:
            self._company._hired_roles.discard(role)
            for a in self._agents:
                if a.role == role:
                    a.hired = False
            if role == "CEO / Coordenador":
                for a in self._agents:
                    a.hired = False
                self._company._hired_roles.clear()
                self._log("🔥 Time inteiro demitido! Orquestrador vai remontar a equipe...")
                threading.Thread(target=self._start_rehiring, daemon=True).start()
            else:
                self._log(f"🔥 {role} foi demitido!")
            self._company._save_company_state()
            self._settings.set("hired_roles", list(self._company._hired_roles))
            self._company._broadcast_state()
        return True

    def _start_rehiring(self):
        import time
        time.sleep(1)
        self._company._hiring_flow()

    def open_output_folder(self):
        import subprocess
        path = str(ROOT / "output" / "videos")
        os.makedirs(path, exist_ok=True)
        try:
            subprocess.Popen(["xdg-open", path])
        except Exception:
            pass

    def test_voice(self, data: dict):
        text = data.get("text", "Olá, esta é a nova voz do seu narrador.")
        voice = data.get("voice", "pt-BR-FranciscaNeural")
        for a in self._agents:
            if isinstance(a, VoiceArtist):
                import asyncio
                path = asyncio.run(a.test_voice(text, voice))
                if path:
                    import base64
                    with open(path, "rb") as f:
                        b64 = base64.b64encode(f.read()).decode("utf-8")
                    return {"path": path, "data": f"data:audio/mp3;base64,{b64}", "message": "Áudio de teste gerado!"}
                return {"path": "", "message": "Falha ao gerar áudio de teste"}
        return {"path": "", "message": "Artista de Voz não encontrado"}


if __name__ == "__main__":
    import webview

    api = Api()
    window = webview.create_window(
        title="AI Studio Corp",
        url=str(ROOT / "web" / "index.html"),
        js_api=api,
        width=1360, height=860,
        resizable=True, min_size=(960, 620),
    )
    api.window = window

    try:
        import gi
        gi.require_version('Gtk', '3.0')
        from gi.repository import Gtk
        Gtk.Window.set_default_icon_from_file(str(ROOT / "icon.png"))
    except Exception:
        pass

    webview.start(gui="gtk", debug=False)
