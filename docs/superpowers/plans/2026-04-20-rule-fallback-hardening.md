# Rule Fallback Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Improve the quality of rule-based memory fallback results so that when the LLM path fails, the system still produces conservative, minimally reusable viewer memories rather than raw, low-quality sentences.

**Architecture:** Keep the current “fallback only on LLM exception” rule unchanged, but strengthen the fallback path by expanding only a narrow set of high-confidence templates, adding a conservative rule-based canonicalizer, inferring negative polarity for clear constraints, and capping fallback confidence/quality so fallback results remain usable but clearly below equivalent LLM outputs.

**Tech Stack:** Python, unittest

---

### Task 1: Add Tests That Lock Down Fallback Eligibility And Basic Output Shape

**Files:**
- Modify: `tests/test_llm_memory_extractor.py`
- Modify: `backend/services/memory_extractor.py:165`

- [ ] **Step 1: Write the failing tests**

Add tests in [test_llm_memory_extractor.py](H:\DouYin_llm\tests\test_llm_memory_extractor.py) that require:

```python
def test_rule_fallback_only_runs_when_llm_raises(self):
    ...
```

```python
def test_rule_fallback_does_not_run_when_llm_returns_empty(self):
    ...
```

```python
def test_rule_fallback_rejects_question_like_content(self):
    ...
    self.assertEqual(result, [])
```

These tests should verify:

- `extract_high_confidence()` is only used when the LLM extractor raises
- empty-but-successful LLM results do not trigger rule fallback
- question-like content is still rejected even on fallback

- [ ] **Step 2: Run the targeted test to verify it fails if behavior is missing**

Run: `python -m unittest tests.test_llm_memory_extractor`

Expected: PASS or fail only where behavior is still missing. If already PASS, keep the tests as guardrails and proceed.

- [ ] **Step 3: Tighten fallback entry logic only if needed**

If any test fails, minimally adjust [memory_extractor.py](H:\DouYin_llm\backend\services\memory_extractor.py) so:

```python
except Exception:
    ...
    return self._rule_extractor.extract_high_confidence(event)
...
if llm_candidates:
    return llm_candidates
return []
```

Do not widen fallback conditions.

- [ ] **Step 4: Run the test to verify it passes**

Run: `python -m unittest tests.test_llm_memory_extractor`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/test_llm_memory_extractor.py backend/services/memory_extractor.py
git commit -m "test: lock down memory fallback eligibility"
```

### Task 2: Expand High-Confidence Fallback Templates Conservatively

**Files:**
- Modify: `backend/services/memory_extractor.py:16`
- Test: `tests/test_llm_memory_extractor.py`

- [ ] **Step 1: Write the failing template tests**

Add tests that require fallback to accept a few additional clearly stable patterns:

```python
def test_rule_fallback_accepts_clear_negative_food_constraint(self):
    ...
    self.assertEqual(result[0]["memory_text_canonical"], "不太能吃辣")
```

```python
def test_rule_fallback_accepts_clear_negative_preference(self):
    ...
```

```python
def test_rule_fallback_accepts_clear_stable_job_pattern(self):
    ...
```

- [ ] **Step 2: Run the targeted test to verify it fails**

Run: `python -m unittest tests.test_llm_memory_extractor`

Expected: FAIL because the current template set is too narrow.

- [ ] **Step 3: Extend `HIGH_CONFIDENCE_RULE_PATTERNS` minimally**

Update [memory_extractor.py](H:\DouYin_llm\backend\services\memory_extractor.py):

```python
HIGH_CONFIDENCE_RULE_PATTERNS = (
    ...,
    (re.compile(r"^我不太能吃.+$"), "preference"),
    (re.compile(r"^我不能吃.+$"), "preference"),
    (re.compile(r"^我忌口.+$"), "preference"),
    (re.compile(r"^我不喜欢.+$"), "preference"),
    (re.compile(r"^我在.+做.+$"), "context"),
)
```

Keep the scope tight. Do not add broad fuzzy patterns that would open the floodgates.

- [ ] **Step 4: Re-run the template tests to verify they pass**

Run: `python -m unittest tests.test_llm_memory_extractor`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/services/memory_extractor.py tests/test_llm_memory_extractor.py
git commit -m "feat: expand high-confidence memory fallback templates"
```

### Task 3: Add A Conservative Canonicalizer For Rule Fallback

**Files:**
- Modify: `backend/services/memory_extractor.py:104`
- Test: `tests/test_llm_memory_extractor.py`

- [ ] **Step 1: Write the failing canonicalization tests**

Add tests that assert the fallback path no longer stores the raw sentence as canonical for simple cases.

```python
def test_rule_fallback_canonicalizes_food_constraint(self):
    ...
    self.assertEqual(result[0]["memory_text_raw"], "我其实吧不太能吃辣")
    self.assertEqual(result[0]["memory_text_canonical"], "不太能吃辣")
```

