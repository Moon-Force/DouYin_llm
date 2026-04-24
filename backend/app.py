"""Backend application entrypoint."""

import asyncio
import json
import logging
import subprocess
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from backend.config import settings
from backend.memory.embedding_service import EmbeddingService
from backend.memory.long_term import LongTermStore
from backend.memory.rebuild_embeddings import build_memory_collection_name
from backend.memory.rebuild_embeddings import load_manifest
from backend.memory.session_memory import SessionMemory
from backend.memory.vector_store import VectorMemory
from backend.schemas.live import CommentProcessingStatus, LiveEvent, ModelStatus
from backend.services.agent import LivePromptAgent
from backend.services.broker import EventBroker
from backend.services.collector import DouyinCollector
from backend.services.llm_memory_extractor import LLMBackedViewerMemoryExtractor
from backend.services.memory_confidence_service import MemoryConfidenceService
from backend.services.memory_extractor_client import MemoryExtractorClient
from backend.services.memory_extractor import ViewerMemoryExtractor
from backend.services.memory_merge_service import ViewerMemoryMergeService

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

broker = None
session_memory = None
long_term_store = None
embedding_service = None
vector_memory = None
agent = None
memory_extractor = None
collector = None
memory_merge_service = None
memory_confidence_service = None
_primed_memory_room_id = ""


class RoomSwitchRequest(BaseModel):
    room_id: str


class ViewerNoteUpsertRequest(BaseModel):
    room_id: str
    viewer_id: str
    content: str
    author: str = "主播"
    is_pinned: bool = False
    note_id: str | None = None


class ViewerMemoryUpsertRequest(BaseModel):
    room_id: str
    viewer_id: str
    memory_text: str
    memory_type: str = "fact"
    is_pinned: bool = False
    correction_reason: str = ""


class ViewerMemoryUpdateRequest(BaseModel):
    memory_text: str
    memory_type: str = "fact"
    is_pinned: bool = False
    correction_reason: str = ""


class ViewerMemoryStatusRequest(BaseModel):
    reason: str = ""


class LlmSettingsUpdateRequest(BaseModel):
    model: str
    system_prompt: str = ""
    embedding_model: str = ""
    memory_extractor_model: str = ""


def _active_memory_count(memories):
    count = 0
    for memory in memories or []:
        if not memory or not getattr(memory, "memory_text", "") or not getattr(memory, "viewer_id", ""):
            continue
        if str(getattr(memory, "status", "active") or "active") != "active":
            continue
        count += 1
    return count


def _should_force_memory_rebuild(memories):
    if vector_memory is None:
        return False

    manifest = load_manifest(settings)
    collection_name = build_memory_collection_name(vector_memory)
    collection_info = manifest.get("collections", {}).get(collection_name, {})
    expected_count = _active_memory_count(memories)

    if manifest.get("active_signature") != settings.embedding_signature():
        return True
    if collection_info.get("collection_name") != collection_name:
        return True
    return int(collection_info.get("count", -1)) != expected_count


def _normalize_recalled_memory_ids(raw_ids):
    if raw_ids is None:
        return []
    if isinstance(raw_ids, str):
        normalized = raw_ids.strip()
        return [normalized] if normalized else []

    try:
        values = list(raw_ids)
    except TypeError:
        return []

    normalized_ids = []
    for value in values:
        normalized = str(value or "").strip()
        if normalized:
            normalized_ids.append(normalized)
    return normalized_ids


def _parse_ollama_list_output(stdout):
    models = []
    for index, raw_line in enumerate(str(stdout or "").splitlines()):
        line = raw_line.strip()
        if not line:
            continue
        if index == 0 and line.lower().startswith("name"):
            continue
        model = line.split(maxsplit=1)[0].strip()
        if model and model.lower() != "name":
            models.append(model)
    return models


