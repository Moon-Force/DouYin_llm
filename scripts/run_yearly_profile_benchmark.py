from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.config import settings
from backend.memory.embedding_service import EmbeddingService
from backend.memory.long_term import LongTermStore
from backend.memory.vector_store import VectorMemory
from backend.schemas.live import LiveEvent
from backend.services.llm_memory_extractor import LLMBackedViewerMemoryExtractor
from backend.services.memory_extractor_client import MemoryExtractorClient
from tests.memory_pipeline_verifier.runner import (
    render_memory_extraction_report_markdown,
    render_semantic_recall_report_markdown,
)
from tests.memory_pipeline_verifier.yearly_profile_benchmark import (
    build_yearly_profile_benchmark_dataset,
    build_yearly_profile_dataset_summary,
    render_yearly_profile_report_markdown,
    write_yearly_profile_benchmark_dataset,
)


PROFILE_COUNT = 24
COMMENTS_PER_USER = 12


def reset_runtime_storage():
    if settings.database_path.exists():
        settings.database_path.unlink()
    journal_path = settings.database_path.with_name(f"{settings.database_path.name}-journal")
    if journal_path.exists():
        journal_path.unlink()
    if settings.chroma_dir.exists():
        shutil.rmtree(settings.chroma_dir)
    settings.ensure_dirs()


def _safe_ratio(numerator: int, denominator: int) -> float:
    if not denominator:
        return 0.0
    return float(numerator) / float(denominator)


def _f1(precision: float, recall: float) -> float:
    if not precision and not recall:
        return 0.0
    return 2 * precision * recall / (precision + recall)


def build_llm_extractor() -> LLMBackedViewerMemoryExtractor:
    client = MemoryExtractorClient(settings)
    return LLMBackedViewerMemoryExtractor(settings, client)


def evaluate_memory_extraction_llm(extraction_cases: list[dict]) -> tuple[dict, list[dict]]:
    extractor = build_llm_extractor()
    parsed_count = 0
    schema_valid_count = 0
    predicted_positive_count = 0
    expected_positive_count = 0
    true_positive_count = 0
    memory_type_match_count = 0
    polarity_match_count = 0
    temporal_scope_match_count = 0
    false_positive_count = 0
    false_negative_count = 0
    short_term_false_positive_count = 0
    negative_polarity_mismatch_count = 0
    failures = []

    for index, case in enumerate(extraction_cases, start=1):
        event = LiveEvent(
            event_id=f"yearly-extract-{index:03d}",
            room_id=str(case.get("room_id") or "yearly-profile-room"),
            source_room_id=str(case.get("room_id") or "yearly-profile-room"),
            session_id="yearly-profile-benchmark",
            platform="douyin",
            event_type="comment",
            method="WebcastChatMessage",
            livename="yearly-profile-benchmark",
            ts=1_700_000_000_000 + index,
            user={
                "id": str(case.get("user_id") or f"viewer-{index:03d}"),
                "nickname": str(case.get("nickname") or f"观众{index:03d}"),
            },
            content=str(case.get("content") or ""),
            metadata={},
            raw={},
        )
        expected = dict(case.get("expected") or {})
        raw_payload = extractor.extract_payload(event)
        parsed_count += 1
        schema_valid_count += 1
        candidates = extractor._normalize(raw_payload)
        actual = candidates[0] if candidates else {}

        expected_should_extract = bool(expected.get("should_extract"))
        actual_should_extract = bool(candidates)

        if expected_should_extract:
            expected_positive_count += 1
        if actual_should_extract:
            predicted_positive_count += 1
        if expected_should_extract and actual_should_extract:
            true_positive_count += 1

        if actual_should_extract and not expected_should_extract:
            false_positive_count += 1
            if str(expected.get("temporal_scope") or "").strip() == "short_term":
                short_term_false_positive_count += 1
        if expected_should_extract and not actual_should_extract:
            false_negative_count += 1

        if expected_should_extract:
            if actual_should_extract and actual.get("memory_type") == expected.get("memory_type"):
                memory_type_match_count += 1
            if actual_should_extract and actual.get("polarity") == expected.get("polarity"):
                polarity_match_count += 1
            if actual_should_extract and actual.get("temporal_scope") == expected.get("temporal_scope"):
                temporal_scope_match_count += 1
            if str(expected.get("polarity") or "").strip() == "negative":
                if not actual_should_extract or actual.get("polarity") != "negative":
                    negative_polarity_mismatch_count += 1

        mismatch = False
        if actual_should_extract != expected_should_extract:
            mismatch = True
        elif expected_should_extract:
            for field in ("memory_text", "memory_type", "polarity", "temporal_scope"):
                if str(actual.get(field) or "").strip() != str(expected.get(field) or "").strip():
                    mismatch = True
                    break

        if mismatch:
            failures.append(
                {
                    "label": str(case.get("label") or f"case-{index}"),
                    "content": str(case.get("content") or ""),
                    "expected": expected,
                    "actual": actual,
                    "error_type": "mismatch",
                }
            )

    precision = _safe_ratio(true_positive_count, predicted_positive_count)
    recall = _safe_ratio(true_positive_count, expected_positive_count)
    metrics = {
        "case_count": len(extraction_cases),
        "json_parse_rate": _safe_ratio(parsed_count, len(extraction_cases)),
        "schema_valid_rate": _safe_ratio(schema_valid_count, len(extraction_cases)),
        "should_extract_precision": precision,
        "should_extract_recall": recall,
        "should_extract_f1": _f1(precision, recall),
        "memory_type_accuracy": _safe_ratio(memory_type_match_count, expected_positive_count),
        "polarity_accuracy": _safe_ratio(polarity_match_count, expected_positive_count),
        "temporal_scope_accuracy": _safe_ratio(temporal_scope_match_count, expected_positive_count),
        "false_positive_count": false_positive_count,
        "false_negative_count": false_negative_count,
        "short_term_false_positive_count": short_term_false_positive_count,
        "negative_polarity_mismatch_count": negative_polarity_mismatch_count,
    }
    return metrics, failures


