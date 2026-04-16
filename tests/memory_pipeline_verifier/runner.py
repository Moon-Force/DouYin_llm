import argparse
from dataclasses import dataclass
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
from backend.services.memory_extractor import ViewerMemoryExtractor
from tests.memory_pipeline_verifier.datasets import build_memory_dataset
from tests.memory_pipeline_verifier.datasets import load_dataset_fixture
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
    if normalized not in {"pipeline", "semantic-recall"}:
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


def run_semantic_recall_verification(dataset_path):
    print_header("Memory Pipeline Verify: semantic recall")
    results = []
    settings.ensure_dirs()
    cases = load_semantic_recall_fixture(dataset_path)
    record_step(results, "dataset", True, f"path={dataset_path} cases={len(cases)}")

    temp_root = Path(tempfile.mkdtemp(prefix="semantic-recall-"))
    try:
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
        for index, case in enumerate(cases, start=1):
            room_id = str(case.get("room_id") or DEFAULT_ROOM_ID).strip()
            viewer_id = str(case.get("viewer_id") or f"id:semantic-eval-viewer-{index:03d}").strip()
            expected = str(case.get("expected_memory_text") or "").strip()
            recalled = vector.similar_memories(str(case.get("query") or "").strip(), room_id, viewer_id, limit=3)
            top_texts = [str(item.get("memory_text") or "") for item in recalled]

            if top_texts[:1] and top_texts[0] == expected:
                top1_hits += 1
            if expected in top_texts:
                top3_hits += 1
            else:
                failures.append(
                    {
                        "label": str(case.get("label") or f"case-{index}"),
                        "query": str(case.get("query") or ""),
                        "expected_memory_text": expected,
                        "top_texts": top_texts,
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
        return results
    finally:
        cleanup_temp_dir(temp_root)


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
        choices=["pipeline", "semantic-recall"],
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
        results = run_semantic_recall_verification(args.dataset)
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
