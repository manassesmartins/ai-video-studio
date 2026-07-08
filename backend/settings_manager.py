import json
import os
from pathlib import Path
from threading import Lock


DEFAULT_SETTINGS = {
    "agent_configs": {},
    "news_count": 5,
    "rss_feeds": [
        "https://www.tecmundo.com.br/feed",
        "https://g1.globo.com/rss/g1/tecnologia/",
        "https://olhardigital.com.br/feed",
        "https://www.theverge.com/rss/index.xml",
        "https://www.wired.com/feed/rss",
        "https://arstechnica.com/feed/",
        "https://techcrunch.com/feed/",
        "https://www.engadget.com/rss.xml",
    ],
    "openrouter_api_key": "",
    "cached_models": [],
    "video": {
        "width": 1920,
        "height": 1080,
        "fps": 30,
        "codec": "libx264",
        "bitrate": "5000k",
        "format": "mp4",
    },
    "audio": {
        "sample_rate": 44100,
        "bitrate": "192k",
        "codec": "aac",
        "channels": 2,
    },
    "image": {
        "width": 1920,
        "height": 1080,
        "format": "jpg",
    },
    "hired_roles": [],
    "company_level": 1,
    "company_xp": 0,
    "company_videos": 0,
    "company_revenue": 0,
    "company_quality": 30,
    "youtube": {
        "auto_publish": False,
        "privacy": "public",
        "channel_category": "28",
        "channel_name": "AI Studio",
    },
    "theme": "default",
    "font_scale": 1.0,
    "layout_scale": 1.0,
}


class SettingsManager:
    def __init__(self, path: str = None):
        self._path = Path(path or (Path(__file__).parent.parent / "settings.json"))
        self._lock = Lock()
        self._data = dict(DEFAULT_SETTINGS)
        self._load()

    def _load(self):
        if self._path.exists():
            try:
                with open(self._path) as f:
                    loaded = json.load(f)
                for k, v in DEFAULT_SETTINGS.items():
                    if k in loaded and isinstance(v, dict) and isinstance(loaded[k], dict):
                        merged = dict(v)
                        merged.update(loaded[k])
                        self._data[k] = merged
                    elif k in loaded:
                        self._data[k] = loaded[k]
                for k in loaded:
                    if k not in DEFAULT_SETTINGS:
                        self._data[k] = loaded[k]
                # Migração: remover api_keys antigo
                if "api_keys" in self._data:
                    del self._data["api_keys"]
                # Migração: forçar provider=openrouter em agent_configs (exceto local)
                LOCAL_ROLES = {"Editor de Vídeo"}
                ac = self._data.get("agent_configs", {})
                for role, cfg in ac.items():
                    if role in LOCAL_ROLES:
                        cfg["provider"] = "local"
                    else:
                        cfg["provider"] = "openrouter"
                        if not cfg.get("model"):
                            cfg["model"] = "openai/gpt-4o-mini"
            except Exception:
                pass

    def save(self):
        with self._lock:
            tmp = str(self._path) + ".tmp"
            try:
                with open(tmp, "w") as f:
                    json.dump(self._data, f, indent=2)
                os.replace(tmp, self._path)
            except Exception:
                pass

    def get(self, key, default=None):
        return self._data.get(key, default)

    def set(self, key, value):
        self._data[key] = value
        self.save()

    def update(self, key, subkey, value):
        if key not in self._data or not isinstance(self._data[key], dict):
            self._data[key] = {}
        self._data[key][subkey] = value
        self.save()

    def get_nested(self, key, subkey, default=None):
        section = self._data.get(key, {})
        if isinstance(section, dict):
            return section.get(subkey, default)
        return default

    def to_dict(self):
        return dict(self._data)

    def apply_env_api_keys(self):
        from dotenv import load_dotenv
        load_dotenv(Path(__file__).parent.parent / ".env")
        val = os.getenv("OPENROUTER_API_KEY", "")
        if val and not self._data.get("openrouter_api_key"):
            self._data["openrouter_api_key"] = val
            self.save()
