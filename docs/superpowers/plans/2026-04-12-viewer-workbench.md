# Viewer Workbench Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a right-side viewer workbench that opens when the operator clicks a viewer in the live event feed, showing profile, memories, recent interactions, and editable pinned notes.

**Architecture:** Keep the backend surface area minimal by reusing the existing viewer detail and note APIs in `backend/app.py`. On the frontend, extend the live store with selected-viewer state and CRUD helpers, make `EventFeed` emit viewer selection events, and mount a new `ViewerWorkbench` drawer beside the current teleprompter/feed layout.

**Tech Stack:** FastAPI, Vue 3, Pinia, Vite, Tailwind, node-based smoke tests, Python `unittest`

---

## File Map

- Modify: `H:\DouYin_llm\frontend\src\components\EventFeed.vue`
  Purpose: emit viewer-selection events from feed cards without breaking existing filter/clear controls.
- Modify: `H:\DouYin_llm\frontend\src\stores\live.js`
  Purpose: hold selected-viewer drawer state, load viewer detail, and manage notes CRUD.
- Modify: `H:\DouYin_llm\frontend\src\App.vue`
  Purpose: mount the new workbench component and wire emitted events to the store.
- Create: `H:\DouYin_llm\frontend\src\components\ViewerWorkbench.vue`
  Purpose: render the drawer UI for profile summary, memories, recent history, and editable notes.
- Create: `H:\DouYin_llm\frontend\src\stores\viewer-workbench.test.mjs`
  Purpose: front-end regression coverage for drawer state and note CRUD orchestration.
- Modify: `H:\DouYin_llm\backend\app.py` only if frontend implementation exposes a missing field or malformed response.
  Purpose: keep backend changes minimal and strictly additive.

### Task 1: Add failing store-level tests for the viewer workbench flow

**Files:**
- Create: `H:\DouYin_llm\frontend\src\stores\viewer-workbench.test.mjs`
- Modify: `H:\DouYin_llm\frontend\src\stores\live.js`

- [ ] **Step 1: Write the failing test**

```javascript
import assert from "node:assert/strict";
import { createPinia, setActivePinia } from "pinia";

import { useLiveStore } from "./live.js";

setActivePinia(createPinia());

const requests = [];
global.fetch = async (url, options = {}) => {
  requests.push({ url, options });

  if (url.startsWith("/api/viewer?")) {
    return {
      ok: true,
      async json() {
        return {
          room_id: "841354217566",
          viewer_id: "id:viewer-1",
          nickname: "阿明",
          comment_count: 12,
          gift_event_count: 2,
          memories: [{ memory_id: "m1", memory_text: "喜欢拉面" }],
          notes: [{ note_id: "n1", content: "老粉", is_pinned: 1 }],
          recent_comments: [],
          recent_gift_events: [],
          recent_sessions: [],
        };
      },
    };
  }

  if (url === "/api/viewer/notes" && options.method === "POST") {
    return {
      ok: true,
      async json() {
        return {
          note_id: "n2",
          room_id: "841354217566",
          viewer_id: "id:viewer-1",
          content: "今晚主推套餐敏感",
          author: "主播",
          is_pinned: true,
          created_at: 1,
          updated_at: 2,
        };
      },
    };
  }

  throw new Error(`Unexpected request: ${url}`);
};

const store = useLiveStore();
await store.openViewerWorkbench({
  roomId: "841354217566",
  viewerId: "id:viewer-1",
  nickname: "阿明",
});

assert.equal(store.isViewerWorkbenchOpen, true);
assert.equal(store.viewerWorkbench.viewer.nickname, "阿明");
assert.equal(store.viewerWorkbench.viewer.memories.length, 1);

await store.saveViewerNote({
  roomId: "841354217566",
  viewerId: "id:viewer-1",
  content: "今晚主推套餐敏感",
  isPinned: true,
});

assert.equal(
  requests.some((request) => request.url.startsWith("/api/viewer?room_id=841354217566")),
  true,
);
assert.equal(
  requests.some((request) => request.url === "/api/viewer/notes" && request.options.method === "POST"),
  true,
);
```

- [ ] **Step 2: Run test to verify it fails**

Run: `& 'C:\Program Files\nodejs\node.exe' frontend\src\stores\viewer-workbench.test.mjs`

Expected: FAIL because `openViewerWorkbench`, `saveViewerNote`, and viewer workbench state do not exist yet.

