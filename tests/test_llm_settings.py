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
        resolved_llm_base_url=lambda: "https://example.test/v1",
        resolved_llm_model=lambda: "qwen3.5-flash-2026-02-23",
    )


class LlmSettingsTests(unittest.TestCase):
    def test_long_term_store_persists_llm_settings(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = LongTermStore(Path(tmpdir) / "test.db")

            store.save_llm_settings("qwen-max", "custom system prompt")
            payload = store.get_llm_settings("default-model", "default prompt")
            store.close()

        self.assertEqual(payload["model"], "qwen-max")
        self.assertEqual(payload["system_prompt"], "custom system prompt")
        self.assertEqual(payload["default_model"], "default-model")
        self.assertEqual(payload["default_system_prompt"], "default prompt")

    def test_blank_prompt_falls_back_to_default_prompt(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = LongTermStore(Path(tmpdir) / "test.db")
            store.save_llm_settings("qwen-max", "")
            payload = store.get_llm_settings("default-model", "default prompt")
            store.close()

        self.assertEqual(payload["model"], "qwen-max")
        self.assertEqual(payload["system_prompt"], "default prompt")

    def test_agent_reads_runtime_overrides(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = LongTermStore(Path(tmpdir) / "test.db")
            store.save_llm_settings("qwen-max", "override prompt")
            agent = LivePromptAgent(make_settings(), vector_memory=object(), long_term_store=store)

            current = agent.current_status()
            prompt = agent.current_system_prompt()
            store.close()

        self.assertEqual(current["model"], "qwen-max")
        self.assertEqual(prompt, "override prompt")


if __name__ == "__main__":
    unittest.main()
