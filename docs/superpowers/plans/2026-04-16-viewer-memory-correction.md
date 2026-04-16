# Viewer Memory Correction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add manual viewer-memory correction so the workbench can create, edit, invalidate, reactivate, pin, delete, and timeline-audit memories while keeping semantic recall in sync with the real current memory state.

**Architecture:** Extend the existing SQLite-backed `viewer_memories` model into a current-state table, add a new `viewer_memory_logs` audit table, and teach the vector layer to upsert or remove memories based on their current status. Reuse the existing `ViewerWorkbench` + `live` store pattern on the frontend, but split memory label/timeline formatting into a small presenter module so the component stays readable and the timeline logic remains testable.

**Tech Stack:** Python 3, FastAPI, SQLite, unittest, Vue 3, Pinia, plain ESM tests, Vite, Chroma-backed vector memory.

---

## File Structure

- Modify: `H:\DouYin_llm\backend\schemas\live.py`
  - Extend `ViewerMemory` with correction metadata and add a `ViewerMemoryLog` model for API responses.

- Modify: `H:\DouYin_llm\backend\memory\long_term.py`
  - Migrate `viewer_memories`, add `viewer_memory_logs`, implement CRUD/status/log methods, and keep all state + log writes transactional.

- Modify: `H:\DouYin_llm\backend\memory\vector_store.py`
  - Store status/source/pin metadata in the vector layer, add explicit remove/sync helpers, and ensure only active memories are recallable.

- Modify: `H:\DouYin_llm\backend\app.py`
  - Add viewer-memory request models and CRUD/log endpoints, and wire auto-extracted memories into the new storage contract.

- Modify: `H:\DouYin_llm\tests\test_long_term.py`
  - Add persistent-store coverage for save, edit, invalidate, reactivate, delete, filtering, and log history.

- Modify: `H:\DouYin_llm\tests\test_vector_store.py`
  - Add coverage for sync/remove behavior, active-only recall, and manual/pinned reranking.

- Create: `H:\DouYin_llm\tests\test_viewer_memory_api.py`
  - Cover route behavior without booting a browser or rewriting existing comment-status tests.

- Modify: `H:\DouYin_llm\tests\test_comment_processing_status.py`
  - Assert auto-extracted memories are saved with the new metadata contract.

- Modify: `H:\DouYin_llm\frontend\src\stores\live.js`
  - Add memory form state, edit state, per-memory log state, and workbench memory actions.

- Modify: `H:\DouYin_llm\frontend\src\stores\viewer-workbench.test.mjs`
  - Cover memory CRUD requests, error handling, and log loading.

- Create: `H:\DouYin_llm\frontend\src\components\viewer-memory-presenter.js`
  - Centralize memory status/source/action/timeline label mapping for the workbench.

- Create: `H:\DouYin_llm\frontend\src\components\viewer-memory-presenter.test.mjs`
  - Verify the presenter maps backend memory fields into the Chinese timeline UI model.

- Modify: `H:\DouYin_llm\frontend\src\components\ViewerWorkbench.vue`
  - Replace the memory read-only block with the mixed card + timeline UI and add the create/edit controls.

- Modify: `H:\DouYin_llm\frontend\src\App.vue`
  - Pass the new memory props and events from the `live` store into `ViewerWorkbench`.

- Modify: `H:\DouYin_llm\frontend\src\i18n.js`
  - Add Chinese and English strings for the memory correction workflow.

- Modify: `H:\DouYin_llm\README.md`
  - Document the new correction workflow and the rule that invalid/deleted memories do not participate in semantic recall.

### Task 1: Extend SQLite storage for memory state and audit logs

**Files:**
- Modify: `H:\DouYin_llm\backend\schemas\live.py`
- Modify: `H:\DouYin_llm\backend\memory\long_term.py`
- Modify: `H:\DouYin_llm\tests\test_long_term.py`

- [ ] **Step 1: Write the failing storage tests**

Append this new test class to `H:\DouYin_llm\tests\test_long_term.py` below the existing connect test:

```python
import os
import tempfile
import unittest

from backend.memory.long_term import LongTermStore


class ViewerMemoryCorrectionStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_path = os.path.join(self.temp_dir.name, "memory.db")
        self.store = LongTermStore(self.database_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_save_manual_memory_persists_extended_fields_and_created_log(self):
        memory = self.store.save_viewer_memory(
            room_id="room-1",
            viewer_id="viewer-1",
            memory_text="喜欢豚骨拉面",
            source_event_id="",
            memory_type="preference",
            confidence=0.96,
            source_kind="manual",
            status="active",
            is_pinned=True,
            correction_reason="主播手动补充",
            corrected_by="主播",
            operation="created",
        )

        self.assertEqual(memory.source_kind, "manual")
        self.assertEqual(memory.status, "active")
        self.assertTrue(memory.is_pinned)
        self.assertEqual(memory.correction_reason, "主播手动补充")
        self.assertEqual(memory.corrected_by, "主播")
        self.assertEqual(memory.last_operation, "created")

        listed = self.store.list_viewer_memories("room-1", "viewer-1", limit=10)
        self.assertEqual(len(listed), 1)
        self.assertEqual(listed[0]["memory_id"], memory.memory_id)

        logs = self.store.list_viewer_memory_logs(memory.memory_id, limit=10)
        self.assertEqual([log["operation"] for log in logs], ["created"])
        self.assertEqual(logs[0]["operator"], "主播")
        self.assertEqual(logs[0]["new_memory_text"], "喜欢豚骨拉面")

    def test_update_invalidate_reactivate_and_delete_change_state_and_logs(self):
        memory = self.store.save_viewer_memory(
            room_id="room-1",
            viewer_id="viewer-1",
            memory_text="喜欢拉面",
            source_event_id="evt-1",
            memory_type="preference",
            confidence=0.88,
            source_kind="auto",
            status="active",
            is_pinned=False,
            correction_reason="",
            corrected_by="system",
            operation="created",
        )

        edited = self.store.update_viewer_memory(
            memory_id=memory.memory_id,
            memory_text="喜欢豚骨拉面",
            memory_type="preference",
            is_pinned=True,
            correction_reason="自动抽取过于笼统",
            corrected_by="主播",
        )
        self.assertEqual(edited.memory_text, "喜欢豚骨拉面")
        self.assertTrue(edited.is_pinned)
        self.assertEqual(edited.last_operation, "edited")

        invalidated = self.store.invalidate_viewer_memory(
            memory.memory_id,
            reason="信息过期",
            corrected_by="主播",
        )
        self.assertEqual(invalidated.status, "invalid")
        self.assertEqual(invalidated.last_operation, "invalidated")

        reactivated = self.store.reactivate_viewer_memory(
            memory.memory_id,
            reason="重新确认仍然有效",
            corrected_by="主播",
        )
        self.assertEqual(reactivated.status, "active")
        self.assertEqual(reactivated.last_operation, "reactivated")

        deleted = self.store.delete_viewer_memory(
            memory.memory_id,
            reason="彻底删除错误记忆",
            corrected_by="主播",
        )
        self.assertEqual(deleted.status, "deleted")
        self.assertEqual(deleted.last_operation, "deleted")

        visible = self.store.list_viewer_memories("room-1", "viewer-1", limit=10)
        self.assertEqual(visible, [])

        logs = self.store.list_viewer_memory_logs(memory.memory_id, limit=10)
        self.assertEqual(
            [log["operation"] for log in logs],
            ["deleted", "reactivated", "invalidated", "edited", "created"],
        )
```

- [ ] **Step 2: Run the store tests and verify they fail on missing columns and methods**

Run: `python -m unittest tests.test_long_term -v`

Expected: FAIL with errors such as missing `source_kind` / `status` fields or missing methods like `list_viewer_memory_logs`.

- [ ] **Step 3: Implement the storage schema, models, and lifecycle methods**

Update `H:\DouYin_llm\backend\schemas\live.py`:

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


class ViewerMemoryLog(BaseModel):
    log_id: str
    memory_id: str
    room_id: str
    viewer_id: str
    operation: str
    operator: str = ""
    reason: str = ""
    old_memory_text: str = ""
    new_memory_text: str = ""
    old_memory_type: str = ""
    new_memory_type: str = ""
    old_status: str = ""
    new_status: str = ""
    old_is_pinned: bool = False
    new_is_pinned: bool = False
    created_at: int
