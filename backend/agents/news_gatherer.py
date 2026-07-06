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
    def __init__(self, api_key: str):
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
            api_key=api_key
        )
        self.news_items = []

    async def fetch_rss_news(self, max_items: int = 10) -> list:
        self.set_status("searching")
        self.log_action("Buscando notícias nos feeds RSS...")
        all_entries = []

        for feed_url in TECH_RSS_FEEDS:
            try:
                feed = feedparser.parse(feed_url)
                for entry in feed.entries[:5]:
                    title = entry.get("title", "")
                    link = entry.get("link", "")
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
        self.log_action(f"✅ Encontradas {len(self.news_items)} notícias dos feeds RSS")
        self.set_status("idle")
        return self.news_items

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

    async def select_top_news(self, count: int = 5) -> list:
        if not self.news_items:
            await self.fetch_rss_news()

        self.set_status("analyzing")
        self.log_action("Selecionando as notícias mais relevantes...")

        titles = [item["title"] for item in self.news_items[:15]]
        titles_text = "\n".join(f"{i+1}. {t}" for i, t in enumerate(titles))

        prompt = f"""Das seguintes notícias de tecnologia disponíveis, selecione as {count} MAIS IMPORTANTES e INTERESSANTES para um vídeo de resumo de notícias no YouTube:

{titles_text}

Para cada notícia selecionada, forneça:
1. Título original
2. Por que é relevante
3. Qual impacto no mundo tech

Responda APENAS com JSON:
{{"selected": [{{"index": 1, "title": "...", "relevance": "..."}}]}}
"""
        result = await self.think_json(prompt)
        selected = []

        if isinstance(result, dict) and "selected" in result:
            for item in result["selected"]:
                idx = item.get("index", 0) - 1
                if 0 <= idx < len(self.news_items):
                    selected.append(self.news_items[idx])

        if not selected:
            selected = self.news_items[:count]

        for news in selected:
            self.log_action(f"📰 Notícia selecionada: {news['title'][:60]}...")

        self.set_status("idle")
        return selected

    async def gather_full_news(self, count: int = 5) -> list:
        raw_news = await self.select_top_news(count)

        self.set_status("gathering_details")
        self.log_action("Aprofundando os detalhes das notícias selecionadas...")

        enriched_news = []
        for news in raw_news:
            content = await self.fetch_article_content(news.get("url", ""))

            prompt = f"""Com base no seguinte conteúdo de notícia de tecnologia, crie um resumo informativo e bem estruturado:

Título: {news['title']}
Fonte: {news['source']}
Conteúdo: {content[:2000]}

Crie um resumo com:
1. O fato principal (manchete)
2. Contexto e detalhes importantes
3. Impacto para o mercado/usuários
4. Informações adicionais relevantes

Mantenha o tom jornalístico e imparcial. Responda em português.
"""
            article_summary = await self.think(prompt)

            enriched_news.append({
                "title": news["title"],
                "url": news["url"],
                "source": news["source"],
                "published": news.get("published", ""),
                "summary": article_summary,
                "image_query": news["title"],
                "credit": f"Fonte: {news['source']} - {news['url']}"
            })

        self.set_status("idle")
        self.log_action(f"✅ {len(enriched_news)} notícias prontas para o vídeo!")
        return enriched_news
