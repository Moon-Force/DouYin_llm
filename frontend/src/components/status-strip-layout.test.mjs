import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

const componentPath = fileURLToPath(new URL("./StatusStrip.vue", import.meta.url));
const statusStripSource = readFileSync(componentPath, "utf8");
const eventFeedPath = fileURLToPath(new URL("./EventFeed.vue", import.meta.url));
const eventFeedSource = readFileSync(eventFeedPath, "utf8");

assert.match(
  statusStripSource,
  /xl:grid-cols-\[minmax\(0,1\.4fr\)_minmax\(320px,1fr\)\]/,
);
assert.match(statusStripSource, /md:grid-cols-4/);
assert.match(statusStripSource, /getConnectionBadgePresentation/);
assert.doesNotMatch(statusStripSource, /absolute right-5 top-5/);
assert.doesNotMatch(statusStripSource, /xl:grid-cols-1/);
assert.match(statusStripSource, /"\\u4E2D"/);
assert.match(statusStripSource, /"\\u5DE5\\u5177"/);
assert.match(statusStripSource, /semanticHealth/);
assert.match(statusStripSource, /status\.semantic\.title/);
assert.match(statusStripSource, /status\.semantic\.strictEnabled/);

assert.match(eventFeedSource, /getCommentProcessingTimeline/);
assert.match(eventFeedSource, /processingStepTone/);
assert.match(eventFeedSource, /if \(state === "failed"\)/);
assert.match(eventFeedSource, /border-l border-line\/14 pl-4/);
assert.match(eventFeedSource, /feed\.processing\.hideDetails/);
assert.match(eventFeedSource, /reasonKey/);
assert.match(eventFeedSource, /step\.reason/);
assert.match(eventFeedSource, /metaItem\.valueKey \? t\(metaItem\.valueKey\) : metaItem\.value/);
assert.match(eventFeedSource, /item\.label/);
assert.match(eventFeedSource, /item\.value/);
assert.doesNotMatch(eventFeedSource, /getCommentProcessingBadges/);
