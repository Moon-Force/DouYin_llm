# Comment Processing Timeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the comment status badge row in the event feed with a mixed timeline UI: horizontal summary by default and vertical processing trail when expanded.

**Architecture:** Keep all processing-state interpretation inside the presenter layer so `EventFeed.vue` only renders view models. Reuse the existing `expandedEventIds` interaction, extend the i18n keys for Chinese/English labels, and verify both presenter logic and template structure with the existing lightweight Node-based frontend tests plus a production build.

**Tech Stack:** Vue 3 SFCs, plain ESM presenter modules, Tailwind utility classes, Node built-in test/assert tooling, Vite build.

---

### Task 1: Refactor the presenter to emit timeline view models

**Files:**
- Modify: `H:\DouYin_llm\frontend\src\components\event-feed-processing-presenter.js`
- Test: `H:\DouYin_llm\frontend\src\components\event-feed-processing-presenter.test.mjs`

- [ ] **Step 1: Rewrite the presenter test to describe the new timeline API**

```js
import assert from "node:assert/strict";

import {
  getCommentProcessingDetails,
  getCommentProcessingTimeline,
} from "./event-feed-processing-presenter.js";

const successEvent = {
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
    suggestion_id: "sug-1",
  },
};

assert.deepEqual(getCommentProcessingTimeline(successEvent), [
  { key: "received", state: "success", labelKey: "feed.processing.timeline.received.success" },
  { key: "persisted", state: "success", labelKey: "feed.processing.timeline.persisted.success" },
  { key: "memorySaved", state: "success", labelKey: "feed.processing.timeline.memorySaved.success" },
  { key: "memoryRecalled", state: "success", labelKey: "feed.processing.timeline.memoryRecalled.success" },
  { key: "suggestionGenerated", state: "success", labelKey: "feed.processing.timeline.suggestionGenerated.success" },
]);

assert.deepEqual(getCommentProcessingDetails(successEvent), [
  {
    key: "received",
    state: "success",
    titleKey: "feed.processing.detail.received.title",
    summaryKey: "feed.processing.detail.received.success",
    meta: [],
  },
  {
    key: "persisted",
    state: "success",
    titleKey: "feed.processing.detail.persisted.title",
    summaryKey: "feed.processing.detail.persisted.success",
    meta: [],
  },
  {
    key: "memorySaved",
    state: "success",
    titleKey: "feed.processing.detail.memorySaved.title",
    summaryKey: "feed.processing.detail.memorySaved.success",
    meta: [{ key: "feed.processing.savedMemoryIds", value: "mem-1" }],
  },
  {
    key: "memoryRecalled",
    state: "success",
    titleKey: "feed.processing.detail.memoryRecalled.title",
    summaryKey: "feed.processing.detail.memoryRecalled.success",
    meta: [{ key: "feed.processing.recalledMemoryIds", value: "mem-9" }],
  },
  {
    key: "suggestionGenerated",
    state: "success",
    titleKey: "feed.processing.detail.suggestionGenerated.title",
    summaryKey: "feed.processing.detail.suggestionGenerated.success",
    meta: [{ key: "feed.processing.suggestionId", value: "sug-1" }],
  },
]);

const skippedRecallEvent = {
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
  },
};

assert.equal(
  getCommentProcessingTimeline(skippedRecallEvent)[3].labelKey,
  "feed.processing.timeline.memoryRecalled.skipped",
);
assert.equal(
  getCommentProcessingDetails(skippedRecallEvent)[2].summaryKey,
  "feed.processing.detail.memorySaved.neutral",
);
assert.equal(
  getCommentProcessingDetails(skippedRecallEvent)[3].summaryKey,
  "feed.processing.detail.memoryRecalled.skipped",
);

assert.deepEqual(
  getCommentProcessingTimeline({ event_type: "gift", processing_status: { persisted: true } }),
  [],
);
assert.deepEqual(
  getCommentProcessingDetails({ event_type: "gift", processing_status: { persisted: true } }),
  [],
);
```

- [ ] **Step 2: Run the presenter test and confirm it fails on the missing export / old data shape**

Run: `node H:\DouYin_llm\frontend\src\components\event-feed-processing-presenter.test.mjs`

Expected: FAIL with an import error for `getCommentProcessingTimeline`, or a deep-equal mismatch because the presenter still returns badge-oriented data.

- [ ] **Step 3: Implement timeline/detail builders in the presenter**

