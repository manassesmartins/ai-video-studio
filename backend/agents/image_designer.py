import os
import requests
from .base import BaseAgent


class ImageDesigner(BaseAgent):
    def __init__(self, api_key: str):
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
            api_key=api_key
        )
        self.unsplash_client_id = None

    async def search_unsplash(self, query: str, max_results: int = 3) -> list:
        try:
            url = f"https://api.unsplash.org/search/photos"
            params = {
                "query": query,
                "per_page": max_results,
                "orientation": "landscape"
            }

            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }

            resp = requests.get(url, params=params, headers=headers, timeout=10)

            if resp.status_code == 200:
                data = resp.json()
                results = []
                for photo in data.get("results", []):
                    results.append({
                        "url": photo["urls"]["regular"],
                        "download_url": photo["links"]["download"],
                        "credit": f"Foto por {photo['user']['name']} no Unsplash",
                        "credit_link": f"{photo['user']['links']['html']}?utm_source=AI_Studio&utm_medium=referral"
                    })
                return results
            else:
                return []

        except Exception:
            return []

    async def search_image(self, query: str) -> dict:
        self.set_status("searching_images")
        self.log_action(f"Buscando imagens para: {query[:50]}...")

        search_terms_prompt = f"""
Crie 2 termos de busca em inglês para encontrar imagens relacionadas a:
"{query}"

Os termos devem ser objetivos e descritivos para busca de fotos.

Responda JSON: {{"terms": ["termo1", "termo2"]}}
"""
        search_terms = await self.think_json(search_terms_prompt)
        terms = search_terms.get("terms", [query]) if isinstance(search_terms, dict) else [query]

        all_images = []
        for term in terms[:2]:
            unsplash_images = await self.search_unsplash(term)
            all_images.extend(unsplash_images)

        if all_images:
            best = all_images[0]
            self.log_action(f"✅ Imagem encontrada: créditos - {best['credit']}")
            self.set_status("idle")
            return best

        self.set_status("idle")
        return {"url": "", "credit": "Imagem não encontrada", "download_url": ""}

    async def download_image(self, image_data: dict, filename: str) -> str:
        if not image_data.get("url"):
            return ""

        self.set_status("downloading")
        self.log_action(f"Baixando imagem: {filename}...")

        output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "output", "images")
        os.makedirs(output_dir, exist_ok=True)

        filepath = os.path.join(output_dir, filename)

        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
            resp = requests.get(image_data["url"], headers=headers, timeout=15)
            if resp.status_code == 200:
                with open(filepath, "wb") as f:
                    f.write(resp.content)
                self.log_action(f"✅ Imagem salva: {filename}")
                return filepath
        except Exception as e:
            self.log_action(f"❌ Erro ao baixar imagem: {str(e)}")

        return ""

    async def prepare_images(self, segments: list, news_items: list) -> list:
        self.set_status("planning_images")
        self.log_action("Preparando imagens para o vídeo...")

        prepared_images = []

        for i, segment in enumerate(segments):
            title = segment.get("title", "")
            image_desc = segment.get("image_desc", title)
            credit = segment.get("credit", "")

            image_data = await self.search_image(image_desc)
            filename = f"news_{i}.jpg"
            local_path = await self.download_image(image_data, filename)

            news_item = news_items[i] if i < len(news_items) else {}
            source_credit = news_item.get("credit", credit)

            prepared_images.append({
                "segment_index": i,
                "title": title,
                "local_path": local_path,
                "credit": source_credit,
                "image_desc": image_desc
            })

        self.log_action(f"✅ {len(prepared_images)} imagens preparadas!")
        self.set_status("idle")
        return prepared_images
