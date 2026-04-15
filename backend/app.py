"""Backend application entrypoint."""

import asyncio
import json
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from backend.config import settings
from backend.memory.embedding_service import EmbeddingService
from backend.memory.long_term import LongTermStore
from backend.memory.session_memory import SessionMemory
from backend.memory.vector_store import VectorMemory
from backend.schemas.live import CommentProcessingStatus, LiveEvent, ModelStatus
from backend.services.agent import LivePromptAgent
from backend.services.broker import EventBroker
from backend.services.collector import DouyinCollector
from backend.services.memory_extractor import ViewerMemoryExtractor

settings.ensure_dirs()
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

broker = EventBroker()
session_memory = SessionMemory(settings.redis_url, settings.session_ttl_seconds)
long_term_store = LongTermStore(settings.database_path)
embedding_service = EmbeddingService(settings)
vector_memory = VectorMemory(settings.chroma_dir, settings=settings, embedding_service=embedding_service)
for memory in long_term_store.list_all_viewer_memories(limit=10000):
    vector_memory.add_memory(memory)
agent = LivePromptAgent(settings, vector_memory, long_term_store)
memory_extractor = ViewerMemoryExtractor()


class RoomSwitchRequest(BaseModel):
    room_id: str


class ViewerNoteUpsertRequest(BaseModel):
    room_id: str
    viewer_id: str
    content: str
    author: str = "主播"
    is_pinned: bool = False
    note_id: str | None = None


class LlmSettingsUpdateRequest(BaseModel):
    model: str
    system_prompt: str = ""


def event_envelope(kind, data):
    return {"type": kind, "data": data}


def snapshot_with_status(room_id):
    room_id = str(room_id or "").strip()
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
    processing_status = CommentProcessingStatus(received=True)
    session_memory.add_event(event)
    long_term_store.persist_event(event)
    processing_status.persisted = True

    recent_events = session_memory.recent_events(event.room_id, limit=15)
    suggestion = agent.maybe_generate(event, recent_events)
    generation_metadata = agent.consume_last_generation_metadata()
    processing_status.suggestion_status = str(generation_metadata.get("suggestion_status") or "")
    processing_status.suggestion_block_reason = str(generation_metadata.get("suggestion_block_reason") or "")
    processing_status.suggestion_block_detail = str(generation_metadata.get("suggestion_block_detail") or "")
    processing_status.memory_recall_attempted = bool(generation_metadata.get("memory_recall_attempted"))
    processing_status.recalled_memory_ids = list(generation_metadata.get("recalled_memory_ids", []))
    processing_status.memory_recalled = bool(
        generation_metadata.get("memory_recalled") or processing_status.recalled_memory_ids
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

    processing_status.memory_extraction_attempted = True
    saved_memory_ids = []

    for candidate in memory_extractor.extract(event):
        memory = long_term_store.save_viewer_memory(
            room_id=event.room_id,
            viewer_id=event.user.viewer_id,
            memory_text=candidate["memory_text"],
            source_event_id=event.event_id,
            memory_type=candidate["memory_type"],
            confidence=candidate["confidence"],
        )
        if memory:
            vector_memory.add_memory(memory)
            saved_memory_ids.append(memory.memory_id)

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


collector = DouyinCollector(settings, event_handler=process_event)


@asynccontextmanager
async def lifespan(app: FastAPI):
    collector.start(asyncio.get_running_loop())
    try:
        yield
    finally:
        if settings.room_id:
            long_term_store.close_active_session(settings.room_id)
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
    target_room_id = (room_id or settings.room_id).strip()
    return snapshot_with_status(target_room_id).model_dump()


@app.post("/api/room")
async def switch_room(payload: RoomSwitchRequest):
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
    suggestion = await process_event(event)
    return {
        "accepted": True,
        "event_id": event.event_id,
        "session_id": event.session_id,
        "suggestion": suggestion.model_dump() if suggestion else None,
    }


@app.get("/api/viewer")
async def viewer_detail(room_id: str | None = None, viewer_id: str | None = None, nickname: str | None = None):
    target_room_id = (room_id or settings.room_id).strip()
    detail = long_term_store.get_viewer_detail(target_room_id, viewer_id=viewer_id or "", nickname=nickname or "")
    if not detail:
        raise HTTPException(status_code=404, detail="viewer not found")
    return detail


@app.get("/api/viewer/memories")
async def viewer_memories(room_id: str | None = None, viewer_id: str | None = None, limit: int = 20):
    target_room_id = (room_id or settings.room_id).strip()
    target_viewer_id = (viewer_id or "").strip()
    if not target_viewer_id:
        raise HTTPException(status_code=400, detail="viewer_id is required")
    return {"items": long_term_store.list_viewer_memories(target_room_id, target_viewer_id, limit=limit)}


@app.get("/api/viewer/notes")
async def viewer_notes(room_id: str | None = None, viewer_id: str | None = None, limit: int = 20):
    target_room_id = (room_id or settings.room_id).strip()
    target_viewer_id = (viewer_id or "").strip()
    if not target_viewer_id:
        raise HTTPException(status_code=400, detail="viewer_id is required")
    return {"items": long_term_store.list_viewer_notes(target_room_id, target_viewer_id, limit=limit)}


@app.post("/api/viewer/notes")
async def save_viewer_note(payload: ViewerNoteUpsertRequest):
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
    if not long_term_store.delete_viewer_note(note_id):
        raise HTTPException(status_code=404, detail="note not found")
    return {"deleted": True, "note_id": note_id}


@app.get("/api/settings/llm")
async def get_llm_settings():
    return agent.current_llm_settings()


@app.put("/api/settings/llm")
async def save_llm_settings(payload: LlmSettingsUpdateRequest):
    model = payload.model.strip()
    if not model:
        raise HTTPException(status_code=400, detail="model is required")
    return long_term_store.save_llm_settings(model, payload.system_prompt or "")


@app.get("/api/sessions")
async def list_sessions(room_id: str | None = None, status: str | None = None, limit: int = 20):
    target_room_id = (room_id or "").strip()
    target_status = (status or "").strip()
    return {"items": long_term_store.list_live_sessions(target_room_id, target_status, limit=limit)}


@app.get("/api/sessions/current")
async def current_session(room_id: str | None = None):
    target_room_id = (room_id or settings.room_id).strip()
    if not target_room_id:
        return {}
    return long_term_store.get_active_session(target_room_id)


@app.get("/api/events/stream")
async def stream_events(room_id: str | None = None):
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
    await websocket.accept()
    queue = broker.subscribe()
    await websocket.send_json(event_envelope("bootstrap", snapshot_with_status(settings.room_id).model_dump()))
    try:
        while True:
            payload = await queue.get()
            await websocket.send_json(payload)
    except WebSocketDisconnect:
        broker.unsubscribe(queue)
