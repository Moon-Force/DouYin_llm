# Embedding Strict Mode Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a configurable embedding strict mode that blocks hash embedding and token-match fallback so viewer memory recall is guaranteed to use real embeddings and real vector retrieval when strict mode is enabled.

**Architecture:** Extend `Settings` with a strict-mode flag and teach `EmbeddingService` plus `VectorMemory` to distinguish “development fallback allowed” from “semantic backend must be real”. Surface semantic backend readiness through `VectorMemory` and `/health`, and keep the implementation test-first so strict and non-strict behavior are both explicit and stable.

**Tech Stack:** Python 3, FastAPI, unittest, MagicMock/patch, Chroma-backed vector store, local/cloud embedding backends.

---

## File Structure

- Modify: `H:\DouYin_llm\backend\config.py`
  Add `embedding_strict` parsing and keep the setting available to all semantic components.

- Modify: `H:\DouYin_llm\backend\memory\embedding_service.py`
  Block hash fallback in strict mode and expose a consistent strict-mode error path.

- Modify: `H:\DouYin_llm\backend\memory\vector_store.py`
  Track semantic backend readiness and block in-memory/token fallback when strict mode is enabled.

- Modify: `H:\DouYin_llm\backend\memory\rebuild_embeddings.py`
  Reuse the strict-mode behavior so rebuilds fail instead of writing pseudo embeddings.

- Modify: `H:\DouYin_llm\backend\app.py`
  Add semantic backend status to `/health`.

- Modify: `H:\DouYin_llm\tests\test_embedding_service.py`
  Cover strict vs non-strict embedding fallback behavior.

- Modify: `H:\DouYin_llm\tests\test_vector_store.py`
  Cover strict vs non-strict vector recall fallback behavior.

- Modify: `H:\DouYin_llm\tests\test_rebuild_embeddings.py`
  Cover strict rebuild failure behavior.

- Modify: `H:\DouYin_llm\tests\test_comment_processing_status.py`
  Add `/health` semantic readiness coverage without creating a brand-new test module.

### Task 1: Add strict embedding configuration and block hash fallback

**Files:**
- Modify: `H:\DouYin_llm\backend\config.py`
- Modify: `H:\DouYin_llm\backend\memory\embedding_service.py`
- Modify: `H:\DouYin_llm\tests\test_embedding_service.py`

- [ ] **Step 1: Write failing tests for strict-mode embedding behavior**

Replace `H:\DouYin_llm\tests\test_embedding_service.py` with:

