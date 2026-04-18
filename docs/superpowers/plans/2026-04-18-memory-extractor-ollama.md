# Memory Extractor Ollama Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move viewer memory extraction from the abandoned in-process GGUF runtime path to an Ollama-backed OpenAI-compatible HTTP client, while preserving rule fallback and removing obsolete local-runtime code/config/docs.

**Architecture:** Keep `backend/services/llm_memory_extractor.py` as the protocol and validation layer, introduce a small HTTP transport for memory extraction, and rewire `backend/app.py` to instantiate that client instead of the local GGUF runtime. Remove the `llama-cpp-python` file-backed runtime, its config surface, and its tests, but leave suggestion generation and embedding behavior unchanged.

**Tech Stack:** Python 3, FastAPI backend, standard-library `urllib.request`, Ollama OpenAI-compatible `/v1/chat/completions`, `unittest`

---

## File Structure

### Files to Create

- `backend/services/memory_extractor_client.py`
- `tests/test_memory_extractor_client.py`

### Files to Modify

- `backend/config.py`
- `backend/app.py`
- `backend/services/llm_memory_extractor.py`
- `tests/test_comment_processing_status.py`
- `requirements.txt`
- `.env.example`
- `README.md`
- `docs/superpowers/specs/2026-04-17-local-memory-extractor-design.md`

### Files to Delete

- `backend/services/local_memory_model.py`
- `tests/test_local_memory_model.py`

## Task 1: Replace Local Runtime Config With Ollama Config

**Files:**
- Modify: `backend/config.py`
- Modify: `.env.example`
- Test: `tests/test_comment_processing_status.py`

- [ ] **Step 1: Write the failing config test**

Add a new test case in `tests/test_comment_processing_status.py` that asserts `backend.app.ensure_runtime()` wires the memory extractor using an HTTP client instead of `LocalMemoryExtractionModel`.

```python
    def test_ensure_runtime_wires_ollama_memory_extractor_when_enabled(self):
        original_settings = app_module.settings
        original_broker = app_module.broker
        original_session_memory = app_module.session_memory
        original_long_term_store = app_module.long_term_store
        original_embedding_service = app_module.embedding_service
        original_vector_memory = app_module.vector_memory
        original_agent = app_module.agent
        original_memory_extractor = app_module.memory_extractor
        original_collector = app_module.collector
        try:
            app_module.settings = SimpleNamespace(
                ensure_dirs=MagicMock(),
                redis_url="redis://localhost:6379/0",
                session_ttl_seconds=3600,
                database_path="data/live_prompter.db",
                chroma_dir="data/chroma",
                memory_extractor_enabled=True,
                memory_extractor_mode="ollama",
                memory_extractor_base_url="http://127.0.0.1:11434/v1",
                memory_extractor_model="qwen2.5:3b",
                memory_extractor_api_key="",
                memory_extractor_timeout_seconds=30.0,
                memory_extractor_max_tokens=512,
            )
            app_module.broker = None
            app_module.session_memory = None
            app_module.long_term_store = None
            app_module.embedding_service = None
            app_module.vector_memory = None
            app_module.agent = None
            app_module.memory_extractor = None
            app_module.collector = None

            with patch("backend.app._should_force_memory_rebuild", return_value=False), patch(
                "backend.app.EventBroker", return_value=MagicMock()
            ), patch(
                "backend.app.SessionMemory", return_value=MagicMock()
            ), patch(
                "backend.app.LongTermStore"
            ) as long_term_store_cls, patch(
                "backend.app.EmbeddingService", return_value=MagicMock()
            ), patch(
                "backend.app.VectorMemory", return_value=MagicMock()
            ), patch(
                "backend.app.LivePromptAgent", return_value=MagicMock()
            ), patch(
                "backend.app.DouyinCollector", return_value=MagicMock()
            ), patch(
                "backend.app.MemoryExtractorClient"
            ) as memory_client_cls, patch(
                "backend.app.LLMBackedViewerMemoryExtractor"
            ) as llm_extractor_cls, patch(
                "backend.app.ViewerMemoryExtractor", return_value=MagicMock()
            ) as composite_cls:
                long_term_store_instance = MagicMock()
                long_term_store_instance.list_all_viewer_memories.return_value = []
                long_term_store_cls.return_value = long_term_store_instance

                app_module.ensure_runtime()

                memory_client_cls.assert_called_once_with(app_module.settings)
                llm_extractor_cls.assert_called_once_with(app_module.settings, memory_client_cls.return_value)
                composite_cls.assert_called_once_with(
                    settings=app_module.settings,
                    llm_extractor=llm_extractor_cls.return_value,
                )
        finally:
            app_module.settings = original_settings
            app_module.broker = original_broker
            app_module.session_memory = original_session_memory
            app_module.long_term_store = original_long_term_store
            app_module.embedding_service = original_embedding_service
            app_module.vector_memory = original_vector_memory
            app_module.agent = original_agent
            app_module.memory_extractor = original_memory_extractor
            app_module.collector = original_collector
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
python -m unittest tests.test_comment_processing_status.CommentProcessingStatusTests.test_ensure_runtime_wires_ollama_memory_extractor_when_enabled
```

