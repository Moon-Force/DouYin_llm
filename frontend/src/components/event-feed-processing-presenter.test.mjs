import assert from "node:assert/strict";

import {
  getCommentProcessingBadges,
  getCommentProcessingDetails,
} from "./event-feed-processing-presenter.js";

const commentEvent = {
  event_type: "comment",
  processing_status: {
    persisted: true,
    memory_saved: true,
    saved_memory_ids: ["mem-1"],
    memory_recalled: true,
    recalled_memory_ids: ["mem-9"],
    suggestion_generated: true,
    suggestion_id: "sug-1",
  },
};

assert.deepEqual(getCommentProcessingBadges(commentEvent), [
  "feed.processing.persisted",
  "feed.processing.memorySaved",
  "feed.processing.memoryRecalled",
  "feed.processing.suggestionGenerated",
]);

assert.deepEqual(getCommentProcessingDetails(commentEvent), [
  { key: "feed.processing.savedMemoryIds", value: "mem-1" },
  { key: "feed.processing.recalledMemoryIds", value: "mem-9" },
  { key: "feed.processing.suggestionId", value: "sug-1" },
]);

assert.deepEqual(
  getCommentProcessingBadges({
    event_type: "gift",
    processing_status: {
      persisted: true,
      memory_saved: true,
      memory_recalled: true,
      suggestion_generated: true,
    },
  }),
  [],
);
