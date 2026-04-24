import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const source = await readFile(new URL("./ViewerWorkbench.vue", import.meta.url), "utf8");

assert.ok(
  source.includes("viewerWorkbench.addNote") && source.includes("emit('open-new-note')"),
  "Viewer workbench should render a top-level note action near the viewer identity block",
);
assert.ok(
  source.includes('v-if="noteEditorOpen"'),
  "Viewer note editor should stay hidden until explicitly opened",
);
assert.ok(
  source.includes("emit('close-note-editor')"),
  "Viewer note editor should provide a cancel/close action",
);