```

Update `H:\DouYin_llm\backend\memory\long_term.py` with the schema additions and the new methods:

```python
CREATE TABLE IF NOT EXISTS viewer_memory_logs (
    log_id TEXT PRIMARY KEY,
    memory_id TEXT NOT NULL,
    room_id TEXT NOT NULL,
    viewer_id TEXT NOT NULL,
    operation TEXT NOT NULL,
    operator TEXT NOT NULL,
    reason TEXT NOT NULL,
    old_memory_text TEXT NOT NULL,
    new_memory_text TEXT NOT NULL,
    old_memory_type TEXT NOT NULL,
    new_memory_type TEXT NOT NULL,
    old_status TEXT NOT NULL,
    new_status TEXT NOT NULL,
    old_is_pinned INTEGER NOT NULL DEFAULT 0,
    new_is_pinned INTEGER NOT NULL DEFAULT 0,
    created_at INTEGER NOT NULL
);
```

```python
def _setup(self):
    with self._connect() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS viewer_memory_logs (
                log_id TEXT PRIMARY KEY,
                memory_id TEXT NOT NULL,
                room_id TEXT NOT NULL,
                viewer_id TEXT NOT NULL,
                operation TEXT NOT NULL,
                operator TEXT NOT NULL,
                reason TEXT NOT NULL,
                old_memory_text TEXT NOT NULL,
                new_memory_text TEXT NOT NULL,
                old_memory_type TEXT NOT NULL,
                new_memory_type TEXT NOT NULL,
                old_status TEXT NOT NULL,
                new_status TEXT NOT NULL,
                old_is_pinned INTEGER NOT NULL DEFAULT 0,
                new_is_pinned INTEGER NOT NULL DEFAULT 0,
                created_at INTEGER NOT NULL
            );
            """
        )
        self._ensure_event_columns(connection)
        self._ensure_viewer_profile_columns(connection)
        self._ensure_viewer_memory_columns(connection)
        self._create_indexes(connection)
        self._backfill_event_columns(connection)
        self._rebuild_viewer_aggregates(connection)
```

```python
def _ensure_viewer_memory_columns(self, connection):
    existing_columns = self._table_columns(connection, "viewer_memories")
    required_columns = {
        "source_kind": "TEXT NOT NULL DEFAULT 'auto'",
        "status": "TEXT NOT NULL DEFAULT 'active'",
        "is_pinned": "INTEGER NOT NULL DEFAULT 0",
        "correction_reason": "TEXT NOT NULL DEFAULT ''",
        "corrected_by": "TEXT NOT NULL DEFAULT ''",
        "last_operation": "TEXT NOT NULL DEFAULT 'created'",
        "last_operation_at": "INTEGER NOT NULL DEFAULT 0",
    }
    for column_name, column_type in required_columns.items():
        if column_name not in existing_columns:
            connection.execute(f"ALTER TABLE viewer_memories ADD COLUMN {column_name} {column_type}")
```

```python
def _viewer_memory_from_row(self, row):
    if not row:
        return None
    return ViewerMemory(
        memory_id=row["memory_id"],
        room_id=row["room_id"],
        viewer_id=row["viewer_id"],
        source_event_id=row["source_event_id"] or "",
        memory_text=row["memory_text"],
        memory_type=row["memory_type"] or "fact",
        confidence=row["confidence"] or 0.0,
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        last_recalled_at=row["last_recalled_at"],
        recall_count=row["recall_count"] or 0,
        source_kind=row["source_kind"] or "auto",
        status=row["status"] or "active",
        is_pinned=bool(row["is_pinned"]),
        correction_reason=row["correction_reason"] or "",
        corrected_by=row["corrected_by"] or "",
        last_operation=row["last_operation"] or "created",
        last_operation_at=row["last_operation_at"] or row["updated_at"],
    )
```

```python
def list_all_viewer_memories(self, limit=5000):
    limit = max(1, min(int(limit), 20000))
    with self._connect() as connection:
        rows = connection.execute(
            """
            SELECT memory_id, room_id, viewer_id, source_event_id, memory_text, memory_type,
                   confidence, created_at, updated_at, last_recalled_at, recall_count,
                   source_kind, status, is_pinned, correction_reason, corrected_by,
                   last_operation, last_operation_at
            FROM viewer_memories
            WHERE status <> 'deleted'
            ORDER BY updated_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [self._viewer_memory_from_row(row) for row in rows if row]
```

```python
def _append_viewer_memory_log(
    self,
    connection,
    memory_id,
    room_id,
    viewer_id,
    operation,
    operator="",
    reason="",
    old_memory_text="",
    new_memory_text="",
    old_memory_type="",
    new_memory_type="",
    old_status="",
    new_status="",
    old_is_pinned=False,
    new_is_pinned=False,
):
    connection.execute(
        """
        INSERT INTO viewer_memory_logs (
            log_id, memory_id, room_id, viewer_id, operation, operator, reason,
            old_memory_text, new_memory_text, old_memory_type, new_memory_type,
            old_status, new_status, old_is_pinned, new_is_pinned, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            str(uuid.uuid4()),
            memory_id,
            room_id,
            viewer_id,
            operation,
            operator,
            reason,
            old_memory_text,
            new_memory_text,
            old_memory_type,
            new_memory_type,
            old_status,
            new_status,
            1 if old_is_pinned else 0,
            1 if new_is_pinned else 0,
            current_millis(),
        ),
    )
```

```python
def get_viewer_memory(self, memory_id):
    with self._connect() as connection:
        row = connection.execute(
            """
            SELECT memory_id, room_id, viewer_id, source_event_id, memory_text, memory_type,
                   confidence, created_at, updated_at, last_recalled_at, recall_count,
                   source_kind, status, is_pinned, correction_reason, corrected_by,
                   last_operation, last_operation_at
            FROM viewer_memories
            WHERE memory_id = ?
            """,
            (memory_id,),
        ).fetchone()
    return self._viewer_memory_from_row(row)
```

```python
def list_viewer_memories(self, room_id, viewer_id, limit=20):
    if not viewer_id:
        return []
    limit = max(1, min(int(limit), 200))
    with self._connect() as connection:
        rows = connection.execute(
            """
            SELECT memory_id, room_id, viewer_id, source_event_id, memory_text, memory_type,
                   confidence, created_at, updated_at, last_recalled_at, recall_count,
                   source_kind, status, is_pinned, correction_reason, corrected_by,
                   last_operation, last_operation_at
            FROM viewer_memories
            WHERE room_id = ? AND viewer_id = ? AND status <> 'deleted'
            ORDER BY is_pinned DESC, updated_at DESC
            LIMIT ?
            """,
            (room_id, viewer_id, limit),
        ).fetchall()
    return [dict(row) for row in rows]
```

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
):
    room_id = safe_text(room_id)
    viewer_id = safe_text(viewer_id)
    memory_text = safe_text(memory_text)
    source_event_id = safe_text(source_event_id)
    memory_type = safe_text(memory_type) or "fact"
    source_kind = safe_text(source_kind) or "auto"
    status = safe_text(status) or "active"
    correction_reason = safe_text(correction_reason)
    corrected_by = safe_text(corrected_by)
    operation = safe_text(operation) or "created"
    if not room_id or not viewer_id or not memory_text:
        return None

    timestamp = current_millis()
    with self._connect() as connection:
        existing = connection.execute(
            """
            SELECT memory_id, created_at, last_recalled_at, recall_count
            FROM viewer_memories
            WHERE room_id = ? AND viewer_id = ? AND source_event_id = ? AND memory_text = ?
            LIMIT 1
            """,
            (room_id, viewer_id, source_event_id, memory_text),
        ).fetchone()
        memory_id = existing["memory_id"] if existing else str(uuid.uuid4())
        created_at = existing["created_at"] if existing else timestamp
        last_recalled_at = existing["last_recalled_at"] if existing else None
        recall_count = existing["recall_count"] if existing else 0
        connection.execute(
            """
            INSERT OR REPLACE INTO viewer_memories (
                memory_id, room_id, viewer_id, source_event_id, memory_text, memory_type,
                confidence, created_at, updated_at, last_recalled_at, recall_count,
                source_kind, status, is_pinned, correction_reason, corrected_by,
                last_operation, last_operation_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                memory_id, room_id, viewer_id, source_event_id, memory_text, memory_type,
                confidence, created_at, timestamp, last_recalled_at, recall_count,
                source_kind, status, 1 if is_pinned else 0, correction_reason, corrected_by,
                operation, timestamp,
            ),
        )
        self._append_viewer_memory_log(
            connection,
            memory_id=memory_id,
            room_id=room_id,
            viewer_id=viewer_id,
            operation=operation,
            operator=corrected_by,
            reason=correction_reason,
            new_memory_text=memory_text,
            new_memory_type=memory_type,
            new_status=status,
            new_is_pinned=is_pinned,
        )
    return self.get_viewer_memory(memory_id)
