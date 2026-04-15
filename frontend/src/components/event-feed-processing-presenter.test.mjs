import assert from "node:assert/strict";

import {
  getCommentProcessingDetails,
  getCommentProcessingTimeline,
} from "./event-feed-processing-presenter.js";

const successEvent = {
  event_type: "comment",
  processing_status: {
    received: true,
    persisted: true,
    memory_extraction_attempted: true,
    memory_saved: true,
    saved_memory_ids: ["mem-1"],
    memory_recall_attempted: true,
    memory_recalled: true,
    recalled_memory_ids: ["mem-9"],
    suggestion_generated: true,
    suggestion_id: "sug-1",
  },
};

assert.deepEqual(getCommentProcessingTimeline(successEvent), [
  { key: "received", state: "success", labelKey: "feed.processing.timeline.received.success" },
  { key: "persisted", state: "success", labelKey: "feed.processing.timeline.persisted.success" },
  {
    key: "memorySaved",
    state: "success",
    labelKey: "feed.processing.timeline.memorySaved.success",
  },
  {
    key: "memoryRecalled",
    state: "success",
    labelKey: "feed.processing.timeline.memoryRecalled.success",
  },
  {
    key: "suggestionGenerated",
    state: "success",
    labelKey: "feed.processing.timeline.suggestionGenerated.success",
  },
]);

assert.deepEqual(getCommentProcessingDetails(successEvent), [
  {
    key: "received",
    state: "success",
    titleKey: "feed.processing.detail.received.title",
    summaryKey: "feed.processing.detail.received.success",
    meta: [],
  },
  {
    key: "persisted",
    state: "success",
    titleKey: "feed.processing.detail.persisted.title",
    summaryKey: "feed.processing.detail.persisted.success",
    meta: [],
  },
  {
    key: "memorySaved",
    state: "success",
    titleKey: "feed.processing.detail.memorySaved.title",
    summaryKey: "feed.processing.detail.memorySaved.success",
    meta: [{ key: "feed.processing.savedMemoryIds", value: "mem-1" }],
  },
  {
    key: "memoryRecalled",
    state: "success",
    titleKey: "feed.processing.detail.memoryRecalled.title",
    summaryKey: "feed.processing.detail.memoryRecalled.success",
    meta: [{ key: "feed.processing.recalledMemoryIds", value: "mem-9" }],
  },
  {
    key: "suggestionGenerated",
    state: "success",
    titleKey: "feed.processing.detail.suggestionGenerated.title",
    summaryKey: "feed.processing.detail.suggestionGenerated.success",
    meta: [{ key: "feed.processing.suggestionId", value: "sug-1" }],
  },
]);

const skippedRecallEvent = {
  event_type: "comment",
  processing_status: {
    received: true,
    persisted: true,
    memory_extraction_attempted: true,
    memory_saved: false,
    saved_memory_ids: [],
    memory_recall_attempted: false,
    memory_recalled: false,
    recalled_memory_ids: [],
    suggestion_generated: false,
  },
};

assert.equal(
  getCommentProcessingTimeline(skippedRecallEvent)[2].labelKey,
  "feed.processing.timeline.memorySaved.neutral",
);
assert.equal(
  getCommentProcessingTimeline(skippedRecallEvent)[3].labelKey,
  "feed.processing.timeline.memoryRecalled.skipped",
);
assert.equal(
  getCommentProcessingDetails(skippedRecallEvent)[2].summaryKey,
  "feed.processing.detail.memorySaved.neutral",
);
assert.equal(
  getCommentProcessingDetails(skippedRecallEvent)[3].summaryKey,
  "feed.processing.detail.memoryRecalled.skipped",
);

assert.deepEqual(
  getCommentProcessingTimeline({ event_type: "gift", processing_status: { persisted: true } }),
  [],
);
assert.deepEqual(
  getCommentProcessingDetails({ event_type: "gift", processing_status: { persisted: true } }),
  [],
);