```js
function isCommentWithStatus(event) {
  return event?.event_type === "comment" && event?.processing_status;
}

function joinIds(values) {
  return Array.isArray(values) && values.length > 0 ? values.join(", ") : "";
}

function buildMeta(key, values) {
  const joined = joinIds(values);
  return joined ? [{ key, value: joined }] : [];
}

function buildState(status, successFlag, attemptedFlag) {
  if (status?.[successFlag]) {
    return "success";
  }
  if (attemptedFlag && status?.[attemptedFlag] === false) {
    return "skipped";
  }
  return "neutral";
}

export function getCommentProcessingTimeline(event) {
  if (!isCommentWithStatus(event)) {
    return [];
  }

  const status = event.processing_status;

  return [
    { key: "received", state: status.received ? "success" : "neutral", labelKey: `feed.processing.timeline.received.${status.received ? "success" : "neutral"}` },
    { key: "persisted", state: status.persisted ? "success" : "neutral", labelKey: `feed.processing.timeline.persisted.${status.persisted ? "success" : "neutral"}` },
    {
      key: "memorySaved",
      state: buildState(status, "memory_saved", "memory_extraction_attempted"),
      labelKey: `feed.processing.timeline.memorySaved.${buildState(status, "memory_saved", "memory_extraction_attempted")}`,
    },
    {
      key: "memoryRecalled",
      state: buildState(status, "memory_recalled", "memory_recall_attempted"),
      labelKey: `feed.processing.timeline.memoryRecalled.${buildState(status, "memory_recalled", "memory_recall_attempted")}`,
    },
    {
      key: "suggestionGenerated",
      state: status.suggestion_generated ? "success" : "neutral",
      labelKey: `feed.processing.timeline.suggestionGenerated.${status.suggestion_generated ? "success" : "neutral"}`,
    },
  ];
}

export function getCommentProcessingDetails(event) {
  if (!isCommentWithStatus(event)) {
    return [];
  }

  const status = event.processing_status;
  const memorySavedState = buildState(status, "memory_saved", "memory_extraction_attempted");
  const memoryRecalledState = buildState(status, "memory_recalled", "memory_recall_attempted");

  return [
    {
      key: "received",
      state: status.received ? "success" : "neutral",
      titleKey: "feed.processing.detail.received.title",
      summaryKey: `feed.processing.detail.received.${status.received ? "success" : "neutral"}`,
      meta: [],
    },
    {
      key: "persisted",
      state: status.persisted ? "success" : "neutral",
      titleKey: "feed.processing.detail.persisted.title",
      summaryKey: `feed.processing.detail.persisted.${status.persisted ? "success" : "neutral"}`,
      meta: [],
    },
    {
      key: "memorySaved",
      state: memorySavedState,
      titleKey: "feed.processing.detail.memorySaved.title",
      summaryKey: `feed.processing.detail.memorySaved.${memorySavedState}`,
      meta: buildMeta("feed.processing.savedMemoryIds", status.saved_memory_ids),
    },
    {
      key: "memoryRecalled",
      state: memoryRecalledState,
      titleKey: "feed.processing.detail.memoryRecalled.title",
      summaryKey: `feed.processing.detail.memoryRecalled.${memoryRecalledState}`,
      meta: buildMeta("feed.processing.recalledMemoryIds", status.recalled_memory_ids),
    },
    {
      key: "suggestionGenerated",
      state: status.suggestion_generated ? "success" : "neutral",
      titleKey: "feed.processing.detail.suggestionGenerated.title",
      summaryKey: `feed.processing.detail.suggestionGenerated.${status.suggestion_generated ? "success" : "neutral"}`,
      meta: status.suggestion_id
        ? [{ key: "feed.processing.suggestionId", value: status.suggestion_id }]
        : [],
    },
  ];
}
```

- [ ] **Step 4: Run the presenter test again**

Run: `node H:\DouYin_llm\frontend\src\components\event-feed-processing-presenter.test.mjs`

Expected: PASS with no output.

- [ ] **Step 5: Commit the presenter refactor**

```bash
git -C H:\DouYin_llm add frontend/src/components/event-feed-processing-presenter.js frontend/src/components/event-feed-processing-presenter.test.mjs
git -C H:\DouYin_llm commit -m "feat: add comment processing timeline presenter"
```

### Task 2: Replace badge rendering in the event card with the mixed timeline UI

