import assert from "node:assert/strict";
import { createPinia, setActivePinia } from "pinia";

import { useLiveStore } from "./live.js";

setActivePinia(createPinia());

const originalFetch = global.fetch;
const originalEventSource = global.EventSource;

const viewerPayload = {
  room_id: "841354217566",
  viewer_id: "id:viewer-1",
  nickname: "A Ming",
  comment_count: 42,
  gift_event_count: 6,
  memories: [
    {
      memory_id: "mem-ramen",
      memory_text: "喜欢豚骨拉面",
      memory_type: "preference",
      source_kind: "manual",
      status: "active",
      is_pinned: 1,
      correction_reason: "主播确认过",
      last_operation: "upgraded",
      last_operation_at: 12,
      confidence: 0.92,
      recall_count: 7,
    },
    {
      memory_id: "mem-spicy",
      memory_text: "不能吃太辣",
      memory_type: "preference",
      source_kind: "auto",
      status: "invalid",
      is_pinned: 0,
      correction_reason: "口味变了",
      last_operation: "invalidated",
      last_operation_at: 11,
      confidence: 0.81,
      recall_count: 3,
    },
  ],
  notes: [{ note_id: "n1", content: "老观众，常聊吃饭", is_pinned: 1 }],
  recent_comments: [{ event_id: "evt-1", content: "今晚还想去吃面" }],
  recent_gift_events: [],
  recent_sessions: [{ session_id: "session-1", comment_count: 5, gift_event_count: 1 }],
};

let requests = [];

global.EventSource = class {
  constructor(url) {
    this.url = url;
  }

  addEventListener() {}

  close() {}
};

global.fetch = async (url, options = {}) => {
  requests.push({ url, options });

  if (url.startsWith("/api/viewer?")) {
    return {
      ok: true,
      async json() {
        return { ...viewerPayload };
      },
    };
  }

  if (url === "/api/viewer/memories/mem-ramen/logs?limit=20") {
    return {
      ok: true,
      async json() {
        return {
          items: [
            { log_id: "l2", operation: "upgraded", reason: "新评论里信息更具体" },
            { log_id: "l1", operation: "created", reason: "" },
          ],
        };
      },
    };
  }

  throw new Error(`Unexpected request: ${url} ${options.method || "GET"}`);
};

try {
  const store = useLiveStore();

  await store.openViewerWorkbench({
    roomId: "841354217566",
    viewerId: "id:viewer-1",
    nickname: "A Ming",
  });

  assert.equal(store.isViewerWorkbenchOpen, true);
  assert.equal(store.viewerWorkbench.viewer.nickname, "A Ming");
  assert.equal(store.viewerWorkbench.viewer.memories.length, 2);
  assert.equal(store.viewerWorkbench.viewer.memories[0].memory_text, "喜欢豚骨拉面");
  assert.equal(store.viewerWorkbench.viewer.memories[1].status, "invalid");
  assert.equal(store.viewerWorkbench.viewer.notes[0].content, "老观众，常聊吃饭");
  assert.equal(store.viewerWorkbench.viewer.recent_comments[0].content, "今晚还想去吃面");

  await store.loadViewerMemoryLogs("mem-ramen");

  assert.equal(store.viewerMemoryLogsById["mem-ramen"].items.length, 2);
  assert.equal(store.viewerMemoryLogsById["mem-ramen"].items[0].operation, "upgraded");
  assert.equal(store.viewerMemoryLogsById["mem-ramen"].items[0].reason, "新评论里信息更具体");
  assert.equal(
    requests.some((request) => request.url.startsWith("/api/viewer?room_id=841354217566")),
    true,
  );
  assert.equal(
    requests.some((request) => request.url === "/api/viewer/memories/mem-ramen/logs?limit=20"),
    true,
  );
} finally {
  global.fetch = originalFetch;
  global.EventSource = originalEventSource;
}
