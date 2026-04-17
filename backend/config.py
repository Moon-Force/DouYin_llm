"""Backend runtime configuration."""

import os
import re
from dataclasses import dataclass, field
from pathlib import Path


def load_dotenv(dotenv_path=".env"):
    """Load simple KEY=VALUE pairs from .env."""

    path = Path(dotenv_path)
    if not path.exists():
        return

    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue

        key, value = stripped.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'").strip('"')

        if key and key not in os.environ:
            os.environ[key] = value


load_dotenv()

_TRUE_VALUES = {"1", "true", "yes", "on"}


def _env_bool(key, default):
    return os.getenv(key, str(default)).strip().lower() in _TRUE_VALUES


def _env_int(key, default):
    value = os.getenv(key, "")
    if value is None:
        return int(default)
    value = value.strip()
    if value == "":
        return int(default)
    return int(value)


def _env_float(key, default):
    value = os.getenv(key, "")
    if value is None:
        return float(default)
    value = value.strip()
    if value == "":
        return float(default)
    return float(value)


def _env_path(key, default):
    value = os.getenv(key, "").strip()
    if value:
        return Path(value)
    return Path(default)


def _default_memory_extractor_model_dir():
    local_app_data = os.getenv("LOCALAPPDATA", "").strip()
    if local_app_data:
        return Path(local_app_data) / "DouYinLLM" / "models" / "memory_extractor"

    return Path.home() / ".douyin_llm" / "models" / "memory_extractor"


def _memory_extractor_model_path():
    value = os.getenv("MEMORY_EXTRACTOR_MODEL_PATH", "").strip()
    if value:
        return Path(value)
    return _default_memory_extractor_model_dir()


