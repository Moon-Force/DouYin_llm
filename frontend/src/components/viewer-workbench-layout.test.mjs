import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const source = await readFile(new URL("./ViewerWorkbench.vue", import.meta.url), "utf8");

assert.ok(
  source.includes("{{ t(\"common.firstSeen\") }}: {{ formatTimestamp(viewer.first_seen_at) }}"),
  "Viewer workbench should format first_seen_at before rendering",
);
assert.ok(
  source.includes("{{ t(\"common.lastSeen\") }}: {{ formatTimestamp(viewer.last_seen_at) }}"),
  "Viewer workbench should format last_seen_at before rendering",
);
assert.ok(
  source.includes("sessionStart: formatTimestamp(session.started_at || session.last_viewer_event_at)"),
  "Viewer workbench should format recent session time instead of exposing raw session ids",
);
assert.ok(
  source.includes("sessionId: formatTimestamp(session.started_at || session.last_viewer_event_at)"),
  "Viewer workbench should provide a formatted sessionId fallback for old translation templates",
);
