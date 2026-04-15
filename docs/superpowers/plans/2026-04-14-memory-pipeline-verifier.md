# Memory Pipeline Verifier Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a developer-facing verifier that checks the viewer memory extraction, persistence, and semantic recall pipeline, with both internal and end-to-end modes.

**Architecture:** Keep the real logic in a new `tool/memory_pipeline_verifier/` package so the verifier stays organized in its own folder, and expose a thin entry script at `tool/verify_memory_pipeline.py` for easy invocation. Cover the coordination logic with focused `unittest` tests first, then implement the script to print step-by-step PASS/FAIL output, optionally booting the backend for HTTP verification.

**Tech Stack:** Python, argparse, subprocess, urllib, unittest, existing backend memory services

---

## File Structure

- Create: `H:\DouYin_llm\tool\memory_pipeline_verifier\__init__.py`
  Purpose: package marker for the new verifier tool folder.
- Create: `H:\DouYin_llm\tool\memory_pipeline_verifier\runner.py`
  Purpose: core verifier logic, step execution, checks, and backend bootstrapping helpers.
- Create: `H:\DouYin_llm\tool\verify_memory_pipeline.py`
  Purpose: thin CLI entry point that delegates to the verifier package.
- Create: `H:\DouYin_llm\tests\test_verify_memory_pipeline.py`
  Purpose: regression coverage for fixed test data, result tracking, and orchestration helpers.
- Modify: `H:\DouYin_llm\README.md`
  Purpose: document how to run the new verifier once implementation is complete.

## Task 1: Add failing tests for verifier helpers and result tracking

**Files:**
- Create: `H:\DouYin_llm\tests\test_verify_memory_pipeline.py`
- Read: `H:\DouYin_llm\docs\superpowers\specs\2026-04-14-memory-pipeline-verifier-design.md`

- [ ] **Step 1: Write the failing test**

```python
import unittest

from tool.memory_pipeline_verifier.runner import (
    DEFAULT_EVENT_CONTENT,
    DEFAULT_QUERY_TEXT,
    StepResult,
    summarize_results,
)


class VerifyMemoryPipelineTests(unittest.TestCase):
    def test_default_texts_are_stable_unicode_strings(self):
        self.assertEqual(
            DEFAULT_EVENT_CONTENT,
            "我在杭州上班，最近总是熬夜，周末想补补皮肤状态",
        )
        self.assertEqual(DEFAULT_QUERY_TEXT, "最近熬夜皮肤状态不太好")

    def test_summarize_results_marks_failure_when_any_step_fails(self):
        results = [
            StepResult(name="extract", ok=True, details="ok"),
            StepResult(name="persist", ok=False, details="viewer_memories missing"),
        ]

        summary = summarize_results(results)

        self.assertEqual(summary["overall_ok"], False)
        self.assertEqual(summary["failed_steps"], ["persist"])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_verify_memory_pipeline`

Expected: FAIL with `ModuleNotFoundError` because the verifier package does not exist yet.

- [ ] **Step 3: Write minimal implementation**

```python
from dataclasses import dataclass


DEFAULT_EVENT_CONTENT = "我在杭州上班，最近总是熬夜，周末想补补皮肤状态"
DEFAULT_QUERY_TEXT = "最近熬夜皮肤状态不太好"


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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m unittest tests.test_verify_memory_pipeline`

Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add tests/test_verify_memory_pipeline.py tool/memory_pipeline_verifier/__init__.py tool/memory_pipeline_verifier/runner.py
git commit -m "test: add memory pipeline verifier helpers"
```

## Task 2: Add failing tests for mode handling and backend boot decisions

**Files:**
- Modify: `H:\DouYin_llm\tests\test_verify_memory_pipeline.py`
- Modify: `H:\DouYin_llm\tool\memory_pipeline_verifier\runner.py`

- [ ] **Step 1: Write the failing test**

```python
from tool.memory_pipeline_verifier.runner import should_start_backend, normalize_mode

