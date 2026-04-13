"""后端配置模块。

配置优先从环境变量和 `.env` 读取，默认值尽量保证本地开箱可跑。
"""

import os
import re
from dataclasses import dataclass
from pathlib import Path


def load_dotenv(dotenv_path=".env"):
    """读取项目根目录下的 `.env` 文件。

    这里只实现项目实际需要的最小功能：
    - 支持 `KEY=VALUE`
    - 支持注释和空行
    """

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

        if key:
            os.environ[key] = value


load_dotenv()


@dataclass
class Settings:
    """后端运行时配置集合。"""

    app_host: str = os.getenv("APP_HOST", "127.0.0.1")
    app_port: int = int(os.getenv("APP_PORT", "8010"))
    room_id: str = os.getenv("ROOM_ID", "")
    collector_enabled: bool = os.getenv("COLLECTOR_ENABLED", "true").lower() in {"1", "true", "yes", "on"}
    collector_host: str = os.getenv("COLLECTOR_HOST", "127.0.0.1")
    collector_port: int = int(os.getenv("COLLECTOR_PORT", "1088"))
    collector_ping_interval_seconds: float = float(os.getenv("COLLECTOR_PING_INTERVAL_SECONDS", "30"))
    collector_reconnect_delay_seconds: float = float(os.getenv("COLLECTOR_RECONNECT_DELAY_SECONDS", "3"))
    data_dir: Path = Path(os.getenv("DATA_DIR", "data"))
    database_path: Path = Path(os.getenv("DATABASE_PATH", "data/live_prompter.db"))
    chroma_dir: Path = Path(os.getenv("CHROMA_DIR", "data/chroma"))
    redis_url: str = os.getenv("REDIS_URL", "")
    session_ttl_seconds: int = int(os.getenv("SESSION_TTL_SECONDS", "14400"))
    llm_mode: str = os.getenv("LLM_MODE", "heuristic")
    llm_base_url: str = os.getenv("LLM_BASE_URL", "")
    llm_model: str = os.getenv("LLM_MODEL", "")
    llm_api_key: str = os.getenv("LLM_API_KEY", "") or os.getenv("DASHSCOPE_API_KEY", "")
    llm_temperature: float = float(os.getenv("LLM_TEMPERATURE", "0.4"))
    llm_timeout_seconds: float = float(os.getenv("LLM_TIMEOUT_SECONDS", "6.0"))
    llm_max_tokens: int = int(os.getenv("LLM_MAX_TOKENS", "120"))
    embedding_mode: str = os.getenv("EMBEDDING_MODE", "cloud").strip().lower()
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
    embedding_base_url: str = os.getenv("EMBEDDING_BASE_URL", "https://api.openai.com/v1")
    embedding_api_key: str = os.getenv("EMBEDDING_API_KEY", "") or os.getenv("LLM_API_KEY", "") or os.getenv("DASHSCOPE_API_KEY", "")
    embedding_timeout_seconds: float = float(os.getenv("EMBEDDING_TIMEOUT_SECONDS", "10.0"))
    local_embedding_device: str = os.getenv("LOCAL_EMBEDDING_DEVICE", "cpu")
    local_embedding_batch_size: int = int(os.getenv("LOCAL_EMBEDDING_BATCH_SIZE", "32"))
    semantic_event_min_score: float = float(os.getenv("SEMANTIC_EVENT_MIN_SCORE", "0.35"))
    semantic_memory_min_score: float = float(os.getenv("SEMANTIC_MEMORY_MIN_SCORE", "0.35"))
    semantic_event_query_limit: int = int(os.getenv("SEMANTIC_EVENT_QUERY_LIMIT", "8"))
    semantic_memory_query_limit: int = int(os.getenv("SEMANTIC_MEMORY_QUERY_LIMIT", "6"))
    semantic_final_k: int = int(os.getenv("SEMANTIC_FINAL_K", "3"))

    def ensure_dirs(self):
        """创建运行期需要的本地数据目录。"""

        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self.chroma_dir.mkdir(parents=True, exist_ok=True)

    def resolved_llm_base_url(self):
        """解析最终实际使用的模型服务地址。"""

        if self.llm_base_url:
            return self.llm_base_url.rstrip("/")

        if self.llm_mode == "qwen":
            return "https://dashscope.aliyuncs.com/compatible-mode/v1"

        return "https://api.openai.com/v1"

    def resolved_llm_model(self):
        """解析最终实际使用的模型名。"""

        if self.llm_model:
            return self.llm_model

        if self.llm_mode == "qwen":
            return "qwen-plus-latest"

        return "gpt-4.1-mini"

    def embedding_signature(self):
        mode = re.sub(r"[^a-z0-9]+", "_", self.embedding_mode.strip().lower()).strip("_") or "unknown"
        model = re.sub(r"[^a-z0-9]+", "_", self.embedding_model.strip().lower()).strip("_") or "default"
        return f"{mode}_{model}"


settings = Settings()