**Files:**
- Modify: `H:\DouYin_llm\frontend\src\components\EventFeed.vue`
- Modify: `H:\DouYin_llm\frontend\src\i18n.js`
- Test: `H:\DouYin_llm\frontend\src\components\status-strip-layout.test.mjs`

- [ ] **Step 1: Add i18n keys for timeline labels, detail titles, and detail summaries**

```js
processing: {
  showDetails: "查看轨迹",
  hideDetails: "收起轨迹",
  savedMemoryIds: "保存记忆 ID",
  recalledMemoryIds: "召回记忆 ID",
  suggestionId: "提词 ID",
  timeline: {
    received: { success: "已接收", neutral: "待接收" },
    persisted: { success: "已入库", neutral: "未入库" },
    memorySaved: { success: "已写记忆", neutral: "未写记忆", skipped: "已跳过" },
    memoryRecalled: { success: "已召回", neutral: "未召回", skipped: "已跳过" },
    suggestionGenerated: { success: "已生成建议", neutral: "未生成建议" },
  },
  detail: {
    received: {
      title: "收到评论",
      success: "系统已接收该评论并进入处理流程",
      neutral: "系统尚未确认收到该评论",
    },
    persisted: {
      title: "评论入库",
      success: "评论已成功写入本地存储",
      neutral: "评论尚未写入本地存储",
    },
    memorySaved: {
      title: "观众记忆写入",
      success: "已从这条评论中保存观众记忆",
      neutral: "已尝试提取记忆，但没有可保存内容",
      skipped: "本次流程跳过了记忆写入",
    },
    memoryRecalled: {
      title: "观众记忆召回",
      success: "已参与语义召回并命中观众记忆",
      neutral: "已参与语义召回，但没有命中观众记忆",
      skipped: "本次流程跳过了观众记忆召回",
    },
    suggestionGenerated: {
      title: "回复建议生成",
      success: "已生成回复建议，可继续用于提词",
      neutral: "本次流程没有生成回复建议",
    },
  },
}
```

Mirror the same structure in the `en` dictionary with concise English equivalents so locale switching keeps working.

- [ ] **Step 2: Update `EventFeed.vue` to consume timeline/detail view models instead of badge text**

```vue
<script setup>
import {
  getCommentProcessingDetails,
  getCommentProcessingTimeline,
} from "./event-feed-processing-presenter.js";

function processingTimeline(event) {
  return getCommentProcessingTimeline(event).map((item) => ({
    ...item,
    label: t(item.labelKey),
  }));
}

function processingDetails(event) {
  return getCommentProcessingDetails(event).map((item) => ({
    ...item,
    title: t(item.titleKey),
    summary: t(item.summaryKey),
    meta: item.meta.map((metaItem) => ({
      ...metaItem,
      label: t(metaItem.key),
    })),
  }));
}

function processingStepClass(state) {
  if (state === "success") return "border-emerald-300/50 bg-emerald-400/18 text-emerald-100";
  if (state === "skipped") return "border-line/12 bg-panel/55 text-muted";
  return "border-amber-300/30 bg-amber-400/12 text-paper/80";
}
</script>

<div v-if="processingTimeline(event).length > 0" class="mt-4 rounded-2xl border border-line/12 bg-panel-soft/55 px-3 py-3">
  <div class="flex flex-wrap items-start gap-2 sm:gap-0">
    <div
      v-for="(step, index) in processingTimeline(event)"
      :key="step.key"
      class="flex min-w-[96px] flex-1 items-center gap-2"
    >
      <div class="flex items-center gap-2">
        <span class="h-2.5 w-2.5 rounded-full" :class="processingStepClass(step.state)" />
        <span class="text-[11px] tracking-[0.12em]" :class="step.state === 'success' ? 'text-paper' : 'text-muted'">
          {{ step.label }}
        </span>
      </div>
      <span
        v-if="index < processingTimeline(event).length - 1"
        class="hidden h-px flex-1 bg-line/20 sm:block"
        :class="step.state === 'skipped' ? 'border-t border-dashed border-line/16 bg-transparent' : ''"
      />
    </div>
  </div>

  <button
    v-if="hasProcessingDetails(event)"
    type="button"
    class="mt-3 rounded-full border border-line/16 bg-panel px-2.5 py-1 text-[11px] tracking-[0.12em] text-accent transition hover:border-accent/40"
    @click="toggleProcessingDetails(event)"
  >
    {{ isProcessingExpanded(event) ? t("feed.processing.hideDetails") : t("feed.processing.showDetails") }}
  </button>

  <ol v-if="isProcessingExpanded(event)" class="mt-4 space-y-3 border-l border-line/14 pl-4">
    <li v-for="detail in processingDetails(event)" :key="detail.key" class="relative">
      <span class="absolute -left-[1.08rem] top-1.5 h-2.5 w-2.5 rounded-full" :class="processingStepClass(detail.state)" />
      <p class="text-sm font-medium text-paper">{{ detail.title }}</p>
      <p class="mt-1 text-xs leading-5 text-muted">{{ detail.summary }}</p>
      <dl v-if="detail.meta.length > 0" class="mt-2 space-y-1">
        <div v-for="item in detail.meta" :key="`${detail.key}-${item.key}`" class="text-xs text-paper/80">
          <dt class="inline text-muted">{{ item.label }}：</dt>
          <dd class="inline break-all">{{ item.value }}</dd>
        </div>
      </dl>
    </li>
  </ol>
</div>
```

