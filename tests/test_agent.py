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


if __name__ == "__main__":
    unittest.main()
