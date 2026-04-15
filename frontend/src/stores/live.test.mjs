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
