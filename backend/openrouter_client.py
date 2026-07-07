import os
import requests
from typing import Optional

OPENROUTER_BASE = "https://openrouter.ai/api/v1"

ROLE_FREE_MODELS = {
    "Jornalista de Tecnologia": ["qwen/qwen3-next-80b-a3b-instruct:free", "google/gemma-4-26b-a4b-it:free", "nvidia/nemotron-3-nano-30b-a3b:free"],
    "Roteirista Criativo": ["qwen/qwen3-next-80b-a3b-instruct:free", "google/gemma-4-26b-a4b-it:free", "nvidia/nemotron-3-ultra-550b-a55b:free"],
    "CEO / Coordenador": ["qwen/qwen3-next-80b-a3b-instruct:free", "nvidia/nemotron-3-ultra-550b-a55b:free", "google/gemma-4-31b-it:free"],
    "Designer de Imagens": ["qwen/qwen3-next-80b-a3b-instruct:free", "google/gemma-4-26b-a4b-it:free", "nvidia/nemotron-3-nano-30b-a3b:free"],
}


def is_free_model(model_id: str) -> bool:
    return model_id.endswith(":free")


def fetch_models(api_key: str) -> list:
    headers = {"Authorization": f"Bearer {api_key}"}
    try:
        resp = requests.get(f"{OPENROUTER_BASE}/models", headers=headers, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            models = []
            for m in data.get("data", []):
                mid = m.get("id", "")
                if mid and is_free_model(mid):
                    models.append({
                        "id": mid,
                        "name": m.get("name", mid),
                        "pricing": m.get("pricing", {}),
                    })
            return models
    except Exception as e:
        print(f"[OpenRouter] Erro ao buscar modelos: {e}")
    return []


def pick_free_model_for_role(role: str, available_models: list) -> str:
    prefs = ROLE_FREE_MODELS.get(role, ["qwen/qwen3-next-80b-a3b-instruct:free"])
    available_ids = {m["id"] for m in available_models} if available_models else set()
    for pref in prefs:
        if pref in available_ids:
            return pref
    fallback = [m["id"] for m in available_models if is_free_model(m["id"])] if available_models else []
    return fallback[0] if fallback else "qwen/qwen3-next-80b-a3b-instruct:free"


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
