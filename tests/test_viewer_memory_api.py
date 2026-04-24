import asyncio
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock
from unittest.mock import patch
from unittest.mock import ANY

import backend.app as app_module


class ViewerMemoryApiTests(unittest.TestCase):
    def setUp(self):
        self.original_store = app_module.long_term_store
        self.original_vector = app_module.vector_memory
        app_module.long_term_store = MagicMock()
        app_module.vector_memory = MagicMock()

    def tearDown(self):
        app_module.long_term_store = self.original_store
        app_module.vector_memory = self.original_vector

    def test_create_viewer_memory_uses_manual_defaults_and_syncs_vector_store(self):
        memory = SimpleNamespace(memory_id="mem-1", status="active")
        app_module.long_term_store.save_viewer_memory.return_value = memory

        payload = app_module.ViewerMemoryUpsertRequest(
            room_id="room-1",
            viewer_id="viewer-1",
            memory_text="喜欢豚骨拉面",
            memory_type="preference",
            is_pinned=True,
            correction_reason="主播补充",
        )

        result = asyncio.run(app_module.create_viewer_memory(payload))

        self.assertIs(result, memory)
        app_module.long_term_store.save_viewer_memory.assert_called_once_with(
            "room-1",
            "viewer-1",
            "喜欢豚骨拉面",
            memory_recall_text=ANY,
            source_event_id="",
            memory_type="preference",
            confidence=1.0,
            source_kind="manual",
            status="active",
            is_pinned=True,
            correction_reason="主播补充",
            corrected_by="主播",
            operation="created",
        )
        app_module.vector_memory.sync_memory.assert_called_once_with(memory)

    def test_invalidate_delete_and_log_routes_call_store_methods(self):
        invalid = SimpleNamespace(memory_id="mem-1", status="invalid")
        deleted = SimpleNamespace(memory_id="mem-1", status="deleted")
        app_module.long_term_store.invalidate_viewer_memory.return_value = invalid
        app_module.long_term_store.delete_viewer_memory.return_value = deleted
        app_module.long_term_store.list_viewer_memory_logs.return_value = [{"operation": "created"}]

        status_payload = app_module.ViewerMemoryStatusRequest(reason="信息过期")

        invalidate_result = asyncio.run(app_module.invalidate_viewer_memory("mem-1", status_payload))
        delete_result = asyncio.run(app_module.delete_viewer_memory("mem-1", status_payload))
        logs_result = asyncio.run(app_module.viewer_memory_logs("mem-1", limit=10))

        self.assertIs(invalidate_result, invalid)
        self.assertIs(delete_result, deleted)
        self.assertEqual(logs_result, {"items": [{"operation": "created"}]})
        app_module.vector_memory.sync_memory.assert_called_once_with(invalid)
        app_module.vector_memory.remove_memory.assert_called_once_with("mem-1")

    def test_get_llm_settings_returns_runtime_options(self):
        original_agent = app_module.agent
        original_ensure_runtime = app_module.ensure_runtime
        try:
            app_module.ensure_runtime = MagicMock()
            app_module.agent = MagicMock()
            app_module.agent.current_llm_settings.return_value = {
                "model": "qwen-main",
                "system_prompt": "prompt",
                "default_model": "qwen-main",
                "default_system_prompt": "prompt",
                "embedding_model": "bge-m3:latest",
                "memory_extractor_model": "qwen3.5:0.8b",
                "default_embedding_model": "bge-m3:latest",
                "default_memory_extractor_model": "qwen3.5:0.8b",
                "embedding_model_options": ["bge-m3:latest", "nomic-embed-text:latest"],
                "memory_extractor_model_options": ["qwen3.5:0.8b", "llama3.2:latest"],
            }

            with patch.object(
                app_module,
                "_list_ollama_models",
                return_value=["bge-m3:latest", "nomic-embed-text:latest"],
            ):
                result = asyncio.run(app_module.get_llm_settings())
        finally:
            app_module.agent = original_agent
            app_module.ensure_runtime = original_ensure_runtime

        self.assertEqual(result["embedding_model"], "bge-m3:latest")
        self.assertEqual(result["memory_extractor_model"], "qwen3.5:0.8b")
        self.assertEqual(result["embedding_model_options"], ["bge-m3:latest", "nomic-embed-text:latest"])
        self.assertEqual(
            result["memory_extractor_model_options"],
            ["qwen3.5:0.8b", "bge-m3:latest", "nomic-embed-text:latest"],
        )

    def test_save_llm_settings_persists_embedding_and_extractor_models(self):
        original_ensure_runtime = app_module.ensure_runtime
        try:
            app_module.ensure_runtime = MagicMock()
            app_module.long_term_store.save_llm_settings.return_value = {
                "model": "qwen-main",
                "system_prompt": "prompt",
                "default_model": "qwen-main",
                "default_system_prompt": "prompt",
                "embedding_model": "bge-m3:latest",
                "memory_extractor_model": "qwen3.5:0.8b",
                "default_embedding_model": "bge-m3:latest",
                "default_memory_extractor_model": "qwen3.5:0.8b",
                "embedding_model_options": ["bge-m3:latest"],
                "memory_extractor_model_options": ["qwen3.5:0.8b"],
            }

            payload = app_module.LlmSettingsUpdateRequest(
                model="qwen-main",
                system_prompt="prompt",
                embedding_model="bge-m3:latest",
                memory_extractor_model="qwen3.5:0.8b",
            )

            result = asyncio.run(app_module.save_llm_settings(payload))
        finally:
            app_module.ensure_runtime = original_ensure_runtime

        self.assertEqual(result["embedding_model"], "bge-m3:latest")
        self.assertEqual(result["memory_extractor_model"], "qwen3.5:0.8b")
        app_module.long_term_store.save_llm_settings.assert_called_with(
            "qwen-main",
            "prompt",
            "bge-m3:latest",
            "qwen3.5:0.8b",
        )


if __name__ == "__main__":
    unittest.main()
