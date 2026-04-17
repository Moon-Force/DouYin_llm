import json
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock
from unittest.mock import patch

from backend.schemas.live import LiveEvent


def make_event(
    *,
    event_type="comment",
    content="我喜欢吃面",
    user=None,
):
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
        user=user or {"id": "user-1", "nickname": "Alice"},
        content=content,
        metadata={},
        raw={},
    )


class FakeRuntime:
    def __init__(self, payload):
        self.payload = payload
        self.calls = []

    def infer_json(self, system_prompt, user_prompt):
        self.calls.append((system_prompt, user_prompt))
        return self.payload


class LLMBackedViewerMemoryExtractorTests(unittest.TestCase):
    def test_extract_returns_candidate_for_valid_long_term_preference(self):
        from backend.services.llm_memory_extractor import LLMBackedViewerMemoryExtractor

        runtime = FakeRuntime(
            json.dumps(
                {
                    "should_extract": True,
                    "memory_text": "喜欢喝无糖可乐",
                    "memory_type": "preference",
                    "polarity": "positive",
                    "temporal_scope": "long_term",
                    "certainty": "high",
                    "reason": "稳定偏好",
                },
                ensure_ascii=False,
            )
        )
        extractor = LLMBackedViewerMemoryExtractor(settings=SimpleNamespace(), runtime=runtime)

        result = extractor.extract(make_event())

        self.assertEqual(
            result,
            [{"memory_text": "喜欢喝无糖可乐", "memory_type": "preference", "confidence": 0.86}],
        )
        self.assertEqual(len(runtime.calls), 1)
        prompt_payload = json.loads(runtime.calls[0][1])
        self.assertEqual(prompt_payload["event"]["room_id"], "room-1")
        self.assertEqual(prompt_payload["event"]["viewer_id"], "id:user-1")

    def test_extract_rejects_short_term_candidate(self):
        from backend.services.llm_memory_extractor import LLMBackedViewerMemoryExtractor

        runtime = FakeRuntime(
            json.dumps(
                {
                    "should_extract": True,
                    "memory_text": "今晚加班",
                    "memory_type": "context",
                    "polarity": "neutral",
                    "temporal_scope": "short_term",
                    "certainty": "high",
                    "reason": "只对今晚有效",
                },
                ensure_ascii=False,
            )
        )
        extractor = LLMBackedViewerMemoryExtractor(settings=SimpleNamespace(), runtime=runtime)

        result = extractor.extract(make_event(content="今晚加班"))

        self.assertEqual(result, [])

    def test_extract_raises_json_decode_error_for_invalid_json(self):
        from backend.services.llm_memory_extractor import LLMBackedViewerMemoryExtractor

        runtime = FakeRuntime("{")
        extractor = LLMBackedViewerMemoryExtractor(settings=SimpleNamespace(), runtime=runtime)

        with self.assertRaises(json.JSONDecodeError):
            extractor.extract(make_event())

    def test_extract_preserves_negative_preference_text(self):
        from backend.services.llm_memory_extractor import LLMBackedViewerMemoryExtractor

        runtime = FakeRuntime(
            json.dumps(
                {
                    "should_extract": True,
                    "memory_text": "不喜欢辣",
                    "memory_type": "preference",
                    "polarity": "negative",
                    "temporal_scope": "long_term",
                    "certainty": "medium",
                    "reason": "明确长期口味偏好",
                },
                ensure_ascii=False,
            )
        )
        extractor = LLMBackedViewerMemoryExtractor(settings=SimpleNamespace(), runtime=runtime)

        result = extractor.extract(make_event(content="我不喜欢辣"))

        self.assertEqual(
            result,
            [{"memory_text": "不喜欢辣", "memory_type": "preference", "confidence": 0.72}],
        )

    def test_extract_returns_empty_for_non_comment_empty_content_or_missing_viewer(self):
        from backend.services.llm_memory_extractor import LLMBackedViewerMemoryExtractor

        runtime = FakeRuntime(
            json.dumps(
                {
                    "should_extract": True,
                    "memory_text": "喜欢牛肉面",
                    "memory_type": "preference",
                    "polarity": "positive",
                    "temporal_scope": "long_term",
                    "certainty": "high",
                    "reason": "测试",
                },
                ensure_ascii=False,
            )
        )
        extractor = LLMBackedViewerMemoryExtractor(settings=SimpleNamespace(), runtime=runtime)

        non_comment = make_event(event_type="gift", content="")
        empty_content = make_event(content="   ")
        no_viewer = make_event(content="我喜欢面", user={"id": "", "short_id": "", "sec_uid": "", "nickname": "   "})

        self.assertEqual(extractor.extract(non_comment), [])
        self.assertEqual(extractor.extract(empty_content), [])
        self.assertEqual(extractor.extract(no_viewer), [])
        self.assertEqual(runtime.calls, [])

    def test_extract_rejects_candidate_without_polarity(self):
        from backend.services.llm_memory_extractor import LLMBackedViewerMemoryExtractor

        runtime = FakeRuntime(
            json.dumps(
                {
                    "should_extract": True,
                    "memory_text": "喜欢喝无糖可乐",
                    "memory_type": "preference",
                    "temporal_scope": "long_term",
                    "certainty": "high",
                    "reason": "稳定偏好",
                },
                ensure_ascii=False,
            )
        )
        extractor = LLMBackedViewerMemoryExtractor(settings=SimpleNamespace(), runtime=runtime)

        self.assertEqual(extractor.extract(make_event()), [])

    def test_extract_rejects_candidate_without_or_empty_reason(self):
        from backend.services.llm_memory_extractor import LLMBackedViewerMemoryExtractor

        missing_reason_runtime = FakeRuntime(
            json.dumps(
                {
                    "should_extract": True,
                    "memory_text": "喜欢喝无糖可乐",
                    "memory_type": "preference",
                    "polarity": "positive",
                    "temporal_scope": "long_term",
                    "certainty": "high",
                },
                ensure_ascii=False,
            )
        )
        empty_reason_runtime = FakeRuntime(
            json.dumps(
                {
                    "should_extract": True,
                    "memory_text": "喜欢喝无糖可乐",
                    "memory_type": "preference",
                    "polarity": "positive",
                    "temporal_scope": "long_term",
                    "certainty": "high",
                    "reason": "   ",
                },
                ensure_ascii=False,
            )
        )

        missing_reason_extractor = LLMBackedViewerMemoryExtractor(
            settings=SimpleNamespace(), runtime=missing_reason_runtime
        )
        empty_reason_extractor = LLMBackedViewerMemoryExtractor(
            settings=SimpleNamespace(), runtime=empty_reason_runtime
        )

        self.assertEqual(missing_reason_extractor.extract(make_event()), [])
        self.assertEqual(empty_reason_extractor.extract(make_event()), [])

    def test_extract_rejects_non_dict_payload(self):
        from backend.services.llm_memory_extractor import LLMBackedViewerMemoryExtractor

        list_runtime = FakeRuntime("[]")
        int_runtime = FakeRuntime("1")
        list_extractor = LLMBackedViewerMemoryExtractor(settings=SimpleNamespace(), runtime=list_runtime)
        int_extractor = LLMBackedViewerMemoryExtractor(settings=SimpleNamespace(), runtime=int_runtime)

        self.assertEqual(list_extractor.extract(make_event()), [])
        self.assertEqual(int_extractor.extract(make_event()), [])

    def test_extract_rejects_invalid_or_non_string_polarity(self):
        from backend.services.llm_memory_extractor import LLMBackedViewerMemoryExtractor

        invalid_value_runtime = FakeRuntime(
            json.dumps(
                {
                    "should_extract": True,
                    "memory_text": "喜欢喝无糖可乐",
                    "memory_type": "preference",
                    "polarity": "mixed",
                    "temporal_scope": "long_term",
                    "certainty": "high",
                    "reason": "稳定偏好",
                },
                ensure_ascii=False,
            )
        )
        non_string_runtime = FakeRuntime(
            json.dumps(
                {
                    "should_extract": True,
                    "memory_text": "喜欢喝无糖可乐",
                    "memory_type": "preference",
                    "polarity": 1,
                    "temporal_scope": "long_term",
                    "certainty": "high",
                    "reason": "稳定偏好",
                },
                ensure_ascii=False,
            )
        )
        invalid_value_extractor = LLMBackedViewerMemoryExtractor(
            settings=SimpleNamespace(), runtime=invalid_value_runtime
        )
        non_string_extractor = LLMBackedViewerMemoryExtractor(settings=SimpleNamespace(), runtime=non_string_runtime)

        self.assertEqual(invalid_value_extractor.extract(make_event()), [])
        self.assertEqual(non_string_extractor.extract(make_event()), [])

    def test_extract_rejects_non_string_memory_text_or_reason(self):
        from backend.services.llm_memory_extractor import LLMBackedViewerMemoryExtractor

        non_string_text_runtime = FakeRuntime(
            json.dumps(
                {
                    "should_extract": True,
                    "memory_text": 123,
                    "memory_type": "preference",
                    "polarity": "positive",
                    "temporal_scope": "long_term",
                    "certainty": "high",
                    "reason": "稳定偏好",
                },
                ensure_ascii=False,
            )
        )
        non_string_reason_runtime = FakeRuntime(
            json.dumps(
                {
                    "should_extract": True,
                    "memory_text": "喜欢喝无糖可乐",
                    "memory_type": "preference",
                    "polarity": "positive",
                    "temporal_scope": "long_term",
                    "certainty": "high",
                    "reason": 123,
                },
                ensure_ascii=False,
            )
        )
        non_string_text_extractor = LLMBackedViewerMemoryExtractor(
            settings=SimpleNamespace(), runtime=non_string_text_runtime
        )
        non_string_reason_extractor = LLMBackedViewerMemoryExtractor(
            settings=SimpleNamespace(), runtime=non_string_reason_runtime
        )

        self.assertEqual(non_string_text_extractor.extract(make_event()), [])
        self.assertEqual(non_string_reason_extractor.extract(make_event()), [])

    def test_extract_rejects_negative_polarity_without_negative_text_signal(self):
        from backend.services.llm_memory_extractor import LLMBackedViewerMemoryExtractor

        runtime = FakeRuntime(
            json.dumps(
                {
                    "should_extract": True,
                    "memory_text": "喜欢吃辣",
                    "memory_type": "preference",
                    "polarity": "negative",
                    "temporal_scope": "long_term",
                    "certainty": "high",
                    "reason": "长期口味偏好",
                },
                ensure_ascii=False,
            )
        )
        extractor = LLMBackedViewerMemoryExtractor(settings=SimpleNamespace(), runtime=runtime)

        self.assertEqual(extractor.extract(make_event(content="我不喜欢辣")), [])

    def test_extract_rejects_negative_polarity_for_ambiguous_words_like_wu_tang_or_te_bie(self):
        from backend.services.llm_memory_extractor import LLMBackedViewerMemoryExtractor

        runtime = FakeRuntime(
            json.dumps(
                {
                    "should_extract": True,
                    "memory_text": "特别喜欢无糖可乐",
                    "memory_type": "preference",
                    "polarity": "negative",
                    "temporal_scope": "long_term",
                    "certainty": "high",
                    "reason": "长期饮食偏好",
                },
                ensure_ascii=False,
            )
        )
        extractor = LLMBackedViewerMemoryExtractor(settings=SimpleNamespace(), runtime=runtime)

        self.assertEqual(extractor.extract(make_event(content="我喜欢无糖可乐")), [])

    def test_extract_accepts_negative_polarity_with_explicit_negative_phrase(self):
        from backend.services.llm_memory_extractor import LLMBackedViewerMemoryExtractor

        runtime = FakeRuntime(
            json.dumps(
                {
                    "should_extract": True,
                    "memory_text": "不喜欢辣",
                    "memory_type": "preference",
                    "polarity": "negative",
                    "temporal_scope": " LONG_TERM ",
                    "certainty": "high",
                    "reason": "长期口味偏好",
                },
                ensure_ascii=False,
            )
        )
        extractor = LLMBackedViewerMemoryExtractor(settings=SimpleNamespace(), runtime=runtime)

        self.assertEqual(
            extractor.extract(make_event(content="我不喜欢辣")),
            [{"memory_text": "不喜欢辣", "memory_type": "preference", "confidence": 0.86}],
        )

    def test_extract_rejects_should_extract_false_unknown_certainty_and_invalid_memory_type(self):
        from backend.services.llm_memory_extractor import LLMBackedViewerMemoryExtractor

        should_extract_false_runtime = FakeRuntime(
            json.dumps(
                {
                    "should_extract": False,
                    "memory_text": "喜欢喝无糖可乐",
                    "memory_type": "preference",
                    "polarity": "positive",
                    "temporal_scope": "long_term",
                    "certainty": "high",
                    "reason": "稳定偏好",
                },
                ensure_ascii=False,
            )
        )
        unknown_certainty_runtime = FakeRuntime(
            json.dumps(
                {
                    "should_extract": True,
                    "memory_text": "喜欢喝无糖可乐",
                    "memory_type": "preference",
                    "polarity": "positive",
                    "temporal_scope": "long_term",
                    "certainty": "unknown",
                    "reason": "稳定偏好",
                },
                ensure_ascii=False,
            )
        )
        invalid_memory_type_runtime = FakeRuntime(
            json.dumps(
                {
                    "should_extract": True,
                    "memory_text": "喜欢喝无糖可乐",
                    "memory_type": "plan",
                    "polarity": "positive",
                    "temporal_scope": "long_term",
                    "certainty": "high",
                    "reason": "稳定偏好",
                },
                ensure_ascii=False,
            )
        )

        should_extract_false_extractor = LLMBackedViewerMemoryExtractor(
            settings=SimpleNamespace(), runtime=should_extract_false_runtime
        )
        unknown_certainty_extractor = LLMBackedViewerMemoryExtractor(
            settings=SimpleNamespace(), runtime=unknown_certainty_runtime
        )
        invalid_memory_type_extractor = LLMBackedViewerMemoryExtractor(
            settings=SimpleNamespace(), runtime=invalid_memory_type_runtime
        )

        self.assertEqual(should_extract_false_extractor.extract(make_event()), [])
        self.assertEqual(unknown_certainty_extractor.extract(make_event()), [])
        self.assertEqual(invalid_memory_type_extractor.extract(make_event()), [])


