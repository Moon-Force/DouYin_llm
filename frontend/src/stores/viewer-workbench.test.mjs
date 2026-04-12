import assert from "node:assert/strict";
import { createPinia, setActivePinia } from "pinia";

import { useLiveStore } from "./live.js";

setActivePinia(createPinia());

const baseViewerPayload = {
  room_id: "841354217566",
  viewer_id: "id:viewer-1",
  nickname: "A Ming",
  comment_count: 12,
  gift_event_count: 2,
  memories: [{ memory_id: "m1", memory_text: "likes ramen" }],
  notes: [{ note_id: "n1", content: "regular fan", is_pinned: 1 }],
  recent_comments: [],
  recent_gift_events: [],
  recent_sessions: [],
};

const event = {
  room_id: "841354217566",
  user: { viewer_id: "id:viewer-1", nickname: "A Ming" },
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
    nickname: "A Ming",
  },
);

let requests = [];

global.EventSource = class {
  constructor(url) {
    this.url = url;
  }

  addEventListener() {}

  close() {}
};

function setFetch(handler) {
  requests = [];
  global.fetch = async (url, options = {}) => {
    requests.push({ url, options });
    return handler(url, options);
  };
}

setFetch(async (url, options) => {
  if (url.startsWith("/api/viewer?")) {
    return {
      ok: true,
      async json() {
        return { ...baseViewerPayload };
      },
    };
  }

  throw new Error(`Unexpected request during initial load: ${url} ${options.method || "GET"}`);
});

const store = useLiveStore();
await store.openViewerWorkbench({
  roomId: "841354217566",
  viewerId: "id:viewer-1",
  nickname: "A Ming",
});

assert.equal(store.isViewerWorkbenchOpen, true);
assert.equal(store.viewerWorkbench.viewer.nickname, "A Ming");
assert.equal(store.viewerWorkbench.viewer.memories.length, 1);

store.beginEditingViewerNote({
  note_id: "n1",
  content: "regular fan",
  is_pinned: 1,
});

assert.equal(store.viewerNoteDraft, "regular fan");
assert.equal(store.viewerNotePinned, true);
assert.equal(store.editingViewerNoteId, "n1");

store.toggleViewerNotePinned();
assert.equal(store.viewerNotePinned, false);
store.toggleViewerNotePinned();
assert.equal(store.viewerNotePinned, true);

setFetch(async (url, options) => {
  if (url === "/api/viewer/notes" && options.method === "POST") {
    return {
      ok: true,
      async json() {
        return {
          note_id: "n1",
          room_id: "841354217566",
          viewer_id: "id:viewer-1",
          content: "prefers combo meals",
          author: "host",
          is_pinned: true,
          created_at: 1,
          updated_at: 2,
        };
      },
    };
  }

  if (url.startsWith("/api/viewer?")) {
    return {
      ok: true,
      async json() {
        return {
          ...baseViewerPayload,
          notes: [{ note_id: "n1", content: "prefers combo meals", is_pinned: 1 }],
        };
      },
    };
  }

  throw new Error(`Unexpected request during save: ${url} ${options.method || "GET"}`);
});

store.setViewerNoteDraft("prefers combo meals");
await store.saveActiveViewerNote();

const savePost = requests.find(
  (request) => request.url === "/api/viewer/notes" && request.options.method === "POST",
);
assert.ok(savePost);
assert.deepEqual(JSON.parse(savePost.options.body), {
  room_id: "841354217566",
  viewer_id: "id:viewer-1",
  content: "prefers combo meals",
  is_pinned: true,
  note_id: "n1",
});
assert.equal(store.viewerNoteDraft, "");
assert.equal(store.viewerNotePinned, false);
assert.equal(store.editingViewerNoteId, "");
assert.equal(store.viewerWorkbench.error, "");
assert.equal(
  requests.some((request) => request.url.startsWith("/api/viewer?room_id=841354217566")),
  true,
);

setFetch(async (url, options) => {
  if (url === "/api/viewer/notes" && options.method === "POST") {
    return {
      ok: false,
      statusText: "bad request",
      async json() {
        return { detail: "note save failed" };
      },
    };
  }

  if (url.startsWith("/api/viewer?")) {
    return {
      ok: true,
      async json() {
        return { ...baseViewerPayload };
      },
    };
  }

  throw new Error(`Unexpected request during failed save: ${url} ${options.method || "GET"}`);
});

store.setViewerNoteDraft("this save should fail");
await store.saveActiveViewerNote();

assert.equal(store.viewerWorkbench.error, "note save failed");
assert.equal(
  requests.some((request) => request.url === "/api/viewer/notes" && request.options.method === "POST"),
  true,
);

requests = [];
store.setViewerNoteDraft("   ");
await store.saveActiveViewerNote();
assert.equal(store.viewerWorkbench.error, "Note content is required");
assert.equal(requests.length, 0);

