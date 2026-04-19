# Memory Extractor Online Refinement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade viewer memory extraction so the current comment can immediately use newly extracted memory, while only persisting refined canonical memory and weakening rule fallback to true-exception cases.

**Architecture:** Keep the existing prefilter at the composite extractor entry, upgrade the LLM protocol to emit both raw and canonical memory text in one response, and reorder `process_event` so extraction/refinement happens before suggestion generation. Current-comment memories are injected as ephemeral context for the current suggestion, then persisted only after strict gating passes.

**Tech Stack:** Python, FastAPI, unittest, existing Ollama/OpenAI-compatible memory extractor client

---

### File Map

**Modify:**
- `H:\DouYin_llm\backend\services\llm_memory_extractor.py`
  Responsibility: extend extractor protocol to `memory_text_raw` and `memory_text_canonical`, validate refined output, and return candidates with canonical text plus raw debug text.
- `H:\DouYin_llm\backend\services\memory_extractor.py`
  Responsibility: keep prefiltering, downgrade rule fallback so it triggers only on LLM transport/protocol exceptions, and restrict fallback to high-confidence rule templates.
- `H:\DouYin_llm\backend\services\agent.py`
  Responsibility: accept ephemeral memories in context building and prioritize them for the current suggestion without mutating vector recall behavior.
- `H:\DouYin_llm\backend\app.py`
  Responsibility: reorder `process_event` so extraction/refinement happens before suggestion generation, inject ephemeral memory into current context, then persist canonical memory and set new status flags.
- `H:\DouYin_llm\tests\test_llm_memory_extractor.py`
  Responsibility: cover the dual-field protocol, canonical gating, exception-only fallback, and high-confidence rule fallback boundaries.
- `H:\DouYin_llm\tests\test_comment_processing_status.py`
  Responsibility: verify reordered processing, ephemeral memory usage, and the new processing status fields.
- `H:\DouYin_llm\tests\test_verify_memory_pipeline.py`
  Responsibility: verify that the current comment can benefit from freshly extracted memory and that canonical text is the persisted text.

**Reference docs:**
- `H:\DouYin_llm\docs\superpowers\specs\2026-04-19-memory-extractor-online-refinement-design.md`

### Task 1: Upgrade The LLM Protocol To Dual Memory Text Fields

**Files:**
- Modify: `H:\DouYin_llm\backend\services\llm_memory_extractor.py`
- Test: `H:\DouYin_llm\tests\test_llm_memory_extractor.py`

- [ ] **Step 1: Write the failing test for dual-field extraction**

```python
def test_extract_returns_canonical_memory_text_and_keeps_raw_text_for_debug(self):
    from backend.services.llm_memory_extractor import LLMBackedViewerMemoryExtractor

    runtime = FakeRuntime(
        json.dumps(
            {
                "should_extract": True,
                "memory_text_raw": "我其实平时吧都不太能吃辣",
                "memory_text_canonical": "不太能吃辣",
                "memory_type": "preference",
                "polarity": "negative",
                "temporal_scope": "long_term",
                "reason": "稳定饮食限制",
            },
            ensure_ascii=False,
        )
    )

    extractor = LLMBackedViewerMemoryExtractor(settings=SimpleNamespace(), runtime=runtime)

    self.assertEqual(
        extractor.extract(make_event(content="我其实平时吧都不太能吃辣")),
        [
            {
                "memory_text": "不太能吃辣",
                "memory_text_raw": "我其实平时吧都不太能吃辣",
                "memory_type": "preference",
                "confidence": 0.86,
            }
        ],
    )
```

- [ ] **Step 2: Run the single test and verify it fails**

Run:

```powershell
python -m unittest tests.test_llm_memory_extractor.LLMBackedViewerMemoryExtractorTests.test_extract_returns_canonical_memory_text_and_keeps_raw_text_for_debug -v
```

Expected: FAIL because the extractor still expects `memory_text` instead of the dual-field protocol.

- [ ] **Step 3: Add a second failing test for canonical gating**

```python
def test_extract_rejects_payload_when_canonical_text_is_blank(self):
    from backend.services.llm_memory_extractor import LLMBackedViewerMemoryExtractor

    runtime = FakeRuntime(
        json.dumps(
            {
                "should_extract": True,
                "memory_text_raw": "我其实平时吧都不太能吃辣",
                "memory_text_canonical": "   ",
                "memory_type": "preference",
                "polarity": "negative",
                "temporal_scope": "long_term",
                "reason": "稳定饮食限制",
            },
            ensure_ascii=False,
        )
    )

    extractor = LLMBackedViewerMemoryExtractor(settings=SimpleNamespace(), runtime=runtime)

    self.assertEqual(extractor.extract(make_event(content="我其实平时吧都不太能吃辣")), [])
```

