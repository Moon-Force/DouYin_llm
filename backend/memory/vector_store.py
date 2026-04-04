import hashlib
import math
import re

from backend.schemas.live import LiveEvent

try:
    import chromadb
except ImportError:  # pragma: no cover - optional dependency
    chromadb = None


class HashEmbeddingFunction:
    def __init__(self, dimensions=64):
        self.dimensions = dimensions

    def embed_text(self, text):
        vector = [0.0] * self.dimensions
        tokens = re.findall(r"[\w\u4e00-\u9fff]+", text.lower())
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
    def __init__(self, storage_path):
        self._items = []
        self.collection = None
        self.embedding = HashEmbeddingFunction()

        if chromadb:
            client = chromadb.PersistentClient(path=str(storage_path))
            self.collection = client.get_or_create_collection("live_history")

    def add_event(self, event: LiveEvent):
        if not event.content:
            return

        document = f"{event.user.nickname} {event.content}".strip()
        metadata = {"room_id": event.room_id, "event_type": event.event_type}

        if self.collection:
            self.collection.upsert(
                ids=[event.event_id],
                documents=[document],
                metadatas=[metadata],
                embeddings=[self.embedding.embed_text(document)],
            )
            return

        self._items.append({"id": event.event_id, "document": document, "metadata": metadata})
        self._items = self._items[-500:]

    def similar(self, text, limit=3):
        if not text:
            return []

        if self.collection:
            result = self.collection.query(
                query_embeddings=[self.embedding.embed_text(text)],
                n_results=limit,
            )
            return result.get("documents", [[]])[0]

        words = set(re.findall(r"[\w\u4e00-\u9fff]+", text.lower()))
        scored = []
        for item in self._items:
            target_words = set(re.findall(r"[\w\u4e00-\u9fff]+", item["document"].lower()))
            overlap = len(words & target_words)
            if overlap:
                scored.append((overlap, item["document"]))

        scored.sort(reverse=True)
        return [document for _, document in scored[:limit]]
