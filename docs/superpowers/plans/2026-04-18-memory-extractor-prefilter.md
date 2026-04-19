# Memory Extractor Prefilter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a conservative prefilter that short-circuits obvious non-memory comments before the LLM memory extractor runs.

**Architecture:** Keep the new behavior in the composite viewer-memory extractor so there is a single entry point for skip decisions. Prefiltered comments return no candidates; all other comments keep the existing `LLM -> fallback to rules` behavior.

**Tech Stack:** Python, unittest, existing backend memory extraction services

---

### Task 1: Add Red Tests For Prefiltered Comments

**Files:**
- Modify: `H:\DouYin_llm\tests\test_llm_memory_extractor.py`
- Test: `H:\DouYin_llm\tests\test_llm_memory_extractor.py`

- [ ] **Step 1: Write the failing test**

```python
def test_composite_short_circuits_obvious_noise_without_calling_extractors(self):
    from backend.services.memory_extractor import ViewerMemoryExtractor

    llm_extractor = MagicMock()
    rule_extractor = MagicMock()
    extractor = ViewerMemoryExtractor(settings=None, llm_extractor=llm_extractor, rule_extractor=rule_extractor)

    for content in ("来了", "哈哈哈哈", "支持主播", "多少钱", "链接在哪"):
        with self.subTest(content=content):
            self.assertEqual(extractor.extract(make_event(content=content)), [])

    llm_extractor.extract.assert_not_called()
    rule_extractor.extract.assert_not_called()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_llm_memory_extractor.ViewerMemoryExtractorCompositeTests.test_composite_short_circuits_obvious_noise_without_calling_extractors -v`
Expected: FAIL because the composite extractor still calls the fallback path.

- [ ] **Step 3: Write minimal implementation**

```python
def _should_skip_comment(self, event):
    ...
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m unittest tests.test_llm_memory_extractor.ViewerMemoryExtractorCompositeTests.test_composite_short_circuits_obvious_noise_without_calling_extractors -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/test_llm_memory_extractor.py backend/services/memory_extractor.py
git commit -m "feat: prefilter obvious non-memory comments"
```

### Task 2: Protect Pass-Through Behavior

**Files:**
- Modify: `H:\DouYin_llm\tests\test_llm_memory_extractor.py`
- Modify: `H:\DouYin_llm\backend\services\memory_extractor.py`
- Test: `H:\DouYin_llm\tests\test_llm_memory_extractor.py`

- [ ] **Step 1: Write the failing test**

```python
def test_composite_allows_memory_like_comment_to_reach_llm(self):
    from backend.services.memory_extractor import ViewerMemoryExtractor

    llm_extractor = MagicMock()
    llm_extractor.extract.return_value = []
    rule_extractor = MagicMock()
    rule_extractor.extract.return_value = []
    extractor = ViewerMemoryExtractor(settings=None, llm_extractor=llm_extractor, rule_extractor=rule_extractor)

    extractor.extract(make_event(content="我在杭州上班"))

    llm_extractor.extract.assert_called_once()
```

- [ ] **Step 2: Run test to verify it fails if the prefilter is too broad**

Run: `python -m unittest tests.test_llm_memory_extractor.ViewerMemoryExtractorCompositeTests.test_composite_allows_memory_like_comment_to_reach_llm -v`
Expected: PASS only if the prefilter remains conservative; otherwise FAIL showing an accidental skip.

- [ ] **Step 3: Keep implementation minimal**

```python
if self._should_skip_comment(event):
    return []
```

- [ ] **Step 4: Run focused suite**

Run: `python -m unittest tests.test_llm_memory_extractor -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/test_llm_memory_extractor.py backend/services/memory_extractor.py
git commit -m "test: cover memory extractor prefilter boundaries"
```

### Task 3: Verify No Regression In Comment Processing Status

**Files:**
- Test: `H:\DouYin_llm\tests\test_comment_processing_status.py`

- [ ] **Step 1: Run targeted integration-adjacent verification**

Run: `python -m unittest tests.test_comment_processing_status tests.test_llm_memory_extractor -v`
Expected: PASS

- [ ] **Step 2: Run broader backend checks**

Run: `python -m unittest tests.test_verify_memory_pipeline tests.test_memory_extractor_client -v`
Expected: PASS

- [ ] **Step 3: Review worktree before handoff**

Run: `git status --short`
Expected: only the intended source, test, and docs changes are present.

- [ ] **Step 4: Commit**

```bash
git add docs/superpowers/specs/2026-04-18-memory-extractor-prefilter-design.md docs/superpowers/plans/2026-04-18-memory-extractor-prefilter.md
git commit -m "docs: capture memory extractor prefilter design"
```
