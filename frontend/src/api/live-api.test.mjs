import assert from "node:assert/strict";

import {
  bootstrapLiveState,
  loadLlmSettingsRequest,
  saveLlmSettingsRequest,
  switchLiveRoom,
} from "./live-api.js";

const originalFetch = global.fetch;

global.fetch = async (url, options = {}) => ({
  ok: true,
  async json() {
    return { url, options };
  },
});

try {
  const bootstrap = await bootstrapLiveState("9527");
  assert.equal(bootstrap.url, "/api/bootstrap?room_id=9527");

  const bootstrapDefault = await bootstrapLiveState("");
  assert.equal(bootstrapDefault.url, "/api/bootstrap");

  const switched = await switchLiveRoom("9528");
  assert.equal(switched.url, "/api/room");
  assert.equal(switched.options.method, "POST");
  assert.deepEqual(JSON.parse(switched.options.body), { room_id: "9528" });

  const llm = await loadLlmSettingsRequest();
  assert.equal(llm.url, "/api/settings/llm");

  const saved = await saveLlmSettingsRequest({
    model: "qwen-plus-latest",
    systemPrompt: "hi",
    embeddingModel: "bge-m3:latest",
    memoryExtractorModel: "qwen3.5:0.8b",
  });
  assert.equal(saved.url, "/api/settings/llm");
  assert.equal(saved.options.method, "PUT");
  assert.deepEqual(JSON.parse(saved.options.body), {
    model: "qwen-plus-latest",
    system_prompt: "hi",
    embedding_model: "bge-m3:latest",
    memory_extractor_model: "qwen3.5:0.8b",
  });
} finally {
  global.fetch = originalFetch;
}
