# Suggestion Block Reason Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expose a structured “why no suggestion was generated” status from the backend all the way to the frontend comment timeline.

**Architecture:** Extend `LivePromptAgent` so every generation attempt records a structured suggestion outcome alongside the existing memory-recall metadata. Persist that outcome into `CommentProcessingStatus` inside `process_event()`, then let the frontend presenter map status and reason codes into a short timeline conclusion plus a richer expanded explanation.

**Tech Stack:** FastAPI + Pydantic backend, Python `unittest` / `pytest`, Vue 3 single-file components, existing Node `assert` frontend tests, Vite build.

---

## File Structure

- Modify: `H:\DouYin_llm\backend\services\agent.py`
  Add structured suggestion outcome metadata and map skip/failure cases to stable reason codes.

- Modify: `H:\DouYin_llm\tests\test_agent.py`
  Lock down skip/failure metadata at the agent boundary before touching application wiring.

- Modify: `H:\DouYin_llm\backend\schemas\live.py`
  Extend `CommentProcessingStatus` with `suggestion_status`, `suggestion_block_reason`, and `suggestion_block_detail`.

- Modify: `H:\DouYin_llm\backend\app.py`
  Copy agent metadata into the published `processing_status` object for each event.

- Modify: `H:\DouYin_llm\tests\test_comment_processing_status.py`
  Verify streamed comment payloads include the new suggestion-stage fields for both generated and skipped cases.

- Modify: `H:\DouYin_llm\frontend\src\components\event-feed-processing-presenter.js`
  Translate backend status into timeline/detail presentation objects without pushing inference into Vue templates.

- Modify: `H:\DouYin_llm\frontend\src\components\event-feed-processing-presenter.test.mjs`
  Freeze the presenter contract for generated / skipped / failed outcomes and unknown reason-code fallback.

- Modify: `H:\DouYin_llm\frontend\src\components\EventFeed.vue`
  Render a short reason in the collapsed timeline and a richer reason/detail block in the expanded view.

- Modify: `H:\DouYin_llm\frontend\src\components\status-strip-layout.test.mjs`
  Guard the new event-feed timeline/detail template structure with the existing source-based layout test.

- Modify: `H:\DouYin_llm\frontend\src\i18n.js`
  Add Chinese and English copy for suggestion status labels, reason labels, and the unknown fallback.

### Task 1: Add structured suggestion outcome metadata inside the agent

**Files:**
- Modify: `H:\DouYin_llm\tests\test_agent.py`
- Modify: `H:\DouYin_llm\backend\services\agent.py`

- [ ] **Step 1: Add failing agent tests for skip and failure metadata**

Append the following tests to `H:\DouYin_llm\tests\test_agent.py` inside `LivePromptAgentTests`:

```python
    def test_maybe_generate_records_skip_metadata_for_blank_comment(self):
        agent = LivePromptAgent(make_settings(), MagicMock(), MagicMock())

        suggestion = agent.maybe_generate(make_event(content="   "), [])
        metadata = agent.consume_last_generation_metadata()

        self.assertIsNone(suggestion)
        self.assertEqual(metadata["suggestion_status"], "skipped")
        self.assertEqual(metadata["suggestion_block_reason"], "no_generation_needed")
        self.assertEqual(metadata["suggestion_block_detail"], "评论内容为空，未生成建议。")
        self.assertFalse(metadata["memory_recall_attempted"])
        self.assertEqual(metadata["recalled_memory_ids"], [])

    def test_maybe_generate_records_failure_metadata_for_semantic_backend_error(self):
        vector_memory = MagicMock()
        vector_memory.similar_memories.side_effect = RuntimeError(
            "Vector recall strict mode blocked fallback: Chroma is unavailable"
        )

        agent = LivePromptAgent(make_settings(), vector_memory, MagicMock())
        suggestion = agent.maybe_generate(make_event(content="还记得我上次说的拉面吗"), [])
        metadata = agent.consume_last_generation_metadata()

        self.assertIsNone(suggestion)
        self.assertEqual(metadata["suggestion_status"], "failed")
        self.assertEqual(metadata["suggestion_block_reason"], "semantic_backend_unavailable")
        self.assertEqual(metadata["suggestion_block_detail"], "语义召回后端不可用，未生成建议。")
        self.assertTrue(metadata["memory_recall_attempted"])
        self.assertFalse(metadata["memory_recalled"])
```

