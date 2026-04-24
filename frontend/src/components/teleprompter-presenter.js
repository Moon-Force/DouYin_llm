export function getSuggestionConfidenceBand(suggestion) {
  const confidence = Number(suggestion?.confidence ?? 0);
  if (confidence >= 0.85) {
    return "teleprompter.confidence.high";
  }
  if (confidence >= 0.65) {
    return "teleprompter.confidence.medium";
  }
  return "teleprompter.confidence.low";
}

export function getSuggestionSupportLabel(suggestion) {
  const supportKind = `${suggestion?.support_kind ?? ""}`.trim().toLowerCase();
  if (supportKind === "memory") {
    return "teleprompter.support.memory";
  }
  if (supportKind === "current_comment") {
    return "teleprompter.support.currentComment";
  }
  if (supportKind === "context") {
    return "teleprompter.support.context";
  }
  const source = `${suggestion?.source ?? ""}`.trim().toLowerCase();
  if (source === "heuristic_fallback") {
    return "teleprompter.support.fallback";
  }
  if (Array.isArray(suggestion?.references) && suggestion.references.length > 0) {
    return "teleprompter.support.memory";
  }
  return "teleprompter.support.context";
}

export function getSuggestionReferencePreview(suggestion, limit = 2) {
  return Array.isArray(suggestion?.references)
    ? suggestion.references.filter(Boolean).slice(0, Math.max(0, limit))
    : [];
}
