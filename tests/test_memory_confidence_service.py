import unittest


class MemoryConfidenceServiceTests(unittest.TestCase):
    def test_score_new_memory_prefers_long_term_food_restriction_over_short_term_status(self):
        from backend.services.memory_confidence_service import MemoryConfidenceService

        service = MemoryConfidenceService()

        stable = service.score_new_memory(
            {
                "memory_text": "不太能吃辣",
                "memory_text_raw": "我平时都不太能吃辣",
                "memory_text_canonical": "不太能吃辣",
                "memory_type": "preference",
                "temporal_scope": "long_term",
            }
        )
        short_term = service.score_new_memory(
            {
                "memory_text": "这周都在上海出差",
                "memory_text_raw": "这周我都在上海出差",
                "memory_text_canonical": "这周都在上海出差",
                "memory_type": "context",
                "temporal_scope": "short_term",
            }
        )

        self.assertGreater(stable["stability_score"], short_term["stability_score"])
        self.assertGreater(stable["confidence"], short_term["confidence"])

    def test_score_new_memory_rewards_clear_short_canonical(self):
        from backend.services.memory_confidence_service import MemoryConfidenceService

        service = MemoryConfidenceService()

        concise = service.score_new_memory(
            {
                "memory_text": "租房住在公司附近",
                "memory_text_raw": "我租房住在公司附近，这样通勤方便点",
                "memory_text_canonical": "租房住在公司附近",
                "memory_type": "context",
                "temporal_scope": "long_term",
            }
        )
        noisy = service.score_new_memory(
            {
                "memory_text": "我其实是租房住在公司附近这样通勤方便一点",
                "memory_text_raw": "我其实是租房住在公司附近这样通勤方便一点",
                "memory_text_canonical": "我其实是租房住在公司附近这样通勤方便一点",
                "memory_type": "context",
                "temporal_scope": "long_term",
            }
        )

        self.assertGreater(concise["clarity_score"], noisy["clarity_score"])

    def test_score_existing_memory_update_increases_evidence_score_after_merge(self):
        from backend.services.memory_confidence_service import MemoryConfidenceService

        service = MemoryConfidenceService()
        memory = type(
            "Memory",
            (),
            {
                "memory_text": "不太能吃辣",
                "memory_type": "preference",
                "evidence_count": 1,
                "last_confirmed_at": 100,
                "stability_score": 0.9,
                "interaction_value_score": 0.9,
                "clarity_score": 0.8,
                "evidence_score": 0.35,
            },
        )()

        updated = service.score_existing_memory_update(memory, evidence_increment=1)

        self.assertGreater(updated["evidence_score"], 0.35)

    def test_score_new_memory_caps_rule_fallback_quality(self):
        from backend.services.memory_confidence_service import MemoryConfidenceService

        service = MemoryConfidenceService()

        llm_like = service.score_new_memory(
            {
                "memory_text": "不太能吃辣",
                "memory_text_raw": "我平时都不太能吃辣",
                "memory_text_canonical": "不太能吃辣",
                "memory_type": "preference",
                "temporal_scope": "long_term",
                "extraction_source": "llm",
            }
        )
        fallback_like = service.score_new_memory(
            {
                "memory_text": "不太能吃辣",
                "memory_text_raw": "我平时都不太能吃辣",
                "memory_text_canonical": "不太能吃辣",
                "memory_type": "preference",
                "temporal_scope": "long_term",
                "extraction_source": "rule_fallback",
            }
        )

        self.assertLess(fallback_like["confidence"], llm_like["confidence"])


if __name__ == "__main__":
    unittest.main()
