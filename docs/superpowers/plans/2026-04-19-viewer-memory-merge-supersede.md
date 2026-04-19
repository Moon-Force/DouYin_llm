# Viewer Memory Merge Supersede Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add save-time dedupe, merge, upgrade, and supersede handling so viewer memories become a maintained profile instead of a growing pile of near-duplicate sentences.

**Architecture:** Insert a new merge-decision layer between extraction and persistence. Extend `viewer_memories` with evidence and supersede metadata, add a dedicated `memory_merge_service` that combines deterministic text rules with same-viewer vector similarity, and update persistence plus vector syncing so `create / merge / upgrade / supersede` all behave consistently and remain auditable.

**Tech Stack:** Python, FastAPI backend, SQLite, Chroma vector store, unittest

---

### Task 1: Extend Viewer Memory Schema And Storage Metadata

**Files:**
- Modify: `backend/memory/long_term.py:39`
- Modify: `backend/schemas/live.py:54`
- Test: `tests/test_long_term_store.py`

- [ ] **Step 1: Write the failing schema/storage tests**

Add tests that assert newly saved memories expose the new metadata fields and that store migrations populate defaults for existing rows.

```python
def test_save_viewer_memory_sets_merge_metadata_defaults(self):
    memory = store.save_viewer_memory(
        room_id="room-1",
        viewer_id="id:user-1",
        memory_text="租房住在公司附近",
        source_event_id="evt-1",
        memory_type="context",
        confidence=0.78,
        source_kind="auto",
        status="active",
        raw_memory_text="我租房住在公司附近，这样通勤方便点",
        evidence_count=1,
        first_confirmed_at=111,
        last_confirmed_at=111,
        superseded_by="",
        merge_parent_id="",
    )

    assert memory.memory_text_raw_latest == "我租房住在公司附近，这样通勤方便点"
    assert memory.evidence_count == 1
    assert memory.first_confirmed_at == 111
    assert memory.last_confirmed_at == 111
    assert memory.superseded_by == ""
    assert memory.merge_parent_id == ""
```

- [ ] **Step 2: Run the storage test to verify it fails**

Run: `python -m unittest tests.test_long_term_store`

Expected: FAIL with missing fields or unexpected keyword arguments for the new metadata.

- [ ] **Step 3: Extend `ViewerMemory` and the SQLite schema**

Update [live.py](H:\DouYin_llm\backend\schemas\live.py) and [long_term.py](H:\DouYin_llm\backend\memory\long_term.py) so `viewer_memories` supports:

```python
class ViewerMemory(BaseModel):
    memory_id: str
    room_id: str
    viewer_id: str
    source_event_id: str = ""
    memory_text: str
    memory_type: str = "fact"
    confidence: float = 0.0
    created_at: int
    updated_at: int
    last_recalled_at: int | None = None
    recall_count: int = 0
    source_kind: str = "auto"
    status: str = "active"
    is_pinned: bool = False
    correction_reason: str = ""
    corrected_by: str = ""
    last_operation: str = "created"
    last_operation_at: int = 0
    memory_text_raw_latest: str = ""
    evidence_count: int = 1
    first_confirmed_at: int = 0
    last_confirmed_at: int = 0
    superseded_by: str = ""
    merge_parent_id: str = ""
```

And make `_ensure_viewer_memory_columns()` add the SQLite columns with safe defaults.

- [ ] **Step 4: Update row serialization and `save_viewer_memory()`**

Extend row parsing plus `save_viewer_memory()` so the new metadata is accepted and stored.

```python
def save_viewer_memory(
    self,
    room_id,
    viewer_id,
    memory_text,
    source_event_id="",
    memory_type="fact",
    confidence=0.0,
    source_kind="auto",
    status="active",
    is_pinned=False,
    correction_reason="",
    corrected_by="",
    operation="created",
    raw_memory_text="",
    evidence_count=1,
    first_confirmed_at=0,
    last_confirmed_at=0,
    superseded_by="",
    merge_parent_id="",
):
    ...
```

- [ ] **Step 5: Run the storage test to verify it passes**

Run: `python -m unittest tests.test_long_term_store`

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/memory/long_term.py backend/schemas/live.py tests/test_long_term_store.py
git commit -m "feat: extend viewer memory merge metadata"
```

### Task 2: Add Merge Decision Service With Deterministic Actions

**Files:**
- Create: `backend/services/memory_merge_service.py`
- Test: `tests/test_memory_merge_service.py`

- [ ] **Step 1: Write the failing merge service tests**

Add tests for the four core actions.

```python
def test_decide_merge_when_canonical_text_matches():
    service = ViewerMemoryMergeService(similarity_threshold=0.88, supersede_threshold=0.82)
    incoming = {
        "memory_text": "喜欢拉面",
        "memory_text_raw": "我喜欢拉面",
        "memory_text_canonical": "喜欢拉面",
        "memory_type": "preference",
        "confidence": 0.86,
    }
    existing = [
        build_memory(memory_id="mem-1", memory_text="喜欢拉面", memory_type="preference"),
    ]

    decision = service.decide(incoming, existing, similar_memories=[])

    assert decision.action == "merge"
    assert decision.target_memory_id == "mem-1"