- [ ] **Step 3: Write minimal implementation**

```javascript
const isViewerWorkbenchOpen = ref(false);
const viewerWorkbench = ref({
  viewer: null,
  loading: false,
  error: "",
});

async function openViewerWorkbench({ roomId, viewerId, nickname }) {
  isViewerWorkbenchOpen.value = true;
  viewerWorkbench.value.loading = true;
  const query = new URLSearchParams({ room_id: roomId, viewer_id: viewerId, nickname });
  const response = await fetch(`/api/viewer?${query.toString()}`);
  viewerWorkbench.value.viewer = await response.json();
  viewerWorkbench.value.loading = false;
}

async function saveViewerNote(payload) {
  await fetch("/api/viewer/notes", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  await openViewerWorkbench({
    roomId: payload.roomId,
    viewerId: payload.viewerId,
    nickname: payload.nickname || "",
  });
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `& 'C:\Program Files\nodejs\node.exe' frontend\src\stores\viewer-workbench.test.mjs`

Expected: exits with code `0`.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/stores/live.js frontend/src/stores/viewer-workbench.test.mjs
git commit -m "feat: add viewer workbench store state"
```

### Task 2: Make event feed viewer names selectable

**Files:**
- Modify: `H:\DouYin_llm\frontend\src\components\EventFeed.vue`
- Modify: `H:\DouYin_llm\frontend\src\App.vue`

- [ ] **Step 1: Write the failing test**

Add a smoke assertion to `frontend/src/stores/viewer-workbench.test.mjs` that the selection payload shape is stable:

```javascript
const event = {
  room_id: "841354217566",
  user: { viewer_id: "id:viewer-1", nickname: "阿明" },
};

assert.deepEqual(
  {
    roomId: event.room_id,
    viewerId: event.user.viewer_id,
    nickname: event.user.nickname,
  },
  {
    roomId: "841354217566",
    viewerId: "id:viewer-1",
    nickname: "阿明",
  },
);
```

- [ ] **Step 2: Run test to verify it fails**

Run: `& 'C:\Program Files\nodejs\node.exe' frontend\src\stores\viewer-workbench.test.mjs`

Expected: FAIL after you temporarily wire the test to call a missing helper such as `store.selectViewerFromEvent(event)`.

- [ ] **Step 3: Write minimal implementation**

```vue
const emit = defineEmits([
  "toggle-filter",
  "select-all-filters",
  "clear-events",
  "select-viewer",
]);

function selectViewer(event) {
  const viewerId = event.user?.viewer_id;
  const nickname = event.user?.nickname;
  if (!viewerId && !nickname) {
    return;
  }

  emit("select-viewer", {
    roomId: event.room_id,
    viewerId: viewerId || "",
    nickname: nickname || "",
  });
}
```

And render the name as a button:

```vue
<button
  type="button"
  class="mt-2 text-left text-sm font-medium leading-6 text-paper transition hover:text-accent"
  @click="selectViewer(event)"
>
  {{ event.user.nickname || "未知用户" }}
</button>
```

Wire it in `App.vue`:

```vue
<EventFeed
  ...
  @select-viewer="liveStore.openViewerWorkbench"
/>
```

- [ ] **Step 4: Run test to verify it passes**

Run: `& 'C:\Program Files\nodejs\node.exe' frontend\src\stores\viewer-workbench.test.mjs`

Expected: exits with code `0`.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/EventFeed.vue frontend/src/App.vue frontend/src/stores/viewer-workbench.test.mjs
git commit -m "feat: open viewer workbench from event feed"
```

### Task 3: Build the right-side viewer workbench drawer

**Files:**
- Create: `H:\DouYin_llm\frontend\src\components\ViewerWorkbench.vue`
- Modify: `H:\DouYin_llm\frontend\src\App.vue`
- Modify: `H:\DouYin_llm\frontend\src\stores\live.js`

- [ ] **Step 1: Write the failing test**

Add a drawer-state assertion to `frontend/src/stores/viewer-workbench.test.mjs`:

```javascript
store.closeViewerWorkbench();
assert.equal(store.isViewerWorkbenchOpen, false);
assert.equal(store.viewerWorkbench.viewer, null);
```

Expected failure reason before implementation: `closeViewerWorkbench` missing and no viewer workbench state reset.

- [ ] **Step 2: Run test to verify it fails**

Run: `& 'C:\Program Files\nodejs\node.exe' frontend\src\stores\viewer-workbench.test.mjs`

Expected: FAIL with missing drawer close/reset behavior.

- [ ] **Step 3: Write minimal implementation**

Create `ViewerWorkbench.vue` with this starting structure:

```vue
<script setup>
const props = defineProps({
  open: { type: Boolean, required: true },
  viewer: { type: Object, default: null },
  loading: { type: Boolean, default: false },
  error: { type: String, default: "" },
  noteDraft: { type: String, default: "" },
  notePinned: { type: Boolean, default: false },
  saving: { type: Boolean, default: false },
  editingNoteId: { type: String, default: "" },
});

