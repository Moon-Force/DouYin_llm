# Status Strip Layout Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild the top status strip into a clear left/right workspace header with carded sections and a visual connection-status badge, without changing existing live-room behavior.

**Architecture:** Keep the existing `StatusStrip.vue` entry point and props/events contract, but extract the connection-status presentation into small computed helpers so layout work stays readable. The redesign remains frontend-only: no API, store shape, or parent layout changes outside the header. Verification uses one focused smoke test for the status helpers plus a full frontend production build.

**Tech Stack:** Vue 3 SFCs, Pinia-fed props, Tailwind utility classes, node-based smoke tests, Vite build

---

## File Structure

- Modify: `H:\DouYin_llm\frontend\src\components\StatusStrip.vue`
  - Responsibility: render the redesigned dual-column header, cards, tool group, and connection status badge
- Create: `H:\DouYin_llm\frontend\src\components\status-strip-presenter.js`
  - Responsibility: map connection state to translated label keys, badge tones, and icon tokens in a testable pure helper
- Create: `H:\DouYin_llm\frontend\src\components\status-strip-presenter.test.mjs`
  - Responsibility: verify connection-state badge mapping for idle/connecting/live/reconnecting/switching

## Task 1: Add a testable connection-status presenter

**Files:**
- Create: `H:\DouYin_llm\frontend\src\components\status-strip-presenter.js`
- Test: `H:\DouYin_llm\frontend\src\components\status-strip-presenter.test.mjs`

- [ ] **Step 1: Write the failing test**

```javascript
import assert from "node:assert/strict";

import { getConnectionBadgePresentation } from "./status-strip-presenter.js";

assert.deepEqual(getConnectionBadgePresentation("idle"), {
  tone: "danger",
  labelKey: "status.connectionState.idle",
  icon: "dot",
});

assert.deepEqual(getConnectionBadgePresentation("connecting"), {
  tone: "warning",
  labelKey: "status.connectionState.connecting",
  icon: "pulse",
});

assert.deepEqual(getConnectionBadgePresentation("live"), {
  tone: "success",
  labelKey: "status.connectionState.live",
  icon: "check",
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `node H:\DouYin_llm\frontend\src\components\status-strip-presenter.test.mjs`
Expected: FAIL with module-not-found or missing export for `getConnectionBadgePresentation`

- [ ] **Step 3: Write minimal implementation**

```javascript
const CONNECTION_BADGE_MAP = {
  idle: { tone: "danger", labelKey: "status.connectionState.idle", icon: "dot" },
  reconnecting: { tone: "danger", labelKey: "status.connectionState.reconnecting", icon: "dot" },
  connecting: { tone: "warning", labelKey: "status.connectionState.connecting", icon: "pulse" },
  switching: { tone: "warning", labelKey: "status.connectionState.switching", icon: "pulse" },
  live: { tone: "success", labelKey: "status.connectionState.live", icon: "check" },
};

export function getConnectionBadgePresentation(connectionState) {
  return CONNECTION_BADGE_MAP[connectionState] || CONNECTION_BADGE_MAP.idle;
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `node H:\DouYin_llm\frontend\src\components\status-strip-presenter.test.mjs`
Expected: PASS with no output

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/status-strip-presenter.js frontend/src/components/status-strip-presenter.test.mjs
git commit -m "test: add status strip presenter mapping"
```

## Task 2: Rebuild StatusStrip into a dual-column card layout

**Files:**
- Modify: `H:\DouYin_llm\frontend\src\components\StatusStrip.vue`
- Read: `H:\DouYin_llm\frontend\src\i18n.js`
- Read: `H:\DouYin_llm\docs\superpowers\specs\2026-04-13-status-strip-layout-redesign-design.md`

- [ ] **Step 1: Write the failing test expectation**

Document the behavior being added before editing the component:

```text
StatusStrip must render:
1. one left-side connection card
2. three right-side cards (comments, model, tools)
3. a visual connection badge that keeps the translated "未连接"/"Idle" text
```

Add one more assertion to the presenter test so the redesign depends on the helper:

```javascript
assert.equal(
  getConnectionBadgePresentation("reconnecting").labelKey,
  "status.connectionState.reconnecting",
);
```

- [ ] **Step 2: Run the presenter test again**

Run: `node H:\DouYin_llm\frontend\src\components\status-strip-presenter.test.mjs`
Expected: PASS, confirming the layout refactor is safe to build on the helper

- [ ] **Step 3: Write the minimal implementation**

Update `StatusStrip.vue` with this structure:

```vue
<header class="rounded-[28px] border border-line/14 bg-panel/92 p-4 shadow-[var(--shadow-elev)]">
  <div class="grid gap-4 xl:grid-cols-[1.4fr_1fr]">
    <section class="rounded-[24px] border border-line/12 bg-panel-soft/70 p-5">
      <!-- room label, current room, input row, switch button, connection badge -->
    </section>

    <section class="grid gap-3 md:grid-cols-3">
      <article class="rounded-[22px] border border-line/12 bg-panel-soft/60 p-4">
        <!-- comments card -->
      </article>
      <article class="rounded-[22px] border border-line/12 bg-panel-soft/60 p-4">
        <!-- model card -->
      </article>
      <article class="rounded-[22px] border border-line/12 bg-panel-soft/60 p-4">
        <!-- tools card -->
      </article>
    </section>
  </div>
</header>
```

Inside the component, use the helper like this:

```javascript
import { getConnectionBadgePresentation } from "./status-strip-presenter.js";

const connectionBadge = computed(() =>
  getConnectionBadgePresentation(props.connectionState),
);

const connectionBadgeLabel = computed(() =>
  t(connectionBadge.value.labelKey),
);
```

Render the badge with tone classes:

```vue
<span
  class="inline-flex items-center gap-2 rounded-full px-3 py-1 text-xs font-medium"
  :class="{
    'bg-rose-500/12 text-rose-300 ring-1 ring-inset ring-rose-400/25': connectionBadge.tone === 'danger',
    'bg-amber-500/12 text-amber-200 ring-1 ring-inset ring-amber-400/25': connectionBadge.tone === 'warning',
    'bg-emerald-500/12 text-emerald-300 ring-1 ring-inset ring-emerald-400/25': connectionBadge.tone === 'success',
  }"