- [ ] **Step 2: Run the agent test file and verify it fails**

Run: `python -m pytest H:\DouYin_llm\tests\test_agent.py -q`

Expected: FAIL because the consumed metadata does not yet include `suggestion_status`, `suggestion_block_reason`, or `suggestion_block_detail`.

- [ ] **Step 3: Implement agent-side suggestion outcome recording**

Update `H:\DouYin_llm\backend\services\agent.py` with a small helper and explicit skip/failure branches:

```python
    def _generation_metadata(
        self,
        *,
        memory_recall_attempted=False,
        memory_recalled=False,
        recalled_memory_ids=None,
        suggestion_status="",
        suggestion_block_reason="",
        suggestion_block_detail="",
    ):
        return {
            "memory_recall_attempted": bool(memory_recall_attempted),
            "memory_recalled": bool(memory_recalled),
            "recalled_memory_ids": list(recalled_memory_ids or []),
            "suggestion_status": suggestion_status,
            "suggestion_block_reason": suggestion_block_reason,
            "suggestion_block_detail": suggestion_block_detail,
        }
```

At the top of `maybe_generate()` handle the two explicit skip cases:

```python
        if event.event_type not in {"comment", "gift", "follow"}:
            self._last_generation_metadata = self._generation_metadata(
                suggestion_status="skipped",
                suggestion_block_reason="rule_skipped",
                suggestion_block_detail="当前事件类型不参与建议生成。",
            )
            return None

        if event.event_type == "comment" and not str(event.content or "").strip():
            self._last_generation_metadata = self._generation_metadata(
                suggestion_status="skipped",
                suggestion_block_reason="no_generation_needed",
                suggestion_block_detail="评论内容为空，未生成建议。",
            )
            return None
```

Wrap the context-building / payload-generation section so semantic-backend failures become structured agent metadata instead of leaking as implicit “no suggestion”:

```python
        try:
            if self._should_short_circuit_with_heuristic(event):
                payload = self._generate_heuristic(event, context, source="heuristic")
            else:
                context = self.build_context(event, recent_events)
                generation_metadata = self._generation_metadata(
                    memory_recall_attempted=True,
                    memory_recalled=bool(context["recalled_memory_ids"]),
                    recalled_memory_ids=context["recalled_memory_ids"],
                )
                payload = self._generate_payload(event, context)
        except RuntimeError as exc:
            detail = "模型处理失败，未生成建议。"
            reason = "llm_failed"
            if "Vector recall strict mode blocked fallback" in str(exc):
                reason = "semantic_backend_unavailable"
                detail = "语义召回后端不可用，未生成建议。"
            self._mark_status("error", reason)
            self._last_generation_metadata = self._generation_metadata(
                memory_recall_attempted=True,
                memory_recalled=False,
                recalled_memory_ids=[],
                suggestion_status="failed",
                suggestion_block_reason=reason,
                suggestion_block_detail=detail,
            )
            return None
```

When generation succeeds, make the success metadata explicit before returning the `Suggestion`:

```python
        self._last_generation_metadata = self._generation_metadata(
            memory_recall_attempted=generation_metadata["memory_recall_attempted"],
            memory_recalled=generation_metadata["memory_recalled"],
            recalled_memory_ids=generation_metadata["recalled_memory_ids"],
            suggestion_status="generated",
            suggestion_block_reason="",
            suggestion_block_detail="",
        )
```

- [ ] **Step 4: Re-run the agent tests**

Run: `python -m pytest H:\DouYin_llm\tests\test_agent.py -q`

Expected: PASS.

- [ ] **Step 5: Commit the agent metadata slice**

```bash
git -C H:\DouYin_llm add backend/services/agent.py tests/test_agent.py
git -C H:\DouYin_llm commit -m "feat: add suggestion outcome metadata"
```

### Task 2: Persist suggestion outcome fields into comment processing status

**Files:**
- Modify: `H:\DouYin_llm\backend\schemas\live.py`
- Modify: `H:\DouYin_llm\backend\app.py`
- Modify: `H:\DouYin_llm\tests\test_comment_processing_status.py`

