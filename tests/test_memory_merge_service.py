import unittest
from types import SimpleNamespace


def build_memory(
    *,
    memory_id,
    memory_text,
    memory_type="preference",
    confidence=0.8,
):
    return SimpleNamespace(
        memory_id=memory_id,
        memory_text=memory_text,
        memory_type=memory_type,
        confidence=confidence,
    )


class ViewerMemoryMergeServiceTests(unittest.TestCase):
    def test_decide_merge_when_canonical_text_matches(self):
        from backend.services.memory_merge_service import ViewerMemoryMergeService

        service = ViewerMemoryMergeService(similarity_threshold=0.88, supersede_threshold=0.82)
        incoming = {
            "memory_text": "喜欢拉面",
            "memory_text_raw": "我喜欢拉面",
            "memory_text_canonical": "喜欢拉面",
            "memory_type": "preference",
            "confidence": 0.86,
        }
        existing = [build_memory(memory_id="mem-1", memory_text="喜欢拉面")]

        decision = service.decide(incoming, existing, similar_memories=[])

        self.assertEqual(decision.action, "merge")
        self.assertEqual(decision.target_memory_id, "mem-1")

    def test_decide_upgrade_when_incoming_is_more_specific(self):
        from backend.services.memory_merge_service import ViewerMemoryMergeService

        service = ViewerMemoryMergeService(similarity_threshold=0.88, supersede_threshold=0.82)
        incoming = {
            "memory_text": "喜欢豚骨拉面",
            "memory_text_raw": "我超爱豚骨拉面",
            "memory_text_canonical": "喜欢豚骨拉面",
            "memory_type": "preference",
            "confidence": 0.86,
        }
        existing = [build_memory(memory_id="mem-1", memory_text="喜欢拉面")]
        similar_memories = [{"memory_id": "mem-1", "memory_text": "喜欢拉面", "score": 0.91, "metadata": {}}]

        decision = service.decide(incoming, existing, similar_memories=similar_memories)

        self.assertEqual(decision.action, "upgrade")
        self.assertEqual(decision.target_memory_id, "mem-1")

    def test_decide_supersede_when_direction_conflicts(self):
        from backend.services.memory_merge_service import ViewerMemoryMergeService

        service = ViewerMemoryMergeService(similarity_threshold=0.88, supersede_threshold=0.82)
        incoming = {
            "memory_text": "不太能吃辣",
            "memory_text_raw": "我平时不太能吃辣",
            "memory_text_canonical": "不太能吃辣",
            "memory_type": "preference",
            "confidence": 0.86,
        }
        existing = [build_memory(memory_id="mem-1", memory_text="喜欢吃辣")]
        similar_memories = [{"memory_id": "mem-1", "memory_text": "喜欢吃辣", "score": 0.84, "metadata": {}}]

        decision = service.decide(incoming, existing, similar_memories=similar_memories)

        self.assertEqual(decision.action, "supersede")
        self.assertEqual(decision.target_memory_id, "mem-1")

    def test_decide_create_when_no_close_match_exists(self):
        from backend.services.memory_merge_service import ViewerMemoryMergeService

        service = ViewerMemoryMergeService(similarity_threshold=0.88, supersede_threshold=0.82)
        incoming = {
            "memory_text": "租房住在公司附近",
            "memory_text_raw": "我租房住在公司附近",
            "memory_text_canonical": "租房住在公司附近",
            "memory_type": "context",
            "confidence": 0.78,
        }
        existing = [build_memory(memory_id="mem-1", memory_text="家里养了两只猫", memory_type="fact")]

        decision = service.decide(incoming, existing, similar_memories=[])

        self.assertEqual(decision.action, "create")
        self.assertEqual(decision.target_memory_id, "")


if __name__ == "__main__":
    unittest.main()
