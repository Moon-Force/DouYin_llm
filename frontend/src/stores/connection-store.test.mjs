import assert from "node:assert/strict";
import { createPinia, setActivePinia } from "pinia";

import { useConnectionStore } from "./connection.js";

setActivePinia(createPinia());

const originalFetch = global.fetch;
const originalEventSource = global.EventSource;

let eventSourceInstance = null;
let bootstrapFetchUrl = null;
let roomRequestBody = null;
let eventCount = 0;
let suggestionCount = 0;
let statsPayload = null;

class FakeEventSource {
  constructor(url) {
    this.url = url;
    this.listeners = new Map();
    this.closed = false;
    eventSourceInstance = this;
  }

  addEventListener(type, handler) {
    this.listeners.set(type, handler);
  }

  close() {
    this.closed = true;
  }

  emit(type, payload) {
    const handler = this.listeners.get(type);
    if (handler) {
      handler({ data: JSON.stringify(payload) });
    }
  }
}

global.EventSource = FakeEventSource;
global.fetch = async (url, options = {}) => {
  if (url.startsWith("/api/bootstrap")) {
    bootstrapFetchUrl = url;
    return {
      ok: true,
      async json() {
        return {
          room_id: "room-1",
          recent_events: [],
          recent_suggestions: [],
          stats: {
            room_id: "room-1",
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
  }

  if (url === "/api/room") {
    roomRequestBody = JSON.parse(options.body);
    return {
      ok: true,
      async json() {
        return {
          room_id: "room-2",
          recent_events: [],
          recent_suggestions: [],
          stats: {
            room_id: "room-2",
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
          embedding_strict: false,
          semantic_backend_ready: true,
          semantic_backend_reason: "",
        };
      },
    };
  }

  throw new Error(`Unexpected request: ${url} ${options.method || "GET"}`);
};

try {
  const store = useConnectionStore();
  const payload = await store.bootstrap("room-1");

  assert.equal(bootstrapFetchUrl, "/api/bootstrap?room_id=room-1");
  assert.equal(payload.room_id, "room-1");
  assert.equal(store.roomId, "room-1");
  assert.equal(store.semanticHealth.embeddingStrict, true);
  assert.equal(store.semanticHealth.ready, false);

  store.connect("room-1", {
    onEvent() {
      eventCount += 1;
    },
    onSuggestion() {
      suggestionCount += 1;
    },
    onStats(payload) {
      statsPayload = payload;
    },
  });

  assert.equal(store.connectionState, "connecting");
  eventSourceInstance.onopen();
  assert.equal(store.connectionState, "live");

  eventSourceInstance.emit("event", { event_id: "e1" });
  eventSourceInstance.emit("suggestion", { suggestion_id: "s1" });
  eventSourceInstance.emit("stats", { room_id: "room-1", total_events: 1 });

  assert.equal(eventCount, 1);
  assert.equal(suggestionCount, 1);
  assert.equal(statsPayload.total_events, 1);

  const switched = await store.switchRoom("room-2");
  assert.equal(roomRequestBody.room_id, "room-2");
  assert.equal(switched.room_id, "room-2");
  assert.equal(store.roomId, "room-2");
  assert.equal(store.connectionState, "loading_room_memory");
} finally {
  global.fetch = originalFetch;
  global.EventSource = originalEventSource;
}