- [ ] **Step 1: Extend the comment-processing test to assert the new fields**

Replace the first test body in `H:\DouYin_llm\tests\test_comment_processing_status.py` with the stronger assertions below, then add a second skipped-case test:

```python
    def test_process_event_attaches_processing_status_to_streamed_comment(self):
        event = make_event()
        suggestion = SimpleNamespace(
            suggestion_id="sug-1",
            model_dump=lambda: {"suggestion_id": "sug-1", "room_id": "room-1"},
        )
        memory = SimpleNamespace(memory_id="mem-1")

        original_session_memory = app_module.session_memory
        original_long_term_store = app_module.long_term_store
        original_agent = app_module.agent
        original_memory_extractor = app_module.memory_extractor
        original_vector_memory = app_module.vector_memory
        original_broker = app_module.broker
        try:
            app_module.session_memory = MagicMock()
            app_module.session_memory.recent_events.return_value = [event]
            app_module.session_memory.stats.return_value = SimpleNamespace(
                model_dump=lambda: {"room_id": "room-1", "total_events": 1}
            )

            app_module.long_term_store = MagicMock()
            app_module.long_term_store.save_viewer_memory.return_value = memory

            app_module.agent = MagicMock()
            app_module.agent.maybe_generate.return_value = suggestion
            app_module.agent.consume_last_generation_metadata.return_value = {
                "memory_recall_attempted": True,
                "memory_recalled": True,
                "recalled_memory_ids": ["mem-9"],
                "suggestion_status": "generated",
                "suggestion_block_reason": "",
                "suggestion_block_detail": "",
            }
            app_module.agent.current_status.return_value = {
                "mode": "qwen",
                "model": "qwen3.5-flash",
                "backend": "https://example.test/v1",
                "last_result": "ok",
                "last_error": "",
                "updated_at": 1,
            }

            app_module.memory_extractor = MagicMock()
            app_module.memory_extractor.extract.return_value = [
                {
                    "memory_text": "likes ramen",
                    "memory_type": "preference",
                    "confidence": 0.91,
                }
            ]

            app_module.vector_memory = MagicMock()
            app_module.broker = MagicMock()
            app_module.broker.publish = AsyncMock()

            asyncio.run(app_module.process_event(event))

            published_event = app_module.broker.publish.await_args_list[0].args[0]
            status = published_event["data"]["processing_status"]

            self.assertEqual(status["suggestion_status"], "generated")
            self.assertEqual(status["suggestion_block_reason"], "")
            self.assertEqual(status["suggestion_block_detail"], "")
            self.assertTrue(status["suggestion_generated"])
            self.assertEqual(status["suggestion_id"], "sug-1")
        finally:
            app_module.session_memory = original_session_memory
            app_module.long_term_store = original_long_term_store
            app_module.agent = original_agent
            app_module.memory_extractor = original_memory_extractor
            app_module.vector_memory = original_vector_memory
            app_module.broker = original_broker

    def test_process_event_publishes_skip_reason_when_agent_returns_no_suggestion(self):
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
            app_module.session_memory.stats.return_value = SimpleNamespace(
                model_dump=lambda: {"room_id": "room-1", "total_events": 1}
            )

            app_module.long_term_store = MagicMock()
            app_module.agent = MagicMock()
            app_module.agent.maybe_generate.return_value = None
            app_module.agent.consume_last_generation_metadata.return_value = {
                "memory_recall_attempted": False,
                "memory_recalled": False,
                "recalled_memory_ids": [],
                "suggestion_status": "skipped",
                "suggestion_block_reason": "no_generation_needed",
                "suggestion_block_detail": "评论内容为空，未生成建议。",
            }
            app_module.agent.current_status.return_value = {
                "mode": "heuristic",
                "model": "heuristic",
                "backend": "local",
                "last_result": "idle",
                "last_error": "",
                "updated_at": 1,
            }

            app_module.memory_extractor = MagicMock()
            app_module.memory_extractor.extract.return_value = []
            app_module.vector_memory = MagicMock()
            app_module.broker = MagicMock()
            app_module.broker.publish = AsyncMock()

            asyncio.run(app_module.process_event(event))

            published_event = app_module.broker.publish.await_args_list[0].args[0]
            status = published_event["data"]["processing_status"]

            self.assertFalse(status["suggestion_generated"])
            self.assertEqual(status["suggestion_status"], "skipped")
            self.assertEqual(status["suggestion_block_reason"], "no_generation_needed")
            self.assertEqual(status["suggestion_block_detail"], "评论内容为空，未生成建议。")
            self.assertEqual(status["suggestion_id"], "")
        finally:
            app_module.session_memory = original_session_memory
            app_module.long_term_store = original_long_term_store
            app_module.agent = original_agent
            app_module.memory_extractor = original_memory_extractor
            app_module.vector_memory = original_vector_memory
            app_module.broker = original_broker
```