Expected: FAIL with an import or patch error because `MemoryExtractorClient` does not exist yet and `backend.app` still references `LocalMemoryExtractionModel`.

- [ ] **Step 3: Update config defaults and remove obsolete local-runtime settings**

Edit `backend/config.py` so `Settings` exposes Ollama/OpenAI-compatible memory extractor settings and no longer exposes local file-backed runtime settings.

```python
    memory_extractor_enabled: bool = field(default_factory=lambda: _env_bool("MEMORY_EXTRACTOR_ENABLED", False))
    memory_extractor_mode: str = field(default_factory=lambda: os.getenv("MEMORY_EXTRACTOR_MODE", "ollama").strip().lower())
    memory_extractor_base_url: str = field(
        default_factory=lambda: os.getenv("MEMORY_EXTRACTOR_BASE_URL", "http://127.0.0.1:11434/v1").strip()
    )
    memory_extractor_model: str = field(default_factory=lambda: os.getenv("MEMORY_EXTRACTOR_MODEL", "").strip())
    memory_extractor_api_key: str = field(default_factory=lambda: os.getenv("MEMORY_EXTRACTOR_API_KEY", "").strip())
    memory_extractor_max_tokens: int = field(default_factory=lambda: _env_int("MEMORY_EXTRACTOR_MAX_TOKENS", 512))
    memory_extractor_timeout_seconds: float = field(
        default_factory=lambda: _env_float("MEMORY_EXTRACTOR_TIMEOUT_SECONDS", 30.0)
    )
```

Also remove the local memory extractor model directory creation from `ensure_dirs()`:

```python
    def ensure_dirs(self):
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self.chroma_dir.mkdir(parents=True, exist_ok=True)
```

Update `.env.example` to replace the old local runtime block with:

```env
# Memory Extractor
# Uses an Ollama or other OpenAI-compatible chat endpoint.
MEMORY_EXTRACTOR_ENABLED=false
MEMORY_EXTRACTOR_MODE=ollama
MEMORY_EXTRACTOR_BASE_URL=http://127.0.0.1:11434/v1
MEMORY_EXTRACTOR_MODEL=
MEMORY_EXTRACTOR_API_KEY=
MEMORY_EXTRACTOR_MAX_TOKENS=512
MEMORY_EXTRACTOR_TIMEOUT_SECONDS=30
```

- [ ] **Step 4: Run the targeted config wiring test**

Run:

```powershell
python -m unittest tests.test_comment_processing_status.CommentProcessingStatusTests.test_ensure_runtime_wires_ollama_memory_extractor_when_enabled
```

Expected: still FAIL, but now only because the new runtime client and app wiring are not implemented yet.

- [ ] **Step 5: Commit the config-only checkpoint**

```bash
git add backend/config.py .env.example tests/test_comment_processing_status.py
git commit -m "refactor: prepare memory extractor ollama config"
```

## Task 2: Add Ollama Memory Extractor Client

**Files:**
- Create: `backend/services/memory_extractor_client.py`
- Test: `tests/test_memory_extractor_client.py`

- [ ] **Step 1: Write the failing client tests**

Create `tests/test_memory_extractor_client.py` with transport-focused tests.

