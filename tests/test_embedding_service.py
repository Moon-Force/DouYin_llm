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

    def test_local_mode_falls_back_to_hash_embedding_when_local_backend_is_removed(self):
        service = EmbeddingService(make_settings(embedding_mode="local"), fallback_dimensions=8)

        vector = service.embed_text("fallback text")

        self.assertEqual(len(vector), 8)
        self.assertTrue(any(value != 0.0 for value in vector))

    def test_local_mode_does_not_use_sentence_transformer_even_if_available(self):
        fake_model = type(
            "FakeModel",
            (),
            {
                "encode": lambda self, texts, **kwargs: [[0.4, 0.5, 0.6] for _ in texts],
            },
        )()

        with patch("backend.memory.embedding_service.SentenceTransformer", return_value=fake_model, create=True):
            service = EmbeddingService(make_settings(embedding_mode="local"), fallback_dimensions=8)
            vector = service.embed_text("fallback text")

        self.assertEqual(len(vector), 8)
        self.assertTrue(any(value != 0.0 for value in vector))
        self.assertNotEqual(vector, [0.4, 0.5, 0.6])

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

    def test_strict_mode_raises_when_local_mode_is_requested(self):
        service = EmbeddingService(
            make_settings(
                embedding_mode="local",
                embedding_strict=True,
            )
        )

        with self.assertRaisesRegex(RuntimeError, "strict mode"):
            service.embed_text("x")


if __name__ == "__main__":
    unittest.main()
