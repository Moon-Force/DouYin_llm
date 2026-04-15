import asyncio
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock
from unittest.mock import MagicMock

import backend.app as app_module
from backend.schemas.live import LiveEvent


def make_event():
    return LiveEvent(
        event_id="evt-1",
        room_id="room-1",
        source_room_id="source-room-1",
        session_id="session-1",
        platform="douyin",
        event_type="comment",
        method="WebcastChatMessage",
        livename="test-room",
        ts=1234567890,
        user={"id": "user-1", "nickname": "A-Ming"},
        content="I like ramen",
        metadata={},
        raw={},
    )


class CommentProcessingStatusTests(unittest.TestCase):
    def test_process_event_attaches_processing_status_to_streamed_comment(self):
        event = make_event()
        suggestion = SimpleNamespace(
            suggestion_id="sug-1",
            model_dump=lambda: {"suggestion_id": "sug-1", "room_id": "room-1"},
        )
        memory = SimpleNamespace(memory_id="mem-1")

        original_session_memory = app_module.session_memory
        original_long_term_store = app_module.long_term_store
        original_agent = app_module.agent
        original_memory_extractor = app_module.memory_extractor
        original_vector_memory = app_module.vector_memory
        original_broker = app_module.broker
        try:
            app_module.session_memory = MagicMock()
            app_module.session_memory.recent_events.return_value = [event]
            app_module.session_memory.stats.return_value = SimpleNamespace(
                model_dump=lambda: {"room_id": "room-1", "total_events": 1}
            )

            app_module.long_term_store = MagicMock()
            app_module.long_term_store.save_viewer_memory.return_value = memory

            app_module.agent = MagicMock()
            app_module.agent.maybe_generate.return_value = suggestion
            app_module.agent.consume_last_generation_metadata.return_value = {
                "memory_recall_attempted": True,
                "memory_recalled": True,
                "recalled_memory_ids": ["mem-9"],
            }
            app_module.agent.current_status.return_value = {
                "mode": "qwen",
                "model": "qwen3.5-flash",
                "backend": "https://example.test/v1",
                "last_result": "ok",
                "last_error": "",
                "updated_at": 1,
            }

            app_module.memory_extractor = MagicMock()
            app_module.memory_extractor.extract.return_value = [
                {
                    "memory_text": "likes ramen",
                    "memory_type": "preference",
                    "confidence": 0.91,
                }
            ]

            app_module.vector_memory = MagicMock()
            app_module.broker = MagicMock()
            app_module.broker.publish = AsyncMock()

            asyncio.run(app_module.process_event(event))

            published_event = app_module.broker.publish.await_args_list[0].args[0]
            status = published_event["data"]["processing_status"]

            self.assertTrue(status["received"])
            self.assertTrue(status["persisted"])
            self.assertTrue(status["memory_extraction_attempted"])
            self.assertTrue(status["memory_saved"])
            self.assertEqual(status["saved_memory_ids"], ["mem-1"])
            self.assertTrue(status["memory_recall_attempted"])
            self.assertTrue(status["memory_recalled"])
            self.assertEqual(status["recalled_memory_ids"], ["mem-9"])
            self.assertTrue(status["suggestion_generated"])
            self.assertEqual(status["suggestion_id"], "sug-1")
        finally:
            app_module.session_memory = original_session_memory
            app_module.long_term_store = original_long_term_store
            app_module.agent = original_agent
            app_module.memory_extractor = original_memory_extractor
            app_module.vector_memory = original_vector_memory
            app_module.broker = original_broker

    def test_health_reports_embedding_strict_and_semantic_backend_status(self):
        original_settings = app_module.settings
        original_long_term_store = app_module.long_term_store
        original_vector_memory = app_module.vector_memory
        try:
            app_module.settings = SimpleNamespace(room_id="room-1", embedding_strict=True)
            app_module.long_term_store = MagicMock()
            app_module.long_term_store.get_active_session.return_value = {"room_id": "room-1"}
            app_module.vector_memory = MagicMock()
            app_module.vector_memory.semantic_backend_ready.return_value = False
            app_module.vector_memory.semantic_backend_reason.return_value = "Chroma is unavailable"

            payload = asyncio.run(app_module.health())

            self.assertEqual(payload["status"], "ok")
            self.assertTrue(payload["embedding_strict"])
            self.assertFalse(payload["semantic_backend_ready"])
            self.assertEqual(payload["semantic_backend_reason"], "Chroma is unavailable")
        finally:
            app_module.settings = original_settings
            app_module.long_term_store = original_long_term_store
            app_module.vector_memory = original_vector_memory


if __name__ == "__main__":
    unittest.main()
