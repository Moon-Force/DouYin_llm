import argparse
from dataclasses import dataclass
from dataclasses import replace
import json
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from backend.config import settings
from backend.memory.embedding_service import EmbeddingService
from backend.memory.long_term import LongTermStore
from backend.memory.vector_store import VectorMemory
from backend.schemas.live import LiveEvent
from backend.services.agent import LivePromptAgent
from backend.services.llm_memory_extractor import LLMBackedViewerMemoryExtractor
from backend.services.memory_confidence_service import MemoryConfidenceService
from backend.services.memory_extractor import ViewerMemoryExtractor
from backend.services.memory_extractor_client import MemoryExtractorClient
from tests.memory_pipeline_verifier.datasets import build_memory_dataset
from tests.memory_pipeline_verifier.datasets import load_client_case_fixture
from tests.memory_pipeline_verifier.datasets import load_dataset_fixture
from tests.memory_pipeline_verifier.datasets import load_memory_extraction_fixture
from tests.memory_pipeline_verifier.datasets import load_recent_context_fixture
from tests.memory_pipeline_verifier.datasets import load_semantic_recall_fixture


DEFAULT_ROOM_ID = "verify-memory-room"
DEFAULT_USER_ID = "verify-memory-viewer"
DEFAULT_NICKNAME = "验证用户"
DEFAULT_EVENT_CONTENT = "我在杭州上班，最近总是熬夜，周末想补补皮肤状态"
DEFAULT_QUERY_TEXT = "最近熬夜皮肤状态不太好"
DEFAULT_BASE_URL = "http://127.0.0.1:8010"
DEFAULT_STARTUP_TIMEOUT_SECONDS = 20.0


@dataclass
class StepResult:
    name: str
    ok: bool
    details: str


def summarize_results(results):
    failed_steps = [result.name for result in results if not result.ok]
    return {
        "overall_ok": not failed_steps,
        "failed_steps": failed_steps,
    }


def normalize_mode(mode):
    normalized = str(mode or "").strip().lower()
    if normalized not in {"internal", "e2e"}:
        raise ValueError(f"unsupported mode: {mode}")
    return normalized


def normalize_task(task):
    normalized = str(task or "").strip().lower()
    if normalized not in {"pipeline", "semantic-recall", "memory-extraction", "client-cases", "recent-context", "history-recall"}:
        raise ValueError(f"unsupported task: {task}")
    return normalized


def should_start_backend(mode, health_ok):
    return normalize_mode(mode) == "e2e" and not bool(health_ok)


def build_test_event_payload():
    timestamp = int(time.time() * 1000)
    return {
        "event_id": f"verify-memory-{timestamp}",
        "room_id": DEFAULT_ROOM_ID,
        "platform": "douyin",
        "event_type": "comment",
        "method": "WebcastChatMessage",
        "livename": "verify-room",
        "ts": timestamp,
        "user": {
            "id": DEFAULT_USER_ID,
            "nickname": DEFAULT_NICKNAME,
        },
        "content": DEFAULT_EVENT_CONTENT,
        "metadata": {},
        "raw": {},
    }


def format_step_status(result):
    prefix = "PASS" if result.ok else "FAIL"
    return f"[{prefix}] {result.name}: {result.details}"


def backend_ready_after_attempts(attempt_results):
    return any(bool(result) for result in attempt_results)


def print_header(title):
    print(f"\n== {title} ==")


def print_step(result):
    print(format_step_status(result))


def record_step(results, name, ok, details):
    result = StepResult(name=name, ok=ok, details=details)
    results.append(result)
    print_step(result)
    return result


def build_live_event():
    return LiveEvent(**build_test_event_payload())


def build_live_events(dataset=None, count=1):
    if dataset:
        return [LiveEvent(**payload) for payload in dataset]
    if int(count) > 1:
        return [LiveEvent(**payload) for payload in build_memory_dataset(count=count)]
    return [build_live_event()]


def build_memory_extraction_event(case, index):
    timestamp = int(time.time() * 1000) + index
    room_id = str(case.get("room_id") or DEFAULT_ROOM_ID).strip()
    user_id = str(case.get("user_id") or f"memory-extraction-viewer-{index:03d}").strip()
    nickname = str(case.get("nickname") or f"MemoryEval{index:03d}").strip() or f"MemoryEval{index:03d}"
    content = str(case.get("content") or "").strip()
    return LiveEvent(
        event_id=f"memory-extraction-{index:03d}",
        room_id=room_id,
        source_room_id=room_id,
        session_id="memory-extraction-eval",
        platform="douyin",
        event_type="comment",
        method="WebcastChatMessage",
        livename=DEFAULT_NICKNAME,
        ts=timestamp,
        user={"id": user_id, "nickname": nickname},
        content=content,
        metadata={"dataset": "memory_extraction", "label": str(case.get("label") or f"case-{index}")},
        raw={},
    )


def build_memory_extraction_evaluator(runtime_settings=None):
    active_settings = runtime_settings or settings
    client = MemoryExtractorClient(active_settings)
    return LLMBackedViewerMemoryExtractor(active_settings, client)