setFetch(async (url, options) => {
  if (url === "/api/viewer/notes" && options.method === "POST") {
    return {
      ok: true,
      async json() {
        return {
          note_id: "n1",
          room_id: "841354217566",
          viewer_id: "id:viewer-1",
          content: "unpinned note",
          author: "host",
          is_pinned: false,
          created_at: 1,
          updated_at: 3,
        };
      },
    };
  }

  if (url.startsWith("/api/viewer?")) {
    return {
      ok: true,
      async json() {
        return {
          ...baseViewerPayload,
          notes: [{ note_id: "n1", content: "unpinned note", is_pinned: 0 }],
        };
      },
    };
  }

  throw new Error(`Unexpected request during unpin save: ${url} ${options.method || "GET"}`);
});

store.beginEditingViewerNote({
  note_id: "n1",
  content: "unpinned note",
  is_pinned: 1,
});
store.toggleViewerNotePinned();
await store.saveActiveViewerNote();

const unpinPost = requests.find(
  (request) => request.url === "/api/viewer/notes" && request.options.method === "POST",
);
assert.ok(unpinPost);
assert.equal(JSON.parse(unpinPost.options.body).is_pinned, false);

setFetch(async (url, options) => {
  if (url === "/api/viewer/notes/n1" && options.method === "DELETE") {
    return {
      ok: true,
      async json() {
        return { deleted: true };
      },
    };
  }

  if (url.startsWith("/api/viewer?")) {
    return {
      ok: true,
      async json() {
        return {
          ...baseViewerPayload,
          notes: [],
        };
      },
    };
  }

  throw new Error(`Unexpected request during delete: ${url} ${options.method || "GET"}`);
});

store.beginEditingViewerNote({
  note_id: "n1",
  content: "regular fan",
  is_pinned: 1,
});

await store.deleteViewerNote("n1");

assert.equal(
  requests.some((request) => request.url === "/api/viewer/notes/n1" && request.options.method === "DELETE"),
  true,
);
assert.equal(store.viewerWorkbench.error, "");
assert.equal(store.viewerNoteDraft, "");
assert.equal(store.viewerNotePinned, false);
assert.equal(store.editingViewerNoteId, "");

store.closeViewerWorkbench();
assert.equal(store.isViewerWorkbenchOpen, false);
assert.equal(store.viewerWorkbench.viewer, null);
assert.equal(store.viewerNoteDraft, "");
assert.equal(store.viewerNotePinned, false);
assert.equal(store.editingViewerNoteId, "");

setFetch(async (url, options) => {
  if (url.startsWith("/api/viewer?")) {
    return {
      ok: true,
      async json() {
        return { ...baseViewerPayload };
      },
    };
  }

  if (url === "/api/room" && options.method === "POST") {
    return {
      ok: true,
      async json() {
        return {
          room_id: "952700000001",
          recent_events: [],
          recent_suggestions: [],
          stats: {
            room_id: "952700000001",
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
        };
      },
    };
  }

  throw new Error(`Unexpected request during room switch: ${url} ${options.method || "GET"}`);
});

await store.openViewerWorkbench({
  roomId: "841354217566",
  viewerId: "id:viewer-1",
  nickname: "A Ming",
});
store.setRoomDraft("952700000001");
await store.switchRoom();

assert.equal(store.isViewerWorkbenchOpen, false);
assert.equal(store.viewerWorkbench.viewer, null);
assert.equal(store.viewerNoteDraft, "");

setFetch(async (url, options) => {
  if (url.startsWith("/api/viewer?")) {
    return {
      ok: true,
      async json() {
        return { ...baseViewerPayload };
      },
    };
  }

  if (url === "/api/room" && options.method === "POST") {
    return {
      ok: false,
      async json() {
        return { detail: "switch failed" };
      },
    };
  }

  if (url.startsWith("/api/bootstrap?")) {
    return {
      ok: true,
      async json() {
        return {
          room_id: "841354217566",
          recent_events: [],
          recent_suggestions: [],
          stats: {
            room_id: "841354217566",
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
        };
      },
    };
  }

  throw new Error(`Unexpected request during failed room switch: ${url} ${options.method || "GET"}`);
});

await store.openViewerWorkbench({
  roomId: "841354217566",
  viewerId: "id:viewer-1",
  nickname: "A Ming",
});
store.beginEditingViewerNote({
  note_id: "n1",
  content: "keep this draft",
  is_pinned: 1,
});
store.setRoomDraft("952700000002");
await store.switchRoom();

assert.equal(store.isViewerWorkbenchOpen, true);
assert.equal(store.viewerWorkbench.viewer?.viewer_id, "id:viewer-1");
assert.equal(store.viewerNoteDraft, "keep this draft");
assert.equal(store.roomError, "switch failed");

setFetch(async (url, options) => {
  if (url.startsWith("/api/viewer?")) {
    return {
      ok: true,
      async json() {
        return {
          ...baseViewerPayload,
          viewer_id: "",
          nickname: "Nickname Only",
        };
      },
    };
  }

  if (url === "/api/viewer/notes" && options.method === "POST") {
    throw new Error("save should not be called for nickname-only viewer");
  }

  throw new Error(`Unexpected request during nickname-only flow: ${url} ${options.method || "GET"}`);
});

await store.openViewerWorkbench({
  roomId: "841354217566",
  viewerId: "",
  nickname: "Nickname Only",
});
store.setViewerNoteDraft("should not save");
await store.saveActiveViewerNote();

assert.equal(store.viewerWorkbench.error, "Viewer id is required to save notes");
