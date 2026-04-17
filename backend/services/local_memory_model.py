"""In-process local runtime wrapper for memory extraction model."""

from __future__ import annotations

from pathlib import Path
from urllib.request import urlretrieve


class LocalMemoryExtractionModel:
    """Lazy local LLM runtime used by the memory extractor."""

    def __init__(self, settings, downloader=None, llama_factory=None):
        self._settings = settings
        self._downloader = downloader or self._default_downloader
        self._llama_factory = llama_factory
        self._runtime = None

    def _configured_model_file_path(self) -> Path:
        model_path = Path(self._settings.memory_extractor_model_path)
        if model_path.exists() and model_path.is_file():
            return model_path
        return Path(self._settings.memory_extractor_model_file_path)

    @staticmethod
    def _is_valid_model_file(path: Path) -> bool:
        if not path.is_file():
            return False
        try:
            return path.stat().st_size > 0
        except OSError:
            return False

    def resolve_model_path(self) -> Path:
        model_file = self._configured_model_file_path()
        if self._is_valid_model_file(model_file):
            return model_file

        model_url = (self._settings.memory_extractor_model_url or "").strip()
        if not model_url:
            raise FileNotFoundError(f"Local memory extractor model not found: {model_file}")

        model_file.parent.mkdir(parents=True, exist_ok=True)
        self._downloader(model_url, model_file)
        if not self._is_valid_model_file(model_file):
            raise FileNotFoundError(f"Downloaded model is missing or invalid: {model_file}")
        return model_file

    def _resolve_llama_factory(self):
        if self._llama_factory is not None:
            return self._llama_factory
        try:
            from llama_cpp import Llama  # pylint: disable=import-outside-toplevel
        except ImportError as exc:
            raise RuntimeError(
                "llama_cpp is required for local memory extraction runtime. Install llama-cpp-python first."
            ) from exc
        self._llama_factory = Llama
        return self._llama_factory

    def _runtime_instance(self):
        if self._runtime is not None:
            return self._runtime

        llama_factory = self._resolve_llama_factory()
        model_file = self.resolve_model_path()
        self._runtime = llama_factory(
            model_path=str(model_file),
            n_ctx=self._settings.memory_extractor_context_size,
            n_threads=self._settings.memory_extractor_threads,
            verbose=False,
        )
        return self._runtime

    def infer_json(self, system_prompt: str, user_prompt: str) -> str:
        runtime = self._runtime_instance()
        response = runtime.create_chat_completion(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            max_tokens=self._settings.memory_extractor_max_tokens,
        )
        return response["choices"][0]["message"]["content"]

    @staticmethod
    def _default_downloader(model_url: str, destination: Path):
        urlretrieve(model_url, str(destination))