- [ ] **Step 4: Run the second single test and verify it fails**

Run:

```powershell
python -m unittest tests.test_llm_memory_extractor.LLMBackedViewerMemoryExtractorTests.test_extract_rejects_payload_when_canonical_text_is_blank -v
```

Expected: FAIL because blank canonical text is not yet validated.

- [ ] **Step 5: Implement the minimal protocol upgrade**

Update `LLMBackedViewerMemoryExtractor` so:

```python
required_string_fields = ("memory_text_raw", "memory_text_canonical", "memory_type", "polarity", "temporal_scope", "reason")
canonical_text = payload.get("memory_text_canonical")
raw_text = payload.get("memory_text_raw")
```

Normalize output to:

```python
return [
    {
        "memory_text": canonical_text.strip(),
        "memory_text_raw": raw_text.strip(),
        "memory_type": memory_type,
        "confidence": confidence,
    }
]
```

- [ ] **Step 6: Update the system prompt and few-shot examples to require both fields**

Adjust the schema text and example JSON in `backend/services/llm_memory_extractor.py` so every positive example includes:

```json
"memory_text_raw":"我其实平时吧都不太能吃辣",
"memory_text_canonical":"不太能吃辣"
```

and every negative example includes both fields as empty strings.

- [ ] **Step 7: Run the focused extractor suite**

Run:

```powershell
python -m unittest tests.test_llm_memory_extractor -v
```

Expected: PASS

- [ ] **Step 8: Commit**

```powershell
git add backend/services/llm_memory_extractor.py tests/test_llm_memory_extractor.py
git commit -m "feat: add dual-field memory extraction protocol"
```

### Task 2: Downgrade Rule Fallback To Exception-Only High-Confidence Rescue

**Files:**
- Modify: `H:\DouYin_llm\backend\services\memory_extractor.py`
- Test: `H:\DouYin_llm\tests\test_llm_memory_extractor.py`

- [ ] **Step 1: Write the failing test for no fallback after explicit LLM rejection**

```python
def test_composite_does_not_fallback_to_rules_when_llm_explicitly_rejects(self):
    from backend.services.memory_extractor import ViewerMemoryExtractor

    llm_extractor = MagicMock()
    llm_extractor.extract.return_value = []
    llm_extractor.extract_payload = MagicMock(return_value={"should_extract": False})
    rule_extractor = MagicMock()
    rule_extractor.extract.return_value = [{"memory_text": "我在杭州上班", "memory_type": "context", "confidence": 0.7}]
    extractor = ViewerMemoryExtractor(settings=None, llm_extractor=llm_extractor, rule_extractor=rule_extractor)

    self.assertEqual(extractor.extract(make_event(content="这周可能都在上海出差")), [])
    rule_extractor.extract.assert_not_called()
```

- [ ] **Step 2: Run the single test and verify it fails**

Run:

```powershell
python -m unittest tests.test_llm_memory_extractor.ViewerMemoryExtractorCompositeTests.test_composite_does_not_fallback_to_rules_when_llm_explicitly_rejects -v
```

Expected: FAIL because the current composite extractor falls back whenever `extract()` returns `[]`.

- [ ] **Step 3: Write the failing test for exception-only fallback with high-confidence rule rescue**

```python
def test_composite_uses_rule_rescue_only_for_high_confidence_template_when_llm_raises(self):
    from backend.services.memory_extractor import ViewerMemoryExtractor

    llm_extractor = MagicMock()
    llm_extractor.extract.side_effect = RuntimeError("timeout")
    rule_extractor = MagicMock()
    rule_extractor.extract.return_value = [{"memory_text": "我在杭州上班", "memory_type": "context", "confidence": 0.8}]
    extractor = ViewerMemoryExtractor(settings=None, llm_extractor=llm_extractor, rule_extractor=rule_extractor)

    self.assertEqual(
        extractor.extract(make_event(content="我在杭州上班")),
        [{"memory_text": "我在杭州上班", "memory_type": "context", "confidence": 0.8}],
    )
```

