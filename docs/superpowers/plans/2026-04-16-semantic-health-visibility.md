# Semantic Health Visibility Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Document `EMBEDDING_STRICT` clearly and expose semantic backend health in the frontend status strip so operators can immediately see whether real semantic recall is available.

**Architecture:** Keep the backend API unchanged and consume the existing `/health`-style semantic fields through the frontend bootstrap snapshot. Ship this in two small, independently committable slices: first update docs and `.env.example`, then wire the bootstrap/store/status strip UI and matching tests.

**Tech Stack:** Markdown docs, dotenv example config, Vue 3 + Pinia, existing Node assert-based frontend tests, Vite/Tailwind UI components.

---

## File Structure

- Modify: `H:\DouYin_llm\README.md`
  Explain `EMBEDDING_STRICT`, what fallback paths it blocks, and how to inspect semantic backend health.

- Modify: `H:\DouYin_llm\.env.example`
  Add `EMBEDDING_STRICT=false` in the embedding section.

- Modify: `H:\DouYin_llm\frontend\src\stores\live.js`
  Store semantic health fields from bootstrap snapshots and room switches.

- Modify: `H:\DouYin_llm\frontend\src\stores\live.test.mjs`
  Verify store bootstrap picks up semantic health and still skips SSE when room id is empty.

- Modify: `H:\DouYin_llm\frontend\src\components\StatusStrip.vue`
  Render a semantic backend status card with success/warning/error states and the backend reason.

- Modify: `H:\DouYin_llm\frontend\src\components\status-strip-layout.test.mjs`
  Guard the new semantic status structure in the status strip template.

- Modify: `H:\DouYin_llm\frontend\src\i18n.js`
  Add semantic status labels in both Chinese and English.

### Task 1: Update strict-mode docs and environment example

**Files:**
- Modify: `H:\DouYin_llm\README.md`
- Modify: `H:\DouYin_llm\.env.example`

- [ ] **Step 1: Edit `README.md` to explain strict semantic mode**

Add the following content into the embedding / semantic retrieval sections of `H:\DouYin_llm\README.md`:

```md
### Strict Semantic Mode

If you require **real embeddings and real vector recall**, enable:

```powershell
EMBEDDING_STRICT=true
```

When strict mode is enabled:

- embedding generation is not allowed to fall back to hash embeddings
- vector recall is not allowed to fall back to token-overlap matching
- embedding rebuild will fail instead of writing pseudo embeddings

This is the recommended setting when semantic recall quality matters more than developer convenience.

### Semantic Health Fields

`GET /health` now returns:

- `embedding_strict`
- `semantic_backend_ready`
- `semantic_backend_reason`

Use these fields to distinguish “semantic recall returned no hit” from “semantic backend is unavailable”.
```

Also update the “改进方向” section so it no longer says strict semantic embedding is still missing; replace that bullet with a shorter follow-up such as strengthening observability on top of the new strict mode.

- [ ] **Step 2: Update `.env.example` with the new flag**

Modify the embedding block in `H:\DouYin_llm\.env.example` so it includes:

```dotenv
# Embedding
EMBEDDING_MODE=cloud
EMBEDDING_STRICT=false
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_BASE_URL=https://api.openai.com/v1
EMBEDDING_API_KEY=
EMBEDDING_TIMEOUT_SECONDS=10
LOCAL_EMBEDDING_DEVICE=cpu
LOCAL_EMBEDDING_BATCH_SIZE=32
```

- [ ] **Step 3: Review the doc diff for scope discipline**

Run:

```powershell
git -C H:\DouYin_llm diff -- README.md .env.example
```

Expected: only strict-mode explanation and config example changes appear; do not pull in unrelated README rewrites.

- [ ] **Step 4: Commit the docs/config example slice**

```bash
git -C H:\DouYin_llm add README.md .env.example
git -C H:\DouYin_llm commit -m "docs: explain strict semantic health settings"
```

### Task 2: Wire semantic backend health into the frontend store and status strip

**Files:**
- Modify: `H:\DouYin_llm\frontend\src\stores\live.js`
- Modify: `H:\DouYin_llm\frontend\src\stores\live.test.mjs`
- Modify: `H:\DouYin_llm\frontend\src\components\StatusStrip.vue`
- Modify: `H:\DouYin_llm\frontend\src\components\status-strip-layout.test.mjs`
- Modify: `H:\DouYin_llm\frontend\src\i18n.js`