```python
import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from backend.services.memory_extractor_client import MemoryExtractorClient


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def read(self):
        return json.dumps(self._payload, ensure_ascii=False).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class MemoryExtractorClientTests(unittest.TestCase):
    def make_settings(self):
        return SimpleNamespace(
            memory_extractor_base_url="http://127.0.0.1:11434/v1",
            memory_extractor_model="qwen2.5:3b",
            memory_extractor_api_key="",
            memory_extractor_timeout_seconds=12.5,
            memory_extractor_max_tokens=256,
        )

    def test_infer_json_posts_openai_compatible_payload(self):
        client = MemoryExtractorClient(self.make_settings())
        captured = {}

        def fake_urlopen(request, timeout):
            captured["url"] = request.full_url
            captured["timeout"] = timeout
            captured["headers"] = dict(request.header_items())
            captured["body"] = json.loads(request.data.decode("utf-8"))
            return FakeResponse(
                {
                    "choices": [
                        {"message": {"content": "{\"should_extract\": true}"}}
                    ]
                }
            )

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            result = client.infer_json("sys", "{\"event\": 1}")

        self.assertEqual(result, "{\"should_extract\": true}")
        self.assertEqual(captured["url"], "http://127.0.0.1:11434/v1/chat/completions")
        self.assertEqual(captured["timeout"], 12.5)
        self.assertEqual(captured["body"]["model"], "qwen2.5:3b")
        self.assertEqual(captured["body"]["max_tokens"], 256)
        self.assertEqual(captured["body"]["messages"][0]["content"], "sys")
        self.assertEqual(captured["body"]["messages"][1]["content"], "{\"event\": 1}")

    def test_infer_json_adds_authorization_header_when_api_key_present(self):
        settings = self.make_settings()
        settings.memory_extractor_api_key = "secret"
        client = MemoryExtractorClient(settings)
        captured = {}

        def fake_urlopen(request, timeout):
            captured["headers"] = dict(request.header_items())
            return FakeResponse(
                {"choices": [{"message": {"content": "{\"ok\": true}"}}]}
            )

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            client.infer_json("sys", "user")

        self.assertEqual(captured["headers"]["Authorization"], "Bearer secret")
```

- [ ] **Step 2: Run client tests to verify they fail**

Run:

```powershell
python -m unittest tests.test_memory_extractor_client
```

Expected: FAIL because `backend/services/memory_extractor_client.py` does not exist yet.

- [ ] **Step 3: Implement the thin HTTP client**

Create `backend/services/memory_extractor_client.py`:

```python
"""OpenAI-compatible HTTP client for viewer memory extraction."""

import json
import urllib.request


class MemoryExtractorClient:
    def __init__(self, settings):
        self._settings = settings

    def infer_json(self, system_prompt: str, user_prompt: str) -> str:
        headers = {"Content-Type": "application/json"}
        if self._settings.memory_extractor_api_key:
            headers["Authorization"] = f"Bearer {self._settings.memory_extractor_api_key}"

        request = urllib.request.Request(
            f"{self._settings.memory_extractor_base_url.rstrip('/')}/chat/completions",
            data=json.dumps(
                {
                    "model": self._settings.memory_extractor_model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "max_tokens": self._settings.memory_extractor_max_tokens,
                    "temperature": 0,
                },
                ensure_ascii=False,
            ).encode("utf-8"),
            headers=headers,
            method="POST",
        )

        with urllib.request.urlopen(request, timeout=self._settings.memory_extractor_timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8"))
        return payload["choices"][0]["message"]["content"]
```

- [ ] **Step 4: Run the client tests**

Run:

```powershell
python -m unittest tests.test_memory_extractor_client
```

Expected: PASS

- [ ] **Step 5: Commit the transport layer**

```bash
git add backend/services/memory_extractor_client.py tests/test_memory_extractor_client.py
git commit -m "feat: add ollama memory extractor client"
```

## Task 3: Rewire Memory Extractor Runtime and Remove Local Runtime

**Files:**
- Modify: `backend/app.py`
- Delete: `backend/services/local_memory_model.py`
- Modify: `tests/test_comment_processing_status.py`

- [ ] **Step 1: Write the failing runtime cleanup test**

