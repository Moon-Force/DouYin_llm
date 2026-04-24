# Frontend API Extraction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extract frontend network requests from `frontend/src/stores/live.js` into focused API modules without changing runtime behavior.

**Architecture:** Introduce small `src/api` helpers that wrap `fetch` and preserve the existing request URLs, methods, and payload shapes. Keep `live.js` as the orchestration layer for state and UI flow, but replace direct `fetch` calls with imported API functions so later store and component splits can proceed on stable boundaries.

**Tech Stack:** Vue 3, Pinia, native `fetch`, native Node `.mjs` tests, Vite

---

### Task 1: Add API module tests

**Files:**
- Create: `H:/DouYin_llm/frontend/src/api/live-api.test.mjs`
- Create: `H:/DouYin_llm/frontend/src/api/viewer-api.test.mjs`

- [ ] **Step 1: Write the failing tests**

```javascript
import assert from "node:assert/strict";
import {
  bootstrapLiveState,
  saveLlmSettings,
  switchLiveRoom,
} from "./live-api.js";

global.fetch = async (url, options = {}) => ({
  ok: true,
  async json() {
    return { url, options };
  },
});

const bootstrap = await bootstrapLiveState("9527");
assert.equal(bootstrap.url, "/api/bootstrap?room_id=9527");

const switched = await switchLiveRoom("9528");
assert.equal(switched.url, "/api/room");
assert.equal(switched.options.method, "POST");

const saved = await saveLlmSettings({ model: "qwen", systemPrompt: "hi" });
assert.equal(saved.url, "/api/settings/llm");
assert.equal(JSON.parse(saved.options.body).system_prompt, "hi");
```

```javascript
import assert from "node:assert/strict";
import {
  deleteViewerMemoryRequest,
  deleteViewerNoteRequest,
  loadViewerDetailsRequest,
  loadViewerMemoryLogsRequest,
  saveViewerMemoryRequest,
  saveViewerNoteRequest,
  updateViewerMemoryStatusRequest,
} from "./viewer-api.js";

global.fetch = async (url, options = {}) => ({
  ok: true,
  async json() {
    return { url, options };
  },
});

const detail = await loadViewerDetailsRequest({
  roomId: "1",
  viewerId: "id:u1",
  nickname: "A",
});
assert.equal(detail.url, "/api/viewer?room_id=1&viewer_id=id%3Au1&nickname=A");

const note = await saveViewerNoteRequest({
  roomId: "1",
  viewerId: "id:u1",
  content: "note",
  isPinned: true,
});
assert.equal(note.url, "/api/viewer/notes");

const memory = await saveViewerMemoryRequest("/api/viewer/memories", "POST", {
  room_id: "1",
  viewer_id: "id:u1",
  memory_text: "likes ramen",
});
assert.equal(memory.options.method, "POST");

await updateViewerMemoryStatusRequest("m1", "invalidate", "expired");
await deleteViewerMemoryRequest("m1", "expired");
await deleteViewerNoteRequest("n1");
await loadViewerMemoryLogsRequest("m1");
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `node frontend/src/api/live-api.test.mjs`
Expected: FAIL with module-not-found for `./live-api.js`

Run: `node frontend/src/api/viewer-api.test.mjs`
Expected: FAIL with module-not-found for `./viewer-api.js`

- [ ] **Step 3: Write minimal implementation**

```javascript
export async function bootstrapLiveState(roomId = "") {
  const normalizedRoomId = `${roomId ?? ""}`.trim();
  const url = normalizedRoomId
    ? `/api/bootstrap?${new URLSearchParams({ room_id: normalizedRoomId }).toString()}`
    : "/api/bootstrap";
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(response.statusText || "Failed to bootstrap live state");
  }
  return response.json();
}
```

```javascript
async function parseJsonOrEmpty(response) {
  return response.json().catch(() => ({}));
}

export async function saveViewerNoteRequest(payload) {
  const response = await fetch("/api/viewer/notes", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    const data = await parseJsonOrEmpty(response);
    throw new Error(data.detail || response.statusText || "viewer note request failed");
  }
  return response.json();
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `node frontend/src/api/live-api.test.mjs`
Expected: PASS with no output

Run: `node frontend/src/api/viewer-api.test.mjs`
Expected: PASS with no output

- [ ] **Step 5: Commit**

```bash
git add frontend/src/api/live-api.js frontend/src/api/live-api.test.mjs frontend/src/api/viewer-api.js frontend/src/api/viewer-api.test.mjs
git commit -m "refactor(frontend): 提取 live store 的 API 请求模块"
```

### Task 2: Migrate store calls to API modules

**Files:**
- Modify: `H:/DouYin_llm/frontend/src/stores/live.js`
- Test: `H:/DouYin_llm/frontend/src/stores/live.test.mjs`
- Test: `H:/DouYin_llm/frontend/src/stores/viewer-workbench.test.mjs`

- [ ] **Step 1: Run existing store tests as baseline**

Run: `node frontend/src/stores/live.test.mjs`
Expected: PASS

Run: `node frontend/src/stores/viewer-workbench.test.mjs`
Expected: PASS

- [ ] **Step 2: Replace direct fetch calls with API imports**

```javascript
import {
  bootstrapLiveState,
  loadLlmSettingsRequest,
  saveLlmSettingsRequest,
  switchLiveRoom,
} from "../api/live-api.js";
import {
  deleteViewerMemoryRequest,
  deleteViewerNoteRequest,
  loadViewerDetailsRequest,
  loadViewerMemoryLogsRequest,
  saveViewerMemoryRequest,
  saveViewerNoteRequest,
  updateViewerMemoryStatusRequest,
} from "../api/viewer-api.js";
```

- [ ] **Step 3: Keep store-specific error mapping in place**

```javascript
try {
  const viewer = await loadViewerDetailsRequest({
    roomId: payload.roomId,
    viewerId: payload.viewerId,
    nickname: payload.nickname ?? "",
  });
  viewerWorkbench.value.viewer = viewer;
} catch (error) {
  viewerWorkbench.value.error = getViewerErrorMessage(error, "errors.viewerLoadFailed");
}
```

- [ ] **Step 4: Re-run store tests**

Run: `node frontend/src/stores/live.test.mjs`
Expected: PASS

Run: `node frontend/src/stores/viewer-workbench.test.mjs`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/stores/live.js
git commit -m "refactor(frontend): 让 live store 通过 API 模块发请求"
```

### Task 3: Final verification

**Files:**
- Verify only

- [ ] **Step 1: Run focused frontend regression**

Run: `node frontend/src/api/live-api.test.mjs`
Expected: PASS

Run: `node frontend/src/api/viewer-api.test.mjs`
Expected: PASS

Run: `node frontend/src/stores/live.test.mjs`
Expected: PASS

Run: `node frontend/src/stores/viewer-workbench.test.mjs`
Expected: PASS

- [ ] **Step 2: Run frontend build**

Run: `npm --prefix frontend run build`
Expected: `vite build` exits with code 0

- [ ] **Step 3: Commit verification-only follow-up if needed**

```bash
git status --short
```

Expected: no unexpected file changes
