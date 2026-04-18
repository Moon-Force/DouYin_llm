# Local Memory Extractor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace keyword-only viewer memory extraction with an in-process local GGUF-backed extractor that runs on Windows + CPU, auto-downloads the model when missing, and falls back to the current rule extractor when the local model is unavailable or returns invalid output.

**Architecture:** Keep `backend.services.memory_extractor.ViewerMemoryExtractor` as the public entrypoint, but split the implementation into a local model runtime, an LLM-backed extraction layer, and a rule-based fallback layer. Wire the extractor in `backend.app.ensure_runtime()` so the rest of the event-processing pipeline stays unchanged, and gate the first version to comment-only long-term memory extraction.

**Tech Stack:** Python, `llama-cpp-python`, FastAPI, SQLite, existing `unittest` suite, project `.env` configuration, Windows-friendly GGUF model files under `data/models/`.

---

## File Structure

- Modify: `H:/DouYin_llm/backend/config.py`
  - Add memory-extractor-specific settings for enable/mode/path/url/filename/context/max tokens/timeout/threads.
- Create: `H:/DouYin_llm/backend/services/local_memory_model.py`
  - Hold the in-process GGUF loader, auto-download logic, lazy initialization, and single-call inference API.
- Create: `H:/DouYin_llm/backend/services/llm_memory_extractor.py`
  - Hold prompt construction, JSON parsing, protocol validation, certainty-to-confidence mapping, and candidate shaping.
- Modify: `H:/DouYin_llm/backend/services/memory_extractor.py`
  - Convert current `ViewerMemoryExtractor` implementation into rule fallback behavior and compose it with the LLM-backed extractor.
- Modify: `H:/DouYin_llm/backend/app.py`
  - Instantiate the new extractor with `settings` and use it without changing the downstream save flow.
- Modify: `H:/DouYin_llm/.env.example`
  - Document the new memory extractor settings.
- Modify: `H:/DouYin_llm/requirements.txt`
  - Add `llama-cpp-python`.
- Create: `H:/DouYin_llm/tests/test_local_memory_model.py`
  - Cover local model path resolution, download behavior, lazy loading, and timeout-safe inference surfaces.
- Create: `H:/DouYin_llm/tests/test_llm_memory_extractor.py`
  - Cover prompt protocol, JSON validation, `short_term` rejection, negative polarity handling, and fallback behavior.
- Modify: `H:/DouYin_llm/tests/test_comment_processing_status.py`
  - Keep the current end-to-end save path stable when the extractor returns LLM-shaped candidates.
- Modify: `H:/DouYin_llm/tests/test_verify_memory_pipeline.py`
  - Preserve pipeline assumptions around `ViewerMemoryExtractor.extract()` returning valid candidates.

### Task 1: Add Configuration Surface for Local Memory Extraction

**Files:**
- Modify: `H:/DouYin_llm/backend/config.py`
- Modify: `H:/DouYin_llm/.env.example`
- Create: `H:/DouYin_llm/tests/test_local_memory_model.py`

- [ ] **Step 1: Write the failing settings test**

```python
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.config import Settings


class LocalMemoryModelSettingsTests(unittest.TestCase):
    def test_memory_extractor_settings_default_to_local_paths(self):
        with tempfile.TemporaryDirectory() as tmpdir, patch.dict(
            "os.environ",
            {
                "DATA_DIR": tmpdir,
                "DATABASE_PATH": str(Path(tmpdir) / "live_prompter.db"),
                "CHROMA_DIR": str(Path(tmpdir) / "chroma"),
            },
            clear=False,
        ):
            settings = Settings()

        self.assertTrue(settings.memory_extractor_enabled)
        self.assertEqual(settings.memory_extractor_mode, "local_llm")
        self.assertEqual(
            settings.memory_extractor_default_dir,
            Path(tmpdir) / "models" / "memory_extractor",
        )
        self.assertEqual(
            settings.memory_extractor_model_filename,
            "qwen2.5-3b-instruct-q4_k_m.gguf",
        )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_local_memory_model.LocalMemoryModelSettingsTests.test_memory_extractor_settings_default_to_local_paths -v`

Expected: `FAIL` with `AttributeError` for missing `memory_extractor_*` settings on `Settings`.

- [ ] **Step 3: Add minimal settings implementation**