>
  <span class="h-2 w-2 rounded-full bg-current"></span>
  {{ connectionBadgeLabel }}
</span>
```

Keep the existing emits and props unchanged:

```javascript
defineEmits([
  "update-room-draft",
  "switch-room",
  "toggle-theme",
  "toggle-locale",
  "open-llm-settings",
]);
```

- [ ] **Step 4: Run the verification commands**

Run: `node H:\DouYin_llm\frontend\src\components\status-strip-presenter.test.mjs`
Expected: PASS

Run: `npm run build`
Expected: `✓ built in ...`

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/StatusStrip.vue frontend/src/components/status-strip-presenter.js frontend/src/components/status-strip-presenter.test.mjs
git commit -m "feat: redesign status strip layout"
```

## Task 3: Final verification sweep

**Files:**
- Verify: `H:\DouYin_llm\frontend\src\components\StatusStrip.vue`
- Verify: `H:\DouYin_llm\frontend\src\components\status-strip-presenter.js`
- Verify: `H:\DouYin_llm\frontend\src\components\status-strip-presenter.test.mjs`

- [ ] **Step 1: Run the focused smoke test**

Run: `node H:\DouYin_llm\frontend\src\components\status-strip-presenter.test.mjs`
Expected: PASS

- [ ] **Step 2: Run the existing frontend smoke tests**

Run: `node H:\DouYin_llm\frontend\src\stores\locale.test.mjs`
Expected: PASS

Run: `node H:\DouYin_llm\frontend\src\stores\llm-settings.test.mjs`
Expected: PASS

Run: `node H:\DouYin_llm\frontend\src\stores\viewer-workbench.test.mjs`
Expected: PASS

Run: `node H:\DouYin_llm\frontend\src\stores\live.test.mjs`
Expected: PASS

- [ ] **Step 3: Run the production build**

Run: `npm run build`
Expected: `✓ built in ...`

- [ ] **Step 4: Review the diff**

Run: `git -c safe.directory=H:/DouYin_llm diff -- frontend/src/components/StatusStrip.vue frontend/src/components/status-strip-presenter.js frontend/src/components/status-strip-presenter.test.mjs`
Expected: only the planned header-layout and status-badge changes

- [ ] **Step 5: Commit any final polish**

```bash
git add frontend/src/components/StatusStrip.vue frontend/src/components/status-strip-presenter.js frontend/src/components/status-strip-presenter.test.mjs
git commit -m "test: verify status strip redesign"
```

## Self-Review

- Spec coverage:
  - Dual-column header is implemented in Task 2
  - Connection/comment/model/tool card split is implemented in Task 2
  - Visual connection badge for “未连接” is implemented in Tasks 1 and 2
  - Verification is covered in Task 3
- Placeholder scan:
  - No `TODO`, `TBD`, or “handle appropriately” placeholders remain
- Type consistency:
  - `getConnectionBadgePresentation(connectionState)` is defined in Task 1 and reused consistently in Task 2 and Task 3

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-04-13-status-strip-layout-redesign.md`. Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**
