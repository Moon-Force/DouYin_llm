"""向量检索记忆层。

如果本地安装了 Chroma，就使用持久化向量库；
否则退化为轻量文本相似度方案，保证检索能力不断路。
"""

import hashlib
import math
import re

from backend.schemas.live import LiveEvent

try:
    import chromadb
except ImportError:  # pragma: no cover - optional dependency
    chromadb = None


class HashEmbeddingFunction:
    """轻量哈希嵌入函数。

    这是没有外部 embedding 模型时的本地替代方案，目标不是高精度，
    而是给历史相似文本检索提供一个可运行的近似能力。
    """

    def __init__(self, dimensions=64):
        self.dimensions = dimensions

    def embed_text(self, text):
        """把文本哈希到固定维度向量，并做归一化。"""

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
        """兼容 Chroma 所需的 embedding 函数调用接口。"""

        return [self.embed_text(text) for text in input]


class VectorMemory:
    def __init__(self, storage_path):
        """初始化向量存储。"""

        self._items = []
        self.collection = None
        self.embedding = HashEmbeddingFunction()

        if chromadb:
            client = chromadb.PersistentClient(path=str(storage_path))
            self.collection = client.get_or_create_collection("live_history")

    def add_event(self, event: LiveEvent):
        """把有内容的事件写入检索索引。"""

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
        """返回与当前文本最相近的历史片段。"""

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