def evaluate_semantic_recall(semantic_cases: list[dict]) -> tuple[dict, list[dict]]:
    store = LongTermStore(settings.database_path)
    embedding_service = EmbeddingService(settings)
    vector = VectorMemory(settings.chroma_dir, settings=settings, embedding_service=embedding_service)

    try:
        total_memories = 0
        for index, case in enumerate(semantic_cases, start=1):
            room_id = str(case.get("room_id") or "yearly-profile-room")
            viewer_id = str(case.get("viewer_id") or f"id:viewer-{index:03d}")
            for memory_text in case.get("memory_texts", []):
                store.save_viewer_memory(
                    room_id,
                    viewer_id,
                    memory_text,
                    source_event_id=f"yearly-semantic-{index:03d}",
                    memory_type="fact",
                    confidence=0.8,
                )
                total_memories += 1

        vector.prime_memory_index(store.list_all_viewer_memories(limit=10000), batch_size=64, force_rebuild=True)

        top1_hits = 0
        top3_hits = 0
        failures = []
        case_results = []
        for index, case in enumerate(semantic_cases, start=1):
            room_id = str(case.get("room_id") or "yearly-profile-room")
            viewer_id = str(case.get("viewer_id") or f"id:viewer-{index:03d}")
            query = str(case.get("query") or "").strip()
            expected = str(case.get("expected_memory_text") or "").strip()
            recalled = vector.similar_memories(query, room_id, viewer_id, limit=3)
            top_texts = [str(item.get("memory_text") or "") for item in recalled]
            top1_hit = bool(top_texts[:1] and top_texts[0] == expected)
            top3_hit = bool(expected and expected in top_texts)
            if top1_hit:
                top1_hits += 1
            if top3_hit:
                top3_hits += 1
            else:
                failures.append(
                    {
                        "label": str(case.get("label") or f"case-{index}"),
                        "query": query,
                        "expected_memory_text": expected,
                        "top_texts": top_texts,
                    }
                )
            case_results.append(
                {
                    "label": str(case.get("label") or f"case-{index}"),
                    "tags": list(case.get("tags") or []),
                    "query": query,
                    "expected_memory_text": expected,
                    "top_texts": top_texts,
                    "top1_hit": top1_hit,
                    "top3_hit": top3_hit,
                }
            )

        summary = {
            "case_count": len(semantic_cases),
            "top1_hits": top1_hits,
            "top3_hits": top3_hits,
            "top1_rate": _safe_ratio(top1_hits, len(semantic_cases)),
            "top3_rate": _safe_ratio(top3_hits, len(semantic_cases)),
            "total_memories": total_memories,
            "case_results": case_results,
        }
        return summary, failures
    finally:
        store.close_active_session("yearly-profile-room")


