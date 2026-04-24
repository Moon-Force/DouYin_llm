import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const source = await readFile(new URL("./EventFeed.vue", import.meta.url), "utf8");

assert.ok(
  source.includes("viewer_notes_preview"),
  "Event feed should render viewer note previews from event metadata",
);
assert.ok(
  source.includes("feed.notes"),
  "Event feed should label the note preview section",
);
