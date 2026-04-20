# Memory Lifecycle Management Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add minimal lifecycle management to viewer memories so short-lived or explicitly time-bounded memories can expire out of recall without requiring a full dual-pool architecture.

**Architecture:** Extend `viewer_memories` with `lifecycle_kind` and `expires_at`, derive a minimal lifecycle policy from `temporal_scope`, and filter expired records out of store queries, index warmup, and vector recall. Keep the current `active / invalid / deleted` status model unchanged and let expiration work as an orthogonal recall gate rather than a new status family.

**Tech Stack:** Python, FastAPI backend, SQLite, Chroma vector store, unittest

---

### Task 1: Add Lifecycle Fields And Configuration

**Files:**
- Modify: `backend/config.py:121`
- Modify: `backend/schemas/live.py:65`
- Modify: `backend/memory/long_term.py:166`
- Test: `tests/test_long_term.py`

- [ ] **Step 1: Write the failing storage tests**

Add tests to [test_long_term.py](H:\DouYin_llm\tests\test_long_term.py) that require:

- new memories to expose `lifecycle_kind`
- new memories to expose `expires_at`
- default long-term memories to persist `lifecycle_kind="long_term"` and `expires_at=0`

```python
def test_save_viewer_memory_defaults_to_long_term_lifecycle(self):
    memory = self.store.save_viewer_memory(
        room_id="room-1",
        viewer_id="viewer-1",
        memory_text="租房住在公司附近",
        source_event_id="evt-1",
        memory_type="context",
        confidence=0.78,
    )

    self.assertEqual(memory.lifecycle_kind, "long_term")
    self.assertEqual(memory.expires_at, 0)
```

```python
def test_save_viewer_memory_persists_short_term_expiry(self):
    memory = self.store.save_viewer_memory(
        room_id="room-1",
        viewer_id="viewer-1",
        memory_text="这周都在上海出差",
        source_event_id="evt-1",
        memory_type="context",
        confidence=0.5,
        lifecycle_kind="short_term",
        expires_at=999999,
    )

    self.assertEqual(memory.lifecycle_kind, "short_term")
    self.assertEqual(memory.expires_at, 999999)
```

- [ ] **Step 2: Run the targeted test to verify it fails**

Run: `python -m unittest tests.test_long_term`

Expected: FAIL with missing fields or unexpected keyword arguments for `lifecycle_kind` / `expires_at`.

- [ ] **Step 3: Add the new config knob**

Update [config.py](H:\DouYin_llm\backend\config.py):

```python
memory_short_term_ttl_hours: float = field(
    default_factory=lambda: _env_float("MEMORY_SHORT_TERM_TTL_HOURS", 72.0)
)
```

- [ ] **Step 4: Extend `ViewerMemory` and SQLite schema**

Update [live.py](H:\DouYin_llm\backend\schemas\live.py):

```python
class ViewerMemory(BaseModel):
    ...
    lifecycle_kind: str = "long_term"
    expires_at: int = 0
```

Update [long_term.py](H:\DouYin_llm\backend\memory\long_term.py):

```python
CREATE TABLE IF NOT EXISTS viewer_memories (
    ...
    evidence_score REAL NOT NULL DEFAULT 0,
    lifecycle_kind TEXT NOT NULL DEFAULT 'long_term',
    expires_at INTEGER NOT NULL DEFAULT 0
);
```

And add both columns to `_ensure_viewer_memory_columns()`.

- [ ] **Step 5: Extend row parsing and `save_viewer_memory()`**

Update `save_viewer_memory()` to accept:

```python
def save_viewer_memory(
    ...,
    lifecycle_kind="long_term",
    expires_at=0,
):
    ...
```

Also update `_viewer_memory_from_row()` and the select lists in:

- `list_all_viewer_memories()`
- `list_viewer_memories()`
- `get_viewer_memory()`

- [ ] **Step 6: Run the storage tests to verify they pass**

