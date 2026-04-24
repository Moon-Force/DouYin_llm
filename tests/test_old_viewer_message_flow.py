import asyncio
import json
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from unittest.mock import patch
from unittest.mock import ANY

import backend.app as app_module
from backend.schemas.live import LiveEvent
from backend.services.agent import LivePromptAgent
from backend.services.memory_merge_service import MemoryMergeDecision


def make_settings():
    return SimpleNamespace(
        llm_mode="heuristic",
        llm_temperature=0.4,
        llm_timeout_seconds=6,
        llm_max_tokens=120,
        llm_api_key="",
        memory_short_term_ttl_hours=72.0,
        resolved_llm_base_url=lambda: "https://example.test/v1",
        resolved_llm_model=lambda: "heuristic",
    )


def make_event():
    return LiveEvent(
        event_id="evt-old-viewer-1",
        room_id="room-1",
        source_room_id="source-room-1",
        session_id="session-1",
        platform="douyin",
        event_type="comment",
        method="WebcastChatMessage",
        livename="test-room",
        ts=1234567890,
        user={"id": "user-1", "nickname": "A-Ming"},
        content="今晚还想去吃面",
        metadata={},
        raw={},
    )


class OldViewerMessageFlowTests(unittest.TestCase):
    def test_process_event_sends_recalled_and_current_comment_memories_into_llm_prompt(self):
        event = make_event()
        settings = SimpleNamespace(
            llm_mode="qwen",
            llm_temperature=0.4,
            llm_timeout_seconds=6,
            llm_max_tokens=120,
            llm_api_key="test-key",
            memory_short_term_ttl_hours=72.0,
            resolved_llm_base_url=lambda: "https://example.test/v1",
            resolved_llm_model=lambda: "qwen3.5-flash",
        )
        captured = {}

        original_settings = app_module.settings
        original_session_memory = app_module.session_memory
        original_long_term_store = app_module.long_term_store
        original_agent = app_module.agent
        original_memory_extractor = app_module.memory_extractor
        original_vector_memory = app_module.vector_memory
        original_broker = app_module.broker
        original_memory_merge_service = getattr(app_module, "memory_merge_service", None)
        original_memory_confidence_service = getattr(app_module, "memory_confidence_service", None)
        try:
            app_module.settings = settings
            app_module.session_memory = MagicMock()
            app_module.session_memory.recent_events.return_value = [event]
            app_module.session_memory.stats.return_value = SimpleNamespace(
                model_dump=lambda: {"room_id": "room-1", "total_events": 1}
            )

            app_module.long_term_store = MagicMock()
            app_module.long_term_store.get_user_profile.return_value = {
                "nickname": "A-Ming",
                "comment_count": 25,
                "gift_event_count": 4,
                "last_comment": "上次聊过拉面",
            }
            app_module.long_term_store.get_llm_settings.return_value = {
                "model": "qwen3.5-flash",
                "system_prompt": "system prompt",
                "default_model": "qwen3.5-flash",
                "default_system_prompt": "system prompt",
            }
            app_module.long_term_store.list_viewer_memories.return_value = [
                {
                    "memory_id": "mem-ramen",
                    "memory_text": "喜欢拉面",
                    "memory_type": "preference",
                    "status": "active",
                },
                {
                    "memory_id": "mem-spicy",
                    "memory_text": "不能吃太辣",
                    "memory_type": "preference",
                    "status": "active",
                },
            ]
            app_module.long_term_store.touch_viewer_memories = MagicMock()

            app_module.vector_memory = MagicMock()
            app_module.vector_memory.similar_memories.side_effect = [
                [
                    {
                        "memory_id": "mem-ramen",
                        "memory_text": "喜欢拉面",
                        "score": 0.93,
                        "metadata": {"room_id": "room-1", "viewer_id": "id:user-1", "status": "active"},
                    },
                    {
                        "memory_id": "mem-spicy",
                        "memory_text": "不能吃太辣",
                        "score": 0.88,
                        "metadata": {"room_id": "room-1", "viewer_id": "id:user-1", "status": "active"},
                    },
                ],
                [
                    {
                        "memory_id": "mem-ramen",
                        "memory_text": "喜欢拉面",
                        "score": 0.91,
                        "metadata": {"room_id": "room-1", "viewer_id": "id:user-1", "status": "active"},
                    }
                ],
            ]

            app_module.agent = LivePromptAgent(settings, app_module.vector_memory, app_module.long_term_store)

            app_module.memory_extractor = MagicMock()
            app_module.memory_extractor.extract.return_value = [
                {
                    "memory_text": "喜欢豚骨拉面",
                    "memory_text_raw": "我还是最爱吃豚骨拉面",
                    "memory_text_canonical": "喜欢豚骨拉面",
                    "memory_type": "preference",
                    "confidence": 0.91,
                    "polarity": "positive",
                    "temporal_scope": "long_term",
                }
            ]
            app_module.memory_extractor.consume_last_extraction_metadata.return_value = {
                "memory_prefiltered": False,
                "memory_llm_attempted": True,
                "memory_refined": True,
                "fallback_used": False,
            }

            app_module.memory_merge_service = MagicMock()
            app_module.memory_merge_service.decide.return_value = MemoryMergeDecision(
                action="create",
                target_memory_id="",
                reason="new_memory",
            )

            app_module.memory_confidence_service = MagicMock()
            app_module.memory_confidence_service.score_new_memory.return_value = {
                "stability_score": 0.6,
                "interaction_value_score": 0.8,
                "clarity_score": 0.9,
                "evidence_score": 0.4,
                "confidence": 0.81,
            }
            app_module.long_term_store.save_viewer_memory.return_value = SimpleNamespace(memory_id="mem-new", status="active")

            app_module.broker = MagicMock()
            app_module.broker.publish = AsyncMock()

            response_payload = {
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "priority": "high",
                                    "reply_text": "接上次拉面的话题",
                                    "tone": "natural",
                                    "reason": "memory context found",
                                    "confidence": 0.9,
                                },
                                ensure_ascii=False,
                            )
                        }
                    }
                ]
            }

            class FakeResponse:
                def __enter__(self):
                    return self

                def __exit__(self, exc_type, exc, tb):
                    return False

                def read(self):
                    return json.dumps(response_payload, ensure_ascii=False).encode("utf-8")

            def fake_urlopen(request, timeout):
                captured["timeout"] = timeout
                captured["body"] = json.loads(request.data.decode("utf-8"))
                return FakeResponse()

            with patch("backend.services.agent.urllib.request.urlopen", side_effect=fake_urlopen):
                suggestion = asyncio.run(app_module.process_event(event))

            self.assertIsNotNone(suggestion)
            prompt = json.loads(captured["body"]["messages"][1]["content"])
            self.assertEqual(captured["body"]["model"], "qwen3.5-flash")
            self.assertEqual(prompt["event"]["content"], "今晚还想去吃面")
            self.assertEqual(
                prompt["context"]["viewer_memories"],
                ["喜欢豚骨拉面", "喜欢拉面", "不能吃太辣"],
            )

            published_event = app_module.broker.publish.await_args_list[0].args[0]
            status = published_event["data"]["processing_status"]
            self.assertTrue(status["memory_recall_attempted"])
            self.assertTrue(status["memory_recalled"])
            self.assertTrue(status["memory_used_for_current_suggestion"])
            self.assertEqual(status["recalled_memory_ids"], ["mem-ramen", "mem-spicy"])
        finally:
            app_module.settings = original_settings
            app_module.session_memory = original_session_memory
            app_module.long_term_store = original_long_term_store
            app_module.agent = original_agent
            app_module.memory_extractor = original_memory_extractor
            app_module.vector_memory = original_vector_memory
            app_module.broker = original_broker
            app_module.memory_merge_service = original_memory_merge_service
            app_module.memory_confidence_service = original_memory_confidence_service

    def test_process_event_uses_old_viewer_memories_for_suggestion_and_upgrade_flow(self):
        event = make_event()
        settings = make_settings()
        upgraded_memory = SimpleNamespace(memory_id="mem-ramen", status="active")

        original_settings = app_module.settings
        original_session_memory = app_module.session_memory
        original_long_term_store = app_module.long_term_store
        original_agent = app_module.agent
        original_memory_extractor = app_module.memory_extractor
        original_vector_memory = app_module.vector_memory
        original_broker = app_module.broker
        original_memory_merge_service = getattr(app_module, "memory_merge_service", None)
        original_memory_confidence_service = getattr(app_module, "memory_confidence_service", None)
        try:
            app_module.settings = settings
            app_module.session_memory = MagicMock()
            app_module.session_memory.recent_events.return_value = [event]
            app_module.session_memory.stats.return_value = SimpleNamespace(
                model_dump=lambda: {"room_id": "room-1", "total_events": 1}
            )

            app_module.long_term_store = MagicMock()
            app_module.long_term_store.get_user_profile.return_value = {
                "nickname": "A-Ming",
                "comment_count": 25,
                "gift_event_count": 4,
                "last_comment": "上次去吃了拉面",
            }
            app_module.long_term_store.get_llm_settings.return_value = {
                "model": "heuristic",
                "system_prompt": "test system prompt",
                "default_model": "heuristic",
                "default_system_prompt": "test system prompt",
            }
            app_module.long_term_store.list_viewer_memories.return_value = [
                {
                    "memory_id": "mem-ramen",
                    "memory_text": "喜欢拉面",
                    "memory_type": "preference",
                    "status": "active",
                },
                {
                    "memory_id": "mem-spicy",
                    "memory_text": "不能吃太辣",
                    "memory_type": "preference",
                    "status": "active",
                },
                {
                    "memory_id": "mem-city",
                    "memory_text": "住在公司附近",
                    "memory_type": "context",
                    "status": "active",
                },
            ]
            app_module.long_term_store.upgrade_viewer_memory.return_value = upgraded_memory

            app_module.vector_memory = MagicMock()
            app_module.vector_memory.similar_memories.side_effect = [
                [
                    {
                        "memory_id": "mem-ramen",
                        "memory_text": "喜欢拉面",
                        "score": 0.93,
                        "metadata": {
                            "room_id": "room-1",
                            "viewer_id": "id:user-1",
                            "status": "active",
                            "source_kind": "manual",
                            "is_pinned": 1,
                            "interaction_value_score": 0.9,
                            "evidence_score": 0.8,
                            "updated_at": 300,
                            "recall_count": 5,
                        },
                    },
                    {
                        "memory_id": "mem-spicy",
                        "memory_text": "不能吃太辣",
                        "score": 0.88,
                        "metadata": {
                            "room_id": "room-1",
                            "viewer_id": "id:user-1",
                            "status": "active",
                            "source_kind": "auto",
                            "is_pinned": 0,
                            "interaction_value_score": 0.7,
                            "evidence_score": 0.6,
                            "updated_at": 280,
                            "recall_count": 3,
                        },
                    },
                ],
                [
                    {
                        "memory_id": "mem-ramen",
                        "memory_text": "喜欢拉面",
                        "score": 0.91,
                        "metadata": {
                            "room_id": "room-1",
                            "viewer_id": "id:user-1",
                            "status": "active",
                        },
                    }
                ],
            ]

            app_module.agent = LivePromptAgent(settings, app_module.vector_memory, app_module.long_term_store)

            app_module.memory_extractor = MagicMock()
            app_module.memory_extractor.extract.return_value = [
                {
                    "memory_text": "喜欢豚骨拉面",
                    "memory_text_raw": "我还是最爱吃豚骨拉面",
                    "memory_text_canonical": "喜欢豚骨拉面",
                    "memory_type": "preference",
                    "confidence": 0.91,
                    "polarity": "positive",
                    "temporal_scope": "long_term",
                }
            ]
            app_module.memory_extractor.consume_last_extraction_metadata.return_value = {
                "memory_prefiltered": False,
                "memory_llm_attempted": True,
                "memory_refined": True,
                "fallback_used": False,
            }

            app_module.memory_merge_service = MagicMock()
            app_module.memory_merge_service.decide.return_value = MemoryMergeDecision(
                action="upgrade",
                target_memory_id="mem-ramen",
                reason="more_specific",
            )

            app_module.memory_confidence_service = MagicMock()
            app_module.broker = MagicMock()
            app_module.broker.publish = AsyncMock()

            suggestion = asyncio.run(app_module.process_event(event))

            self.assertIsNotNone(suggestion)
            self.assertEqual(suggestion.reply_text, "可以接一句：你上次说喜欢豚骨拉面，今晚是不是去那家？")
            self.assertEqual(suggestion.references, ["喜欢豚骨拉面", "喜欢拉面", "不能吃太辣"])

            app_module.long_term_store.persist_event.assert_called_once_with(event)
            app_module.long_term_store.persist_suggestion.assert_called_once()
            app_module.long_term_store.touch_viewer_memories.assert_called_once_with(["mem-ramen", "mem-spicy"])
            app_module.long_term_store.upgrade_viewer_memory.assert_called_once_with(
                "mem-ramen",
                memory_text="喜欢豚骨拉面",
                raw_memory_text="我还是最爱吃豚骨拉面",
                confidence=0.91,
                source_event_id="evt-old-viewer-1",
                memory_recall_text=ANY,
            )
            app_module.long_term_store.save_viewer_memory.assert_not_called()
            app_module.vector_memory.sync_memory.assert_called_once_with(upgraded_memory)

            published_event = app_module.broker.publish.await_args_list[0].args[0]
            published_suggestion = app_module.broker.publish.await_args_list[1].args[0]
            status = published_event["data"]["processing_status"]

            self.assertTrue(status["received"])
            self.assertTrue(status["persisted"])
            self.assertTrue(status["memory_extraction_attempted"])
            self.assertTrue(status["memory_llm_attempted"])
            self.assertTrue(status["memory_refined"])
            self.assertTrue(status["memory_recall_attempted"])
            self.assertTrue(status["memory_recalled"])
            self.assertEqual(status["recalled_memory_ids"], ["mem-ramen", "mem-spicy"])
            self.assertTrue(status["memory_used_for_current_suggestion"])
            self.assertTrue(status["suggestion_generated"])
            self.assertEqual(status["saved_memory_ids"], ["mem-ramen"])
            self.assertEqual(published_suggestion["data"]["references"], ["喜欢豚骨拉面", "喜欢拉面", "不能吃太辣"])
        finally:
            app_module.settings = original_settings
            app_module.session_memory = original_session_memory
            app_module.long_term_store = original_long_term_store
            app_module.agent = original_agent
            app_module.memory_extractor = original_memory_extractor
            app_module.vector_memory = original_vector_memory
            app_module.broker = original_broker
            app_module.memory_merge_service = original_memory_merge_service
            app_module.memory_confidence_service = original_memory_confidence_service


if __name__ == "__main__":
    unittest.main()
