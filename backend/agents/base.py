import json
import time
from typing import Optional, Callable

from .config import default_config_for_role
from openrouter_client import create_client


class BaseAgent:
    def __init__(self, name: str, role: str, system_prompt: str, config: dict = None):
        self.name = name
        self.role = role
        self.system_prompt = system_prompt
        self.status = "idle"
        self.log = []
        self.hired = False
        self.personality = ""
        self.config = dict(default_config_for_role(role))
        if config:
            self.config.update(config)
        self.current_action = ""
        self.action_progress = 0
        self.xp = 0
        self.level = 1
        self.on_action: Optional[Callable] = None
        self._api_key_override = ""

    def set_global_api_key(self, key: str):
        self._api_key_override = key

    def _report(self, action: str, progress: int = 0):
        self.current_action = action
        self.action_progress = progress
        if self.on_action:
            self.on_action(self.role, action, progress)

    async def think(self, prompt: str) -> str:
        self._report(f"Processando: {prompt[:60]}...", 10)
        provider = self.config.get("provider", "openrouter")
        api_key = self._api_key_override or self.config.get("api_key", "")
        model = self.config.get("model", "openai/gpt-4o-mini")
        temperature = self.config.get("temperature", 0.7)

        if provider == "local":
            self._report("Processamento local...", 50)
            self._report("Concluído", 100)
            return "[Processado localmente]"

        if not api_key:
            err = "Chave da API OpenRouter não configurada"
            self.log_action(err)
            self._report(f"Erro: {err}", 0)
            return f"Erro: {err}"

        try:
            client = create_client(api_key)
            self._report("Consultando OpenRouter...", 30)
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=temperature,
                max_tokens=512,
            )
            self._report("Resposta recebida", 90)
            result = response.choices[0].message.content
            self.log_action(f"OpenRouter/{model}: resposta obtida ({len(result)} chars)")
            self._report("Concluído", 100)
            return result

        except Exception as e:
            err = f"Erro ao consultar OpenRouter ({model}): {e}"
            self.log_action(err)
            self._report("Erro", 0)
            return f"Erro: {err}"

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
            self.log_action(f"Falha ao parsear JSON")
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
            "personality": self.personality,
            "config": {
                "provider": self.config.get("provider", "openrouter"),
                "model": self.config.get("model", "openai/gpt-4o-mini"),
                "temperature": self.config.get("temperature", 0.7),
            },
            "current_action": self.current_action,
            "action_progress": self.action_progress,
            "xp": self.xp,
            "level": self.level,
        }

    def update_config(self, new_config: dict):
        self.config.update(new_config)
        self.log_action(f"Config atualizada: {new_config}")

    async def interview(self, job_description: str) -> dict:
        self.set_status("interviewing")
        self._report("Respondendo à entrevista...", 50)
        prompt = f"""
Você está sendo entrevistado para a vaga de {self.role}.
Descrição: {job_description}

Responda:
1. Qual sua experiência para esta vaga?
2. Como abordaria os desafios?
3. Por que é o melhor candidato?

Seja convincente. Responda em português.
"""
        answer = await self.think(prompt)
        self.set_status("idle")
        return {"agent_name": self.name, "role": self.role, "answer": answer, "hired": False}