```python
from pathlib import Path


@dataclass
class Settings:
    ...
    memory_extractor_enabled: bool = os.getenv("MEMORY_EXTRACTOR_ENABLED", "true").lower() in {"1", "true", "yes", "on"}
    memory_extractor_mode: str = os.getenv("MEMORY_EXTRACTOR_MODE", "local_llm").strip().lower()
    memory_extractor_model_path: str = os.getenv("MEMORY_EXTRACTOR_MODEL_PATH", "").strip()
    memory_extractor_model_url: str = os.getenv("MEMORY_EXTRACTOR_MODEL_URL", "").strip()
    memory_extractor_model_filename: str = os.getenv(
        "MEMORY_EXTRACTOR_MODEL_FILENAME",
        "qwen2.5-3b-instruct-q4_k_m.gguf",
    ).strip()
    memory_extractor_context_size: int = int(os.getenv("MEMORY_EXTRACTOR_CONTEXT_SIZE", "2048"))
    memory_extractor_max_tokens: int = int(os.getenv("MEMORY_EXTRACTOR_MAX_TOKENS", "256"))
    memory_extractor_timeout_seconds: float = float(os.getenv("MEMORY_EXTRACTOR_TIMEOUT_SECONDS", "8"))
    memory_extractor_threads: int = int(os.getenv("MEMORY_EXTRACTOR_THREADS", "0"))

    @property
    def memory_extractor_default_dir(self) -> Path:
        return self.data_dir / "models" / "memory_extractor"

    def ensure_dirs(self):
        ...
        self.memory_extractor_default_dir.mkdir(parents=True, exist_ok=True)
```

- [ ] **Step 4: Document the new environment variables**

```env
# Local Memory Extractor
MEMORY_EXTRACTOR_ENABLED=true
MEMORY_EXTRACTOR_MODE=local_llm
MEMORY_EXTRACTOR_MODEL_PATH=
MEMORY_EXTRACTOR_MODEL_URL=
MEMORY_EXTRACTOR_MODEL_FILENAME=qwen2.5-3b-instruct-q4_k_m.gguf
MEMORY_EXTRACTOR_CONTEXT_SIZE=2048
MEMORY_EXTRACTOR_MAX_TOKENS=256
MEMORY_EXTRACTOR_TIMEOUT_SECONDS=8
MEMORY_EXTRACTOR_THREADS=0
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python -m unittest tests.test_local_memory_model.LocalMemoryModelSettingsTests.test_memory_extractor_settings_default_to_local_paths -v`

Expected: `PASS`

- [ ] **Step 6: Commit**

```bash
git add backend/config.py .env.example tests/test_local_memory_model.py
git commit -m "feat: add local memory extractor settings"
```

### Task 2: Implement the In-Process Local Model Runtime

**Files:**
- Create: `H:/DouYin_llm/backend/services/local_memory_model.py`
- Modify: `H:/DouYin_llm/requirements.txt`
- Create: `H:/DouYin_llm/tests/test_local_memory_model.py`

- [ ] **Step 1: Write the failing local runtime tests**

```python
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock
from unittest.mock import patch

from backend.services.local_memory_model import LocalMemoryExtractionModel


class LocalMemoryExtractionModelTests(unittest.TestCase):
    def test_existing_model_file_is_reused_without_download(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            model_path = Path(tmpdir) / "model.gguf"
            model_path.write_bytes(b"gguf")
            settings = SimpleNamespace(
                memory_extractor_model_path=str(model_path),
                memory_extractor_model_url="https://example.test/model.gguf",
                memory_extractor_model_filename="model.gguf",
                memory_extractor_default_dir=Path(tmpdir),
                memory_extractor_context_size=2048,
                memory_extractor_threads=0,
                memory_extractor_timeout_seconds=8,
                memory_extractor_max_tokens=256,
            )
            runtime = LocalMemoryExtractionModel(settings)

            with patch.object(runtime, "_download_model") as download_mock:
                resolved = runtime.resolve_model_path()

        self.assertEqual(resolved, model_path)
        download_mock.assert_not_called()

    def test_missing_model_downloads_when_url_is_configured(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            settings = SimpleNamespace(
                memory_extractor_model_path="",
                memory_extractor_model_url="https://example.test/model.gguf",
                memory_extractor_model_filename="model.gguf",
                memory_extractor_default_dir=Path(tmpdir),
                memory_extractor_context_size=2048,
                memory_extractor_threads=0,
                memory_extractor_timeout_seconds=8,
                memory_extractor_max_tokens=256,
            )
            runtime = LocalMemoryExtractionModel(settings)

            with patch.object(runtime, "_download_model", side_effect=lambda target: target.write_bytes(b"gguf")):
                resolved = runtime.resolve_model_path()

        self.assertTrue(resolved.exists())
        self.assertEqual(resolved.read_bytes(), b"gguf")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_local_memory_model.LocalMemoryExtractionModelTests -v`