```python
import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from backend.memory.embedding_service import EmbeddingService


def make_settings(**overrides):
    defaults = {
        "embedding_mode": "cloud",
        "embedding_model": "text-embedding-3-small",
        "embedding_base_url": "https://example.test/v1",
        "embedding_api_key": "test-key",
        "embedding_timeout_seconds": 10.0,
        "local_embedding_device": "cpu",
        "local_embedding_batch_size": 8,
        "embedding_strict": False,
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


class EmbeddingServiceTests(unittest.TestCase):
    def test_cloud_mode_uses_embeddings_endpoint(self):
        service = EmbeddingService(make_settings(), fallback_dimensions=8)
        captured = {}

        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def read(self):
                return json.dumps(
                    {"data": [{"embedding": [0.1, 0.2, 0.3]}]},
                    ensure_ascii=False,
                ).encode("utf-8")

        def fake_urlopen(request, timeout):
            captured["url"] = request.full_url
            captured["body"] = json.loads(request.data.decode("utf-8"))
            captured["timeout"] = timeout
            return FakeResponse()

        with patch("backend.memory.embedding_service.urllib.request.urlopen", side_effect=fake_urlopen):
            vector = service.embed_text("hello world")

        self.assertEqual(captured["url"], "https://example.test/v1/embeddings")
        self.assertEqual(captured["body"]["model"], "text-embedding-3-small")
        self.assertEqual(captured["body"]["input"], ["hello world"])
        self.assertEqual(captured["timeout"], 10.0)
        self.assertEqual(vector, [0.1, 0.2, 0.3])

    def test_local_mode_uses_sentence_transformer(self):
        fake_model = type(
            "FakeModel",
            (),
            {
                "encode": lambda self, texts, **kwargs: [[0.4, 0.5, 0.6] for _ in texts],
            },
        )()

        with patch("backend.memory.embedding_service.SentenceTransformer", return_value=fake_model):
            service = EmbeddingService(make_settings(embedding_mode="local", embedding_model="bge-small-zh-v1.5"))
            vector = service.embed_text("喜欢拉面")

        self.assertEqual(vector, [0.4, 0.5, 0.6])

    def test_non_strict_mode_falls_back_to_hash_embedding_when_cloud_call_fails(self):
        service = EmbeddingService(make_settings(), fallback_dimensions=8)

        with patch("backend.memory.embedding_service.urllib.request.urlopen", side_effect=OSError("network down")):
            vector = service.embed_text("fallback text")

        self.assertEqual(len(vector), 8)
        self.assertTrue(any(value != 0.0 for value in vector))

    def test_strict_mode_raises_when_cloud_embedding_fails(self):
        service = EmbeddingService(make_settings(embedding_strict=True), fallback_dimensions=8)

        with patch("backend.memory.embedding_service.urllib.request.urlopen", side_effect=OSError("network down")):
            with self.assertRaisesRegex(RuntimeError, "strict mode"):
                service.embed_text("fallback text")

    def test_strict_mode_raises_when_local_dependency_is_missing(self):
        service = EmbeddingService(
            make_settings(
                embedding_mode="local",
                embedding_model="bge-small-zh-v1.5",
                embedding_strict=True,
            )
        )

        with patch("backend.memory.embedding_service.SentenceTransformer", None):
            with self.assertRaisesRegex(RuntimeError, "strict mode"):
                service.embed_text("喜欢拉面")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the embedding tests and verify the new strict assertions fail first**

Run: `python -m unittest tests.test_embedding_service -v`

Expected: FAIL because the current implementation still falls back to hash embeddings even when strict mode should block it.

- [ ] **Step 3: Implement the strict-mode gate in config and embedding service**

Update `H:\DouYin_llm\backend\config.py`:

```python
    embedding_mode: str = os.getenv("EMBEDDING_MODE", "cloud").strip().lower()
    embedding_strict: bool = os.getenv("EMBEDDING_STRICT", "false").lower() in {"1", "true", "yes", "on"}
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
```

Update `H:\DouYin_llm\backend\memory\embedding_service.py`:

```python
class EmbeddingService:
    def __init__(self, settings, fallback_dimensions=256):
        self.settings = settings
        self.fallback = HashEmbeddingFunction(dimensions=fallback_dimensions)
        self._local_model = None
        self._fallback_logged = False

    def _strict_mode_enabled(self) -> bool:
        return bool(getattr(self.settings, "embedding_strict", False))

    def _raise_strict_mode_error(self, exc: Exception):
        raise RuntimeError(
            f"Embedding strict mode blocked fallback: mode={self.settings.embedding_mode} "
            f"model={self.settings.embedding_model} error={exc}"
        ) from exc

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        normalized = [str(text or "").strip() for text in texts]
        if not normalized:
            return []

        try:
            if self.settings.embedding_mode == "local":
                return self._embed_local(normalized)
            if self.settings.embedding_mode == "cloud":
                return self._embed_cloud(normalized)
        except Exception as exc:
            if self._strict_mode_enabled():
                logger.error(
                    "Embedding backend failed and strict mode blocked fallback: mode=%s model=%s error=%s",
                    self.settings.embedding_mode,
                    self.settings.embedding_model,
                    exc,
                )
                self._raise_strict_mode_error(exc)

            if not self._fallback_logged:
                logger.warning(
                    "Embedding backend failed; falling back to hash embeddings: mode=%s model=%s error=%s",
                    self.settings.embedding_mode,
                    self.settings.embedding_model,
                    exc,
                )
                self._fallback_logged = True

        return [self.fallback.embed_text(text) for text in normalized]
```

- [ ] **Step 4: Re-run the embedding tests**

Run: `python -m unittest tests.test_embedding_service -v`

Expected: PASS.

- [ ] **Step 5: Commit the strict embedding fallback change**

```bash
git -C H:\DouYin_llm add backend/config.py backend/memory/embedding_service.py tests/test_embedding_service.py
git -C H:\DouYin_llm commit -m "feat: add strict embedding fallback guard"
```

### Task 2: Block vector-store pseudo recall and strict rebuild fallback

**Files:**
- Modify: `H:\DouYin_llm\backend\memory\vector_store.py`
- Modify: `H:\DouYin_llm\backend\memory\rebuild_embeddings.py`
- Modify: `H:\DouYin_llm\tests\test_vector_store.py`
- Modify: `H:\DouYin_llm\tests\test_rebuild_embeddings.py`

- [ ] **Step 1: Write failing tests for strict vector recall and strict rebuild**

Replace `H:\DouYin_llm\tests\test_vector_store.py` with:

```python
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock
from unittest.mock import patch