Run: `python -m unittest tests.test_long_term`

Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add backend/config.py backend/schemas/live.py backend/memory/long_term.py tests/test_long_term.py
git commit -m "feat: add viewer memory lifecycle fields"
```

### Task 2: Filter Expired Memories Out Of Store Queries

**Files:**
- Modify: `backend/memory/long_term.py:783`
- Test: `tests/test_long_term.py`

- [ ] **Step 1: Write the failing query tests**

Add tests that verify expired memories do not show up in store query helpers.

```python
def test_list_viewer_memories_excludes_expired_records(self):
    active = self.store.save_viewer_memory(..., lifecycle_kind="long_term", expires_at=0)
    expired = self.store.save_viewer_memory(..., lifecycle_kind="short_term", expires_at=1)

    memories = self.store.list_viewer_memories("room-1", "viewer-1", limit=10, now_ms=1000)

    self.assertEqual([item["memory_id"] for item in memories], [active.memory_id])
```

```python
def test_list_all_viewer_memories_excludes_expired_records(self):
    ...
```

- [ ] **Step 2: Run the query tests to verify they fail**

Run: `python -m unittest tests.test_long_term`

Expected: FAIL because the current queries only filter `deleted`.

- [ ] **Step 3: Add a reusable expiry predicate**

In [long_term.py](H:\DouYin_llm\backend\memory\long_term.py), add a helper such as:

```python
def _active_not_deleted_and_not_expired_clause(now_ms):
    return "(status <> 'deleted') AND (expires_at = 0 OR expires_at > ?)"
```

Keep the implementation simple and local.

- [ ] **Step 4: Update query helpers**

Change:

- `list_all_viewer_memories()`
- `list_viewer_memories()`

to accept an optional `now_ms` argument and apply the expiry filter:

```python
def list_viewer_memories(self, room_id, viewer_id, limit=20, now_ms=None):
    now_ms = safe_int(now_ms, current_millis())
    ...
```

Do not change `get_viewer_memory()` yet; it should still return the row for audit and management use.

- [ ] **Step 5: Run the query tests to verify they pass**

Run: `python -m unittest tests.test_long_term`

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/memory/long_term.py tests/test_long_term.py
git commit -m "feat: filter expired viewer memories from store queries"
```

### Task 3: Filter Expired Memories Out Of Vector Warmup And Recall

**Files:**
- Modify: `backend/memory/vector_store.py:228`
- Test: `tests/test_vector_store.py`

- [ ] **Step 1: Write the failing vector tests**

Add tests to [test_vector_store.py](H:\DouYin_llm\tests\test_vector_store.py) proving expired memories are excluded from indexing and recall.

```python
def test_prime_memory_index_skips_expired_memories(self):
    memories = [
        SimpleNamespace(memory_id="m-live", ..., lifecycle_kind="long_term", expires_at=0, status="active"),
        SimpleNamespace(memory_id="m-expired", ..., lifecycle_kind="short_term", expires_at=1, status="active"),
    ]
    with patch("backend.memory.vector_store.time.time", return_value=10):
        store.prime_memory_index(memories, batch_size=64)

    self.assertEqual([item["id"] for item in store._memory_items], ["m-live"])
```

```python
def test_similar_memories_excludes_expired_metadata(self):
    ...
```

- [ ] **Step 2: Run the vector tests to verify they fail**

Run: `python -m unittest tests.test_vector_store`

Expected: FAIL because current index warmup and query logic only use `status`.

- [ ] **Step 3: Add an expiry helper to `VectorMemory`**

In [vector_store.py](H:\DouYin_llm\backend\memory\vector_store.py), add:

```python
@staticmethod
def _is_expired(metadata, now_ms):
    expires_at = int(metadata.get("expires_at") or 0)
    return expires_at > 0 and now_ms >= expires_at
```

- [ ] **Step 4: Apply the helper in warmup and recall**

Update:

