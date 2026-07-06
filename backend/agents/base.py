import time
import json
from openai import OpenAI
from typing import Optional


class BaseAgent:
    def __init__(self, name: str, role: str, system_prompt: str, api_key: str, model: str = "gpt-4o"):
        self.name = name
        self.role = role
        self.system_prompt = system_prompt
        self.model = model
        self.client = OpenAI(api_key=api_key)
        self.status = "idle"
        self.log = []
        self.hired = False
        self.personality = ""

    async def think(self, prompt: str) -> str:
        self.log_action(f"Pensando sobre: {prompt[:100]}...")
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7
            )
            result = response.choices[0].message.content
            self.log_action("Pensamento concluído")
            return result
        except Exception as e:
            self.log_action(f"Erro ao pensar: {str(e)}")
            return f"Erro: {str(e)}"

    async def think_json(self, prompt: str) -> dict:
        result = await self.think(prompt + "\n\nResponda APENAS com JSON válido, sem markdown, sem formatação extra.")
        result = result.strip()
        if result.startswith("```json"):
            result = result[7:]
        if result.startswith("```"):
            result = result[3:]
        if result.endswith("```"):
            result = result[:-3]
        result = result.strip()
        try:
            return json.loads(result)
        except json.JSONDecodeError:
            self.log_action(f"Falha ao parsear JSON, resposta: {result[:200]}")
            return {"error": "Failed to parse JSON", "raw": result[:500]}

    def set_status(self, status: str):
        self.status = status

    def log_action(self, message: str):
        timestamp = time.strftime("%H:%M:%S")
        entry = f"[{timestamp}] {self.name}: {message}"
        self.log.append(entry)
        print(entry)

    def get_state(self) -> dict:
        return {
            "name": self.name,
            "role": self.role,
            "status": self.status,
            "hired": self.hired,
            "log": self.log[-5:],
            "personality": self.personality
        }

    async def interview(self, job_description: str) -> dict:
        self.set_status("interviewing")
        prompt = f"""
Você está sendo entrevistado para a vaga de {self.role}.

Descrição da vaga: {job_description}

Responda às seguintes perguntas como se fosse um candidato:
1. Qual sua experiência e habilidades para esta vaga?
2. Como você abordaria os desafios deste trabalho?
3. Por que você é o melhor candidato?

Seja convincente e mostre entusiasmo. Responda em português.
"""
        answer = await self.think(prompt)
        self.set_status("idle")
        return {
            "agent_name": self.name,
            "role": self.role,
            "answer": answer,
            "hired": False
        }