- [ ] **Step 2: Run the processing-status tests and verify they fail**

Run: `python -m pytest H:\DouYin_llm\tests\test_comment_processing_status.py -q`

Expected: FAIL because `CommentProcessingStatus` and `process_event()` do not yet publish the new suggestion-stage fields.

- [ ] **Step 3: Extend the schema and process-event mapping**

In `H:\DouYin_llm\backend\schemas\live.py`, extend `CommentProcessingStatus`:

```python
class CommentProcessingStatus(BaseModel):
    """Per-comment runtime processing status shown in the frontend."""

    received: bool = False
    persisted: bool = False
    memory_extraction_attempted: bool = False
    memory_saved: bool = False
    saved_memory_ids: list[str] = Field(default_factory=list)
    memory_recall_attempted: bool = False
    memory_recalled: bool = False
    recalled_memory_ids: list[str] = Field(default_factory=list)
    suggestion_generated: bool = False
    suggestion_status: str = ""
    suggestion_block_reason: str = ""
    suggestion_block_detail: str = ""
    suggestion_id: str = ""
```

In `H:\DouYin_llm\backend\app.py`, copy the agent metadata into `processing_status` immediately after `consume_last_generation_metadata()`:

```python
    processing_status.memory_recall_attempted = bool(generation_metadata.get("memory_recall_attempted"))
    processing_status.recalled_memory_ids = list(generation_metadata.get("recalled_memory_ids", []))
    processing_status.memory_recalled = bool(
        generation_metadata.get("memory_recalled") or processing_status.recalled_memory_ids
    )
    processing_status.suggestion_status = str(generation_metadata.get("suggestion_status") or "")
    processing_status.suggestion_block_reason = str(generation_metadata.get("suggestion_block_reason") or "")
    processing_status.suggestion_block_detail = str(generation_metadata.get("suggestion_block_detail") or "")

    if suggestion:
        session_memory.add_suggestion(suggestion)
        long_term_store.persist_suggestion(suggestion)
        processing_status.suggestion_generated = True
        processing_status.suggestion_status = processing_status.suggestion_status or "generated"
        processing_status.suggestion_id = suggestion.suggestion_id
    else:
        processing_status.suggestion_generated = False
        processing_status.suggestion_id = ""
```

- [ ] **Step 4: Re-run the processing-status tests**

Run: `python -m pytest H:\DouYin_llm\tests\test_comment_processing_status.py -q`

Expected: PASS.

- [ ] **Step 5: Commit the processing-status slice**

```bash
git -C H:\DouYin_llm add backend/schemas/live.py backend/app.py tests/test_comment_processing_status.py
git -C H:\DouYin_llm commit -m "feat: expose suggestion block status in processing state"
```

### Task 3: Render suggestion outcome and reason in the comment timeline

**Files:**
- Modify: `H:\DouYin_llm\frontend\src\components\event-feed-processing-presenter.test.mjs`
- Modify: `H:\DouYin_llm\frontend\src\components\event-feed-processing-presenter.js`
- Modify: `H:\DouYin_llm\frontend\src\components\EventFeed.vue`
- Modify: `H:\DouYin_llm\frontend\src\components\status-strip-layout.test.mjs`
- Modify: `H:\DouYin_llm\frontend\src\i18n.js`

- [ ] **Step 1: Replace the presenter test with generated / skipped / failed coverage**

Replace `H:\DouYin_llm\frontend\src\components\event-feed-processing-presenter.test.mjs` with:

