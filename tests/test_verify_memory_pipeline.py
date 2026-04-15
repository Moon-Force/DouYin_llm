from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import MagicMock
from unittest.mock import patch

from backend.schemas.live import LiveEvent
from backend.services.memory_extractor import ViewerMemoryExtractor
from tests.memory_pipeline_verifier.datasets import (
    DEFAULT_DATASET_SIZE,
    build_memory_dataset,
    export_dataset_fixture,
)
from tests.memory_pipeline_verifier.runner import (
    DEFAULT_EVENT_CONTENT,
    DEFAULT_QUERY_TEXT,
    StepResult,
    backend_ready_after_attempts,
    build_test_event_payload,
    format_step_status,
    normalize_mode,
    parse_args,
    query_batch_sqlite_counts,
    run_internal_verification,
    should_start_backend,
    summarize_results,
)


class VerifyMemoryPipelineTests(unittest.TestCase):
    def test_default_texts_are_non_empty_strings(self):
        self.assertIsInstance(DEFAULT_EVENT_CONTENT, str)
        self.assertIsInstance(DEFAULT_QUERY_TEXT, str)
        self.assertTrue(DEFAULT_EVENT_CONTENT.strip())
        self.assertTrue(DEFAULT_QUERY_TEXT.strip())

    def test_summarize_results_marks_failure_when_any_step_fails(self):
        results = [
            StepResult(name="extract", ok=True, details="ok"),
            StepResult(name="persist", ok=False, details="viewer_memories missing"),
        ]

        summary = summarize_results(results)

        self.assertFalse(summary["overall_ok"])
        self.assertEqual(summary["failed_steps"], ["persist"])

    def test_normalize_mode_accepts_internal_and_e2e(self):
        self.assertEqual(normalize_mode("internal"), "internal")
        self.assertEqual(normalize_mode("e2e"), "e2e")
        with self.assertRaises(ValueError):
            normalize_mode("other")

    def test_should_start_backend_only_for_missing_healthcheck_in_e2e(self):
        self.assertFalse(should_start_backend(mode="internal", health_ok=False))
        self.assertFalse(should_start_backend(mode="e2e", health_ok=True))
        self.assertTrue(should_start_backend(mode="e2e", health_ok=False))

    def test_build_test_event_payload_uses_stable_room_and_viewer_ids(self):
        payload = build_test_event_payload()

        self.assertEqual(payload["room_id"], "verify-memory-room")
        self.assertEqual(payload["user"]["id"], "verify-memory-viewer")
        self.assertEqual(payload["content"], DEFAULT_EVENT_CONTENT)

    def test_format_step_status_includes_name_and_pass_flag(self):
        result = StepResult(name="extract", ok=True, details="1 candidate")
        self.assertEqual(format_step_status(result), "[PASS] extract: 1 candidate")

    def test_backend_ready_after_attempts_returns_false_for_all_failures(self):
        self.assertFalse(backend_ready_after_attempts([False, False, False]))
        self.assertTrue(backend_ready_after_attempts([False, True]))

    def test_entry_script_help_runs_successfully(self):
        repo_root = Path(__file__).resolve().parents[1]
        script_path = repo_root / "tests" / "verify_memory_pipeline.py"
        completed = subprocess.run(
            [sys.executable, str(script_path), "--help"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=10,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)

    def test_build_memory_dataset_returns_fifty_plus_extractable_events(self):
        dataset = build_memory_dataset()
        extractor = ViewerMemoryExtractor()

        self.assertGreaterEqual(len(dataset), DEFAULT_DATASET_SIZE)
        self.assertEqual(len({item["event_id"] for item in dataset}), len(dataset))
        self.assertTrue(all(extractor.extract(LiveEvent(**item)) for item in dataset))

    def test_export_dataset_fixture_writes_json_file(self):
        dataset = build_memory_dataset(count=3)
        output_dir = Path("data") / "tmp-tests"
        output_path = output_dir / "memory-events.json"
        try:
            export_dataset_fixture(output_path, dataset)

            self.assertTrue(output_path.exists())
            self.assertIn("verify-memory-batch-0001", output_path.read_text(encoding="utf-8"))
        finally:
            if output_path.exists():
                output_path.unlink()
            if output_dir.exists():
                output_dir.rmdir()

    def test_parse_args_accepts_dataset_and_count(self):
        args = parse_args(["--mode", "internal", "--count", "50", "--dataset", "tests/fixtures/demo.json"])

        self.assertEqual(args.mode, "internal")
        self.assertEqual(args.count, 50)
        self.assertEqual(args.dataset, "tests/fixtures/demo.json")

    def test_query_batch_sqlite_counts_sums_multiple_viewers(self):
        rows = {
            "id:viewer-1": {"events": 2, "viewer_profiles": 1, "viewer_memories": 2},
            "id:viewer-2": {"events": 3, "viewer_profiles": 1, "viewer_memories": 3},
        }

        counts = query_batch_sqlite_counts(
            Path("data/live_prompter.db"),
            "verify-memory-room",
            ["id:viewer-1", "id:viewer-2"],
            query_fn=lambda database_path, room_id, viewer_id: rows[viewer_id],
        )

        self.assertEqual(counts, {"events": 5, "viewer_profiles": 2, "viewer_memories": 5})

    def test_run_internal_verification_reports_batch_counts(self):
        dataset = build_memory_dataset(count=50)
        fake_store = MagicMock()
        fake_store.save_viewer_memory.side_effect = lambda room_id, viewer_id, memory_text, **kwargs: MagicMock(
            room_id=room_id,
            viewer_id=viewer_id,
            memory_text=memory_text,
            memory_id=f"memory-{viewer_id}",
            memory_type=kwargs["memory_type"],
            confidence=kwargs["confidence"],
            updated_at=1,
            recall_count=0,
        )
        fake_vector = MagicMock()
        fake_vector.similar_memories.side_effect = lambda query_text, room_id, viewer_id, limit=2: [
            {"memory_text": query_text}
        ]
        fake_settings = MagicMock()
        fake_settings.ensure_dirs.return_value = None
        fake_settings.database_path = Path("data/live_prompter.db")
        fake_settings.embedding_mode = "cloud"
        fake_settings.llm_mode = "qwen"

        with patch("tests.memory_pipeline_verifier.runner.settings", fake_settings), patch(
            "tests.memory_pipeline_verifier.runner.EmbeddingService", return_value=MagicMock()
        ), patch(
            "tests.memory_pipeline_verifier.runner.LongTermStore", return_value=fake_store
        ), patch(
            "tests.memory_pipeline_verifier.runner.VectorMemory", return_value=fake_vector
        ), patch(
            "tests.memory_pipeline_verifier.runner.query_sqlite_counts",
            return_value={"events": 50, "viewer_profiles": 50, "viewer_memories": 50},
        ):
            results, processed = run_internal_verification(dataset=dataset)

        self.assertEqual(processed, 50)
        self.assertEqual(results[1].details, "candidates=50/50")
        self.assertEqual(results[2].details, "events=50 profiles=50 memories=50 processed=50")
        self.assertEqual(results[3].details, "matches=50/50")


if __name__ == "__main__":
    unittest.main()
