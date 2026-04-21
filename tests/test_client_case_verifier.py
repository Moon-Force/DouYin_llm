from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock
from unittest.mock import patch

from tests.memory_pipeline_verifier.runner import normalize_task
from tests.memory_pipeline_verifier.runner import _run_client_case_verification_internal
from tests.memory_pipeline_verifier.runner import run_client_case_verification
from tests.memory_pipeline_verifier.datasets import load_client_case_fixture


class ClientCaseVerifierTests(unittest.TestCase):
    def test_normalize_task_accepts_client_cases(self):
        self.assertEqual(normalize_task("client-cases"), "client-cases")

    def test_load_client_case_fixture_returns_cases_with_history_and_followup_events(self):
        cases = load_client_case_fixture(Path("tests/fixtures/client_memory_cases.json"))

        self.assertEqual(len(cases), 20)
        first_case = cases[0]
        self.assertIn("label", first_case)
        self.assertIn("history_event", first_case)
        self.assertIn("followup_event", first_case)
        self.assertEqual(first_case["history_event"]["event_type"], "comment")
        self.assertEqual(first_case["followup_event"]["event_type"], "comment")
        self.assertTrue(first_case["history_event"]["user"]["id"].strip())
        self.assertTrue(first_case["followup_event"]["user"]["nickname"].strip())
        self.assertLess(first_case["history_event"]["ts"], first_case["followup_event"]["ts"])

    def test_run_client_case_verification_reports_summary_counts(self):
        fake_cases = [
            {
                "label": "程序员+加班",
                "history_event": {
                    "event_id": "evt-1",
                    "room_id": "room-1",
                    "source_room_id": "room-1",
                    "session_id": "session-1",
                    "platform": "douyin",
                    "event_type": "comment",
                    "method": "WebcastChatMessage",
                    "livename": "live-room",
                    "ts": 1710000000000,
                    "user": {"id": "viewer-1", "nickname": "观众A"},
                    "content": "刚下班，今天 bug 修到 10 点",
                    "metadata": {},
                    "raw": {},
                },
                "followup_event": {
                    "event_id": "evt-2",
                    "room_id": "room-1",
                    "source_room_id": "room-1",
                    "session_id": "session-2",
                    "platform": "douyin",
                    "event_type": "comment",
                    "method": "WebcastChatMessage",
                    "livename": "live-room",
                    "ts": 1715184000000,
                    "user": {"id": "viewer-1", "nickname": "观众A"},
                    "content": "又要改需求了",
                    "metadata": {},
                    "raw": {},
                },
                "expected": {
                    "history_should_extract": True,
                    "followup_should_recall": True,
                    "suggestion_should_generate": True,
                },
            }
        ]

        fake_result = {
            "summary": {
                "case_count": 1,
                "history_extract_success": 1,
                "follow_recall_success": 1,
                "suggestion_success": 1,
            },
            "cases": [
                {
                    "label": "程序员+加班",
                    "history_extracted_count": 1,
                    "follow_recalled_count": 1,
                    "suggestion_generated": True,
                }
            ],
        }

        with tempfile.TemporaryDirectory(prefix="client-cases-") as tempdir:
            with patch(
                "tests.memory_pipeline_verifier.runner.load_client_case_fixture",
                return_value=fake_cases,
            ), patch(
                "tests.memory_pipeline_verifier.runner._run_client_case_verification_internal",
                return_value=fake_result,
            ):
                results, report = run_client_case_verification(
                    "tests/fixtures/client_memory_cases.json",
                    report_dir=Path(tempdir),
                )

        self.assertEqual(results[0].name, "dataset")
        self.assertEqual(results[1].name, "client_cases")
        self.assertTrue(results[1].ok)
        self.assertIn("cases=1", results[1].details)
        self.assertEqual(report["summary"]["follow_recall_success"], 1)

    def test_internal_client_case_verification_does_not_pass_history_as_recent_events(self):
        case = {
            "label": "dev-overtime",
            "history_event": {
                "event_id": "evt-1",
                "room_id": "room-1",
                "source_room_id": "room-1",
                "session_id": "session-1",
                "platform": "douyin",
                "event_type": "comment",
                "method": "WebcastChatMessage",
                "livename": "live-room",
                "ts": 1710000000000,
                "user": {"id": "viewer-1", "nickname": "viewer-a"},
                "content": "worked late fixing bugs",
                "metadata": {},
                "raw": {},
            },
            "followup_event": {
                "event_id": "evt-2",
                "room_id": "room-1",
                "source_room_id": "room-1",
                "session_id": "session-2",
                "platform": "douyin",
                "event_type": "comment",
                "method": "WebcastChatMessage",
                "livename": "live-room",
                "ts": 1715184000000,
                "user": {"id": "viewer-1", "nickname": "viewer-a"},
                "content": "requirements changed again",
                "metadata": {},
                "raw": {},
            },
            "expected": {
                "history_should_extract": True,
                "followup_should_recall": True,
                "suggestion_should_generate": True,
            },
        }
        captured = {"recent_events": None}

        class FakeAgent:
            def __init__(self, *args, **kwargs):
                pass

            def build_context(self, event, recent_events, current_comment_memories=None):
                captured["recent_events"] = list(recent_events)
                return {
                    "viewer_memories": [],
                    "viewer_memory_texts": [],
                    "recalled_memory_ids": [],
                    "current_comment_memories": [],
                    "current_comment_memory_texts": [],
                    "recent_events": [],
                    "user_profile": {},
                }

            def maybe_generate(self, event, recent_events, current_comment_memories=None):
                captured["recent_events"] = list(recent_events)
                return SimpleNamespace(
                    source="model",
                    reply_text="ok",
                    references=[],
                )

            def consume_last_generation_metadata(self):
                return {"recalled_memory_ids": []}

        with patch("tests.memory_pipeline_verifier.runner.EmbeddingService", return_value=MagicMock()), patch(
            "tests.memory_pipeline_verifier.runner.LongTermStore"
        ) as store_cls, patch(
            "tests.memory_pipeline_verifier.runner.VectorMemory", return_value=MagicMock()
        ), patch(
            "tests.memory_pipeline_verifier.runner.MemoryExtractorClient", return_value=MagicMock()
        ), patch(
            "tests.memory_pipeline_verifier.runner.LLMBackedViewerMemoryExtractor", return_value=MagicMock()
        ), patch(
            "tests.memory_pipeline_verifier.runner.ViewerMemoryExtractor"
        ) as extractor_cls, patch(
            "tests.memory_pipeline_verifier.runner.LivePromptAgent", FakeAgent
        ), patch(
            "tests.memory_pipeline_verifier.runner.MemoryConfidenceService", return_value=MagicMock()
        ):
            store_cls.return_value = MagicMock()
            fake_extractor = MagicMock()
            fake_extractor.extract.return_value = []
            extractor_cls.return_value = fake_extractor

            report = _run_client_case_verification_internal([case])

        self.assertEqual(captured["recent_events"], [])
        self.assertEqual(report["summary"]["case_count"], 1)


if __name__ == "__main__":
    unittest.main()