```js
import assert from "node:assert/strict";

import {
  getCommentProcessingDetails,
  getCommentProcessingTimeline,
} from "./event-feed-processing-presenter.js";

const generatedEvent = {
  event_type: "comment",
  processing_status: {
    received: true,
    persisted: true,
    memory_extraction_attempted: true,
    memory_saved: true,
    saved_memory_ids: ["mem-1"],
    memory_recall_attempted: true,
    memory_recalled: true,
    recalled_memory_ids: ["mem-9"],
    suggestion_generated: true,
    suggestion_status: "generated",
    suggestion_block_reason: "",
    suggestion_block_detail: "",
    suggestion_id: "sug-1",
  },
};

const skippedEvent = {
  event_type: "comment",
  processing_status: {
    received: true,
    persisted: true,
    memory_extraction_attempted: true,
    memory_saved: false,
    saved_memory_ids: [],
    memory_recall_attempted: false,
    memory_recalled: false,
    recalled_memory_ids: [],
    suggestion_generated: false,
    suggestion_status: "skipped",
    suggestion_block_reason: "no_generation_needed",
    suggestion_block_detail: "评论内容为空，未生成建议。",
    suggestion_id: "",
  },
};

const failedEvent = {
  event_type: "comment",
  processing_status: {
    received: true,
    persisted: true,
    memory_extraction_attempted: true,
    memory_saved: false,
    saved_memory_ids: [],
    memory_recall_attempted: true,
    memory_recalled: false,
    recalled_memory_ids: [],
    suggestion_generated: false,
    suggestion_status: "failed",
    suggestion_block_reason: "semantic_backend_unavailable",
    suggestion_block_detail: "语义召回后端不可用，未生成建议。",
    suggestion_id: "",
  },
};

assert.equal(
  getCommentProcessingTimeline(generatedEvent)[4].labelKey,
  "feed.processing.timeline.suggestionGenerated.success",
);
assert.equal(getCommentProcessingTimeline(generatedEvent)[4].reasonKey, "");

assert.equal(
  getCommentProcessingTimeline(skippedEvent)[4].labelKey,
  "feed.processing.timeline.suggestionGenerated.skipped",
);
assert.equal(
  getCommentProcessingTimeline(skippedEvent)[4].reasonKey,
  "feed.processing.reason.no_generation_needed.short",
);

assert.equal(
  getCommentProcessingTimeline(failedEvent)[4].labelKey,
  "feed.processing.timeline.suggestionGenerated.failed",
);
assert.equal(
  getCommentProcessingTimeline(failedEvent)[4].reasonKey,
  "feed.processing.reason.semantic_backend_unavailable.short",
);

const skippedDetail = getCommentProcessingDetails(skippedEvent)[4];
assert.equal(skippedDetail.summaryKey, "feed.processing.detail.suggestionGenerated.skipped");
assert.deepEqual(skippedDetail.meta, [
  { key: "feed.processing.suggestionReason", valueKey: "feed.processing.reason.no_generation_needed.label" },
  { key: "feed.processing.suggestionDetail", value: "评论内容为空，未生成建议。" },
]);

const failedDetail = getCommentProcessingDetails(failedEvent)[4];
assert.equal(failedDetail.summaryKey, "feed.processing.detail.suggestionGenerated.failed");
assert.deepEqual(failedDetail.meta, [
  {
    key: "feed.processing.suggestionReason",
    valueKey: "feed.processing.reason.semantic_backend_unavailable.label",
  },
  { key: "feed.processing.suggestionDetail", value: "语义召回后端不可用，未生成建议。" },
]);

const unknownReasonEvent = {
  event_type: "comment",
  processing_status: {
    ...failedEvent.processing_status,
    suggestion_block_reason: "totally_new_reason",
  },
};

assert.equal(
  getCommentProcessingTimeline(unknownReasonEvent)[4].reasonKey,
  "feed.processing.reason.unknown.short",
);
assert.equal(
  getCommentProcessingDetails(unknownReasonEvent)[4].meta[0].valueKey,
  "feed.processing.reason.unknown.label",
);
```

- [ ] **Step 2: Run the presenter test and verify it fails**

Run: `node H:\DouYin_llm\frontend\src\components\event-feed-processing-presenter.test.mjs`