def classify_memory_extraction_error(exc):
    message = str(exc or "")
    for code in (
        "reasoning_only",
        "response_truncated",
        "empty_content",
        "invalid_response_shape",
        "invalid_json_body",
        "invalid_schema",
    ):
        if code in message:
            return code
    if isinstance(exc, json.JSONDecodeError):
        return "invalid_json_body"
    return exc.__class__.__name__.lower() or "unknown_error"


def _safe_ratio(numerator, denominator):
    if not denominator:
        return 0.0
    return float(numerator) / float(denominator)


def _f1(precision, recall):
    if not precision and not recall:
        return 0.0
    return 2 * precision * recall / (precision + recall)


def validate_memory_extraction_payload(payload):
    if not isinstance(payload, dict):
        raise ValueError("invalid_schema payload must be an object")

    required_string_fields = ("memory_type", "polarity", "temporal_scope", "reason")
    if not isinstance(payload.get("should_extract"), bool):
        raise ValueError("invalid_schema should_extract must be a boolean")
    for field in required_string_fields:
        if not isinstance(payload.get(field), str):
            raise ValueError(f"invalid_schema {field} must be a string")

    raw_text = payload.get("memory_text_raw")
    canonical_text = payload.get("memory_text_canonical")
    legacy_text = payload.get("memory_text")
    if not isinstance(raw_text, str):
        raw_text = legacy_text if isinstance(legacy_text, str) else ""
    if not isinstance(canonical_text, str):
        canonical_text = legacy_text if isinstance(legacy_text, str) else ""

    if payload["memory_type"] not in {"preference", "fact", "context"}:
        raise ValueError("invalid_schema memory_type is invalid")
    if payload["polarity"] not in {"positive", "negative", "neutral"}:
        raise ValueError("invalid_schema polarity is invalid")
    if payload["temporal_scope"] not in {"long_term", "short_term"}:
        raise ValueError("invalid_schema temporal_scope is invalid")
    if not payload["reason"].strip():
        raise ValueError("invalid_schema reason must not be blank")
    if payload["should_extract"] and not raw_text.strip():
        raise ValueError("invalid_schema memory_text_raw must not be blank when should_extract is true")
    if payload["should_extract"] and not canonical_text.strip():
        raise ValueError("invalid_schema memory_text_canonical must not be blank when should_extract is true")
    return {
        **payload,
        "memory_text_raw": raw_text,
        "memory_text_canonical": canonical_text,
        "memory_text": canonical_text,
    }


def fetch_backend_health(base_url=DEFAULT_BASE_URL):
    url = f"{base_url.rstrip('/')}/health"
    try:
        with urllib.request.urlopen(url, timeout=3) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        return False, str(exc), {}
    return True, payload.get("status", "unknown"), payload


def start_backend_process(repo_root: Path):
    command = [
        sys.executable,
        "-m",
        "uvicorn",
        "backend.app:app",
        "--host",
        "127.0.0.1",
        "--port",
        "8010",
    ]
    creationflags = 0
    if sys.platform.startswith("win"):
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP
    return subprocess.Popen(
        command,
        cwd=str(repo_root),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=creationflags,
    )


def wait_for_backend(base_url=DEFAULT_BASE_URL, timeout_seconds=DEFAULT_STARTUP_TIMEOUT_SECONDS):
    started_at = time.time()
    attempts = []
    while time.time() - started_at < timeout_seconds:
        ok, _, _ = fetch_backend_health(base_url)
        attempts.append(ok)
        if ok:
            return True, attempts
        time.sleep(0.5)
    return False, attempts


def stop_backend_process(process):
    if process is None:
        return
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def query_sqlite_counts(database_path, room_id, viewer_id):
    connection = sqlite3.connect(str(database_path))
    try:
        events_count = connection.execute(
            "SELECT COUNT(*) FROM events WHERE room_id = ? AND viewer_id = ?",
            (room_id, viewer_id),
        ).fetchone()[0]
        profiles_count = connection.execute(
            "SELECT COUNT(*) FROM viewer_profiles WHERE room_id = ? AND viewer_id = ?",
            (room_id, viewer_id),
        ).fetchone()[0]
        memories_count = connection.execute(
            "SELECT COUNT(*) FROM viewer_memories WHERE room_id = ? AND viewer_id = ?",
            (room_id, viewer_id),
        ).fetchone()[0]
    finally:
        connection.close()
    return {
        "events": events_count,
        "viewer_profiles": profiles_count,
        "viewer_memories": memories_count,
    }


def query_batch_sqlite_counts(database_path, room_id, viewer_ids, query_fn=None):
    query_fn = query_fn or query_sqlite_counts
    totals = {
        "events": 0,
        "viewer_profiles": 0,
        "viewer_memories": 0,
    }
    for viewer_id in {value for value in viewer_ids if value}:
        counts = query_fn(database_path, room_id, viewer_id)
        for key in totals:
            totals[key] += int(counts.get(key, 0))
    return totals


def cleanup_temp_dir(path, retries=3, delay_seconds=0.1):
    target = Path(path)
    attempts = max(1, int(retries))
    for attempt in range(attempts):
        try:
            shutil.rmtree(target)
            return True
        except FileNotFoundError:
            return True
        except PermissionError:
            if attempt >= attempts - 1:
                return False
            time.sleep(max(0.0, float(delay_seconds)))
    return False