def _list_ollama_models():
    try:
        completed = subprocess.run(
            ["ollama", "list"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        logging.exception("Failed to load Ollama model list")
        return []

    if completed.returncode != 0:
        stderr = str(completed.stderr or "").strip()
        logging.warning("ollama list failed with code=%s stderr=%s", completed.returncode, stderr)
        return []
    return _parse_ollama_list_output(completed.stdout)


def _model_options_with_current(current_value, options):
    normalized_current = str(current_value or "").strip()
    merged = []
    if normalized_current:
        merged.append(normalized_current)
    for option in options or []:
        normalized = str(option or "").strip()
        if normalized and normalized not in merged:
            merged.append(normalized)
    return merged


def _consume_extraction_metadata(extractor):
    consume = getattr(extractor, "consume_last_extraction_metadata", None)
    if not callable(consume):
        return {
            "memory_prefiltered": False,
            "memory_llm_attempted": False,
            "memory_refined": False,
            "fallback_used": False,
        }
    metadata = consume()
    if not isinstance(metadata, dict):
        return {
            "memory_prefiltered": False,
            "memory_llm_attempted": False,
            "memory_refined": False,
            "fallback_used": False,
        }
    return metadata


def _candidate_is_suggestion_ready(candidate):
    if not isinstance(candidate, dict):
        return False
    memory_text = str(candidate.get("memory_text") or "").strip()
    memory_type = str(candidate.get("memory_type") or "").strip().lower()
    if not memory_text or memory_type not in {"preference", "fact", "context"}:
        return False
    if any(token in memory_text for token in ("?", "？")):
        return False
    return True


def _candidate_raw_text(candidate):
    return str(candidate.get("memory_text_raw") or "").strip()


def _candidate_extraction_source(candidate):
    source = str(candidate.get("extraction_source") or "").strip().lower()
    if source == "llm":
        return "llm"
    if source == "rule_fallback":
        return "rule_fallback"
    return "auto"


def _existing_memory_candidates(room_id, viewer_id):
    if long_term_store is None:
        return []
    try:
        return list(long_term_store.list_viewer_memories(room_id, viewer_id, limit=20) or [])
    except Exception:
        logging.exception("Failed to load viewer memory merge candidates for room_id=%s viewer_id=%s", room_id, viewer_id)
        return []


def _candidate_lifecycle(candidate, created_at, settings_obj):
    temporal_scope = str(candidate.get("temporal_scope") or "long_term").strip().lower()
    if temporal_scope == "short_term":
        ttl_hours = float(getattr(settings_obj, "memory_short_term_ttl_hours", 72.0) or 72.0)
        return "short_term", created_at + int(ttl_hours * 3600 * 1000)
    return "long_term", 0


def _viewer_note_preview(room_id, viewer_id, limit=5):
    if long_term_store is None:
        return []
    room_id = str(room_id or "").strip()
    viewer_id = str(viewer_id or "").strip()
    if not room_id or not viewer_id:
        return []
    try:
        notes = long_term_store.list_viewer_notes(room_id, viewer_id, limit=limit) or []
    except Exception:
        logging.exception(
            "Failed to load viewer notes preview for room_id=%s viewer_id=%s",
            room_id,
            viewer_id,
        )
        return []
    preview = []
    for note in notes:
        content = str((note or {}).get("content") or "").strip()
        if content:
            preview.append(content)
    return preview


def ensure_runtime():
    global broker, session_memory, long_term_store, embedding_service, vector_memory, agent, memory_extractor, collector, memory_merge_service, memory_confidence_service

    if all(
        component is not None
        for component in (broker, session_memory, long_term_store, embedding_service, vector_memory, agent, memory_extractor, collector, memory_merge_service, memory_confidence_service)
    ):
        return

    ensure_dirs = getattr(settings, "ensure_dirs", None)
    if callable(ensure_dirs):
        ensure_dirs()

    if broker is None:
        broker = EventBroker()
    if session_memory is None:
        session_memory = SessionMemory(settings.redis_url, settings.session_ttl_seconds)
    if long_term_store is None:
        long_term_store = LongTermStore(settings.database_path)
    if embedding_service is None:
        embedding_service = EmbeddingService(settings)
    if vector_memory is None:
        vector_memory = VectorMemory(settings.chroma_dir, settings=settings, embedding_service=embedding_service)
    if agent is None:
        agent = LivePromptAgent(settings, vector_memory, long_term_store)
    if memory_extractor is None:
        if getattr(settings, "memory_extractor_enabled", False):
            mode = str(getattr(settings, "memory_extractor_mode", "") or "").strip().lower()
            if mode == "ollama":
                try:
                    memory_extractor_client = MemoryExtractorClient(settings)
                    llm_memory_extractor = LLMBackedViewerMemoryExtractor(settings, memory_extractor_client)
                    memory_extractor = ViewerMemoryExtractor(settings=settings, llm_extractor=llm_memory_extractor)
                except Exception:
                    logging.exception(
                        "Ollama memory extractor initialization failed; using rule-only memory extractor"
                    )
                    memory_extractor = ViewerMemoryExtractor(settings=settings)
            else:
                logging.warning(
                    "Unsupported memory_extractor_mode=%r while memory extractor is enabled; using rule-only memory extractor",
                    mode or "<empty>",
                )
                memory_extractor = ViewerMemoryExtractor(settings=settings)
        else:
            memory_extractor = ViewerMemoryExtractor(settings=settings)
    if collector is None:
        collector = DouyinCollector(settings, event_handler=process_event)
    if memory_merge_service is None:
        memory_merge_service = ViewerMemoryMergeService()
    if memory_confidence_service is None:
        memory_confidence_service = MemoryConfidenceService()


def event_envelope(kind, data):
    return {"type": kind, "data": data}


def prime_room_memory_index(room_id):
    global _primed_memory_room_id
    room_id = str(room_id or "").strip()
    if not room_id or room_id == _primed_memory_room_id:
        return
    ensure_runtime()
    memories = long_term_store.list_room_viewer_memories(room_id, limit=10000)
    vector_memory.prime_memory_index(memories, force_rebuild=_should_force_memory_rebuild(memories))
    _primed_memory_room_id = room_id


def snapshot_with_status(room_id):
    ensure_runtime()
    room_id = str(room_id or "").strip()
    prime_room_memory_index(room_id)
    snapshot = session_memory.snapshot(room_id)
    if not snapshot.recent_events:
        snapshot.recent_events = long_term_store.recent_events(room_id, limit=30)
    if not snapshot.recent_suggestions:
        snapshot.recent_suggestions = long_term_store.recent_suggestions(room_id, limit=10)
    if snapshot.stats.total_events == 0:
        snapshot.stats = long_term_store.stats(room_id)
    snapshot.model_status = ModelStatus(**agent.current_status())
    return snapshot


async def process_event(event: LiveEvent):
    ensure_runtime()
    note_preview = _viewer_note_preview(event.room_id, event.user.viewer_id)
    if note_preview:
        event.metadata = {
            **dict(event.metadata or {}),
            "viewer_notes_preview": note_preview,
        }
    processing_status = CommentProcessingStatus(received=True)
    session_memory.add_event(event)
    long_term_store.persist_event(event)
    processing_status.persisted = True

    recent_events = session_memory.recent_events(event.room_id, limit=15)
    saved_memory_ids = []
    extracted_candidates = []
    extract_method = getattr(memory_extractor, "extract", None)
    processing_status.memory_extraction_attempted = bool(event.event_type == "comment" and callable(extract_method))

    if processing_status.memory_extraction_attempted:
        try:
            extracted_candidates = list(extract_method(event) or [])
        except Exception:
            extracted_candidates = []
            logging.exception("Memory extraction pipeline failed for event_id=%s", event.event_id)
        extraction_metadata = _consume_extraction_metadata(memory_extractor)
        processing_status.memory_prefiltered = bool(extraction_metadata.get("memory_prefiltered"))
        processing_status.memory_llm_attempted = bool(extraction_metadata.get("memory_llm_attempted"))
        processing_status.memory_refined = bool(extraction_metadata.get("memory_refined"))

    current_comment_memories = [
        candidate for candidate in extracted_candidates if _candidate_is_suggestion_ready(candidate)
    ]
    processing_status.extracted_memory_texts = [
        str(candidate.get("memory_text") or "").strip()
        for candidate in current_comment_memories
        if str(candidate.get("memory_text") or "").strip()
    ]
    suggestion = agent.maybe_generate(
        event,
        recent_events,
        current_comment_memories=current_comment_memories,
    )
    generation_metadata = agent.consume_last_generation_metadata()
    processing_status.suggestion_status = str(generation_metadata.get("suggestion_status") or "")
    processing_status.suggestion_block_reason = str(generation_metadata.get("suggestion_block_reason") or "")
    processing_status.suggestion_block_detail = str(generation_metadata.get("suggestion_block_detail") or "")
    processing_status.memory_recall_attempted = bool(generation_metadata.get("memory_recall_attempted"))
    processing_status.recalled_memory_ids = _normalize_recalled_memory_ids(
        generation_metadata.get("recalled_memory_ids")
    )
    processing_status.recalled_memory_texts = [
        str(text or "").strip()
        for text in (generation_metadata.get("recalled_memory_texts") or [])
        if str(text or "").strip()
    ]
    processing_status.memory_recalled = bool(
        generation_metadata.get("memory_recalled") or processing_status.recalled_memory_ids
    )
    processing_status.memory_used_for_current_suggestion = bool(
        generation_metadata.get("current_comment_memory_used")
    )
    processing_status.suggestion_support_kind = str(
        generation_metadata.get("suggestion_support_kind") or ""
    )
    if suggestion:
        session_memory.add_suggestion(suggestion)
        long_term_store.persist_suggestion(suggestion)
        processing_status.suggestion_generated = True
        processing_status.suggestion_id = suggestion.suggestion_id
        if not processing_status.suggestion_status:
            processing_status.suggestion_status = "generated"
    else:
        processing_status.suggestion_generated = False
        processing_status.suggestion_id = ""

    if extracted_candidates:
        try:
            for candidate in extracted_candidates:
                existing_memories = _existing_memory_candidates(event.room_id, event.user.viewer_id)
                similar_memories = vector_memory.similar_memories(
                    candidate["memory_text"],
                    event.room_id,
                    event.user.viewer_id,
                    limit=5,
                )
                decision = memory_merge_service.decide(candidate, existing_memories, similar_memories)

                if decision.action == "merge":
                    memory = long_term_store.merge_viewer_memory_evidence(
                        decision.target_memory_id,
                        raw_memory_text=_candidate_raw_text(candidate),
                        confidence=candidate["confidence"],
                        source_event_id=event.event_id,
                    )
                    if memory:
                        vector_memory.sync_memory(memory)
                        saved_memory_ids.append(memory.memory_id)
                    continue

                if decision.action == "upgrade":
                    memory = long_term_store.upgrade_viewer_memory(
                        decision.target_memory_id,
                        memory_text=candidate["memory_text"],
                        raw_memory_text=_candidate_raw_text(candidate),
                        confidence=candidate["confidence"],
                        source_event_id=event.event_id,
                    )
                    if memory:
                        vector_memory.sync_memory(memory)
                        saved_memory_ids.append(memory.memory_id)
                    continue

                if decision.action == "supersede":
                    old_memory, new_memory = long_term_store.supersede_viewer_memory(
                        decision.target_memory_id,
                        room_id=event.room_id,
                        viewer_id=event.user.viewer_id,
                        memory_text=candidate["memory_text"],
                        raw_memory_text=_candidate_raw_text(candidate),
                        source_event_id=event.event_id,
                        memory_type=candidate["memory_type"],
                        confidence=candidate["confidence"],
                    )
                    if old_memory:
                        vector_memory.sync_memory(old_memory)
                    if new_memory:
                        vector_memory.sync_memory(new_memory)
                        saved_memory_ids.append(new_memory.memory_id)
                    continue

                scores = memory_confidence_service.score_new_memory(candidate)
                lifecycle_kind, expires_at = _candidate_lifecycle(candidate, event.ts, settings)
                memory = long_term_store.save_viewer_memory(
                    room_id=event.room_id,
                    viewer_id=event.user.viewer_id,
                    memory_text=candidate["memory_text"],
                    source_event_id=event.event_id,
                    memory_type=candidate["memory_type"],
                    polarity=str(candidate.get("polarity") or "neutral"),
                    temporal_scope=str(candidate.get("temporal_scope") or "long_term"),
                    confidence=scores["confidence"],
                    source_kind=_candidate_extraction_source(candidate),
                    status="active",
                    is_pinned=False,
                    correction_reason="",
                    corrected_by="system",
                    operation="created",
                    raw_memory_text=_candidate_raw_text(candidate),
                    evidence_count=1,
                    first_confirmed_at=event.ts,
                    last_confirmed_at=event.ts,
                    superseded_by="",
                    merge_parent_id="",
                    stability_score=scores["stability_score"],
                    interaction_value_score=scores["interaction_value_score"],
                    clarity_score=scores["clarity_score"],
                    evidence_score=scores["evidence_score"],
                    lifecycle_kind=lifecycle_kind,
                    expires_at=expires_at,
                )
                if memory:
                    vector_memory.sync_memory(memory)
                    saved_memory_ids.append(memory.memory_id)
        except Exception:
            saved_memory_ids = []
            logging.exception("Memory persistence pipeline failed for event_id=%s", event.event_id)

    processing_status.memory_persisted = bool(saved_memory_ids)
    processing_status.memory_saved = bool(saved_memory_ids)
    processing_status.saved_memory_ids = saved_memory_ids
    event.processing_status = processing_status

    await broker.publish(event_envelope("event", event.model_dump()))
    if suggestion:
        await broker.publish(event_envelope("suggestion", suggestion.model_dump()))

    stats = session_memory.stats(event.room_id)
    await broker.publish(event_envelope("stats", stats.model_dump()))
    await broker.publish(event_envelope("model_status", ModelStatus(**agent.current_status()).model_dump()))
    return suggestion

@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_runtime()
    collector.start(asyncio.get_running_loop())
    try:
        yield
    finally:
        if settings.room_id and long_term_store:
            long_term_store.close_active_session(settings.room_id)
        if collector:
            collector.stop()


app = FastAPI(title="Live Prompter Backend", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    if long_term_store is None or vector_memory is None:
        ensure_runtime()
    return {
        "status": "ok",
        "room_id": settings.room_id,
        "active_session": long_term_store.get_active_session(settings.room_id) if settings.room_id else {},
        "embedding_strict": bool(getattr(settings, "embedding_strict", False)),
        "semantic_backend_ready": bool(vector_memory.semantic_backend_ready()),
        "semantic_backend_reason": vector_memory.semantic_backend_reason(),
    }


@app.get("/api/bootstrap")
async def bootstrap(room_id: str | None = None):
    ensure_runtime()
    target_room_id = (room_id or settings.room_id).strip()
    return snapshot_with_status(target_room_id).model_dump()


@app.post("/api/room")
async def switch_room(payload: RoomSwitchRequest):
    ensure_runtime()
    target_room_id = payload.room_id.strip()
    if not target_room_id:
        raise HTTPException(status_code=400, detail="room_id is required")

    current_room_id = settings.room_id
    if current_room_id != target_room_id:
        long_term_store.close_active_session(current_room_id)
        collector.switch_room(target_room_id)

    return snapshot_with_status(target_room_id).model_dump()


@app.post("/api/events")
async def ingest_event(event: LiveEvent):
    ensure_runtime()
    suggestion = await process_event(event)
    return {
        "accepted": True,
        "event_id": event.event_id,
        "session_id": event.session_id,
        "suggestion": suggestion.model_dump() if suggestion else None,
    }


@app.get("/api/viewer")
async def viewer_detail(room_id: str | None = None, viewer_id: str | None = None, nickname: str | None = None):
    ensure_runtime()
    target_room_id = (room_id or settings.room_id).strip()
    detail = long_term_store.get_viewer_detail(target_room_id, viewer_id=viewer_id or "", nickname=nickname or "")
    if not detail:
        raise HTTPException(status_code=404, detail="viewer not found")
    return detail


@app.get("/api/viewer/memories")
async def viewer_memories(room_id: str | None = None, viewer_id: str | None = None, limit: int = 20):
    ensure_runtime()
    target_room_id = (room_id or settings.room_id).strip()
    target_viewer_id = (viewer_id or "").strip()
    if not target_viewer_id:
        raise HTTPException(status_code=400, detail="viewer_id is required")
    return {"items": long_term_store.list_viewer_memories(target_room_id, target_viewer_id, limit=limit)}


@app.post("/api/viewer/memories")
async def create_viewer_memory(payload: ViewerMemoryUpsertRequest):
    ensure_runtime()
    room_id = payload.room_id.strip()
    viewer_id = payload.viewer_id.strip()
    memory_text = payload.memory_text.strip()
    if not room_id:
        raise HTTPException(status_code=400, detail="room_id is required")
    if not viewer_id:
        raise HTTPException(status_code=400, detail="viewer_id is required")
    if not memory_text:
        raise HTTPException(status_code=400, detail="memory_text is required")

    memory = long_term_store.save_viewer_memory(
        room_id,
        viewer_id,
        memory_text,
        source_event_id="",
        memory_type=payload.memory_type.strip() or "fact",
        confidence=1.0,
        source_kind="manual",
        status="active",
        is_pinned=payload.is_pinned,
        correction_reason=payload.correction_reason,
        corrected_by="主播",
        operation="created",
    )
    vector_memory.sync_memory(memory)
    return memory


@app.put("/api/viewer/memories/{memory_id}")
async def update_viewer_memory(memory_id: str, payload: ViewerMemoryUpdateRequest):
    ensure_runtime()
    memory = long_term_store.update_viewer_memory(
        memory_id=memory_id,
        memory_text=payload.memory_text,
        memory_type=payload.memory_type,
        is_pinned=payload.is_pinned,
        correction_reason=payload.correction_reason,
        corrected_by="主播",
    )
    if not memory:
        raise HTTPException(status_code=404, detail="memory not found")
    vector_memory.sync_memory(memory)
    return memory


@app.post("/api/viewer/memories/{memory_id}/invalidate")
async def invalidate_viewer_memory(memory_id: str, payload: ViewerMemoryStatusRequest):
    ensure_runtime()
    memory = long_term_store.invalidate_viewer_memory(memory_id, reason=payload.reason, corrected_by="主播")
    if not memory:
        raise HTTPException(status_code=404, detail="memory not found")
    vector_memory.sync_memory(memory)
    return memory


@app.post("/api/viewer/memories/{memory_id}/reactivate")
async def reactivate_viewer_memory(memory_id: str, payload: ViewerMemoryStatusRequest):
    ensure_runtime()
    memory = long_term_store.reactivate_viewer_memory(memory_id, reason=payload.reason, corrected_by="主播")
    if not memory:
        raise HTTPException(status_code=404, detail="memory not found")
    vector_memory.sync_memory(memory)
    return memory


@app.delete("/api/viewer/memories/{memory_id}")
async def delete_viewer_memory(memory_id: str, payload: ViewerMemoryStatusRequest):
    ensure_runtime()
    memory = long_term_store.delete_viewer_memory(memory_id, reason=payload.reason, corrected_by="主播")
    if not memory:
        raise HTTPException(status_code=404, detail="memory not found")
    vector_memory.remove_memory(memory_id)
    return memory


@app.get("/api/viewer/memories/{memory_id}/logs")
async def viewer_memory_logs(memory_id: str, limit: int = 20):
    ensure_runtime()
    return {"items": long_term_store.list_viewer_memory_logs(memory_id, limit=limit)}


@app.get("/api/viewer/notes")
async def viewer_notes(room_id: str | None = None, viewer_id: str | None = None, limit: int = 20):
    ensure_runtime()
    target_room_id = (room_id or settings.room_id).strip()
    target_viewer_id = (viewer_id or "").strip()
    if not target_viewer_id:
        raise HTTPException(status_code=400, detail="viewer_id is required")
    return {"items": long_term_store.list_viewer_notes(target_room_id, target_viewer_id, limit=limit)}


@app.post("/api/viewer/notes")
async def save_viewer_note(payload: ViewerNoteUpsertRequest):
    ensure_runtime()
    room_id = payload.room_id.strip()
    viewer_id = payload.viewer_id.strip()
    content = payload.content.strip()
    if not room_id:
        raise HTTPException(status_code=400, detail="room_id is required")
    if not viewer_id:
        raise HTTPException(status_code=400, detail="viewer_id is required")
    if not content:
        raise HTTPException(status_code=400, detail="content is required")
    return long_term_store.save_viewer_note(
        room_id,
        viewer_id,
        content,
        author=payload.author.strip() or "主播",
        is_pinned=payload.is_pinned,
        note_id=payload.note_id or "",
    )


@app.delete("/api/viewer/notes/{note_id}")
async def delete_viewer_note(note_id: str):
    ensure_runtime()
    if not long_term_store.delete_viewer_note(note_id):
        raise HTTPException(status_code=404, detail="note not found")
    return {"deleted": True, "note_id": note_id}


@app.get("/api/settings/llm")
async def get_llm_settings():
    ensure_runtime()
    payload = dict(agent.current_llm_settings())
    ollama_models = _list_ollama_models()
    payload["embedding_model_options"] = _model_options_with_current(
        payload.get("embedding_model"),
        ollama_models,
    )
    payload["memory_extractor_model_options"] = _model_options_with_current(
        payload.get("memory_extractor_model"),
        ollama_models,
    )
    return payload


@app.put("/api/settings/llm")
async def save_llm_settings(payload: LlmSettingsUpdateRequest):
    ensure_runtime()
    model = payload.model.strip()
    if not model:
        raise HTTPException(status_code=400, detail="model is required")
    saved = long_term_store.save_llm_settings(
        model,
        payload.system_prompt or "",
        payload.embedding_model or "",
        payload.memory_extractor_model or "",
    )
    ollama_models = _list_ollama_models()
    saved["embedding_model_options"] = _model_options_with_current(
        saved.get("embedding_model"),
        ollama_models,
    )
    saved["memory_extractor_model_options"] = _model_options_with_current(
        saved.get("memory_extractor_model"),
        ollama_models,
    )
    return saved


@app.get("/api/sessions")
async def list_sessions(room_id: str | None = None, status: str | None = None, limit: int = 20):
    ensure_runtime()
    target_room_id = (room_id or "").strip()
    target_status = (status or "").strip()
    return {"items": long_term_store.list_live_sessions(target_room_id, target_status, limit=limit)}


@app.get("/api/sessions/current")
async def current_session(room_id: str | None = None):
    ensure_runtime()
    target_room_id = (room_id or settings.room_id).strip()
    if not target_room_id:
        return {}
    return long_term_store.get_active_session(target_room_id)


@app.get("/api/events/stream")
async def stream_events(room_id: str | None = None):
    ensure_runtime()
    target_room_id = (room_id or settings.room_id).strip()

    async def event_generator():
        queue = broker.subscribe()
        try:
            yield "retry: 1500\n\n"
            while True:
                payload = await queue.get()
                payload_room_id = ""
                if isinstance(payload.get("data"), dict):
                    payload_room_id = str(payload["data"].get("room_id", "")).strip()
                if target_room_id and payload["type"] != "model_status" and payload_room_id != target_room_id:
                    continue
                yield f"event: {payload['type']}\ndata: {json.dumps(payload['data'], ensure_ascii=False)}\n\n"
        finally:
            broker.unsubscribe(queue)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.websocket("/ws/live")
async def live_socket(websocket: WebSocket):
    ensure_runtime()
    await websocket.accept()
    queue = broker.subscribe()
    await websocket.send_json(event_envelope("bootstrap", snapshot_with_status(settings.room_id).model_dump()))
    try:
        while True:
            payload = await queue.get()
            await websocket.send_json(payload)
    except WebSocketDisconnect:
        broker.unsubscribe(queue)