Expected: FAIL because the presenter does not yet expose `reasonKey`, `valueKey`, or the new suggestion states.

- [ ] **Step 3: Implement presenter mapping, Vue rendering, and i18n copy**

In `H:\DouYin_llm\frontend\src\components\event-feed-processing-presenter.js`, add dedicated helpers for suggestion state and reason-key fallback:

```js
function suggestionState(status) {
  const explicit = `${status?.suggestion_status || ""}`;
  if (explicit === "generated" || explicit === "skipped" || explicit === "failed") {
    return explicit;
  }
  return status?.suggestion_generated ? "success" : "neutral";
}

function normalizeSuggestionState(status) {
  const state = suggestionState(status);
  if (state === "generated") {
    return "success";
  }
  if (state === "skipped") {
    return "skipped";
  }
  if (state === "failed") {
    return "failed";
  }
  return "neutral";
}

function suggestionReasonKey(status, variant = "short") {
  const reason = `${status?.suggestion_block_reason || ""}`.trim();
  const supported = new Set([
    "semantic_backend_unavailable",
    "llm_failed",
    "rule_skipped",
    "no_generation_needed",
  ]);
  const resolved = supported.has(reason) ? reason : "unknown";
  return reason ? `feed.processing.reason.${resolved}.${variant}` : "";
}
```

Then replace the suggestion-stage objects in both exported functions:

```js
  const suggestionPresentationState = normalizeSuggestionState(status);
```

```js
    {
      key: "suggestionGenerated",
      state: suggestionPresentationState,
      labelKey: `feed.processing.timeline.suggestionGenerated.${suggestionPresentationState}`,
      reasonKey:
        suggestionPresentationState === "success"
          ? ""
          : suggestionReasonKey(status, "short"),
    },
```

```js
    {
      key: "suggestionGenerated",
      state: suggestionPresentationState,
      titleKey: "feed.processing.detail.suggestionGenerated.title",
      summaryKey: `feed.processing.detail.suggestionGenerated.${suggestionPresentationState}`,
      meta: [
        ...(status.suggestion_generated && status.suggestion_id
          ? [{ key: "feed.processing.suggestionId", value: status.suggestion_id }]
          : []),
        ...(!status.suggestion_generated && status.suggestion_block_reason
          ? [{ key: "feed.processing.suggestionReason", valueKey: suggestionReasonKey(status, "label") }]
          : []),
        ...(!status.suggestion_generated && status.suggestion_block_detail
          ? [{ key: "feed.processing.suggestionDetail", value: status.suggestion_block_detail }]
          : []),
      ],
    },
```

In `H:\DouYin_llm\frontend\src\components\EventFeed.vue`, translate the new keys and render a second line for the short reason under the suggestion node:

```js
function processingTimeline(event) {
  return getCommentProcessingTimeline(event).map((item) => ({
    ...item,
    label: t(item.labelKey),
    reason: item.reasonKey ? t(item.reasonKey) : "",
  }));
}
```

```js
function processingDetails(event) {
  return getCommentProcessingDetails(event).map((item) => ({
    ...item,
    title: t(item.titleKey),
    summary: t(item.summaryKey),
    meta: item.meta.map((metaItem) => ({
      ...metaItem,
      label: t(metaItem.key),
      value: metaItem.valueKey ? t(metaItem.valueKey) : metaItem.value,
    })),
  }));
}
```

```vue
                    <div class="flex min-w-0 flex-col gap-1">
                      <div class="flex min-w-0 items-center gap-2">
                        <span
                          class="h-2.5 w-2.5 shrink-0 rounded-full"
                          :class="processingStepTone(step.state).dot"
                        />
                        <span
                          class="text-[11px] tracking-[0.12em]"
                          :class="processingStepTone(step.state).label"
                        >
                          {{ step.label }}
                        </span>
                      </div>
                      <p v-if="step.reason" class="pl-[1.15rem] text-[11px] leading-5 text-muted">
                        {{ step.reason }}
                      </p>
                    </div>
```

In `H:\DouYin_llm\frontend\src\i18n.js`, add the suggestion reason labels and new status copy under both locales:

```js
        suggestionReason: "未生成原因",
        suggestionDetail: "处理说明",
```