```

```python
def update_viewer_memory(self, memory_id, memory_text="", memory_type="", is_pinned=False, correction_reason="", corrected_by="主播"):
    existing = self.get_viewer_memory(memory_id)
    if not existing or existing.status == "deleted":
        return None
    timestamp = current_millis()
    next_text = safe_text(memory_text) or existing.memory_text
    next_type = safe_text(memory_type) or existing.memory_type
    next_reason = safe_text(correction_reason)
    next_is_pinned = bool(is_pinned) and existing.status == "active"
    operation = "edited"
    with self._connect() as connection:
        connection.execute(
            """
            UPDATE viewer_memories
            SET memory_text = ?, memory_type = ?, is_pinned = ?, correction_reason = ?,
                corrected_by = ?, updated_at = ?, last_operation = ?, last_operation_at = ?
            WHERE memory_id = ?
            """,
            (
                next_text, next_type, 1 if next_is_pinned else 0, next_reason,
                safe_text(corrected_by), timestamp, operation, timestamp, memory_id,
            ),
        )
        self._append_viewer_memory_log(
            connection,
            memory_id=existing.memory_id,
            room_id=existing.room_id,
            viewer_id=existing.viewer_id,
            operation=operation,
            operator=safe_text(corrected_by),
            reason=next_reason,
            old_memory_text=existing.memory_text,
            new_memory_text=next_text,
            old_memory_type=existing.memory_type,
            new_memory_type=next_type,
            old_status=existing.status,
            new_status=existing.status,
            old_is_pinned=existing.is_pinned,
            new_is_pinned=next_is_pinned,
        )
    return self.get_viewer_memory(memory_id)
```

```python
def _set_viewer_memory_status(self, memory_id, status, reason="", corrected_by="主播", operation="invalidated"):
    existing = self.get_viewer_memory(memory_id)
    if not existing or existing.status == "deleted":
        return None
    timestamp = current_millis()
    next_status = safe_text(status) or existing.status
    next_reason = safe_text(reason)
    next_is_pinned = existing.is_pinned if next_status == "active" else False
    with self._connect() as connection:
        connection.execute(
            """
            UPDATE viewer_memories
            SET status = ?, is_pinned = ?, correction_reason = ?, corrected_by = ?,
                updated_at = ?, last_operation = ?, last_operation_at = ?
            WHERE memory_id = ?
            """,
            (
                next_status,
                1 if next_is_pinned else 0,
                next_reason,
                safe_text(corrected_by),
                timestamp,
                operation,
                timestamp,
                memory_id,
            ),
        )
        self._append_viewer_memory_log(
            connection,
            memory_id=existing.memory_id,
            room_id=existing.room_id,
            viewer_id=existing.viewer_id,
            operation=operation,
            operator=safe_text(corrected_by),
            reason=next_reason,
            old_memory_text=existing.memory_text,
            new_memory_text=existing.memory_text,
            old_memory_type=existing.memory_type,
            new_memory_type=existing.memory_type,
            old_status=existing.status,
            new_status=next_status,
            old_is_pinned=existing.is_pinned,
            new_is_pinned=next_is_pinned,
        )
    return self.get_viewer_memory(memory_id)
```

```python
def invalidate_viewer_memory(self, memory_id, reason="", corrected_by="主播"):
    return self._set_viewer_memory_status(memory_id, status="invalid", reason=reason, corrected_by=corrected_by, operation="invalidated")


def reactivate_viewer_memory(self, memory_id, reason="", corrected_by="主播"):
    return self._set_viewer_memory_status(memory_id, status="active", reason=reason, corrected_by=corrected_by, operation="reactivated")


def delete_viewer_memory(self, memory_id, reason="", corrected_by="主播"):
    return self._set_viewer_memory_status(memory_id, status="deleted", reason=reason, corrected_by=corrected_by, operation="deleted")


