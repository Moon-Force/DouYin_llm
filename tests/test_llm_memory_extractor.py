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


def llm_payload(
    *,
    should_extract=True,
    raw="我其实平时吧都不太能吃辣",
    canonical="不太能吃辣",
    memory_type="preference",
    polarity="negative",
    temporal_scope="long_term",
    reason="稳定饮食限制，对后续推荐有复用价值",
):
    return {
        "should_extract": should_extract,
        "memory_text_raw": raw,
        "memory_text_canonical": canonical,
        "memory_type": memory_type,
        "polarity": polarity,
        "temporal_scope": temporal_scope,
        "reason": reason,
    }


class FakeRuntime:
    def __init__(self, payload):
        self.payload = payload
        self.calls = []

    def infer_json(self, system_prompt, user_prompt):
        self.calls.append((system_prompt, user_prompt))
        return self.payload


class LLMBackedViewerMemoryExtractorTests(unittest.TestCase):
    def test_system_prompt_mentions_dual_fields_and_refinement_rules(self):
        from backend.services.llm_memory_extractor import LLMBackedViewerMemoryExtractor

        prompt = LLMBackedViewerMemoryExtractor(
            settings=SimpleNamespace(memory_extractor_prompt_variant="cot"),
            runtime=FakeRuntime("{}"),
        )._system_prompt()

        self.assertIn("memory_text_raw", prompt)
        self.assertIn("memory_text_canonical", prompt)
        self.assertIn("最小可复用表达", prompt)
        self.assertIn("不要暴露思考过程", prompt)

    def test_system_prompt_uses_prompt_variant_from_settings(self):
        from backend.services.llm_memory_extractor import LLMBackedViewerMemoryExtractor

        prompt = LLMBackedViewerMemoryExtractor(
            settings=SimpleNamespace(memory_extractor_prompt_variant="baseline"),
            runtime=FakeRuntime("{}"),
        )._system_prompt()

        self.assertNotIn("不要暴露思考过程", prompt)

    def test_extract_returns_candidate_with_raw_and_canonical_fields(self):
        from backend.services.llm_memory_extractor import LLMBackedViewerMemoryExtractor

        runtime = FakeRuntime(
            json.dumps(
                llm_payload(
                    raw="我平时很少吃外卖，基本都是自己做饭",
                    canonical="平时很少吃外卖，基本自己做饭",
                    memory_type="fact",
                    polarity="neutral",
                    reason="稳定生活方式事实，对后续互动有复用价值",
                ),
                ensure_ascii=False,
            )
        )
        extractor = LLMBackedViewerMemoryExtractor(settings=SimpleNamespace(), runtime=runtime)

        result = extractor.extract(make_event(content="我平时很少吃外卖，基本都是自己做饭"))

        self.assertEqual(
            result,
            [
                {
                    "memory_text": "平时很少吃外卖，基本自己做饭",
                    "memory_text_raw": "我平时很少吃外卖，基本都是自己做饭",
                    "memory_text_canonical": "平时很少吃外卖，基本自己做饭",
                    "memory_type": "fact",
                    "polarity": "neutral",
                    "temporal_scope": "long_term",
                    "confidence": 0.74,
                    "extraction_source": "llm",
                }
            ],
        )
        self.assertEqual(len(runtime.calls), 1)
        prompt_payload = json.loads(runtime.calls[0][1])
        self.assertEqual(prompt_payload["event"]["room_id"], "room-1")
        self.assertEqual(prompt_payload["event"]["viewer_id"], "id:user-1")

    def test_extract_rejects_short_term_candidate(self):
        from backend.services.llm_memory_extractor import LLMBackedViewerMemoryExtractor

        runtime = FakeRuntime(
            json.dumps(
                llm_payload(
                    raw="这周我都在上海出差",
                    canonical="都在上海出差",
                    memory_type="context",
                    polarity="neutral",
                    temporal_scope="short_term",
                    reason="短期状态",
                ),
                ensure_ascii=False,
            )
        )
        extractor = LLMBackedViewerMemoryExtractor(settings=SimpleNamespace(), runtime=runtime)

        self.assertEqual(extractor.extract(make_event(content="这周我都在上海出差")), [])

    def test_extract_rejects_missing_canonical_text(self):
        from backend.services.llm_memory_extractor import LLMBackedViewerMemoryExtractor

        runtime = FakeRuntime(
            json.dumps(
                llm_payload(canonical="   "),
                ensure_ascii=False,
            )
        )
        extractor = LLMBackedViewerMemoryExtractor(settings=SimpleNamespace(), runtime=runtime)

        self.assertEqual(extractor.extract(make_event()), [])

    def test_extract_rejects_interaction_shell_canonical_text(self):
        from backend.services.llm_memory_extractor import LLMBackedViewerMemoryExtractor

        runtime = FakeRuntime(
            json.dumps(
                llm_payload(raw="我是不是不能吃辣", canonical="是不是不能吃辣"),
                ensure_ascii=False,
            )
        )
        extractor = LLMBackedViewerMemoryExtractor(settings=SimpleNamespace(), runtime=runtime)

        self.assertEqual(extractor.extract(make_event(content="我是不是不能吃辣")), [])

    def test_extract_rejects_guess_name_interaction_shell(self):
        from backend.services.llm_memory_extractor import LLMBackedViewerMemoryExtractor

        runtime = FakeRuntime(
            json.dumps(
                llm_payload(
                    raw="主播猜猜我的名字",
                    canonical="主播猜猜我的名字",
                    memory_type="fact",
                    polarity="neutral",
                    reason="互动问句",
                ),
                ensure_ascii=False,
            )
        )
        extractor = LLMBackedViewerMemoryExtractor(settings=SimpleNamespace(), runtime=runtime)

        self.assertEqual(extractor.extract(make_event(content="主播猜猜我的名字")), [])

    def test_extract_rejects_negative_polarity_without_negative_signal(self):
        from backend.services.llm_memory_extractor import LLMBackedViewerMemoryExtractor

        runtime = FakeRuntime(
            json.dumps(
                llm_payload(
                    raw="我喜欢吃辣",
                    canonical="喜欢吃辣",
                    polarity="negative",
                ),
                ensure_ascii=False,
            )
        )
        extractor = LLMBackedViewerMemoryExtractor(settings=SimpleNamespace(), runtime=runtime)

        self.assertEqual(extractor.extract(make_event(content="我喜欢吃辣")), [])

    def test_extract_returns_empty_for_non_comment_empty_content_or_missing_viewer(self):
        from backend.services.llm_memory_extractor import LLMBackedViewerMemoryExtractor

        runtime = FakeRuntime(json.dumps(llm_payload(), ensure_ascii=False))
        extractor = LLMBackedViewerMemoryExtractor(settings=SimpleNamespace(), runtime=runtime)

        non_comment = make_event(event_type="gift", content="")
        empty_content = make_event(content="   ")
        no_viewer = make_event(content="我喜欢面", user={"id": "", "short_id": "", "sec_uid": "", "nickname": "   "})

        self.assertEqual(extractor.extract(non_comment), [])
        self.assertEqual(extractor.extract(empty_content), [])
        self.assertEqual(extractor.extract(no_viewer), [])
        self.assertEqual(runtime.calls, [])

    def test_extract_raises_json_decode_error_for_invalid_json(self):
        from backend.services.llm_memory_extractor import LLMBackedViewerMemoryExtractor

        extractor = LLMBackedViewerMemoryExtractor(settings=SimpleNamespace(), runtime=FakeRuntime("{"))

        with self.assertRaises(json.JSONDecodeError):
            extractor.extract(make_event())


