import json
import io
import unittest
import urllib.error
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


class _FakeResponse:
    def __init__(self, body):
        self._body = body

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class MemoryExtractorClientTests(unittest.TestCase):
    def _settings(self, **overrides):
        values = {
            "memory_extractor_base_url": "http://127.0.0.1:11434/v1",
            "memory_extractor_model": "qwen3:8b",
            "memory_extractor_max_tokens": 256,
            "memory_extractor_timeout_seconds": 9.5,
            "memory_extractor_api_key": "",
        }
        values.update(overrides)
        return SimpleNamespace(**values)

    def test_posts_openai_compatible_payload_to_chat_completions(self):
        from backend.services.memory_extractor_client import MemoryExtractorClient

        with patch(
            "backend.services.memory_extractor_client.urllib.request.urlopen",
            return_value=_FakeResponse(
                b'{"choices":[{"message":{"role":"assistant","content":"{\\"ok\\":true}"}}]}'
            ),
        ) as urlopen:
            client = MemoryExtractorClient(self._settings())

            result = client.infer_json("sys prompt", "user prompt")

        self.assertEqual(result, '{"ok":true}')
        request = urlopen.call_args.args[0]
        self.assertEqual(request.full_url, "http://127.0.0.1:11434/v1/chat/completions")
        self.assertEqual(request.get_method(), "POST")
        self.assertEqual(request.get_header("Content-type"), "application/json; charset=utf-8")
        self.assertEqual(request.get_header("Accept"), "application/json")

        payload = json.loads(request.data.decode("utf-8"))
        self.assertEqual(payload["model"], "qwen3:8b")
        self.assertEqual(payload["max_tokens"], 256)
        self.assertEqual(payload["temperature"], 0)
        self.assertEqual(
            payload["messages"],
            [
                {"role": "system", "content": "sys prompt"},
                {"role": "user", "content": "user prompt"},
            ],
        )

    def test_propagates_configured_timeout(self):
        from backend.services.memory_extractor_client import MemoryExtractorClient

        with patch(
            "backend.services.memory_extractor_client.urllib.request.urlopen",
            return_value=_FakeResponse(b'{"choices":[{"message":{"content":"{}"}}]}'),
        ) as urlopen:
            client = MemoryExtractorClient(self._settings(memory_extractor_timeout_seconds=3.25))

            client.infer_json("sys", "user")

        self.assertEqual(urlopen.call_args.kwargs["timeout"], 3.25)

    def test_uses_configured_model_and_max_tokens(self):
        from backend.services.memory_extractor_client import MemoryExtractorClient

        with patch(
            "backend.services.memory_extractor_client.urllib.request.urlopen",
            return_value=_FakeResponse(b'{"choices":[{"message":{"content":"{}"}}]}'),
        ) as urlopen:
            client = MemoryExtractorClient(
                self._settings(memory_extractor_model="llama3.1:8b", memory_extractor_max_tokens=777)
            )

            client.infer_json("system", "user")

        request = urlopen.call_args.args[0]
        payload = json.loads(request.data.decode("utf-8"))
        self.assertEqual(payload["model"], "llama3.1:8b")
        self.assertEqual(payload["max_tokens"], 777)

    def test_adds_authorization_header_when_api_key_present(self):
        from backend.services.memory_extractor_client import MemoryExtractorClient

        with patch(
            "backend.services.memory_extractor_client.urllib.request.urlopen",
            return_value=_FakeResponse(b'{"choices":[{"message":{"content":"{}"}}]}'),
        ) as urlopen:
            client = MemoryExtractorClient(self._settings(memory_extractor_api_key="secret-key"))

            client.infer_json("system", "user")

        request = urlopen.call_args.args[0]
        self.assertEqual(request.get_header("Authorization"), "Bearer secret-key")

    def test_omits_authorization_header_when_api_key_blank(self):
        from backend.services.memory_extractor_client import MemoryExtractorClient

        with patch(
            "backend.services.memory_extractor_client.urllib.request.urlopen",
            return_value=_FakeResponse(b'{"choices":[{"message":{"content":"{}"}}]}'),
        ) as urlopen:
            client = MemoryExtractorClient(self._settings(memory_extractor_api_key="   "))

            client.infer_json("system", "user")

        request = urlopen.call_args.args[0]
        self.assertIsNone(request.get_header("Authorization"))

    def test_normalizes_trailing_slash_in_base_url(self):
        from backend.services.memory_extractor_client import MemoryExtractorClient

        with patch(
            "backend.services.memory_extractor_client.urllib.request.urlopen",
            return_value=_FakeResponse(b'{"choices":[{"message":{"content":"{}"}}]}'),
        ) as urlopen:
            client = MemoryExtractorClient(self._settings(memory_extractor_base_url="http://host/v1/"))

            client.infer_json("sys", "user")

        request = urlopen.call_args.args[0]
        self.assertEqual(request.full_url, "http://host/v1/chat/completions")

    def test_validates_required_settings(self):
        from backend.services.memory_extractor_client import MemoryExtractorClient

        with self.assertRaisesRegex(ValueError, "memory_extractor_base_url must not be blank"):
            MemoryExtractorClient(self._settings(memory_extractor_base_url=""))

        with self.assertRaisesRegex(ValueError, "memory_extractor_model must not be blank"):
            MemoryExtractorClient(self._settings(memory_extractor_model=" "))

        with self.assertRaisesRegex(ValueError, "memory_extractor_max_tokens must be > 0"):
            MemoryExtractorClient(self._settings(memory_extractor_max_tokens=0))

        with self.assertRaisesRegex(ValueError, "memory_extractor_timeout_seconds must be > 0"):
            MemoryExtractorClient(self._settings(memory_extractor_timeout_seconds=0))

    def test_raises_value_error_for_missing_response_envelope_with_url_context(self):
        from backend.services.memory_extractor_client import MemoryExtractorClient

        with patch(
            "backend.services.memory_extractor_client.urllib.request.urlopen",
            return_value=_FakeResponse(b"{}"),
        ):
            client = MemoryExtractorClient(self._settings())
            with self.assertRaisesRegex(ValueError, "choices\\[0\\]\\.message\\.content"):
                client.infer_json("system", "user")

    def test_returns_non_json_assistant_content_as_text(self):
        from backend.services.memory_extractor_client import MemoryExtractorClient

        with patch(
            "backend.services.memory_extractor_client.urllib.request.urlopen",
            return_value=_FakeResponse(b'{"choices":[{"message":{"content":"not-json"}}]}'),
        ):
            client = MemoryExtractorClient(self._settings())
            self.assertEqual(client.infer_json("system", "user"), "not-json")

    def test_wraps_http_error_with_status_and_body_snippet(self):
        from backend.services.memory_extractor_client import MemoryExtractorClient

        http_error = urllib.error.HTTPError(
            "http://127.0.0.1:11434/v1/chat/completions",
            503,
            "Service Unavailable",
            hdrs=None,
            fp=io.BytesIO(b"temporary upstream failure"),
        )
        with patch(
            "backend.services.memory_extractor_client.urllib.request.urlopen",
            side_effect=http_error,
        ):
            client = MemoryExtractorClient(self._settings())
            with self.assertRaisesRegex(
                ValueError,
                "chat/completions.*HTTP 503.*temporary upstream failure",
            ):
                client.infer_json("system", "user")

    def test_wraps_url_error_with_url_context(self):
        from backend.services.memory_extractor_client import MemoryExtractorClient

        with patch(
            "backend.services.memory_extractor_client.urllib.request.urlopen",
            side_effect=urllib.error.URLError("connection refused"),
        ):
            client = MemoryExtractorClient(self._settings())
            with self.assertRaisesRegex(
                ValueError,
                "request failed.*chat/completions.*connection refused",
            ):
                client.infer_json("system", "user")


class DocsCleanupTests(unittest.TestCase):
    def test_env_example_documents_ollama_memory_extractor(self):
        env_example = Path(__file__).resolve().parents[1] / ".env.example"
        content = env_example.read_text(encoding="utf-8")

        self.assertIn("Ollama", content)
        self.assertIn("OpenAI-compatible", content)
        self.assertIn("MEMORY_EXTRACTOR_MODE=ollama", content)
        self.assertIn("MEMORY_EXTRACTOR_BASE_URL=http://127.0.0.1:11434/v1", content)
        self.assertIn("MEMORY_EXTRACTOR_MODEL=", content)

    def test_env_example_no_longer_mentions_local_model_path_setting(self):
        env_example = Path(__file__).resolve().parents[1] / ".env.example"
        content = env_example.read_text(encoding="utf-8")

        self.assertNotIn("MEMORY_EXTRACTOR_MODEL_PATH", content)


if __name__ == "__main__":
    unittest.main()