Expected: `FAIL` with `ModuleNotFoundError` for missing `backend.services.local_memory_model`.

- [ ] **Step 3: Add the runtime module and dependency**

```python
from pathlib import Path
import json
import logging
import urllib.request

try:
    from llama_cpp import Llama
except ImportError:  # pragma: no cover
    Llama = None


logger = logging.getLogger(__name__)


class LocalMemoryExtractionModel:
    def __init__(self, settings):
        self.settings = settings
        self._model = None

    def resolve_model_path(self) -> Path:
        explicit = Path(self.settings.memory_extractor_model_path).expanduser() if self.settings.memory_extractor_model_path else None
        if explicit and explicit.exists():
            return explicit
        target = self.settings.memory_extractor_default_dir / self.settings.memory_extractor_model_filename
        if target.exists():
            return target
        if not self.settings.memory_extractor_model_url:
            raise FileNotFoundError("local memory extractor model file is missing")
        self._download_model(target)
        return target

    def _download_model(self, target: Path) -> None:
        target.parent.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(self.settings.memory_extractor_model_url, timeout=30) as response:
            target.write_bytes(response.read())

    def _load_model(self):
        if self._model is not None:
            return self._model
        if Llama is None:
            raise RuntimeError("llama-cpp-python is not installed")
        model_path = self.resolve_model_path()
        threads = self.settings.memory_extractor_threads or None
        self._model = Llama(
            model_path=str(model_path),
            n_ctx=self.settings.memory_extractor_context_size,
            n_threads=threads,
            verbose=False,
        )
        return self._model
```

```text
llama-cpp-python>=0.3.0
```

- [ ] **Step 4: Add an inference surface test and minimal implementation**

```python
def test_infer_json_uses_cached_runtime_and_returns_text(self):
    settings = SimpleNamespace(...)
    runtime = LocalMemoryExtractionModel(settings)
    fake_model = MagicMock()
    fake_model.create_chat_completion.return_value = {
        "choices": [{"message": {"content": "{\"should_extract\": true}"}}]
    }

    with patch.object(runtime, "_load_model", return_value=fake_model):
        payload = runtime.infer_json("system", "{\"event\": \"comment\"}")

    self.assertEqual(payload, "{\"should_extract\": true}")
```

```python
def infer_json(self, system_prompt: str, user_prompt: str) -> str:
    model = self._load_model()
    response = model.create_chat_completion(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.0,
        max_tokens=self.settings.memory_extractor_max_tokens,
        response_format={"type": "json_object"},
    )
    return str(response["choices"][0]["message"]["content"])
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m unittest tests.test_local_memory_model.LocalMemoryExtractionModelTests -v`

Expected: `PASS`

- [ ] **Step 6: Commit**

```bash
git add requirements.txt backend/services/local_memory_model.py tests/test_local_memory_model.py
git commit -m "feat: add local memory extraction runtime"
```

### Task 3: Implement the LLM-Backed Extraction Layer

**Files:**
- Create: `H:/DouYin_llm/backend/services/llm_memory_extractor.py`
- Create: `H:/DouYin_llm/tests/test_llm_memory_extractor.py`

- [ ] **Step 1: Write the failing protocol tests**