- `_active_memory_records()`
- `similar_memories()`

so expired memories are skipped:

```python
if self._is_expired(metadata, now_ms):
    continue
```

Use `now_ms = int(time.time() * 1000)` once per query path, not repeatedly inside loops.

- [ ] **Step 5: Run the vector tests to verify they pass**

Run: `python -m unittest tests.test_vector_store`

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/memory/vector_store.py tests/test_vector_store.py
git commit -m "feat: exclude expired viewer memories from recall"
```

### Task 4: Derive Lifecycle Metadata At Save Time

**Files:**
- Modify: `backend/app.py:362`
- Test: `tests/test_comment_processing_status.py`

- [ ] **Step 1: Write the failing process-event test**

Add a targeted test that proves short-term candidates, when explicitly allowed to be saved, receive lifecycle metadata.

```python
def test_process_event_assigns_long_term_lifecycle_defaults_to_new_memory(self):
    ...
    app_module.long_term_store.save_viewer_memory.assert_called_with(
        ...,
        lifecycle_kind="long_term",
        expires_at=0,
    )
```

For this task, keep the test focused on the current create path and the default long-term case. Do not widen scope to separate short-term storage in this plan.

- [ ] **Step 2: Run the process-event test to verify it fails**

Run: `python -m unittest tests.test_comment_processing_status`

Expected: FAIL because `process_event()` does not yet pass lifecycle metadata to `save_viewer_memory()`.

- [ ] **Step 3: Add a small lifecycle helper in `app.py`**

Implement a helper like:

```python
def _candidate_lifecycle(candidate, created_at, settings):
    temporal_scope = str(candidate.get("temporal_scope") or "long_term")
    if temporal_scope == "short_term":
        ttl_hours = float(getattr(settings, "memory_short_term_ttl_hours", 72.0))
        return "short_term", created_at + int(ttl_hours * 3600 * 1000)
    return "long_term", 0
```

- [ ] **Step 4: Pass lifecycle metadata into `save_viewer_memory()`**

Update the create branch in [app.py](H:\DouYin_llm\backend\app.py):

```python
lifecycle_kind, expires_at = _candidate_lifecycle(candidate, event.ts, settings)
memory = long_term_store.save_viewer_memory(
    ...,
    lifecycle_kind=lifecycle_kind,
    expires_at=expires_at,
)
```

Do not change merge/upgrade/supersede semantics in this task.

- [ ] **Step 5: Run the process-event test to verify it passes**

Run: `python -m unittest tests.test_comment_processing_status`

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app.py tests/test_comment_processing_status.py
git commit -m "feat: assign lifecycle metadata to new viewer memories"
```

### Task 5: Update Documentation And Final Regression Coverage

**Files:**
- Modify: `README.md`
- Test: `tests/test_long_term.py`
- Test: `tests/test_vector_store.py`

- [ ] **Step 1: Write any final missing regression tests**

If coverage gaps remain after Tasks 1-4, add them now. Keep them narrow:

```python
def test_expired_memory_still_readable_by_id_for_audit(self):
    ...
```

- [ ] **Step 2: Run the combined regression suite to verify current behavior**

Run: `python -m unittest tests.test_long_term tests.test_vector_store tests.test_comment_processing_status`

Expected: PASS before doc updates are claimed complete.

- [ ] **Step 3: Update README lifecycle wording**

Adjust [README.md](H:\DouYin_llm\README.md) so it no longer says there is no decay at all if lifecycle expiration has been implemented. The doc should clearly distinguish:

- lightweight time decay
- explicit expiry / lifecycle fields

- [ ] **Step 4: Run the combined regression suite again**

Run: `python -m unittest tests.test_long_term tests.test_vector_store tests.test_comment_processing_status`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add README.md tests/test_long_term.py tests/test_vector_store.py tests/test_comment_processing_status.py
git commit -m "docs: describe viewer memory lifecycle management"
```