```

Also cover:

```python
assert decision.action == "upgrade"
assert decision.action == "supersede"
assert decision.action == "create"
```

- [ ] **Step 2: Run the merge service tests to verify they fail**

Run: `python -m unittest tests.test_memory_merge_service`

Expected: FAIL with module not found or missing service behavior.

- [ ] **Step 3: Create the merge decision types and service**

Create [memory_merge_service.py](H:\DouYin_llm\backend\services\memory_merge_service.py) with a focused service:

```python
from dataclasses import dataclass


@dataclass
class MemoryMergeDecision:
    action: str
    target_memory_id: str = ""
    reason: str = ""


class ViewerMemoryMergeService:
    def __init__(self, similarity_threshold=0.88, supersede_threshold=0.82):
        self.similarity_threshold = similarity_threshold
        self.supersede_threshold = supersede_threshold

    def decide(self, incoming, existing_memories, similar_memories):
        ...
```

- [ ] **Step 4: Implement first-pass deterministic rules**

Support these exact rules in order:

```python
if same_canonical:
    return MemoryMergeDecision(action="merge", target_memory_id=match.memory_id, reason="same_canonical")
if more_specific_same_topic:
    return MemoryMergeDecision(action="upgrade", target_memory_id=match.memory_id, reason="more_specific")
if conflicting_preference_direction:
    return MemoryMergeDecision(action="supersede", target_memory_id=match.memory_id, reason="conflicting_direction")
return MemoryMergeDecision(action="create", reason="no_close_match")
```

Use:

- normalized canonical exact match
- contains/contained-by checks
- explicit negative token checks such as `不喜欢`, `不能`, `不吃`, `不喝`, `忌口`, `接受不了`
- same-viewer vector matches only as supporting candidates, not as automatic decisions by themselves

- [ ] **Step 5: Run the merge service tests to verify they pass**

Run: `python -m unittest tests.test_memory_merge_service`

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/services/memory_merge_service.py tests/test_memory_merge_service.py
git commit -m "feat: add viewer memory merge decision service"
```

### Task 3: Add Store Operations For Merge Upgrade And Supersede

**Files:**
- Modify: `backend/memory/long_term.py:839`
- Test: `tests/test_long_term_store.py`

- [ ] **Step 1: Write the failing persistence action tests**

Add tests that assert the store can perform merge, upgrade, and supersede transitions.

```python
def test_supersede_viewer_memory_marks_old_invalid_and_links_new_id(self):
    old_memory = store.save_viewer_memory(
        room_id="room-1",
        viewer_id="id:user-1",
        memory_text="喜欢吃辣",
        source_event_id="evt-1",
        memory_type="preference",
        confidence=0.74,
    )

    new_memory = store.supersede_viewer_memory(
        old_memory.memory_id,
        room_id="room-1",
        viewer_id="id:user-1",
        memory_text="不太能吃辣",
        raw_memory_text="我平时都不太能吃辣",
        memory_type="preference",
        confidence=0.86,
        source_event_id="evt-2",
    )

    refreshed_old = store.get_viewer_memory(old_memory.memory_id)
    assert refreshed_old.status == "invalid"
    assert refreshed_old.superseded_by == new_memory.memory_id
    assert refreshed_old.last_operation == "superseded"
```

- [ ] **Step 2: Run the persistence tests to verify they fail**

Run: `python -m unittest tests.test_long_term_store`

Expected: FAIL because merge/upgrade/supersede helpers do not exist yet.

- [ ] **Step 3: Add explicit store helpers**

Implement these helpers in [long_term.py](H:\DouYin_llm\backend\memory\long_term.py):

```python
def merge_viewer_memory_evidence(self, memory_id, raw_memory_text="", confidence=0.0, source_event_id=""):
    ...

def upgrade_viewer_memory(self, memory_id, memory_text="", raw_memory_text="", confidence=0.0, source_event_id=""):
    ...

def supersede_viewer_memory(
    self,
    memory_id,
    room_id,
    viewer_id,
    memory_text,
    raw_memory_text="",
    source_event_id="",
    memory_type="fact",
    confidence=0.0,
):
    ...
```

- [ ] **Step 4: Write audit logs for the new actions**

Update `_append_viewer_memory_log()` call sites so:

- `merge` logs `operation="merged"`
- `upgrade` logs the text change
- `supersede` logs the old record becoming invalid and includes the replacing memory id in `reason`

- [ ] **Step 5: Run the persistence tests to verify they pass**

