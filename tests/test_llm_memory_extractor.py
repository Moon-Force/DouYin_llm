import json
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock
from unittest.mock import patch

from backend.schemas.live import LiveEvent


def make_event(*, event_type="comment", content="我喜欢吃面", user=None):
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
    def test_system_prompt_includes_few_shot_examples_for_boundary_cases(self):
        from backend.services.llm_memory_extractor import LLMBackedViewerMemoryExtractor

        prompt = LLMBackedViewerMemoryExtractor(
            settings=SimpleNamespace(memory_extractor_prompt_variant="cot"),
            runtime=FakeRuntime("{}"),
        )._system_prompt()

        self.assertIn("少样本示例", prompt)
        self.assertIn("示例1：一直喝无糖可乐", prompt)
        self.assertIn("示例2：一点都不喜欢香菜", prompt)
        self.assertIn("示例3：在杭州做前端开发", prompt)
        self.assertIn("示例4：今晚下班准备去吃火锅", prompt)
        self.assertIn("示例5：来了哈哈哈", prompt)
        self.assertIn("示例6：这个多少钱，链接在哪", prompt)
        self.assertIn("在作答前请先在内部逐步思考", prompt)
        self.assertIn("不要暴露你的思考过程", prompt)
        self.assertNotIn("certainty", prompt)

    def test_system_prompt_includes_boundary_labeling_rules_and_new_examples(self):
        from backend.services.llm_memory_extractor import LLMBackedViewerMemoryExtractor

        prompt = LLMBackedViewerMemoryExtractor(
            settings=SimpleNamespace(memory_extractor_prompt_variant="cot"),
            runtime=FakeRuntime("{}"),
        )._system_prompt()

        self.assertIn("标注规则", prompt)
        self.assertIn("fact = 稳定客观事实", prompt)
        self.assertIn("context = 稳定背景信息", prompt)
        self.assertIn("preference = 明确的喜欢/不喜欢", prompt)
        self.assertIn("对猫毛过敏", prompt)
        self.assertIn("示例7：家里养了两只猫", prompt)
        self.assertIn("示例8：平时凌晨一点以后才睡", prompt)
        self.assertIn("示例9：一直都只用安卓手机", prompt)
        self.assertIn("示例10：不是不喜欢猫，只是对猫毛过敏", prompt)
        self.assertIn("示例16：现在在苏州带娃", prompt)
        self.assertIn("示例17：不是很能吃辣", prompt)
        self.assertIn("示例18：去年刚毕业，现在在做产品助理", prompt)

    def test_system_prompt_uses_prompt_variant_from_settings(self):
        from backend.services.llm_memory_extractor import LLMBackedViewerMemoryExtractor

        prompt = LLMBackedViewerMemoryExtractor(
            settings=SimpleNamespace(memory_extractor_prompt_variant="baseline"),
            runtime=FakeRuntime("{}"),
        )._system_prompt()

        self.assertNotIn("在作答前请先在内部逐步思考", prompt)

    def test_extract_returns_candidate_for_valid_long_term_preference_without_model_certainty(self):
        from backend.services.llm_memory_extractor import LLMBackedViewerMemoryExtractor

        runtime = FakeRuntime(
            json.dumps(
                {
                    "should_extract": True,
                    "memory_text": "喜欢喝无糖可乐",
                    "memory_type": "preference",
                    "polarity": "positive",
                    "temporal_scope": "long_term",
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

    def test_extract_assigns_context_confidence_in_code(self):
        from backend.services.llm_memory_extractor import LLMBackedViewerMemoryExtractor

        runtime = FakeRuntime(
            json.dumps(
                {
                    "should_extract": True,
                    "memory_text": "在杭州做前端开发",
                    "memory_type": "context",
                    "polarity": "neutral",
                    "temporal_scope": "long_term",
                    "reason": "稳定背景",
                },
                ensure_ascii=False,
            )
        )
        extractor = LLMBackedViewerMemoryExtractor(settings=SimpleNamespace(), runtime=runtime)

        result = extractor.extract(make_event(content="我在杭州做前端开发"))

        self.assertEqual(
            result,
            [{"memory_text": "在杭州做前端开发", "memory_type": "context", "confidence": 0.78}],
        )

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
                    "reason": "只对今晚有效",
                },
                ensure_ascii=False,
            )
        )
        extractor = LLMBackedViewerMemoryExtractor(settings=SimpleNamespace(), runtime=runtime)

        self.assertEqual(extractor.extract(make_event(content="今晚加班")), [])

    def test_extract_raises_json_decode_error_for_invalid_json(self):
        from backend.services.llm_memory_extractor import LLMBackedViewerMemoryExtractor

        extractor = LLMBackedViewerMemoryExtractor(settings=SimpleNamespace(), runtime=FakeRuntime("{"))

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
                    "reason": "明确长期口味偏好",
                },
                ensure_ascii=False,
            )
        )
        extractor = LLMBackedViewerMemoryExtractor(settings=SimpleNamespace(), runtime=runtime)

        self.assertEqual(
            extractor.extract(make_event(content="我不喜欢辣")),
            [{"memory_text": "不喜欢辣", "memory_type": "preference", "confidence": 0.86}],
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
                    "reason": "   ",
                },
                ensure_ascii=False,
            )
        )

        self.assertEqual(
            LLMBackedViewerMemoryExtractor(settings=SimpleNamespace(), runtime=missing_reason_runtime).extract(
                make_event()
            ),
            [],
        )
        self.assertEqual(
            LLMBackedViewerMemoryExtractor(settings=SimpleNamespace(), runtime=empty_reason_runtime).extract(
                make_event()
            ),
            [],
        )

    def test_extract_rejects_non_dict_payload(self):
        from backend.services.llm_memory_extractor import LLMBackedViewerMemoryExtractor

        self.assertEqual(
            LLMBackedViewerMemoryExtractor(settings=SimpleNamespace(), runtime=FakeRuntime("[]")).extract(make_event()),
            [],
        )
        self.assertEqual(
            LLMBackedViewerMemoryExtractor(settings=SimpleNamespace(), runtime=FakeRuntime("1")).extract(make_event()),
            [],
        )

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
                    "reason": "稳定偏好",
                },
                ensure_ascii=False,
            )
        )

        self.assertEqual(
            LLMBackedViewerMemoryExtractor(settings=SimpleNamespace(), runtime=invalid_value_runtime).extract(
                make_event()
            ),
            [],
        )
        self.assertEqual(
            LLMBackedViewerMemoryExtractor(settings=SimpleNamespace(), runtime=non_string_runtime).extract(
                make_event()
            ),
            [],
        )

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
                    "reason": 123,
                },
                ensure_ascii=False,
            )
        )

        self.assertEqual(
            LLMBackedViewerMemoryExtractor(settings=SimpleNamespace(), runtime=non_string_text_runtime).extract(
                make_event()
            ),
            [],
        )
        self.assertEqual(
            LLMBackedViewerMemoryExtractor(settings=SimpleNamespace(), runtime=non_string_reason_runtime).extract(
                make_event()
            ),
            [],
        )

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
                    "reason": "长期口味偏好",
                },
                ensure_ascii=False,
            )
        )
        extractor = LLMBackedViewerMemoryExtractor(settings=SimpleNamespace(), runtime=runtime)

        self.assertEqual(extractor.extract(make_event(content="我不喜欢辣")), [])

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

    def test_extract_rejects_should_extract_false_and_invalid_memory_type(self):
        from backend.services.llm_memory_extractor import LLMBackedViewerMemoryExtractor

        should_extract_false_runtime = FakeRuntime(
            json.dumps(
                {
                    "should_extract": False,
                    "memory_text": "喜欢喝无糖可乐",
                    "memory_type": "preference",
                    "polarity": "positive",
                    "temporal_scope": "long_term",
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
                    "reason": "稳定偏好",
                },
                ensure_ascii=False,
            )
        )

        self.assertEqual(
            LLMBackedViewerMemoryExtractor(settings=SimpleNamespace(), runtime=should_extract_false_runtime).extract(
                make_event()
            ),
            [],
        )
        self.assertEqual(
            LLMBackedViewerMemoryExtractor(settings=SimpleNamespace(), runtime=invalid_memory_type_runtime).extract(
                make_event()
            ),
            [],
        )


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
