import os

AGENT_PROVIDER_SCHEMA = {
    "Jornalista de Tecnologia": {
        "label": "Jornalista",
        "emoji": "📰",
        "providers": ["openrouter"],
        "default_provider": "openrouter",
        "default_model": "qwen/qwen3.5-flash:free",
        "actions": [
            {"name": "Buscar Notícias", "type": "rss"},
            {"name": "Resumir Artigos", "type": "chat"},
            {"name": "Analisar Relevância", "type": "chat"},
        ]
    },
    "Roteirista Criativo": {
        "label": "Roteirista",
        "emoji": "✍️",
        "providers": ["openrouter"],
        "default_provider": "openrouter",
        "default_model": "qwen/qwen3-next-80b-a3b-instruct:free",
        "actions": [
            {"name": "Criar Roteiro", "type": "chat"},
            {"name": "Revisar Texto", "type": "chat"},
            {"name": "Extrair Segmentos", "type": "chat"},
        ]
    },
    "Artista de Voz": {
        "label": "Locutor",
        "emoji": "🎙️",
        "providers": ["openrouter"],
        "default_provider": "local",
        "default_model": "edge-tts",
        "extra_fields": {
            "voice": {"label": "Voz", "type": "select", "options": ["pt-BR-FranciscaNeural|Francisca (Feminino)", "pt-BR-AntonioNeural|Antonio (Masculino)", "pt-BR-ThalitaMultilingualNeural|Thalita (Feminino)"], "default": "pt-BR-FranciscaNeural"},
            "intro_prompt": {"label": "Frase de abertura", "type": "text", "default": "Olá pessoal! Sejam bem-vindos ao nosso resumo de notícias de tecnologia. Vamos conferir as principais novidades do mundo tech hoje."},
            "outro_prompt": {"label": "Frase de encerramento", "type": "text", "default": "Obrigado por assistir! Não se esqueça de se inscrever para mais conteúdo. Até a próxima!"},
        },
        "actions": [
            {"name": "Gerar Narração", "type": "tts"},
            {"name": "Ajustar Entonação", "type": "settings"},
        ]
    },
    "Designer de Imagens": {
        "label": "Designer",
        "emoji": "🎨",
        "providers": ["openrouter"],
        "default_provider": "openrouter",
        "default_model": "qwen/qwen3-next-80b-a3b-instruct:free",
        "extra_fields": {"image_gen_model": {"label": "Modelo p/ gerar imagens por IA", "options": [], "default": "nenhum"}},
        "actions": [
            {"name": "Buscar Imagens", "type": "search"},
            {"name": "Gerar Descrições", "type": "chat"},
        ]
    },
    "Editor de Vídeo": {
        "label": "Editor",
        "emoji": "🎬",
        "providers": ["local"],
        "default_provider": "local",
        "default_model": "moviepy",
        "extra_fields": {"gpu_accel": {"label": "Aceleração GPU (VAAPI)", "type": "boolean", "default": False}},
        "actions": [
            {"name": "Compor Vídeo", "type": "local"},
            {"name": "Adicionar Transições", "type": "local"},
        ]
    },
    "CEO / Coordenador": {
        "label": "Orquestrador",
        "emoji": "👔",
        "providers": ["openrouter"],
        "default_provider": "openrouter",
        "default_model": "qwen/qwen3-next-80b-a3b-instruct:free",
        "actions": [
            {"name": "Definir Metas", "type": "chat"},
            {"name": "Atribuir Tarefas", "type": "chat"},
            {"name": "Avaliar Resultados", "type": "chat"},
        ]
    },
    "YouTube Publisher": {
        "label": "Publicador",
        "emoji": "▶️",
        "providers": ["openrouter"],
        "default_provider": "openrouter",
        "default_model": "qwen/qwen3-next-80b-a3b-instruct:free",
        "extra_fields": {
            "privacy": {"label": "Privacidade", "type": "select", "options": ["public|Público", "unlisted|Não listado", "private|Privado"], "default": "public"},
            "auto_publish": {"label": "Publicar automaticamente", "type": "boolean", "default": False},
            "channel_category": {"label": "Categoria do Vídeo", "type": "select", "options": ["22|Pessoas & Blogs", "25|Notícias & Política", "28|Ciência & Tecnologia", "24|Entretenimento", "27|Educação"], "default": "28"},
        },
        "actions": [
            {"name": "Autenticar YouTube", "type": "auth"},
            {"name": "Publicar Vídeo", "type": "upload"},
            {"name": "Gerar Thumbnail", "type": "image"},
        ]
    },
}


def default_config_for_role(role: str) -> dict:
    schema = AGENT_PROVIDER_SCHEMA.get(role, {})
    provider = schema.get("default_provider", "openrouter")
    model = schema.get("default_model", "openai/gpt-4o-mini")
    cfg = {
        "provider": provider,
        "model": model,
        "api_key": "",
        "temperature": 0.7,
    }
    extra = schema.get("extra_fields", {})
    for key, val in extra.items():
        cfg[key] = val.get("default", "")
    return cfg