```js
          suggestionGenerated: {
            success: "已生成建议",
            neutral: "未生成建议",
            skipped: "已跳过生成",
            failed: "生成失败",
          },
```

```js
          suggestionGenerated: {
            title: "回复建议生成",
            success: "已生成回复建议，可继续用于提词。",
            neutral: "本次流程没有生成回复建议。",
            skipped: "本次流程明确跳过了建议生成。",
            failed: "本次流程尝试生成建议，但最终失败。",
          },
```

```js
        reason: {
          semantic_backend_unavailable: {
            short: "语义后端不可用",
            label: "语义后端不可用",
          },
          llm_failed: {
            short: "模型调用失败",
            label: "模型调用失败",
          },
          rule_skipped: {
            short: "命中跳过规则",
            label: "命中跳过规则",
          },
          no_generation_needed: {
            short: "当前评论无需生成",
            label: "当前评论无需生成",
          },
          unknown: {
            short: "原因未标注",
            label: "原因未标注",
          },
        },
```

Add the matching English copy in the `en.feed.processing` branch as well.

- [ ] **Step 4: Extend the EventFeed source-layout assertions**

Append to `H:\DouYin_llm\frontend\src\components\status-strip-layout.test.mjs`:

```js
assert.match(eventFeedSource, /reasonKey/);
assert.match(eventFeedSource, /feed\.processing\.suggestionReason/);
assert.match(eventFeedSource, /feed\.processing\.suggestionDetail/);
assert.match(eventFeedSource, /step\.reason/);
```

- [ ] **Step 5: Re-run the frontend checks**

Run:

```powershell
node H:\DouYin_llm\frontend\src\components\event-feed-processing-presenter.test.mjs
node H:\DouYin_llm\frontend\src\components\status-strip-layout.test.mjs
npm --prefix H:\DouYin_llm\frontend run build
```

Expected: all three commands PASS.

- [ ] **Step 6: Commit the frontend timeline slice**

```bash
git -C H:\DouYin_llm add frontend/src/components/event-feed-processing-presenter.js frontend/src/components/event-feed-processing-presenter.test.mjs frontend/src/components/EventFeed.vue frontend/src/components/status-strip-layout.test.mjs frontend/src/i18n.js
git -C H:\DouYin_llm commit -m "feat: show suggestion block reasons in comment timeline"
```

### Task 4: Final verification and scope review

**Files:**
- Review: `H:\DouYin_llm\backend\services\agent.py`
- Review: `H:\DouYin_llm\backend\schemas\live.py`
- Review: `H:\DouYin_llm\backend\app.py`
- Review: `H:\DouYin_llm\frontend\src\components\event-feed-processing-presenter.js`
- Review: `H:\DouYin_llm\frontend\src\components\EventFeed.vue`
- Review: `H:\DouYin_llm\frontend\src\i18n.js`

- [ ] **Step 1: Run the targeted backend and frontend verification suite**

Run:

```powershell
python -m pytest H:\DouYin_llm\tests\test_agent.py H:\DouYin_llm\tests\test_comment_processing_status.py -q
node H:\DouYin_llm\frontend\src\components\event-feed-processing-presenter.test.mjs
node H:\DouYin_llm\frontend\src\components\status-strip-layout.test.mjs
npm --prefix H:\DouYin_llm\frontend run build
```

Expected: PASS on all commands.

- [ ] **Step 2: Review the final diff for scope discipline**

Run:

```powershell
git -C H:\DouYin_llm diff -- backend/services/agent.py backend/schemas/live.py backend/app.py tests/test_agent.py tests/test_comment_processing_status.py frontend/src/components/event-feed-processing-presenter.js frontend/src/components/event-feed-processing-presenter.test.mjs frontend/src/components/EventFeed.vue frontend/src/components/status-strip-layout.test.mjs frontend/src/i18n.js
```

Expected: only suggestion-outcome status plumbing and timeline reason visibility changes appear.

- [ ] **Step 3: Confirm unrelated working-tree files remain outside the feature work**

Run: `git -C H:\DouYin_llm status --short`

Expected: unrelated `.qoder/...` and pre-existing untracked plan files remain untouched unless explicitly requested later.