@dataclass
class Settings:
    """Backend settings."""

    app_host: str = field(default_factory=lambda: os.getenv("APP_HOST", "127.0.0.1"))
    app_port: int = field(default_factory=lambda: _env_int("APP_PORT", 8010))
    room_id: str = field(default_factory=lambda: os.getenv("ROOM_ID", ""))
    collector_enabled: bool = field(default_factory=lambda: _env_bool("COLLECTOR_ENABLED", True))
    collector_host: str = field(default_factory=lambda: os.getenv("COLLECTOR_HOST", "127.0.0.1"))
    collector_port: int = field(default_factory=lambda: _env_int("COLLECTOR_PORT", 1088))
    collector_ping_interval_seconds: float = field(default_factory=lambda: _env_float("COLLECTOR_PING_INTERVAL_SECONDS", 30))
    collector_reconnect_delay_seconds: float = field(
        default_factory=lambda: _env_float("COLLECTOR_RECONNECT_DELAY_SECONDS", 3)
    )
    data_dir: Path = field(default_factory=lambda: _env_path("DATA_DIR", "data"))
    database_path: Path = field(default_factory=lambda: _env_path("DATABASE_PATH", "data/live_prompter.db"))
    chroma_dir: Path = field(default_factory=lambda: _env_path("CHROMA_DIR", "data/chroma"))
    redis_url: str = field(default_factory=lambda: os.getenv("REDIS_URL", ""))
    session_ttl_seconds: int = field(default_factory=lambda: _env_int("SESSION_TTL_SECONDS", 14400))
    llm_mode: str = field(default_factory=lambda: os.getenv("LLM_MODE", "heuristic"))
    llm_base_url: str = field(default_factory=lambda: os.getenv("LLM_BASE_URL", ""))
    llm_model: str = field(default_factory=lambda: os.getenv("LLM_MODEL", ""))
    llm_api_key: str = field(default_factory=lambda: os.getenv("LLM_API_KEY", "") or os.getenv("DASHSCOPE_API_KEY", ""))
    llm_temperature: float = field(default_factory=lambda: _env_float("LLM_TEMPERATURE", 0.4))
    llm_timeout_seconds: float = field(default_factory=lambda: _env_float("LLM_TIMEOUT_SECONDS", 6.0))
    llm_max_tokens: int = field(default_factory=lambda: _env_int("LLM_MAX_TOKENS", 120))
    embedding_mode: str = field(default_factory=lambda: os.getenv("EMBEDDING_MODE", "cloud").strip().lower())
    embedding_strict: bool = field(default_factory=lambda: _env_bool("EMBEDDING_STRICT", False))
    embedding_model: str = field(default_factory=lambda: os.getenv("EMBEDDING_MODEL", "text-embedding-3-small"))
    embedding_base_url: str = field(default_factory=lambda: os.getenv("EMBEDDING_BASE_URL", "https://api.openai.com/v1"))
    embedding_api_key: str = field(
        default_factory=lambda: os.getenv("EMBEDDING_API_KEY", "")
        or os.getenv("LLM_API_KEY", "")
        or os.getenv("DASHSCOPE_API_KEY", "")
    )
    embedding_timeout_seconds: float = field(default_factory=lambda: _env_float("EMBEDDING_TIMEOUT_SECONDS", 10.0))
    local_embedding_device: str = field(default_factory=lambda: os.getenv("LOCAL_EMBEDDING_DEVICE", "cpu"))
    local_embedding_batch_size: int = field(default_factory=lambda: _env_int("LOCAL_EMBEDDING_BATCH_SIZE", 32))
    semantic_memory_min_score: float = field(default_factory=lambda: _env_float("SEMANTIC_MEMORY_MIN_SCORE", 0.35))
    semantic_memory_query_limit: int = field(default_factory=lambda: _env_int("SEMANTIC_MEMORY_QUERY_LIMIT", 6))
    semantic_final_k: int = field(default_factory=lambda: _env_int("SEMANTIC_FINAL_K", 3))
    memory_extractor_enabled: bool = field(default_factory=lambda: _env_bool("MEMORY_EXTRACTOR_ENABLED", False))
    memory_extractor_mode: str = field(default_factory=lambda: os.getenv("MEMORY_EXTRACTOR_MODE", "local").strip().lower())
    memory_extractor_model_path: Path = field(default_factory=_memory_extractor_model_path)
    memory_extractor_model_url: str = field(default_factory=lambda: os.getenv("MEMORY_EXTRACTOR_MODEL_URL", ""))
    memory_extractor_model_filename: str = field(
        default_factory=lambda: os.getenv("MEMORY_EXTRACTOR_MODEL_FILENAME", "memory-extractor.gguf")
    )
    memory_extractor_context_size: int = field(default_factory=lambda: _env_int("MEMORY_EXTRACTOR_CONTEXT_SIZE", 4096))
    memory_extractor_max_tokens: int = field(default_factory=lambda: _env_int("MEMORY_EXTRACTOR_MAX_TOKENS", 512))
    memory_extractor_timeout_seconds: float = field(
        default_factory=lambda: _env_float("MEMORY_EXTRACTOR_TIMEOUT_SECONDS", 30.0)
    )
    memory_extractor_threads: int = field(
        default_factory=lambda: _env_int("MEMORY_EXTRACTOR_THREADS", max(1, min(8, os.cpu_count() or 1)))
    )

    def ensure_dirs(self):
        """Create required runtime directories."""

        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self.chroma_dir.mkdir(parents=True, exist_ok=True)
        self.memory_extractor_model_path.mkdir(parents=True, exist_ok=True)

    def resolved_llm_base_url(self):
        """Resolve effective LLM base URL."""

        if self.llm_base_url:
            return self.llm_base_url.rstrip("/")

        if self.llm_mode == "qwen":
            return "https://dashscope.aliyuncs.com/compatible-mode/v1"

        return "https://api.openai.com/v1"

    def resolved_llm_model(self):
        """Resolve effective LLM model."""

        if self.llm_model:
            return self.llm_model

        if self.llm_mode == "qwen":
            return "qwen-plus-latest"

        return "gpt-4.1-mini"

    def embedding_signature(self):
        mode = re.sub(r"[^a-z0-9]+", "_", self.embedding_mode.strip().lower()).strip("_") or "unknown"
        model = re.sub(r"[^a-z0-9]+", "_", self.embedding_model.strip().lower()).strip("_") or "default"
        return f"{mode}_{model}"

    @property
    def memory_extractor_model_file_path(self):
        return self.memory_extractor_model_path / self.memory_extractor_model_filename


settings = Settings()