```python
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock

from backend.schemas.live import LiveEvent
from backend.services.llm_memory_extractor import LLMBackedViewerMemoryExtractor


def make_event(content):
    return LiveEvent(
        event_id="evt-1",
        room_id="room-1",
        source_room_id="room-1",
        session_id="session-1",
        platform="douyin",
        event_type="comment",
        method="WebcastChatMessage",
        livename="test",
        ts=123,
        user={"id": "user-1", "nickname": "tester"},
        content=content,
        metadata={},
        raw={},
    )


class LLMBackedViewerMemoryExtractorTests(unittest.TestCase):
    def test_returns_candidate_for_valid_long_term_preference(self):
        runtime = MagicMock()
        runtime.infer_json.return_value = (
            '{"should_extract": true, "memory_text": "喜欢豚骨拉面", '
            '"memory_type": "preference", "polarity": "positive", '
            '"temporal_scope": "long_term", "certainty": "high", "reason": "stable"}'
        )
        extractor = LLMBackedViewerMemoryExtractor(SimpleNamespace(), runtime)

        candidates = extractor.extract(make_event("我超爱吃豚骨拉面"))

        self.assertEqual(
            candidates,
            [{"memory_text": "喜欢豚骨拉面", "memory_type": "preference", "confidence": 0.85}],
        )

    def test_rejects_short_term_candidate(self):
        runtime = MagicMock()
        runtime.infer_json.return_value = (
            '{"should_extract": true, "memory_text": "今晚想吃拉面", '
            '"memory_type": "fact", "polarity": "neutral", '
            '"temporal_scope": "short_term", "certainty": "high", "reason": "temporary"}'
        )
        extractor = LLMBackedViewerMemoryExtractor(SimpleNamespace(), runtime)

        self.assertEqual(extractor.extract(make_event("我今晚想吃拉面")), [])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_llm_memory_extractor.LLMBackedViewerMemoryExtractorTests -v`

Expected: `FAIL` with `ModuleNotFoundError` for missing `backend.services.llm_memory_extractor`.

- [ ] **Step 3: Add the extractor with protocol validation**

```python
import json
import re


class LLMBackedViewerMemoryExtractor:
    SYSTEM_PROMPT = (
        "你是直播间观众长期记忆抽取器。"
        "只提取对主播后续互动有用的长期记忆。"
        "必须返回合法 JSON。"
    )

    def __init__(self, settings, runtime):
        self.settings = settings
        self.runtime = runtime

    def extract(self, event):
        if event.event_type != "comment" or not event.user.viewer_id or not str(event.content or "").strip():
            return []
        payload = self.runtime.infer_json(self.SYSTEM_PROMPT, self._build_user_prompt(event))
        parsed = json.loads(payload)
        normalized = self._normalize(parsed)
        if not normalized:
            return []
        return [normalized]

    def _build_user_prompt(self, event):
        return json.dumps(
            {
                "event_type": event.event_type,
                "room_id": event.room_id,
                "viewer_id": event.user.viewer_id,
                "nickname": event.user.nickname,
                "content": event.content,
            },
            ensure_ascii=False,
        )

    def _normalize(self, payload):
        if payload.get("should_extract") is not True:
            return None
        if payload.get("temporal_scope") != "long_term":
            return None
        if payload.get("certainty") == "low":
            return None
        memory_type = str(payload.get("memory_type") or "").strip()
        if memory_type not in {"preference", "fact", "context"}:
            return None
        memory_text = str(payload.get("memory_text") or "").strip()
        if not memory_text or len(memory_text) > 32:
            return None
        confidence = self._confidence_from_payload(payload, memory_text=memory_text, memory_type=memory_type)
        return {
            "memory_text": memory_text,
            "memory_type": memory_type,
            "confidence": confidence,
        }
```

- [ ] **Step 4: Add validation and fallback-oriented tests**

```python
def test_invalid_json_bubbles_runtime_error_for_composite_fallback(self):
    runtime = MagicMock()
    runtime.infer_json.return_value = "not-json"
    extractor = LLMBackedViewerMemoryExtractor(SimpleNamespace(), runtime)

    with self.assertRaises(json.JSONDecodeError):
        extractor.extract(make_event("我超爱吃豚骨拉面"))


def test_negative_preference_keeps_negative_text(self):
    runtime = MagicMock()
    runtime.infer_json.return_value = (
        '{"should_extract": true, "memory_text": "不喜欢辣", '
        '"memory_type": "preference", "polarity": "negative", '
        '"temporal_scope": "long_term", "certainty": "high", "reason": "stable"}'
    )
    extractor = LLMBackedViewerMemoryExtractor(SimpleNamespace(), runtime)

    candidates = extractor.extract(make_event("我不喜欢辣的"))

    self.assertEqual(candidates[0]["memory_text"], "不喜欢辣")
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m unittest tests.test_llm_memory_extractor -v`

Expected: `PASS`

- [ ] **Step 6: Commit**

```bash
git add backend/services/llm_memory_extractor.py tests/test_llm_memory_extractor.py
git commit -m "feat: add llm-backed memory extractor"
```

### Task 4: Refactor the Existing Rule Extractor into a Fallback Composite

**Files:**
- Modify: `H:/DouYin_llm/backend/services/memory_extractor.py`
- Modify: `H:/DouYin_llm/tests/test_verify_memory_pipeline.py`
- Modify: `H:/DouYin_llm/tests/test_llm_memory_extractor.py`

