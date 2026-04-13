"""Vector-backed recall helpers for event history and viewer memories."""

import hashlib
import logging
import math
import re

from backend.schemas.live import LiveEvent, ViewerMemory

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
        self._event_items = []
        self._memory_items = []
        self._client = None
        self.collection = None
        self.memory_collection = None
        self.embedding = embedding_service or HashEmbeddingFunction()
        self._collection_suffix = settings.embedding_signature() if settings else "hash_default"

        if chromadb:
            client = chromadb.PersistentClient(path=str(storage_path))
            self._client = client
            self.collection = client.get_or_create_collection(f"live_history_{self._collection_suffix}")
            self.memory_collection = client.get_or_create_collection(f"viewer_memories_{self._collection_suffix}")
            logger.info(
                "VectorMemory initialized with Chroma collections: events=%s memories=%s",
                f"live_history_{self._collection_suffix}",
                f"viewer_memories_{self._collection_suffix}",
            )
        else:
            logger.warning(
                "Chroma is unavailable; VectorMemory will use in-process fallback indexes only (suffix=%s)",
                self._collection_suffix,
            )

    @staticmethod
    def _distance_to_score(distance):
        if distance is None:
            return 0.0
        return 1.0 / (1.0 + float(distance))

    def _event_min_score(self):
        return getattr(self.settings, "semantic_event_min_score", 0.0) if self.settings else 0.0

    def _memory_min_score(self):
        return getattr(self.settings, "semantic_memory_min_score", 0.0) if self.settings else 0.0

    def _event_query_limit(self, limit):
        base = getattr(self.settings, "semantic_event_query_limit", limit) if self.settings else limit
        return max(int(limit), int(base))

    def _memory_query_limit(self, limit):
        base = getattr(self.settings, "semantic_memory_query_limit", limit) if self.settings else limit
        return max(int(limit), int(base))

    def _final_k(self, limit):
        base = getattr(self.settings, "semantic_final_k", limit) if self.settings else limit
        return min(int(limit), int(base))

    @staticmethod
    def _event_rank_key(item, query_text):
        text = str(item.get("text") or "")
        metadata = item.get("metadata") or {}
        contains_query = 1 if query_text and query_text in text else 0
        event_type_boost = 1 if metadata.get("event_type") == "comment" else 0
        ts = int(metadata.get("ts") or 0)
        return (item.get("score", 0.0), contains_query, event_type_boost, ts)

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

    def add_event(self, event: LiveEvent):
        if not event.content:
            return

        document = f"{event.user.nickname} {event.content}".strip()
        metadata = {
            "room_id": event.room_id,
            "event_type": event.event_type,
            "nickname": event.user.nickname,
            "ts": event.ts,
        }
        self._event_items = [item for item in self._event_items if item["id"] != event.event_id]
        self._event_items.append({"id": event.event_id, "document": document, "metadata": metadata})
        self._event_items = self._event_items[-1000:]

        if self.collection:
            self.collection.upsert(
                ids=[event.event_id],
                documents=[document],
                metadatas=[metadata],
                embeddings=[self.embedding.embed_text(document)],
            )

    def similar(self, text, room_id="", limit=3):
        query_text = str(text or "").strip()
        if not query_text:
            return []
        query_limit = self._event_query_limit(limit)
        min_score = self._event_min_score()
        final_k = self._final_k(limit)

        if self.collection:
            try:
                query_kwargs = {
                    "query_embeddings": [self.embedding.embed_text(query_text)],
                    "n_results": query_limit,
                }
                if room_id:
                    query_kwargs["where"] = {"room_id": room_id}
                result = self.collection.query(**query_kwargs)
                ids = result.get("ids", [[]])[0]
                documents = result.get("documents", [[]])[0]
                metadatas = result.get("metadatas", [[]])[0]
                distances = result.get("distances", [[]])[0]
                items = []
                for index, item_id in enumerate(ids):
                    score = self._distance_to_score(distances[index] if index < len(distances) else None)
                    if score < min_score:
                        continue
                    items.append(
                        {
                            "id": item_id,
                            "text": documents[index] if index < len(documents) else "",
                            "score": score,
                            "metadata": metadatas[index] if index < len(metadatas) else {},
                        }
                    )
                items.sort(key=lambda item: self._event_rank_key(item, query_text), reverse=True)
                return items[:final_k]
            except Exception:
                pass

        query_tokens = set(tokenize_text(query_text))
        scored = []
        for item in self._event_items:
            if room_id and item["metadata"].get("room_id") != room_id:
                continue
            target_text = item["document"]
            target_tokens = set(tokenize_text(target_text))
            score = self._score_tokens(query_tokens, target_tokens, query_text, target_text)
            if score >= min_score:
                scored.append(
                    {
                        "id": item["id"],
                        "text": target_text,
                        "score": score,
                        "metadata": item["metadata"],
                    }
                )

        scored.sort(key=lambda item: self._event_rank_key(item, query_text), reverse=True)
        return scored[:final_k]

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
            except Exception:
                pass

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
