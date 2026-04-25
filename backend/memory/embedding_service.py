"""Embedding service with HTTP backend only."""

import json
import logging
import urllib.request

logger = logging.getLogger(__name__)


class EmbeddingService:
    def __init__(self, settings):
        self.settings = settings

    def _raise_backend_error(self, exc: Exception):
        raise RuntimeError(
            f"Embedding backend failed: mode={self.settings.embedding_mode} "
            f"model={self.settings.embedding_model} error={exc}"
        ) from exc

    def embed_text(self, text: str) -> list[float]:
        return self.embed_texts([text])[0]

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        normalized = [t for t in (str(text or "").strip() for text in texts) if t]
        if not normalized:
            return []

        try:
            if self.settings.embedding_mode == "cloud":
                return self._embed_cloud(normalized)
            raise RuntimeError(f"Unsupported embedding mode: {self.settings.embedding_mode}")
        except Exception as exc:
            logger.error(
                "Embedding backend failed: mode=%s model=%s error=%s",
                self.settings.embedding_mode,
                self.settings.embedding_model,
                exc,
            )
            self._raise_backend_error(exc)

    def _embed_cloud(self, texts: list[str]) -> list[list[float]]:
        headers = {"Content-Type": "application/json"}
        if self.settings.embedding_api_key:
            headers["Authorization"] = f"Bearer {self.settings.embedding_api_key}"
        logger.info(
            "Requesting cloud embeddings: model=%s count=%s",
            self.settings.embedding_model,
            len(texts),
        )

        request = urllib.request.Request(
            f"{self.settings.embedding_base_url.rstrip('/')}/embeddings",
            data=json.dumps(
                {
                    "model": self.settings.embedding_model,
                    "input": texts,
                },
                ensure_ascii=False,
            ).encode("utf-8"),
            headers=headers,
            method="POST",
        )

        with urllib.request.urlopen(request, timeout=self.settings.embedding_timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8"))
        return [list(item["embedding"]) for item in payload["data"]]