class VerifyMemoryPipelineTests(unittest.TestCase):
    ...
    def test_normalize_mode_accepts_internal_and_e2e(self):
        self.assertEqual(normalize_mode("internal"), "internal")
        self.assertEqual(normalize_mode("e2e"), "e2e")
        with self.assertRaises(ValueError):
            normalize_mode("other")

    def test_should_start_backend_only_for_missing_healthcheck_in_e2e(self):
        self.assertEqual(should_start_backend(mode="internal", health_ok=False), False)
        self.assertEqual(should_start_backend(mode="e2e", health_ok=True), False)
        self.assertEqual(should_start_backend(mode="e2e", health_ok=False), True)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_verify_memory_pipeline`

Expected: FAIL with missing exports for `should_start_backend` and `normalize_mode`.

- [ ] **Step 3: Write minimal implementation**

```python
def normalize_mode(mode):
    normalized = str(mode or "").strip().lower()
    if normalized not in {"internal", "e2e"}:
        raise ValueError(f"unsupported mode: {mode}")
    return normalized


def should_start_backend(mode, health_ok):
    return normalize_mode(mode) == "e2e" and not bool(health_ok)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m unittest tests.test_verify_memory_pipeline`

Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add tests/test_verify_memory_pipeline.py tool/memory_pipeline_verifier/runner.py
git commit -m "test: cover memory pipeline verifier mode helpers"
```

## Task 3: Implement internal verification flow and CLI entry point

**Files:**
- Modify: `H:\DouYin_llm\tool\memory_pipeline_verifier\runner.py`
- Create: `H:\DouYin_llm\tool\verify_memory_pipeline.py`

- [ ] **Step 1: Write the failing test**

Extend `tests/test_verify_memory_pipeline.py`:

```python
from tool.memory_pipeline_verifier.runner import build_test_event_payload

class VerifyMemoryPipelineTests(unittest.TestCase):
    ...
    def test_build_test_event_payload_uses_stable_room_and_viewer_ids(self):
        payload = build_test_event_payload()

        self.assertEqual(payload["room_id"], "verify-memory-room")
        self.assertEqual(payload["user"]["id"], "verify-memory-viewer")
        self.assertEqual(payload["content"], DEFAULT_EVENT_CONTENT)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_verify_memory_pipeline`

Expected: FAIL with missing export for `build_test_event_payload`.

- [ ] **Step 3: Write minimal implementation**

Implement in `runner.py`:

```python
import argparse
import time

from backend.config import settings
from backend.memory.embedding_service import EmbeddingService
from backend.memory.long_term import LongTermStore
from backend.memory.vector_store import VectorMemory
from backend.schemas.live import LiveEvent
from backend.services.memory_extractor import ViewerMemoryExtractor

DEFAULT_ROOM_ID = "verify-memory-room"
DEFAULT_VIEWER_ID = "id:verify-memory-viewer"
DEFAULT_USER_ID = "verify-memory-viewer"
DEFAULT_NICKNAME = "验证用户"


def build_test_event_payload():
    return {
        "event_id": f"verify-memory-{int(time.time() * 1000)}",
        "room_id": DEFAULT_ROOM_ID,
        "platform": "douyin",
        "event_type": "comment",
        "method": "WebcastChatMessage",
        "livename": "verify-room",
        "ts": int(time.time() * 1000),
        "user": {
            "id": DEFAULT_USER_ID,
            "nickname": DEFAULT_NICKNAME,
        },
        "content": DEFAULT_EVENT_CONTENT,
        "metadata": {},
        "raw": {},
    }
```

Add `tool/verify_memory_pipeline.py`:

```python
from tool.memory_pipeline_verifier.runner import main


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m unittest tests.test_verify_memory_pipeline`

Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add tool/memory_pipeline_verifier/runner.py tool/verify_memory_pipeline.py tests/test_verify_memory_pipeline.py
git commit -m "feat: add memory pipeline verifier internal entrypoint"
```

## Task 4: Complete the internal verifier checks

**Files:**
- Modify: `H:\DouYin_llm\tool\memory_pipeline_verifier\runner.py`
- Test: `H:\DouYin_llm\tests\test_verify_memory_pipeline.py`

- [ ] **Step 1: Write the failing test**

Add a test for result formatting:

```python
from tool.memory_pipeline_verifier.runner import format_step_status

class VerifyMemoryPipelineTests(unittest.TestCase):
    ...
    def test_format_step_status_includes_name_and_pass_flag(self):
        result = StepResult(name="extract", ok=True, details="1 candidate")
        self.assertEqual(format_step_status(result), "[PASS] extract: 1 candidate")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_verify_memory_pipeline`

Expected: FAIL with missing export for `format_step_status`.

- [ ] **Step 3: Write minimal implementation**

Implement in `runner.py`:

```python
def format_step_status(result):
    prefix = "PASS" if result.ok else "FAIL"
    return f"[{prefix}] {result.name}: {result.details}"