- [ ] **Step 4: Write the failing negative test for low-confidence rule rescue**

```python
def test_composite_blocks_low_confidence_rule_rescue_when_llm_raises(self):
    from backend.services.memory_extractor import ViewerMemoryExtractor

    llm_extractor = MagicMock()
    llm_extractor.extract.side_effect = RuntimeError("timeout")
    rule_extractor = MagicMock()
    rule_extractor.extract.return_value = [{"memory_text": "哈哈哈哈", "memory_type": "fact", "confidence": 0.46}]
    extractor = ViewerMemoryExtractor(settings=None, llm_extractor=llm_extractor, rule_extractor=rule_extractor)

    self.assertEqual(extractor.extract(make_event(content="哈哈哈哈")), [])
```

- [ ] **Step 5: Run the composite suite and verify failures are correct**

Run:

```powershell
python -m unittest tests.test_llm_memory_extractor.ViewerMemoryExtractorCompositeTests -v
```

Expected: FAIL only in the new fallback tests.

- [ ] **Step 6: Implement the minimal fallback policy**

Change `ViewerMemoryExtractor.extract()` so:

```python
try:
    llm_candidates = self._llm_extractor.extract(event)
except Exception:
    rule_candidates = self._rule_extractor.extract(event)
    return self._filter_high_confidence_rule_candidates(event, rule_candidates)

if llm_candidates:
    return llm_candidates

return []
```

and add a focused helper like:

```python
def _filter_high_confidence_rule_candidates(self, event, candidates):
    ...
```

that allows only stable, non-question, high-confidence rule candidates.

- [ ] **Step 7: Run the extractor suite**

Run:

```powershell
python -m unittest tests.test_llm_memory_extractor -v
```

Expected: PASS

- [ ] **Step 8: Commit**

```powershell
git add backend/services/memory_extractor.py tests/test_llm_memory_extractor.py
git commit -m "feat: downgrade rule fallback for memory extraction"
```

### Task 3: Reorder Event Processing And Inject Ephemeral Memory Into The Current Suggestion

**Files:**
- Modify: `H:\DouYin_llm\backend\app.py`
- Modify: `H:\DouYin_llm\backend\services\agent.py`
- Test: `H:\DouYin_llm\tests\test_comment_processing_status.py`

- [ ] **Step 1: Write the failing processing test for current-comment memory usage**

```python
def test_process_event_uses_new_memory_for_current_suggestion_before_persisting(self):
    event = make_event()

    original_session_memory = app_module.session_memory
    original_long_term_store = app_module.long_term_store
    original_agent = app_module.agent
    original_memory_extractor = app_module.memory_extractor
    original_vector_memory = app_module.vector_memory
    original_broker = app_module.broker
    try:
        app_module.session_memory = MagicMock()
        app_module.session_memory.recent_events.return_value = [event]
        app_module.session_memory.stats.return_value = SimpleNamespace(model_dump=lambda: {"room_id": "room-1", "total_events": 1})
        app_module.long_term_store = MagicMock()
        app_module.vector_memory = MagicMock()
        app_module.memory_extractor = MagicMock()
        app_module.memory_extractor.extract.return_value = [
            {
                "memory_text": "不太能吃辣",
                "memory_text_raw": "我其实平时吧都不太能吃辣",
                "memory_type": "preference",
                "confidence": 0.86,
            }
        ]
        app_module.agent = MagicMock()
        app_module.agent.maybe_generate.return_value = SimpleNamespace(suggestion_id="sug-1", model_dump=lambda: {"suggestion_id": "sug-1"})
        app_module.agent.consume_last_generation_metadata.return_value = {}
        app_module.agent.current_status.return_value = {"mode": "qwen", "model": "qwen", "backend": "", "last_result": "ok", "last_error": "", "updated_at": 1}
        app_module.broker = MagicMock()
        app_module.broker.publish = AsyncMock()

        asyncio.run(app_module.process_event(event))

        kwargs = app_module.agent.maybe_generate.call_args.kwargs
        self.assertEqual(kwargs["ephemeral_memories"][0]["memory_text"], "不太能吃辣")
    finally:
        app_module.session_memory = original_session_memory
        app_module.long_term_store = original_long_term_store
        app_module.agent = original_agent
        app_module.memory_extractor = original_memory_extractor
        app_module.vector_memory = original_vector_memory
        app_module.broker = original_broker
```

- [ ] **Step 2: Run the single test and verify it fails**

