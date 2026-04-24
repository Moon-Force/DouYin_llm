import assert from "node:assert/strict";

import { getConnectionBadgePresentation } from "./status-strip-presenter.js";

const expectBadge = (connectionState, expected) => {
  assert.deepEqual(getConnectionBadgePresentation(connectionState), expected);
};

expectBadge("idle", {
  tone: "danger",
  labelKey: "status.connectionState.idle",
  icon: "dot",
});

expectBadge("connecting", {
  tone: "warning",
  labelKey: "status.connectionState.connecting",
  icon: "pulse",
});

expectBadge("reconnecting", {
  tone: "danger",
  labelKey: "status.connectionState.reconnecting",
  icon: "dot",
});

expectBadge("switching", {
  tone: "warning",
  labelKey: "status.connectionState.switching",
  icon: "pulse",
});

expectBadge("loading_room_memory", {
  tone: "warning",
  labelKey: "status.connectionState.loadingRoomMemory",
  icon: "pulse",
});

expectBadge("live", {
  tone: "success",
  labelKey: "status.connectionState.live",
  icon: "check",
});

expectBadge("unknown", {
  tone: "danger",
  labelKey: "status.connectionState.idle",
  icon: "dot",
});

const mutatedIdleBadge = getConnectionBadgePresentation("idle");
mutatedIdleBadge.tone = "mutated-tone";
mutatedIdleBadge.labelKey = "status.connectionState.mutated";

assert.equal(getConnectionBadgePresentation("idle").tone, "danger");
