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
        "local_embedding_device": "cpu",
        "local_embedding_batch_size": 8,
        "embedding_strict": False,
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


class EmbeddingServiceTests(unittest.TestCase):
    def test_cloud_mode_uses_embeddings_endpoint(self):
        service = EmbeddingService(make_settings(), fallback_dimensions=8)
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

    def test_local_mode_uses_sentence_transformer(self):
        fake_model = type(
            "FakeModel",
            (),
            {
                "encode": lambda self, texts, **kwargs: [[0.4, 0.5, 0.6] for _ in texts],
            },
        )()

        with patch("backend.memory.embedding_service.SentenceTransformer", return_value=fake_model):
            service = EmbeddingService(make_settings(embedding_mode="local", embedding_model="bge-small-zh-v1.5"))
            vector = service.embed_text("喜欢拉面")

        self.assertEqual(vector, [0.4, 0.5, 0.6])

    def test_non_strict_mode_falls_back_to_hash_embedding_when_cloud_call_fails(self):
        service = EmbeddingService(make_settings(), fallback_dimensions=8)

        with patch("backend.memory.embedding_service.urllib.request.urlopen", side_effect=OSError("network down")):
            vector = service.embed_text("fallback text")

        self.assertEqual(len(vector), 8)
        self.assertTrue(any(value != 0.0 for value in vector))

    def test_strict_mode_raises_when_cloud_embedding_fails(self):
        service = EmbeddingService(make_settings(embedding_strict=True), fallback_dimensions=8)

        with patch("backend.memory.embedding_service.urllib.request.urlopen", side_effect=OSError("network down")):
            with self.assertRaisesRegex(RuntimeError, "strict mode"):
                service.embed_text("fallback text")

    def test_strict_mode_raises_when_local_dependency_is_missing(self):
        service = EmbeddingService(
            make_settings(
                embedding_mode="local",
                embedding_model="bge-small-zh-v1.5",
                embedding_strict=True,
            )
        )

        with patch("backend.memory.embedding_service.SentenceTransformer", None):
            with self.assertRaisesRegex(RuntimeError, "strict mode"):
                service.embed_text("喜欢拉面")


if __name__ == "__main__":
    unittest.main()