from backend.memory.vector_store import VectorMemory


def make_settings(signature="cloud_text_embedding_3_small", strict=False):
    return SimpleNamespace(
        embedding_signature=lambda: signature,
        embedding_strict=strict,
        semantic_memory_min_score=0.35,
        semantic_memory_query_limit=6,
        semantic_final_k=3,
    )


class VectorMemoryTests(unittest.TestCase):
    def test_collection_names_only_create_viewer_memory_collection(self):
        fake_client = MagicMock()
        fake_client.get_or_create_collection.return_value = MagicMock()
        fake_embedding = MagicMock()

        with patch("backend.memory.vector_store.chromadb") as chromadb_mock:
            chromadb_mock.PersistentClient.return_value = fake_client
            store = VectorMemory("data/chroma", settings=make_settings(), embedding_service=fake_embedding)

        fake_client.get_or_create_collection.assert_called_once_with("viewer_memories_cloud_text_embedding_3_small")
        self.assertIsNone(store.collection)

    def test_similar_memories_prefers_higher_confidence_when_scores_are_close(self):
        fake_embedding = MagicMock()
        fake_embedding.embed_text.return_value = [0.1, 0.2]
        fake_collection = MagicMock()
        fake_collection.query.return_value = {
            "ids": [["m1", "m2"]],
            "documents": [["likes ramen", "likes noodles"]],
            "metadatas": [[
                {
                    "room_id": "room-1",
                    "viewer_id": "viewer-1",
                    "memory_type": "preference",
                    "confidence": 0.9,
                    "updated_at": 200,
                    "recall_count": 2,
                },
                {
                    "room_id": "room-1",
                    "viewer_id": "viewer-1",
                    "memory_type": "preference",
                    "confidence": 0.4,
                    "updated_at": 300,
                    "recall_count": 1,
                },
            ]],
            "distances": [[0.6, 0.59]],
        }

        store = VectorMemory("data/chroma", settings=make_settings(), embedding_service=fake_embedding)
        store.memory_collection = fake_collection

        result = store.similar_memories("likes eating noodles", "room-1", "viewer-1", limit=2)

        self.assertEqual(result[0]["memory_id"], "m1")

    def test_non_strict_mode_falls_back_to_token_matching_when_query_fails(self):
        fake_embedding = MagicMock()
        fake_embedding.embed_text.return_value = [0.1, 0.2]
        fake_collection = MagicMock()
        fake_collection.query.side_effect = RuntimeError("chroma down")

        store = VectorMemory("data/chroma", settings=make_settings(strict=False), embedding_service=fake_embedding)
        store.memory_collection = fake_collection
        store._memory_items = [
            {
                "id": "m1",
                "document": "likes ramen",
                "metadata": {
                    "room_id": "room-1",
                    "viewer_id": "viewer-1",
                    "memory_type": "preference",
                    "confidence": 0.9,
                    "updated_at": 200,
                    "recall_count": 1,
                },
            }
        ]

        result = store.similar_memories("likes ramen", "room-1", "viewer-1", limit=1)

        self.assertEqual(result[0]["memory_id"], "m1")

    def test_strict_mode_raises_when_query_fails(self):
        fake_embedding = MagicMock()
        fake_embedding.embed_text.return_value = [0.1, 0.2]
        fake_collection = MagicMock()
        fake_collection.query.side_effect = RuntimeError("chroma down")

        store = VectorMemory("data/chroma", settings=make_settings(strict=True), embedding_service=fake_embedding)
        store.memory_collection = fake_collection

        with self.assertRaisesRegex(RuntimeError, "strict mode"):
            store.similar_memories("likes ramen", "room-1", "viewer-1", limit=1)

    def test_strict_mode_marks_backend_not_ready_when_chroma_is_missing(self):
        with patch("backend.memory.vector_store.chromadb", None):
            store = VectorMemory("data/chroma", settings=make_settings(strict=True), embedding_service=MagicMock())

        self.assertFalse(store.semantic_backend_ready())
        self.assertIn("Chroma", store.semantic_backend_reason())
