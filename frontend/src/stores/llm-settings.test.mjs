import assert from "node:assert/strict";
import { createPinia, setActivePinia } from "pinia";

import { useLiveStore } from "./live.js";

setActivePinia(createPinia());

let requests = [];
global.fetch = async (url, options = {}) => {
  requests.push({ url, options });

  if (url === "/api/settings/llm") {
    if (!options.method || options.method === "GET") {
      return {
        ok: true,
        async json() {
          return {
            model: "qwen3.5-flash-2026-02-23",
            system_prompt: "default system prompt",
            default_model: "qwen3.5-flash-2026-02-23",
            default_system_prompt: "default system prompt",
          };
        },
      };
    }

    if (options.method === "PUT") {
      const payload = JSON.parse(options.body);
      return {
        ok: true,
        async json() {
          return {
            model: payload.model,
            system_prompt: payload.system_prompt || "default system prompt",
            default_model: "qwen3.5-flash-2026-02-23",
            default_system_prompt: "default system prompt",
          };
        },
      };
    }
  }

  throw new Error(`Unexpected request: ${url} ${options.method || "GET"}`);
};

const store = useLiveStore();
await store.openLlmSettings();

assert.equal(store.isLlmSettingsOpen, true);
assert.equal(store.llmSettingsDraft.model, "qwen3.5-flash-2026-02-23");

store.updateLlmModelDraft("qwen-max");
store.updateSystemPromptDraft("custom prompt");
await store.saveLlmSettings();

const putRequest = requests.find(
  (request) => request.url === "/api/settings/llm" && request.options.method === "PUT",
);
assert.ok(putRequest);
assert.deepEqual(JSON.parse(putRequest.options.body), {
  model: "qwen-max",
  system_prompt: "custom prompt",
});
assert.equal(store.llmSettings.model, "qwen-max");
assert.equal(store.llmSettings.systemPrompt, "custom prompt");

await store.resetLlmSettings();
assert.equal(store.llmSettingsDraft.model, "qwen3.5-flash-2026-02-23");
assert.equal(store.llmSettingsDraft.systemPrompt, "default system prompt");