defineEmits([
  "close",
  "update-note-draft",
  "toggle-note-pinned",
  "save-note",
  "edit-note",
  "delete-note",
]);
</script>

<template>
  <aside
    v-if="open"
    class="fixed inset-y-4 right-4 z-40 w-[420px] rounded-[30px] border border-line/16 bg-panel p-6 shadow-[var(--shadow-elev)]"
  >
    <button type="button" @click="$emit('close')">关闭</button>
    <div v-if="loading">加载中...</div>
    <div v-else-if="error">{{ error }}</div>
    <div v-else-if="viewer">
      <h2>{{ viewer.nickname || "未知观众" }}</h2>
      <p>{{ viewer.viewer_id }}</p>
      <p>评论 {{ viewer.comment_count || 0 }}</p>
      <p>礼物事件 {{ viewer.gift_event_count || 0 }}</p>
      <section>
        <h3>语义记忆</h3>
        <article v-for="memory in viewer.memories || []" :key="memory.memory_id">
          <p>{{ memory.memory_text }}</p>
        </article>
      </section>
      <section>
        <h3>备注</h3>
        <textarea
          :value="noteDraft"
          @input="$emit('update-note-draft', $event.target.value)"
        />
        <button type="button" @click="$emit('toggle-note-pinned')">
          {{ notePinned ? "取消置顶" : "置顶备注" }}
        </button>
        <button type="button" :disabled="saving" @click="$emit('save-note')">
          {{ saving ? "保存中" : "保存备注" }}
        </button>
        <article v-for="note in viewer.notes || []" :key="note.note_id">
          <p>{{ note.content }}</p>
          <button type="button" @click="$emit('edit-note', note)">编辑</button>
          <button type="button" @click="$emit('delete-note', note.note_id)">删除</button>
        </article>
      </section>
    </div>
  </aside>
</template>
```

Mount it in `App.vue`:

```vue
<ViewerWorkbench
  :open="isViewerWorkbenchOpen"
  :viewer="viewerWorkbench.viewer"
  :loading="viewerWorkbench.loading"
  :error="viewerWorkbench.error"
  :note-draft="viewerNoteDraft"
  :note-pinned="viewerNotePinned"
  :saving="isSavingViewerNote"
  :editing-note-id="editingViewerNoteId"
  @close="liveStore.closeViewerWorkbench"
  @update-note-draft="liveStore.setViewerNoteDraft"
  @toggle-note-pinned="liveStore.toggleViewerNotePinned"
  @save-note="liveStore.saveActiveViewerNote"
  @edit-note="liveStore.beginEditingViewerNote"
  @delete-note="liveStore.deleteViewerNote"
/>
```

- [ ] **Step 4: Run test to verify it passes**

Run: `& 'C:\Program Files\nodejs\node.exe' frontend\src\stores\viewer-workbench.test.mjs`

Expected: exits with code `0`.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/ViewerWorkbench.vue frontend/src/App.vue frontend/src/stores/live.js frontend/src/stores/viewer-workbench.test.mjs
git commit -m "feat: add viewer workbench drawer"
```

### Task 4: Add note editing, pinning, and deletion workflow

**Files:**
- Modify: `H:\DouYin_llm\frontend\src\stores\live.js`
- Modify: `H:\DouYin_llm\frontend\src\components\ViewerWorkbench.vue`
- Test: `H:\DouYin_llm\frontend\src\stores\viewer-workbench.test.mjs`

- [ ] **Step 1: Write the failing test**

Extend `frontend/src/stores/viewer-workbench.test.mjs`:

