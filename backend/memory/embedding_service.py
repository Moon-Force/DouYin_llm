"""Embedding service with local/cloud backends and hash fallback."""

import json
import logging
import urllib.request

from backend.memory.vector_store import HashEmbeddingFunction

try:
    from sentence_transformers import SentenceTransformer
except ImportError:  # pragma: no cover - optional dependency
    SentenceTransformer = None


logger = logging.getLogger(__name__)


class EmbeddingService:
    def __init__(self, settings, fallback_dimensions=256):
        self.settings = settings
        self.fallback = HashEmbeddingFunction(dimensions=fallback_dimensions)
        self._local_model = None
        self._fallback_logged = False

    def embed_text(self, text: str) -> list[float]:
        return self.embed_texts([text])[0]

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        normalized = [str(text or "").strip() for text in texts]
        if not normalized:
            return []

        try:
            if self.settings.embedding_mode == "local":
                return self._embed_local(normalized)
            if self.settings.embedding_mode == "cloud":
                return self._embed_cloud(normalized)
        except Exception as exc:
            if not self._fallback_logged:
                logger.warning(
                    "Embedding backend failed; falling back to hash embeddings: mode=%s model=%s error=%s",
                    self.settings.embedding_mode,
                    self.settings.embedding_model,
                    exc,
                )
                self._fallback_logged = True

        return [self.fallback.embed_text(text) for text in normalized]

    def _get_local_model(self):
        if self._local_model is None:
            if SentenceTransformer is None:
                raise RuntimeError("sentence-transformers is not installed")
            logger.info(
                "Loading local embedding model: model=%s device=%s",
                self.settings.embedding_model,
                self.settings.local_embedding_device,
            )
            self._local_model = SentenceTransformer(
                self.settings.embedding_model,
                device=self.settings.local_embedding_device,
            )
        return self._local_model

    def _embed_local(self, texts: list[str]) -> list[list[float]]:
        model = self._get_local_model()
        vectors = model.encode(
            texts,
            batch_size=self.settings.local_embedding_batch_size,
            convert_to_numpy=False,
            normalize_embeddings=True,
        )
        return [list(vector) for vector in vectors]

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
        self._fallback_logged = False
        return [list(item["embedding"]) for item in payload["data"]]