```

Then implement the internal flow:

```python
def run_internal_verification():
    results = []
    extractor = ViewerMemoryExtractor()
    payload = build_test_event_payload()
    event = LiveEvent(**payload)
    settings.ensure_dirs()
    store = LongTermStore(settings.database_path)
    vector = VectorMemory(settings.chroma_dir, settings=settings, embedding_service=EmbeddingService(settings))

    candidates = extractor.extract(event)
    results.append(StepResult("extract", bool(candidates), f"candidates={len(candidates)}"))
    if not candidates:
        return results

    store.persist_event(event)
    memory = store.save_viewer_memory(
        event.room_id,
        event.user.viewer_id,
        candidates[0]["memory_text"],
        source_event_id=event.event_id,
        memory_type=candidates[0]["memory_type"],
        confidence=candidates[0]["confidence"],
    )
    results.append(StepResult("persist", memory is not None, f"memory_id={memory['memory_id'] if memory else ''}"))
    if memory:
        vector.add_memory(memory)
    recalled = vector.similar_memories(DEFAULT_QUERY_TEXT, event.room_id, event.user.viewer_id, limit=2)
    found = any(item.get("memory_text") == candidates[0]["memory_text"] for item in recalled)
    results.append(StepResult("recall", found, f"matches={len(recalled)}"))
    return results
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m unittest tests.test_verify_memory_pipeline`

Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add tool/memory_pipeline_verifier/runner.py tests/test_verify_memory_pipeline.py
git commit -m "feat: implement internal memory pipeline verification"
```

## Task 5: Add end-to-end mode and README documentation

**Files:**
- Modify: `H:\DouYin_llm\tool\memory_pipeline_verifier\runner.py`
- Modify: `H:\DouYin_llm\README.md`
- Test: `H:\DouYin_llm\tests\test_verify_memory_pipeline.py`

- [ ] **Step 1: Write the failing test**

Add a focused timeout test:

```python
from tool.memory_pipeline_verifier.runner import backend_ready_after_attempts

class VerifyMemoryPipelineTests(unittest.TestCase):
    ...
    def test_backend_ready_after_attempts_returns_false_for_all_failures(self):
        self.assertEqual(backend_ready_after_attempts([False, False, False]), False)
        self.assertEqual(backend_ready_after_attempts([False, True]), True)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_verify_memory_pipeline`

Expected: FAIL with missing export for `backend_ready_after_attempts`.

- [ ] **Step 3: Write minimal implementation**

Implement helper plus end-to-end runner in `runner.py`, using `subprocess.Popen` for `uvicorn`, `urllib.request` for `/health`, `/api/events`, and `/api/viewer`, and ensure only verifier-started processes are terminated. Update `README.md` with:

```markdown
## Memory Pipeline 自检

```powershell
python tool/verify_memory_pipeline.py --mode internal
python tool/verify_memory_pipeline.py --mode e2e
```

默认会逐步打印每一步校验结果；`e2e` 模式会在需要时自动启动本地后端。
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m unittest tests.test_verify_memory_pipeline`

Expected: `OK`

Then run:

`python tool/verify_memory_pipeline.py --mode internal`

Expected: prints PASS for extract, persist, and recall

- [ ] **Step 5: Commit**

```bash
git add tool/memory_pipeline_verifier/runner.py tool/verify_memory_pipeline.py tests/test_verify_memory_pipeline.py README.md
git commit -m "feat: add memory pipeline verifier"
```

## Self-Review

- Spec coverage:
  - New tool subdirectory layout is implemented in Tasks 1-5
  - Internal mode is implemented in Tasks 3-4
  - End-to-end mode and auto-start backend are implemented in Task 5
  - Step-by-step printing and result summary are implemented in Tasks 1 and 4
  - README usage docs are implemented in Task 5
- Placeholder scan:
  - No `TODO`, `TBD`, or vague follow-up placeholders remain
- Type consistency:
  - `StepResult`, `summarize_results`, `normalize_mode`, `should_start_backend`, and `build_test_event_payload` are introduced before later tasks reuse them

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-04-14-memory-pipeline-verifier.md`. Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

Given you asked me to implement directly in this session, I am proceeding with **Inline Execution**.
