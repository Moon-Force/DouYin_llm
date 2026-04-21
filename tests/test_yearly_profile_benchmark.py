import tempfile
import unittest
from pathlib import Path

from tests.memory_pipeline_verifier.yearly_profile_benchmark import (
    build_yearly_profile_benchmark_dataset,
    build_yearly_profile_dataset_summary,
    render_yearly_profile_report_markdown,
    write_yearly_profile_benchmark_dataset,
)


class YearlyProfileBenchmarkTests(unittest.TestCase):
    def test_build_yearly_profile_benchmark_dataset_uses_ten_comments_per_user_over_nearly_one_year(self):
        dataset = build_yearly_profile_benchmark_dataset(profile_count=20, comments_per_user=10)

        self.assertEqual(len(dataset["profiles"]), 20)
        self.assertEqual(len(dataset["history_events"]), 200)
        self.assertEqual(len(dataset["extraction_cases"]), 200)
        self.assertEqual(len(dataset["semantic_cases"]), 60)

        for profile in dataset["profiles"]:
            self.assertEqual(profile["comment_count"], 10)
            self.assertGreaterEqual(profile["span_days"], 300)
            self.assertLessEqual(profile["span_days"], 370)

        first_semantic_case = dataset["semantic_cases"][0]
        self.assertGreaterEqual(len(first_semantic_case["memory_texts"]), 5)
        self.assertIn(first_semantic_case["expected_memory_text"], first_semantic_case["memory_texts"])
        self.assertGreaterEqual(len(first_semantic_case.get("distractor_memory_texts", [])), 4)
        self.assertNotEqual(first_semantic_case["query"].strip(), first_semantic_case["expected_memory_text"].strip())

    def test_build_yearly_profile_benchmark_dataset_supports_large_scale_profile_range(self):
        dataset = build_yearly_profile_benchmark_dataset(profile_count=24, comments_per_user=12)

        self.assertEqual(len(dataset["profiles"]), 24)
        self.assertEqual(len(dataset["history_events"]), 24 * 12)
        self.assertEqual(len(dataset["extraction_cases"]), 24 * 12)
        self.assertGreaterEqual(len(dataset["semantic_cases"]), 24 * 3)

        for profile in dataset["profiles"]:
            self.assertEqual(profile["comment_count"], 12)
            self.assertGreaterEqual(profile["span_days"], 300)
            self.assertLessEqual(profile["span_days"], 370)

        ambiguous_cases = [
            case
            for case in dataset["semantic_cases"]
            if len(case.get("distractor_memory_texts", [])) >= 4
            and any(tag in case.get("tags", []) for tag in ("ambiguous", "spoken", "paraphrase"))
        ]
        self.assertGreaterEqual(len(ambiguous_cases), 24)

    def test_build_yearly_profile_dataset_summary_reports_min_max_comment_counts(self):
        dataset = build_yearly_profile_benchmark_dataset(profile_count=20, comments_per_user=15)

        summary = build_yearly_profile_dataset_summary(dataset)

        self.assertEqual(summary["profile_count"], 20)
        self.assertEqual(summary["total_comments"], 300)
        self.assertEqual(summary["comments_per_user_min"], 15)
        self.assertEqual(summary["comments_per_user_max"], 15)
        self.assertGreaterEqual(summary["time_span_days_min"], 300)
        self.assertLessEqual(summary["time_span_days_max"], 370)

    def test_write_yearly_profile_benchmark_dataset_writes_three_json_files(self):
        dataset = build_yearly_profile_benchmark_dataset(profile_count=2)

        with tempfile.TemporaryDirectory(prefix="yearly-profile-dataset-") as tempdir:
            output_paths = write_yearly_profile_benchmark_dataset(Path(tempdir), dataset)

            self.assertTrue(output_paths["history_events"].exists())
            self.assertTrue(output_paths["extraction_cases"].exists())
            self.assertTrue(output_paths["semantic_cases"].exists())
            self.assertIn("viewer-yearly-001", output_paths["history_events"].read_text(encoding="utf-8"))
            self.assertIn("should_extract", output_paths["extraction_cases"].read_text(encoding="utf-8"))
            self.assertIn("expected_memory_text", output_paths["semantic_cases"].read_text(encoding="utf-8"))

    def test_render_yearly_profile_report_markdown_outputs_chinese_summary(self):
        markdown = render_yearly_profile_report_markdown(
            dataset_summary={
                "profile_count": 24,
                "total_comments": 288,
                "comments_per_user_min": 12,
                "comments_per_user_max": 12,
                "time_span_days_min": 335,
                "time_span_days_max": 362,
            },
            extraction_metrics={
                "case_count": 288,
                "json_parse_rate": 0.9861,
                "schema_valid_rate": 0.9792,
                "should_extract_precision": 0.9435,
                "should_extract_recall": 0.9174,
                "should_extract_f1": 0.9303,
                "memory_type_accuracy": 0.9120,
                "polarity_accuracy": 0.9640,
                "temporal_scope_accuracy": 0.9880,
                "false_positive_count": 11,
                "false_negative_count": 19,
                "short_term_false_positive_count": 5,
                "negative_polarity_mismatch_count": 3,
            },
            semantic_summary={
                "case_count": 72,
                "top1_hits": 63,
                "top3_hits": 69,
                "top1_rate": 63 / 72,
                "top3_rate": 69 / 72,
            },
            output_files={
                "history_events": "artifacts/yearly_profile_benchmark/history_events.json",
                "extraction_cases": "artifacts/yearly_profile_benchmark/extraction_cases.json",
                "semantic_cases": "artifacts/yearly_profile_benchmark/semantic_cases.json",
                "memory_extraction_report": "artifacts/yearly_profile_benchmark/memory_extraction_report.md",
                "semantic_recall_report": "artifacts/yearly_profile_benchmark/semantic_recall_report.md",
            },
            llm_summary={
                "mode": "llm",
                "model": "qwen3.5:0.8b",
                "base_url": "http://127.0.0.1:11434/v1",
            },
        )

        self.assertIn("# 年度用户记忆画像评测报告", markdown)
        self.assertIn("## 数据概览", markdown)
        self.assertIn("## 抽取模式", markdown)
        self.assertIn("## 记忆画像抽取成功率", markdown)
        self.assertIn("## 语义召回成功率", markdown)
        self.assertIn("## 分析结论", markdown)
        self.assertIn("总评论数：288", markdown)
        self.assertIn("每位用户评论数范围：12 - 12", markdown)
        self.assertIn("时间跨度范围（天）：335 - 362", markdown)
        self.assertIn("抽取模式：LLM 抽取", markdown)
        self.assertIn("抽取模型：qwen3.5:0.8b", markdown)
        self.assertIn("Top1 命中率：0.8750", markdown)
        self.assertIn("Top3 命中率：0.9583", markdown)
        self.assertIn("本轮结果说明 LLM 抽取已经明显优于规则抽取", markdown)
        self.assertIn("artifacts/yearly_profile_benchmark/memory_extraction_report.md", markdown)


if __name__ == "__main__":
    unittest.main()
