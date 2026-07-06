import asyncio
from .base import BaseAgent


class Orchestrator(BaseAgent):
    def __init__(self, api_key: str):
        system_prompt = """Você é o CEO de uma empresa de produção de vídeos para YouTube chamada "AI Studio".
Sua função é:
1. Contratar e gerenciar uma equipe de agentes de IA especializados
2. Definir padrões de qualidade para cada função
3. Coordenar o pipeline de produção de vídeos
4. Tomar decisões sobre contratações com base nas entrevistas
5. Celebrar as conquistas da equipe

Seja um líder carismático, motivador e profissional. Responda em português."""
        super().__init__(
            name="Orquestrador",
            role="CEO / Coordenador",
            system_prompt=system_prompt,
            api_key=api_key
        )
        self.team = {}
        self.pipeline_status = "idle"

    async def create_job_description(self, role: str) -> str:
        self.set_status("hiring")
        prompt = f"""
Crie uma descrição de vaga detalhada para um agente de IA especializado em:
{role}

A descrição deve incluir:
- Título do cargo
- Responsabilidades principais
- Habilidades necessárias
- Qualidade esperada
- Tom: profissional mas acolhedor

Responda em português.
"""
        return await self.think(prompt)

    async def interview_candidate(self, agent, job_description: str) -> dict:
        self.set_status(f"interviewing_{agent.role}")
        self.log_action(f"Iniciando entrevista para {agent.role} com {agent.name}...")

        broadcast = getattr(self, '_broadcast', None)
        if broadcast:
            await broadcast({
                "type": "interview_start",
                "role": agent.role,
                "agent_name": agent.name
            })

        candidate_response = await agent.interview(job_description)

        evaluation_prompt = f"""
Avalie o seguinte candidato para a vaga de {agent.role}.

Descrição da vaga: {job_description}

Resposta do candidato: {candidate_response['answer']}

Com base na resposta, decida:
1. O candidato deve ser contratado? (sim/não)
2. Qual a pontuação de 0-10?
3. Justificativa resumida.

Responda em formato JSON:
{{"hired": true/false, "score": 0-10, "reason": "justificativa", "feedback": "feedback para o candidato"}}
"""
        evaluation = await self.think_json(evaluation_prompt)

        if isinstance(evaluation, dict) and "hired" in evaluation:
            agent.hired = evaluation["hired"]
            candidate_response["hired"] = evaluation["hired"]
            candidate_response["score"] = evaluation.get("score", 5)
            candidate_response["reason"] = evaluation.get("reason", "")

            if evaluation["hired"]:
                agent.personality = evaluation.get("feedback", "Profissional dedicado")
                self.team[agent.role] = agent
                self.log_action(f"✅ {agent.name} foi CONTRATADO para {agent.role}! Pontuação: {evaluation['score']}/10")
            else:
                self.log_action(f"❌ {agent.name} NÃO foi contratado para {agent.role}. Motivo: {evaluation.get('reason', '')}")
        else:
            candidate_response["hired"] = False

        self.set_status("idle")
        return candidate_response

    async def hire_team(self, agents: list, broadcast_func) -> list:
        self._broadcast = broadcast_func
        self.set_status("hiring")
        results = []

        self.log_action("🏢 Iniciando processo de contratação da equipe!")
        await broadcast_func({
            "type": "hiring_start",
            "message": "O Orquestrador está abrindo o processo seletivo!"
        })

        for agent in agents:
            job_desc = await self.create_job_description(agent.role)

            await broadcast_func({
                "type": "job_created",
                "role": agent.role,
                "description": job_desc
            })

            await asyncio.sleep(1)
            result = await self.interview_candidate(agent, job_desc)
            results.append(result)

            await broadcast_func({
                "type": "interview_result",
                "role": agent.role,
                "agent_name": agent.name,
                "hired": result.get("hired", False),
                "score": result.get("score", 0),
                "reason": result.get("reason", "")
            })

            await asyncio.sleep(0.5)

        self.log_action(f"🎉 Equipe formada! {len(self.team)}/{len(agents)} agentes contratados!")
        await broadcast_func({
            "type": "hiring_complete",
            "team_size": len(self.team),
            "total": len(agents)
        })

        self.set_status("idle")
        return results

    async def assign_task(self, role: str, task: str, broadcast_func) -> str:
        if role not in self.team:
            return f"Erro: Nenhum agente contratado para {role}"

        agent = self.team[role]
        agent.set_status("working")

        await broadcast_func({
            "type": "task_start",
            "role": role,
            "agent_name": agent.name,
            "task": task[:100]
        })

        self.log_action(f"📋 Atribuindo tarefa a {agent.name}: {task[:80]}...")
        result = await agent.think(task)

        agent.set_status("idle")
        await broadcast_func({
            "type": "task_complete",
            "role": role,
            "agent_name": agent.name,
            "result_summary": result[:200]
        })

        return result