- [ ] **Step 3: Add a structural test that guards the new timeline markup**

Append assertions to `H:\DouYin_llm\frontend\src\components\status-strip-layout.test.mjs`:

```js
const eventFeedPath = fileURLToPath(new URL("./EventFeed.vue", import.meta.url));
const eventFeedSource = readFileSync(eventFeedPath, "utf8");

assert.match(eventFeedSource, /getCommentProcessingTimeline/);
assert.match(eventFeedSource, /processingStepClass/);
assert.match(eventFeedSource, /border-l border-line\\/14 pl-4/);
assert.match(eventFeedSource, /feed\\.processing\\.timeline\\.received\\.success/);
assert.doesNotMatch(eventFeedSource, /getCommentProcessingBadges/);
```

- [ ] **Step 4: Run the frontend Node tests**

Run:

```powershell
node H:\DouYin_llm\frontend\src\components\event-feed-processing-presenter.test.mjs
node H:\DouYin_llm\frontend\src\components\status-strip-layout.test.mjs
```

Expected: both commands PASS with no output.

- [ ] **Step 5: Commit the timeline UI**

```bash
git -C H:\DouYin_llm add frontend/src/components/EventFeed.vue frontend/src/components/status-strip-layout.test.mjs frontend/src/i18n.js
git -C H:\DouYin_llm commit -m "feat: render comment processing as timeline"
```

### Task 3: Run regression verification and prepare the branch for review

**Files:**
- Review: `H:\DouYin_llm\frontend\src\components\EventFeed.vue`
- Review: `H:\DouYin_llm\frontend\src\components\event-feed-processing-presenter.js`
- Review: `H:\DouYin_llm\frontend\src\i18n.js`
- Review: `H:\DouYin_llm\frontend\src\components\status-strip-layout.test.mjs`
- Review: `H:\DouYin_llm\frontend\src\components\event-feed-processing-presenter.test.mjs`

- [ ] **Step 1: Build the frontend**

Run: `npm --prefix H:\DouYin_llm\frontend run build`

Expected: Vite build succeeds and emits the production bundle under `H:\DouYin_llm\frontend\dist`.

- [ ] **Step 2: Re-run the targeted tests after the build**

Run:

```powershell
node H:\DouYin_llm\frontend\src\components\event-feed-processing-presenter.test.mjs
node H:\DouYin_llm\frontend\src\components\status-strip-layout.test.mjs
```

Expected: both commands PASS again, confirming the final code matches the tested shape.

- [ ] **Step 3: Review the final diff for scope discipline**

Run: `git -C H:\DouYin_llm diff -- frontend/src/components/EventFeed.vue frontend/src/components/event-feed-processing-presenter.js frontend/src/i18n.js frontend/src/components/status-strip-layout.test.mjs frontend/src/components/event-feed-processing-presenter.test.mjs`

Expected: diff only shows the timeline UI, presenter view-models, i18n additions, and matching tests; no unrelated event-feed behavior changes.

- [ ] **Step 4: Commit any final polish if needed**

```bash
git -C H:\DouYin_llm add frontend/src/components/EventFeed.vue frontend/src/components/event-feed-processing-presenter.js frontend/src/i18n.js frontend/src/components/status-strip-layout.test.mjs frontend/src/components/event-feed-processing-presenter.test.mjs
git -C H:\DouYin_llm commit -m "test: verify comment processing timeline flow"
```

Skip this commit if Task 1 and Task 2 already cover the final verified state with no additional edits.