def build_semantic_recall_report_path(dataset_path, report_dir=None):
    dataset = Path(dataset_path)
    root = Path(report_dir) if report_dir else Path("artifacts") / "semantic_recall_reports"
    return root / f"{dataset.stem}.md"


def normalize_report_tag(value, default):
    normalized = str(value or "").strip().lower()
    if not normalized:
        normalized = str(default or "").strip().lower()
    normalized = normalized.replace("_", "-").replace(" ", "-")
    normalized = "".join(ch for ch in normalized if ch.isalnum() or ch == "-").strip("-")
    return normalized or str(default or "default").strip().lower()


def build_memory_extraction_report_path(dataset_path, reasoning_effort="none", prompt_variant="cot", report_dir=None):
    dataset = Path(dataset_path)
    root = Path(report_dir) if report_dir else Path("artifacts") / "memory_extraction_reports"
    reasoning_tag = normalize_report_tag(reasoning_effort, "none")
    prompt_tag = normalize_report_tag(prompt_variant, "cot")
    return root / f"{dataset.stem}.reasoning-{reasoning_tag}.prompt-{prompt_tag}.md"


def build_client_case_report_path(dataset_path, report_dir=None):
    dataset = Path(dataset_path)
    root = Path(report_dir) if report_dir else Path("artifacts") / "client_case_reports"
    return root / f"{dataset.stem}.md"


def build_recent_context_report_path(dataset_path, report_dir=None):
    dataset = Path(dataset_path)
    root = Path(report_dir) if report_dir else Path("artifacts") / "recent_context_reports"
    return root / f"{dataset.stem}.md"


