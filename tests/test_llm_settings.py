import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from backend.memory.long_term import LongTermStore
from backend.services.agent import LivePromptAgent


def make_settings():
    return SimpleNamespace(
        llm_mode="qwen",
        llm_temperature=0.4,
        llm_timeout_seconds=6,
        llm_max_tokens=120,
        llm_api_key="test-key",
        llm_model="qwen3.5-flash-2026-02-23",
        embedding_model="bge-m3:latest",
        memory_extractor_model="qwen3.5:0.8b",
        resolved_llm_base_url=lambda: "https://example.test/v1",
        resolved_llm_model=lambda: "qwen3.5-flash-2026-02-23",
    )


class LlmSettingsTests(unittest.TestCase):
    def test_long_term_store_persists_llm_settings(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = LongTermStore(Path(tmpdir) / "test.db")

            store.save_llm_settings(
                "qwen-max",
                "custom system prompt",
                "bge-m3:latest",
                "qwen3.5:0.8b",
            )
            payload = store.get_llm_settings(
                "default-model",
                "default prompt",
                "text-embedding-3-small",
                "qwen2.5:latest",
                ["bge-m3:latest", "nomic-embed-text:latest"],
                ["qwen3.5:0.8b", "llama3.2:latest"],
            )
            store.close()

        self.assertEqual(payload["model"], "qwen-max")
        self.assertEqual(payload["system_prompt"], "custom system prompt")
        self.assertEqual(payload["default_model"], "default-model")
        self.assertEqual(payload["default_system_prompt"], "default prompt")
        self.assertEqual(payload["embedding_model"], "bge-m3:latest")
        self.assertEqual(payload["memory_extractor_model"], "qwen3.5:0.8b")
        self.assertEqual(payload["default_embedding_model"], "text-embedding-3-small")
        self.assertEqual(payload["default_memory_extractor_model"], "qwen2.5:latest")
        self.assertEqual(payload["embedding_model_options"], ["bge-m3:latest", "nomic-embed-text:latest"])
        self.assertEqual(payload["memory_extractor_model_options"], ["qwen3.5:0.8b", "llama3.2:latest"])

    def test_blank_prompt_falls_back_to_default_prompt(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = LongTermStore(Path(tmpdir) / "test.db")
            store.save_llm_settings("qwen-max", "", "bge-m3:latest", "qwen3.5:0.8b")
            payload = store.get_llm_settings(
                "default-model",
                "default prompt",
                "text-embedding-3-small",
                "qwen2.5:latest",
            )
            store.close()

        self.assertEqual(payload["model"], "qwen-max")
        self.assertEqual(payload["system_prompt"], "default prompt")
        self.assertEqual(payload["embedding_model"], "bge-m3:latest")
        self.assertEqual(payload["memory_extractor_model"], "qwen3.5:0.8b")

    def test_agent_reads_runtime_overrides(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = LongTermStore(Path(tmpdir) / "test.db")
            store.save_llm_settings("qwen-max", "override prompt", "bge-m3:latest", "qwen3.5:0.8b")
            agent = LivePromptAgent(make_settings(), vector_memory=object(), long_term_store=store)

            current = agent.current_status()
            settings_payload = agent.current_llm_settings()
            prompt = agent.current_system_prompt()
            store.close()

        self.assertEqual(current["model"], "qwen-max")
        self.assertEqual(prompt, "override prompt")
        self.assertEqual(settings_payload["embedding_model"], "bge-m3:latest")
        self.assertEqual(settings_payload["memory_extractor_model"], "qwen3.5:0.8b")


if __name__ == "__main__":
    unittest.main()
