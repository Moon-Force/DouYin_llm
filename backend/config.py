import os
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Settings:
    app_host: str = os.getenv("APP_HOST", "127.0.0.1")
    app_port: int = int(os.getenv("APP_PORT", "8000"))
    room_id: str = os.getenv("ROOM_ID", "32137571630")
    data_dir: Path = Path(os.getenv("DATA_DIR", "data"))
    database_path: Path = Path(os.getenv("DATABASE_PATH", "data/live_prompter.db"))
    chroma_dir: Path = Path(os.getenv("CHROMA_DIR", "data/chroma"))
    redis_url: str = os.getenv("REDIS_URL", "")
    session_ttl_seconds: int = int(os.getenv("SESSION_TTL_SECONDS", "14400"))
    llm_mode: str = os.getenv("LLM_MODE", "heuristic")
    llm_base_url: str = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
    llm_model: str = os.getenv("LLM_MODEL", "gpt-4.1-mini")
    llm_api_key: str = os.getenv("LLM_API_KEY", "")
    llm_temperature: float = float(os.getenv("LLM_TEMPERATURE", "0.4"))

    def ensure_dirs(self):
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self.chroma_dir.mkdir(parents=True, exist_ok=True)


settings = Settings()