def list_viewer_memory_logs(self, memory_id, limit=20):
    with self._connect() as connection:
        rows = connection.execute(
            """
            SELECT log_id, memory_id, room_id, viewer_id, operation, operator, reason,
                   old_memory_text, new_memory_text, old_memory_type, new_memory_type,
                   old_status, new_status, old_is_pinned, new_is_pinned, created_at
            FROM viewer_memory_logs
            WHERE memory_id = ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (memory_id, max(1, min(int(limit), 100))),
        ).fetchall()
    return [dict(row) for row in rows]
```

- [ ] **Step 4: Re-run the store tests**

Run: `python -m unittest tests.test_long_term -v`

Expected: PASS with the new lifecycle tests green.

- [ ] **Step 5: Commit the storage layer**

```bash
git -C H:\DouYin_llm add backend/schemas/live.py backend/memory/long_term.py tests/test_long_term.py
git -C H:\DouYin_llm commit -m "feat: add viewer memory correction storage"
```

### Task 2: Make vector recall honor active status, pinning, and removals

**Files:**
- Modify: `H:\DouYin_llm\backend\memory\vector_store.py`
- Modify: `H:\DouYin_llm\tests\test_vector_store.py`

- [ ] **Step 1: Add failing vector-store tests for sync and removal**

Update the imports in `H:\DouYin_llm\tests\test_vector_store.py` to include `SimpleNamespace`, then append these tests:

```python
from types import SimpleNamespace
```

```python
    def test_add_memory_includes_status_source_and_pin_metadata(self):
        fake_embedding = MagicMock()
        fake_embedding.embed_text.return_value = [0.1, 0.2]
        fake_collection = MagicMock()

        store = VectorMemory("data/chroma", settings=make_settings(), embedding_service=fake_embedding)
        store.memory_collection = fake_collection

        memory = SimpleNamespace(
            memory_id="mem-1",
            room_id="room-1",
            viewer_id="viewer-1",
            source_event_id="evt-1",
            memory_text="喜欢豚骨拉面",
            memory_type="preference",
            confidence=0.91,
            updated_at=123,
            recall_count=2,
            status="active",
            source_kind="manual",
            is_pinned=True,
        )

        store.add_memory(memory)

        upsert_kwargs = fake_collection.upsert.call_args.kwargs
        self.assertEqual(upsert_kwargs["metadatas"][0]["status"], "active")
        self.assertEqual(upsert_kwargs["metadatas"][0]["source_kind"], "manual")
        self.assertEqual(upsert_kwargs["metadatas"][0]["is_pinned"], 1)
```

```python
    def test_sync_memory_removes_deleted_or_invalid_entries(self):
        fake_embedding = MagicMock()
        fake_embedding.embed_text.return_value = [0.1, 0.2]
        fake_collection = MagicMock()

        store = VectorMemory("data/chroma", settings=make_settings(), embedding_service=fake_embedding)
        store.memory_collection = fake_collection
        store._memory_items = [
            {
                "id": "mem-1",
                "document": "喜欢拉面",
                "metadata": {
                    "room_id": "room-1",
                    "viewer_id": "viewer-1",
                    "status": "active",
                    "source_kind": "auto",
                    "is_pinned": 0,
                    "confidence": 0.8,
                    "updated_at": 10,
                    "recall_count": 1,
                },
            }
        ]

        store.sync_memory(
            SimpleNamespace(
                memory_id="mem-1",
                room_id="room-1",
                viewer_id="viewer-1",
                source_event_id="evt-1",
                memory_text="喜欢拉面",
                memory_type="preference",
                confidence=0.8,
                updated_at=20,
                recall_count=1,
                status="deleted",
                source_kind="auto",
                is_pinned=False,
            )
        )

        self.assertEqual(store._memory_items, [])
        fake_collection.delete.assert_called_once_with(ids=["mem-1"])
```

```python
    def test_similar_memories_prefers_manual_and_pinned_when_scores_are_close(self):
        fake_embedding = MagicMock()
        fake_embedding.embed_text.return_value = [0.1, 0.2]
        fake_collection = MagicMock()
        fake_collection.query.return_value = {
            "ids": [["m-auto", "m-manual"]],
            "documents": [["喜欢拉面", "喜欢拉面"]],
            "metadatas": [[
                {
                    "room_id": "room-1",
                    "viewer_id": "viewer-1",
                    "memory_type": "preference",
                    "confidence": 0.8,
                    "updated_at": 100,
                    "recall_count": 2,
                    "status": "active",
                    "source_kind": "auto",
                    "is_pinned": 0,
                },
                {
                    "room_id": "room-1",
                    "viewer_id": "viewer-1",
                    "memory_type": "preference",
                    "confidence": 0.8,
                    "updated_at": 90,
                    "recall_count": 2,
                    "status": "active",
                    "source_kind": "manual",
                    "is_pinned": 1,
                },
            ]],
            "distances": [[0.4, 0.4]],
        }

        store = VectorMemory("data/chroma", settings=make_settings(), embedding_service=fake_embedding)
        store.memory_collection = fake_collection

        result = store.similar_memories("喜欢拉面", "room-1", "viewer-1", limit=2)
        self.assertEqual(result[0]["memory_id"], "m-manual")
```

- [ ] **Step 2: Run the vector tests and verify the new cases fail**

Run: `python -m unittest tests.test_vector_store -v`

Expected: FAIL because the current vector layer does not expose `sync_memory`, does not remove deleted memories, and does not rank manual/pinned memories higher.

- [ ] **Step 3: Implement vector sync and ranking changes**

Update `H:\DouYin_llm\backend\memory\vector_store.py`:

```python
    @staticmethod
    def _memory_rank_key(item, query_text):
        text = str(item.get("memory_text") or "")
        metadata = item.get("metadata") or {}
        contains_query = 1 if query_text and query_text in text else 0
        confidence = float(metadata.get("confidence") or 0.0)
        recall_count = int(metadata.get("recall_count") or 0)
        updated_at = int(metadata.get("updated_at") or 0)
        source_kind = str(metadata.get("source_kind") or "auto")
        is_pinned = int(metadata.get("is_pinned") or 0)
        reranked_score = (
            float(item.get("score", 0.0))
            + (0.1 * confidence)
            + (0.02 * contains_query)
            + (0.01 * min(recall_count, 10))
            + (0.03 if source_kind == "manual" else 0.0)
            + (0.05 if is_pinned else 0.0)
        )
        return (reranked_score, updated_at)
```

```python
    def remove_memory(self, memory_id):
        memory_id = str(memory_id or "").strip()
        if not memory_id:
            return
        self._memory_items = [item for item in self._memory_items if item["id"] != memory_id]
        self._ensure_semantic_backend()
        if self.memory_collection:
            self.memory_collection.delete(ids=[memory_id])

    def sync_memory(self, memory):
        if not memory or str(getattr(memory, "status", "active") or "active") != "active":
            self.remove_memory(getattr(memory, "memory_id", ""))
            return
        self.add_memory(memory)
```

```python
    def add_memory(self, memory: ViewerMemory):
        if not memory.memory_text or not memory.viewer_id:
            return
        if str(getattr(memory, "status", "active") or "active") != "active":
            self.remove_memory(memory.memory_id)
            return

        metadata = {
            "room_id": memory.room_id,
            "viewer_id": memory.viewer_id,
            "memory_type": memory.memory_type,
            "source_event_id": memory.source_event_id,
            "confidence": memory.confidence,
            "updated_at": memory.updated_at,
            "recall_count": memory.recall_count,
            "status": getattr(memory, "status", "active"),
            "source_kind": getattr(memory, "source_kind", "auto"),
            "is_pinned": 1 if getattr(memory, "is_pinned", False) else 0,
        }
```

```python
                for index, memory_id in enumerate(ids):
                    metadata = metadatas[index] if index < len(metadatas) else {}
                    if str(metadata.get("status") or "active") != "active":
                        continue
                    score = self._distance_to_score(distances[index] if index < len(distances) else None)
                    if score < min_score:
                        continue
                    items.append(
                        {
                            "memory_id": memory_id,
                            "memory_text": documents[index] if index < len(documents) else "",
                            "score": score,
                            "metadata": metadata,
                        }
                    )
```

- [ ] **Step 4: Re-run the vector tests**

Run: `python -m unittest tests.test_vector_store -v`

Expected: PASS with sync/remove and ranking tests green.

- [ ] **Step 5: Commit the vector sync layer**

```bash
git -C H:\DouYin_llm add backend/memory/vector_store.py tests/test_vector_store.py
git -C H:\DouYin_llm commit -m "feat: sync viewer memory correction with vector recall"
```

### Task 3: Add backend APIs for memory correction and wire auto extraction into the new model

**Files:**
- Modify: `H:\DouYin_llm\backend\app.py`
- Create: `H:\DouYin_llm\tests\test_viewer_memory_api.py`
- Modify: `H:\DouYin_llm\tests\test_comment_processing_status.py`

- [ ] **Step 1: Write failing API and process-event tests**

Create `H:\DouYin_llm\tests\test_viewer_memory_api.py`:

```python
import asyncio
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock

import backend.app as app_module


class ViewerMemoryApiTests(unittest.TestCase):
    def setUp(self):
        self.original_store = app_module.long_term_store
        self.original_vector = app_module.vector_memory
        app_module.long_term_store = MagicMock()
        app_module.vector_memory = MagicMock()

    def tearDown(self):
        app_module.long_term_store = self.original_store
        app_module.vector_memory = self.original_vector

    def test_create_viewer_memory_uses_manual_defaults_and_syncs_vector_store(self):
        memory = SimpleNamespace(memory_id="mem-1", status="active")
        app_module.long_term_store.save_viewer_memory.return_value = memory

        payload = app_module.ViewerMemoryUpsertRequest(
            room_id="room-1",
            viewer_id="viewer-1",
            memory_text="喜欢豚骨拉面",
            memory_type="preference",
            is_pinned=True,
            correction_reason="主播补充",
        )

        result = asyncio.run(app_module.create_viewer_memory(payload))

        self.assertIs(result, memory)
        app_module.long_term_store.save_viewer_memory.assert_called_once_with(
            "room-1",
            "viewer-1",
            "喜欢豚骨拉面",
            source_event_id="",
            memory_type="preference",
            confidence=1.0,
            source_kind="manual",
            status="active",
            is_pinned=True,
            correction_reason="主播补充",
            corrected_by="主播",
            operation="created",
        )
        app_module.vector_memory.sync_memory.assert_called_once_with(memory)
```

```python
    def test_invalidate_delete_and_log_routes_call_store_methods(self):
        invalid = SimpleNamespace(memory_id="mem-1", status="invalid")
        deleted = SimpleNamespace(memory_id="mem-1", status="deleted")
        app_module.long_term_store.invalidate_viewer_memory.return_value = invalid
        app_module.long_term_store.delete_viewer_memory.return_value = deleted
        app_module.long_term_store.list_viewer_memory_logs.return_value = [{"operation": "created"}]

        status_payload = app_module.ViewerMemoryStatusRequest(reason="信息过期")

        invalidate_result = asyncio.run(app_module.invalidate_viewer_memory("mem-1", status_payload))
        delete_result = asyncio.run(app_module.delete_viewer_memory("mem-1", status_payload))
        logs_result = asyncio.run(app_module.viewer_memory_logs("mem-1", limit=10))

        self.assertIs(invalidate_result, invalid)
        self.assertIs(delete_result, deleted)
        self.assertEqual(logs_result, {"items": [{"operation": "created"}]})
        app_module.vector_memory.sync_memory.assert_called_once_with(invalid)
        app_module.vector_memory.remove_memory.assert_called_once_with("mem-1")
```

Append this assertion to `H:\DouYin_llm\tests\test_comment_processing_status.py` in the first `process_event` test after the existing `save_viewer_memory.return_value` setup:

```python
            app_module.long_term_store.save_viewer_memory.assert_called_with(
                room_id="room-1",
                viewer_id="id:user-1",
                memory_text="likes ramen",
                source_event_id="evt-1",
                memory_type="preference",
                confidence=0.91,
                source_kind="auto",
                status="active",
                is_pinned=False,
                correction_reason="",
                corrected_by="system",
                operation="created",
            )
```

- [ ] **Step 2: Run the backend API tests and confirm they fail**

Run: `python -m unittest tests.test_viewer_memory_api tests.test_comment_processing_status -v`

Expected: FAIL because the request models, routes, and new `save_viewer_memory` call signature are not implemented yet.

- [ ] **Step 3: Add request models, endpoints, and auto-memory metadata**

Update `H:\DouYin_llm\backend\app.py`:

```python
class ViewerMemoryUpsertRequest(BaseModel):
    room_id: str
    viewer_id: str
    memory_text: str
    memory_type: str = "fact"
    is_pinned: bool = False
    correction_reason: str = ""


class ViewerMemoryUpdateRequest(BaseModel):
    memory_text: str
    memory_type: str = "fact"
    is_pinned: bool = False
    correction_reason: str = ""


class ViewerMemoryStatusRequest(BaseModel):
    reason: str = ""
```

```python
        memory = long_term_store.save_viewer_memory(
            room_id=event.room_id,
            viewer_id=event.user.viewer_id,
            memory_text=candidate["memory_text"],
            source_event_id=event.event_id,
            memory_type=candidate["memory_type"],
            confidence=candidate["confidence"],
            source_kind="auto",
            status="active",
            is_pinned=False,
            correction_reason="",
            corrected_by="system",
            operation="created",
        )
        if memory:
            vector_memory.sync_memory(memory)
            saved_memory_ids.append(memory.memory_id)
```

```python
@app.post("/api/viewer/memories")
async def create_viewer_memory(payload: ViewerMemoryUpsertRequest):
    room_id = payload.room_id.strip()
    viewer_id = payload.viewer_id.strip()
    memory_text = payload.memory_text.strip()
    if not room_id:
        raise HTTPException(status_code=400, detail="room_id is required")
    if not viewer_id:
        raise HTTPException(status_code=400, detail="viewer_id is required")
    if not memory_text:
        raise HTTPException(status_code=400, detail="memory_text is required")
    memory = long_term_store.save_viewer_memory(
        room_id,
        viewer_id,
        memory_text,
        source_event_id="",
        memory_type=payload.memory_type.strip() or "fact",
        confidence=1.0,
        source_kind="manual",
        status="active",
        is_pinned=payload.is_pinned,
        correction_reason=payload.correction_reason,
        corrected_by="主播",
        operation="created",
    )
    vector_memory.sync_memory(memory)
    return memory
```

```python
@app.put("/api/viewer/memories/{memory_id}")
async def update_viewer_memory(memory_id: str, payload: ViewerMemoryUpdateRequest):
    memory = long_term_store.update_viewer_memory(
        memory_id=memory_id,
        memory_text=payload.memory_text,
        memory_type=payload.memory_type,
        is_pinned=payload.is_pinned,
        correction_reason=payload.correction_reason,
        corrected_by="主播",
    )
    if not memory:
        raise HTTPException(status_code=404, detail="memory not found")
    vector_memory.sync_memory(memory)
    return memory


@app.post("/api/viewer/memories/{memory_id}/invalidate")
async def invalidate_viewer_memory(memory_id: str, payload: ViewerMemoryStatusRequest):
    memory = long_term_store.invalidate_viewer_memory(memory_id, reason=payload.reason, corrected_by="主播")
    if not memory:
        raise HTTPException(status_code=404, detail="memory not found")
    vector_memory.sync_memory(memory)
    return memory


@app.post("/api/viewer/memories/{memory_id}/reactivate")
async def reactivate_viewer_memory(memory_id: str, payload: ViewerMemoryStatusRequest):
    memory = long_term_store.reactivate_viewer_memory(memory_id, reason=payload.reason, corrected_by="主播")
    if not memory:
        raise HTTPException(status_code=404, detail="memory not found")
    vector_memory.sync_memory(memory)
    return memory


@app.delete("/api/viewer/memories/{memory_id}")
async def delete_viewer_memory(memory_id: str, payload: ViewerMemoryStatusRequest):
    memory = long_term_store.delete_viewer_memory(memory_id, reason=payload.reason, corrected_by="主播")
    if not memory:
        raise HTTPException(status_code=404, detail="memory not found")
    vector_memory.remove_memory(memory_id)
    return memory


@app.get("/api/viewer/memories/{memory_id}/logs")
async def viewer_memory_logs(memory_id: str, limit: int = 20):
    return {"items": long_term_store.list_viewer_memory_logs(memory_id, limit=limit)}
```

- [ ] **Step 4: Re-run the backend API tests**

Run: `python -m unittest tests.test_viewer_memory_api tests.test_comment_processing_status -v`

Expected: PASS.

- [ ] **Step 5: Commit the backend API layer**

```bash
git -C H:\DouYin_llm add backend/app.py tests/test_viewer_memory_api.py tests/test_comment_processing_status.py
git -C H:\DouYin_llm commit -m "feat: add viewer memory correction api"
```

### Task 4: Add memory correction state and actions to the Pinia store

**Files:**
- Modify: `H:\DouYin_llm\frontend\src\stores\live.js`
- Modify: `H:\DouYin_llm\frontend\src\stores\viewer-workbench.test.mjs`

- [ ] **Step 1: Extend the store test to cover memory actions**

Append these cases to `H:\DouYin_llm\frontend\src\stores\viewer-workbench.test.mjs`:

```js
store.viewerWorkbench.viewer = {
  ...baseViewerPayload,
  memories: [
    {
      memory_id: "m1",
      memory_text: "喜欢拉面",
      memory_type: "preference",
      source_kind: "auto",
      status: "active",
      is_pinned: 0,
      correction_reason: "",
      last_operation: "created",
      last_operation_at: 1,
    },
  ],
};
```

```js
setFetch(async (url, options) => {
  if (url === "/api/viewer/memories" && options.method === "POST") {
    return {
      ok: true,
      async json() {
        return { memory_id: "m2" };
      },
    };
  }

  if (url.startsWith("/api/viewer?")) {
    return {
      ok: true,
      async json() {
        return {
          ...baseViewerPayload,
          memories: [
            {
              memory_id: "m2",
              memory_text: "喜欢豚骨拉面",
              memory_type: "preference",
              source_kind: "manual",
              status: "active",
              is_pinned: 1,
              correction_reason: "主播补充",
              last_operation: "created",
              last_operation_at: 2,
            },
          ],
          notes: [],
        };
      },
    };
  }

  throw new Error(`Unexpected request during memory create: ${url} ${options.method || "GET"}`);
});

store.setViewerMemoryDraft({
  memoryText: "喜欢豚骨拉面",
  memoryType: "preference",
  isPinned: true,
  correctionReason: "主播补充",
});
await store.saveActiveViewerMemory();
```

```js
const memoryCreate = requests.find(
  (request) => request.url === "/api/viewer/memories" && request.options.method === "POST",
);
assert.ok(memoryCreate);
assert.deepEqual(JSON.parse(memoryCreate.options.body), {
  room_id: "841354217566",
  viewer_id: "id:viewer-1",
  memory_text: "喜欢豚骨拉面",
  memory_type: "preference",
  is_pinned: true,
  correction_reason: "主播补充",
});
```

```js
setFetch(async (url, options) => {
  if (url === "/api/viewer/memories/m1/invalidate" && options.method === "POST") {
    return {
      ok: true,
      async json() {
        return { memory_id: "m1", status: "invalid" };
      },
    };
  }

  if (url === "/api/viewer/memories/m1/logs?limit=20") {
    return {
      ok: true,
      async json() {
        return {
          items: [
            { log_id: "l2", operation: "invalidated", reason: "信息过期" },
            { log_id: "l1", operation: "created", reason: "" },
          ],
        };
      },
    };
  }

  if (url.startsWith("/api/viewer?")) {
    return {
      ok: true,
      async json() {
        return {
          ...baseViewerPayload,
          memories: [
            {
              memory_id: "m1",
              memory_text: "喜欢拉面",
              memory_type: "preference",
              source_kind: "auto",
              status: "invalid",
              is_pinned: 0,
              correction_reason: "信息过期",
              last_operation: "invalidated",
              last_operation_at: 3,
            },
          ],
          notes: [],
        };
      },
    };
  }

  throw new Error(`Unexpected request during memory invalidation: ${url} ${options.method || "GET"}`);
});

await store.invalidateViewerMemory("m1", "信息过期");
await store.loadViewerMemoryLogs("m1");

assert.equal(store.viewerMemoryLogsById.m1.items.length, 2);
assert.equal(store.viewerWorkbench.viewer.memories[0].status, "invalid");
```

- [ ] **Step 2: Run the workbench store test and verify it fails**

Run: `node H:\DouYin_llm\frontend\src\stores\viewer-workbench.test.mjs`

Expected: FAIL because the store does not yet expose memory draft state, memory actions, or log loading.

- [ ] **Step 3: Implement the new memory state and actions in the store**

Update `H:\DouYin_llm\frontend\src\stores\live.js` with the new refs and actions:

```js
  const viewerMemoryDraft = ref({
    memoryText: "",
    memoryType: "fact",
    isPinned: false,
    correctionReason: "",
  });
  const editingViewerMemoryId = ref("");
  const isSavingViewerMemory = ref(false);
  const viewerMemoryLogsById = ref({});
```

```js
  function resetViewerMemoryEditor() {
    viewerMemoryDraft.value = {
      memoryText: "",
      memoryType: "fact",
      isPinned: false,
      correctionReason: "",
    };
    editingViewerMemoryId.value = "";
  }

  function setViewerMemoryDraft(patch) {
    viewerMemoryDraft.value = {
      ...viewerMemoryDraft.value,
      ...patch,
    };
  }

  function beginEditingViewerMemory(memory) {
    if (!memory) {
      resetViewerMemoryEditor();
      return;
    }
    editingViewerMemoryId.value = memory.memory_id || "";
    viewerMemoryDraft.value = {
      memoryText: memory.memory_text || "",
      memoryType: memory.memory_type || "fact",
      isPinned: Boolean(memory.is_pinned),
      correctionReason: memory.correction_reason || "",
    };
  }
```

```js
  async function saveActiveViewerMemory() {
    if (!viewerWorkbench.value.viewer || isSavingViewerMemory.value) {
      return;
    }
    const currentViewer = viewerWorkbench.value.viewer;
    if (!currentViewer.viewer_id) {
      viewerWorkbench.value.error = "errors.viewerIdRequiredToSaveMemories";
      return;
    }
    if (!viewerMemoryDraft.value.memoryText.trim()) {
      viewerWorkbench.value.error = "errors.viewerMemoryRequired";
      return;
    }
    const url = editingViewerMemoryId.value
      ? `/api/viewer/memories/${editingViewerMemoryId.value}`
      : "/api/viewer/memories";
    const method = editingViewerMemoryId.value ? "PUT" : "POST";
    const body = editingViewerMemoryId.value
      ? {
          memory_text: viewerMemoryDraft.value.memoryText,
          memory_type: viewerMemoryDraft.value.memoryType,
          is_pinned: viewerMemoryDraft.value.isPinned,
          correction_reason: viewerMemoryDraft.value.correctionReason,
        }
      : {
          room_id: currentViewer.room_id,
          viewer_id: currentViewer.viewer_id,
          memory_text: viewerMemoryDraft.value.memoryText,
          memory_type: viewerMemoryDraft.value.memoryType,
          is_pinned: viewerMemoryDraft.value.isPinned,
          correction_reason: viewerMemoryDraft.value.correctionReason,
        };
    isSavingViewerMemory.value = true;
    viewerWorkbench.value.error = "";
    try {
      const response = await fetch(url, {
        method,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!response.ok) {
        throw new Error(await getResponseError(response, "errors.viewerMemorySaveFailed"));
      }
      resetViewerMemoryEditor();
      await refreshViewerWorkbench();
    } catch (error) {
      viewerWorkbench.value.error = getViewerErrorMessage(error, "errors.viewerMemorySaveFailed");
    } finally {
      isSavingViewerMemory.value = false;
    }
  }
```

```js
  async function invalidateViewerMemory(memoryId, reason) {
    await updateViewerMemoryStatus(memoryId, "invalidate", reason);
  }

  async function reactivateViewerMemory(memoryId, reason) {
    await updateViewerMemoryStatus(memoryId, "reactivate", reason);
  }

  async function updateViewerMemoryStatus(memoryId, action, reason) {
    if (!memoryId) {
      return;
    }
    isSavingViewerMemory.value = true;
    viewerWorkbench.value.error = "";
    try {
      const response = await fetch(`/api/viewer/memories/${memoryId}/${action}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ reason }),
      });
      if (!response.ok) {
        throw new Error(await getResponseError(response, "errors.viewerMemoryStatusFailed"));
      }
      await refreshViewerWorkbench();
    } catch (error) {
      viewerWorkbench.value.error = getViewerErrorMessage(error, "errors.viewerMemoryStatusFailed");
    } finally {
      isSavingViewerMemory.value = false;
    }
  }

  async function toggleViewerMemoryPin(memory) {
    if (!memory) {
      return;
    }
    await beginEditingViewerMemory(memory);
    setViewerMemoryDraft({ isPinned: !Boolean(memory.is_pinned) });
    await saveActiveViewerMemory();
  }

  async function deleteViewerMemory(memoryId, reason) {
    if (!memoryId) {
      return;
    }
    isSavingViewerMemory.value = true;
    try {
      const response = await fetch(`/api/viewer/memories/${memoryId}`, {
        method: "DELETE",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ reason }),
      });
      if (!response.ok) {
        throw new Error(await getResponseError(response, "errors.viewerMemoryDeleteFailed"));
      }
      if (editingViewerMemoryId.value === memoryId) {
        resetViewerMemoryEditor();
      }
      await refreshViewerWorkbench();
    } catch (error) {
      viewerWorkbench.value.error = getViewerErrorMessage(error, "errors.viewerMemoryDeleteFailed");
    } finally {
      isSavingViewerMemory.value = false;
    }
  }
```

```js
  async function loadViewerMemoryLogs(memoryId) {
    if (!memoryId) {
      return;
    }
    viewerMemoryLogsById.value = {
      ...viewerMemoryLogsById.value,
      [memoryId]: {
        ...(viewerMemoryLogsById.value[memoryId] || {}),
        loading: true,
        error: "",
      },
    };
    try {
      const response = await fetch(`/api/viewer/memories/${memoryId}/logs?limit=20`);
      if (!response.ok) {
        throw new Error(await getResponseError(response, "errors.viewerMemoryLogsLoadFailed"));
      }
      const payload = await response.json();
      viewerMemoryLogsById.value = {
        ...viewerMemoryLogsById.value,
        [memoryId]: {
          loading: false,
          error: "",
          items: payload.items || [],
        },
      };
    } catch (error) {
      viewerMemoryLogsById.value = {
        ...viewerMemoryLogsById.value,
        [memoryId]: {
          loading: false,
          error: getViewerErrorMessage(error, "errors.viewerMemoryLogsLoadFailed"),
          items: [],
        },
      };
    }
  }
```

Expose the new store state and methods from the `return { ... }` block in `H:\DouYin_llm\frontend\src\stores\live.js`:

```js
    viewerMemoryDraft,
    editingViewerMemoryId,
    isSavingViewerMemory,
    viewerMemoryLogsById,
    setViewerMemoryDraft,
    beginEditingViewerMemory,
    saveActiveViewerMemory,
    invalidateViewerMemory,
    reactivateViewerMemory,
    deleteViewerMemory,
    toggleViewerMemoryPin,
    loadViewerMemoryLogs,
```

- [ ] **Step 4: Re-run the workbench store test**

Run: `node H:\DouYin_llm\frontend\src\stores\viewer-workbench.test.mjs`

Expected: PASS with memory create/invalidate/log loading coverage green.

- [ ] **Step 5: Commit the store work**

```bash
git -C H:\DouYin_llm add frontend/src/stores/live.js frontend/src/stores/viewer-workbench.test.mjs
git -C H:\DouYin_llm commit -m "feat: add viewer memory correction store actions"
```

### Task 5: Build the mixed card + timeline memory UI in the workbench

**Files:**
- Create: `H:\DouYin_llm\frontend\src\components\viewer-memory-presenter.js`
- Create: `H:\DouYin_llm\frontend\src\components\viewer-memory-presenter.test.mjs`
- Modify: `H:\DouYin_llm\frontend\src\components\ViewerWorkbench.vue`
- Modify: `H:\DouYin_llm\frontend\src\App.vue`
- Modify: `H:\DouYin_llm\frontend\src\i18n.js`

- [ ] **Step 1: Write the presenter test for Chinese status/timeline mapping**

Create `H:\DouYin_llm\frontend\src\components\viewer-memory-presenter.test.mjs`:

```js
import assert from "node:assert/strict";

import {
  canReactivateViewerMemory,
  canTogglePinViewerMemory,
  getViewerMemoryBadges,
  getViewerMemoryTimelinePreview,
} from "./viewer-memory-presenter.js";

const manualActivePinned = {
  memory_id: "m1",
  source_kind: "manual",
  status: "active",
  is_pinned: 1,
  correction_reason: "主播补充",
  last_operation: "edited",
};

assert.deepEqual(getViewerMemoryBadges(manualActivePinned), [
  "viewerWorkbench.memorySource.manual",
  "viewerWorkbench.memoryStatus.active",
  "viewerWorkbench.memoryPinned",
  "viewerWorkbench.memoryOperation.edited",
]);

assert.equal(
  getViewerMemoryTimelinePreview(manualActivePinned).labelKey,
  "viewerWorkbench.timeline.edited",
);
assert.equal(
  getViewerMemoryTimelinePreview(manualActivePinned).reason,
  "主播补充",
);
assert.equal(canTogglePinViewerMemory({ status: "active" }), true);
assert.equal(canTogglePinViewerMemory({ status: "invalid" }), false);
assert.equal(canReactivateViewerMemory({ status: "invalid" }), true);
assert.equal(canReactivateViewerMemory({ status: "active" }), false);
```

- [ ] **Step 2: Run the presenter test and confirm it fails on the missing module**

Run: `node H:\DouYin_llm\frontend\src\components\viewer-memory-presenter.test.mjs`

Expected: FAIL with a missing module error because the presenter file does not exist yet.

- [ ] **Step 3: Implement the presenter, UI template, and translations**

Create `H:\DouYin_llm\frontend\src\components\viewer-memory-presenter.js`:

```js
export function getViewerMemoryBadges(memory) {
  const badges = [
    memory?.source_kind === "manual"
      ? "viewerWorkbench.memorySource.manual"
      : "viewerWorkbench.memorySource.auto",
    memory?.status === "invalid"
      ? "viewerWorkbench.memoryStatus.invalid"
      : "viewerWorkbench.memoryStatus.active",
  ];

  if (memory?.is_pinned) {
    badges.push("viewerWorkbench.memoryPinned");
  }
  if (memory?.last_operation) {
    badges.push(`viewerWorkbench.memoryOperation.${memory.last_operation}`);
  }
  return badges;
}

export function getViewerMemoryTimelinePreview(memory) {
  return {
    labelKey: `viewerWorkbench.timeline.${memory?.last_operation || "created"}`,
    reason: memory?.correction_reason || "",
  };
}

export function canTogglePinViewerMemory(memory) {
  return memory?.status === "active";
}

export function canReactivateViewerMemory(memory) {
  return memory?.status === "invalid";
}
```

Update the `<script setup>` section of `H:\DouYin_llm\frontend\src\components\ViewerWorkbench.vue`:

```vue
import {
  canReactivateViewerMemory,
  canTogglePinViewerMemory,
  getViewerMemoryBadges,
  getViewerMemoryTimelinePreview,
} from "./viewer-memory-presenter.js";

const props = defineProps({
  locale: { type: String, required: true },
  open: { type: Boolean, required: true },
  viewer: { type: Object, default: null },
  loading: { type: Boolean, default: false },
  error: { type: String, default: "" },
  noteDraft: { type: String, default: "" },
  notePinned: { type: Boolean, default: false },
  saving: { type: Boolean, default: false },
  editingNoteId: { type: String, default: "" },
  memoryDraft: {
    type: Object,
    default: () => ({ memoryText: "", memoryType: "fact", isPinned: false, correctionReason: "" }),
  },
  editingMemoryId: { type: String, default: "" },
  memoryLogsById: {
    type: Object,
    default: () => ({}),
  },
});

const emit = defineEmits([
  "close",
  "update-note-draft",
  "toggle-note-pinned",
  "save-note",
  "edit-note",
  "delete-note",
  "update-memory-draft",
  "save-memory",
  "edit-memory",
  "invalidate-memory",
  "reactivate-memory",
  "delete-memory",
  "toggle-memory-pin",
  "load-memory-logs",
]);
```

Replace the memory section in `H:\DouYin_llm\frontend\src\components\ViewerWorkbench.vue` with:

```vue
      <section class="space-y-3">
        <p class="text-xs font-semibold uppercase tracking-widest text-muted">
          {{ t("viewerWorkbench.memories") }}
        </p>

        <div class="space-y-2 rounded-xl border border-line/20 bg-surface px-3 py-3">
          <textarea
            class="w-full rounded-xl border border-line/40 bg-panel px-3 py-2 text-xs text-paper outline-none transition placeholder:text-muted focus:border-accent"
            rows="3"
            :value="memoryDraft.memoryText"
            :placeholder="t('viewerWorkbench.memoryPlaceholder')"
            @input="emit('update-memory-draft', { memoryText: $event.target.value })"
          ></textarea>

          <input
            class="w-full rounded-xl border border-line/40 bg-panel px-3 py-2 text-xs text-paper outline-none transition placeholder:text-muted focus:border-accent"
            :value="memoryDraft.memoryType"
            :placeholder="t('viewerWorkbench.memoryTypePlaceholder')"
            @input="emit('update-memory-draft', { memoryType: $event.target.value })"
          />

          <input
            class="w-full rounded-xl border border-line/40 bg-panel px-3 py-2 text-xs text-paper outline-none transition placeholder:text-muted focus:border-accent"
            :value="memoryDraft.correctionReason"
            :placeholder="t('viewerWorkbench.memoryReasonPlaceholder')"
            @input="emit('update-memory-draft', { correctionReason: $event.target.value })"
          />

          <div class="flex items-center justify-between gap-3 text-xs text-muted">
            <button
              type="button"
              class="font-semibold text-paper transition hover:text-accent"
              @click="emit('update-memory-draft', { isPinned: !memoryDraft.isPinned })"
            >
              {{
                memoryDraft.isPinned
                  ? t("viewerWorkbench.unpinMemory")
                  : t("viewerWorkbench.pinMemory")
              }}
            </button>
            <button
              type="button"
              class="rounded-full bg-accent px-3 py-1 text-[11px] font-semibold text-ink transition hover:bg-accent/90"
              @click="emit('save-memory')"
            >
              {{
                editingMemoryId
                  ? t("viewerWorkbench.updateMemory")
                  : t("viewerWorkbench.saveMemory")
              }}
            </button>
          </div>
        </div>

        <article
          v-for="memory in viewer.memories || []"
          :key="memory.memory_id"
          class="rounded-xl border border-line/20 bg-surface px-3 py-3"
        >
          <p class="text-xs leading-relaxed text-paper">{{ memory.memory_text }}</p>
          <div class="mt-2 flex flex-wrap gap-2 text-[11px] uppercase tracking-[0.14em] text-muted">
            <span
              v-for="badgeKey in getViewerMemoryBadges(memory)"
              :key="badgeKey"
            >
              {{ t(badgeKey) }}
            </span>
          </div>
          <p class="mt-2 text-[11px] text-muted">
            {{ t(getViewerMemoryTimelinePreview(memory).labelKey) }}
            <span v-if="getViewerMemoryTimelinePreview(memory).reason">
              ：{{ getViewerMemoryTimelinePreview(memory).reason }}
            </span>
          </p>
          <div class="mt-3 flex flex-wrap gap-3 text-[11px] text-muted">
            <button type="button" class="font-semibold text-paper transition hover:text-accent" @click="emit('edit-memory', memory)">
              {{ t("common.edit") }}
            </button>
            <button
              v-if="memory.status === 'active'"
              type="button"
              class="font-semibold text-paper transition hover:text-accent"
              @click="emit('invalidate-memory', memory.memory_id, memory.correction_reason || t('viewerWorkbench.defaultInvalidateReason'))"
            >
              {{ t("viewerWorkbench.invalidateMemory") }}
            </button>
            <button
              v-if="canReactivateViewerMemory(memory)"
              type="button"
              class="font-semibold text-paper transition hover:text-accent"
              @click="emit('reactivate-memory', memory.memory_id, memory.correction_reason || t('viewerWorkbench.defaultReactivateReason'))"
            >
              {{ t("viewerWorkbench.reactivateMemory") }}
            </button>
            <button
              v-if="canTogglePinViewerMemory(memory)"
              type="button"
              class="font-semibold text-paper transition hover:text-accent"
              @click="emit('toggle-memory-pin', memory)"
            >
              {{ memory.is_pinned ? t("viewerWorkbench.unpinMemory") : t("viewerWorkbench.pinMemory") }}
            </button>
            <button
              type="button"
              class="font-semibold text-rose-500 transition hover:text-rose-400"
              @click="emit('delete-memory', memory.memory_id, memory.correction_reason || t('viewerWorkbench.defaultDeleteReason'))"
            >
              {{ t("common.delete") }}
            </button>
            <button
              type="button"
              class="font-semibold text-paper transition hover:text-accent"
              @click="emit('load-memory-logs', memory.memory_id)"
            >
              {{ t("viewerWorkbench.loadMemoryTimeline") }}
            </button>
          </div>
          <div v-if="memoryLogsById[memory.memory_id]?.items?.length" class="mt-3 space-y-2 border-l border-line/30 pl-3">
            <div
              v-for="log in memoryLogsById[memory.memory_id].items"
              :key="log.log_id"
              class="text-[11px] text-muted"
            >
              <p class="font-semibold text-paper">{{ t(`viewerWorkbench.timeline.${log.operation}`) }}</p>
              <p v-if="log.reason">{{ log.reason }}</p>
            </div>
          </div>
        </article>
      </section>
```

Update `H:\DouYin_llm\frontend\src\i18n.js` by adding these `viewerWorkbench` keys in both locales:

```js
      memoryPlaceholder: "补充一条观众记忆...",
      memoryTypePlaceholder: "记忆类型，例如 preference / context / plan",
      memoryReasonPlaceholder: "写明纠偏原因",
      pinMemory: "置顶记忆",
      unpinMemory: "取消置顶",
      saveMemory: "保存记忆",
      updateMemory: "更新记忆",
      invalidateMemory: "标记失效",
      reactivateMemory: "恢复有效",
      loadMemoryTimeline: "查看时间线",
      memoryPinned: "已置顶",
      defaultInvalidateReason: "人工标记失效",
      defaultReactivateReason: "人工恢复有效",
      defaultDeleteReason: "人工删除错误记忆",
      memorySource: {
        auto: "自动抽取",
        manual: "人工新增",
      },
      memoryStatus: {
        active: "有效",
        invalid: "已失效",
      },
      memoryOperation: {
        created: "已创建",
        edited: "人工修正",
        invalidated: "已失效",
        reactivated: "已恢复",
        pinned: "已置顶",
        unpinned: "已取消置顶",
        deleted: "已删除",
      },
      timeline: {
        created: "自动抽取",
        edited: "人工修正",
        invalidated: "标记失效",
        reactivated: "恢复有效",
        pinned: "置顶记忆",
        unpinned: "取消置顶",
        deleted: "删除记忆",
      },
```

Add these matching `errors` keys in both locales inside `H:\DouYin_llm\frontend\src\i18n.js`:

```js
      viewerMemorySaveFailed: "保存观众记忆失败",
      viewerMemoryDeleteFailed: "删除观众记忆失败",
      viewerMemoryLogsLoadFailed: "加载记忆时间线失败",
      viewerMemoryStatusFailed: "更新记忆状态失败",
      viewerMemoryRequired: "记忆内容不能为空",
      viewerIdRequiredToSaveMemories: "保存观众记忆需要可用的 viewer id",
```

Update `H:\DouYin_llm\frontend\src\App.vue` so the workbench receives the new store state and handlers:

```vue
const {
  isViewerWorkbenchOpen,
  viewerWorkbench,
  viewerNoteDraft,
  viewerNotePinned,
  isSavingViewerNote,
  editingViewerNoteId,
  viewerMemoryDraft,
  editingViewerMemoryId,
  isSavingViewerMemory,
  viewerMemoryLogsById,
} = storeToRefs(liveStore);
```

```vue
  <ViewerWorkbench
    :locale="locale"
    :open="isViewerWorkbenchOpen"
    :viewer="viewerWorkbench.viewer"
    :loading="viewerWorkbench.loading"
    :error="viewerWorkbench.error"
    :note-draft="viewerNoteDraft"
    :note-pinned="viewerNotePinned"
    :saving="isSavingViewerNote || isSavingViewerMemory"
    :editing-note-id="editingViewerNoteId"
    :memory-draft="viewerMemoryDraft"
    :editing-memory-id="editingViewerMemoryId"
    :memory-logs-by-id="viewerMemoryLogsById"
    @close="liveStore.closeViewerWorkbench"
    @update-note-draft="liveStore.setViewerNoteDraft"
    @toggle-note-pinned="liveStore.toggleViewerNotePinned"
    @save-note="liveStore.saveActiveViewerNote"
    @edit-note="liveStore.beginEditingViewerNote"
    @delete-note="liveStore.deleteViewerNote"
    @update-memory-draft="liveStore.setViewerMemoryDraft"
    @save-memory="liveStore.saveActiveViewerMemory"
    @edit-memory="liveStore.beginEditingViewerMemory"
    @invalidate-memory="liveStore.invalidateViewerMemory"
    @reactivate-memory="liveStore.reactivateViewerMemory"
    @delete-memory="liveStore.deleteViewerMemory"
    @toggle-memory-pin="liveStore.toggleViewerMemoryPin"
    @load-memory-logs="liveStore.loadViewerMemoryLogs"
  />
```

- [ ] **Step 4: Run the presenter test and the frontend build**

Run: `node H:\DouYin_llm\frontend\src\components\viewer-memory-presenter.test.mjs`

Expected: PASS.

Run: `npm --prefix H:\DouYin_llm\frontend run build`

Expected: PASS with a production bundle emitted by Vite.

- [ ] **Step 5: Commit the UI layer**

```bash
git -C H:\DouYin_llm add frontend/src/components/viewer-memory-presenter.js frontend/src/components/viewer-memory-presenter.test.mjs frontend/src/components/ViewerWorkbench.vue frontend/src/App.vue frontend/src/i18n.js
git -C H:\DouYin_llm commit -m "feat: add viewer memory correction timeline ui"
```

### Task 6: Document the feature and run the focused regression suite

**Files:**
- Modify: `H:\DouYin_llm\README.md`

- [ ] **Step 1: Add README documentation for the correction workflow**

Update the feature and usage sections of `H:\DouYin_llm\README.md` with:

```md
### 观众记忆人工纠偏

在右侧观众工作台中，主播可以对单个观众记忆执行以下操作：

- 人工新增记忆
- 编辑自动抽取或人工新增的记忆文本
- 标记记忆失效
- 恢复失效记忆
- 置顶高优先级记忆
- 删除错误记忆
- 查看单条记忆的处理时间线

语义召回规则：

- `active` 记忆才会参与语义召回
- `invalid` 和 `deleted` 记忆不会参与语义召回
- 人工新增和置顶记忆在排序上优先级更高
```

- [ ] **Step 2: Run the focused regression suite**

Run: `python -m unittest tests.test_long_term tests.test_vector_store tests.test_viewer_memory_api tests.test_comment_processing_status -v`

Expected: PASS.

Run: `node H:\DouYin_llm\frontend\src\stores\viewer-workbench.test.mjs`

Expected: PASS.

Run: `node H:\DouYin_llm\frontend\src\components\viewer-memory-presenter.test.mjs`

Expected: PASS.

Run: `npm --prefix H:\DouYin_llm\frontend run build`

Expected: PASS.

- [ ] **Step 3: Commit the docs and regression checkpoint**

```bash
git -C H:\DouYin_llm add README.md
git -C H:\DouYin_llm commit -m "docs: describe viewer memory correction workflow"
```
