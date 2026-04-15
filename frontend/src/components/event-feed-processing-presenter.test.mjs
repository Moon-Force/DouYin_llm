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
    suggestion_status: "generated",
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

const skippedSuggestionEvent = {
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
    suggestion_status: "skipped",
    suggestion_block_reason: "rule_skipped",
    suggestion_block_detail: "Rule gate skipped this turn",
  },
};

assert.equal(
  getCommentProcessingTimeline(skippedSuggestionEvent)[2].labelKey,
  "feed.processing.timeline.memorySaved.neutral",
);
assert.equal(
  getCommentProcessingTimeline(skippedSuggestionEvent)[3].labelKey,
  "feed.processing.timeline.memoryRecalled.skipped",
);
assert.equal(
  getCommentProcessingDetails(skippedSuggestionEvent)[2].summaryKey,
  "feed.processing.detail.memorySaved.neutral",
);
assert.equal(
  getCommentProcessingDetails(skippedSuggestionEvent)[3].summaryKey,
  "feed.processing.detail.memoryRecalled.skipped",
);
assert.deepEqual(getCommentProcessingTimeline(skippedSuggestionEvent)[4], {
  key: "suggestionGenerated",
  state: "skipped",
  labelKey: "feed.processing.timeline.suggestionGenerated.skipped",
  reasonKey: "feed.processing.reason.rule_skipped",
});
assert.deepEqual(getCommentProcessingDetails(skippedSuggestionEvent)[4], {
  key: "suggestionGenerated",
  state: "skipped",
  titleKey: "feed.processing.detail.suggestionGenerated.title",
  summaryKey: "feed.processing.detail.suggestionGenerated.skipped",
  meta: [
    {
      key: "feed.processing.suggestionReason",
      valueKey: "feed.processing.reason.rule_skipped.label",
    },
    {
      key: "feed.processing.suggestionDetail",
      value: "Rule gate skipped this turn",
    },
  ],
});

const failedSuggestionEvent = {
  event_type: "comment",
  processing_status: {
    received: true,
    persisted: true,
    memory_extraction_attempted: true,
    memory_saved: true,
    memory_recall_attempted: true,
    memory_recalled: true,
    suggestion_status: "failed",
    suggestion_block_reason: "llm_failed",
    suggestion_block_detail: "LLM timeout",
  },
};

assert.deepEqual(getCommentProcessingTimeline(failedSuggestionEvent)[4], {
  key: "suggestionGenerated",
  state: "failed",
  labelKey: "feed.processing.timeline.suggestionGenerated.failed",
  reasonKey: "feed.processing.reason.llm_failed",
});
assert.deepEqual(getCommentProcessingDetails(failedSuggestionEvent)[4], {
  key: "suggestionGenerated",
  state: "failed",
  titleKey: "feed.processing.detail.suggestionGenerated.title",
  summaryKey: "feed.processing.detail.suggestionGenerated.failed",
  meta: [
    {
      key: "feed.processing.suggestionReason",
      valueKey: "feed.processing.reason.llm_failed.label",
    },
    {
      key: "feed.processing.suggestionDetail",
      value: "LLM timeout",
    },
  ],
});

const unknownSuggestionReasonEvent = {
  event_type: "comment",
  processing_status: {
    received: true,
    persisted: true,
    memory_extraction_attempted: true,
    memory_saved: true,
    memory_recall_attempted: true,
    memory_recalled: true,
    suggestion_status: "skipped",
    suggestion_block_reason: "not_registered_reason",
  },
};

assert.equal(
  getCommentProcessingTimeline(unknownSuggestionReasonEvent)[4].reasonKey,
  "feed.processing.reason.unknown",
);
assert.equal(
  getCommentProcessingDetails(unknownSuggestionReasonEvent)[4].meta[0].valueKey,
  "feed.processing.reason.unknown.label",
);

const legacySuggestionEvent = {
  event_type: "comment",
  processing_status: {
    received: true,
    persisted: true,
    memory_extraction_attempted: true,
    memory_saved: true,
    memory_recall_attempted: true,
    memory_recalled: true,
    suggestion_generated: false,
  },
};

const legacyTimelineSuggestion = getCommentProcessingTimeline(legacySuggestionEvent)[4];
assert.deepEqual(legacyTimelineSuggestion, {
  key: "suggestionGenerated",
  state: "neutral",
  labelKey: "feed.processing.timeline.suggestionGenerated.neutral",
});
assert.equal("reasonKey" in legacyTimelineSuggestion, false);

const legacyDetailSuggestion = getCommentProcessingDetails(legacySuggestionEvent)[4];
assert.equal(legacyDetailSuggestion.state, "neutral");
assert.equal(legacyDetailSuggestion.summaryKey, "feed.processing.detail.suggestionGenerated.neutral");
assert.deepEqual(legacyDetailSuggestion.meta, []);

const legacySuggestionSuccessEvent = {
  event_type: "comment",
  processing_status: {
    received: true,
    persisted: true,
    memory_extraction_attempted: true,
    memory_saved: true,
    memory_recall_attempted: true,
    memory_recalled: true,
    suggestion_generated: true,
    suggestion_id: "legacy-sug-1",
  },
};

const legacySuccessTimelineSuggestion = getCommentProcessingTimeline(legacySuggestionSuccessEvent)[4];
assert.deepEqual(legacySuccessTimelineSuggestion, {
  key: "suggestionGenerated",
  state: "success",
  labelKey: "feed.processing.timeline.suggestionGenerated.success",
});
assert.equal("reasonKey" in legacySuccessTimelineSuggestion, false);

const legacySuccessDetailSuggestion = getCommentProcessingDetails(legacySuggestionSuccessEvent)[4];
assert.deepEqual(legacySuccessDetailSuggestion, {
  key: "suggestionGenerated",
  state: "success",
  titleKey: "feed.processing.detail.suggestionGenerated.title",
  summaryKey: "feed.processing.detail.suggestionGenerated.success",
  meta: [{ key: "feed.processing.suggestionId", value: "legacy-sug-1" }],
});

const mixedPayloadPrecedenceEvent = {
  event_type: "comment",
  processing_status: {
    received: true,
    persisted: true,
    memory_extraction_attempted: true,
    memory_saved: true,
    memory_recall_attempted: true,
    memory_recalled: true,
    suggestion_status: "failed",
    suggestion_generated: true,
    suggestion_block_reason: "llm_failed",
    suggestion_id: "legacy-sug-2",
  },
};

assert.deepEqual(getCommentProcessingTimeline(mixedPayloadPrecedenceEvent)[4], {
  key: "suggestionGenerated",
  state: "failed",
  labelKey: "feed.processing.timeline.suggestionGenerated.failed",
  reasonKey: "feed.processing.reason.llm_failed",
});
assert.deepEqual(getCommentProcessingDetails(mixedPayloadPrecedenceEvent)[4], {
  key: "suggestionGenerated",
  state: "failed",
  titleKey: "feed.processing.detail.suggestionGenerated.title",
  summaryKey: "feed.processing.detail.suggestionGenerated.failed",
  meta: [
    {
      key: "feed.processing.suggestionReason",
      valueKey: "feed.processing.reason.llm_failed.label",
    },
  ],
});

assert.deepEqual(
  getCommentProcessingTimeline({ event_type: "gift", processing_status: { persisted: true } }),
  [],
);
assert.deepEqual(
  getCommentProcessingDetails({ event_type: "gift", processing_status: { persisted: true } }),
  [],
);
