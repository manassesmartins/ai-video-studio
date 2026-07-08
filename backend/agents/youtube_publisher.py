import os
import json
import pickle
import asyncio
from pathlib import Path

from .base import BaseAgent

ROOT = Path(__file__).parent.parent.parent
TOKEN_FILE = ROOT / "youtube_token.pickle"
CLIENT_SECRET_FILE = ROOT / "client_secret.json"

SCOPES = ["https://www.googleapis.com/auth/youtube.upload",
          "https://www.googleapis.com/auth/youtube"]
YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"


class YouTubePublisher(BaseAgent):
    def __init__(self, config: dict = None):
        system_prompt = """Você é o Gerente de Publicação do YouTube.

SUAS RESPONSABILIDADES:
1. Gerar títulos otimizados para SEO (chamativos e com palavras-chave)
2. Escrever descrições detalhadas com timestamps, links, créditos
3. Escolher tags relevantes para o vídeo
4. Definir categoria e configurações de privacidade
5. Agendar publicação para melhor horário de engajamento

Regras:
- Títulos: máx. 70 caracteres, gancho forte, palavras-chave no início
- Descrições: incluir timestamps, créditos das fontes, links, call-to-action
- Tags: 5-15 tags relevantes, começar com as mais importantes
- Usar português brasileiro"""
        super().__init__(
            name="Publicador YouTube",
            role="YouTube Publisher",
            system_prompt=system_prompt,
            config=config
        )
        self._service = None

    def _get_credentials(self):
        from google.auth.transport.requests import Request
        from google_auth_oauthlib.flow import InstalledAppFlow

        credentials = None
        if TOKEN_FILE.exists():
            try:
                with open(TOKEN_FILE, "rb") as f:
                    credentials = pickle.load(f)
            except Exception:
                pass

        if credentials and credentials.expired and credentials.refresh_token:
            try:
                credentials.refresh(Request())
            except Exception:
                credentials = None

        if not credentials or not credentials.valid:
            if not CLIENT_SECRET_FILE.exists():
                self.log_action("Arquivo client_secret.json não encontrado")
                return None
            flow = InstalledAppFlow.from_client_secrets_file(
                str(CLIENT_SECRET_FILE), SCOPES
            )
            credentials = flow.run_local_server(port=8080, open_browser=True)

            with open(TOKEN_FILE, "wb") as f:
                pickle.dump(credentials, f)

        return credentials

    def _get_service(self):
        if self._service:
            return self._service
        credentials = self._get_credentials()
        if not credentials:
            return None
        from googleapiclient.discovery import build
        self._service = build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION,
                              credentials=credentials)
        return self._service

    def is_authenticated(self) -> bool:
        return TOKEN_FILE.exists() or CLIENT_SECRET_FILE.exists()

    def is_ready(self) -> bool:
        return TOKEN_FILE.exists() and self._get_service() is not None

    async def authenticate(self) -> bool:
        self.set_status("authenticating")
        self._report("Autenticando com YouTube...", 10)
        try:
            creds = await asyncio.to_thread(self._get_credentials)
            ok = creds is not None
            self.set_status("idle")
            self._report("Autenticação concluída" if ok else "Falha na autenticação", 100)
            return ok
        except Exception as e:
            self.log_action(f"Erro na autenticação: {e}")
            self.set_status("idle")
            return False

    async def generate_metadata(self, news_items: list, segments: list,
                                 script: str = "", video_path: str = "") -> dict:
        self.set_status("planning")
        self._report("Gerando metadados para o YouTube...", 10)

        provider = self.config.get("provider", "openrouter")
        if provider == "local":
            return self._build_local_metadata(news_items, segments)

        titles_text = "\n".join(f"- {n.get('title', '')}" for n in news_items[:5])
        segments_text = "\n".join(
            f"{i+1}. {s.get('title', s.get('narration', '')[:80])}"
            for i, s in enumerate(segments[:10])
        )

        prompt = f"""Com base nestas notícias do vídeo, gere metadados otimizados para YouTube:

NOTÍCIAS:
{titles_text}

SEGMENTOS DO VÍDEO:
{segments_text}

Responda APENAS com JSON:
{{
  "title": "título chamativo (máx. 70 caracteres, SEO)",
  "description": "descrição completa com timestamps, créditos e call-to-action",
  "tags": ["tag1", "tag2", "tag3", ...],
  "category": "22",
  "privacy": "public",
  "language": "pt"
}}

Categoria: 22=People & Blogs, 25=News & Politics, 28=Science & Technology
Privacidade: public, unlisted, private
Use português brasileiro.
"""
        result = await self.think_json(prompt)
        if isinstance(result, dict) and "title" in result:
            self._report("Metadados gerados", 100)
            self.set_status("idle")
            return result

        self.set_status("idle")
        return self._build_local_metadata(news_items, segments)

    def _build_local_metadata(self, news_items: list, segments: list) -> dict:
        titles = [n.get("title", "") for n in news_items[:5]]
        main_title = titles[0][:60] if titles else "Resumo de Notícias"
        if len(titles) > 1:
            main_title = f"{main_title} e mais {len(titles)-1} notícias"

        desc_lines = ["📰 RESUMO DE NOTÍCIAS DE TECNOLOGIA\n"]
        for i, s in enumerate(segments):
            t = s.get("title", s.get("narration", "")[:60])
            desc_lines.append(f"{i+1}:00 - {t}")
        desc_lines.append("")
        desc_lines.append("🔔 Inscreva-se para mais conteúdo!")
        desc_lines.append("👍 Curta e compartilhe!")
        desc_lines.append("")
        desc_lines.append("#Notícias #Tecnologia #YouTube")
        desc_lines.append("")
        for n in news_items:
            src = n.get("source", "")
            url = n.get("url", "")
            if src and url:
                desc_lines.append(f"Fonte: {src} - {url}")

        tags = ["notícias", "tecnologia", "resumo de notícias", "youtube"]
        seen = set()
        for n in news_items:
            for w in n.get("title", "").split()[:3]:
                w = w.lower().strip(",.!?;:")
                if w and len(w) > 3 and w not in seen:
                    tags.append(w)
                    seen.add(w)
                    if len(tags) >= 15:
                        break

        return {
            "title": main_title[:100],
            "description": "\n".join(desc_lines)[:5000],
            "tags": tags[:15],
            "category": "28",
            "privacy": self.config.get("privacy", "public"),
            "language": "pt",
        }

    async def upload_video(self, video_path: str, metadata: dict,
                           thumbnail_path: str = "") -> dict:
        self.set_status("uploading")
        self._report("Enviando vídeo para o YouTube...", 10)

        if not os.path.exists(video_path):
            err = f"Vídeo não encontrado: {video_path}"
            self.log_action(err)
            self.set_status("idle")
            return {"success": False, "error": err}

        service = self._get_service()
        if not service:
            err = "YouTube não autenticado"
            self.log_action(err)
            self.set_status("idle")
            return {"success": False, "error": err}

        try:
            from googleapiclient.http import MediaFileUpload

            body = {
                "snippet": {
                    "title": metadata.get("title", "Vídeo AI Studio")[:100],
                    "description": metadata.get("description", "")[:5000],
                    "tags": metadata.get("tags", [])[:50],
                    "categoryId": metadata.get("category", "28"),
                    "defaultLanguage": metadata.get("language", "pt"),
                },
                "status": {
                    "privacyStatus": metadata.get("privacy", "public"),
                    "selfDeclaredMadeForKids": False,
                },
            }

            self._report("Fazendo upload...", 30)
            media = MediaFileUpload(video_path, chunksize=-1, resumable=True)

            request = service.videos().insert(
                part="snippet,status",
                body=body,
                media_body=media,
            )

            response = None
            last_progress = 30

            def progress_callback(current, total):
                nonlocal last_progress
                pct = 30 + int((current / max(total, 1)) * 60)
                if pct > last_progress:
                    last_progress = pct
                    self._report(f"Upload: {pct-30}%...", pct)

            response = await asyncio.to_thread(
                lambda: request.execute() if not hasattr(request, 'next_chunk')
                else self._resumable_upload(request, progress_callback)
            )

            video_id = response.get("id", "")
            self._report("Upload concluído, definindo thumbnail...", 95)

            if thumbnail_path and os.path.exists(thumbnail_path):
                try:
                    media_thumb = MediaFileUpload(thumbnail_path)
                    service.thumbnails().set(
                        videoId=video_id,
                        media_body=media_thumb,
                    ).execute()
                    self.log_action("Thumbnail enviada!")
                except Exception as e:
                    self.log_action(f"Erro na thumbnail: {e}")

            result = {
                "success": True,
                "video_id": video_id,
                "url": f"https://youtu.be/{video_id}",
                "title": metadata.get("title", ""),
            }
            self.log_action(f"Vídeo publicado! https://youtu.be/{video_id}")
            self._report("Publicado!", 100)
            self.set_status("idle")
            return result

        except Exception as e:
            err = f"Erro no upload: {e}"
            self.log_action(err)
            self.set_status("idle")
            return {"success": False, "error": err}

    def _resumable_upload(self, request, progress_cb):
        import http
        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                progress_cb(status.resumable_progress, status.total_size)
        return response

    async def publish(self, video_path: str, news_items: list,
                      segments: list, script: str = "",
                      thumbnail_path: str = "") -> dict:
        self._report("Preparando publicação no YouTube...", 5)
        metadata = await self.generate_metadata(news_items, segments, script, video_path)
        self._report(f"Título: {metadata.get('title', '')[:50]}...", 15)

        thumb_path = thumbnail_path
        if not thumb_path:
            thumb_dir = ROOT / "output" / "thumbnails"
            thumb_path = str(thumb_dir / "thumbnail.jpg")

        result = await self.upload_video(video_path, metadata, thumb_path)
        return result

    async def check_channel_info(self) -> dict:
        service = self._get_service()
        if not service:
            return {"error": "Não autenticado"}
        try:
            request = service.channels().list(part="snippet,statistics", mine=True)
            response = await asyncio.to_thread(lambda: request.execute())
            items = response.get("items", [])
            if items:
                ch = items[0]
                return {
                    "name": ch["snippet"]["title"],
                    "subscribers": ch["statistics"].get("subscriberCount", "0"),
                    "videos": ch["statistics"].get("videoCount", "0"),
                    "thumbnail": ch["snippet"]["thumbnails"]["default"]["url"],
                }
            return {"error": "Nenhum canal encontrado"}
        except Exception as e:
            return {"error": str(e)}
