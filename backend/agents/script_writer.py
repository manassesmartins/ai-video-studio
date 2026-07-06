from .base import BaseAgent


class ScriptWriter(BaseAgent):
    def __init__(self, api_key: str):
        system_prompt = """Você é um Roteirista especializado em criar conteúdos para vídeos do YouTube.

SUAS HABILIDADES:
1. Transformar notícias em roteiros envolventes para vídeos narrados
2. Criar textos com ritmo adequado para narração (fallas pausadas e claras)
3. Organizar o conteúdo em segmentos com transições naturais
4. Adaptar a linguagem para ser acessível mas informativa
5. Incluir chamadas para ação (curtir, inscrever-se) de forma natural
6. Usar tom descontraído mas profissional

REGRAS:
- Use português do Brasil natural e fluente
- Frases curtas e objetivas para facilitar a narração
- Inclua markers visuais entre as notícias: [TRANSICAO], [IMAGEM: descrição]
- Tempo estimado total do vídeo: 5-8 minutos
- Abertura: 15 segundos
- Cada notícia: 45-90 segundos
- Encerramento: 20 segundos

Seja criativo mas mantenha a fidelidade aos fatos das notícias."""
        super().__init__(
            name="Roteirista",
            role="Roteirista Criativo",
            system_prompt=system_prompt,
            api_key=api_key
        )

    async def create_script(self, news_items: list) -> str:
        self.set_status("writing")
        self.log_action("Criando roteiro para o vídeo...")

        news_text = ""
        for i, news in enumerate(news_items, 1):
            news_text += f"\n--- NOTÍCIA {i} ---\n"
            news_text += f"Título: {news['title']}\n"
            news_text += f"Fonte: {news['source']}\n"
            news_text += f"Resumo: {news['summary'][:1500]}\n"

        prompt = f"""Crie um roteiro COMPLETO para um vídeo do YouTube chamado "RESUMO DE NOTÍCIAS DE TECNOLOGIA".

O vídeo terá {len(news_items)} notícias.

Conteúdo das notícias:
{news_text}

O roteiro deve ter esta estrutura:

=== ABERTURA ===
[Abertura animada com música]
"Olá pessoal! Sejam bem-vindos ao nosso resumo de notícias de tecnologia..."

=== NOTÍCIAS ===
[Para cada notícia:]
- [TRANSICAO] animada
- [IMAGEM: descrição da imagem necessária]
- Texto da narração da notícia (bem detalhado)
- Créditos da fonte: [fonte]

=== ENCERRAMENTO ===
"E essas foram as principais notícias de tecnologia..."
[CHAMADA: Inscreva-se, ative o sininho, comente]

IMPORTANTE: Escreva o texto COMPLETO da narração, como se o apresentador fosse falar. Inclua [IMAGEM: ...] e [TRANSICAO] nos lugares apropriados mas o texto de narração deve ser completo e fluido.

Responda com o roteiro completo em português do Brasil.
"""
        script = await self.think(prompt)

        self.set_status("reviewing")
        self.log_action("Revisando e refinando o roteiro...")

        polish_prompt = f"""Revise e refine o seguinte roteiro para vídeo do YouTube:

{script}

Verifique:
1. ✓ Fluência natural para narração
2. ✓ Transições suaves entre notícias
3. ✓ Créditos das fontes incluídos
4. ✓ Tom engajante e profissional
5. ✓ Duração adequada (5-8 min de narração)

Faça ajustes se necessário e devolva a versão final."""
        final_script = await self.think(polish_prompt)

        self.set_status("idle")
        self.log_action("✅ Roteiro completo e revisado!")
        return final_script

    async def extract_segments(self, script: str) -> list:
        self.set_status("analyzing")
        self.log_action("Extraindo segmentos do roteiro...")

        prompt = f"""Analise o seguinte roteiro de vídeo e extraia os segmentos individuais:

{script[:4000]}

Para cada segmento de notícia, identifique:
1. O título da notícia
2. O texto da narração (apenas a parte narrada)
3. A descrição da imagem necessária (entre [IMAGEM: ...])
4. A fonte/créditos

Responda APENAS com JSON:
{{"segments": [
    {{
        "title": "título",
        "narration": "texto da narração",
        "image_desc": "descrição da imagem",
        "credit": "créditos da fonte"
    }}
]}}
"""
        result = await self.think_json(prompt)

        if isinstance(result, dict) and "segments" in result:
            self.set_status("idle")
            self.log_action(f"✅ Extraídos {len(result['segments'])} segmentos")
            return result["segments"]

        self.set_status("idle")
        return []
