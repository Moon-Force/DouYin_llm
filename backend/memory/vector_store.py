"""Vector-backed recall helpers for viewer memories."""

import hashlib
import logging
import math
import re

from backend.schemas.live import ViewerMemory

try:
    import chromadb
except ImportError:  # pragma: no cover - optional dependency
    chromadb = None


logger = logging.getLogger(__name__)


def tokenize_text(text):
    normalized = str(text or "").lower().strip()
    if not normalized:
        return []

    tokens = set(re.findall(r"[a-z0-9]+", normalized))
    for run in re.findall(r"[\u4e00-\u9fff]+", normalized):
        tokens.update(run)
        tokens.update(run[index : index + 2] for index in range(len(run) - 1))
        if len(run) <= 12:
            tokens.add(run)

    return [token for token in tokens if token]


class HashEmbeddingFunction:
    """Local hashing fallback when no external embedding model is available."""

    def __init__(self, dimensions=256):
        self.dimensions = dimensions

    def embed_text(self, text):
        vector = [0.0] * self.dimensions
        tokens = tokenize_text(text)
        if not tokens:
            return vector

        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = digest[0] % self.dimensions
            sign = 1.0 if digest[1] % 2 == 0 else -1.0
            vector[index] += sign

        length = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [value / length for value in vector]

    def __call__(self, input):
        return [self.embed_text(text) for text in input]


