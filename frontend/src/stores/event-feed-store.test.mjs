import assert from "node:assert/strict";
import { createPinia, setActivePinia } from "pinia";

import { useEventFeedStore } from "./event-feed.js";

setActivePinia(createPinia());

const originalWindow = global.window;

global.window = {
  localStorage: {
    getItem() {
      return null;
    },
    setItem() {},
  },
};

try {
  const store = useEventFeedStore();

  assert.deepEqual([...store.selectedEventTypes], ["comment", "gift", "member"]);

  store.hydrateEventFeed({
    room_id: "room-1",
    recent_events: [
      { event_id: "comment-1", event_type: "comment", room_id: "room-1" },
      { event_id: "gift-1", event_type: "gift", room_id: "room-1" },
      { event_id: "member-1", event_type: "member", room_id: "room-1" },
      { event_id: "follow-1", event_type: "follow", room_id: "room-1" },
    ],
    recent_suggestions: [{ suggestion_id: "s1" }],
    stats: {
      room_id: "room-1",
      total_events: 4,
      comments: 1,
      gifts: 1,
      likes: 0,
      members: 1,
      follows: 1,
    },
  });

  assert.deepEqual(
    store.events.map((event) => event.event_type),
    ["comment", "gift", "member"],
  );
  assert.equal(store.suggestions.length, 1);
  assert.equal(store.stats.total_events, 4);

  store.ingestEvent({ event_id: "comment-2", event_type: "comment", room_id: "room-1" });
  store.ingestEvent({ event_id: "system-1", event_type: "system", room_id: "room-1" });
  store.ingestSuggestion({ suggestion_id: "s2" });
  store.updateStats({ room_id: "room-1", total_events: 5 });

  assert.equal(store.events[0].event_id, "comment-2");
  assert.equal(store.events.some((event) => event.event_type === "system"), false);
  assert.equal(store.suggestions[0].suggestion_id, "s2");
  assert.equal(store.stats.total_events, 5);

  store.toggleEventType("gift");
  assert.deepEqual([...store.selectedEventTypes], ["comment", "member"]);
  assert.deepEqual(
    store.filteredEvents.map((event) => event.event_type),
    ["comment", "comment", "member"],
  );

  store.selectAllEventTypes();
  assert.deepEqual([...store.selectedEventTypes], ["comment", "gift", "member"]);

  store.clearEvents();
  assert.deepEqual(store.events, []);
} finally {
  global.window = originalWindow;
}