- [ ] **Step 1: Rewrite the store test to include semantic health fields**

Replace `H:\DouYin_llm\frontend\src\stores\live.test.mjs` with:

```js
import assert from "node:assert/strict";

import { createPinia, setActivePinia } from "pinia";

import { useLiveStore } from "./live.js";

setActivePinia(createPinia());

const originalFetch = global.fetch;
const originalEventSource = global.EventSource;

let fetchUrl = null;
let eventSourceCount = 0;

global.fetch = async (url) => {
  fetchUrl = url;
  return {
    ok: true,
    async json() {
      return {
        room_id: "",
        recent_events: [],
        recent_suggestions: [],
        stats: {
          room_id: "",
          total_events: 0,
          comments: 0,
          gifts: 0,
          likes: 0,
          members: 0,
          follows: 0,
        },
        model_status: {
          mode: "heuristic",
          model: "heuristic",
          backend: "local",
          last_result: "idle",
          last_error: "",
          updated_at: 0,
        },
        embedding_strict: true,
        semantic_backend_ready: false,
        semantic_backend_reason: "Chroma is unavailable",
      };
    },
  };
};

global.EventSource = class {
  constructor() {
    eventSourceCount += 1;
  }
};

try {
  const store = useLiveStore();
  assert.equal(store.roomId, "");
  assert.equal(store.roomDraft, "");
  assert.equal(store.connectionState, "idle");

  await store.bootstrap();
  store.connect();

  assert.equal(fetchUrl, "/api/bootstrap");
  assert.equal(eventSourceCount, 0);
  assert.equal(store.connectionState, "idle");
  assert.equal(store.semanticHealth.embeddingStrict, true);
  assert.equal(store.semanticHealth.ready, false);
  assert.equal(store.semanticHealth.reason, "Chroma is unavailable");
} finally {
  global.fetch = originalFetch;
  global.EventSource = originalEventSource;
}
```

- [ ] **Step 2: Run the store test and verify it fails on the missing semantic health state**

Run: `node H:\DouYin_llm\frontend\src\stores\live.test.mjs`

Expected: FAIL because `store.semanticHealth` does not exist yet.

- [ ] **Step 3: Implement semantic health state in the Pinia store**

Update `H:\DouYin_llm\frontend\src\stores\live.js` by adding a semantic health state object near `modelStatus`:

```js
  const semanticHealth = ref({
    embeddingStrict: false,
    ready: true,
    reason: "",
  });
```

Update `hydrateSnapshot(payload)` so it stores the backend fields:

```js
  function hydrateSnapshot(payload) {
    roomId.value = `${payload.room_id ?? ""}`;
    stats.value = payload.stats || createEmptyStats(roomId.value);
    modelStatus.value = payload.model_status || modelStatus.value;
    semanticHealth.value = {
      embeddingStrict: Boolean(payload.embedding_strict),
      ready: payload.semantic_backend_ready !== false,
      reason: `${payload.semantic_backend_reason ?? ""}`,
    };
    events.value = payload.recent_events || [];
    suggestions.value = payload.recent_suggestions || [];
    if (!roomId.value) {
      connectionState.value = "idle";
    }
  }
```

Return `semanticHealth` from the store API:

```js
    modelStatus,
    semanticHealth,
    llmSettings,
```

- [ ] **Step 4: Re-run the store test**

Run: `node H:\DouYin_llm\frontend\src\stores\live.test.mjs`

Expected: PASS.

- [ ] **Step 5: Add i18n keys for semantic health**

In `H:\DouYin_llm\frontend\src\i18n.js`, add under `status`:

```js
      semantic: {
        title: "语义后端",
        ready: "语义后端正常",
        unavailable: "语义后端异常",
        strictEnabled: "严格模式已开启",
        reason: "异常原因",
      },
```

And under English `status`:

```js
      semantic: {
        title: "Semantic Backend",
        ready: "Semantic backend ready",
        unavailable: "Semantic backend unavailable",
        strictEnabled: "Strict mode enabled",
        reason: "Reason",
      },
```