Add a second assertion to the existing disabled-path test to make sure the app no longer imports or wires `LocalMemoryExtractionModel`.

```python
                local_model_cls.assert_not_called()
                llm_extractor_cls.assert_not_called()
                composite_cls.assert_called_once_with(settings=app_module.settings)
```

Then update the enabled-path test from Task 1 to patch `MemoryExtractorClient` instead of `LocalMemoryExtractionModel`.

- [ ] **Step 2: Run the runtime wiring tests to verify current failure**

Run:

```powershell
python -m unittest tests.test_comment_processing_status
```

Expected: FAIL because `backend.app` still imports and instantiates `LocalMemoryExtractionModel`.

- [ ] **Step 3: Update app wiring and remove the local runtime**

Modify `backend/app.py` imports and `ensure_runtime()`:

```python
from backend.services.llm_memory_extractor import LLMBackedViewerMemoryExtractor
from backend.services.memory_extractor import ViewerMemoryExtractor
from backend.services.memory_extractor_client import MemoryExtractorClient
```

```python
    if memory_extractor is None:
        if getattr(settings, "memory_extractor_enabled", False):
            memory_client = MemoryExtractorClient(settings)
            llm_memory_extractor = LLMBackedViewerMemoryExtractor(settings, memory_client)
            memory_extractor = ViewerMemoryExtractor(settings=settings, llm_extractor=llm_memory_extractor)
        else:
            memory_extractor = ViewerMemoryExtractor(settings=settings)
```

Delete `backend/services/local_memory_model.py`.

- [ ] **Step 4: Run the wiring tests**

Run:

```powershell
python -m unittest tests.test_comment_processing_status
```

Expected: PASS

- [ ] **Step 5: Commit the runtime rewire**

```bash
git add backend/app.py tests/test_comment_processing_status.py
git rm backend/services/local_memory_model.py
git commit -m "refactor: switch memory extractor runtime to ollama client"
```

## Task 4: Remove Obsolete Local Runtime Tests and Dependency

**Files:**
- Delete: `tests/test_local_memory_model.py`
- Modify: `requirements.txt`
- Test: `tests/test_llm_memory_extractor.py`
- Test: `tests/test_memory_extractor_client.py`
- Test: `tests/test_comment_processing_status.py`

- [ ] **Step 1: Write the failing dependency expectation check**

Add this test near the config/doc-facing tests in `tests/test_memory_extractor_client.py`:

```python
class RequirementsCleanupTests(unittest.TestCase):
    def test_requirements_no_longer_include_llama_cpp_python(self):
        with open("requirements.txt", "r", encoding="utf-8") as handle:
            requirements = handle.read()
        self.assertNotIn("llama-cpp-python", requirements)
```

- [ ] **Step 2: Run the targeted cleanup tests to verify failure**

Run:

```powershell
python -m unittest tests.test_memory_extractor_client.RequirementsCleanupTests
```

Expected: FAIL because `requirements.txt` still contains `llama-cpp-python`.

- [ ] **Step 3: Remove the dependency and local runtime test file**

Update `requirements.txt` to remove this line:

```text
llama-cpp-python>=0.3.0
```

Delete `tests/test_local_memory_model.py`.

- [ ] **Step 4: Run the backend test suite that should remain**

Run:

```powershell
python -m unittest tests.test_llm_memory_extractor tests.test_memory_extractor_client tests.test_comment_processing_status
```

Expected: PASS

- [ ] **Step 5: Commit the cleanup**

```bash
git add requirements.txt tests/test_memory_extractor_client.py
git rm tests/test_local_memory_model.py
git commit -m "chore: remove local memory runtime dependency"
```

## Task 5: Update Docs and Example Config

**Files:**
- Modify: `.env.example`
- Modify: `README.md`
- Modify: `docs/superpowers/specs/2026-04-17-local-memory-extractor-design.md`

- [ ] **Step 1: Write the failing doc regression test**

Create a doc guard test in `tests/test_memory_extractor_client.py`:

```python
class DocsCleanupTests(unittest.TestCase):
    def test_env_example_documents_ollama_memory_extractor(self):
        with open(".env.example", "r", encoding="utf-8") as handle:
            content = handle.read()
        self.assertIn("MEMORY_EXTRACTOR_BASE_URL=http://127.0.0.1:11434/v1", content)
        self.assertIn("MEMORY_EXTRACTOR_MODEL=", content)
        self.assertNotIn("MEMORY_EXTRACTOR_MODEL_PATH", content)
```

