import os
import requests
import random
from .base import BaseAgent


class ImageDesigner(BaseAgent):
    def __init__(self, config: dict = None):
        system_prompt = """Você é um Designer Gráfico / Editor de Imagens especializado em:

1. Encontrar imagens relevantes para notícias de tecnologia
2. Criar descrições precisas para busca de imagens
3. Organizar imagens com créditos e fontes adequados
4. Garantir que todas as imagens tenham atribuição correta
5. Criar composições visuais atraentes para vídeos do YouTube

REGRAS IMPORTANTES:
- Sempre inclua os créditos da fonte original da imagem
- Prefira imagens que ilustrem claramente o assunto da notícia
- Organize as imagens na ordem correta das notícias"""
        super().__init__(
            name="Designer",
            role="Designer de Imagens",
            system_prompt=system_prompt,
            config=config
        )

    def _images_dir(self):
        return os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "output", "images")

    async def generate_ai_image(self, prompt: str, filename: str) -> str:
        model = self.config.get("image_gen_model", "") or ""
        if model and model != "nenhum":
            self.set_status("generating_ai")
            self.log_action(f"Gerando imagem com IA ({model})...")
            os.makedirs(self._images_dir(), exist_ok=True)
            filepath = os.path.join(self._images_dir(), filename)
            try:
                from openrouter_client import create_client
                client = create_client(self._api_key_override)
                resp = client.images.generate(
                    model=model,
                    prompt=prompt[:1000],
                    size="1792x1024" if "dall-e-3" in model else "1024x1024",
                    quality="standard",
                    n=1,
                )
                img_url = resp.data[0].url
                if img_url:
                    r = requests.get(img_url, timeout=30)
                    if r.status_code == 200:
                        with open(filepath, "wb") as f:
                            f.write(r.content)
                        self.log_action(f"✅ Imagem gerada por IA: {filename}")
                        self.set_status("idle")
                        return filepath
            except Exception as e:
                self.log_action(f"Erro ao gerar imagem por IA: {e}")
        self.set_status("idle")
        return ""

    async def generate_placeholder(self, text: str, filename: str) -> str:
        self.set_status("generating")
        self.log_action(f"Gerando placeholder para: {text[:50]}...")
        os.makedirs(self._images_dir(), exist_ok=True)
        filepath = os.path.join(self._images_dir(), filename)
        try:
            from PIL import Image, ImageDraw, ImageFont
            palettes = [
                (30, 38, 58), (58, 30, 38), (38, 58, 30),
                (20, 36, 56), (56, 20, 36), (36, 56, 20),
                (25, 25, 50), (50, 25, 25), (25, 50, 25),
                (40, 20, 50), (50, 40, 20), (20, 50, 40),
            ]
            bg = palettes[id(text) % len(palettes)] if isinstance(text, str) else random.choice(palettes)
            img = Image.new("RGB", (1920, 1080), bg)
            draw = ImageDraw.Draw(img)

            try:
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 48)
            except (IOError, OSError):
                try:
                    font = ImageFont.truetype("/usr/share/fonts/TTF/DejaVuSans-Bold.ttf", 48)
                except (IOError, OSError):
                    font = ImageFont.load_default()

            words = text.split()
            lines = []
            buf = ""
            for w in words:
                test = buf + " " + w if buf else w
                try:
                    tw = draw.textlength(test, font=font)
                except AttributeError:
                    tw = len(test) * 24
                if tw > 1700 and buf:
                    lines.append(buf)
                    buf = w
                else:
                    buf = test
            if buf:
                lines.append(buf)
            if not lines:
                lines = [text[:80]]

            y = 480
            for line in lines:
                try:
                    tw = draw.textlength(line, font=font)
                except AttributeError:
                    tw = len(line) * 24
                draw.text(((1920 - tw) / 2, y), line, fill=(200, 210, 230), font=font)
                y += 56

            y += 20
            lw = min(1200, len(max(lines, key=len)) * 22)
            draw.line(((1920 - lw) / 2, y, (1920 + lw) / 2, y), fill=(100, 140, 200), width=3)

            img.save(filepath, "JPEG", quality=85)
            self.log_action(f"✅ Placeholder gerado: {filename}")
            self.set_status("idle")
            return filepath
        except ImportError:
            self.log_action("Pillow não disponível, pulando placeholder")
        except Exception as e:
            self.log_action(f"Erro ao gerar placeholder: {e}")
        self.set_status("idle")
        return ""

    async def prepare_images(self, segments: list, news_items: list, instruction: str = "") -> list:
        self.set_status("planning_images")
        self.log_action("Preparando imagens para o vídeo...")
        prepared_images = []

        for i, segment in enumerate(segments):
            title = segment.get("title", "")
            image_desc = segment.get("image_desc", title)
            credit = segment.get("credit", "")
            filename = f"news_{i}.jpg"
            has_image = False

            news_item = news_items[i] if i < len(news_items) else {}
            article_images = news_item.get("article_images", [])

            # 1. Usar TODAS as imagens extraídas do artigo
            if article_images:
                for j, art_img in enumerate(article_images):
                    src = art_img.get("local_path", "")
                    if src and os.path.exists(src):
                        prepared_images.append({
                            "segment_index": i,
                            "title": title,
                            "local_path": src,
                            "credit": art_img.get("credit", credit),
                            "image_desc": image_desc
                        })
                        has_image = True
                        self.log_action(f"✅ Usando imagem {j+1} do artigo: {src}")

            # 2. Tentar gerar por IA (se nenhuma imagem do artigo)
            if not has_image:
                ai_path = await self.generate_ai_image(image_desc, filename)
                if ai_path:
                    prepared_images.append({
                        "segment_index": i,
                        "title": title,
                        "local_path": ai_path,
                        "credit": news_item.get("credit", credit),
                        "image_desc": image_desc
                    })
                    has_image = True

            # 3. Fallback: placeholder
            if not has_image:
                local_path = await self.generate_placeholder(image_desc, filename)
                prepared_images.append({
                    "segment_index": i,
                    "title": title,
                    "local_path": local_path,
                    "credit": news_item.get("credit", credit),
                    "image_desc": image_desc
                })

        self.log_action(f"✅ {len(prepared_images)} imagens preparadas!")
        self.set_status("idle")
        return prepared_images