Run:

```powershell
python -m unittest tests.test_comment_processing_status.CommentProcessingStatusTests.test_process_event_uses_new_memory_for_current_suggestion_before_persisting -v
```

Expected: FAIL because `maybe_generate()` does not yet accept injected ephemeral memories.

- [ ] **Step 3: Implement the minimal `agent.py` change**

Extend the signatures:

```python
def build_context(self, event, recent_events, ephemeral_memories=None):
    ...

def maybe_generate(self, event, recent_events, ephemeral_memories=None):
    ...
```

Merge the new memories ahead of recalled memories:

```python
ephemeral_memory_texts = [item["memory_text"] for item in (ephemeral_memories or [])]
viewer_memory_texts = self._dedupe_preserve_order(ephemeral_memory_texts + recalled_memory_texts)
```

- [ ] **Step 4: Implement the minimal `app.py` reorder**

Reshape `process_event()` to:

```python
ephemeral_memories = extract_current_comment_memories(event)
suggestion = agent.maybe_generate(event, recent_events, ephemeral_memories=ephemeral_memories)
persist_ephemeral_memories(...)
```

Preserve the existing event publication behavior and error handling.

- [ ] **Step 5: Add status flags to the streamed processing payload**

Populate:

```python
processing_status.memory_llm_attempted = ...
processing_status.memory_refined = ...
processing_status.memory_used_for_current_suggestion = ...
processing_status.memory_persisted = ...
```

- [ ] **Step 6: Run the comment-processing suite**

Run:

```powershell
python -m unittest tests.test_comment_processing_status -v
```

Expected: PASS

- [ ] **Step 7: Commit**

```powershell
git add backend/app.py backend/services/agent.py tests/test_comment_processing_status.py
git commit -m "feat: use current-comment memory in suggestions"
```

### Task 4: Verify Canonical Persistence And Current-Comment Online Behavior

**Files:**
- Modify: `H:\DouYin_llm\tests\test_verify_memory_pipeline.py`
- Test: `H:\DouYin_llm\tests\test_verify_memory_pipeline.py`

- [ ] **Step 1: Write the failing test for canonical persistence**

```python
def test_memory_pipeline_persists_canonical_memory_text_not_raw_text(self):
    candidate = {
        "memory_text": "不太能吃辣",
        "memory_text_raw": "我其实平时吧都不太能吃辣",
        "memory_type": "preference",
        "confidence": 0.86,
    }
    store = MagicMock()
    vector = MagicMock()

    persisted = persist_memory_candidate(store, vector, event=make_event(), candidate=candidate)

    store.save_viewer_memory.assert_called_once()
    self.assertEqual(store.save_viewer_memory.call_args.kwargs["memory_text"], "不太能吃辣")
```

- [ ] **Step 2: Run the single verifier test and verify it fails**

Run:

```powershell
python -m unittest tests.test_verify_memory_pipeline.VerifyMemoryPipelineTests.test_memory_pipeline_persists_canonical_memory_text_not_raw_text -v
```

Expected: FAIL because there is no dedicated helper or assertion yet for canonical-only persistence.

- [ ] **Step 3: Add the minimal helper or direct persistence assertion**

If extracting a helper improves readability, add a small local helper in `backend/app.py` or keep the assertion at the current persistence call site. Persist only:

```python
memory_text=candidate["memory_text"]
```

Never `memory_text_raw`.

- [ ] **Step 4: Run the focused verifier suite**

Run:

```powershell
python -m unittest tests.test_verify_memory_pipeline tests.test_memory_extractor_client -v
```

Expected: PASS

- [ ] **Step 5: Run the full targeted regression pack**

Run:

```powershell
python -m unittest tests.test_llm_memory_extractor tests.test_comment_processing_status tests.test_verify_memory_pipeline tests.test_memory_extractor_client -v
```

Expected: PASS

- [ ] **Step 6: Review the worktree**

Run:

```powershell
git status --short
```

Expected: only the intended source, test, and doc files are modified.

- [ ] **Step 7: Commit**

```powershell
git add backend/app.py backend/services/agent.py backend/services/llm_memory_extractor.py backend/services/memory_extractor.py tests/test_llm_memory_extractor.py tests/test_comment_processing_status.py tests/test_verify_memory_pipeline.py docs/superpowers/plans/2026-04-19-memory-extractor-online-refinement.md
git commit -m "feat: refine online memory extraction for current suggestions"
```
