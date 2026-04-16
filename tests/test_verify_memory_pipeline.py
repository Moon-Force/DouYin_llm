from collections import Counter
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock
from unittest.mock import patch

from backend.config import settings as backend_settings
from backend.memory.long_term import LongTermStore
from backend.memory.vector_store import VectorMemory
from backend.schemas.live import LiveEvent
from backend.services.memory_extractor import ViewerMemoryExtractor
from tests.memory_pipeline_verifier.datasets import (
    DEFAULT_DATASET_SIZE,
    build_memory_dataset,
    export_dataset_fixture,
    load_semantic_recall_fixture,
    validate_semantic_recall_cases,
)
from tests.memory_pipeline_verifier.runner import (
    DEFAULT_EVENT_CONTENT,
    DEFAULT_QUERY_TEXT,
    StepResult,
    backend_ready_after_attempts,
    build_test_event_payload,
    cleanup_temp_dir,
    format_step_status,
    normalize_mode,
    normalize_task,
    parse_args,
    query_batch_sqlite_counts,
    run_internal_verification,
    run_semantic_recall_verification,
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

    def test_runner_module_help_runs_successfully(self):
        repo_root = Path(__file__).resolve().parents[1]
        completed = subprocess.run(
            [sys.executable, "-m", "tests.memory_pipeline_verifier.runner", "--help"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=10,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("Verify the viewer memory extraction pipeline.", completed.stdout)

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

    def test_load_semantic_recall_fixture_returns_cases(self):
        fixture_path = Path("tests/fixtures/semantic_recall/default.json")

        cases = load_semantic_recall_fixture(fixture_path)

        self.assertGreaterEqual(len(cases), 5)
        self.assertIn("memory_texts", cases[0])
        self.assertIn("query", cases[0])
        self.assertIn("expected_memory_text", cases[0])

    def test_load_semantic_recall_hard_fixture_returns_twenty_five_plus_cases(self):
        fixture_path = Path("tests/fixtures/semantic_recall/hard.json")

        cases = load_semantic_recall_fixture(fixture_path)

        self.assertGreaterEqual(len(cases), 25)
        self.assertEqual(len({case["label"] for case in cases}), len(cases))
        self.assertTrue(all(len(case["memory_texts"]) >= 3 for case in cases))

    def test_hard_semantic_recall_fixture_is_written_into_vector_collection(self):
        cases = load_semantic_recall_fixture(Path("tests/fixtures/semantic_recall/hard.json"))
        temp_root = Path(tempfile.mkdtemp(prefix="semantic-hard-vector-"))
        total_memories = sum(len(case["memory_texts"]) for case in cases)

        try:
            database_path = temp_root / "live_prompter.db"
            chroma_dir = temp_root / "chroma"
            chroma_dir.mkdir(parents=True, exist_ok=True)

            store = LongTermStore(database_path)
            fake_embedding = MagicMock()
            fake_embedding.embed_texts.side_effect = lambda texts: [
                [float(index + 1), 0.0, 0.0, 0.0] for index, _ in enumerate(texts)
            ]
            vector = VectorMemory(chroma_dir, settings=backend_settings, embedding_service=fake_embedding)

            for index, case in enumerate(cases, start=1):
                room_id = str(case.get("room_id") or "semantic-hard-room").strip()
                viewer_id = str(case.get("viewer_id") or f"id:semantic-hard-viewer-{index:03d}").strip()
                for memory_text in case["memory_texts"]:
                    store.save_viewer_memory(
                        room_id,
                        viewer_id,
                        memory_text,
                        source_event_id=f"hard-fixture-{index:03d}",
                        memory_type="fact",
                        confidence=0.8,
                    )

            memories = store.list_all_viewer_memories(limit=10000)
            vector.prime_memory_index(memories, batch_size=64, force_rebuild=True)

            self.assertEqual(vector.memory_collection.count(), total_memories)

            sample_memory = memories[0]
            stored = vector.memory_collection.get(
                ids=[sample_memory.memory_id],
                include=["documents", "metadatas"],
            )
            self.assertEqual(stored["documents"][0], sample_memory.memory_text)
            self.assertEqual(stored["metadatas"][0]["viewer_id"], sample_memory.viewer_id)
            self.assertEqual(stored["metadatas"][0]["room_id"], sample_memory.room_id)
        finally:
            cleanup_temp_dir(temp_root)

    def test_load_semantic_recall_blind_fixture_has_hundred_tagged_cases(self):
        fixture_path = Path("tests/fixtures/semantic_recall/blind_100.json")

        cases = load_semantic_recall_fixture(fixture_path)

        self.assertGreaterEqual(len(cases), 100)
        self.assertEqual(len({case["label"] for case in cases}), len(cases))
        self.assertTrue(
            all(
                isinstance(case.get("tags"), list)
                and case["tags"]
                and all(str(tag).strip() for tag in case["tags"])
                for case in cases
            )
        )

    def test_blind_semantic_recall_fixture_cases_have_dense_memory_choices(self):
        fixture_path = Path("tests/fixtures/semantic_recall/blind_100.json")

        cases = load_semantic_recall_fixture(fixture_path)

        self.assertTrue(all(len(case["memory_texts"]) >= 4 for case in cases))
        self.assertTrue(all(case["expected_memory_text"] in case["memory_texts"] for case in cases))

    def test_blind_semantic_recall_fixture_keeps_category_balance_and_non_copy_queries(self):
        fixture_path = Path("tests/fixtures/semantic_recall/blind_100.json")

        cases = load_semantic_recall_fixture(fixture_path)
        category_counts = Counter(tuple(case["tags"]) for case in cases)

        self.assertEqual(category_counts[("typo",)], 20)
        self.assertEqual(category_counts[("spoken",)], 20)
        self.assertEqual(category_counts[("fragment",)], 20)
        self.assertEqual(category_counts[("typo", "spoken", "fragment", "mixed_noise")], 20)
        self.assertEqual(category_counts[("distractor",)], 20)
        self.assertTrue(
            all(case["query"].strip() != case["expected_memory_text"].strip() for case in cases)
        )

    def test_validate_semantic_recall_cases_rejects_expected_text_outside_memory_texts(self):
        with self.assertRaises(ValueError):
            validate_semantic_recall_cases(
                [
                    {
                        "label": "bad-case",
                        "memory_texts": ["我住在公司附近。"],
                        "query": "我家离公司很近",
                        "expected_memory_text": "我平时骑车上班。",
                    }
                ]
            )

    def test_parse_args_accepts_dataset_and_count(self):
        args = parse_args(["--mode", "internal", "--count", "50", "--dataset", "tests/fixtures/demo.json"])

        self.assertEqual(args.mode, "internal")
        self.assertEqual(args.count, 50)
        self.assertEqual(args.dataset, "tests/fixtures/demo.json")

    def test_normalize_task_accepts_pipeline_and_semantic_recall(self):
        self.assertEqual(normalize_task("pipeline"), "pipeline")
        self.assertEqual(normalize_task("semantic-recall"), "semantic-recall")
        with self.assertRaises(ValueError):
            normalize_task("unknown")

    def test_parse_args_accepts_task_dataset_and_count(self):
        args = parse_args(
            [
                "--mode",
                "internal",
                "--task",
                "semantic-recall",
                "--dataset",
                "tests/fixtures/semantic_recall/default.json",
                "--count",
                "50",
            ]
        )

        self.assertEqual(args.mode, "internal")
        self.assertEqual(args.task, "semantic-recall")
        self.assertEqual(args.dataset, "tests/fixtures/semantic_recall/default.json")
        self.assertEqual(args.count, 50)

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
            return_value={"events": 1, "viewer_profiles": 1, "viewer_memories": 1},
        ):
            results, processed = run_internal_verification(dataset=dataset)

        self.assertEqual(processed, 50)
        self.assertEqual(results[1].details, "candidates=50/50")
        self.assertEqual(results[2].details, "events=50 profiles=50 memories=50 processed=50")
        self.assertEqual(results[3].details, "matches=50/50")

    def test_run_internal_verification_uses_isolated_temp_storage(self):
        dataset = [build_memory_dataset(count=1)[0]]
        captured = {}
        fake_settings = SimpleNamespace(
            ensure_dirs=MagicMock(),
            database_path=Path("data/live_prompter.db"),
            chroma_dir=Path("data/chroma"),
            embedding_mode="cloud",
            llm_mode="qwen",
        )

        def make_store(database_path):
            captured["database_path"] = database_path
            store = MagicMock()
            store.persist_event.return_value = None
            store.save_viewer_memory.side_effect = lambda room_id, viewer_id, memory_text, **kwargs: MagicMock(
                room_id=room_id,
                viewer_id=viewer_id,
                memory_text=memory_text,
                memory_id=f"memory-{viewer_id}",
                memory_type=kwargs["memory_type"],
                confidence=kwargs["confidence"],
                updated_at=1,
                recall_count=0,
                status="active",
                source_kind="auto",
                is_pinned=False,
                source_event_id=kwargs.get("source_event_id", ""),
            )
            return store

        def make_vector(chroma_dir, settings=None, embedding_service=None):
            captured["chroma_dir"] = chroma_dir
            vector = MagicMock()
            vector.similar_memories.side_effect = lambda query_text, room_id, viewer_id, limit=2: [
                {"memory_text": DEFAULT_QUERY_TEXT if query_text == DEFAULT_QUERY_TEXT else query_text}
            ]
            return vector

        with patch("tests.memory_pipeline_verifier.runner.settings", fake_settings), patch(
            "tests.memory_pipeline_verifier.runner.EmbeddingService", return_value=MagicMock()
        ), patch(
            "tests.memory_pipeline_verifier.runner.LongTermStore", side_effect=make_store
        ), patch(
            "tests.memory_pipeline_verifier.runner.VectorMemory", side_effect=make_vector
        ), patch(
            "tests.memory_pipeline_verifier.runner.query_batch_sqlite_counts",
            return_value={"events": 1, "viewer_profiles": 1, "viewer_memories": 1},
        ):
            results, processed = run_internal_verification(dataset=dataset)

        self.assertEqual(processed, 1)
        self.assertNotEqual(captured["database_path"], fake_settings.database_path)
        self.assertNotEqual(captured["chroma_dir"], fake_settings.chroma_dir)
        self.assertIn("temp", str(captured["database_path"]).lower())
        self.assertIn("temp", str(captured["chroma_dir"]).lower())

    def test_run_semantic_recall_verification_reports_top1_and_top3(self):
        dataset = [
            {
                "label": "job-overtime",
                "room_id": "room-1",
                "viewer_id": "id:viewer-1",
                "memory_texts": [
                    "我在杭州做前端开发，最近连续两周都在加班赶需求。",
                    "我周末常去西湖边夜跑，一次差不多十公里。",
                    "我皮肤偏干，换季的时候脸上很容易起皮。",
                ],
                "query": "最近写页面经常熬夜赶进度",
                "expected_memory_text": "我在杭州做前端开发，最近连续两周都在加班赶需求。",
            }
        ]

        with patch("tests.memory_pipeline_verifier.runner.load_semantic_recall_fixture", return_value=dataset), patch(
            "tests.memory_pipeline_verifier.runner.EmbeddingService", return_value=MagicMock()
        ), patch("tests.memory_pipeline_verifier.runner.VectorMemory") as vector_cls:
            fake_vector = MagicMock()
            fake_vector.similar_memories.return_value = [
                {"memory_text": "我在杭州做前端开发，最近连续两周都在加班赶需求。"},
                {"memory_text": "我皮肤偏干，换季的时候脸上很容易起皮。"},
            ]
            vector_cls.return_value = fake_vector

            results = run_semantic_recall_verification("tests/fixtures/semantic_recall/default.json")

        self.assertEqual(results[0].name, "dataset")
        self.assertEqual(results[1].name, "index_memories")
        self.assertEqual(results[2].name, "semantic_recall")
        self.assertEqual(
            results[2].details,
            "cases=1 top1=1/1 top3=1/1 top1_rate=1.0000 top3_rate=1.0000",
        )

    def test_run_semantic_recall_verification_marks_failure_when_expected_text_misses_top3(self):
        dataset = [
            {
                "label": "missed-case",
                "memory_texts": ["我住在公司附近。", "我早饭只喝美式咖啡。"],
                "query": "家离单位很近",
                "expected_memory_text": "我住在公司附近。",
            }
        ]

        with patch("tests.memory_pipeline_verifier.runner.load_semantic_recall_fixture", return_value=dataset), patch(
            "tests.memory_pipeline_verifier.runner.EmbeddingService", return_value=MagicMock()
        ), patch("tests.memory_pipeline_verifier.runner.VectorMemory") as vector_cls:
            fake_vector = MagicMock()
            fake_vector.similar_memories.return_value = [{"memory_text": "我早饭只喝美式咖啡。"}]
            vector_cls.return_value = fake_vector

            results = run_semantic_recall_verification("tests/fixtures/semantic_recall/default.json")

        self.assertFalse(results[2].ok)
        self.assertEqual(
            results[2].details,
            "cases=1 top1=0/1 top3=0/1 top1_rate=0.0000 top3_rate=0.0000",
        )

    def test_cleanup_temp_dir_swallows_permission_error(self):
        with patch("tests.memory_pipeline_verifier.runner.shutil.rmtree", side_effect=PermissionError("busy")):
            removed = cleanup_temp_dir(Path("C:/temp/semantic-recall"), retries=1, delay_seconds=0)

        self.assertFalse(removed)


if __name__ == "__main__":
    unittest.main()
