import assert from "node:assert/strict";

import {
  getSuggestionConfidenceBand,
  getSuggestionReferencePreview,
  getSuggestionSupportLabel,
} from "./teleprompter-presenter.js";
import { translate } from "../i18n.js";

const suggestion = {
  source: "model",
  priority: "high",
  tone: "natural",
  confidence: 0.91,
  references: ["喜欢豚骨拉面", "不能吃太辣", "住在公司附近"],
};

assert.equal(
  translate("zh", getSuggestionConfidenceBand(suggestion)),
  "高置信",
);
assert.equal(
  translate("zh", getSuggestionSupportLabel(suggestion)),
  "依据：历史记忆",
);
assert.deepEqual(
  getSuggestionReferencePreview(suggestion),
  ["喜欢豚骨拉面", "不能吃太辣"],
);

assert.equal(
  translate("en", getSuggestionConfidenceBand({ confidence: 0.3 })),
  "Low confidence",
);
assert.equal(
  translate("en", getSuggestionSupportLabel({ source: "heuristic_fallback", references: [] })),
  "Rule fallback",
);
