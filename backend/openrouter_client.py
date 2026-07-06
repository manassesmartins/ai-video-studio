import os
import requests
from typing import Optional

OPENROUTER_BASE = "https://openrouter.ai/api/v1"


def fetch_models(api_key: str) -> list:
    headers = {"Authorization": f"Bearer {api_key}"}
    try:
        resp = requests.get(f"{OPENROUTER_BASE}/models", headers=headers, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            models = []
            for m in data.get("data", []):
                mid = m.get("id", "")
                if mid:
                    models.append({
                        "id": mid,
                        "name": m.get("name", mid),
                        "pricing": m.get("pricing", {}),
                    })
            return models
    except Exception as e:
        print(f"[OpenRouter] Erro ao buscar modelos: {e}")
    return []


def create_client(api_key: str):
    from openai import OpenAI
    return OpenAI(
        api_key=api_key,
        base_url=OPENROUTER_BASE,
        default_headers={
            "HTTP-Referer": "https://github.com/ai-studio-corp",
            "X-Title": "AI Studio Corp",
        }
    )