- [ ] **Step 1: Write the failing composite fallback test**

```python
def test_composite_extractor_falls_back_to_rules_on_llm_failure(self):
    llm_extractor = MagicMock()
    llm_extractor.extract.side_effect = ValueError("invalid llm payload")
    extractor = ViewerMemoryExtractor(settings=None, llm_extractor=llm_extractor)
    event = make_event("我喜欢拉面")

    candidates = extractor.extract(event)

    self.assertEqual(len(candidates), 1)
    self.assertEqual(candidates[0]["memory_type"], "preference")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_llm_memory_extractor.CompositeExtractorTests.test_composite_extractor_falls_back_to_rules_on_llm_failure -v`

Expected: `FAIL` because `ViewerMemoryExtractor` does not yet accept an LLM extractor or preserve the old rule extractor as a fallback.

- [ ] **Step 3: Split the current rules into a dedicated fallback class and compose them**

```python
class RuleFallbackMemoryExtractor:
    def extract(self, event: LiveEvent):
        ...


class ViewerMemoryExtractor:
    def __init__(self, settings=None, llm_extractor=None, rule_extractor=None):
        self.settings = settings
        self.llm_extractor = llm_extractor
        self.rule_extractor = rule_extractor or RuleFallbackMemoryExtractor()

    def extract(self, event: LiveEvent):
        if self.llm_extractor is None:
            return self.rule_extractor.extract(event)
        try:
            candidates = self.llm_extractor.extract(event)
        except Exception:
            return self.rule_extractor.extract(event)
        if candidates:
            return candidates
        return self.rule_extractor.extract(event)
```

- [ ] **Step 4: Preserve the existing pipeline expectations**

```python
def test_build_memory_dataset_returns_fifty_plus_extractable_events(self):
    dataset = build_memory_dataset()
    extractor = ViewerMemoryExtractor()

    self.assertGreaterEqual(len(dataset), DEFAULT_DATASET_SIZE)
    self.assertTrue(all(extractor.extract(LiveEvent(**item)) for item in dataset))
```

Keep this test green so that the internal verifier still works when no local LLM is configured.

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m unittest tests.test_llm_memory_extractor tests.test_verify_memory_pipeline.VerifyMemoryPipelineTests.test_build_memory_dataset_returns_fifty_plus_extractable_events -v`

Expected: `PASS`

- [ ] **Step 6: Commit**

```bash
git add backend/services/memory_extractor.py tests/test_llm_memory_extractor.py tests/test_verify_memory_pipeline.py
git commit -m "refactor: compose llm and rule memory extractors"
```

### Task 5: Wire the Composite Extractor into the Runtime Pipeline

**Files:**
- Modify: `H:/DouYin_llm/backend/app.py`
- Modify: `H:/DouYin_llm/tests/test_comment_processing_status.py`

- [ ] **Step 1: Write the failing runtime wiring test**

```python
import unittest
from unittest.mock import MagicMock
from unittest.mock import patch

import backend.app as app_module


class EnsureRuntimeMemoryExtractorTests(unittest.TestCase):
    def test_ensure_runtime_builds_memory_extractor_with_local_llm_components(self):
        original_memory_extractor = app_module.memory_extractor
        original_settings = app_module.settings
        try:
            app_module.memory_extractor = None
            app_module.settings = MagicMock()
            app_module.settings.ensure_dirs.return_value = None
            app_module.settings.redis_url = ""
            app_module.settings.session_ttl_seconds = 1
            app_module.settings.database_path = "data/test.db"
            app_module.settings.chroma_dir = "data/chroma"
            app_module.settings.embedding_signature.return_value = "sig"
            app_module.settings.room_id = "room-1"

            with patch("backend.app.EventBroker"), patch("backend.app.SessionMemory"), patch("backend.app.LongTermStore"), patch("backend.app.EmbeddingService"), patch("backend.app.VectorMemory"), patch("backend.app.LivePromptAgent"), patch("backend.app.LocalMemoryExtractionModel") as runtime_cls, patch("backend.app.LLMBackedViewerMemoryExtractor") as llm_cls, patch("backend.app.ViewerMemoryExtractor") as extractor_cls, patch("backend.app.DouyinCollector"):
                app_module.ensure_runtime()

            runtime_cls.assert_called_once()
            llm_cls.assert_called_once()
            extractor_cls.assert_called_once()
        finally:
            app_module.memory_extractor = original_memory_extractor
            app_module.settings = original_settings
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_comment_processing_status.EnsureRuntimeMemoryExtractorTests.test_ensure_runtime_builds_memory_extractor_with_local_llm_components -v`

Expected: `FAIL` because `ensure_runtime()` still instantiates `ViewerMemoryExtractor()` directly and does not import the new local components.

- [ ] **Step 3: Update `backend.app` imports and runtime assembly**

```python
from backend.services.local_memory_model import LocalMemoryExtractionModel
from backend.services.llm_memory_extractor import LLMBackedViewerMemoryExtractor
from backend.services.memory_extractor import ViewerMemoryExtractor


