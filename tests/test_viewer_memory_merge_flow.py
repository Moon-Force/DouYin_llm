import asyncio
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock
from unittest.mock import MagicMock

import backend.app as app_module
from backend.schemas.live import LiveEvent
from backend.services.memory_merge_service import MemoryMergeDecision
from backend.services.memory_merge_service import ViewerMemoryMergeService


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


class ViewerMemoryMergeFlowTests(unittest.TestCase):
    def test_process_event_merges_duplicate_memory_before_persisting(self):
        event = make_event()
        existing = SimpleNamespace(memory_id="mem-1", memory_text="likes ramen", memory_type="preference")

        original_session_memory = app_module.session_memory
        original_long_term_store = app_module.long_term_store
        original_agent = app_module.agent
        original_memory_extractor = app_module.memory_extractor
        original_vector_memory = app_module.vector_memory
        original_broker = app_module.broker
        original_memory_merge_service = getattr(app_module, "memory_merge_service", None)
        try:
            app_module.session_memory = MagicMock()
            app_module.session_memory.recent_events.return_value = [event]
            app_module.session_memory.stats.return_value = SimpleNamespace(
                model_dump=lambda: {"room_id": "room-1", "total_events": 1}
            )

            app_module.long_term_store = MagicMock()
            app_module.long_term_store.list_viewer_memories.return_value = [
                {
                    "memory_id": "mem-1",
                    "memory_text": "likes ramen",
                    "memory_type": "preference",
                    "status": "active",
                }
            ]
            app_module.long_term_store.merge_viewer_memory_evidence.return_value = existing

            app_module.agent = MagicMock()
            app_module.agent.maybe_generate.return_value = None
            app_module.agent.consume_last_generation_metadata.return_value = {
                "memory_recall_attempted": False,
                "memory_recalled": False,
                "recalled_memory_ids": [],
                "suggestion_status": "skipped",
                "suggestion_block_reason": "",
                "suggestion_block_detail": "",
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
                    "memory_text_raw": "I really like ramen",
                    "memory_text_canonical": "likes ramen",
                    "memory_type": "preference",
                    "confidence": 0.91,
                }
            ]
            app_module.memory_extractor.consume_last_extraction_metadata.return_value = {
                "memory_prefiltered": False,
                "memory_llm_attempted": True,
                "memory_refined": True,
                "fallback_used": False,
            }

            app_module.vector_memory = MagicMock()
            app_module.vector_memory.similar_memories.return_value = [
                {"memory_id": "mem-1", "memory_text": "likes ramen", "score": 0.94, "metadata": {}}
            ]

            app_module.memory_merge_service = ViewerMemoryMergeService()

            app_module.broker = MagicMock()
            app_module.broker.publish = AsyncMock()

            asyncio.run(app_module.process_event(event))

            app_module.long_term_store.merge_viewer_memory_evidence.assert_called_once()
            app_module.long_term_store.save_viewer_memory.assert_not_called()
        finally:
            app_module.session_memory = original_session_memory
            app_module.long_term_store = original_long_term_store
            app_module.agent = original_agent
            app_module.memory_extractor = original_memory_extractor
            app_module.vector_memory = original_vector_memory
            app_module.broker = original_broker
            app_module.memory_merge_service = original_memory_merge_service

    def test_process_event_supersedes_conflicting_memory(self):
        event = make_event()
        old_memory = SimpleNamespace(memory_id="mem-old", status="invalid")
        new_memory = SimpleNamespace(memory_id="mem-new", status="active")

        original_session_memory = app_module.session_memory
        original_long_term_store = app_module.long_term_store
        original_agent = app_module.agent
        original_memory_extractor = app_module.memory_extractor
        original_vector_memory = app_module.vector_memory
        original_broker = app_module.broker
        original_memory_merge_service = getattr(app_module, "memory_merge_service", None)
        try:
            app_module.session_memory = MagicMock()
            app_module.session_memory.recent_events.return_value = [event]
            app_module.session_memory.stats.return_value = SimpleNamespace(
                model_dump=lambda: {"room_id": "room-1", "total_events": 1}
            )

            app_module.long_term_store = MagicMock()
            app_module.long_term_store.list_viewer_memories.return_value = [
                {
                    "memory_id": "mem-old",
                    "memory_text": "likes spicy food",
                    "memory_type": "preference",
                    "status": "active",
                }
            ]
            app_module.long_term_store.supersede_viewer_memory.return_value = (old_memory, new_memory)

            app_module.agent = MagicMock()
            app_module.agent.maybe_generate.return_value = None
            app_module.agent.consume_last_generation_metadata.return_value = {
                "memory_recall_attempted": False,
                "memory_recalled": False,
                "recalled_memory_ids": [],
                "suggestion_status": "skipped",
                "suggestion_block_reason": "",
                "suggestion_block_detail": "",
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
                    "memory_text": "cannot eat spicy food",
                    "memory_text_raw": "I usually can't eat spicy food",
                    "memory_text_canonical": "cannot eat spicy food",
                    "memory_type": "preference",
                    "confidence": 0.91,
                }
            ]
            app_module.memory_extractor.consume_last_extraction_metadata.return_value = {
                "memory_prefiltered": False,
                "memory_llm_attempted": True,
                "memory_refined": True,
                "fallback_used": False,
            }

            app_module.vector_memory = MagicMock()
            app_module.vector_memory.similar_memories.return_value = [
                {"memory_id": "mem-old", "memory_text": "likes spicy food", "score": 0.84, "metadata": {}}
            ]

            app_module.memory_merge_service = MagicMock()
            app_module.memory_merge_service.decide.return_value = MemoryMergeDecision(
                action="supersede",
                target_memory_id="mem-old",
                reason="conflicting_direction",
            )

            app_module.broker = MagicMock()
            app_module.broker.publish = AsyncMock()

            asyncio.run(app_module.process_event(event))

            app_module.long_term_store.supersede_viewer_memory.assert_called_once()
            self.assertEqual(app_module.vector_memory.sync_memory.call_count, 2)
        finally:
            app_module.session_memory = original_session_memory
            app_module.long_term_store = original_long_term_store
            app_module.agent = original_agent
            app_module.memory_extractor = original_memory_extractor
            app_module.vector_memory = original_vector_memory
            app_module.broker = original_broker
            app_module.memory_merge_service = original_memory_merge_service


if __name__ == "__main__":
    unittest.main()