```javascript
await store.beginEditingViewerNote({
  note_id: "n1",
  content: "老粉",
  is_pinned: 1,
});

assert.equal(store.viewerNoteDraft, "老粉");
assert.equal(store.viewerNotePinned, true);
assert.equal(store.editingViewerNoteId, "n1");

global.fetch = async (url, options = {}) => {
  requests.push({ url, options });
  if (url === "/api/viewer/notes/n1" && options.method === "DELETE") {
    return { ok: true, async json() { return { deleted: true }; } };
  }
  ...
};

await store.deleteViewerNote("n1");

assert.equal(
  requests.some((request) => request.url === "/api/viewer/notes/n1" && request.options.method === "DELETE"),
  true,
);
```

- [ ] **Step 2: Run test to verify it fails**

Run: `& 'C:\Program Files\nodejs\node.exe' frontend\src\stores\viewer-workbench.test.mjs`

Expected: FAIL because edit/delete note helpers and note form state do not exist yet.

- [ ] **Step 3: Write minimal implementation**

```javascript
const viewerNoteDraft = ref("");
const viewerNotePinned = ref(false);
const editingViewerNoteId = ref("");
const isSavingViewerNote = ref(false);

function beginEditingViewerNote(note) {
  viewerNoteDraft.value = note.content || "";
  viewerNotePinned.value = Boolean(note.is_pinned);
  editingViewerNoteId.value = note.note_id || "";
}

function resetViewerNoteEditor() {
  viewerNoteDraft.value = "";
  viewerNotePinned.value = false;
  editingViewerNoteId.value = "";
}

async function saveActiveViewerNote() {
  if (!viewerWorkbench.value.viewer) return;
  isSavingViewerNote.value = true;
  await saveViewerNote({
    roomId: viewerWorkbench.value.viewer.room_id,
    viewerId: viewerWorkbench.value.viewer.viewer_id,
    content: viewerNoteDraft.value,
    isPinned: viewerNotePinned.value,
    noteId: editingViewerNoteId.value,
    nickname: viewerWorkbench.value.viewer.nickname || "",
  });
  resetViewerNoteEditor();
  isSavingViewerNote.value = false;
}

async function deleteViewerNote(noteId) {
  await fetch(`/api/viewer/notes/${noteId}`, { method: "DELETE" });
  await openViewerWorkbench({
    roomId: viewerWorkbench.value.viewer.room_id,
    viewerId: viewerWorkbench.value.viewer.viewer_id,
    nickname: viewerWorkbench.value.viewer.nickname || "",
  });
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `& 'C:\Program Files\nodejs\node.exe' frontend\src\stores\viewer-workbench.test.mjs`

Expected: exits with code `0`.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/stores/live.js frontend/src/components/ViewerWorkbench.vue frontend/src/stores/viewer-workbench.test.mjs
git commit -m "feat: add viewer note editing workflow"
```

### Task 5: Final verification and backend gap check

**Files:**
- Modify only if needed: `H:\DouYin_llm\backend\app.py`
- Verify: `H:\DouYin_llm\docs\superpowers\specs\2026-04-12-viewer-workbench-design.md`

- [ ] **Step 1: Re-read the spec and checklist behavior coverage**

Checklist:

```text
[ ] Clicking a viewer in EventFeed opens the drawer
[ ] Drawer shows profile summary
[ ] Drawer shows semantic memories
[ ] Drawer shows recent comments / gifts / sessions
[ ] Drawer supports note create
[ ] Drawer supports note edit
[ ] Drawer supports note pin/unpin
[ ] Drawer supports note delete
[ ] Empty/error/loading states are visible
```

- [ ] **Step 2: Run frontend smoke tests**

Run: `& 'C:\Program Files\nodejs\node.exe' frontend\src\stores\viewer-workbench.test.mjs`

Expected: exit code `0`.

- [ ] **Step 3: Run backend regression tests**

Run: `& 'C:\Users\tao\AppData\Local\Python\pythoncore-3.14-64\python.exe' -m unittest tests.test_agent tests.test_empty_room_bootstrap tests.test_long_term`

Expected: `OK`

- [ ] **Step 4: Start the app and manually verify the drawer**

Run:

```powershell
try { (Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8010/health).Content } catch { $_.Exception.Message }
try { (Invoke-WebRequest -UseBasicParsing http://127.0.0.1:5173/index.html).StatusCode } catch { $_.Exception.Message }
```

Expected:

```text
backend health returns status=ok
frontend returns 200
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/EventFeed.vue frontend/src/components/ViewerWorkbench.vue frontend/src/stores/live.js frontend/src/stores/viewer-workbench.test.mjs frontend/src/App.vue
git commit -m "feat: add viewer workbench"
```
