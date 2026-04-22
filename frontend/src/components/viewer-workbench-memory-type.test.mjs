import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const source = await readFile(new URL("./ViewerWorkbench.vue", import.meta.url), "utf8");

assert.ok(
  source.includes("<select"),
  "Viewer workbench should use a select element for memory type",
);
assert.ok(
  source.includes("appearance-none") && source.includes("pointer-events-none"),
  "Viewer workbench memory type select should use the styled custom-select presentation",
);
assert.ok(
  source.includes("viewerWorkbench.memoryTypeOptions.fact") &&
    source.includes("viewerWorkbench.memoryTypeOptions.preference") &&
    source.includes("viewerWorkbench.memoryTypeOptions.context") &&
    source.includes("viewerWorkbench.memoryTypeOptions.plan"),
  "Viewer workbench memory type select should render localized labels for the backend-supported options",
);
