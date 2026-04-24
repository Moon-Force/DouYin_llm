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
            embedding_model: "bge-m3:latest",
            memory_extractor_model: "qwen3.5:0.8b",
            default_embedding_model: "bge-m3:latest",
            default_memory_extractor_model: "qwen3.5:0.8b",
            embedding_model_options: ["bge-m3:latest", "nomic-embed-text:latest"],
            memory_extractor_model_options: ["qwen3.5:0.8b", "gemma4:e2b"],
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
            embedding_model: payload.embedding_model,
            memory_extractor_model: payload.memory_extractor_model,
            default_embedding_model: "bge-m3:latest",
            default_memory_extractor_model: "qwen3.5:0.8b",
            embedding_model_options: ["bge-m3:latest", "nomic-embed-text:latest"],
            memory_extractor_model_options: ["qwen3.5:0.8b", "gemma4:e2b"],
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
assert.equal(store.llmSettingsDraft.embeddingModel, "bge-m3:latest");
assert.equal(store.llmSettingsDraft.memoryExtractorModel, "qwen3.5:0.8b");
assert.deepEqual([...store.llmSettings.embeddingModelOptions], ["bge-m3:latest", "nomic-embed-text:latest"]);
assert.deepEqual([...store.llmSettings.memoryExtractorModelOptions], ["qwen3.5:0.8b", "gemma4:e2b"]);

store.updateLlmModelDraft("qwen-max");
store.updateSystemPromptDraft("custom prompt");
store.updateEmbeddingModelDraft("nomic-embed-text:latest");
store.updateMemoryExtractorModelDraft("gemma4:e2b");
await store.saveLlmSettings();

const putRequest = requests.find(
  (request) => request.url === "/api/settings/llm" && request.options.method === "PUT",
);
assert.ok(putRequest);
assert.deepEqual(JSON.parse(putRequest.options.body), {
  model: "qwen-max",
  system_prompt: "custom prompt",
  embedding_model: "nomic-embed-text:latest",
  memory_extractor_model: "gemma4:e2b",
});
assert.equal(store.llmSettings.model, "qwen-max");
assert.equal(store.llmSettings.systemPrompt, "custom prompt");
assert.equal(store.llmSettings.embeddingModel, "nomic-embed-text:latest");
assert.equal(store.llmSettings.memoryExtractorModel, "gemma4:e2b");

await store.resetLlmSettings();
assert.equal(store.llmSettingsDraft.model, "qwen3.5-flash-2026-02-23");
assert.equal(store.llmSettingsDraft.systemPrompt, "default system prompt");
assert.equal(store.llmSettingsDraft.embeddingModel, "bge-m3:latest");
assert.equal(store.llmSettingsDraft.memoryExtractorModel, "qwen3.5:0.8b");
