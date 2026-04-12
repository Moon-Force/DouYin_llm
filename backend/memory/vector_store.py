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
        self._event_items = []
        self._memory_items = []
        self.collection = None
        self.memory_collection = None
        self.embedding = embedding_service or HashEmbeddingFunction()
        self._collection_suffix = settings.embedding_signature() if settings else "hash_default"

        if chromadb:
            client = chromadb.PersistentClient(path=str(storage_path))
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
        metadata = {"room_id": event.room_id, "event_type": event.event_type}
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

        if self.collection:
            try:
                query_kwargs = {
                    "query_embeddings": [self.embedding.embed_text(query_text)],
                    "n_results": limit,
                }
                if room_id:
                    query_kwargs["where"] = {"room_id": room_id}
                result = self.collection.query(**query_kwargs)
                return result.get("documents", [[]])[0]
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
            if score > 0:
                scored.append((score, target_text))

        scored.sort(key=lambda entry: entry[0], reverse=True)
        return [document for _, document in scored[:limit]]

    def add_memory(self, memory: ViewerMemory):
        if not memory.memory_text or not memory.viewer_id:
            return

        metadata = {
            "room_id": memory.room_id,
            "viewer_id": memory.viewer_id,
            "memory_type": memory.memory_type,
            "source_event_id": memory.source_event_id,
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

        if self.memory_collection:
            try:
                result = self.memory_collection.query(
                    query_embeddings=[self.embedding.embed_text(query_text)],
                    n_results=limit,
                    where={"$and": [{"room_id": room_id}, {"viewer_id": viewer_id}]},
                )
                ids = result.get("ids", [[]])[0]
                documents = result.get("documents", [[]])[0]
                metadatas = result.get("metadatas", [[]])[0]
                distances = result.get("distances", [[]])[0]
                items = []
                for index, memory_id in enumerate(ids):
                    distance = distances[index] if index < len(distances) else None
                    score = 1.0 / (1.0 + float(distance)) if distance is not None else 0.0
                    items.append(
                        {
                            "memory_id": memory_id,
                            "memory_text": documents[index] if index < len(documents) else "",
                            "score": score,
                            "metadata": metadatas[index] if index < len(metadatas) else {},
                        }
                    )
                return items
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
            if score > 0:
                scored.append(
                    {
                        "memory_id": item["id"],
                        "memory_text": target_text,
                        "score": score,
                        "metadata": metadata,
                    }
                )

        scored.sort(key=lambda entry: entry["score"], reverse=True)
        return scored[:limit]
