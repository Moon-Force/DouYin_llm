# Recall Rewrite Memory Expansion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add dedicated memory recall text plus query rewrite so viewer memory recall improves without changing canonical memory display.

**Architecture:** Persist `memory_recall_text` beside `memory_text`, index recall text in Chroma, and keep canonical text in returned memory payloads. Generate recall text through an LLM-first service with deterministic fallback, and rewrite query text before semantic search with a fallback path.

**Tech Stack:** Python, FastAPI, SQLite, ChromaDB, pytest, existing OpenAI-compatible LLM settings.

---

### Task 1: Persist Recall Text

**Files:**
- Modify: `backend/schemas/live.py`
- Modify: `backend/memory/long_term.py`
- Test: `tests/test_long_term_store.py`

- [ ] Add `memory_recall_text` to the `ViewerMemory` schema with default empty string.
- [ ] Add a SQLite column migration for `viewer_memories.memory_recall_text`.
- [ ] Save, load, list, merge, upgrade, and edit viewer memories while preserving the field.
- [ ] Add tests proving the field persists and historical rows fall back safely.

### Task 2: Index Recall Text

**Files:**
- Modify: `backend/memory/vector_store.py`
- Test: `tests/test_vector_store.py`

- [ ] Use `memory_recall_text` as Chroma document and embedding input when present.
- [ ] Keep result payload `memory_text` canonical and expose recall text only as metadata/debug field.
- [ ] Update sample matching so a changed recall document forces collection rebuild.
- [ ] Add tests for canonical return text and recall document indexing.

### Task 3: Generate Recall Expansion

**Files:**
- Create: `backend/services/memory_recall_text.py`
- Modify: `backend/app.py`
- Test: `tests/test_memory_recall_text.py`

- [ ] Implement LLM-first memory recall expansion with rule fallback.
- [ ] Generate recall text when creating, merging, and upgrading memories.
- [ ] Run expansion off the event loop for live event processing.
- [ ] Add tests for LLM success, LLM failure fallback, and app persistence integration.

### Task 4: Rewrite Recall Query

**Files:**
- Create: `backend/services/recall_query_rewriter.py`
- Modify: `backend/services/agent.py`
- Modify: `backend/memory/vector_store.py`
- Test: `tests/test_recall_query_rewriter.py`

- [ ] Implement query rewrite with LLM-first behavior and deterministic fallback.
- [ ] Pass rewritten query into memory recall without changing user-facing comment text.
- [ ] Add tests showing rewritten query is used and original query still works when rewrite fails.

### Task 5: Verify Simulation

**Files:**
- Existing simulation artifacts are not committed unless explicitly requested.

- [ ] Run targeted tests after each task.
- [ ] Run `python -m pytest -q`.
- [ ] Run `npm run build`.
- [ ] Rerun the 20×500 yearly simulation and compare Top1/Top3 against the previous baseline.
