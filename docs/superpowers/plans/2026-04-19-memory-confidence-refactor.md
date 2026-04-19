# Memory Confidence Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the current mechanical viewer-memory confidence score with a multi-factor confidence model that is persisted, testable, and refreshed during merge and upgrade operations.

**Architecture:** Add four persisted confidence sub-scores to `viewer_memories`, introduce a dedicated `memory_confidence_service` that computes the sub-scores plus final `confidence`, and make `save_viewer_memory`, `merge_viewer_memory_evidence`, and `upgrade_viewer_memory` recompute scores instead of treating confidence as a one-time static value. Keep `VectorMemory` compatible by continuing to use the final `confidence` field for ranking while exposing the sub-scores for later rerank work.

**Tech Stack:** Python, FastAPI backend, SQLite, Chroma vector store, unittest

---

### Task 1: Extend Viewer Memory Schema With Confidence Sub-Scores

**Files:**
- Modify: `backend/schemas/live.py:65`
- Modify: `backend/memory/long_term.py:177`
- Test: `tests/test_long_term.py`

- [ ] **Step 1: Write the failing storage tests**

Add tests to [test_long_term.py](H:\DouYin_llm\tests\test_long_term.py) that require the new sub-score fields to exist on stored `ViewerMemory` rows and default safely for migrated rows.

```python
def test_save_viewer_memory_persists_confidence_subscores(self):
    memory = self.store.save_viewer_memory(
        room_id="room-1",
        viewer_id="viewer-1",
        memory_text="不太能吃辣",
        source_event_id="evt-1",
        memory_type="preference",
        confidence=0.82,
        stability_score=0.95,
        interaction_value_score=0.9,
        clarity_score=0.8,
        evidence_score=0.4,
    )

    self.assertEqual(memory.stability_score, 0.95)
    self.assertEqual(memory.interaction_value_score, 0.9)
    self.assertEqual(memory.clarity_score, 0.8)
    self.assertEqual(memory.evidence_score, 0.4)
```

```python
def test_existing_rows_default_new_confidence_subscores_to_zero(self):
    memory = self.store.save_viewer_memory(...)
    with self.store._connect() as connection:
        connection.execute("UPDATE viewer_memories SET stability_score = 0, interaction_value_score = 0, clarity_score = 0, evidence_score = 0 WHERE memory_id = ?", (memory.memory_id,))

    fetched = self.store.get_viewer_memory(memory.memory_id)
    self.assertEqual(fetched.stability_score, 0.0)
    self.assertEqual(fetched.interaction_value_score, 0.0)
    self.assertEqual(fetched.clarity_score, 0.0)
    self.assertEqual(fetched.evidence_score, 0.0)
```

- [ ] **Step 2: Run the targeted test to verify it fails**

Run: `python -m unittest tests.test_long_term`

Expected: FAIL with missing SQLite columns, missing model fields, or `save_viewer_memory()` rejecting the new kwargs.

- [ ] **Step 3: Extend `ViewerMemory` with the new fields**

Update [live.py](H:\DouYin_llm\backend\schemas\live.py):

```python
class ViewerMemory(BaseModel):
    ...
    stability_score: float = 0.0
    interaction_value_score: float = 0.0
    clarity_score: float = 0.0
    evidence_score: float = 0.0
```

- [ ] **Step 4: Add the SQLite columns and row parsing**

Update [long_term.py](H:\DouYin_llm\backend\memory\long_term.py):

```python
CREATE TABLE IF NOT EXISTS viewer_memories (
    ...
    merge_parent_id TEXT NOT NULL DEFAULT '',
    stability_score REAL NOT NULL DEFAULT 0,
    interaction_value_score REAL NOT NULL DEFAULT 0,
    clarity_score REAL NOT NULL DEFAULT 0,
    evidence_score REAL NOT NULL DEFAULT 0
);
```

Also update `_ensure_viewer_memory_columns()`, `_viewer_memory_from_row()`, `list_all_viewer_memories()`, `list_viewer_memories()`, and `get_viewer_memory()` to read the new columns.

- [ ] **Step 5: Extend `save_viewer_memory()` signature to accept explicit sub-scores**

