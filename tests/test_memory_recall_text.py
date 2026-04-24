import unittest

from backend.services.memory_recall_text import MemoryRecallTextService


class FakeClient:
    def __init__(self, response=None, exc=None):
        self.response = response
        self.exc = exc
        self.calls = []

    def infer_json(self, system_prompt, user_prompt):
        self.calls.append((system_prompt, user_prompt))
        if self.exc:
            raise self.exc
        return self.response


class MemoryRecallTextServiceTests(unittest.TestCase):
    def test_expand_memory_uses_llm_recall_text_when_valid(self):
        client = FakeClient('{"recall_text":"用户喜欢拉面，也可能提到面条、豚骨、日式汤面等相关饮食偏好。"}')
        service = MemoryRecallTextService(client=client)

        result = service.expand_memory(
            memory_text="喜欢拉面",
            raw_memory_text="我最喜欢吃豚骨拉面",
            memory_type="preference",
            polarity="neutral",
        )

        self.assertEqual(result, "用户喜欢拉面，也可能提到面条、豚骨、日式汤面等相关饮食偏好。")
        self.assertEqual(len(client.calls), 1)

    def test_expand_memory_falls_back_when_llm_fails(self):
        service = MemoryRecallTextService(client=FakeClient(exc=ValueError("down")))

        result = service.expand_memory(
            memory_text="不太能吃辣",
            raw_memory_text="我平时不太能吃辣",
            memory_type="preference",
            polarity="negative",
        )

        self.assertIn("不太能吃辣", result)
        self.assertIn("偏好", result)
        self.assertIn("负向", result)
        self.assertNotIn("type:", result)
        self.assertNotIn("polarity:", result)
        self.assertIn("我平时不太能吃辣", result)

    def test_expand_memory_rejects_unrelated_llm_output(self):
        service = MemoryRecallTextService(client=FakeClient('{"recall_text":"完全无关的购物车折扣信息"}'))

        result = service.expand_memory(
            memory_text="喜欢拉面",
            raw_memory_text="我最喜欢吃豚骨拉面",
            memory_type="preference",
        )

        self.assertIn("喜欢拉面", result)
        self.assertIn("我最喜欢吃豚骨拉面", result)


    def test_expand_memory_does_not_treat_face_cream_as_noodles(self):
        service = MemoryRecallTextService()

        result = service.expand_memory(
            memory_text="uses sensitive skin face cream",
            raw_memory_text="I only use sensitive skin face cream",
            memory_type="preference",
        )

        self.assertIn("护肤", result)
        self.assertNotIn("ramen", result)
        self.assertNotIn("noodles", result)


if __name__ == "__main__":
    unittest.main()
