# Ollama Setting Models Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add embedding-model and extractor-model selection to the settings panel, load candidate models from `ollama list` on each settings fetch, and persist only the selected values in SQLite.

**Architecture:** Keep the existing `app_settings` key-value persistence path and extend the current `/api/settings/llm` contract. The backend will execute `ollama list` when loading settings, return the parsed model names as runtime-only options, and continue to persist only user-selected overrides. The frontend will keep the main model as free text, add two select controls for embedding and extractor models, and send the expanded payload back through the same API.

**Tech Stack:** FastAPI, SQLite, Python `subprocess`, Vue 3, Pinia, Node-based frontend tests, Python `unittest`

---

### Task 1: Lock Backend Settings Contract With Tests

**Files:**
- Modify: `tests/test_llm_settings.py`
- Modify: `tests/test_viewer_memory_api.py`

- [ ] **Step 1: Write the failing store persistence test**

```python
payload = store.save_llm_settings("qwen-max", "custom system prompt", "bge-m3:latest", "qwen3.5:0.8b")
self.assertEqual(payload["embedding_model"], "bge-m3:latest")
self.assertEqual(payload["memory_extractor_model"], "qwen3.5:0.8b")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_llm_settings -v`
Expected: FAIL because `save_llm_settings()` does not accept the new parameters and `get_llm_settings()` does not return the new keys.

- [ ] **Step 3: Write the failing API route test for settings load/save**

```python
app_module.long_term_store.get_llm_settings.return_value = {
    "model": "qwen-main",
    "system_prompt": "prompt",
    "default_model": "qwen-main",
    "default_system_prompt": "prompt",
    "embedding_model": "bge-m3:latest",
    "memory_extractor_model": "qwen3.5:0.8b",
    "embedding_model_options": ["bge-m3:latest", "nomic-embed-text:latest"],
    "memory_extractor_model_options": ["qwen3.5:0.8b", "llama3.2:latest"],
}
```

- [ ] **Step 4: Run API tests to verify they fail**

Run: `python -m unittest tests.test_viewer_memory_api -v`
Expected: FAIL because `/api/settings/llm` route does not expose the new fields and the update request model is missing them.

- [ ] **Step 5: Commit**

```bash
git add tests/test_llm_settings.py tests/test_viewer_memory_api.py
git commit -m "test: cover embedding and extractor settings"
```

### Task 2: Implement Backend Persistence And Ollama Discovery

**Files:**
- Modify: `backend/memory/long_term.py`
- Modify: `backend/app.py`

- [ ] **Step 1: Add a failing helper-level test expectation mentally anchored to these keys**

```python
"embedding_model_override"
"memory_extractor_model_override"
```

- [ ] **Step 2: Implement minimal store support**

```python
def get_llm_settings(self, default_model, default_system_prompt, default_embedding_model="", default_memory_extractor_model="", embedding_model_options=None, memory_extractor_model_options=None):
    ...

def save_llm_settings(self, model, system_prompt, embedding_model="", memory_extractor_model=""):
    ...
```

- [ ] **Step 3: Implement runtime `ollama list` parsing in the API layer**

```python
def _list_ollama_models():
    ...
    return ["bge-m3:latest", "qwen3.5:0.8b"]
```

- [ ] **Step 4: Wire GET and PUT `/api/settings/llm` to the expanded payload**

```python
class LlmSettingsUpdateRequest(BaseModel):
    model: str
    system_prompt: str = ""
    embedding_model: str = ""
    memory_extractor_model: str = ""
```

- [ ] **Step 5: Run backend tests to verify they pass**

Run: `python -m unittest tests.test_llm_settings tests.test_viewer_memory_api -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/memory/long_term.py backend/app.py tests/test_llm_settings.py tests/test_viewer_memory_api.py
git commit -m "feat: persist embedding and extractor settings"
```

### Task 3: Lock Frontend API And Store Contract With Tests

**Files:**
- Modify: `frontend/src/api/live-api.test.mjs`
- Modify: `frontend/src/stores/llm-settings.test.mjs`

- [ ] **Step 1: Write the failing request payload test**

```javascript
assert.deepEqual(JSON.parse(saved.options.body), {
  model: "qwen-plus-latest",
  system_prompt: "hi",
  embedding_model: "bge-m3:latest",
  memory_extractor_model: "qwen3.5:0.8b",
});
```

- [ ] **Step 2: Write the failing store hydration assertions**

```javascript
assert.equal(store.llmSettingsDraft.embeddingModel, "bge-m3:latest");
assert.equal(store.llmSettingsDraft.memoryExtractorModel, "qwen3.5:0.8b");
assert.deepEqual(store.llmSettings.embeddingModelOptions, ["bge-m3:latest"]);
```

- [ ] **Step 3: Run frontend tests to verify they fail**

Run: `node frontend/src/api/live-api.test.mjs`
Expected: FAIL because the request body lacks the new keys.

Run: `node frontend/src/stores/llm-settings.test.mjs`
Expected: FAIL because the store state does not include the new fields.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/api/live-api.test.mjs frontend/src/stores/llm-settings.test.mjs
git commit -m "test: cover frontend embedding and extractor settings"
```

### Task 4: Implement Frontend Settings Controls

**Files:**
- Modify: `frontend/src/api/live-api.js`
- Modify: `frontend/src/stores/live.js`
- Modify: `frontend/src/components/LlmSettingsPanel.vue`
- Modify: `frontend/src/i18n.js`

- [ ] **Step 1: Extend the API client**

```javascript
body: JSON.stringify({
  model,
  system_prompt: systemPrompt,
  embedding_model: embeddingModel,
  memory_extractor_model: memoryExtractorModel,
})
```

- [ ] **Step 2: Extend store state and actions**

```javascript
llmSettingsDraft.value = {
  model: payload.model || "",
  systemPrompt: payload.systemPrompt || "",
  embeddingModel: payload.embeddingModel || "",
  memoryExtractorModel: payload.memoryExtractorModel || "",
};
```

- [ ] **Step 3: Add two select controls while keeping the main model as free text**

```vue
<select :value="draft.embeddingModel" @change="emit('update-embedding-model', $event.target.value)">
  <option v-for="option in embeddingModelOptions" :key="option" :value="option">{{ option }}</option>
</select>
```

- [ ] **Step 4: Add labels and hints to i18n**

```javascript
embeddingModel: "Embedding Model",
memoryExtractorModel: "Extractor Model",
ollamaOptionsHint: "Loaded from ollama list on open."
```

- [ ] **Step 5: Run frontend tests and build**

Run: `node frontend/src/api/live-api.test.mjs`
Expected: PASS

Run: `node frontend/src/stores/llm-settings.test.mjs`
Expected: PASS

Run: `npm --prefix frontend run build`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add frontend/src/api/live-api.js frontend/src/stores/live.js frontend/src/components/LlmSettingsPanel.vue frontend/src/i18n.js frontend/src/api/live-api.test.mjs frontend/src/stores/llm-settings.test.mjs
git commit -m "feat: add embedding and extractor model selectors"
```