```python
def test_rule_fallback_canonicalizes_context_without_tail_explanation(self):
    ...
    self.assertEqual(result[0]["memory_text_canonical"], "租房住在公司附近")
```

- [ ] **Step 2: Run the targeted test to verify it fails**

Run: `python -m unittest tests.test_llm_memory_extractor`

Expected: FAIL because fallback currently mirrors raw text into canonical.

- [ ] **Step 3: Add a conservative fallback canonicalizer**

Implement a helper in [memory_extractor.py](H:\DouYin_llm\backend\services\memory_extractor.py), such as:

```python
def _canonicalize_high_confidence_text(self, content):
    normalized = clean_comment_text(content)
    normalized = re.sub(r"^(我其实|我其实吧|我吧|其实吧|其实)", "", normalized).strip()
    normalized = re.sub(r"(这样通勤方便点|通勤方便点)$", "", normalized).strip("，。！？!?,.~～ ")
    normalized = re.sub(r"^我", "", normalized).strip()
    return normalized or clean_comment_text(content)
```

Keep it conservative:

- remove only obvious fillers
- keep core constraints and subjects
- never attempt broad paraphrasing

- [ ] **Step 4: Use the canonicalizer only in `extract_high_confidence()`**

Update the fallback result construction:

```python
canonical = self._canonicalize_high_confidence_text(content)
...
"memory_text": canonical,
"memory_text_raw": content,
"memory_text_canonical": canonical,
```

- [ ] **Step 5: Re-run the canonicalization tests to verify they pass**

Run: `python -m unittest tests.test_llm_memory_extractor`

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/services/memory_extractor.py tests/test_llm_memory_extractor.py
git commit -m "feat: canonicalize high-confidence fallback memories"
```

### Task 4: Infer Negative Polarity And Lower Fallback Quality Scores

**Files:**
- Modify: `backend/services/memory_extractor.py:165`
- Modify: `backend/services/memory_confidence_service.py:4`
- Test: `tests/test_llm_memory_extractor.py`

- [ ] **Step 1: Write the failing polarity and quality tests**

Add tests that require:

```python
def test_rule_fallback_marks_negative_food_constraint_as_negative(self):
    ...
    self.assertEqual(result[0]["polarity"], "negative")
```

```python
def test_rule_fallback_is_lower_confidence_than_equivalent_llm_result(self):
    ...
    self.assertLess(result[0]["confidence"], 0.86)
```

And, if needed, a focused confidence-service test for `rule_fallback` lowering:

```python
def test_score_new_memory_caps_rule_fallback_quality(self):
    ...
```

- [ ] **Step 2: Run the targeted test to verify it fails**

Run: `python -m unittest tests.test_llm_memory_extractor tests.test_memory_confidence_service`

Expected: FAIL because fallback still defaults to neutral and does not explicitly lower quality.

- [ ] **Step 3: Add a negative polarity helper in the fallback extractor**

In [memory_extractor.py](H:\DouYin_llm\backend\services\memory_extractor.py), add a helper such as:

```python
def _fallback_polarity(self, canonical):
    if any(token in canonical for token in ("不喜欢", "不能吃", "不太能吃", "忌口")):
        return "negative"
    return "neutral"
```

Use it only in the fallback path.

- [ ] **Step 4: Cap fallback quality in `MemoryConfidenceService`**

Update [memory_confidence_service.py](H:\DouYin_llm\backend\services\memory_confidence_service.py) so `rule_fallback` candidates receive conservative caps, for example:

```python
if candidate.get("extraction_source") == "rule_fallback":
    interaction_value_score = min(interaction_value_score, 0.65)
    clarity_score = min(clarity_score, 0.7)
    confidence = min(confidence, 0.75)
```

Keep the caps simple and explicit; do not over-engineer this pass.

- [ ] **Step 5: Re-run the tests to verify they pass**

Run: `python -m unittest tests.test_llm_memory_extractor tests.test_memory_confidence_service`

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/services/memory_extractor.py backend/services/memory_confidence_service.py tests/test_llm_memory_extractor.py tests/test_memory_confidence_service.py
git commit -m "feat: lower and label rule fallback memory quality"
```

### Task 5: Update README To Match The Hardened Fallback State

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Record the doc mismatch before editing**

Compare the current fallback implementation with [README.md](H:\DouYin_llm\README.md), especially the line that says fallback quality is low.

- [ ] **Step 2: Update the README wording**

Rewrite the relevant shortcoming so it reflects the new state accurately:

- fallback is still conservative and lower quality than LLM
- but no longer defaults to raw sentence storage in the simple high-confidence cases

Use wording like:

```markdown
规则兜底质量已经提升，但仍然只覆盖一小批高置信模板，并继续采取保守降权策略。
```

- [ ] **Step 3: Re-run the focused fallback test suite**

Run: `python -m unittest tests.test_llm_memory_extractor tests.test_memory_confidence_service`

Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add README.md
git commit -m "docs: describe hardened memory fallback behavior"
```

