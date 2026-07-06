import os
import sys
import asyncio
import json
import uuid
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse

from dotenv import load_dotenv

_BACKEND = Path(__file__).parent
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from agents.orchestrator import Orchestrator
from agents.news_gatherer import NewsGatherer
from agents.script_writer import ScriptWriter
from agents.voice_artist import VoiceArtist
from agents.image_designer import ImageDesigner
from agents.video_editor import VideoEditor

load_dotenv()

app = FastAPI(title="YouTube AI Studio")

API_KEY = os.getenv("OPENAI_API_KEY", "")
if not API_KEY:
    print("⚠️  OPENAI_API_KEY não encontrada no .env")

class ConnectionManager:
    def __init__(self):
        self.active: dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket) -> str:
        await websocket.accept()
        client_id = str(uuid.uuid4()[:8])
        self.active[client_id] = websocket
        return client_id

    def disconnect(self, client_id: str):
        self.active.pop(client_id, None)

    async def broadcast(self, message: dict):
        dead = []
        for cid, ws in self.active.items():
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(cid)
        for cid in dead:
            self.active.pop(cid, None)

manager = ConnectionManager()

agents_pool = []


def init_agents():
    global agents_pool
    agents_pool = [
        NewsGatherer(API_KEY),
        ScriptWriter(API_KEY),
        VoiceArtist(API_KEY),
        ImageDesigner(API_KEY),
        VideoEditor(API_KEY),
    ]


@app.on_event("startup")
async def startup():
    init_agents()


@app.get("/api/status")
async def get_status():
    return {
        "api_key_configured": bool(API_KEY),
        "agents_available": len(agents_pool),
        "agents": [a.get_state() for a in agents_pool]
    }


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    client_id = await manager.connect(websocket)
    print(f"Cliente conectado: {client_id}")

    try:
        while True:
            data = await websocket.receive_text()

            try:
                msg = json.loads(data)
            except json.JSONDecodeError:
                msg = {"action": data}

            action = msg.get("action", "")

            if action == "start_pipeline":
                asyncio.create_task(run_pipeline(manager, msg.get("news_count", 5)))

            elif action == "start_hiring":
                asyncio.create_task(run_hiring(manager, agents_pool))

            elif action == "get_status":
                await websocket.send_json({
                    "type": "agents_status",
                    "agents": [a.get_state() for a in agents_pool]
                })

    except WebSocketDisconnect:
        manager.disconnect(client_id)
        print(f"Cliente desconectado: {client_id}")
    except Exception as e:
        print(f"Erro no websocket: {e}")
        manager.disconnect(client_id)


async def run_hiring(broadcast, agents):
    orchestrator = Orchestrator(API_KEY)
    orchestrator._broadcast = broadcast

    await broadcast({
        "type": "status_update",
        "message": "Iniciando processo de contratação...",
        "orchestrator_status": "hiring"
    })

    results = await orchestrator.hire_team(agents, broadcast)

    hired_count = sum(1 for r in results if r.get("hired"))
    await broadcast({
        "type": "status_update",
        "message": f"Processo seletivo concluído! {hired_count}/{len(results)} contratados.",
        "orchestrator_status": "idle",
        "hiring_complete": True,
        "hired_count": hired_count,
        "total": len(results)
    })

    return orchestrator


