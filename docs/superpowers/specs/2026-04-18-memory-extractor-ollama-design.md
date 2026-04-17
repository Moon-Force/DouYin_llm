# Memory Extractor Ollama Design

## Goal

Replace the current local GGUF direct runtime path for viewer memory extraction with an Ollama-backed OpenAI-compatible HTTP client.

Keep the scope narrow:

- Change only the viewer memory extraction LLM path
- Keep prompt suggestion generation unchanged
- Keep embedding configuration unchanged
- Remove code, config, docs, and tests that only exist for the abandoned `llama-cpp-python` local runtime approach

## Why

The current local runtime path depends on `llama-cpp-python`, local GGUF loading, and Windows-native build tooling. That path has proven fragile in the current environment and is not a good default for ordinary users.

Ollama already fits the project's existing integration style better:

- it exposes an OpenAI-compatible HTTP API
- it separates model serving from the app process
- it avoids in-app native build/runtime complexity
- it is easier to explain operationally: install Ollama, pull a model, point the app at `127.0.0.1:11434`

## Current State

Today the memory extraction pipeline looks like this:

1. `backend.app.ensure_runtime()` decides whether to enable LLM-backed extraction
2. If enabled, it creates `LocalMemoryExtractionModel`
3. `LLMBackedViewerMemoryExtractor` asks that runtime for JSON output
4. `ViewerMemoryExtractor` falls back to rules if the LLM path fails
5. Extracted memories are persisted and synced into vector storage

The unstable part is step 2. The protocol layer and fallback behavior are still useful and should stay.

## Recommended Approach

Use a dedicated Ollama/OpenAI-compatible client for memory extraction and keep the existing protocol and fallback layers.

This means:

- keep `LLMBackedViewerMemoryExtractor` as the protocol/validation layer
- replace the local runtime dependency with a thin HTTP client
- keep `ViewerMemoryExtractor` fallback behavior unchanged
- wire `ensure_runtime()` to instantiate the HTTP client instead of the local GGUF runtime

## Alternatives Considered

### 1. Dedicated memory extractor HTTP config

Add a separate base URL and model just for viewer memory extraction.

Pros:

- memory extraction stays independently tunable
- suggestion generation remains untouched
- future model swaps are easy

Cons:

- adds a few more env vars

Recommendation: yes

### 2. Reuse the suggestion LLM config

Use `LLM_BASE_URL` and `LLM_MODEL` directly for memory extraction.

Pros:

- fewer settings

Cons:

- couples two different workloads
- makes optimization harder later
- increases risk of accidental behavior changes

Recommendation: no

### 3. General shared OpenAI-compatible client refactor

Refactor both suggestion generation and memory extraction to a shared transport abstraction.

Pros:

- cleaner long-term architecture

Cons:

- larger change surface
- not aligned with the current "restore a reliable memory extraction path" goal

Recommendation: not in this change

## Configuration Design

Keep:

- `MEMORY_EXTRACTOR_ENABLED`
- `MEMORY_EXTRACTOR_MODE`
- `MEMORY_EXTRACTOR_TIMEOUT_SECONDS`
- `MEMORY_EXTRACTOR_MAX_TOKENS`

Add:

- `MEMORY_EXTRACTOR_BASE_URL`
- `MEMORY_EXTRACTOR_MODEL`
- `MEMORY_EXTRACTOR_API_KEY`

Recommended defaults:

- `MEMORY_EXTRACTOR_MODE=ollama`
- `MEMORY_EXTRACTOR_BASE_URL=http://127.0.0.1:11434/v1`
- `MEMORY_EXTRACTOR_API_KEY=` (blank by default)

Remove obsolete direct-runtime settings:

- `MEMORY_EXTRACTOR_MODEL_PATH`
- `MEMORY_EXTRACTOR_MODEL_URL`
- `MEMORY_EXTRACTOR_MODEL_FILENAME`
- `MEMORY_EXTRACTOR_CONTEXT_SIZE`
- `MEMORY_EXTRACTOR_THREADS`

