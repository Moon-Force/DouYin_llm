# Memory Rerank Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refactor viewer memory ranking into an explicit feature rerank so memories most useful for live prompting consistently rank ahead of generic but semantically similar background memories.

**Architecture:** Keep semantic retrieval as the first stage but make `VectorMemory` compute a clear `semantic_score`, a structured `business_rerank_score`, and a combined `final_score`. The business rerank will explicitly use `interaction_value_score`, `evidence_score`, `stability_score`, `confidence`, `source_kind`, `is_pinned`, `recall_count`, and time decay, while preserving strict mode, token fallback, and expiry filtering behavior.

**Tech Stack:** Python, Chroma vector recall, unittest

---

### Task 1: Split Ranking Into Semantic Score, Business Rerank Score, And Final Score

**Files:**
- Modify: `backend/memory/vector_store.py:272`
- Test: `tests/test_vector_store.py`

- [ ] **Step 1: Write the failing ranking-shape tests**

Add tests in [test_vector_store.py](H:\DouYin_llm\tests\test_vector_store.py) that require the new helper structure to exist.

```python
def test_final_rank_key_combines_semantic_and_business_scores(self):
    item = {
        "memory_id": "m1",
        "memory_text": "不太能吃辣",
        "score": 0.8,
        "metadata": {
            "confidence": 0.9,
            "interaction_value_score": 0.95,
            "evidence_score": 0.7,
            "stability_score": 0.85,
            "source_kind": "manual",
            "is_pinned": 1,
            "updated_at": 100,
            "recall_count": 2,
        },
    }

    rank_key = store._final_rank_key(item, query_text="吃辣", decay_halflife_hours=0)

    self.assertIsInstance(rank_key[0], float)
    self.assertEqual(len(rank_key), 2)
```

```python
def test_business_rerank_score_uses_interaction_evidence_and_stability(self):
    score = store._business_rerank_score(item, query_text="吃辣")
    self.assertGreater(score, 0.0)
```

- [ ] **Step 2: Run the vector test to verify it fails**

Run: `python -m unittest tests.test_vector_store`

Expected: FAIL because `_business_rerank_score()` and `_final_rank_key()` do not exist yet.

- [ ] **Step 3: Add the explicit helper methods**

In [vector_store.py](H:\DouYin_llm\backend\memory\vector_store.py), create:

```python
@staticmethod
def _semantic_score(item):
    return float(item.get("score", 0.0))

@staticmethod
def _business_rerank_score(item, query_text):
    ...

@staticmethod
def _final_rank_key(item, query_text, decay_halflife_hours=0):
    ...
```

- [ ] **Step 4: Implement the first-pass rerank formula**

Use the spec formula directly:

```python
business_rerank_score = (
    0.35 * interaction_value_score
    + 0.20 * evidence_score
    + 0.15 * stability_score
    + 0.10 * confidence
    + 0.08 * manual_bonus
    + 0.07 * pin_bonus
    + 0.05 * recall_bonus
)

final_score = (0.55 * semantic_score) + (0.45 * business_rerank_score)
```

Keep `time_decay` as a multiplicative factor on `final_score`.

- [ ] **Step 5: Replace all `_memory_rank_key()` call sites**

Update internal sorting in:

- `similar_memories()`
- any helper paths that currently use `_memory_rank_key()`

to call `_final_rank_key()` instead.

- [ ] **Step 6: Run the vector test to verify it passes**

Run: `python -m unittest tests.test_vector_store`

Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add backend/memory/vector_store.py tests/test_vector_store.py
git commit -m "refactor: split memory ranking into semantic and business rerank"
```

### Task 2: Prove High Interaction Value And High Evidence Memories Rank Ahead Of Weak Context

**Files:**
- Modify: `tests/test_vector_store.py`
- Modify: `backend/memory/vector_store.py:356`

- [ ] **Step 1: Write the failing behavior tests**

Add tests that prove the rerank produces the intended ordering:

```python
def test_similar_memories_prefers_high_interaction_value_memory_over_generic_context(self):
    ...
    self.assertEqual(result[0]["memory_id"], "m-high-value")