```

Append to `H:\DouYin_llm\tests\test_rebuild_embeddings.py`:

```python
    def test_strict_mode_rebuild_raises_when_embedding_generation_fails(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            chroma_dir = Path(tmpdir) / "chroma"
            conn = sqlite3.connect(db_path)
            conn.executescript(
                """
                CREATE TABLE viewer_memories (
                    memory_id TEXT PRIMARY KEY,
                    room_id TEXT NOT NULL,
                    viewer_id TEXT NOT NULL,
                    source_event_id TEXT,
                    memory_text TEXT NOT NULL,
                    memory_type TEXT NOT NULL,
                    confidence REAL NOT NULL DEFAULT 0,
                    created_at INTEGER NOT NULL,
                    updated_at INTEGER NOT NULL,
                    last_recalled_at INTEGER,
                    recall_count INTEGER NOT NULL DEFAULT 0
                );
                """
            )
            conn.execute(
                """
                INSERT INTO viewer_memories (
                    memory_id, room_id, viewer_id, source_event_id, memory_text, memory_type,
                    confidence, created_at, updated_at, last_recalled_at, recall_count
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                ("m1", "room-1", "viewer-1", "evt-1", "likes ramen", "preference", 0.9, 1, 2, None, 0),
            )
            conn.commit()
            conn.close()

            fake_store = MagicMock()
            fake_store.database_path = db_path
            fake_embedding = MagicMock()
            fake_embedding.embed_texts.side_effect = RuntimeError("Embedding strict mode blocked fallback")
            fake_collection = MagicMock()
            fake_vector_memory = MagicMock()
            fake_vector_memory._collection_suffix = "cloud_bge_m3"
            fake_vector_memory.memory_collection = fake_collection
            fake_vector_memory._client = MagicMock()
            local_settings = make_settings()
            local_settings.database_path = db_path
            local_settings.chroma_dir = chroma_dir
            local_settings.embedding_strict = True

            with self.assertRaisesRegex(RuntimeError, "strict mode"):
                rebuild_embeddings(
                    settings=local_settings,
                    long_term_store=fake_store,
                    embedding_service=fake_embedding,
                    vector_memory=fake_vector_memory,
                    target="memories",
                )
```

- [ ] **Step 2: Run the vector and rebuild tests and verify the new strict assertions fail first**

Run:

```powershell
python -m unittest tests.test_vector_store -v
python -m unittest tests.test_rebuild_embeddings -v
```

Expected: FAIL because `VectorMemory` still falls back to token matching and does not yet expose strict semantic backend readiness helpers.

- [ ] **Step 3: Implement strict-mode blocking in the vector store and let rebuild inherit it**

Update `H:\DouYin_llm\backend\memory\vector_store.py`:

```python
class VectorMemory:
    def __init__(self, storage_path, settings=None, embedding_service=None):
        self.settings = settings
        self._memory_items = []
        self._client = None
        self.collection = None
        self.memory_collection = None
        self.embedding = embedding_service or HashEmbeddingFunction()
        self._collection_suffix = settings.embedding_signature() if settings else "hash_default"
        self._semantic_backend_reason = ""

        if chromadb:
            client = chromadb.PersistentClient(path=str(storage_path))
            self._client = client
            self.memory_collection = client.get_or_create_collection(f"viewer_memories_{self._collection_suffix}")
            self._semantic_backend_reason = ""
        else:
            self._semantic_backend_reason = "Chroma is unavailable"
            logger.warning(
                "Chroma is unavailable; VectorMemory will use in-process fallback indexes only (suffix=%s)",
                self._collection_suffix,
            )

    def _strict_mode_enabled(self):
        return bool(getattr(self.settings, "embedding_strict", False))

    def semantic_backend_ready(self):
        return self.memory_collection is not None and self._client is not None

    def semantic_backend_reason(self):
        if self.semantic_backend_ready():
            return ""
        return self._semantic_backend_reason or "Semantic vector backend is unavailable"

    def _raise_strict_mode_error(self, exc):
        raise RuntimeError(f"Vector recall strict mode blocked fallback: {exc}") from exc

    def _ensure_semantic_backend(self):
        if self._strict_mode_enabled() and not self.semantic_backend_ready():
            self._raise_strict_mode_error(self.semantic_backend_reason())
```

Then call `_ensure_semantic_backend()` at the start of `add_memory()` and `similar_memories()`, and inside the `except Exception:` block in `similar_memories()` change the behavior to:

```python
            except Exception as exc:
                if self._strict_mode_enabled():
                    logger.error("Vector recall failed and strict mode blocked fallback: %s", exc)
                    self._raise_strict_mode_error(exc)
```

`H:\DouYin_llm\backend\memory\rebuild_embeddings.py` should not add any new fallback; keep the current call to `embedding_service.embed_texts(texts)` so the strict-mode exception bubbles out naturally.

- [ ] **Step 4: Re-run the vector and rebuild tests**

Run:

```powershell
python -m unittest tests.test_vector_store -v
python -m unittest tests.test_rebuild_embeddings -v
```

Expected: PASS.

- [ ] **Step 5: Commit the strict vector recall change**

```bash
git -C H:\DouYin_llm add backend/memory/vector_store.py backend/memory/rebuild_embeddings.py tests/test_vector_store.py tests/test_rebuild_embeddings.py
git -C H:\DouYin_llm commit -m "feat: block pseudo semantic recall in strict mode"
```

### Task 3: Surface semantic readiness in `/health` and run regression verification

**Files:**
- Modify: `H:\DouYin_llm\backend\app.py`
- Modify: `H:\DouYin_llm\tests\test_comment_processing_status.py`

- [ ] **Step 1: Write a failing test for `/health` semantic readiness**

Append to `H:\DouYin_llm\tests\test_comment_processing_status.py`:

```python
    def test_health_reports_embedding_strict_and_semantic_backend_status(self):
        original_settings = app_module.settings
        original_long_term_store = app_module.long_term_store
        original_vector_memory = app_module.vector_memory
        try:
            app_module.settings = SimpleNamespace(room_id="room-1", embedding_strict=True)
            app_module.long_term_store = MagicMock()
            app_module.long_term_store.get_active_session.return_value = {"room_id": "room-1"}
            app_module.vector_memory = MagicMock()
            app_module.vector_memory.semantic_backend_ready.return_value = False
            app_module.vector_memory.semantic_backend_reason.return_value = "Chroma is unavailable"

            payload = asyncio.run(app_module.health())

            self.assertEqual(payload["status"], "ok")
            self.assertTrue(payload["embedding_strict"])
            self.assertFalse(payload["semantic_backend_ready"])
            self.assertEqual(payload["semantic_backend_reason"], "Chroma is unavailable")
        finally:
            app_module.settings = original_settings
            app_module.long_term_store = original_long_term_store
            app_module.vector_memory = original_vector_memory
```

- [ ] **Step 2: Run the app/status test and verify it fails first**

Run: `python -m unittest tests.test_comment_processing_status -v`

Expected: FAIL because `/health` does not yet include semantic backend fields.

- [ ] **Step 3: Update `/health` to report semantic readiness**

Modify `H:\DouYin_llm\backend\app.py`:

```python
@app.get("/health")
async def health():
    return {
        "status": "ok",
        "room_id": settings.room_id,
        "active_session": long_term_store.get_active_session(settings.room_id) if settings.room_id else {},
        "embedding_strict": bool(getattr(settings, "embedding_strict", False)),
        "semantic_backend_ready": bool(vector_memory.semantic_backend_ready()),
        "semantic_backend_reason": vector_memory.semantic_backend_reason(),
    }
```

- [ ] **Step 4: Run the targeted regression suite**

Run:

```powershell
python -m unittest tests.test_embedding_service -v
python -m unittest tests.test_vector_store -v
python -m unittest tests.test_rebuild_embeddings -v
python -m unittest tests.test_comment_processing_status -v
```

Expected: PASS for all four commands.

- [ ] **Step 5: Run the broader semantic-memory regression**

Run:

```powershell
python -m unittest tests.test_agent tests.test_embedding_service tests.test_vector_store tests.test_rebuild_embeddings tests.test_comment_processing_status -v
```

Expected: PASS, confirming the stricter semantics did not break the current viewer-memory flow.

- [ ] **Step 6: Commit the health visibility change**

```bash
git -C H:\DouYin_llm add backend/app.py tests/test_comment_processing_status.py
git -C H:\DouYin_llm commit -m "feat: expose semantic backend health status"
```

- [ ] **Step 7: Review final scope and keep the branch clean**

Run: `git -C H:\DouYin_llm diff -- backend/config.py backend/memory/embedding_service.py backend/memory/vector_store.py backend/memory/rebuild_embeddings.py backend/app.py tests/test_embedding_service.py tests/test_vector_store.py tests/test_rebuild_embeddings.py tests/test_comment_processing_status.py`

Expected: diff contains only strict-mode configuration, semantic backend visibility, and matching tests. Do not include `.qoder` or unrelated docs in these commits.