def main():
    output_dir = Path("artifacts/yearly_profile_benchmark")
    output_dir.mkdir(parents=True, exist_ok=True)

    print("== 年度用户画像评测 ==")
    print(f"清空数据库: {settings.database_path}")
    print(f"清空向量库: {settings.chroma_dir}")
    print(f"抽取模式: LLM ({settings.memory_extractor_model} @ {settings.memory_extractor_base_url})")
    print(f"评测规模: {PROFILE_COUNT} 个用户, 每人 {COMMENTS_PER_USER} 条评论")
    reset_runtime_storage()

    dataset = build_yearly_profile_benchmark_dataset(
        profile_count=PROFILE_COUNT,
        comments_per_user=COMMENTS_PER_USER,
    )
    dataset_files = write_yearly_profile_benchmark_dataset(output_dir, dataset)
    extraction_metrics, extraction_failures = evaluate_memory_extraction_llm(dataset["extraction_cases"])
    semantic_summary, semantic_failures = evaluate_semantic_recall(dataset["semantic_cases"])

    memory_extraction_report_path = output_dir / "memory_extraction_report.md"
    semantic_recall_report_path = output_dir / "semantic_recall_report.md"
    final_report_path = output_dir / "年度用户记忆画像评测报告.md"

    memory_extraction_report_path.write_text(
        render_memory_extraction_report_markdown(
            dataset_path=dataset_files["extraction_cases"].as_posix(),
            reasoning_effort=str(getattr(settings, "memory_extractor_reasoning_effort", "none") or "none"),
            prompt_variant=str(getattr(settings, "memory_extractor_prompt_variant", "cot") or "cot"),
            metrics=extraction_metrics,
            failures=extraction_failures,
        ),
        encoding="utf-8",
    )
    semantic_recall_report_path.write_text(
        render_semantic_recall_report_markdown(
            dataset_path=dataset_files["semantic_cases"].as_posix(),
            total_cases=int(semantic_summary["case_count"]),
            top1_hits=int(semantic_summary["top1_hits"]),
            top3_hits=int(semantic_summary["top3_hits"]),
            case_results=semantic_summary["case_results"],
        ),
        encoding="utf-8",
    )

    dataset_summary = build_yearly_profile_dataset_summary(dataset)
    final_report_path.write_text(
        render_yearly_profile_report_markdown(
            dataset_summary=dataset_summary,
            extraction_metrics=extraction_metrics,
            semantic_summary=semantic_summary,
            output_files={
                "history_events": dataset_files["history_events"].as_posix(),
                "extraction_cases": dataset_files["extraction_cases"].as_posix(),
                "semantic_cases": dataset_files["semantic_cases"].as_posix(),
                "memory_extraction_report": memory_extraction_report_path.as_posix(),
                "semantic_recall_report": semantic_recall_report_path.as_posix(),
            },
            llm_summary={
                "mode": "llm",
                "model": settings.memory_extractor_model,
                "base_url": settings.memory_extractor_base_url,
            },
        ),
        encoding="utf-8",
    )

    console_summary = {
        "profiles": dataset_summary["profile_count"],
        "comments": dataset_summary["total_comments"],
        "comments_per_user_min": dataset_summary["comments_per_user_min"],
        "comments_per_user_max": dataset_summary["comments_per_user_max"],
        "extraction_precision": round(extraction_metrics["should_extract_precision"], 4),
        "extraction_recall": round(extraction_metrics["should_extract_recall"], 4),
        "extraction_f1": round(extraction_metrics["should_extract_f1"], 4),
        "semantic_top1": round(semantic_summary["top1_rate"], 4),
        "semantic_top3": round(semantic_summary["top3_rate"], 4),
        "final_report": final_report_path.as_posix(),
    }
    print(json.dumps(console_summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
