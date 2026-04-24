import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from backend.memory.embedding_service import EmbeddingService


def make_settings(**overrides):
    defaults = {
        "embedding_mode": "cloud",
        "embedding_model": "text-embedding-3-small",
        "embedding_base_url": "https://example.test/v1",
        "embedding_api_key": "test-key",
        "embedding_timeout_seconds": 10.0,
        "embedding_strict": False,
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


class EmbeddingServiceTests(unittest.TestCase):
    def test_cloud_mode_uses_embeddings_endpoint(self):
        service = EmbeddingService(make_settings())
        captured = {}

        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def read(self):
                return json.dumps(
                    {"data": [{"embedding": [0.1, 0.2, 0.3]}]},
                    ensure_ascii=False,
                ).encode("utf-8")

        def fake_urlopen(request, timeout):
            captured["url"] = request.full_url
            captured["body"] = json.loads(request.data.decode("utf-8"))
            captured["timeout"] = timeout
            return FakeResponse()

        with patch("backend.memory.embedding_service.urllib.request.urlopen", side_effect=fake_urlopen):
            vector = service.embed_text("hello world")

        self.assertEqual(captured["url"], "https://example.test/v1/embeddings")
        self.assertEqual(captured["body"]["model"], "text-embedding-3-small")
        self.assertEqual(captured["body"]["input"], ["hello world"])
        self.assertEqual(captured["timeout"], 10.0)
        self.assertEqual(vector, [0.1, 0.2, 0.3])

    def test_local_mode_raises_when_backend_is_not_supported(self):
        service = EmbeddingService(make_settings(embedding_mode="local"))

        with self.assertRaisesRegex(RuntimeError, "Unsupported embedding mode"):
            service.embed_text("x")

    def test_cloud_mode_raises_when_embedding_call_fails(self):
        service = EmbeddingService(make_settings())

        with patch("backend.memory.embedding_service.urllib.request.urlopen", side_effect=OSError("network down")):
            with self.assertRaisesRegex(RuntimeError, "Embedding backend failed"):
                service.embed_text("fallback text")


if __name__ == "__main__":
    unittest.main()