def render_semantic_recall_report_markdown(*, dataset_path, total_cases, top1_hits, top3_hits, case_results):
    top1_rate = (top1_hits / total_cases) if total_cases else 0.0
    top3_rate = (top3_hits / total_cases) if total_cases else 0.0

    lines = []
    lines.append("# Semantic Recall Report")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Dataset: `{dataset_path}`")
    lines.append(f"- Cases: {total_cases}")
    lines.append(f"- Top1: {top1_hits}/{total_cases} ({top1_rate:.4f})")
    lines.append(f"- Top3: {top3_hits}/{total_cases} ({top3_rate:.4f})")
    lines.append("")

    for case in case_results:
        label = str(case.get("label") or "").strip() or "unknown"
        lines.append(f"## {label}")
        lines.append("")
        tags = case.get("tags") or []
        if tags:
            lines.append(f"- Tags: {', '.join(str(tag) for tag in tags)}")
        lines.append(f"- Top1 Hit: {'YES' if case.get('top1_hit') else 'NO'}")
        lines.append(f"- Top3 Hit: {'YES' if case.get('top3_hit') else 'NO'}")
        query = str(case.get("query") or "")
        expected = str(case.get("expected_memory_text") or "")
        if query:
            lines.append("")
            lines.append("**Query**")
            lines.append("")
            lines.append(f"> {query}")
        if expected:
            lines.append("")
            lines.append("**Expected Memory**")
            lines.append("")
            lines.append(f"> {expected}")
        top_texts = case.get("top_texts") or []
        if top_texts:
            lines.append("")
            lines.append("**Top 3 Recalled**")
            lines.append("")
            for idx, text in enumerate(top_texts[:3], start=1):
                lines.append(f"{idx}. {text}")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def render_memory_extraction_report_markdown(*, dataset_path, reasoning_effort, prompt_variant, metrics, failures):
    lines = []
    lines.append("# Memory Extraction Report")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Dataset: `{dataset_path}`")
    lines.append(f"- Reasoning Effort: {reasoning_effort}")
    lines.append(f"- Prompt Variant: {prompt_variant}")
    lines.append(f"- Cases: {metrics['case_count']}")
    lines.append(f"- JSON Parse Rate: {metrics['json_parse_rate']:.4f}")
    lines.append(f"- Schema Valid Rate: {metrics['schema_valid_rate']:.4f}")
    lines.append(f"- Should Extract Precision: {metrics['should_extract_precision']:.4f}")
    lines.append(f"- Should Extract Recall: {metrics['should_extract_recall']:.4f}")
    lines.append(f"- Should Extract F1: {metrics['should_extract_f1']:.4f}")
    lines.append(f"- Memory Type Accuracy: {metrics['memory_type_accuracy']:.4f}")
    lines.append(f"- Polarity Accuracy: {metrics['polarity_accuracy']:.4f}")
    lines.append(f"- Temporal Scope Accuracy: {metrics['temporal_scope_accuracy']:.4f}")
    lines.append(f"- False Positives: {metrics['false_positive_count']}")
    lines.append(f"- False Negatives: {metrics['false_negative_count']}")
    lines.append(f"- Short-Term False Positives: {metrics['short_term_false_positive_count']}")
    lines.append(f"- Negative Polarity Mismatches: {metrics['negative_polarity_mismatch_count']}")
    lines.append("")

    for case in failures:
        label = str(case.get("label") or "").strip() or "unknown"
        lines.append(f"## {label}")
        lines.append("")
        lines.append(f"- Error Type: {str(case.get('error_type') or 'unknown')}")
        lines.append("")
        content = str(case.get("content") or "").strip()
        if content:
            lines.append("**Content**")
            lines.append("")
            lines.append(f"> {content}")
            lines.append("")
        expected = case.get("expected") or {}
        actual = case.get("actual") or {}
        lines.append("**Expected**")
        lines.append("")
        lines.append("```json")
        lines.append(json.dumps(expected, ensure_ascii=False, indent=2))
        lines.append("```")
        lines.append("")
        lines.append("**Actual**")
        lines.append("")
        lines.append("```json")
        lines.append(json.dumps(actual, ensure_ascii=False, indent=2))
        lines.append("```")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def render_client_case_report_markdown(*, dataset_path, report):
    summary = report.get("summary") or {}
    case_results = report.get("cases") or []

    lines = []
    lines.append("# Client Case Verification Report")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Dataset: `{dataset_path}`")
    lines.append(f"- Cases: {summary.get('case_count', 0)}")
    lines.append(f"- History Extract Success: {summary.get('history_extract_success', 0)}")
    lines.append(f"- Follow Recall Success: {summary.get('follow_recall_success', 0)}")
    lines.append(f"- Suggestion Success: {summary.get('suggestion_success', 0)}")
    lines.append("")

    for case in case_results:
        lines.append(f"## {str(case.get('label') or 'unknown')}")
        lines.append("")
        lines.append(f"- History Extracted: {case.get('history_extracted_count', 0)}")
        lines.append(f"- Follow Recalled: {case.get('follow_recalled_count', 0)}")
        lines.append(f"- Suggestion Generated: {'YES' if case.get('suggestion_generated') else 'NO'}")
        if case.get("history"):
            lines.append("")
            lines.append("**History Comment**")
            lines.append("")
            lines.append(f"> {case['history']}")
        if case.get("followup"):
            lines.append("")
            lines.append("**Followup Comment**")
            lines.append("")
            lines.append(f"> {case['followup']}")
        if case.get("follow_recalled"):
            lines.append("")
            lines.append("**Recalled Memories**")
            lines.append("")
            for item in case["follow_recalled"]:
                lines.append(f"- {item}")
        if case.get("suggestion_reply_text"):
            lines.append("")
            lines.append("**Suggestion**")
            lines.append("")
            lines.append(f"> {case['suggestion_reply_text']}")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def render_recent_context_report_markdown(*, dataset_path, report):
    summary = report.get("summary") or {}
    case_results = report.get("cases") or []

    lines = []
    lines.append("# Recent Context Verification Report")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Dataset: `{dataset_path}`")
    lines.append(f"- Cases: {summary.get('case_count', 0)}")
    lines.append(f"- Suggestion Success: {summary.get('suggestion_success', 0)}")
    lines.append("")

    for case in case_results:
        lines.append(f"## {str(case.get('label') or 'unknown')}")
        lines.append("")
        lines.append(f"- Recent Event Count: {case.get('recent_event_count', 0)}")
        lines.append(f"- Suggestion Generated: {'YES' if case.get('suggestion_generated') else 'NO'}")
        recent_comments = case.get("recent_comments") or []
        if recent_comments:
            lines.append("")
            lines.append("**Recent Comments**")
            lines.append("")
            for item in recent_comments:
                lines.append(f"- {item}")
        if case.get("current_comment"):
            lines.append("")
            lines.append("**Current Comment**")
            lines.append("")
            lines.append(f"> {case['current_comment']}")
        if case.get("suggestion_reply_text"):
            lines.append("")
            lines.append("**Suggestion**")
            lines.append("")
            lines.append(f"> {case['suggestion_reply_text']}")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def _run_client_case_verification_internal(cases):
    temp_root = Path(tempfile.mkdtemp(prefix="client-case-verification-"))
    try:
        runtime_settings = replace(
            settings,
            data_dir=temp_root,
            database_path=temp_root / "live_prompter.db",
            chroma_dir=temp_root / "chroma",
        )
        runtime_settings.ensure_dirs()

        store = LongTermStore(runtime_settings.database_path)
        embedding_service = EmbeddingService(runtime_settings)
        vector = VectorMemory(runtime_settings.chroma_dir, settings=runtime_settings, embedding_service=embedding_service)
        client = MemoryExtractorClient(runtime_settings)
        llm_extractor = LLMBackedViewerMemoryExtractor(runtime_settings, client)
        extractor = ViewerMemoryExtractor(settings=runtime_settings, llm_extractor=llm_extractor)
        agent = LivePromptAgent(runtime_settings, vector, store)
        confidence_service = MemoryConfidenceService()

        case_results = []
        for case in cases:
            history_event = LiveEvent(**case["history_event"])
            followup_event = LiveEvent(**case["followup_event"])

            store.persist_event(history_event)
            history_candidates = list(extractor.extract(history_event) or [])
            saved_memories = []
            for candidate in history_candidates:
                memory = store.save_viewer_memory(
                    room_id=history_event.room_id,
                    viewer_id=history_event.user.viewer_id,
                    memory_text=candidate["memory_text"],
                    source_event_id=history_event.event_id,
                    memory_type=candidate["memory_type"],
                    polarity=str(candidate.get("polarity") or "neutral"),
                    temporal_scope=str(candidate.get("temporal_scope") or "long_term"),
                    confidence=confidence_service.score_new_memory(candidate)["confidence"],
                    source_kind="auto",
                    status="active",
                    is_pinned=False,
                    correction_reason="",
                    corrected_by="system",
                    operation="created",
                    raw_memory_text=str(candidate.get("memory_text_raw") or ""),
                    evidence_count=1,
                    first_confirmed_at=history_event.ts,
                    last_confirmed_at=history_event.ts,
                )
                if memory:
                    vector.sync_memory(memory)
                    saved_memories.append(memory.memory_text)

            store.persist_event(followup_event)
            current_comment_memories = list(extractor.extract(followup_event) or [])
            context = agent.build_context(
                followup_event,
                [],
                current_comment_memories=current_comment_memories,
            )
            suggestion = agent.maybe_generate(
                followup_event,
                [],
                current_comment_memories=current_comment_memories,
            )
            generation_metadata = agent.consume_last_generation_metadata()
            case_results.append(
                {
                    "label": str(case.get("label") or ""),
                    "history": history_event.content,
                    "followup": followup_event.content,
                    "history_extracted_count": len(history_candidates),
                    "history_extracted": [item.get("memory_text") for item in history_candidates],
                    "history_saved": saved_memories,
                    "follow_recalled_count": len(context.get("viewer_memories") or []),
                    "follow_recalled": [item.get("memory_text") for item in context.get("viewer_memories") or []],
                    "suggestion_generated": bool(suggestion),
                    "suggestion_source": suggestion.source if suggestion else "",
                    "suggestion_reply_text": suggestion.reply_text if suggestion else "",
                    "suggestion_references": suggestion.references if suggestion else [],
                    "recalled_memory_ids": generation_metadata.get("recalled_memory_ids", []),
                }
            )

        return {
            "summary": {
                "case_count": len(case_results),
                "history_extract_success": sum(1 for item in case_results if item["history_extracted_count"] > 0),
                "follow_recall_success": sum(1 for item in case_results if item["follow_recalled_count"] > 0),
                "suggestion_success": sum(1 for item in case_results if item["suggestion_generated"]),
            },
            "cases": case_results,
        }
    finally:
        cleanup_temp_dir(temp_root)