## Code Changes

### 1. Config layer

Update `backend/config.py` so memory extraction config describes an HTTP-served model instead of a local file-backed runtime.

`Settings` should expose:

- `memory_extractor_enabled`
- `memory_extractor_mode`
- `memory_extractor_base_url`
- `memory_extractor_model`
- `memory_extractor_api_key`
- `memory_extractor_timeout_seconds`
- `memory_extractor_max_tokens`

Directory creation for local memory extractor model storage should be removed from `ensure_dirs()`.

### 2. Runtime client

Delete the local runtime file-backed implementation in `backend/services/local_memory_model.py`.

Replace it with a thin HTTP client, for example `backend/services/memory_extractor_client.py`, that:

- sends a `POST` request to `<base_url>/chat/completions`
- uses OpenAI-compatible request shape
- passes `model`, `messages`, and `max_tokens`
- returns the assistant message text

The client should stay intentionally small. It is transport only, not business logic.

### 3. Memory extraction protocol layer

Keep `backend/services/llm_memory_extractor.py` responsible for:

- building the extraction system prompt
- building the user payload
- parsing returned JSON
- validating `should_extract`, `temporal_scope`, `polarity`, `certainty`, and `memory_type`

Its constructor dependency changes from a local runtime object to an HTTP client object that still exposes one text-returning inference method.

### 4. Application wiring

Update `backend/app.py` so `ensure_runtime()` does this when memory extraction is enabled:

1. instantiate the HTTP client
2. instantiate `LLMBackedViewerMemoryExtractor`
3. instantiate `ViewerMemoryExtractor` with that LLM extractor

Fallback to rules-only extraction remains unchanged when memory extraction is disabled.

### 5. Requirements

Remove `llama-cpp-python` from `requirements.txt`.

No new dependency should be required for the Ollama memory extraction client because the codebase already uses standard-library HTTP for OpenAI-compatible calls elsewhere.

## Documentation Changes

Update:

- `.env.example`
- `README.md`
- the local-memory-extractor design spec that currently describes the abandoned GGUF runtime path

Docs should describe the new operator workflow:

1. install/run Ollama
2. pull or create the model in Ollama
3. set `MEMORY_EXTRACTOR_ENABLED=true`
4. set `MEMORY_EXTRACTOR_BASE_URL`
5. set `MEMORY_EXTRACTOR_MODEL`

Docs should also explicitly state that the previous in-process GGUF path has been removed.

## Testing Plan

### Keep

- protocol validation tests in `tests/test_llm_memory_extractor.py`
- end-to-end wiring tests in `tests/test_comment_processing_status.py`

### Remove or replace

- tests that only verify local file-backed runtime resolution or `llama_cpp` import behavior

### Add

Tests for the new HTTP memory extraction client covering:

- request payload shape
- auth header behavior when API key is present
- timeout propagation
- basic response parsing

### Regression expectations

The following behavior must remain true after the change:

- non-comment events are ignored by memory extraction
- malformed LLM output does not crash the app
- LLM failure falls back to rule-based extraction
- extracted memories are still persisted and synced into vector storage

## Error Handling

If the Ollama endpoint is unreachable or returns malformed output:

- the LLM extractor should fail cleanly
- `ViewerMemoryExtractor` should log the failure
- rule fallback should still execute

This preserves the current degradation path and keeps the app usable even when the memory extraction model is unavailable.

## Non-Goals

This change does not:

- refactor suggestion generation onto a shared client abstraction
- change semantic embedding behavior
- redesign rule-based extraction heuristics
- implement model management inside the app

## Rollout Notes

After this change, users who previously placed GGUF files under `model/memory_extractor/` should no longer expect the app to load them directly.

If they want to keep using the same underlying model family, they should expose it through Ollama and point `MEMORY_EXTRACTOR_MODEL` at the Ollama model name instead.
