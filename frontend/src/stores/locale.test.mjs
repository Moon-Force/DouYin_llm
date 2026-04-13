import assert from "node:assert/strict";
import { createPinia, setActivePinia } from "pinia";

import { translate } from "../i18n.js";
import { useLiveStore } from "./live.js";

setActivePinia(createPinia());

const store = useLiveStore();

assert.equal(store.locale, "zh");
assert.equal(translate("zh", "status.room"), "房间");
assert.equal(store.nextThemeLabel, "切换浅色主题");
assert.equal(
  store.eventFilters.find((filter) => filter.value === "comment")?.label,
  "弹幕",
);

store.toggleLocale();
assert.equal(store.locale, "en");
assert.equal(store.nextThemeLabel, "Switch to light theme");
assert.equal(
  store.eventFilters.find((filter) => filter.value === "comment")?.label,
  "Comment",
);

store.toggleLocale();
assert.equal(store.locale, "zh");

store.setLocale("en");
assert.equal(store.locale, "en");

store.setLocale("something-else");
assert.equal(store.locale, "zh");