class ViewerMemoryExtractorCompositeTests(unittest.TestCase):
    def test_composite_short_circuits_obvious_noise_without_calling_extractors(self):
        from backend.services.memory_extractor import ViewerMemoryExtractor

        llm_extractor = MagicMock()
        rule_extractor = MagicMock()
        extractor = ViewerMemoryExtractor(settings=None, llm_extractor=llm_extractor, rule_extractor=rule_extractor)

        for content in ("来了", "哈哈哈哈", "支持主播", "多少钱", "链接在哪"):
            with self.subTest(content=content):
                self.assertEqual(extractor.extract(make_event(content=content)), [])

        llm_extractor.extract.assert_not_called()
        rule_extractor.extract.assert_not_called()
        metadata = extractor.consume_last_extraction_metadata()
        self.assertTrue(metadata["memory_prefiltered"])

    def test_composite_records_refined_metadata_when_llm_succeeds(self):
        from backend.services.memory_extractor import ViewerMemoryExtractor

        llm_extractor = MagicMock()
        llm_extractor.extract.return_value = [
            {
                "memory_text": "租房住在公司附近",
                "memory_text_raw": "我租房住在公司附近，这样通勤方便点",
                "memory_text_canonical": "租房住在公司附近",
                "memory_type": "context",
                "confidence": 0.78,
                "extraction_source": "llm",
            }
        ]
        rule_extractor = MagicMock()
        extractor = ViewerMemoryExtractor(settings=None, llm_extractor=llm_extractor, rule_extractor=rule_extractor)

        result = extractor.extract(make_event(content="我租房住在公司附近，这样通勤方便点"))

        self.assertEqual(result[0]["memory_text"], "租房住在公司附近")
        llm_extractor.extract.assert_called_once()
        rule_extractor.extract.assert_not_called()
        metadata = extractor.consume_last_extraction_metadata()
        self.assertTrue(metadata["memory_llm_attempted"])
        self.assertTrue(metadata["memory_refined"])
        self.assertFalse(metadata["fallback_used"])

    def test_composite_prefilters_question_like_comment_before_llm(self):
        from backend.services.memory_extractor import ViewerMemoryExtractor

        llm_extractor = MagicMock()
        rule_extractor = MagicMock()
        extractor = ViewerMemoryExtractor(settings=None, llm_extractor=llm_extractor, rule_extractor=rule_extractor)

        result = extractor.extract(make_event(content="主播猜猜我的名字"))

        self.assertEqual(result, [])
        llm_extractor.extract.assert_not_called()
        rule_extractor.extract.assert_not_called()
        metadata = extractor.consume_last_extraction_metadata()
        self.assertTrue(metadata["memory_prefiltered"])

    def test_composite_does_not_fallback_when_llm_returns_empty(self):
        from backend.services.memory_extractor import ViewerMemoryExtractor

        llm_extractor = MagicMock()
        llm_extractor.extract.return_value = []
        rule_extractor = MagicMock()
        extractor = ViewerMemoryExtractor(settings=None, llm_extractor=llm_extractor, rule_extractor=rule_extractor)

        result = extractor.extract(make_event(content="我在杭州上班"))

        self.assertEqual(result, [])
        llm_extractor.extract.assert_called_once()
        rule_extractor.extract.assert_not_called()
        metadata = extractor.consume_last_extraction_metadata()
        self.assertTrue(metadata["memory_llm_attempted"])
        self.assertFalse(metadata["fallback_used"])

    def test_composite_uses_high_confidence_rule_fallback_only_when_llm_raises(self):
        from backend.services.memory_extractor import ViewerMemoryExtractor

        llm_extractor = MagicMock()
        llm_extractor.extract.side_effect = RuntimeError("llm failed")
        rule_extractor = MagicMock()
        rule_extractor.extract_high_confidence.return_value = [
            {
                "memory_text": "我在杭州上班",
                "memory_text_raw": "我在杭州上班",
                "memory_text_canonical": "我在杭州上班",
                "memory_type": "context",
                "confidence": 0.88,
                "extraction_source": "rule_fallback",
            }
        ]
        extractor = ViewerMemoryExtractor(settings=None, llm_extractor=llm_extractor, rule_extractor=rule_extractor)

        with patch("backend.services.memory_extractor.logger") as logger_mock:
            result = extractor.extract(make_event(content="我在杭州上班"))

        self.assertEqual(result[0]["memory_text"], "我在杭州上班")
        llm_extractor.extract.assert_called_once()
        rule_extractor.extract_high_confidence.assert_called_once()
        logger_mock.exception.assert_called_once()
        metadata = extractor.consume_last_extraction_metadata()
        self.assertTrue(metadata["memory_llm_attempted"])
        self.assertTrue(metadata["fallback_used"])

    def test_composite_does_not_use_rule_fallback_when_llm_returns_empty(self):
        from backend.services.memory_extractor import ViewerMemoryExtractor

        llm_extractor = MagicMock()
        llm_extractor.extract.return_value = []
        rule_extractor = MagicMock()
        extractor = ViewerMemoryExtractor(settings=None, llm_extractor=llm_extractor, rule_extractor=rule_extractor)

        result = extractor.extract(make_event(content="我在杭州上班"))

        self.assertEqual(result, [])
        llm_extractor.extract.assert_called_once()
        rule_extractor.extract_high_confidence.assert_not_called()
        rule_extractor.extract.assert_not_called()

    def test_rule_fallback_rejects_question_like_content(self):
        from backend.services.memory_extractor import RuleFallbackMemoryExtractor

        extractor = RuleFallbackMemoryExtractor()

        result = extractor.extract_high_confidence(make_event(content="我是不是不太能吃辣？"))

        self.assertEqual(result, [])

    def test_rule_fallback_general_extract_rejects_name_guess_question(self):
        from backend.services.memory_extractor import RuleFallbackMemoryExtractor

        extractor = RuleFallbackMemoryExtractor()

        result = extractor.extract(
            make_event(content="\u4e3b\u64ad\uff0c\u4f60\u731c\u731c\u6211\u7684\u540d\u5b57\u53eb\u4ec0\u4e48\uff1f")
        )

        self.assertEqual(result, [])

    def test_rule_fallback_accepts_clear_negative_food_constraint(self):
        from backend.services.memory_extractor import RuleFallbackMemoryExtractor

        extractor = RuleFallbackMemoryExtractor()

        result = extractor.extract_high_confidence(make_event(content="我不太能吃辣"))

        self.assertEqual(result[0]["memory_type"], "preference")

    def test_rule_fallback_accepts_clear_negative_preference(self):
        from backend.services.memory_extractor import RuleFallbackMemoryExtractor

        extractor = RuleFallbackMemoryExtractor()

        result = extractor.extract_high_confidence(make_event(content="我不喜欢香菜"))

        self.assertEqual(result[0]["memory_type"], "preference")

    def test_rule_fallback_accepts_clear_stable_job_pattern(self):
        from backend.services.memory_extractor import RuleFallbackMemoryExtractor

        extractor = RuleFallbackMemoryExtractor()

        result = extractor.extract_high_confidence(make_event(content="我在杭州做前端开发"))

        self.assertEqual(result[0]["memory_type"], "context")

    def test_rule_fallback_canonicalizes_food_constraint(self):
        from backend.services.memory_extractor import RuleFallbackMemoryExtractor

        extractor = RuleFallbackMemoryExtractor()

        result = extractor.extract_high_confidence(make_event(content="我其实吧不太能吃辣"))

        self.assertEqual(result[0]["memory_text_raw"], "我其实吧不太能吃辣")
        self.assertEqual(result[0]["memory_text_canonical"], "不太能吃辣")

    def test_rule_fallback_canonicalizes_context_without_tail_explanation(self):
        from backend.services.memory_extractor import RuleFallbackMemoryExtractor

        extractor = RuleFallbackMemoryExtractor()

        result = extractor.extract_high_confidence(make_event(content="我租房住在公司附近，这样通勤方便点"))

        self.assertEqual(result[0]["memory_text_canonical"], "租房住在公司附近")

    def test_rule_fallback_marks_negative_food_constraint_as_negative(self):
        from backend.services.memory_extractor import RuleFallbackMemoryExtractor

        extractor = RuleFallbackMemoryExtractor()

        result = extractor.extract_high_confidence(make_event(content="我不太能吃辣"))

        self.assertEqual(result[0]["polarity"], "negative")


