from .base import BaseAgent


class ScriptWriter(BaseAgent):
    def __init__(self, config: dict = None):
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
            config=config
        )

    def _build_local_script(self, news_items: list, instruction: str = "") -> str:
        lines = []
        lines.append("[ABERTURA]")
        lines.append("Olá pessoal! Sejam bem-vindos ao nosso resumo de notícias.")
        lines.append("Vamos conferir as principais novidades.")
        lines.append("")
        for i, news in enumerate(news_items):
            title = news.get("title", "Notícia")
            summary = news.get("summary", "")
            if summary == "[Processado localmente]" or not summary:
                summary = title
            lines.append(f"[NOTÍCIA {i+1}]")
            lines.append(f"[IMAGEM: {title}]")
            lines.append(title)
            lines.append("")
            lines.append(summary[:500])
            lines.append("")
            lines.append("[TRANSICAO]")
            lines.append("")
        lines.append("[ENCERRAMENTO]")
        lines.append("Obrigado por assistir! Não se esqueça de se inscrever para mais conteúdo. Até a próxima!")
        return "\n".join(lines)

    async def create_script(self, news_items: list, instruction: str = "") -> str:
        self.set_status("writing")
        self.log_action("Criando roteiro para o vídeo...")

        provider = self.config.get("provider", "openrouter")
        if provider == "local":
            script = self._build_local_script(news_items, instruction)
            self.set_status("idle")
            self.log_action("✅ Roteiro completo (local)!")
            return script

        news_text = ""
        for i, news in enumerate(news_items, 1):
            news_text += f"\n--- NOTÍCIA {i} ---\n"
            news_text += f"Título: {news['title']}\n"
            news_text += f"Resumo: {news['summary'][:500]}\n"

        instr_text = f"\nInstrução: {instruction[:200]}\n" if instruction else ""

        prompt = f"""Você recebeu notícias que podem estar em qualquer idioma (inglês, espanhol, etc).
Sua tarefa é:

1. TRADUZIR cada título e resumo para o português brasileiro
2. DEPOIS criar um roteiro de vídeo em português brasileiro com as notícias traduzidas

{instr_text}
Notícias originais:
{news_text}

Primeiro traduza cada notícia para português brasileiro mantendo os fatos.
Depois crie o roteiro completo com: ABERTURA, cada notícia (com [TRANSICAO] e [IMAGEM:...]), ENCERRAMENTO.
Texto completo da narração em português brasileiro natural e fluente.
"""
        script = await self.think(prompt)

        self.set_status("reviewing")
        self.log_action("Revisando e refinando o roteiro...")

        polish_prompt = f"""Revise este roteiro e verifique:
1. ✓ Todo o texto está em português brasileiro (nada em outros idiomas)
2. ✓ As traduções são fiéis aos fatos originais
3. ✓ Fluência natural para narração
4. ✓ Transições suaves entre notícias
5. ✓ Tom engajante e profissional

Corrija qualquer termo que não esteja em português brasileiro e devolva a versão final:

{script}
"""
        final_script = await self.think(polish_prompt)

        self.set_status("idle")
        self.log_action("✅ Roteiro completo, traduzido e revisado!")
        return final_script