Run: `python -m unittest tests.test_long_term_store`

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/memory/long_term.py tests/test_long_term_store.py
git commit -m "feat: add viewer memory merge persistence actions"
```

### Task 4: Integrate Save-Time Merge Decisions Into Event Processing

**Files:**
- Modify: `backend/app.py:227`
- Modify: `backend/services/agent.py:117`
- Modify: `backend/memory/vector_store.py:314`
- Test: `tests/test_comment_processing_status.py`
- Test: `tests/test_viewer_memory_merge_flow.py`

- [ ] **Step 1: Write the failing flow tests**

Add one end-to-end style unit test that injects a duplicate memory and verifies no second record is created, plus one supersede flow test.

```python
def test_process_event_merges_duplicate_memory_before_persisting(self):
    existing = build_memory(memory_id="mem-1", memory_text="喜欢拉面", memory_type="preference")
    merge_decision = MemoryMergeDecision(action="merge", target_memory_id="mem-1", reason="same_canonical")

    app_module.long_term_store.list_viewer_memories.return_value = [existing]
    app_module.vector_memory.similar_memories.return_value = [{"memory_id": "mem-1", "memory_text": "喜欢拉面", "score": 0.94, "metadata": {}}]
    app_module.memory_merge_service.decide.return_value = merge_decision

    asyncio.run(app_module.process_event(event))

    app_module.long_term_store.merge_viewer_memory_evidence.assert_called_once()
    app_module.long_term_store.save_viewer_memory.assert_not_called()
```

- [ ] **Step 2: Run the flow tests to verify they fail**

Run: `python -m unittest tests.test_comment_processing_status tests.test_viewer_memory_merge_flow`

Expected: FAIL because `process_event` always saves extracted candidates as new memories.

- [ ] **Step 3: Wire the merge service into runtime setup**

Instantiate the new merge service in [app.py](H:\DouYin_llm\backend\app.py) near the runtime wiring:

```python
memory_merge_service = ViewerMemoryMergeService()
```

And expose it to `process_event`.

- [ ] **Step 4: Add a helper that fetches same-viewer active memory candidates**

Use existing store/vector helpers so `process_event` can build a bounded candidate set:

```python
existing_memories = long_term_store.list_viewer_memories(event.room_id, event.user.viewer_id, limit=20)
similar_memories = vector_memory.similar_memories(candidate["memory_text"], event.room_id, event.user.viewer_id, limit=5)
decision = memory_merge_service.decide(candidate, existing_memories, similar_memories)
```

- [ ] **Step 5: Replace unconditional save with action-based persistence**

Update the persistence loop in [app.py](H:\DouYin_llm\backend\app.py) to dispatch actions:

```python
if decision.action == "create":
    memory = long_term_store.save_viewer_memory(...)
    vector_memory.sync_memory(memory)
elif decision.action == "merge":
    memory = long_term_store.merge_viewer_memory_evidence(...)
    vector_memory.sync_memory(memory)
elif decision.action == "upgrade":
    memory = long_term_store.upgrade_viewer_memory(...)
    vector_memory.sync_memory(memory)
elif decision.action == "supersede":
    old_memory, new_memory = long_term_store.supersede_viewer_memory(...)
    vector_memory.sync_memory(old_memory)
    vector_memory.sync_memory(new_memory)
```

Also update processing status metadata only if the tests require new flags; otherwise keep the current shape stable for this task.

- [ ] **Step 6: Run the flow tests to verify they pass**

Run: `python -m unittest tests.test_comment_processing_status tests.test_viewer_memory_merge_flow`

Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add backend/app.py backend/services/agent.py backend/memory/vector_store.py tests/test_comment_processing_status.py tests/test_viewer_memory_merge_flow.py
git commit -m "feat: merge viewer memories before persistence"
```

### Task 5: Add Focused Vector Recall Regression Coverage

**Files:**
- Modify: `backend/memory/vector_store.py:320`
- Test: `tests/test_verify_memory_pipeline.py`

- [ ] **Step 1: Write the failing regression tests**

Add tests that assert superseded memories do not appear in recall and upgraded memories refresh their vector text.

```python
def test_similar_memories_excludes_superseded_invalid_memory(self):
    recalled = vector.similar_memories("不能吃辣", room_id="room-1", viewer_id="id:user-1", limit=3)
    assert all(item["memory_id"] != old_memory_id for item in recalled)
```

- [ ] **Step 2: Run the recall tests to verify they fail**

Run: `python -m unittest tests.test_verify_memory_pipeline`

Expected: FAIL if invalidated superseded records still leak into recall or upgraded records do not refresh.

- [ ] **Step 3: Tighten vector sync behavior if needed**

Adjust [vector_store.py](H:\DouYin_llm\backend\memory\vector_store.py) only if the regression tests show a gap. The intended behavior is:

```python
def sync_memory(self, memory):
    if not memory or str(getattr(memory, "status", "active") or "active") != "active":
        self.remove_memory(getattr(memory, "memory_id", ""))
        return
    self.add_memory(memory)
```

Keep the implementation minimal and only fix what the tests prove is broken.

- [ ] **Step 4: Run the recall tests to verify they pass**

Run: `python -m unittest tests.test_verify_memory_pipeline`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/memory/vector_store.py tests/test_verify_memory_pipeline.py
git commit -m "test: cover merged and superseded memory recall behavior"
```

