import assert from "node:assert/strict";

import {
  getSuggestionConfidenceBand,
  getSuggestionReferencePreview,
  getSuggestionSupportLabel,
} from "./teleprompter-presenter.js";

assert.equal(
  getSuggestionConfidenceBand({ confidence: 0.92 }),
  "teleprompter.confidence.high",
);
assert.equal(
  getSuggestionConfidenceBand({ confidence: 0.72 }),
  "teleprompter.confidence.medium",
);
assert.equal(
  getSuggestionConfidenceBand({ confidence: 0.41 }),
  "teleprompter.confidence.low",
);

assert.equal(
  getSuggestionSupportLabel({ source: "heuristic_fallback", references: [] }),
  "teleprompter.support.fallback",
);
assert.equal(
  getSuggestionSupportLabel({ support_kind: "current_comment", references: [] }),
  "teleprompter.support.currentComment",
);
assert.equal(
  getSuggestionSupportLabel({ source: "model", references: ["likes ramen"] }),
  "teleprompter.support.memory",
);
assert.equal(
  getSuggestionSupportLabel({ source: "model", references: [] }),
  "teleprompter.support.context",
);

assert.deepEqual(
  getSuggestionReferencePreview({
    references: ["likes tonkotsu ramen", "cannot eat spicy food", "from hangzhou"],
  }),
  ["likes tonkotsu ramen", "cannot eat spicy food"],
);