```

```python
def test_similar_memories_prefers_high_evidence_memory_when_semantic_scores_are_close(self):
    ...
    self.assertEqual(result[0]["memory_id"], "m-high-evidence")
```

- [ ] **Step 2: Run the vector test to verify it fails**

Run: `python -m unittest tests.test_vector_store`

Expected: FAIL if the current coefficients are too weak or imbalanced.

- [ ] **Step 3: Tune coefficients minimally**

Adjust only the business rerank weights as needed so that:

- clearly higher `interaction_value_score` beats generic background
- clearly higher `evidence_score` beats one-off weak memories

Do not add new persisted fields or new concepts in this task.

- [ ] **Step 4: Run the vector test to verify it passes**

Run: `python -m unittest tests.test_vector_store`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/memory/vector_store.py tests/test_vector_store.py
git commit -m "test: rank high-value and high-evidence memories ahead of weak context"
```

### Task 3: Tune Manual And Pinned Priority Without Breaking Semantic Relevance

**Files:**
- Modify: `backend/memory/vector_store.py:272`
- Test: `tests/test_vector_store.py`

- [ ] **Step 1: Write the failing manual/pinned tests**

Add tests that require:

```python
def test_manual_memory_beats_auto_memory_when_quality_is_otherwise_equal(self):
    ...
```

```python
def test_pinned_memory_beats_unpinned_memory_when_quality_is_otherwise_equal(self):
    ...
```

And one guardrail:

```python
def test_manual_and_pinned_bonus_do_not_beat_far_better_semantic_match(self):
    ...
```

- [ ] **Step 2: Run the vector test to verify it fails**

Run: `python -m unittest tests.test_vector_store`

Expected: FAIL if the current manual/pin bonuses are too weak or too strong.

- [ ] **Step 3: Tune only the manual and pin bonuses**

Adjust:

- `manual_bonus`
- `pin_bonus`

so they help when semantic quality is close, but do not let a weak semantic match jump ahead of a much better one.

- [ ] **Step 4: Run the vector test to verify it passes**

Run: `python -m unittest tests.test_vector_store`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/memory/vector_store.py tests/test_vector_store.py
git commit -m "test: tune manual and pinned bonuses in memory rerank"
```

### Task 4: Preserve Expiry, Strict Mode, And Token Fallback Behavior

**Files:**
- Modify: `backend/memory/vector_store.py:156`
- Test: `tests/test_vector_store.py`

- [ ] **Step 1: Tighten the regression tests**

Add or update tests that assert:

```python
def test_expired_memories_never_enter_final_rerank(self):
    ...
```

```python
def test_strict_mode_behavior_unchanged_after_rerank_refactor(self):
    ...
```

```python
def test_token_fallback_behavior_unchanged_after_rerank_refactor(self):
    ...
```

- [ ] **Step 2: Run the vector test to verify regressions are caught**

Run: `python -m unittest tests.test_vector_store`

Expected: PASS or fail only if the refactor introduced a regression.

- [ ] **Step 3: Fix only proven regressions**

If any regression appears, patch it minimally. Do not redesign strict mode, expiry, or fallback logic here.

- [ ] **Step 4: Run the vector test to verify it passes**

Run: `python -m unittest tests.test_vector_store`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/memory/vector_store.py tests/test_vector_store.py
git commit -m "test: preserve expiry and strict mode in memory rerank"
```

### Task 5: Update README To Match The New Rerank State

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Capture the current doc mismatch**

Before editing, compare the actual rerank implementation with [README.md](H:\DouYin_llm\README.md). Identify wording that still implies quality signals are barely used.

- [ ] **Step 2: Update the README wording**

Adjust the memory shortcomings / next steps section so it accurately says:

- quality signals are already used in rerank
- rerank is still feature-based and not yet fully mature

Use wording like:

```markdown
召回排序已经系统利用多维质量信号，但当前仍以 feature rerank 为主，尚未接入更强的业务反馈或专门 reranker model。
```

- [ ] **Step 3: Re-run the vector rerank test suite after docs edits**

Run: `python -m unittest tests.test_vector_store`

Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add README.md
git commit -m "docs: describe feature-based memory rerank"
```