Update the function signature and `INSERT OR REPLACE` payload:

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
    stability_score=0.0,
    interaction_value_score=0.0,
    clarity_score=0.0,
    evidence_score=0.0,
):
    ...
```

- [ ] **Step 6: Run the storage tests to verify they pass**

Run: `python -m unittest tests.test_long_term`

Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add backend/schemas/live.py backend/memory/long_term.py tests/test_long_term.py
git commit -m "feat: persist viewer memory confidence sub-scores"
```

### Task 2: Implement The Confidence Scoring Service

**Files:**
- Create: `backend/services/memory_confidence_service.py`
- Test: `tests/test_memory_confidence_service.py`

- [ ] **Step 1: Write the failing service tests**

Create [test_memory_confidence_service.py](H:\DouYin_llm\tests\test_memory_confidence_service.py) with focused rule-based expectations.

```python
def test_score_new_memory_prefers_long_term_food_restriction_over_short_term_status(self):
    service = MemoryConfidenceService()

    stable = service.score_new_memory(
        {
            "memory_text": "不太能吃辣",
            "memory_text_raw": "我平时都不太能吃辣",
            "memory_text_canonical": "不太能吃辣",
            "memory_type": "preference",
            "temporal_scope": "long_term",
        }
    )
    short_term = service.score_new_memory(
        {
            "memory_text": "这周都在上海出差",
            "memory_text_raw": "这周我都在上海出差",
            "memory_text_canonical": "这周都在上海出差",
            "memory_type": "context",
            "temporal_scope": "short_term",
        }
    )

    self.assertGreater(stable["stability_score"], short_term["stability_score"])
    self.assertGreater(stable["confidence"], short_term["confidence"])
```

```python
def test_score_new_memory_rewards_clear_short_canonical(self):
    service = MemoryConfidenceService()
    concise = service.score_new_memory({... "memory_text_canonical": "租房住在公司附近"})
    noisy = service.score_new_memory({... "memory_text_canonical": "我其实是租房住在公司附近这样通勤方便一点"})
    self.assertGreater(concise["clarity_score"], noisy["clarity_score"])
```

- [ ] **Step 2: Run the targeted test to verify it fails**

Run: `python -m unittest tests.test_memory_confidence_service`

Expected: FAIL with module not found.

- [ ] **Step 3: Create the service skeleton**

Create [memory_confidence_service.py](H:\DouYin_llm\backend\services\memory_confidence_service.py):

```python
class MemoryConfidenceService:
    def score_new_memory(self, candidate: dict) -> dict:
        ...

    def score_existing_memory_update(self, memory, *, evidence_increment=0, candidate: dict | None = None, upgraded_text: str = "") -> dict:
        ...
```

- [ ] **Step 4: Implement first-pass scoring rules**

Use explicit helper functions and keep them deterministic:

```python
def _score_stability(self, candidate):
    ...

def _score_interaction_value(self, candidate):
    ...

def _score_clarity(self, candidate):
    ...

def _score_evidence(self, evidence_count, last_confirmed_at):
    ...
```

And combine them with:

```python
confidence = round(
    (0.35 * stability_score)
    + (0.35 * interaction_value_score)
    + (0.15 * clarity_score)
    + (0.15 * evidence_score),
    4,
)
```

- [ ] **Step 5: Add explicit signal rules**

Implement at least these first-pass rules:

```python
SHORT_TERM_HINTS = ("今天", "今晚", "这周", "最近", "下周", "下个月")
HIGH_VALUE_HINTS = ("不能吃", "不太能吃", "忌口", "喜欢", "职业", "上班", "租房", "住在", "养了", "安卓")
NOISY_SHELL_TOKENS = ("是不是", "其实", "吧", "啊", "呢", "吗")
```

Expected behavior:

- `temporal_scope == "long_term"` lifts `stability_score`
- short-term hints lower `stability_score`
- obvious food restrictions, preferences, living context, work context, and pet context lift `interaction_value_score`
- shorter cleaner canonical strings lift `clarity_score`
- first-write `evidence_score` starts near `0.35`

- [ ] **Step 6: Run the scoring tests to verify they pass**

