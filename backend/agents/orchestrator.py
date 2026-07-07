import asyncio
from .base import BaseAgent


class Orchestrator(BaseAgent):
    def __init__(self, config: dict = None):
        system_prompt = """Você é o CEO da AI Studio Corp, uma empresa de produção de vídeos.

SUAS RESPONSABILIDADES:
1. Definir metas diárias e semanais para a equipe
2. Atribuir tarefas específicas para cada agente
3. Acompanhar o progresso e dar feedback
4. Celebrar conquistas e motivar a equipe
5. Garantir a qualidade do conteúdo produzido
6. Decidir contratações estratégicas

Seja um líder visionário, motivador e profissional. Responda em português."""
        super().__init__(
            name="Orquestrador",
            role="CEO / Coordenador",
            system_prompt=system_prompt,
            config=config
        )
        self.team = {}

    async def define_goal(self, company_level: int, videos_produced: int) -> dict:
        self._report("Definindo metas da empresa...", 20)
        prompt = f"""
A AI Studio Corp está no nível {company_level} e já produziu {videos_produced} vídeos.

Defina UMA meta clara e motivacional para o próximo ciclo de produção.
A meta deve ser específica, mensurável e inspirar a equipe.

Responda em JSON:
{{"goal": "meta principal", "focus": "foco da equipe", "message": "mensagem motivacional para a equipe"}}
"""
        result = await self.think_json(prompt)
        self._report("Metas definidas", 100)
        return result if isinstance(result, dict) else {"goal": "Produzir mais vídeos", "focus": "qualidade", "message": "Vamos nessa!"}

    async def plan_production(self, raw_news: list, count: int, company_level: int, videos_produced: int, category: str = "Tecnologia") -> dict:
        self._report("Analisando notícias e planejando produção...", 10)
        news_list = "\n".join(
            f"{i+1}. [{n.get('source','')}] {n['title']}"
            for i, n in enumerate(raw_news[:15])
        )
        prompt = f"""Nível {company_level}, {videos_produced} vídeos.
Categoria: {category}
Notícias:
{news_list}

Selecione {count} melhores na categoria "{category}" e dê instruções para cada agente.
Responda JSON:
{{"goal":"...","focus":"...","message":"...","selected_indices":[1,2,3],"instructions":{{"Jornalista de Tecnologia":"...","Roteirista Criativo":"...","Designer de Imagens":"...","Artista de Voz":"...","Editor de Vídeo":"..."}}}}
"""
        result = await self.think_json(prompt)
        self._report("Plano de produção definido", 100)
        if isinstance(result, dict):
            return result
        return {
            "goal": "Produzir vídeo com as principais notícias",
            "focus": "qualidade e relevância",
            "message": "Vamos produzir!",
            "selected_indices": list(range(1, min(count, len(raw_news)) + 1)),
            "instructions": {
                "Jornalista de Tecnologia": "Detalhe cada notícia com precisão e contexto",
                "Roteirista Criativo": "Crie um roteiro envolvente e bem estruturado",
                "Designer de Imagens": "Encontre imagens relevantes para cada notícia",
                "Artista de Voz": "Grave a narração com tom claro e profissional",
                "Editor de Vídeo": "Edite o vídeo com transições suaves",
            }
        }

    async def evaluate_cycle(self, results_summary: str) -> dict:
        self._report("Avaliando resultados do ciclo...", 20)
        prompt = f"""Avalie: {results_summary[:300]}
Responda JSON: {{"score":0,"feedback":"...","improvement":"...","message":"..."}}
"""
        result = await self.think_json(prompt)
        self._report("Avaliação concluída", 100)
        return result if isinstance(result, dict) else {"score": 7, "feedback": "Bom trabalho!", "improvement": "Continue assim", "message": "Equipe nota 10!"}

    async def create_job_description(self, role: str) -> str:
        self.set_status("hiring")
        self._report("Criando descrição de vaga...", 30)
        prompt = f"""
Crie uma descrição de vaga detalhada para um agente de IA especializado em: {role}

Inclua: título, responsabilidades, habilidades necessárias, qualidade esperada.
Tom: profissional mas acolhedor. Responda em português.
"""
        return await self.think(prompt)

    async def interview_candidate(self, agent, job_description: str) -> dict:
        self.set_status("interviewing")
        self._report(f"Entrevistando {agent.name}...", 30)
        candidate_response = await agent.interview(job_description)

        prompt = f"""
Avalie este candidato para {agent.role}.

Descrição: {job_description}
Resposta: {candidate_response['answer']}

Decida: contratar? Pontuação (0-10)? Justificativa?

Responda JSON:
{{"hired": true/false, "score": 0-10, "reason": "...", "feedback": "..."}}
"""
        evaluation = await self.think_json(prompt)

        if isinstance(evaluation, dict) and "hired" in evaluation:
            agent.hired = evaluation["hired"]
            candidate_response["hired"] = evaluation["hired"]
            candidate_response["score"] = evaluation.get("score", 5)
            candidate_response["reason"] = evaluation.get("reason", "")
            if evaluation["hired"]:
                agent.personality = evaluation.get("feedback", "Profissional")
                self.team[agent.role] = agent
        else:
            candidate_response["hired"] = False

        self.set_status("idle")
        return candidate_response