async def run_pipeline(broadcast, news_count: int = 5):
    await broadcast({
        "type": "pipeline_start",
        "message": "🎬 Iniciando pipeline de produção do vídeo!"
    })

    orchestrator = Orchestrator(API_KEY)
    orchestrator._broadcast = broadcast

    hired_agents = {}
    for agent in agents_pool:
        if agent.hired:
            hired_agents[agent.role] = agent

    has_hired = len(hired_agents)
    if has_hired == 0:
        await broadcast({
            "type": "hiring_required",
            "message": "Nenhum agente contratado! Execute o processo seletivo primeiro."
        })
        return

    await broadcast({
        "type": "status_update",
        "message": f"Equipe de {has_hired} agentes pronta! Iniciando produção...",
        "orchestrator_status": "working"
    })

    step = 1

    news_agent = hired_agents.get("Jornalista de Tecnologia")
    if news_agent:
        await broadcast({
            "type": "stage_update",
            "stage": f"Etapa {step}/5: Coletando Notícias",
            "agent": news_agent.name
        })
        news_items = await news_agent.gather_full_news(count=news_count)

        await broadcast({
            "type": "news_collected",
            "count": len(news_items),
            "items": [{
                "title": n["title"],
                "source": n["source"],
                "url": n["url"]
            } for n in news_items]
        })
    else:
        await broadcast({"type": "error", "message": "Jornalista não contratado!"})
        return

    step += 1
    script_agent = hired_agents.get("Roteirista Criativo")
    if script_agent:
        await broadcast({
            "type": "stage_update",
            "stage": f"Etapa {step}/5: Criando Roteiro",
            "agent": script_agent.name
        })
        script = await script_agent.create_script(news_items)
        segments = await script_agent.extract_segments(script)

        await broadcast({
            "type": "script_created",
            "preview": script[:500],
            "segments_count": len(segments)
        })
    else:
        await broadcast({"type": "error", "message": "Roteirista não contratado!"})
        return

    step += 1
    image_agent = hired_agents.get("Designer de Imagens")
    if image_agent:
        await broadcast({
            "type": "stage_update",
            "stage": f"Etapa {step}/5: Buscando Imagens",
            "agent": image_agent.name
        })
        images = await image_agent.prepare_images(segments[:len(news_items)], news_items)

        await broadcast({
            "type": "images_prepared",
            "count": len(images),
            "images": [{"title": img["title"], "credit": img["credit"]} for img in images]
        })
    else:
        await broadcast({"type": "error", "message": "Designer não contratado!"})
        return

    step += 1
    voice_agent = hired_agents.get("Artista de Voz")
    if voice_agent:
        await broadcast({
            "type": "stage_update",
            "stage": f"Etapa {step}/5: Gravando Narração",
            "agent": voice_agent.name
        })
        audio_files = await voice_agent.generate_narration(segments[:len(news_items)])

        await broadcast({
            "type": "audio_generated",
            "files_count": len(audio_files),
            "main_audio": audio_files.get("full", "")
        })
    else:
        await broadcast({"type": "error", "message": "Locutor não contratado!"})
        return

    step += 1
    editor_agent = hired_agents.get("Editor de Video")
    if editor_agent:
        await broadcast({
            "type": "stage_update",
            "stage": f"Etapa {step}/5: Editando Vídeo Final",
            "agent": editor_agent.name
        })

        main_audio = audio_files.get("full", "")
        if main_audio and os.path.exists(main_audio):
            video_path = await editor_agent.compose_video(main_audio, images)

            await broadcast({
                "type": "video_complete",
                "video_path": video_path,
                "message": "🎉 VÍDEO FINALIZADO!" if video_path else "❌ Erro na produção do vídeo"
            })
        else:
            await broadcast({
                "type": "error",
                "message": "Áudio principal não encontrado para edição"
            })
    else:
        await broadcast({"type": "error", "message": "Editor não contratado!"})
        return

    await broadcast({
        "type": "pipeline_complete",
        "message": "🎉 Produção do vídeo concluída com sucesso!"
    })


ROOT = Path(__file__).parent.parent / "web"
if ROOT.exists():
    app.mount("/", StaticFiles(directory=str(ROOT), html=True), name="web")


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    print(f"🚀 YouTube AI Studio rodando em http://localhost:{port}")

    os.chdir(str(_BACKEND.parent))
    sys.path.insert(0, str(_BACKEND.parent))

    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=port,
        reload=False,
        log_level="info"
    )
