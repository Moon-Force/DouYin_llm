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
  const suggestionState = buildBinaryState(status.suggestion_generated);

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
  const suggestionState = buildBinaryState(status.suggestion_generated);

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
      meta: status.suggestion_id
        ? [{ key: "feed.processing.suggestionId", value: status.suggestion_id }]
        : [],
    },
  ];
}