def _run_recent_context_verification_internal(cases):
    temp_root = Path(tempfile.mkdtemp(prefix="recent-context-verification-"))
    try:
        runtime_settings = replace(
            settings,
            data_dir=temp_root,
            database_path=temp_root / "live_prompter.db",
            chroma_dir=temp_root / "chroma",
        )
        runtime_settings.ensure_dirs()

        store = LongTermStore(runtime_settings.database_path)
        embedding_service = EmbeddingService(runtime_settings)
        vector = VectorMemory(runtime_settings.chroma_dir, settings=runtime_settings, embedding_service=embedding_service)
        client = MemoryExtractorClient(runtime_settings)
        llm_extractor = LLMBackedViewerMemoryExtractor(runtime_settings, client)
        extractor = ViewerMemoryExtractor(settings=runtime_settings, llm_extractor=llm_extractor)
        agent = LivePromptAgent(runtime_settings, vector, store)

        case_results = []
        for case in cases:
            recent_events = [LiveEvent(**payload) for payload in case["recent_events"]]
            current_event = LiveEvent(**case["current_event"])

            for event in recent_events:
                store.persist_event(event)
            store.persist_event(current_event)

            current_comment_memories = list(extractor.extract(current_event) or [])
            suggestion = agent.maybe_generate(
                current_event,
                recent_events,
                current_comment_memories=current_comment_memories,
            )
            case_results.append(
                {
                    "label": str(case.get("label") or ""),
                    "recent_event_count": len(recent_events),
                    "recent_comments": [item.content for item in recent_events],
                    "current_comment": current_event.content,
                    "suggestion_generated": bool(suggestion),
                    "suggestion_source": suggestion.source if suggestion else "",
                    "suggestion_reply_text": suggestion.reply_text if suggestion else "",
                    "suggestion_references": suggestion.references if suggestion else [],
                }
            )

        return {
            "summary": {
                "case_count": len(case_results),
                "suggestion_success": sum(1 for item in case_results if item["suggestion_generated"]),
            },
            "cases": case_results,
        }
    finally:
        cleanup_temp_dir(temp_root)


def run_client_case_verification(dataset_path, report_dir=None):
    print_header("Memory Pipeline Verify: client cases")
    results = []
    settings.ensure_dirs()
    cases = load_client_case_fixture(dataset_path)
    record_step(results, "dataset", True, f"path={dataset_path} cases={len(cases)}")

    report = _run_client_case_verification_internal(cases)
    summary = report.get("summary") or {}
    case_count = int(summary.get("case_count", 0))
    extract_success = int(summary.get("history_extract_success", 0))
    recall_success = int(summary.get("follow_recall_success", 0))
    suggestion_success = int(summary.get("suggestion_success", 0))
    verification_ok = (
        case_count > 0
        and extract_success == case_count
        and recall_success == case_count
        and suggestion_success == case_count
    )
    record_step(
        results,
        "client_cases",
        verification_ok,
        (
            f"cases={case_count} "
            f"history_extract={extract_success}/{case_count} "
            f"follow_recall={recall_success}/{case_count} "
            f"suggestion={suggestion_success}/{case_count}"
        ),
    )

    try:
        report_path = build_client_case_report_path(dataset_path, report_dir=report_dir)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_text = render_client_case_report_markdown(dataset_path=dataset_path, report=report)
        report_path.write_text(report_text, encoding="utf-8")
        record_step(results, "report", True, f"path={report_path.as_posix()}")
    except Exception as exc:
        record_step(results, "report", False, str(exc))

    return results, report