class InteractiveQuestionRegressionTests(unittest.TestCase):
    def test_llm_normalizer_rejects_guess_name_question_variants(self):
        from backend.services.llm_memory_extractor import LLMBackedViewerMemoryExtractor

        cases = (
            ("主播猜猜我的名字", "主播猜猜我的名字"),
            ("主播猜猜我的名字叫啥", "主播猜猜我的名字"),
            ("主播猜猜我的名字叫什么？", "主播猜猜我的名字"),
        )

        for raw_text, canonical_text in cases:
            with self.subTest(raw_text=raw_text, canonical_text=canonical_text):
                runtime = FakeRuntime(
                    json.dumps(
                        llm_payload(
                            raw=raw_text,
                            canonical=canonical_text,
                            memory_type="fact",
                            polarity="neutral",
                            reason="互动问句",
                        ),
                        ensure_ascii=False,
                    )
                )
                extractor = LLMBackedViewerMemoryExtractor(settings=SimpleNamespace(), runtime=runtime)
                self.assertEqual(extractor.extract(make_event(content=raw_text)), [])

    def test_composite_prefilters_guess_name_question_variants_before_llm(self):
        from backend.services.memory_extractor import ViewerMemoryExtractor

        llm_extractor = MagicMock()
        rule_extractor = MagicMock()
        extractor = ViewerMemoryExtractor(settings=None, llm_extractor=llm_extractor, rule_extractor=rule_extractor)

        for content in ("主播猜猜我的名字", "主播猜猜我的名字叫啥", "主播猜猜我的名字叫什么？"):
            with self.subTest(content=content):
                result = extractor.extract(make_event(content=content))
                self.assertEqual(result, [])
                metadata = extractor.consume_last_extraction_metadata()
                self.assertTrue(metadata["memory_prefiltered"])

        llm_extractor.extract.assert_not_called()
        rule_extractor.extract.assert_not_called()


if __name__ == "__main__":
    unittest.main()
