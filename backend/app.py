import asyncio
import json
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from backend.config import settings
from backend.memory.long_term import LongTermStore
from backend.memory.session_memory import SessionMemory
from backend.memory.vector_store import VectorMemory
from backend.schemas.live import LiveEvent, ModelStatus
from backend.services.agent import LivePromptAgent
from backend.services.broker import EventBroker
from backend.services.collector import DouyinCollector

settings.ensure_dirs()
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

broker = EventBroker()
session_memory = SessionMemory(settings.redis_url, settings.session_ttl_seconds)
long_term_store = LongTermStore(settings.database_path)
vector_memory = VectorMemory(settings.chroma_dir)
agent = LivePromptAgent(settings, vector_memory, long_term_store)


def event_envelope(kind, data):
    return {"type": kind, "data": data}


def snapshot_with_status(room_id):
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
    session_memory.add_event(event)
    long_term_store.persist_event(event)
    vector_memory.add_event(event)

    await broker.publish(event_envelope("event", event.model_dump()))

    recent_events = session_memory.recent_events(event.room_id, limit=15)
    suggestion = agent.maybe_generate(event, recent_events)

    if suggestion:
        session_memory.add_suggestion(suggestion)
        long_term_store.persist_suggestion(suggestion)
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
    return {"status": "ok", "room_id": settings.room_id}


@app.get("/api/bootstrap")
async def bootstrap(room_id: str | None = None):
    target_room_id = room_id or settings.room_id
    snapshot = snapshot_with_status(target_room_id)
    return snapshot.model_dump()


@app.post("/api/events")
async def ingest_event(event: LiveEvent):
    suggestion = await process_event(event)
    return {
        "accepted": True,
        "event_id": event.event_id,
        "suggestion": suggestion.model_dump() if suggestion else None,
    }


@app.get("/api/events/stream")
async def stream_events():
    async def event_generator():
        queue = broker.subscribe()
        try:
            yield "retry: 1500\n\n"
            while True:
                payload = await queue.get()
                message = (
                    f"event: {payload['type']}\n"
                    f"data: {json.dumps(payload['data'], ensure_ascii=False)}\n\n"
                )
                yield message
        finally:
            broker.unsubscribe(queue)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.websocket("/ws/live")
async def live_socket(websocket: WebSocket):
    await websocket.accept()
    queue = broker.subscribe()

    snapshot = snapshot_with_status(settings.room_id)
    await websocket.send_json(event_envelope("bootstrap", snapshot.model_dump()))

    try:
        while True:
            payload = await queue.get()
            await websocket.send_json(payload)
    except WebSocketDisconnect:
        broker.unsubscribe(queue)