def run_recent_context_verification(dataset_path, report_dir=None):
    print_header("Memory Pipeline Verify: recent context")
    results = []
    settings.ensure_dirs()
    cases = load_recent_context_fixture(dataset_path)
    record_step(results, "dataset", True, f"path={dataset_path} cases={len(cases)}")

    report = _run_recent_context_verification_internal(cases)
    summary = report.get("summary") or {}
    case_count = int(summary.get("case_count", 0))
    suggestion_success = int(summary.get("suggestion_success", 0))
    verification_ok = case_count > 0 and suggestion_success == case_count
    record_step(
        results,
        "recent_context",
        verification_ok,
        f"cases={case_count} suggestion={suggestion_success}/{case_count}",
    )

    try:
        report_path = build_recent_context_report_path(dataset_path, report_dir=report_dir)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_text = render_recent_context_report_markdown(dataset_path=dataset_path, report=report)
        report_path.write_text(report_text, encoding="utf-8")
        record_step(results, "report", True, f"path={report_path.as_posix()}")
    except Exception as exc:
        record_step(results, "report", False, str(exc))

    return results, report


def run_internal_verification(dataset=None, count=1):
    print_header("Memory Pipeline Verify: internal")
    results = []
    settings.ensure_dirs()
    events = build_live_events(dataset=dataset, count=count)
    extractor = ViewerMemoryExtractor()

    temp_root = Path(tempfile.mkdtemp(prefix="memory-pipeline-"))
    try:
        database_path = temp_root / "live_prompter.db"
        chroma_dir = temp_root / "chroma"
        chroma_dir.mkdir(parents=True, exist_ok=True)

        store = LongTermStore(database_path)
        embedding_service = EmbeddingService(settings)
        vector = VectorMemory(chroma_dir, settings=settings, embedding_service=embedding_service)

        record_step(
            results,
            "environment",
            True,
            (
                f"database={database_path} "
                f"embedding_mode={settings.embedding_mode} "
                f"llm_mode={settings.llm_mode}"
            ),
        )

        extracted_memories = []
        for event in events:
            candidates = extractor.extract(event)
            if not candidates:
                continue
            extracted_memories.append((event, candidates[0]))

        extract_ok = bool(extracted_memories)
        record_step(results, "extract", extract_ok, f"candidates={len(extracted_memories)}/{len(events)}")
        if not extract_ok:
            return results, 0

        for event, candidate in extracted_memories:
            store.persist_event(event)
            memory = store.save_viewer_memory(
                event.room_id,
                event.user.viewer_id,
                candidate["memory_text"],
                source_event_id=event.event_id,
                memory_type=candidate["memory_type"],
                confidence=candidate["confidence"],
            )
            if memory is not None:
                vector.add_memory(memory)

        room_id = extracted_memories[0][0].room_id
        counts = query_batch_sqlite_counts(
            database_path,
            room_id,
            [event.user.viewer_id for event, _ in extracted_memories],
        )
        persist_ok = all(counts[key] > 0 for key in counts)
        record_step(
            results,
            "persist",
            persist_ok,
            (
                f"events={counts['events']} "
                f"profiles={counts['viewer_profiles']} "
                f"memories={counts['viewer_memories']} "
                f"processed={len(extracted_memories)}"
            ),
        )

        matched_recall_count = 0
        for event, candidate in extracted_memories:
            query_text = DEFAULT_QUERY_TEXT if len(extracted_memories) == 1 else candidate["memory_text"]
            recalled = vector.similar_memories(
                query_text,
                event.room_id,
                event.user.viewer_id,
                limit=2,
            )
            if any(item.get("memory_text") == candidate["memory_text"] for item in recalled):
                matched_recall_count += 1

        recall_ok = matched_recall_count == len(extracted_memories)
        record_step(results, "recall", recall_ok, f"matches={matched_recall_count}/{len(extracted_memories)}")
        return results, len(extracted_memories)
    finally:
        cleanup_temp_dir(temp_root)


