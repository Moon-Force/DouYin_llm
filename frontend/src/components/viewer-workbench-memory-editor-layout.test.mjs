import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const source = await readFile(new URL("./ViewerWorkbench.vue", import.meta.url), "utf8");

assert.ok(
  source.includes('class="flex items-center justify-between gap-3"') &&
    source.includes("emit('open-new-memory')"),
  "Viewer workbench should render a header action for adding a new memory",
);
assert.ok(
  source.includes("v-if=\"memoryEditorOpen\""),
  "Viewer memory editor form should be hidden until explicitly opened",
);
assert.ok(
  source.includes("emit('close-memory-editor')"),
  "Viewer memory editor should provide a cancel/close action",
);