Run: `python -m unittest tests.test_memory_confidence_service`

Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add backend/services/memory_confidence_service.py tests/test_memory_confidence_service.py
git commit -m "feat: add multi-factor memory confidence scoring"
```

### Task 3: Integrate Confidence Scoring Into Memory Creation

**Files:**
- Modify: `backend/app.py`
- Modify: `backend/services/llm_memory_extractor.py:94`
- Modify: `backend/services/memory_extractor.py`
- Modify: `backend/memory/long_term.py:860`
- Test: `tests/test_comment_processing_status.py`
- Test: `tests/test_long_term.py`

- [ ] **Step 1: Write the failing integration tests**

Add a test proving new memories are persisted with sub-scores and a computed final confidence.

```python
def test_process_event_persists_new_memory_with_confidence_subscores(self):
    ...
    app_module.memory_confidence_service.score_new_memory.return_value = {
        "stability_score": 0.95,
        "interaction_value_score": 0.9,
        "clarity_score": 0.8,
        "evidence_score": 0.35,
        "confidence": 0.8225,
    }

    asyncio.run(app_module.process_event(event))

    app_module.long_term_store.save_viewer_memory.assert_called_with(
        ...,
        confidence=0.8225,
        stability_score=0.95,
        interaction_value_score=0.9,
        clarity_score=0.8,
        evidence_score=0.35,
    )
```

- [ ] **Step 2: Run the integration tests to verify they fail**

Run: `python -m unittest tests.test_comment_processing_status tests.test_long_term`

Expected: FAIL because `process_event()` still forwards raw extractor confidence without sub-scores.

- [ ] **Step 3: Instantiate the confidence service in runtime setup**

Update [app.py](H:\DouYin_llm\backend\app.py):

```python
from backend.services.memory_confidence_service import MemoryConfidenceService

memory_confidence_service = None

if memory_confidence_service is None:
    memory_confidence_service = MemoryConfidenceService()
```

- [ ] **Step 4: Ensure extracted candidates carry the minimum scoring inputs**

Make sure LLM and rule extraction candidates consistently include what the scoring service needs:

```python
{
    "memory_text": canonical_text,
    "memory_text_raw": raw_text,
    "memory_text_canonical": canonical_text,
    "memory_type": memory_type,
    "temporal_scope": "long_term",
    ...
}
```

Do not expand scope beyond the fields needed by the scoring service.

- [ ] **Step 5: Compute scores before calling `save_viewer_memory()`**

In [app.py](H:\DouYin_llm\backend\app.py), on the `create` branch:

```python
score = memory_confidence_service.score_new_memory(candidate)
memory = long_term_store.save_viewer_memory(
    ...,
    confidence=score["confidence"],
    stability_score=score["stability_score"],
    interaction_value_score=score["interaction_value_score"],
    clarity_score=score["clarity_score"],
    evidence_score=score["evidence_score"],
)
```

- [ ] **Step 6: Run the integration tests to verify they pass**

Run: `python -m unittest tests.test_comment_processing_status tests.test_long_term`

Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add backend/app.py backend/services/llm_memory_extractor.py backend/services/memory_extractor.py backend/memory/long_term.py tests/test_comment_processing_status.py tests/test_long_term.py
git commit -m "feat: score new viewer memories with confidence sub-scores"
```

### Task 4: Refresh Confidence On Merge And Upgrade

**Files:**
- Modify: `backend/memory/long_term.py:1041`
- Modify: `backend/services/memory_confidence_service.py`
- Modify: `backend/app.py`
- Test: `tests/test_long_term.py`
- Test: `tests/test_viewer_memory_merge_flow.py`

- [ ] **Step 1: Write the failing update tests**

Add targeted tests that prove merge and upgrade refresh the sub-scores instead of only incrementing counters.

```python
def test_merge_viewer_memory_evidence_refreshes_evidence_score(self):
    ...
    merged = self.store.merge_viewer_memory_evidence(...)
    self.assertGreater(merged.evidence_score, original.evidence_score)
    self.assertGreaterEqual(merged.confidence, original.confidence)
```

```python
def test_upgrade_viewer_memory_refreshes_clarity_score(self):
    ...
    upgraded = self.store.upgrade_viewer_memory(...)
    self.assertGreater(upgraded.clarity_score, original.clarity_score)
```