def run_semantic_recall_verification(dataset_path, report_dir=None):
    print_header("Memory Pipeline Verify: semantic recall")
    results = []
    settings.ensure_dirs()
    cases = load_semantic_recall_fixture(dataset_path)
    record_step(results, "dataset", True, f"path={dataset_path} cases={len(cases)}")

    temp_root = Path(tempfile.mkdtemp(prefix="semantic-recall-"))
    try:
        report_path = build_semantic_recall_report_path(dataset_path, report_dir=report_dir)
        database_path = temp_root / "live_prompter.db"
        chroma_dir = temp_root / "chroma"
        chroma_dir.mkdir(parents=True, exist_ok=True)

        store = LongTermStore(database_path)
        embedding_service = EmbeddingService(settings)
        vector = VectorMemory(chroma_dir, settings=settings, embedding_service=embedding_service)

        total_memories = 0
        failures = []
        for index, case in enumerate(cases, start=1):
            room_id = str(case.get("room_id") or DEFAULT_ROOM_ID).strip()
            viewer_id = str(case.get("viewer_id") or f"id:semantic-eval-viewer-{index:03d}").strip()
            for memory_text in case.get("memory_texts", []):
                store.save_viewer_memory(
                    room_id,
                    viewer_id,
                    memory_text,
                    source_event_id=f"semantic-recall-{index:03d}",
                    memory_type="fact",
                    confidence=0.8,
                )
                total_memories += 1

        vector.prime_memory_index(store.list_all_viewer_memories(limit=10000), batch_size=64, force_rebuild=True)
        record_step(results, "index_memories", True, f"cases={len(cases)} memories={total_memories}")

        top1_hits = 0
        top3_hits = 0
        case_results = []
        for index, case in enumerate(cases, start=1):
            room_id = str(case.get("room_id") or DEFAULT_ROOM_ID).strip()
            viewer_id = str(case.get("viewer_id") or f"id:semantic-eval-viewer-{index:03d}").strip()
            expected = str(case.get("expected_memory_text") or "").strip()
            query = str(case.get("query") or "").strip()
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

        total_cases = len(cases)
        recall_ok = top3_hits == total_cases
        record_step(
            results,
            "semantic_recall",
            recall_ok,
            (
                f"cases={total_cases} "
                f"top1={top1_hits}/{total_cases} "
                f"top3={top3_hits}/{total_cases} "
                f"top1_rate={top1_hits / total_cases:.4f} "
                f"top3_rate={top3_hits / total_cases:.4f}"
            ),
        )
        for failure in failures[:5]:
            print(
                json.dumps(
                    {
                        "semantic_recall_failure": failure,
                    },
                    ensure_ascii=False,
                )
            )
        try:
            report_path.parent.mkdir(parents=True, exist_ok=True)
            report_text = render_semantic_recall_report_markdown(
                dataset_path=dataset_path,
                total_cases=total_cases,
                top1_hits=top1_hits,
                top3_hits=top3_hits,
                case_results=case_results,
            )
            report_path.write_text(report_text, encoding="utf-8")
            record_step(results, "report", True, f"path={report_path.as_posix()}")
        except Exception as exc:
            record_step(results, "report", False, str(exc))
        return results, report_path
    finally:
        cleanup_temp_dir(temp_root)