def ensure_runtime():
    ...
    if memory_extractor is None:
        local_memory_model = LocalMemoryExtractionModel(settings)
        llm_memory_extractor = LLMBackedViewerMemoryExtractor(settings, local_memory_model)
        memory_extractor = ViewerMemoryExtractor(settings=settings, llm_extractor=llm_memory_extractor)
```

- [ ] **Step 4: Keep the event save-path test green**

```python
app_module.memory_extractor = MagicMock()
app_module.memory_extractor.extract.return_value = [
    {
        "memory_text": "likes ramen",
        "memory_type": "preference",
        "confidence": 0.91,
    }
]
```

Retain the current `process_event()` assertions so the downstream save behavior stays unchanged.

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m unittest tests.test_comment_processing_status -v`

Expected: `PASS`

- [ ] **Step 6: Commit**

```bash
git add backend/app.py tests/test_comment_processing_status.py
git commit -m "feat: wire local memory extractor into runtime"
```

### Task 6: Final Verification and Docs Alignment

**Files:**
- Modify: `H:/DouYin_llm/.env.example`
- Modify: `H:/DouYin_llm/requirements.txt`
- Modify: `H:/DouYin_llm/tests/test_local_memory_model.py`
- Modify: `H:/DouYin_llm/tests/test_llm_memory_extractor.py`
- Modify: `H:/DouYin_llm/tests/test_comment_processing_status.py`
- Modify: `H:/DouYin_llm/tests/test_verify_memory_pipeline.py`

- [ ] **Step 1: Run the focused extractor test suite**

Run: `python -m unittest tests.test_local_memory_model tests.test_llm_memory_extractor tests.test_comment_processing_status tests.test_verify_memory_pipeline.VerifyMemoryPipelineTests.test_build_memory_dataset_returns_fifty_plus_extractable_events -v`

Expected: `PASS`

- [ ] **Step 2: Run the existing memory API and vector regression suite**

Run: `python -m unittest tests.test_long_term tests.test_vector_store tests.test_viewer_memory_api -v`

Expected: `PASS`

- [ ] **Step 3: Run the full comment-processing and verifier coverage if the focused suite is green**

Run: `python -m unittest tests.test_comment_processing_status tests.test_verify_memory_pipeline -v`

Expected: `PASS`

- [ ] **Step 4: Inspect the working tree**

Run: `git status --short`

Expected: only the planned code, config, dependency, and test files are modified.

- [ ] **Step 5: Commit the verification-complete state**

```bash
git add backend/config.py backend/services/local_memory_model.py backend/services/llm_memory_extractor.py backend/services/memory_extractor.py backend/app.py .env.example requirements.txt tests/test_local_memory_model.py tests/test_llm_memory_extractor.py tests/test_comment_processing_status.py tests/test_verify_memory_pipeline.py
git commit -m "feat: add local llm-backed memory extraction"
```

## Self-Review

- Spec coverage:
  - Local in-process GGUF runtime: Task 2
  - Auto-download and local reuse: Task 2
  - LLM-first extraction with strict JSON protocol: Task 3
  - Rule fallback: Task 4
  - Runtime wiring without touching suggestion generation: Task 5
  - Docs and env alignment: Task 1 and Task 6
  - Test coverage for long-term filtering, fallback, and runtime stability: Tasks 2 through 6
- Placeholder scan:
  - No `TODO`, `TBD`, or “implement later” markers remain.
  - Every code-changing step includes concrete code or exact config text.
- Type consistency:
  - `LocalMemoryExtractionModel`, `LLMBackedViewerMemoryExtractor`, `RuleFallbackMemoryExtractor`, and `ViewerMemoryExtractor` names are used consistently across all tasks.
  - `memory_extractor.extract(event)` continues to return `[{memory_text, memory_type, confidence}]` candidates so downstream save code remains stable.
