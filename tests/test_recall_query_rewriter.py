import unittest

from backend.services.recall_query_rewriter import RecallQueryRewriter


class FakeClient:
    def __init__(self, response=None, exc=None):
        self.response = response
        self.exc = exc

    def infer_json(self, system_prompt, user_prompt):
        if self.exc:
            raise self.exc
        return self.response


class RecallQueryRewriterTests(unittest.TestCase):
    def test_rewrite_uses_llm_query_when_valid(self):
        service = RecallQueryRewriter(client=FakeClient('{"query_recall_text":"用户当前想吃面，召回饮食偏好、拉面、面条相关记忆"}'))

        result = service.rewrite("最近有点想吃面")

        self.assertEqual(result, "最近有点想吃面；用户当前想吃面，召回饮食偏好、拉面、面条相关记忆")

    def test_rewrite_falls_back_when_llm_fails(self):
        service = RecallQueryRewriter(client=FakeClient(exc=ValueError("down")))

        result = service.rewrite("今天不能吃太辣")

        self.assertIn("今天不能吃太辣", result)
        self.assertIn("吃辣", result)
        self.assertIn("忌口", result)

    def test_blank_query_returns_blank(self):
        self.assertEqual(RecallQueryRewriter().rewrite("  "), "")


if __name__ == "__main__":
    unittest.main()
