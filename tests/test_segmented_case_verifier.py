from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tests.memory_pipeline_verifier.datasets import load_client_case_fixture
from tests.memory_pipeline_verifier.datasets import load_memory_extraction_fixture
from tests.memory_pipeline_verifier.datasets import load_recent_context_fixture
from tests.memory_pipeline_verifier.runner import normalize_task
from tests.memory_pipeline_verifier.runner import run_recent_context_verification


class SegmentedCaseVerifierTests(unittest.TestCase):
    def test_normalize_task_accepts_recent_context(self):
        self.assertEqual(normalize_task("recent-context"), "recent-context")

    def test_history_memory_extraction_fixture_has_thirty_cases(self):
        cases = load_memory_extraction_fixture(Path("tests/fixtures/history_memory_extraction_30.json"))

        self.assertEqual(len(cases), 30)

    def test_recent_context_fixture_has_thirty_expanded_cases(self):
        cases = load_recent_context_fixture(Path("tests/fixtures/recent_context_30.json"))

        self.assertEqual(len(cases), 30)
        first_case = cases[0]
        self.assertIn("recent_events", first_case)
        self.assertIn("current_event", first_case)
        self.assertGreaterEqual(len(first_case["recent_events"]), 2)
        self.assertEqual(first_case["current_event"]["event_type"], "comment")

    def test_hybrid_fixture_has_thirty_expanded_cases(self):
        cases = load_client_case_fixture(Path("tests/fixtures/hybrid_history_recent_30.json"))

        self.assertEqual(len(cases), 30)
        self.assertIn("history_event", cases[0])
        self.assertIn("followup_event", cases[0])

    def test_run_recent_context_verification_reports_summary_counts(self):
        fake_cases = [
            {
                "label": "程序员+最近发言",
                "recent_events": [
                    {
                        "event_id": "evt-r1",
                        "room_id": "room-1",
                        "source_room_id": "room-1",
                        "session_id": "session-1",
                        "platform": "douyin",
                        "event_type": "comment",
                        "method": "WebcastChatMessage",
                        "livename": "live-room",
                        "ts": 1710000000000,
                        "user": {"id": "viewer-1", "nickname": "观众A"},
                        "content": "今天又加班了",
                        "metadata": {},
                        "raw": {},
                    },
                    {
                        "event_id": "evt-r2",
                        "room_id": "room-1",
                        "source_room_id": "room-1",
                        "session_id": "session-1",
                        "platform": "douyin",
                        "event_type": "comment",
                        "method": "WebcastChatMessage",
                        "livename": "live-room",
                        "ts": 1710000001000,
                        "user": {"id": "viewer-1", "nickname": "观众A"},
                        "content": "刚改完一个 bug",
                        "metadata": {},
                        "raw": {},
                    },
                ],
                "current_event": {
                    "event_id": "evt-r3",
                    "room_id": "room-1",
                    "source_room_id": "room-1",
                    "session_id": "session-1",
                    "platform": "douyin",
                    "event_type": "comment",
                    "method": "WebcastChatMessage",
                    "livename": "live-room",
                    "ts": 1710000002000,
                    "user": {"id": "viewer-1", "nickname": "观众A"},
                    "content": "终于能下班了",
                    "metadata": {},
                    "raw": {},
                },
                "expected": {
                    "suggestion_should_generate": True,
                },
            }
        ]
        fake_report = {
            "summary": {
                "case_count": 1,
                "suggestion_success": 1,
            },
            "cases": [
                {
                    "label": "程序员+最近发言",
                    "recent_event_count": 2,
                    "suggestion_generated": True,
                }
            ],
        }

        with tempfile.TemporaryDirectory(prefix="recent-context-") as tempdir:
            with patch(
                "tests.memory_pipeline_verifier.runner.load_recent_context_fixture",
                return_value=fake_cases,
            ), patch(
                "tests.memory_pipeline_verifier.runner._run_recent_context_verification_internal",
                return_value=fake_report,
            ):
                results, report = run_recent_context_verification(
                    "tests/fixtures/recent_context_30.json",
                    report_dir=Path(tempdir),
                )

        self.assertEqual(results[0].name, "dataset")
        self.assertEqual(results[1].name, "recent_context")
        self.assertTrue(results[1].ok)
        self.assertIn("cases=1", results[1].details)
        self.assertEqual(report["summary"]["suggestion_success"], 1)


if __name__ == "__main__":
    unittest.main()