- [ ] **Step 2: Run the update tests to verify they fail**

Run: `python -m unittest tests.test_long_term tests.test_viewer_memory_merge_flow`

Expected: FAIL because merge/upgrade helpers currently do not recompute any confidence sub-scores.

- [ ] **Step 3: Expand the confidence service for lifecycle updates**

Implement `score_existing_memory_update()` in [memory_confidence_service.py](H:\DouYin_llm\backend\services\memory_confidence_service.py):

```python
def score_existing_memory_update(self, memory, *, evidence_increment=0, candidate: dict | None = None, upgraded_text: str = "") -> dict:
    next_evidence_count = max(1, memory.evidence_count + evidence_increment)
    ...
```

Use the same weighted formula as creation, but:

- raise `evidence_score` when `evidence_count` grows
- raise `clarity_score` if `upgraded_text` is cleaner/more specific than the old text

- [ ] **Step 4: Recompute scores inside merge and upgrade persistence helpers**

Update [long_term.py](H:\DouYin_llm\backend\memory\long_term.py):

```python
scores = confidence_service.score_existing_memory_update(
    existing,
    evidence_increment=1,
    candidate={"memory_text_raw": raw_memory_text, "memory_text_canonical": existing.memory_text, ...},
)
```

Then persist:

```python
confidence=scores["confidence"]
stability_score=scores["stability_score"]
interaction_value_score=scores["interaction_value_score"]
clarity_score=scores["clarity_score"]
evidence_score=scores["evidence_score"]
```

- [ ] **Step 5: Thread the confidence service into the merge and upgrade call path**

Update [app.py](H:\DouYin_llm\backend\app.py) so the `merge` and `upgrade` branches pass the necessary candidate context into the store helpers or call the scoring service before them. Keep the shape consistent with the existing merge flow.

- [ ] **Step 6: Run the update tests to verify they pass**

Run: `python -m unittest tests.test_long_term tests.test_viewer_memory_merge_flow`

Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add backend/memory/long_term.py backend/services/memory_confidence_service.py backend/app.py tests/test_long_term.py tests/test_viewer_memory_merge_flow.py
git commit -m "feat: refresh memory confidence on merge and upgrade"
```

### Task 5: Add Confidence Regression Coverage For Recall And Evaluation

**Files:**
- Modify: `backend/memory/vector_store.py:320`
- Modify: `tests/memory_pipeline_verifier/runner.py`
- Test: `tests/test_vector_store.py`
- Test: `tests/test_verify_memory_pipeline.py`

- [ ] **Step 1: Write the failing regression tests**

Add tests that prove the new confidence numbers influence ranking and that the verifier can inspect the sub-scores.

```python
def test_similar_memories_prefers_higher_confidence_when_semantic_scores_are_close(self):
    ...
    self.assertEqual(result[0]["memory_id"], "m-high-confidence")
```

```python
def test_validate_memory_extraction_payload_preserves_confidence_subscores(self):
    payload = validate_memory_extraction_payload({...})
    self.assertIn("stability_score", payload)
```

- [ ] **Step 2: Run the regression tests to verify they fail**

Run: `python -m unittest tests.test_vector_store tests.test_verify_memory_pipeline`

Expected: FAIL if the tests require sub-scores that are not yet surfaced.

- [ ] **Step 3: Update only the minimal ranking and verifier surfaces**

If the tests prove a gap, adjust [vector_store.py](H:\DouYin_llm\backend\memory\vector_store.py) and [runner.py](H:\DouYin_llm\tests\memory_pipeline_verifier\runner.py) minimally:

```python
reranked_score = (
    float(item.get("score", 0.0))
    + (0.10 * confidence)
    + (0.03 * interaction_value_score)
    + (0.02 * evidence_score)
    + ...
)
```

And make verifier helpers preserve the sub-score fields when available.

- [ ] **Step 4: Run the regression tests to verify they pass**

Run: `python -m unittest tests.test_vector_store tests.test_verify_memory_pipeline`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/memory/vector_store.py tests/memory_pipeline_verifier/runner.py tests/test_vector_store.py tests/test_verify_memory_pipeline.py
git commit -m "test: cover confidence sub-score ranking and evaluation"
```

