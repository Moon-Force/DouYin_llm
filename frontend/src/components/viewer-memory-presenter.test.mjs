import assert from "node:assert/strict";

import {
  canReactivateViewerMemory,
  canTogglePinViewerMemory,
  getViewerMemoryBadges,
  getViewerMemoryTimelinePreview,
} from "./viewer-memory-presenter.js";

const manualActivePinned = {
  memory_id: "m1",
  source_kind: "manual",
  status: "active",
  is_pinned: 1,
  correction_reason: "主播补充",
  last_operation: "edited",
};

assert.deepEqual(getViewerMemoryBadges(manualActivePinned), [
  "viewerWorkbench.memorySource.manual",
  "viewerWorkbench.memoryStatus.active",
  "viewerWorkbench.memoryPinned",
  "viewerWorkbench.memoryOperation.edited",
]);

assert.equal(
  getViewerMemoryTimelinePreview(manualActivePinned).labelKey,
  "viewerWorkbench.timeline.edited",
);
assert.equal(
  getViewerMemoryTimelinePreview(manualActivePinned).reason,
  "主播补充",
);
assert.equal(canTogglePinViewerMemory({ status: "active" }), true);
assert.equal(canTogglePinViewerMemory({ status: "invalid" }), false);
assert.equal(canReactivateViewerMemory({ status: "invalid" }), true);
assert.equal(canReactivateViewerMemory({ status: "active" }), false);
