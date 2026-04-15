export function getCommentProcessingBadges(event) {
  const status = event?.processing_status;
  if (event?.event_type !== "comment" || !status) {
    return [];
  }

  return [
    status.persisted ? "feed.processing.persisted" : "feed.processing.notPersisted",
    status.memory_saved ? "feed.processing.memorySaved" : "feed.processing.noMemorySaved",
    status.memory_recalled ? "feed.processing.memoryRecalled" : "feed.processing.noMemoryRecalled",
    status.suggestion_generated
      ? "feed.processing.suggestionGenerated"
      : "feed.processing.noSuggestionGenerated",
  ];
}

export function getCommentProcessingDetails(event) {
  const status = event?.processing_status;
  if (event?.event_type !== "comment" || !status) {
    return [];
  }

  const details = [];
  if (status.saved_memory_ids?.length) {
    details.push({
      key: "feed.processing.savedMemoryIds",
      value: status.saved_memory_ids.join(", "),
    });
  }
  if (status.recalled_memory_ids?.length) {
    details.push({
      key: "feed.processing.recalledMemoryIds",
      value: status.recalled_memory_ids.join(", "),
    });
  }
  if (status.suggestion_id) {
    details.push({
      key: "feed.processing.suggestionId",
      value: status.suggestion_id,
    });
  }
  return details;
}
