import assert from "node:assert/strict";

import { createPinia, setActivePinia } from "pinia";

import { useLiveStore } from "./live.js";

setActivePinia(createPinia());

const originalFetch = global.fetch;
const originalEventSource = global.EventSource;

let eventSourceInstance = null;

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

global.fetch = async () => ({
  ok: true,
  async json() {
    return {
      room_id: "room-1",
      recent_events: [
        { event_id: "comment-1", event_type: "comment", room_id: "room-1" },
        { event_id: "gift-1", event_type: "gift", room_id: "room-1" },
        { event_id: "member-1", event_type: "member", room_id: "room-1" },
        { event_id: "follow-1", event_type: "follow", room_id: "room-1" },
        { event_id: "like-1", event_type: "like", room_id: "room-1" },
        { event_id: "system-1", event_type: "system", room_id: "room-1" },
      ],
      recent_suggestions: [],
      stats: {
        room_id: "room-1",
        total_events: 6,
        comments: 1,
        gifts: 1,
        likes: 1,
        members: 1,
        follows: 1,
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
});

global.EventSource = FakeEventSource;

try {
  const store = useLiveStore();

  assert.deepEqual(
    store.eventFilters.map((filter) => filter.value),
    ["comment", "gift", "member"],
  );

  await store.bootstrap("room-1");

  assert.deepEqual(
    store.events.map((event) => event.event_type),
    ["comment", "gift", "member"],
  );
  assert.deepEqual(
    store.filteredEvents.map((event) => event.event_type),
    ["comment", "gift", "member"],
  );

  store.connect("room-1");

  eventSourceInstance.emit("event", {
    event_id: "comment-2",
    event_type: "comment",
    room_id: "room-1",
  });
  eventSourceInstance.emit("event", {
    event_id: "gift-2",
    event_type: "gift",
    room_id: "room-1",
  });
  eventSourceInstance.emit("event", {
    event_id: "member-2",
    event_type: "member",
    room_id: "room-1",
  });
  eventSourceInstance.emit("event", {
    event_id: "follow-2",
    event_type: "follow",
    room_id: "room-1",
  });
  eventSourceInstance.emit("event", {
    event_id: "like-2",
    event_type: "like",
    room_id: "room-1",
  });
  eventSourceInstance.emit("event", {
    event_id: "system-2",
    event_type: "system",
    room_id: "room-1",
  });

  assert.deepEqual(
    store.events.map((event) => event.event_type),
    ["member", "gift", "comment", "comment", "gift", "member"],
  );
} finally {
  global.fetch = originalFetch;
  global.EventSource = originalEventSource;
}
