import json
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock
from unittest.mock import patch

from backend.schemas.live import LiveEvent
from backend.services.agent import LivePromptAgent


def make_settings():
    return SimpleNamespace(
        llm_mode="qwen",
        llm_temperature=0.4,
        llm_timeout_seconds=6,
        llm_max_tokens=120,
        llm_api_key="test-key",
        resolved_llm_base_url=lambda: "https://example.test/v1",
        resolved_llm_model=lambda: "qwen3.5-flash",
    )


def make_event(event_type="comment", content="how much is it", nickname="A-Ming"):
    return LiveEvent(
        event_id="evt-1",
        room_id="room-1",
        source_room_id="source-room-1",
        session_id="session-1",
        platform="douyin",
        event_type=event_type,
        method="WebcastChatMessage" if event_type == "comment" else "WebcastGiftMessage",
        livename="test-room",
        ts=1234567890,
        user={"id": "user-1", "nickname": nickname},
        content=content,
        metadata={"gift_name": "heart"} if event_type == "gift" else {},
        raw={"huge": "payload"},
    )


class LivePromptAgentTests(unittest.TestCase):
    def test_build_context_compacts_prompt_inputs(self):
        vector_memory = MagicMock()
        vector_memory.similar_memories.return_value = [
            {"memory_id": "m1", "memory_text": "likes ramen", "score": 0.9, "metadata": {}},
            {"memory_id": "m2", "memory_text": "from hangzhou", "score": 0.8, "metadata": {}},
            {"memory_id": "m3", "memory_text": "has a cat", "score": 0.7, "metadata": {}},
        ]

        long_term_store = MagicMock()
        long_term_store.get_user_profile.return_value = {
            "viewer_id": "user-1",
            "nickname": "A-Ming",
            "comment_count": 15,
            "gift_event_count": 3,
            "last_comment": "nice outfit today",
            "recent_comments": [{"content": "very long old comment"}],
            "gift_history": [{"gift_name": "heart"}],
            "recent_sessions": [{"session_id": "old"}],
            "memories": [{"memory_text": "old memory"}],
            "notes": [{"content": "manual note"}],
        }

        agent = LivePromptAgent(make_settings(), vector_memory, long_term_store)
        recent_events = [make_event(content=f"recent comment {i}", nickname=f"user{i}") for i in range(5)]

        context = agent.build_context(make_event(content="I like ramen"), recent_events)

        self.assertEqual(len(context["recent_events"]), 3)
        self.assertEqual(
            context["recent_events"][0],
            {"event_type": "comment", "nickname": "user0", "content": "recent comment 0"},
        )
        self.assertEqual(context["viewer_memory_texts"], ["likes ramen", "from hangzhou"])
        self.assertEqual(
            context["user_profile"],
            {
                "nickname": "A-Ming",
                "comment_count": 15,
                "gift_event_count": 3,
                "last_comment": "nice outfit today",
            },
        )
        self.assertEqual(context["recalled_memory_ids"], ["m1", "m2"])

    def test_build_context_uses_rewritten_query_for_memory_recall(self):
        vector_memory = MagicMock()
        vector_memory.similar_memories.return_value = []
        long_term_store = MagicMock()
        long_term_store.get_user_profile.return_value = {}
        query_rewriter = MagicMock()
        query_rewriter.rewrite.return_value = "最近想吃面；召回拉面和饮食偏好"
        agent = LivePromptAgent(make_settings(), vector_memory, long_term_store, query_rewriter=query_rewriter)

        event = make_event(content="最近想吃面")
        agent.build_context(event, [])

        query_rewriter.rewrite.assert_called_once_with("最近想吃面", room_id="room-1", viewer_id="id:user-1")
        vector_memory.similar_memories.assert_called_once_with(
            "最近想吃面；召回拉面和饮食偏好",
            room_id="room-1",
            viewer_id="id:user-1",
            limit=2,
        )

    def test_maybe_generate_skips_llm_for_gift_events(self):
        agent = LivePromptAgent(make_settings(), MagicMock(), MagicMock())
        event = make_event(event_type="gift", content="", nickname="gift-viewer")

        with patch.object(agent, "build_context") as build_context_mock, patch.object(
            agent, "_generate_with_openai_compatible"
        ) as llm_mock, patch.object(
            agent,
            "_generate_heuristic",
            return_value={
                "source": "heuristic",
                "priority": "high",
                "reply_text": "thanks for the gift",
                "tone": "warm",
                "reason": "gift events use heuristics",
                "confidence": 0.9,
            },
        ):
            suggestion = agent.maybe_generate(event, [])

        build_context_mock.assert_not_called()
        llm_mock.assert_not_called()
        self.assertEqual(suggestion.source, "heuristic")
        self.assertEqual(suggestion.priority, "high")

    def test_generate_with_openai_compatible_includes_max_tokens_and_omits_similar_history(self):
        long_term_store = MagicMock()
        long_term_store.get_llm_settings.return_value = {
            "model": "qwen3.5-flash",
            "system_prompt": "system prompt",
            "default_model": "qwen3.5-flash",
            "default_system_prompt": "system prompt",
        }
        agent = LivePromptAgent(make_settings(), MagicMock(), long_term_store)
        event = make_event()
        context = {
            "recent_events": [{"event_type": "comment", "nickname": "A-Ming", "content": "how much"}],
            "user_profile": {"nickname": "A-Ming", "comment_count": 5},
            "viewer_memories": [],
            "viewer_memory_texts": ["likes ramen"],
        }

        response_payload = {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            {
                                "priority": "high",
                                "reply_text": "answer price first",
                                "tone": "direct",
                                "reason": "user asks price",
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
            body = json.loads(request.data.decode("utf-8"))
            self.assertEqual(body["max_tokens"], 120)
            prompt = json.loads(body["messages"][1]["content"])
            self.assertNotIn("similar_history", prompt["context"])
            return FakeResponse()

        with patch("backend.services.agent.urllib.request.urlopen", side_effect=fake_urlopen):
            payload = agent._generate_with_openai_compatible(event, context)

        self.assertEqual(payload["source"], "model")

    def test_maybe_generate_sends_recalled_and_current_comment_memories_into_llm_prompt(self):
        vector_memory = MagicMock()
        vector_memory.similar_memories.return_value = [
            {"memory_id": "m1", "memory_text": "likes ramen", "score": 0.9, "metadata": {}},
            {"memory_id": "m2", "memory_text": "cannot eat spicy food", "score": 0.86, "metadata": {}},
        ]
        long_term_store = MagicMock()
        long_term_store.get_user_profile.return_value = {
            "nickname": "A-Ming",
            "comment_count": 12,
            "last_comment": "lets eat noodles next time",
        }
        long_term_store.get_llm_settings.return_value = {
            "model": "qwen3.5-flash",
            "system_prompt": "system prompt",
            "default_model": "qwen3.5-flash",
            "default_system_prompt": "system prompt",
        }
        agent = LivePromptAgent(make_settings(), vector_memory, long_term_store)
        event = make_event(event_type="comment", content="I still want tonkotsu ramen tonight")
        recent_events = [make_event(content="old comment", nickname="someone")]
        current_comment_memories = [
            {
                "memory_text": "likes tonkotsu ramen",
                "memory_type": "preference",
            }
        ]
        captured = {}

        response_payload = {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            {
                                "priority": "high",
                                "reply_text": "pick up the old food topic",
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
            suggestion = agent.maybe_generate(
                event,
                recent_events,
                current_comment_memories=current_comment_memories,
            )

        self.assertIsNotNone(suggestion)
        prompt = json.loads(captured["body"]["messages"][1]["content"])
        self.assertEqual(captured["body"]["model"], "qwen3.5-flash")
        self.assertEqual(captured["body"]["max_tokens"], 120)
        self.assertEqual(prompt["event"]["content"], "I still want tonkotsu ramen tonight")
        self.assertEqual(
            prompt["context"]["viewer_memories"],
            ["likes tonkotsu ramen", "likes ramen", "cannot eat spicy food"],
        )
        metadata = agent.consume_last_generation_metadata()
        self.assertTrue(metadata["memory_recall_attempted"])
        self.assertTrue(metadata["memory_recalled"])
        self.assertTrue(metadata["current_comment_memory_used"])
        self.assertEqual(metadata["recalled_memory_ids"], ["m1", "m2"])
        self.assertEqual(metadata["recalled_memory_texts"], ["likes ramen", "cannot eat spicy food"])
        self.assertEqual(metadata["suggestion_support_kind"], "memory")

    def test_maybe_generate_returns_none_and_sets_metadata_for_blank_comment(self):
        agent = LivePromptAgent(make_settings(), MagicMock(), MagicMock())
        event = make_event(event_type="comment", content="   ")

        result = agent.maybe_generate(event, [])

        self.assertIsNone(result)
        metadata = agent.consume_last_generation_metadata()
        self.assertEqual(metadata["suggestion_status"], "skipped")
        self.assertEqual(metadata["suggestion_block_reason"], "no_generation_needed")
        self.assertEqual(metadata["suggestion_block_detail"], "评论内容为空，未生成建议。")
        self.assertFalse(metadata["memory_recall_attempted"])
        self.assertEqual(metadata["recalled_memory_ids"], [])

    def test_maybe_generate_handles_semantic_backend_runtime_error_in_strict_mode(self):
        vector_memory = MagicMock()
        vector_memory.similar_memories.side_effect = RuntimeError(
            "Vector recall strict mode blocked fallback: semantic backend unavailable"
        )
        agent = LivePromptAgent(make_settings(), vector_memory, MagicMock())
        event = make_event(event_type="comment", content="hello there")

        result = agent.maybe_generate(event, [])

        self.assertIsNone(result)
        metadata = agent.consume_last_generation_metadata()
        self.assertEqual(metadata["suggestion_status"], "failed")
        self.assertEqual(metadata["suggestion_block_reason"], "semantic_backend_unavailable")
        self.assertEqual(metadata["suggestion_block_detail"], "语义召回后端不可用，未生成建议。")
        self.assertTrue(metadata["memory_recall_attempted"])
        self.assertFalse(metadata["memory_recalled"])
        status = agent.current_status()
        self.assertEqual(status["last_result"], "error")
        self.assertEqual(status["last_error"], "semantic_backend_unavailable")

    def test_maybe_generate_does_not_mislabel_non_strict_runtime_error(self):
        vector_memory = MagicMock()
        vector_memory.similar_memories.side_effect = RuntimeError("unexpected runtime failure")
        agent = LivePromptAgent(make_settings(), vector_memory, MagicMock())
        event = make_event(event_type="comment", content="hello there")

        with self.assertRaises(RuntimeError):
            agent.maybe_generate(event, [])

    def test_maybe_generate_sets_rule_skipped_metadata_for_unsupported_event(self):
        agent = LivePromptAgent(make_settings(), MagicMock(), MagicMock())
        event = make_event(event_type="enter", content="")

        result = agent.maybe_generate(event, [])

        self.assertIsNone(result)
        metadata = agent.consume_last_generation_metadata()
        self.assertEqual(metadata["suggestion_status"], "skipped")
        self.assertEqual(metadata["suggestion_block_reason"], "rule_skipped")
        self.assertEqual(metadata["suggestion_block_detail"], "事件类型不支持，未生成建议。")
        self.assertFalse(metadata["memory_recall_attempted"])
        self.assertFalse(metadata["memory_recalled"])
        self.assertEqual(metadata["recalled_memory_ids"], [])

    def test_maybe_generate_sets_generated_metadata_on_success_with_recall_shape(self):
        vector_memory = MagicMock()
        vector_memory.similar_memories.return_value = [
            {"memory_id": "m-1", "memory_text": "likes noodles", "score": 0.9, "metadata": {}}
        ]
        long_term_store = MagicMock()
        long_term_store.get_user_profile.return_value = {}
        agent = LivePromptAgent(make_settings(), vector_memory, long_term_store)
        event = make_event(event_type="comment", content="just chatting")

        with patch.object(
            agent,
            "_generate_payload",
            return_value={
                "source": "model",
                "priority": "medium",
                "reply_text": "continue naturally",
                "tone": "natural",
                "reason": "context available",
                "confidence": 0.8,
            },
        ):
            result = agent.maybe_generate(event, [])

        self.assertIsNotNone(result)
        metadata = agent.consume_last_generation_metadata()
        self.assertEqual(metadata["suggestion_status"], "generated")
        self.assertEqual(metadata["suggestion_block_reason"], "")
        self.assertEqual(metadata["suggestion_block_detail"], "")
        self.assertTrue(metadata["memory_recall_attempted"])
        self.assertTrue(metadata["memory_recalled"])
        self.assertEqual(metadata["recalled_memory_ids"], ["m-1"])

    def test_maybe_generate_skip_paths_reset_status_after_non_skip_or_error(self):
        vector_memory = MagicMock()
        vector_memory.similar_memories.side_effect = RuntimeError(
            "Vector recall strict mode blocked fallback: semantic backend unavailable"
        )
        agent = LivePromptAgent(make_settings(), vector_memory, MagicMock())

        failed_event = make_event(event_type="comment", content="hello")
        agent.maybe_generate(failed_event, [])
        failed_status = agent.current_status()
        self.assertEqual(failed_status["last_result"], "error")
        self.assertEqual(failed_status["last_error"], "semantic_backend_unavailable")

        skipped_event = make_event(event_type="comment", content="   ")
        skip_result = agent.maybe_generate(skipped_event, [])
        self.assertIsNone(skip_result)
        skip_status = agent.current_status()
        self.assertEqual(skip_status["last_result"], "idle")
        self.assertEqual(skip_status["last_error"], "")

        success_vector_memory = MagicMock()
        success_vector_memory.similar_memories.return_value = []
        success_long_term_store = MagicMock()
        success_long_term_store.get_user_profile.return_value = {}
        success_like_agent = LivePromptAgent(make_settings(), success_vector_memory, success_long_term_store)
        with patch.object(success_like_agent, "_should_short_circuit_with_heuristic", return_value=False), patch.object(
            success_like_agent,
            "_generate_with_openai_compatible",
            return_value={
                "source": "model",
                "priority": "medium",
                "reply_text": "ok",
                "tone": "natural",
                "reason": "ok",
                "confidence": 0.8,
            },
        ):
            success_like_agent.maybe_generate(make_event(event_type="comment", content="normal"), [])
        pre_skip_status = success_like_agent.current_status()
        self.assertEqual(pre_skip_status["last_result"], "ok")

        unsupported_event = make_event(event_type="enter", content="")
        unsupported_result = success_like_agent.maybe_generate(unsupported_event, [])
        self.assertIsNone(unsupported_result)
        post_skip_status = success_like_agent.current_status()
        self.assertEqual(post_skip_status["last_result"], "idle")
        self.assertEqual(post_skip_status["last_error"], "")


if __name__ == "__main__":
    unittest.main()
