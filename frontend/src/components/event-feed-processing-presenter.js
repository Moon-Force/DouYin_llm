function isCommentWithStatus(event) {
  return event?.event_type === "comment" && event?.processing_status;
}

function joinIds(values) {
  return Array.isArray(values) && values.length > 0 ? values.join(", ") : "";
}

function buildMeta(key, values) {
  const joined = joinIds(values);
  return joined ? [{ key, value: joined }] : [];
}

function buildAttemptState(status, successFlag, attemptedFlag) {
  if (status?.[successFlag]) {
    return "success";
  }
  if (status?.[attemptedFlag] === false) {
    return "skipped";
  }
  return "neutral";
}

function buildBinaryState(value) {
  return value ? "success" : "neutral";
}

const suggestionReasonCodes = new Set([
  "semantic_backend_unavailable",
  "llm_failed",
  "rule_skipped",
  "no_generation_needed",
]);

function normalizeSuggestionState(status) {
  const suggestionStatus = status?.suggestion_status;
  if (suggestionStatus === "generated") {
    return "success";
  }
  if (suggestionStatus === "skipped") {
    return "skipped";
  }
  if (suggestionStatus === "failed") {
    return "failed";
  }
  return buildBinaryState(status?.suggestion_generated);
}

function buildSuggestionReasonKey(status) {
  if (typeof status?.suggestion_block_reason !== "string") {
    return "";
  }

  const rawReasonCode = status.suggestion_block_reason.trim();
  if (!rawReasonCode) {
    return "";
  }

  const reasonCode = suggestionReasonCodes.has(rawReasonCode) ? rawReasonCode : "unknown";
  return `feed.processing.reason.${reasonCode}`;
}

function buildSuggestionMeta(status, suggestionState) {
  if (suggestionState === "success") {
    return status.suggestion_id
      ? [{ key: "feed.processing.suggestionId", value: status.suggestion_id }]
      : [];
  }

  const reasonKey = buildSuggestionReasonKey(status);
  if (!reasonKey) {
    return [];
  }

  const meta = [
    {
      key: "feed.processing.suggestionReason",
      valueKey: `${reasonKey}.label`,
    },
  ];

  if (status.suggestion_block_detail) {
    meta.push({
      key: "feed.processing.suggestionDetail",
      value: status.suggestion_block_detail,
    });
  }

  return meta;
}

export function getCommentProcessingTimeline(event) {
  if (!isCommentWithStatus(event)) {
    return [];
  }

  const status = event.processing_status;
  const memorySavedState = buildAttemptState(status, "memory_saved", "memory_extraction_attempted");
  const memoryRecalledState = buildAttemptState(
    status,
    "memory_recalled",
    "memory_recall_attempted",
  );
  const receivedState = buildBinaryState(status.received);
  const persistedState = buildBinaryState(status.persisted);
  const suggestionState = normalizeSuggestionState(status);
  const suggestionReasonKey =
    suggestionState === "success" ? "" : buildSuggestionReasonKey(status);

  return [
    {
      key: "received",
      state: receivedState,
      labelKey: `feed.processing.timeline.received.${receivedState}`,
    },
    {
      key: "persisted",
      state: persistedState,
      labelKey: `feed.processing.timeline.persisted.${persistedState}`,
    },
    {
      key: "memorySaved",
      state: memorySavedState,
      labelKey: `feed.processing.timeline.memorySaved.${memorySavedState}`,
    },
    {
      key: "memoryRecalled",
      state: memoryRecalledState,
      labelKey: `feed.processing.timeline.memoryRecalled.${memoryRecalledState}`,
    },
    {
      key: "suggestionGenerated",
      state: suggestionState,
      labelKey: `feed.processing.timeline.suggestionGenerated.${suggestionState}`,
      ...(suggestionReasonKey ? { reasonKey: suggestionReasonKey } : {}),
    },
  ];
}

export function getCommentProcessingDetails(event) {
  if (!isCommentWithStatus(event)) {
    return [];
  }

  const status = event.processing_status;
  const memorySavedState = buildAttemptState(status, "memory_saved", "memory_extraction_attempted");
  const memoryRecalledState = buildAttemptState(
    status,
    "memory_recalled",
    "memory_recall_attempted",
  );
  const receivedState = buildBinaryState(status.received);
  const persistedState = buildBinaryState(status.persisted);
  const suggestionState = normalizeSuggestionState(status);

  return [
    {
      key: "received",
      state: receivedState,
      titleKey: "feed.processing.detail.received.title",
      summaryKey: `feed.processing.detail.received.${receivedState}`,
      meta: [],
    },
    {
      key: "persisted",
      state: persistedState,
      titleKey: "feed.processing.detail.persisted.title",
      summaryKey: `feed.processing.detail.persisted.${persistedState}`,
      meta: [],
    },
    {
      key: "memorySaved",
      state: memorySavedState,
      titleKey: "feed.processing.detail.memorySaved.title",
      summaryKey: `feed.processing.detail.memorySaved.${memorySavedState}`,
      meta: buildMeta("feed.processing.savedMemoryIds", status.saved_memory_ids),
    },
    {
      key: "memoryRecalled",
      state: memoryRecalledState,
      titleKey: "feed.processing.detail.memoryRecalled.title",
      summaryKey: `feed.processing.detail.memoryRecalled.${memoryRecalledState}`,
      meta: buildMeta("feed.processing.recalledMemoryIds", status.recalled_memory_ids),
    },
    {
      key: "suggestionGenerated",
      state: suggestionState,
      titleKey: "feed.processing.detail.suggestionGenerated.title",
      summaryKey: `feed.processing.detail.suggestionGenerated.${suggestionState}`,
      meta: buildSuggestionMeta(status, suggestionState),
    },
  ];
}