def run_memory_extraction_verification(dataset_path, report_dir=None):
    print_header("Memory Pipeline Verify: memory extraction")
    results = []
    settings.ensure_dirs()
    reasoning_effort = str(getattr(settings, "memory_extractor_reasoning_effort", "none") or "none").strip().lower() or "none"
    prompt_variant = str(getattr(settings, "memory_extractor_prompt_variant", "cot") or "cot").strip().lower() or "cot"
    cases = load_memory_extraction_fixture(dataset_path)
    record_step(results, "dataset", True, f"path={dataset_path} cases={len(cases)}")

    extractor = build_memory_extraction_evaluator()
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

    for index, case in enumerate(cases, start=1):
        label = str(case.get("label") or f"case-{index}").strip()
        content = str(case.get("content") or "").strip()
        expected = dict(case.get("expected") or {})
        event = build_memory_extraction_event(case, index)
        actual = None
        error_type = ""

        try:
            raw_payload = extractor.extract_payload(event)
            parsed_count += 1
            actual = validate_memory_extraction_payload(raw_payload)
            schema_valid_count += 1
        except Exception as exc:
            error_type = classify_memory_extraction_error(exc)

        expected_should_extract = bool(expected.get("should_extract"))
        actual_should_extract = bool(actual and actual.get("should_extract"))

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
            expected_canonical = str(
                expected.get("memory_text_canonical") or expected.get("memory_text") or ""
            ).strip()
            if expected_canonical and actual_should_extract and actual.get("memory_text_canonical") != expected_canonical:
                failures.append(
                    {
                        "label": label,
                        "content": content,
                        "expected": expected,
                        "actual": actual,
                        "error_type": "canonical_mismatch",
                    }
                )
                continue

        if error_type or actual_should_extract != expected_should_extract:
            failures.append(
                {
                    "label": label,
                    "content": content,
                    "expected": expected,
                    "actual": actual or {},
                    "error_type": error_type or "label_mismatch",
                }
            )
            continue

        if expected_should_extract:
            for field in ("memory_type", "polarity", "temporal_scope"):
                if actual.get(field) != expected.get(field):
                    failures.append(
                        {
                            "label": label,
                            "content": content,
                            "expected": expected,
                            "actual": actual,
                            "error_type": f"{field}_mismatch",
                        }
                    )
                    break

    precision = _safe_ratio(true_positive_count, predicted_positive_count)
    recall = _safe_ratio(true_positive_count, expected_positive_count)
    metrics = {
        "case_count": len(cases),
        "json_parse_rate": _safe_ratio(parsed_count, len(cases)),
        "schema_valid_rate": _safe_ratio(schema_valid_count, len(cases)),
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
    evaluation_ok = metrics["json_parse_rate"] == 1.0 and metrics["schema_valid_rate"] == 1.0
    record_step(
        results,
        "memory_extraction",
        evaluation_ok,
        (
            f"cases={metrics['case_count']} "
            f"parse={metrics['json_parse_rate']:.4f} "
            f"schema={metrics['schema_valid_rate']:.4f} "
            f"f1={metrics['should_extract_f1']:.4f} "
            f"type_acc={metrics['memory_type_accuracy']:.4f} "
            f"polarity_acc={metrics['polarity_accuracy']:.4f} "
            f"temporal_acc={metrics['temporal_scope_accuracy']:.4f}"
        ),
    )
    for failure in failures[:5]:
        print(json.dumps({"memory_extraction_failure": failure}, ensure_ascii=False))
    try:
        report_path = build_memory_extraction_report_path(
            dataset_path,
            reasoning_effort=reasoning_effort,
            prompt_variant=prompt_variant,
            report_dir=report_dir,
        )
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_text = render_memory_extraction_report_markdown(
            dataset_path=dataset_path,
            reasoning_effort=reasoning_effort,
            prompt_variant=prompt_variant,
            metrics=metrics,
            failures=failures,
        )
        report_path.write_text(report_text, encoding="utf-8")
        record_step(results, "report", True, f"path={report_path.as_posix()}")
    except Exception as exc:
        record_step(results, "report", False, str(exc))
    return results, metrics


def post_json(url, payload):
    request = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def get_json(url):
    with urllib.request.urlopen(url, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def run_e2e_verification(repo_root: Path, base_url=DEFAULT_BASE_URL):
    print_header("Memory Pipeline Verify: e2e")
    results = []
    backend_process = None
    started_backend = False

    health_ok, health_details, _ = fetch_backend_health(base_url)
    record_step(results, "healthcheck", health_ok, health_details)

    if should_start_backend("e2e", health_ok):
        backend_process = start_backend_process(repo_root)
        started_backend = True
        ready, attempts = wait_for_backend(base_url)
        record_step(results, "boot_backend", ready, f"attempts={len(attempts)}")
        if not ready:
            stop_backend_process(backend_process)
            return results

    event = build_test_event_payload()
    try:
        response = post_json(f"{base_url.rstrip('/')}/api/events", event)
        inject_ok = bool(response.get("accepted"))
        record_step(results, "inject_event", inject_ok, f"event_id={response.get('event_id', '')}")

        viewer_id = f"id:{event['user']['id']}"
        query = urllib.parse.urlencode(
            {
                "room_id": event["room_id"],
                "viewer_id": viewer_id,
            }
        )
        viewer_payload = get_json(f"{base_url.rstrip('/')}/api/viewer?{query}")
        memories = viewer_payload.get("memories", [])
        memory_ok = any(item.get("memory_text") == event["content"] for item in memories)
        record_step(results, "viewer_detail", memory_ok, f"memories={len(memories)}")
    except urllib.error.HTTPError as exc:
        record_step(results, "inject_event", False, f"http_{exc.code}")
    except Exception as exc:
        record_step(results, "inject_event", False, str(exc))
    finally:
        if started_backend:
            stop_backend_process(backend_process)

    return results


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Verify the viewer memory extraction pipeline.")
    parser.add_argument(
        "--mode",
        default="internal",
        choices=["internal", "e2e"],
        help="Verification mode to run.",
    )
    parser.add_argument(
        "--task",
        default="pipeline",
        choices=["pipeline", "semantic-recall", "memory-extraction", "client-cases", "recent-context", "history-recall"],
        help="Verification task to run.",
    )
    parser.add_argument(
        "--count",
        default=1,
        type=int,
        help="Number of generated verification events for internal mode. Values above 1 use the built-in batch dataset.",
    )
    parser.add_argument(
        "--dataset",
        default="",
        help="Optional JSON dataset fixture path for internal mode.",
    )
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    mode = normalize_mode(args.mode)
    task = normalize_task(args.task)
    repo_root = Path(__file__).resolve().parents[2]

    if task == "semantic-recall":
        if mode != "internal":
            raise ValueError("semantic-recall only supports internal mode")
        if not args.dataset:
            raise ValueError("--dataset is required for semantic-recall")
        results, _ = run_semantic_recall_verification(args.dataset)
    elif task == "memory-extraction":
        if mode != "internal":
            raise ValueError("memory-extraction only supports internal mode")
        if not args.dataset:
            raise ValueError("--dataset is required for memory-extraction")
        results, _ = run_memory_extraction_verification(args.dataset)
    elif task == "client-cases":
        if mode != "internal":
            raise ValueError("client-cases only supports internal mode")
        if not args.dataset:
            raise ValueError("--dataset is required for client-cases")
        results, _ = run_client_case_verification(args.dataset)
    elif task == "recent-context":
        if mode != "internal":
            raise ValueError("recent-context only supports internal mode")
        if not args.dataset:
            raise ValueError("--dataset is required for recent-context")
        results, _ = run_recent_context_verification(args.dataset)
    elif task == "history-recall":
        if mode != "internal":
            raise ValueError("history-recall only supports internal mode")
        if not args.dataset:
            raise ValueError("--dataset is required for history-recall")
        results, _ = run_client_case_verification(args.dataset)
    elif mode == "internal":
        dataset = load_dataset_fixture(args.dataset) if args.dataset else None
        results, _ = run_internal_verification(dataset=dataset, count=args.count)
    else:
        results = run_e2e_verification(repo_root)

    print_header("Summary")
    summary = summarize_results(results)
    for result in results:
        print_step(result)
    if summary["overall_ok"]:
        print("overall: PASS")
        return 0
    print(f"overall: FAIL ({', '.join(summary['failed_steps'])})")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
