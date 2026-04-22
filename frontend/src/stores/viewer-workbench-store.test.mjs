import assert from "node:assert/strict";
import { createPinia, setActivePinia } from "pinia";

import { useViewerWorkbenchStore } from "./viewer-workbench.js";

setActivePinia(createPinia());

const originalFetch = global.fetch;

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

let requests = [];

function setFetch(handler) {
  requests = [];
  global.fetch = async (url, options = {}) => {
    requests.push({ url, options });
    return handler(url, options);
  };
}

try {
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

  const store = useViewerWorkbenchStore();
  await store.openViewerWorkbench({
    roomId: "841354217566",
    viewerId: "id:viewer-1",
    nickname: "A Ming",
  });

  assert.equal(store.isViewerWorkbenchOpen, true);
  assert.equal(store.viewerWorkbench.viewer.nickname, "A Ming");

  setFetch(async (url, options) => {
    if (url === "/api/viewer/notes" && options.method === "POST") {
      return {
        ok: true,
        async json() {
          return { note_id: "n1" };
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

    throw new Error(`Unexpected request during note save: ${url} ${options.method || "GET"}`);
  });

  store.setViewerNoteDraft("prefers combo meals");
  store.toggleViewerNotePinned();
  await store.saveActiveViewerNote();

  const noteSave = requests.find(
    (request) => request.url === "/api/viewer/notes" && request.options.method === "POST",
  );
  assert.ok(noteSave);
  assert.deepEqual(JSON.parse(noteSave.options.body), {
    room_id: "841354217566",
    viewer_id: "id:viewer-1",
    content: "prefers combo meals",
    is_pinned: true,
  });

  setFetch(async (url, options) => {
    if (url === "/api/viewer/memories" && options.method === "POST") {
      return {
        ok: true,
        async json() {
          return { memory_id: "m2" };
        },
      };
    }

    if (url.startsWith("/api/viewer?")) {
      return {
        ok: true,
        async json() {
          return {
            ...baseViewerPayload,
            memories: [{ memory_id: "m2", memory_text: "likes tonkotsu ramen", is_pinned: 1 }],
            notes: [{ note_id: "n1", content: "prefers combo meals", is_pinned: 1 }],
          };
        },
      };
    }

    throw new Error(`Unexpected request during memory save: ${url} ${options.method || "GET"}`);
  });

  store.setViewerMemoryDraft({
    memoryText: "likes tonkotsu ramen",
    memoryType: "preference",
    isPinned: true,
    correctionReason: "host added",
  });
  await store.saveActiveViewerMemory();

  const memorySave = requests.find(
    (request) => request.url === "/api/viewer/memories" && request.options.method === "POST",
  );
  assert.ok(memorySave);
  assert.deepEqual(JSON.parse(memorySave.options.body), {
    room_id: "841354217566",
    viewer_id: "id:viewer-1",
    memory_text: "likes tonkotsu ramen",
    memory_type: "preference",
    is_pinned: true,
    correction_reason: "host added",
  });

  store.closeViewerWorkbench();
  assert.equal(store.isViewerWorkbenchOpen, false);
  assert.equal(store.viewerWorkbench.viewer, null);
} finally {
  global.fetch = originalFetch;
}