class ViewerMemoryExtractorCompositeTests(unittest.TestCase):
    def test_composite_falls_back_to_rule_when_llm_raises(self):
        from backend.services.memory_extractor import ViewerMemoryExtractor

        llm_extractor = MagicMock()
        llm_extractor.extract.side_effect = RuntimeError("llm failed")
        rule_extractor = MagicMock()
        rule_extractor.extract.return_value = [{"memory_text": "我喜欢拉面", "memory_type": "preference", "confidence": 0.8}]
        extractor = ViewerMemoryExtractor(settings=None, llm_extractor=llm_extractor, rule_extractor=rule_extractor)

        with patch("backend.services.memory_extractor.logger") as logger_mock:
            result = extractor.extract(make_event(content="我喜欢拉面"))

        self.assertEqual(result, [{"memory_text": "我喜欢拉面", "memory_type": "preference", "confidence": 0.8}])
        llm_extractor.extract.assert_called_once()
        rule_extractor.extract.assert_called_once()
        logger_mock.exception.assert_called_once()

    def test_composite_falls_back_to_rule_when_llm_returns_empty(self):
        from backend.services.memory_extractor import ViewerMemoryExtractor

        llm_extractor = MagicMock()
        llm_extractor.extract.return_value = []
        rule_extractor = MagicMock()
        rule_extractor.extract.return_value = [{"memory_text": "我在杭州上班", "memory_type": "context", "confidence": 0.7}]
        extractor = ViewerMemoryExtractor(settings=None, llm_extractor=llm_extractor, rule_extractor=rule_extractor)

        result = extractor.extract(make_event(content="我在杭州上班"))

        self.assertEqual(result, [{"memory_text": "我在杭州上班", "memory_type": "context", "confidence": 0.7}])
        llm_extractor.extract.assert_called_once()
        rule_extractor.extract.assert_called_once()

    def test_composite_prefers_llm_candidates_over_rule_fallback(self):
        from backend.services.memory_extractor import ViewerMemoryExtractor

        llm_extractor = MagicMock()
        llm_extractor.extract.return_value = [{"memory_text": "不喜欢辣", "memory_type": "preference", "confidence": 0.86}]
        rule_extractor = MagicMock()
        rule_extractor.extract.return_value = [{"memory_text": "喜欢辣", "memory_type": "preference", "confidence": 0.6}]
        extractor = ViewerMemoryExtractor(settings=None, llm_extractor=llm_extractor, rule_extractor=rule_extractor)

        result = extractor.extract(make_event(content="我不喜欢辣"))

        self.assertEqual(result, [{"memory_text": "不喜欢辣", "memory_type": "preference", "confidence": 0.86}])
        llm_extractor.extract.assert_called_once()
        rule_extractor.extract.assert_not_called()


if __name__ == "__main__":
    unittest.main()