- [ ] **Step 2: Run the doc guard test to verify it fails**

Run:

```powershell
python -m unittest tests.test_memory_extractor_client.DocsCleanupTests
```

Expected: FAIL because the docs and example env still describe the old local model file path settings.

- [ ] **Step 3: Update docs for Ollama workflow**

Apply these content changes:

In `.env.example`, keep only the Ollama memory extractor block from Task 1.

In `README.md`, add a short operator note like:

```md
### Viewer Memory Extractor

Viewer memory extraction now uses an Ollama or other OpenAI-compatible chat endpoint.

Recommended local setup:

1. Start Ollama
2. Pull a memory extraction model
3. Set `MEMORY_EXTRACTOR_ENABLED=true`
4. Set `MEMORY_EXTRACTOR_BASE_URL=http://127.0.0.1:11434/v1`
5. Set `MEMORY_EXTRACTOR_MODEL=<your ollama model name>`

The previous in-process GGUF runtime path has been removed.
```

In `docs/superpowers/specs/2026-04-17-local-memory-extractor-design.md`, replace the direct GGUF runtime configuration section with a note that the design has been superseded by the Ollama-backed path and point readers to `docs/superpowers/specs/2026-04-18-memory-extractor-ollama-design.md`.

- [ ] **Step 4: Run the doc guard and remaining backend tests**

Run:

```powershell
python -m unittest tests.test_memory_extractor_client.DocsCleanupTests tests.test_llm_memory_extractor tests.test_comment_processing_status
```

Expected: PASS

- [ ] **Step 5: Commit the documentation sync**

```bash
git add .env.example README.md docs/superpowers/specs/2026-04-17-local-memory-extractor-design.md tests/test_memory_extractor_client.py
git commit -m "docs: switch memory extractor docs to ollama"
```

## Task 6: Final Verification

**Files:**
- Modify: none
- Test: `tests/test_llm_memory_extractor.py`
- Test: `tests/test_memory_extractor_client.py`
- Test: `tests/test_comment_processing_status.py`

- [ ] **Step 1: Run the full relevant backend test suite**

Run:

```powershell
python -m unittest tests.test_llm_memory_extractor tests.test_memory_extractor_client tests.test_comment_processing_status
```

Expected: PASS with all memory-extractor-relevant tests green.

- [ ] **Step 2: Run a smoke script against the new client path**

Run:

```powershell
@'
from backend.config import Settings
from backend.services.memory_extractor_client import MemoryExtractorClient

settings = Settings()
client = MemoryExtractorClient(settings)
print(client._settings.memory_extractor_base_url)
print(client._settings.memory_extractor_model)
'@ | python -
```

Expected: print the configured Ollama base URL and model name without import/runtime errors.

- [ ] **Step 3: Verify no obsolete local runtime references remain**

Run:

```powershell
git grep -n "LocalMemoryExtractionModel\|llama_cpp\|MEMORY_EXTRACTOR_MODEL_PATH\|MEMORY_EXTRACTOR_MODEL_FILENAME\|MEMORY_EXTRACTOR_MODEL_URL\|MEMORY_EXTRACTOR_THREADS\|MEMORY_EXTRACTOR_CONTEXT_SIZE" -- backend tests README.md .env.example docs
```

Expected: no matches, except historical text you intentionally preserved as a superseded note.

- [ ] **Step 4: Check working tree for only intended changes**

Run:

```powershell
git status --short
```

Expected: only the files from this migration plus any unrelated pre-existing user changes outside this scope.

- [ ] **Step 5: Commit the final verification checkpoint**

```bash
git add backend/config.py backend/app.py backend/services/llm_memory_extractor.py backend/services/memory_extractor_client.py requirements.txt tests/test_llm_memory_extractor.py tests/test_memory_extractor_client.py tests/test_comment_processing_status.py .env.example README.md docs/superpowers/specs/2026-04-17-local-memory-extractor-design.md
git commit -m "feat: migrate memory extractor to ollama"
```
