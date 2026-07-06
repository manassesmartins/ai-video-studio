import os
import re
import feedparser
import requests
from bs4 import BeautifulSoup
from .base import BaseAgent


TECH_RSS_FEEDS = [
    "https://www.tecmundo.com.br/feed",
    "https://g1.globo.com/rss/g1/tecnologia/",
    "https://olhardigital.com.br/feed",
    "https://www.theverge.com/rss/index.xml",
    "https://www.wired.com/feed/rss",
    "https://arstechnica.com/feed/",
    "https://techcrunch.com/feed/",
    "https://www.engadget.com/rss.xml",
]


class NewsGatherer(BaseAgent):
    def __init__(self, config: dict = None, rss_feeds: list = None):
        system_prompt = """Você é um Jornalista de Tecnologia especializado em:
1. Buscar as notícias mais recentes e relevantes do mundo tech
2. Resumir notícias de forma objetiva e informativa
3. Verificar fontes e manter a precisão das informações
4. Extrair os pontos mais importantes de cada notícia

Você tem acesso a fontes RSS de tecnologia.
Sempre mantenha os créditos e links das fontes originais.
Responda em português do Brasil."""
        super().__init__(
            name="Repórter Tech",
            role="Jornalista de Tecnologia",
            system_prompt=system_prompt,
            config=config
        )
        self.news_items = []
        self.rss_feeds = rss_feeds or list(TECH_RSS_FEEDS)

    async def fetch_rss_news(self, max_items: int = 10, exclude_urls: set = None) -> list:
        self.set_status("searching")
        self.log_action("Buscando notícias nos feeds RSS...")
        all_entries = []
        exclude = exclude_urls or set()

        for feed_url in self.rss_feeds:
            try:
                feed = feedparser.parse(feed_url)
                for entry in feed.entries[:5]:
                    title = entry.get("title", "")
                    link = entry.get("link", "")
                    if link in exclude:
                        continue
                    summary = entry.get("summary", entry.get("description", ""))
                    published = entry.get("published", "")
                    source = feed_url.split("//")[1].split("/")[0].replace("www.", "")

                    summary_text = BeautifulSoup(summary, "html.parser").get_text()[:500] if summary else ""

                    all_entries.append({
                        "title": title,
                        "url": link,
                        "summary": summary_text,
                        "source": source,
                        "published": published
                    })
            except Exception as e:
                self.log_action(f"Erro ao acessar feed {feed_url}: {str(e)}")

        all_entries.sort(key=lambda x: x.get("published", ""), reverse=True)
        self.news_items = all_entries[:max_items]
        self.log_action(f"✅ Encontradas {len(self.news_items)} notícias novas dos feeds RSS")
        self.set_status("idle")
        return self.news_items

    def _images_dir(self):
        return os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "output", "images")

    async def fetch_article_content(self, url: str) -> str:
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
            resp = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(resp.text, "html.parser")

            for tag in soup(["script", "style", "nav", "footer", "header"]):
                tag.decompose()

            text = soup.get_text()
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            return " ".join(lines[:100])
        except Exception as e:
            return f"Erro ao acessar artigo: {str(e)}"

    async def extract_article_images(self, url: str) -> list:
        images = []
        try:
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
            resp = requests.get(url, headers=headers, timeout=5)
            soup = BeautifulSoup(resp.text, "html.parser")

            for meta in soup.find_all("meta"):
                prop = (meta.get("property") or "").lower()
                name = (meta.get("name") or "").lower()
                if prop == "og:image" or name == "twitter:image":
                    src = meta.get("content", "").strip()
                    if src and src.startswith("http"):
                        alt = (meta.get("alt") or "") or soup.find("title")
                        alt = alt.get_text()[:100] if hasattr(alt, "get_text") else str(alt)[:100]
                        images.append({"url": src, "alt": alt or url.rsplit("/", 1)[-1], "credit": url})
                        return [images[-1]]

            for img in soup.find_all("img"):
                src = img.get("src", "").strip()
                if not src.startswith("http"):
                    if src.startswith("//"):
                        src = "https:" + src
                    elif src.startswith("/"):
                        from urllib.parse import urlparse
                        parsed = urlparse(url)
                        src = f"{parsed.scheme}://{parsed.netloc}{src}"
                    else:
                        continue
                alt = img.get("alt", "")[:100]
                w = img.get("width", "0")
                h = img.get("height", "0")
                try:
                    if int(w) * int(h) < 10000:
                        continue
                except ValueError:
                    pass
                images.append({"url": src, "alt": alt or "Imagem do artigo", "credit": url})
                if len(images) >= 2:
                    break
        except Exception:
            pass
        return images

    async def download_article_image(self, img_data: dict, news_idx: int, img_idx: int) -> str:
        os.makedirs(self._images_dir(), exist_ok=True)
        ext = img_data["url"].rsplit(".", 1)[-1].split("?")[0][:4] if "." in img_data["url"] else "jpg"
        filename = f"article_{news_idx}_{img_idx}.{ext}"
        filepath = os.path.join(self._images_dir(), filename)
        try:
            headers = {"User-Agent": "Mozilla/5.0"}
            resp = requests.get(img_data["url"], headers=headers, timeout=10)
            if resp.status_code == 200:
                with open(filepath, "wb") as f:
                    f.write(resp.content)
                return filepath
        except Exception:
            pass
        return ""

    async def enrich_news(self, news_list: list, instruction: str = "") -> list:
        self.set_status("gathering_details")
        self.log_action("Aprofundando os detalhes das notícias selecionadas...")

        enriched = []
        for i, news in enumerate(news_list):
            content = await self.fetch_article_content(news.get("url", ""))

            prompt = f"""Resuma esta notícia de tecnologia:

Título: {news['title']}
Fonte: {news['source']}
Conteúdo: {content[:800]}

{("Instrução: " + instruction[:200]) if instruction else ""}

Responda: fato principal, contexto, impacto. Português.
"""
            article_summary = await self.think(prompt)

            article_images = []
            if not content.startswith("Erro"):
                raw_images = await self.extract_article_images(news.get("url", ""))
                for j, img in enumerate(raw_images):
                    local = await self.download_article_image(img, i, j)
                    if local:
                        article_images.append({"url": img["url"], "local_path": local, "alt": img.get("alt", ""), "credit": f"Fonte: {news['source']}"})
                    if len(article_images) >= 2:
                        break

            enriched.append({
                "title": news["title"],
                "url": news["url"],
                "source": news["source"],
                "published": news.get("published", ""),
                "summary": article_summary,
                "article_images": article_images,
                "image_query": news["title"],
                "credit": f"Fonte: {news['source']} - {news['url']}"
            })

        self.set_status("idle")
        self.log_action(f"✅ {len(enriched)} notícias enriquecidas!")
        return enriched

    async def gather_full_news(self, count: int = 5, exclude_urls: set = None) -> list:
        raw = await self.fetch_rss_news(max_items=30, exclude_urls=exclude_urls)
        return raw[:count]
