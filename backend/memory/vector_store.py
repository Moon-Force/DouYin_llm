"""Vector-backed recall helpers for viewer memories."""

import hashlib
import logging
import math
import re
import time

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

    def _decay_halflife(self):
        value = getattr(self.settings, "memory_decay_halflife_hours", 0.0) if self.settings else 0.0
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

    def _memory_query_limit(self, limit):
        base = getattr(self.settings, "semantic_memory_query_limit", limit) if self.settings else limit
        return max(int(limit), int(base))

    def _final_k(self, limit):
        base = getattr(self.settings, "semantic_final_k", limit) if self.settings else limit
        return min(int(limit), int(base))

    @staticmethod
    def _memory_metadata(memory):
        return {
            "room_id": memory.room_id,
            "viewer_id": memory.viewer_id,
            "memory_type": memory.memory_type,
            "source_event_id": memory.source_event_id,
            "confidence": memory.confidence,
            "updated_at": memory.updated_at,
            "recall_count": memory.recall_count,
            "status": getattr(memory, "status", "active"),
            "source_kind": getattr(memory, "source_kind", "auto"),
            "is_pinned": 1 if getattr(memory, "is_pinned", False) else 0,
            "stability_score": float(getattr(memory, "stability_score", 0.0) or 0.0),
            "interaction_value_score": float(getattr(memory, "interaction_value_score", 0.0) or 0.0),
            "clarity_score": float(getattr(memory, "clarity_score", 0.0) or 0.0),
            "evidence_score": float(getattr(memory, "evidence_score", 0.0) or 0.0),
            "expires_at": int(getattr(memory, "expires_at", 0) or 0),
        }

    @staticmethod
    def _is_expired(metadata, now_ms):
        expires_at = int((metadata or {}).get("expires_at") or 0)
        return expires_at > 0 and now_ms >= expires_at

    def _active_memory_records(self, memories):
        now_ms = int(time.time() * 1000)
        records = []
        for memory in memories or []:
            if not memory or not getattr(memory, "memory_text", "") or not getattr(memory, "viewer_id", ""):
                continue
            if str(getattr(memory, "status", "active") or "active") != "active":
                continue
            metadata = self._memory_metadata(memory)
            if self._is_expired(metadata, now_ms):
                continue
            records.append(
                {
                    "id": memory.memory_id,
                    "document": memory.memory_text,
                    "metadata": metadata,
                }
            )
        return records

    def _embed_texts(self, texts):
        if hasattr(self.embedding, "embed_texts"):
            return self.embedding.embed_texts(texts)
        return [self.embedding.embed_text(text) for text in texts]

    def _recreate_memory_collection(self):
        if not self._client or not self.memory_collection:
            return
        collection_name = getattr(self.memory_collection, "name", "") or f"viewer_memories_{self._collection_suffix}"
        try:
            self._client.delete_collection(collection_name)
        except Exception:
            logger.warning("Failed to delete stale memory collection during startup warmup: %s", collection_name)
        self.memory_collection = self._client.get_or_create_collection(collection_name)

    def _sample_memory_records(self, records, sample_size=3):
        if not records:
            return []

        size = max(1, int(sample_size))
        samples = []
        for item in records[:size]:
            if item["id"] not in {sample["id"] for sample in samples}:
                samples.append(item)
        for item in records[-size:]:
            if item["id"] not in {sample["id"] for sample in samples}:
                samples.append(item)
        return samples

    def _collection_sample_matches(self, records, sample_size=3):
        if not self.memory_collection:
            return True

        samples = self._sample_memory_records(records, sample_size=sample_size)
        if not samples:
            return True

        expected_by_id = {item["id"]: item for item in samples}
        try:
            result = self.memory_collection.get(
                ids=list(expected_by_id.keys()),
                include=["documents", "metadatas"],
            )
        except Exception:
            return False

        actual_ids = result.get("ids", []) or []
        actual_documents = result.get("documents", []) or []
        actual_metadatas = result.get("metadatas", []) or []
        if len(actual_ids) != len(expected_by_id):
            return False

        for index, memory_id in enumerate(actual_ids):
            expected = expected_by_id.get(memory_id)
            if not expected:
                return False
            if index >= len(actual_documents) or actual_documents[index] != expected["document"]:
                return False
            if index >= len(actual_metadatas) or dict(actual_metadatas[index] or {}) != expected["metadata"]:
                return False
        return True

    def prime_memory_index(self, memories, batch_size=64, force_rebuild=False):
        records = self._active_memory_records(memories)
        self._memory_items = records[-3000:]

        if not self.memory_collection:
            return

        expected_count = len(records)
        try:
            current_count = int(self.memory_collection.count())
        except Exception:
            current_count = -1

        if (
            not force_rebuild
            and current_count == expected_count
            and self._collection_sample_matches(records)
        ):
            return

        if current_count > 0 and expected_count >= 0:
            self._recreate_memory_collection()

        for start in range(0, len(records), max(1, int(batch_size))):
            batch = records[start : start + max(1, int(batch_size))]
            texts = [item["document"] for item in batch]
            self.memory_collection.upsert(
                ids=[item["id"] for item in batch],
                documents=texts,
                metadatas=[item["metadata"] for item in batch],
                embeddings=self._embed_texts(texts),
            )

    @staticmethod
    def _semantic_score(item):
        return float(item.get("score", 0.0))

    @staticmethod
    def _business_rerank_score(item, query_text):
        text = str(item.get("memory_text") or "")
        metadata = item.get("metadata") or {}
        contains_query = 1 if query_text and query_text in text else 0
        confidence = float(metadata.get("confidence") or 0.0)
        interaction_value_score = float(metadata.get("interaction_value_score") or 0.0)
        stability_score = float(metadata.get("stability_score") or 0.0)
        evidence_score = float(metadata.get("evidence_score") or 0.0)
        recall_count = int(metadata.get("recall_count") or 0)
        source_kind = str(metadata.get("source_kind") or "auto")
        is_pinned = int(metadata.get("is_pinned") or 0)
        manual_bonus = 1.0 if source_kind == "manual" else 0.0
        pin_bonus = 1.0 if is_pinned else 0.0
        recall_bonus = min(recall_count, 10) / 10.0

        return (
            (0.35 * interaction_value_score)
            + (0.20 * evidence_score)
            + (0.15 * stability_score)
            + (0.10 * confidence)
            + (0.08 * manual_bonus)
            + (0.07 * pin_bonus)
            + (0.05 * recall_bonus)
            + (0.02 * contains_query)
        )

    @classmethod
    def _final_rank_key(cls, item, query_text, decay_halflife_hours=0):
        metadata = item.get("metadata") or {}
        updated_at = int(metadata.get("updated_at") or 0)
        last_recalled_at = int(metadata.get("last_recalled_at") or 0)
        is_pinned = int(metadata.get("is_pinned") or 0)
        semantic_score = cls._semantic_score(item)
        business_rerank_score = cls._business_rerank_score(item, query_text)
        time_decay = 1.0
        if decay_halflife_hours > 0 and not is_pinned:
            ref_time = max(updated_at, last_recalled_at) if last_recalled_at else updated_at
            if ref_time > 0:
                age_hours = (int(time.time() * 1000) - ref_time) / (1000.0 * 3600.0)
                if age_hours > 0:
                    time_decay = math.pow(2.0, -age_hours / decay_halflife_hours)

        final_score = ((0.55 * semantic_score) + (0.45 * business_rerank_score)) * time_decay
        return (final_score, updated_at)

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
        if str(getattr(memory, "status", "active") or "active") != "active":
            self.remove_memory(memory.memory_id)
            return

        metadata = self._memory_metadata(memory)
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

    def remove_memory(self, memory_id):
        memory_id = str(memory_id or "").strip()
        if not memory_id:
            return
        self._memory_items = [item for item in self._memory_items if item["id"] != memory_id]

        self._ensure_semantic_backend()
        if self.memory_collection:
            self.memory_collection.delete(ids=[memory_id])

    def sync_memory(self, memory):
        if not memory or str(getattr(memory, "status", "active") or "active") != "active":
            self.remove_memory(getattr(memory, "memory_id", ""))
            return
        self.add_memory(memory)

    def similar_memories(self, text, room_id, viewer_id, limit=3):
        query_text = str(text or "").strip()
        room_id = str(room_id or "").strip()
        viewer_id = str(viewer_id or "").strip()
        if not query_text or not room_id or not viewer_id:
            return []
        now_ms = int(time.time() * 1000)
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
                    metadata = metadatas[index] if index < len(metadatas) else {}
                    if str(metadata.get("status") or "active") != "active":
                        continue
                    if self._is_expired(metadata, now_ms):
                        continue
                    score = self._distance_to_score(distances[index] if index < len(distances) else None)
                    if score < min_score:
                        continue
                    items.append(
                        {
                            "memory_id": memory_id,
                            "memory_text": documents[index] if index < len(documents) else "",
                            "score": score,
                            "metadata": metadata,
                        }
                    )
                items.sort(key=lambda item: self._final_rank_key(item, query_text, self._decay_halflife()), reverse=True)
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
            if str(metadata.get("status") or "active") != "active":
                continue
            if self._is_expired(metadata, now_ms):
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

        scored.sort(key=lambda item: self._final_rank_key(item, query_text, self._decay_halflife()), reverse=True)
        return scored[:final_k]