class VectorMemory:
    def __init__(self, storage_path, settings=None, embedding_service=None):
        self.settings = settings
        self._memory_items = []
        self._client = None
        self.collection = None
        self.memory_collection = None
        self.embedding = embedding_service or HashEmbeddingFunction()
        self._collection_suffix = settings.embedding_signature() if settings else "hash_default"
        self._semantic_backend_reason = ""

        if chromadb:
            client = chromadb.PersistentClient(path=str(storage_path))
            self._client = client
            self.memory_collection = client.get_or_create_collection(f"viewer_memories_{self._collection_suffix}")
            self._semantic_backend_reason = ""
            logger.info(
                "VectorMemory initialized with Chroma collection: memories=%s",
                f"viewer_memories_{self._collection_suffix}",
            )
        else:
            self._semantic_backend_reason = "Chroma is unavailable"
            logger.warning(
                "Chroma is unavailable; VectorMemory will use in-process fallback indexes only (suffix=%s)",
                self._collection_suffix,
            )

    def _strict_mode_enabled(self):
        return bool(getattr(self.settings, "embedding_strict", False))

    def semantic_backend_ready(self):
        return self.memory_collection is not None and self._client is not None

    def semantic_backend_reason(self):
        if self.semantic_backend_ready():
            return ""
        return self._semantic_backend_reason or "Semantic vector backend is unavailable"

    def _raise_strict_mode_error(self, exc):
        raise RuntimeError(f"Vector recall strict mode blocked fallback: {exc}") from (
            exc if isinstance(exc, Exception) else None
        )

    def _ensure_semantic_backend(self):
        if self._strict_mode_enabled() and not self.semantic_backend_ready():
            self._raise_strict_mode_error(self.semantic_backend_reason())

    @staticmethod
    def _distance_to_score(distance):
        if distance is None:
            return 0.0
        return 1.0 / (1.0 + float(distance))

    def _memory_min_score(self):
        return getattr(self.settings, "semantic_memory_min_score", 0.0) if self.settings else 0.0

    def _memory_query_limit(self, limit):
        base = getattr(self.settings, "semantic_memory_query_limit", limit) if self.settings else limit
        return max(int(limit), int(base))

    def _final_k(self, limit):
        base = getattr(self.settings, "semantic_final_k", limit) if self.settings else limit
        return min(int(limit), int(base))

    @staticmethod
    def _memory_rank_key(item, query_text):
        text = str(item.get("memory_text") or "")
        metadata = item.get("metadata") or {}
        contains_query = 1 if query_text and query_text in text else 0
        confidence = float(metadata.get("confidence") or 0.0)
        recall_count = int(metadata.get("recall_count") or 0)
        updated_at = int(metadata.get("updated_at") or 0)
        reranked_score = (
            float(item.get("score", 0.0))
            + (0.1 * confidence)
            + (0.02 * contains_query)
            + (0.01 * min(recall_count, 10))
        )
        return (reranked_score, updated_at)

    @staticmethod
    def _score_tokens(query_tokens, target_tokens, query_text, target_text):
        if not query_tokens or not target_tokens:
            return 0.0

        overlap = len(query_tokens & target_tokens)
        if overlap == 0:
            return 0.0

        score = overlap / math.sqrt(len(query_tokens) * len(target_tokens))
        if query_text and query_text in target_text:
            score += 0.35
        return score

    def add_memory(self, memory: ViewerMemory):
        if not memory.memory_text or not memory.viewer_id:
            return

        metadata = {
            "room_id": memory.room_id,
            "viewer_id": memory.viewer_id,
            "memory_type": memory.memory_type,
            "source_event_id": memory.source_event_id,
            "confidence": memory.confidence,
            "updated_at": memory.updated_at,
            "recall_count": memory.recall_count,
        }
        self._memory_items = [item for item in self._memory_items if item["id"] != memory.memory_id]
        self._memory_items.append({"id": memory.memory_id, "document": memory.memory_text, "metadata": metadata})
        self._memory_items = self._memory_items[-3000:]

        self._ensure_semantic_backend()
        if self.memory_collection:
            self.memory_collection.upsert(
                ids=[memory.memory_id],
                documents=[memory.memory_text],
                metadatas=[metadata],
                embeddings=[self.embedding.embed_text(memory.memory_text)],
            )

    def similar_memories(self, text, room_id, viewer_id, limit=3):
        query_text = str(text or "").strip()
        room_id = str(room_id or "").strip()
        viewer_id = str(viewer_id or "").strip()
        if not query_text or not room_id or not viewer_id:
            return []
        self._ensure_semantic_backend()
        query_limit = self._memory_query_limit(limit)
        min_score = self._memory_min_score()
        final_k = self._final_k(limit)

        if self.memory_collection:
            try:
                result = self.memory_collection.query(
                    query_embeddings=[self.embedding.embed_text(query_text)],
                    n_results=query_limit,
                    where={"$and": [{"room_id": room_id}, {"viewer_id": viewer_id}]},
                )
                ids = result.get("ids", [[]])[0]
                documents = result.get("documents", [[]])[0]
                metadatas = result.get("metadatas", [[]])[0]
                distances = result.get("distances", [[]])[0]
                items = []
                for index, memory_id in enumerate(ids):
                    score = self._distance_to_score(distances[index] if index < len(distances) else None)
                    if score < min_score:
                        continue
                    items.append(
                        {
                            "memory_id": memory_id,
                            "memory_text": documents[index] if index < len(documents) else "",
                            "score": score,
                            "metadata": metadatas[index] if index < len(metadatas) else {},
                        }
                    )
                items.sort(key=lambda item: self._memory_rank_key(item, query_text), reverse=True)
                return items[:final_k]
            except Exception as exc:
                if self._strict_mode_enabled():
                    logger.error("Vector recall failed and strict mode blocked fallback: %s", exc)
                    self._raise_strict_mode_error(exc)

        query_tokens = set(tokenize_text(query_text))
        scored = []
        for item in self._memory_items:
            metadata = item["metadata"]
            if metadata.get("room_id") != room_id or metadata.get("viewer_id") != viewer_id:
                continue
            target_text = item["document"]
            target_tokens = set(tokenize_text(target_text))
            score = self._score_tokens(query_tokens, target_tokens, query_text, target_text)
            if score >= min_score:
                scored.append(
                    {
                        "memory_id": item["id"],
                        "memory_text": target_text,
                        "score": score,
                        "metadata": metadata,
                    }
                )

        scored.sort(key=lambda item: self._memory_rank_key(item, query_text), reverse=True)
        return scored[:final_k]
