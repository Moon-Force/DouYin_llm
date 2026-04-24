import json
import unittest
from unittest.mock import MagicMock
from unittest.mock import patch

from backend.services.memory_reranker import GiteeRerankClient
from backend.services.memory_reranker import MemoryReranker


class MemoryRerankerTests(unittest.TestCase):
    def test_gitee_rerank_client_posts_documents_and_returns_scores(self):
        response_payload = {
            "results": [
                {"index": 1, "relevance_score": 0.92},
                {"index": 0, "relevance_score": 0.31},
            ]
        }

        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def read(self):
                return json.dumps(response_payload).encode("utf-8")

        captured = {}

        def fake_urlopen(request, timeout):
            captured["url"] = request.full_url
            captured["timeout"] = timeout
            captured["headers"] = dict(request.header_items())
            captured["body"] = json.loads(request.data.decode("utf-8"))
            return FakeResponse()

        client = GiteeRerankClient(
            base_url="https://ai.gitee.com/v1",
            api_key="test-key",
            model="Qwen3-Reranker-0.6B",
            timeout_seconds=3,
        )

        with patch("backend.services.memory_reranker.urllib.request.urlopen", side_effect=fake_urlopen):
            scores = client.rerank("query", ["doc-a", "doc-b"], top_n=2)

        self.assertEqual(scores, {1: 0.92, 0: 0.31})
        self.assertEqual(captured["url"], "https://ai.gitee.com/v1/rerank")
        self.assertEqual(captured["timeout"], 3)
        self.assertEqual(captured["headers"].get("Authorization"), "Bearer test-key")
        self.assertEqual(captured["body"]["model"], "Qwen3-Reranker-0.6B")
        self.assertEqual(captured["body"]["query"], "query")
        self.assertEqual(captured["body"]["documents"], ["doc-a", "doc-b"])
        self.assertEqual(captured["body"]["top_n"], 2)

    def test_memory_reranker_orders_items_by_online_score(self):
        client = MagicMock()
        client.rerank.return_value = {0: 0.2, 1: 0.9}
        reranker = MemoryReranker(client=client, enabled=True)
        items = [
            {"memory_id": "a", "memory_text": "家里养了猫", "memory_recall_text": "宠物 猫"},
            {"memory_id": "b", "memory_text": "喜欢拉面", "memory_recall_text": "食物 拉面"},
        ]

        result = reranker.rerank("想吃面", items, top_n=2)

        self.assertEqual([item["memory_id"] for item in result], ["b", "a"])
        self.assertEqual(result[0]["rerank_score"], 0.9)
        self.assertEqual(result[0]["rerank_provider"], "gitee")

    def test_memory_reranker_falls_back_to_original_order_on_error(self):
        client = MagicMock()
        client.rerank.side_effect = RuntimeError("down")
        reranker = MemoryReranker(client=client, enabled=True)
        items = [{"memory_id": "a", "memory_text": "A"}, {"memory_id": "b", "memory_text": "B"}]

        result = reranker.rerank("query", items, top_n=2)

        self.assertEqual([item["memory_id"] for item in result], ["a", "b"])


if __name__ == "__main__":
    unittest.main()
