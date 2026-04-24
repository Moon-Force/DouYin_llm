import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const appSource = await readFile(new URL("./App.vue", import.meta.url), "utf8");
const eventFeedSource = await readFile(
  new URL("./components/EventFeed.vue", import.meta.url),
  "utf8",
);
const teleprompterSource = await readFile(
  new URL("./components/TeleprompterCard.vue", import.meta.url),
  "utf8",
);
const cssSource = await readFile(new URL("./assets/main.css", import.meta.url), "utf8");

assert.ok(
  appSource.includes("flex h-screen") && appSource.includes("overflow-hidden"),
  "App shell should lock the page to the viewport and hide outer overflow",
);
assert.ok(
  eventFeedSource.includes("mt-5 flex-1 min-h-0 overflow-y-auto"),
  "Event feed should scroll inside its own panel instead of stretching the page",
);
assert.ok(
  teleprompterSource.includes("flex min-h-0 flex-col overflow-hidden"),
  "Teleprompter shell should clip overflow within its card",
);
assert.ok(
  teleprompterSource.includes('class="mt-10 min-h-0 flex-1 overflow-y-auto pr-1"'),
  "Teleprompter body should use an internal scroll region for long content",
);
assert.ok(
  cssSource.includes("overflow: hidden;") && cssSource.includes("height: 100%;"),
  "Global shell should disable browser-level scrolling",
);
