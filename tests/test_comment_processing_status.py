import asyncio
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from unittest.mock import patch

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
    def test_ensure_runtime_wires_ollama_memory_extractor_when_enabled(self):
        original_settings = app_module.settings
        original_broker = app_module.broker
        original_session_memory = app_module.session_memory
        original_long_term_store = app_module.long_term_store
        original_embedding_service = app_module.embedding_service
        original_vector_memory = app_module.vector_memory
        original_agent = app_module.agent
        original_memory_extractor = app_module.memory_extractor
        original_collector = app_module.collector
        try:
            app_module.settings = SimpleNamespace(
                ensure_dirs=MagicMock(),
                redis_url="redis://localhost:6379/0",
                session_ttl_seconds=3600,
                database_path="data/live_prompter.db",
                chroma_dir="data/chroma",
                memory_extractor_enabled=True,
                memory_extractor_mode="ollama",
                memory_extractor_base_url="http://127.0.0.1:11434/v1",
                memory_extractor_model="qwen2.5:3b",
                memory_extractor_api_key="",
                memory_extractor_timeout_seconds=30.0,
                memory_extractor_max_tokens=512,
            )
            app_module.broker = None
            app_module.session_memory = None
            app_module.long_term_store = None
            app_module.embedding_service = None
            app_module.vector_memory = None
            app_module.agent = None
            app_module.memory_extractor = None
            app_module.collector = None

            with patch("backend.app._should_force_memory_rebuild", return_value=False), patch(
                "backend.app.EventBroker", return_value=MagicMock()
            ), patch(
                "backend.app.SessionMemory", return_value=MagicMock()
            ), patch(
                "backend.app.LongTermStore"
            ) as long_term_store_cls, patch(
                "backend.app.EmbeddingService", return_value=MagicMock()
            ), patch(
                "backend.app.VectorMemory", return_value=MagicMock()
            ), patch(
                "backend.app.LivePromptAgent", return_value=MagicMock()
            ), patch(
                "backend.app.DouyinCollector", return_value=MagicMock()
            ), patch(
                "backend.app.MemoryExtractorClient"
            ) as memory_client_cls, patch(
                "backend.app.LLMBackedViewerMemoryExtractor"
            ) as llm_extractor_cls, patch(
                "backend.app.ViewerMemoryExtractor", return_value=MagicMock()
            ) as composite_cls:
                long_term_store_instance = MagicMock()
                long_term_store_instance.list_all_viewer_memories.return_value = []
                long_term_store_cls.return_value = long_term_store_instance

                app_module.ensure_runtime()

                memory_client_cls.assert_called_once_with(app_module.settings)
                llm_extractor_cls.assert_called_once_with(app_module.settings, memory_client_cls.return_value)
                composite_cls.assert_called_once_with(
                    settings=app_module.settings,
                    llm_extractor=llm_extractor_cls.return_value,
                )
        finally:
            app_module.settings = original_settings
            app_module.broker = original_broker
            app_module.session_memory = original_session_memory
            app_module.long_term_store = original_long_term_store
            app_module.embedding_service = original_embedding_service
            app_module.vector_memory = original_vector_memory
            app_module.agent = original_agent
            app_module.memory_extractor = original_memory_extractor
            app_module.collector = original_collector

    def test_ensure_runtime_uses_rule_only_memory_extractor_when_disabled(self):
        original_settings = app_module.settings
        original_broker = app_module.broker
        original_session_memory = app_module.session_memory
        original_long_term_store = app_module.long_term_store
        original_embedding_service = app_module.embedding_service
        original_vector_memory = app_module.vector_memory
        original_agent = app_module.agent
        original_memory_extractor = app_module.memory_extractor
        original_collector = app_module.collector
        try:
            app_module.settings = SimpleNamespace(
                ensure_dirs=MagicMock(),
                redis_url="redis://localhost:6379/0",
                session_ttl_seconds=3600,
                database_path="data/live_prompter.db",
                chroma_dir="data/chroma",
                memory_extractor_enabled=False,
            )
            app_module.broker = None
            app_module.session_memory = None
            app_module.long_term_store = None
            app_module.embedding_service = None
            app_module.vector_memory = None
            app_module.agent = None
            app_module.memory_extractor = None
            app_module.collector = None

            with patch("backend.app._should_force_memory_rebuild", return_value=False), patch(
                "backend.app.EventBroker", return_value=MagicMock()
            ), patch(
                "backend.app.SessionMemory", return_value=MagicMock()
            ), patch(
                "backend.app.LongTermStore"
            ) as long_term_store_cls, patch(
                "backend.app.EmbeddingService", return_value=MagicMock()
            ), patch(
                "backend.app.VectorMemory", return_value=MagicMock()
            ), patch(
                "backend.app.LivePromptAgent", return_value=MagicMock()
            ), patch(
                "backend.app.DouyinCollector", return_value=MagicMock()
            ), patch(
                "backend.app.MemoryExtractorClient"
            ) as memory_client_cls, patch(
                "backend.app.LLMBackedViewerMemoryExtractor"
            ) as llm_extractor_cls, patch(
                "backend.app.ViewerMemoryExtractor", return_value=MagicMock()
            ) as composite_cls:
                long_term_store_instance = MagicMock()
                long_term_store_instance.list_all_viewer_memories.return_value = []
                long_term_store_cls.return_value = long_term_store_instance

                app_module.ensure_runtime()

                memory_client_cls.assert_not_called()
                llm_extractor_cls.assert_not_called()
                composite_cls.assert_called_once_with(settings=app_module.settings)
        finally:
            app_module.settings = original_settings
            app_module.broker = original_broker
            app_module.session_memory = original_session_memory
            app_module.long_term_store = original_long_term_store
            app_module.embedding_service = original_embedding_service
            app_module.vector_memory = original_vector_memory
            app_module.agent = original_agent
            app_module.memory_extractor = original_memory_extractor
            app_module.collector = original_collector

    def test_ensure_runtime_falls_back_to_rule_only_when_ollama_client_init_fails(self):
        original_settings = app_module.settings
        original_broker = app_module.broker
        original_session_memory = app_module.session_memory
        original_long_term_store = app_module.long_term_store
        original_embedding_service = app_module.embedding_service
        original_vector_memory = app_module.vector_memory
        original_agent = app_module.agent
        original_memory_extractor = app_module.memory_extractor
        original_collector = app_module.collector
        try:
            app_module.settings = SimpleNamespace(
                ensure_dirs=MagicMock(),
                redis_url="redis://localhost:6379/0",
                session_ttl_seconds=3600,
                database_path="data/live_prompter.db",
                chroma_dir="data/chroma",
                memory_extractor_enabled=True,
                memory_extractor_mode="ollama",
            )
            app_module.broker = None
            app_module.session_memory = None
            app_module.long_term_store = None
            app_module.embedding_service = None
            app_module.vector_memory = None
            app_module.agent = None
            app_module.memory_extractor = None
            app_module.collector = None

            with patch("backend.app._should_force_memory_rebuild", return_value=False), patch(
                "backend.app.EventBroker", return_value=MagicMock()
            ), patch(
                "backend.app.SessionMemory", return_value=MagicMock()
            ), patch(
                "backend.app.LongTermStore"
            ) as long_term_store_cls, patch(
                "backend.app.EmbeddingService", return_value=MagicMock()
            ), patch(
                "backend.app.VectorMemory", return_value=MagicMock()
            ), patch(
                "backend.app.LivePromptAgent", return_value=MagicMock()
            ), patch(
                "backend.app.DouyinCollector", return_value=MagicMock()
            ), patch(
                "backend.app.MemoryExtractorClient", side_effect=RuntimeError("bad config")
            ) as memory_client_cls, patch(
                "backend.app.LLMBackedViewerMemoryExtractor"
            ) as llm_extractor_cls, patch(
                "backend.app.ViewerMemoryExtractor", return_value=MagicMock()
            ) as composite_cls, patch(
                "backend.app.logging.exception"
            ) as logging_exception:
                long_term_store_instance = MagicMock()
                long_term_store_instance.list_all_viewer_memories.return_value = []
                long_term_store_cls.return_value = long_term_store_instance

                app_module.ensure_runtime()

                memory_client_cls.assert_called_once_with(app_module.settings)
                llm_extractor_cls.assert_not_called()
                composite_cls.assert_called_once_with(settings=app_module.settings)
                logging_exception.assert_called_once()
        finally:
            app_module.settings = original_settings
            app_module.broker = original_broker
            app_module.session_memory = original_session_memory
            app_module.long_term_store = original_long_term_store
            app_module.embedding_service = original_embedding_service
            app_module.vector_memory = original_vector_memory
            app_module.agent = original_agent
            app_module.memory_extractor = original_memory_extractor
            app_module.collector = original_collector

    def test_ensure_runtime_falls_back_to_rule_only_when_mode_is_not_ollama(self):
        original_settings = app_module.settings
        original_broker = app_module.broker
        original_session_memory = app_module.session_memory
        original_long_term_store = app_module.long_term_store
        original_embedding_service = app_module.embedding_service
        original_vector_memory = app_module.vector_memory
        original_agent = app_module.agent
        original_memory_extractor = app_module.memory_extractor
        original_collector = app_module.collector
        try:
            app_module.settings = SimpleNamespace(
                ensure_dirs=MagicMock(),
                redis_url="redis://localhost:6379/0",
                session_ttl_seconds=3600,
                database_path="data/live_prompter.db",
                chroma_dir="data/chroma",
                memory_extractor_enabled=True,
                memory_extractor_mode="rule",
            )
            app_module.broker = None
            app_module.session_memory = None
            app_module.long_term_store = None
            app_module.embedding_service = None
            app_module.vector_memory = None
            app_module.agent = None
            app_module.memory_extractor = None
            app_module.collector = None

            with patch("backend.app._should_force_memory_rebuild", return_value=False), patch(
                "backend.app.EventBroker", return_value=MagicMock()
            ), patch(
                "backend.app.SessionMemory", return_value=MagicMock()
            ), patch(
                "backend.app.LongTermStore"
            ) as long_term_store_cls, patch(
                "backend.app.EmbeddingService", return_value=MagicMock()
            ), patch(
                "backend.app.VectorMemory", return_value=MagicMock()
            ), patch(
                "backend.app.LivePromptAgent", return_value=MagicMock()
            ), patch(
                "backend.app.DouyinCollector", return_value=MagicMock()
            ), patch(
                "backend.app.MemoryExtractorClient"
            ) as memory_client_cls, patch(
                "backend.app.LLMBackedViewerMemoryExtractor"
            ) as llm_extractor_cls, patch(
                "backend.app.ViewerMemoryExtractor", return_value=MagicMock()
            ) as composite_cls, patch(
                "backend.app.logging.warning"
            ) as logging_warning:
                long_term_store_instance = MagicMock()
                long_term_store_instance.list_all_viewer_memories.return_value = []
                long_term_store_cls.return_value = long_term_store_instance

                app_module.ensure_runtime()

                memory_client_cls.assert_not_called()
                llm_extractor_cls.assert_not_called()
                composite_cls.assert_called_once_with(settings=app_module.settings)
                logging_warning.assert_called_once()
        finally:
            app_module.settings = original_settings
            app_module.broker = original_broker
            app_module.session_memory = original_session_memory
            app_module.long_term_store = original_long_term_store
            app_module.embedding_service = original_embedding_service
            app_module.vector_memory = original_vector_memory
            app_module.agent = original_agent
            app_module.memory_extractor = original_memory_extractor
            app_module.collector = original_collector

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
        original_memory_confidence_service = getattr(app_module, "memory_confidence_service", None)
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
                "recalled_memory_texts": ["likes ramen"],
                "suggestion_support_kind": "memory",
                "suggestion_status": "generated",
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
                    "memory_text_raw": "I like ramen",
                    "memory_text_canonical": "likes ramen",
                    "memory_type": "preference",
                    "polarity": "neutral",
                    "temporal_scope": "long_term",
                    "confidence": 0.91,
                    "extraction_source": "llm",
                }
            ]

            app_module.vector_memory = MagicMock()
            app_module.memory_confidence_service = MagicMock()
            app_module.memory_confidence_service.score_new_memory.return_value = {
                "stability_score": 0.45,
                "interaction_value_score": 0.35,
                "clarity_score": 0.75,
                "evidence_score": 0.35,
                "confidence": 0.445,
            }
            app_module.broker = MagicMock()
            app_module.broker.publish = AsyncMock()

            asyncio.run(app_module.process_event(event))

            app_module.long_term_store.save_viewer_memory.assert_called_with(
                room_id="room-1",
                viewer_id="id:user-1",
                memory_text="likes ramen",
                source_event_id="evt-1",
                memory_type="preference",
                polarity="neutral",
                temporal_scope="long_term",
                confidence=0.445,
                source_kind="llm",
                status="active",
                is_pinned=False,
                correction_reason="",
                corrected_by="system",
                operation="created",
                raw_memory_text="I like ramen",
                evidence_count=1,
                first_confirmed_at=1234567890,
                last_confirmed_at=1234567890,
                superseded_by="",
                merge_parent_id="",
                stability_score=0.45,
                interaction_value_score=0.35,
                clarity_score=0.75,
                evidence_score=0.35,
                lifecycle_kind="long_term",
                expires_at=0,
            )

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
            self.assertEqual(status["extracted_memory_texts"], ["likes ramen"])
            self.assertEqual(status["recalled_memory_texts"], ["likes ramen"])
            self.assertEqual(status["suggestion_support_kind"], "memory")
            self.assertTrue(status["suggestion_generated"])
            self.assertEqual(status["suggestion_id"], "sug-1")
            self.assertEqual(status["suggestion_status"], "generated")
            self.assertEqual(status["suggestion_block_reason"], "")
            self.assertEqual(status["suggestion_block_detail"], "")
        finally:
            app_module.session_memory = original_session_memory
            app_module.long_term_store = original_long_term_store
            app_module.agent = original_agent
            app_module.memory_extractor = original_memory_extractor
            app_module.vector_memory = original_vector_memory
            app_module.broker = original_broker
            app_module.memory_confidence_service = original_memory_confidence_service

    def test_process_event_persists_new_memory_with_confidence_subscores(self):
        event = make_event()
        memory = SimpleNamespace(memory_id="mem-1")

        original_session_memory = app_module.session_memory
        original_long_term_store = app_module.long_term_store
        original_agent = app_module.agent
        original_memory_extractor = app_module.memory_extractor
        original_vector_memory = app_module.vector_memory
        original_broker = app_module.broker
        original_memory_merge_service = getattr(app_module, "memory_merge_service", None)
        original_memory_confidence_service = getattr(app_module, "memory_confidence_service", None)
        try:
            app_module.session_memory = MagicMock()
            app_module.session_memory.recent_events.return_value = [event]
            app_module.session_memory.stats.return_value = SimpleNamespace(
                model_dump=lambda: {"room_id": "room-1", "total_events": 1}
            )

            app_module.long_term_store = MagicMock()
            app_module.long_term_store.list_viewer_memories.return_value = []
            app_module.long_term_store.save_viewer_memory.return_value = memory

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
                    "polarity": "positive",
                    "temporal_scope": "long_term",
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
            app_module.vector_memory.similar_memories.return_value = []

            app_module.memory_merge_service = MagicMock()
            app_module.memory_merge_service.decide.return_value = SimpleNamespace(
                action="create",
                target_memory_id="",
                reason="no_close_match",
            )

            app_module.memory_confidence_service = MagicMock()
            app_module.memory_confidence_service.score_new_memory.return_value = {
                "stability_score": 0.95,
                "interaction_value_score": 0.9,
                "clarity_score": 0.8,
                "evidence_score": 0.35,
                "confidence": 0.8225,
            }

            app_module.broker = MagicMock()
            app_module.broker.publish = AsyncMock()

            asyncio.run(app_module.process_event(event))

            app_module.long_term_store.save_viewer_memory.assert_called_with(
                room_id="room-1",
                viewer_id="id:user-1",
                memory_text="likes ramen",
                source_event_id="evt-1",
                memory_type="preference",
                polarity="positive",
                temporal_scope="long_term",
                confidence=0.8225,
                source_kind="auto",
                status="active",
                is_pinned=False,
                correction_reason="",
                corrected_by="system",
                operation="created",
                raw_memory_text="I really like ramen",
                evidence_count=1,
                first_confirmed_at=1234567890,
                last_confirmed_at=1234567890,
                superseded_by="",
                merge_parent_id="",
                stability_score=0.95,
                interaction_value_score=0.9,
                clarity_score=0.8,
                evidence_score=0.35,
                lifecycle_kind="long_term",
                expires_at=0,
            )
        finally:
            app_module.session_memory = original_session_memory
            app_module.long_term_store = original_long_term_store
            app_module.agent = original_agent
            app_module.memory_extractor = original_memory_extractor
            app_module.vector_memory = original_vector_memory
            app_module.broker = original_broker
            app_module.memory_merge_service = original_memory_merge_service
            app_module.memory_confidence_service = original_memory_confidence_service

    def test_process_event_sets_skipped_suggestion_status_when_no_suggestion_generated(self):
        event = make_event()
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
            app_module.agent.maybe_generate.return_value = None
            app_module.agent.consume_last_generation_metadata.return_value = {
                "memory_recall_attempted": False,
                "memory_recalled": False,
                "recalled_memory_ids": [],
                "suggestion_status": "skipped",
                "suggestion_block_reason": "no_generation_needed",
                "suggestion_block_detail": "评论内容为空，未生成建议。",
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
            app_module.memory_extractor.extract.return_value = []

            app_module.vector_memory = MagicMock()
            app_module.broker = MagicMock()
            app_module.broker.publish = AsyncMock()

            asyncio.run(app_module.process_event(event))

            published_event = app_module.broker.publish.await_args_list[0].args[0]
            status = published_event["data"]["processing_status"]

            self.assertFalse(status["suggestion_generated"])
            self.assertEqual(status["suggestion_status"], "skipped")
            self.assertEqual(status["suggestion_block_reason"], "no_generation_needed")
            self.assertEqual(status["suggestion_block_detail"], "评论内容为空，未生成建议。")
            self.assertEqual(status["suggestion_id"], "")
        finally:
            app_module.session_memory = original_session_memory
            app_module.long_term_store = original_long_term_store
            app_module.agent = original_agent
            app_module.memory_extractor = original_memory_extractor
            app_module.vector_memory = original_vector_memory
            app_module.broker = original_broker

    def test_process_event_preserves_metadata_suggestion_status_when_suggestion_exists(self):
        event = make_event()
        suggestion = SimpleNamespace(
            suggestion_id="sug-1",
            model_dump=lambda: {"suggestion_id": "sug-1", "room_id": "room-1"},
        )

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
            app_module.agent = MagicMock()
            app_module.agent.maybe_generate.return_value = suggestion
            app_module.agent.consume_last_generation_metadata.return_value = {
                "memory_recall_attempted": False,
                "memory_recalled": False,
                "recalled_memory_ids": [],
                "suggestion_status": "generated_with_fallback",
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
            app_module.memory_extractor.extract.return_value = []
            app_module.vector_memory = MagicMock()
            app_module.broker = MagicMock()
            app_module.broker.publish = AsyncMock()

            asyncio.run(app_module.process_event(event))

            published_event = app_module.broker.publish.await_args_list[0].args[0]
            status = published_event["data"]["processing_status"]
            self.assertTrue(status["suggestion_generated"])
            self.assertEqual(status["suggestion_id"], "sug-1")
            self.assertEqual(status["suggestion_status"], "generated_with_fallback")
        finally:
            app_module.session_memory = original_session_memory
            app_module.long_term_store = original_long_term_store
            app_module.agent = original_agent
            app_module.memory_extractor = original_memory_extractor
            app_module.vector_memory = original_vector_memory
            app_module.broker = original_broker

    def test_process_event_defaults_to_generated_when_suggestion_status_missing_or_empty(self):
        for metadata in ({}, {"suggestion_status": ""}):
            with self.subTest(metadata=metadata):
                event = make_event()
                suggestion = SimpleNamespace(
                    suggestion_id="sug-1",
                    model_dump=lambda: {"suggestion_id": "sug-1", "room_id": "room-1"},
                )

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
                    app_module.agent = MagicMock()
                    app_module.agent.maybe_generate.return_value = suggestion
                    app_module.agent.consume_last_generation_metadata.return_value = {
                        "memory_recall_attempted": False,
                        "memory_recalled": False,
                        "recalled_memory_ids": [],
                        "suggestion_block_reason": "",
                        "suggestion_block_detail": "",
                        **metadata,
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
                    app_module.memory_extractor.extract.return_value = []
                    app_module.vector_memory = MagicMock()
                    app_module.broker = MagicMock()
                    app_module.broker.publish = AsyncMock()

                    asyncio.run(app_module.process_event(event))

                    published_event = app_module.broker.publish.await_args_list[0].args[0]
                    status = published_event["data"]["processing_status"]
                    self.assertTrue(status["suggestion_generated"])
                    self.assertEqual(status["suggestion_id"], "sug-1")
                    self.assertEqual(status["suggestion_status"], "generated")
                finally:
                    app_module.session_memory = original_session_memory
                    app_module.long_term_store = original_long_term_store
                    app_module.agent = original_agent
                    app_module.memory_extractor = original_memory_extractor
                    app_module.vector_memory = original_vector_memory
                    app_module.broker = original_broker

    def test_process_event_sets_failed_suggestion_status_when_generation_failed(self):
        event = make_event()

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
            app_module.agent = MagicMock()
            app_module.agent.maybe_generate.return_value = None
            app_module.agent.consume_last_generation_metadata.return_value = {
                "memory_recall_attempted": True,
                "memory_recalled": False,
                "recalled_memory_ids": [],
                "suggestion_status": "failed",
                "suggestion_block_reason": "semantic_backend_unavailable",
                "suggestion_block_detail": "语义召回后端不可用，未生成建议。",
            }
            app_module.agent.current_status.return_value = {
                "mode": "qwen",
                "model": "qwen3.5-flash",
                "backend": "https://example.test/v1",
                "last_result": "error",
                "last_error": "semantic backend unavailable",
                "updated_at": 1,
            }
            app_module.memory_extractor = MagicMock()
            app_module.memory_extractor.extract.return_value = []
            app_module.vector_memory = MagicMock()
            app_module.broker = MagicMock()
            app_module.broker.publish = AsyncMock()

            asyncio.run(app_module.process_event(event))

            published_event = app_module.broker.publish.await_args_list[0].args[0]
            status = published_event["data"]["processing_status"]
            self.assertFalse(status["suggestion_generated"])
            self.assertEqual(status["suggestion_id"], "")
            self.assertEqual(status["suggestion_status"], "failed")
            self.assertEqual(status["suggestion_block_reason"], "semantic_backend_unavailable")
            self.assertEqual(status["suggestion_block_detail"], "语义召回后端不可用，未生成建议。")
        finally:
            app_module.session_memory = original_session_memory
            app_module.long_term_store = original_long_term_store
            app_module.agent = original_agent
            app_module.memory_extractor = original_memory_extractor
            app_module.vector_memory = original_vector_memory
            app_module.broker = original_broker

    def test_process_event_normalizes_recalled_memory_ids_from_unexpected_metadata(self):
        cases = (
            (None, []),
            (123, []),
            ("mem-single", ["mem-single"]),
            (("mem-a", "mem-b"), ["mem-a", "mem-b"]),
        )
        for raw_recalled_memory_ids, expected_ids in cases:
            with self.subTest(raw_recalled_memory_ids=raw_recalled_memory_ids):
                event = make_event()

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
                    app_module.agent = MagicMock()
                    app_module.agent.maybe_generate.return_value = None
                    app_module.agent.consume_last_generation_metadata.return_value = {
                        "memory_recall_attempted": True,
                        "memory_recalled": False,
                        "recalled_memory_ids": raw_recalled_memory_ids,
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
                    app_module.memory_extractor.extract.return_value = []
                    app_module.vector_memory = MagicMock()
                    app_module.broker = MagicMock()
                    app_module.broker.publish = AsyncMock()

                    asyncio.run(app_module.process_event(event))

                    published_event = app_module.broker.publish.await_args_list[0].args[0]
                    status = published_event["data"]["processing_status"]
                    self.assertEqual(status["recalled_memory_ids"], expected_ids)
                    self.assertEqual(status["memory_recalled"], bool(expected_ids))
                finally:
                    app_module.session_memory = original_session_memory
                    app_module.long_term_store = original_long_term_store
                    app_module.agent = original_agent
                    app_module.memory_extractor = original_memory_extractor
                    app_module.vector_memory = original_vector_memory
                    app_module.broker = original_broker

    def test_process_event_publishes_event_when_memory_pipeline_fails(self):
        for failure_point in ("extract", "save", "sync"):
            with self.subTest(failure_point=failure_point):
                event = make_event()
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
                            "memory_type": "preference",
                            "confidence": 0.91,
                        }
                    ]
                    if failure_point == "extract":
                        app_module.memory_extractor.extract.side_effect = RuntimeError("extract failed")
                    if failure_point == "save":
                        app_module.long_term_store.save_viewer_memory.side_effect = RuntimeError("save failed")

                    app_module.vector_memory = MagicMock()
                    if failure_point == "sync":
                        app_module.vector_memory.sync_memory.side_effect = RuntimeError("sync failed")

                    app_module.broker = MagicMock()
                    app_module.broker.publish = AsyncMock()

                    asyncio.run(app_module.process_event(event))

                    published_event = app_module.broker.publish.await_args_list[0].args[0]
                    status = published_event["data"]["processing_status"]
                    self.assertTrue(status["memory_extraction_attempted"])
                    self.assertFalse(status["memory_saved"])
                    self.assertEqual(status["saved_memory_ids"], [])
                    self.assertGreaterEqual(app_module.broker.publish.await_count, 3)
                finally:
                    app_module.session_memory = original_session_memory
                    app_module.long_term_store = original_long_term_store
                    app_module.agent = original_agent
                    app_module.memory_extractor = original_memory_extractor
                    app_module.vector_memory = original_vector_memory
                    app_module.broker = original_broker

    def test_process_event_marks_extraction_not_attempted_when_extractor_unavailable(self):
        event = make_event()

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
            app_module.memory_extractor = None
            app_module.vector_memory = MagicMock()
            app_module.broker = MagicMock()
            app_module.broker.publish = AsyncMock()

            with patch("backend.app.ensure_runtime", return_value=None):
                asyncio.run(app_module.process_event(event))

            published_event = app_module.broker.publish.await_args_list[0].args[0]
            status = published_event["data"]["processing_status"]
            self.assertFalse(status["memory_extraction_attempted"])
            self.assertFalse(status["memory_saved"])
            self.assertEqual(status["saved_memory_ids"], [])
            self.assertGreaterEqual(app_module.broker.publish.await_count, 3)
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