- [ ] **Step 6: Update the status strip to render semantic backend health**

Modify `H:\DouYin_llm\frontend\src\components\StatusStrip.vue`:

1. Add a new required prop:

```js
  semanticHealth: {
    type: Object,
    required: true,
  },
```

2. Add computed helpers in `<script setup>`:

```js
const semanticStatusLabel = computed(() =>
  t(props.semanticHealth.ready ? "status.semantic.ready" : "status.semantic.unavailable"),
);

const semanticReasonLabel = computed(() =>
  props.semanticHealth.reason || t("common.noData"),
);

const semanticCardClass = computed(() =>
  props.semanticHealth.ready
    ? "border-emerald-400/20 bg-emerald-500/10"
    : "border-amber-300/30 bg-amber-500/12",
);
```

3. Change the card grid from `md:grid-cols-3` to `md:grid-cols-4`.

4. Insert a new card between the model card and tools card:

```vue
        <article class="rounded-[22px] border p-4" :class="semanticCardClass">
          <p class="text-[11px] uppercase tracking-[0.28em] text-muted">
            {{ t("status.semantic.title") }}
          </p>
          <p class="mt-4 text-sm font-semibold text-paper">
            {{ semanticStatusLabel }}
          </p>
          <p
            v-if="semanticHealth.embeddingStrict"
            class="mt-2 text-xs font-medium text-accent"
          >
            {{ t("status.semantic.strictEnabled") }}
          </p>
          <p class="mt-2 min-h-[2.5rem] break-words text-xs leading-5 text-muted">
            {{ semanticReasonLabel }}
          </p>
        </article>
```

- [ ] **Step 7: Extend the status strip structure test**

Append to `H:\DouYin_llm\frontend\src\components\status-strip-layout.test.mjs`:

```js
assert.match(statusStripSource, /md:grid-cols-4/);
assert.match(statusStripSource, /semanticHealth/);
assert.match(statusStripSource, /status\.semantic\.title/);
assert.match(statusStripSource, /status\.semantic\.strictEnabled/);
```

- [ ] **Step 8: Pass the new prop from the app shell**

Find the `StatusStrip` usage in `H:\DouYin_llm\frontend\src\App.vue` and add:

```vue
      :semantic-health="live.semanticHealth"
```

Use the component’s existing prop naming style if the template is already camelCase.

- [ ] **Step 9: Run the frontend checks**

Run:

```powershell
node H:\DouYin_llm\frontend\src\stores\live.test.mjs
node H:\DouYin_llm\frontend\src\components\status-strip-layout.test.mjs
npm --prefix H:\DouYin_llm\frontend run build
```

Expected: all three commands PASS.

- [ ] **Step 10: Commit the frontend semantic health slice**

```bash
git -C H:\DouYin_llm add frontend/src/stores/live.js frontend/src/stores/live.test.mjs frontend/src/components/StatusStrip.vue frontend/src/components/status-strip-layout.test.mjs frontend/src/i18n.js frontend/src/App.vue
git -C H:\DouYin_llm commit -m "feat: show semantic backend health in status strip"
```

### Task 3: Final scope review

**Files:**
- Review: `H:\DouYin_llm\README.md`
- Review: `H:\DouYin_llm\.env.example`
- Review: `H:\DouYin_llm\frontend\src\stores\live.js`
- Review: `H:\DouYin_llm\frontend\src\components\StatusStrip.vue`
- Review: `H:\DouYin_llm\frontend\src\i18n.js`

- [ ] **Step 1: Review only the intended files**

Run:

```powershell
git -C H:\DouYin_llm diff -- README.md .env.example frontend/src/stores/live.js frontend/src/stores/live.test.mjs frontend/src/components/StatusStrip.vue frontend/src/components/status-strip-layout.test.mjs frontend/src/i18n.js frontend/src/App.vue
```

Expected: only strict-mode docs/env updates and semantic health frontend visibility changes appear.

- [ ] **Step 2: Confirm unrelated working tree files remain unstaged**

Run: `git -C H:\DouYin_llm status --short`

Expected: `.qoder/...` files and plan/spec docs remain outside the feature commits unless explicitly requested later.
