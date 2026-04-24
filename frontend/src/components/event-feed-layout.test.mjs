import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const appSource = await readFile(new URL("../App.vue", import.meta.url), "utf8");
const eventFeedSource = await readFile(new URL("./EventFeed.vue", import.meta.url), "utf8");

assert.ok(
  appSource.includes("xl:grid-cols-[1.45fr_1.15fr]"),
  "App layout should widen the right-side event feed column",
);
assert.ok(
  appSource.includes("max-w-[1880px]"),
  "App shell should use a wider max width so the page fills more horizontal space",
);
assert.ok(
  eventFeedSource.includes('class="mt-5 flex-1 min-h-0 overflow-y-auto overflow-x-hidden pr-2"'),
  "Event feed scroll region should block horizontal overflow after the panel is widened",
);
assert.ok(
  eventFeedSource.includes('class="flex flex-wrap items-start gap-3"'),
  "Processing timeline should wrap instead of forcing a single row",
);
assert.ok(
  eventFeedSource.includes('class="flex min-w-0 flex-[1_1_140px] items-center gap-2"'),
  "Processing timeline steps should shrink and wrap within the card width",
);
