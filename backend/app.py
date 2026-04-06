"""后端应用入口。

这个模块把整条主链路串起来：
- 采集器负责从 `douyinLive` 读取实时消息
- memory 层负责短期、长期和向量检索
- agent 负责生成提词建议
- FastAPI 对外提供 REST、SSE 和 WebSocket 接口
"""

import asyncio
import json
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from backend.config import settings
from backend.memory.long_term import LongTermStore
from backend.memory.session_memory import SessionMemory
from backend.memory.vector_store import VectorMemory
from backend.schemas.live import LiveEvent, ModelStatus
from backend.services.agent import LivePromptAgent
from backend.services.broker import EventBroker
from backend.services.collector import DouyinCollector

# 启动前先确保数据目录已经存在，避免运行时写入失败。
settings.ensure_dirs()
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

# 整个后端进程共享的核心服务单例。
broker = EventBroker()
session_memory = SessionMemory(settings.redis_url, settings.session_ttl_seconds)
long_term_store = LongTermStore(settings.database_path)
vector_memory = VectorMemory(settings.chroma_dir)
agent = LivePromptAgent(settings, vector_memory, long_term_store)


class RoomSwitchRequest(BaseModel):
    """切换采集房间接口的请求体。"""

    room_id: str


def event_envelope(kind, data):
    """统一 broker 发出的消息结构。"""

    return {"type": kind, "data": data}


def snapshot_with_status(room_id):
    """构造一个房间快照。

    优先从短期内存拿最近数据；如果短期内存为空，再回退到长期存储。
    最后把当前模型状态一起补进返回结果，方便前端首次加载直接渲染。
    """

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
    """处理一条标准化后的直播事件。

    处理顺序：
    1. 写入短期内存
    2. 持久化到 SQLite
    3. 写入向量检索
    4. 推送事件给前端订阅者
    5. 视情况生成提词建议
    6. 推送最新统计和模型状态
    """

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
    """把采集器生命周期绑定到 FastAPI 应用生命周期。"""

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
    """健康检查接口，供本地启动脚本和人工排查使用。"""

    return {"status": "ok", "room_id": settings.room_id}


@app.get("/api/bootstrap")
async def bootstrap(room_id: str | None = None):
    """返回某个房间的初始快照，供前端首次加载使用。"""

    target_room_id = room_id or settings.room_id
    snapshot = snapshot_with_status(target_room_id)
    return snapshot.model_dump()


@app.post("/api/room")
async def switch_room(payload: RoomSwitchRequest):
    """切换当前正在采集的房间，并返回新房间快照。"""

    target_room_id = payload.room_id.strip()
    if not target_room_id:
        raise HTTPException(status_code=400, detail="room_id is required")

    collector.switch_room(target_room_id)
    snapshot = snapshot_with_status(target_room_id)
    return snapshot.model_dump()


@app.post("/api/events")
async def ingest_event(event: LiveEvent):
    """兼容接口：允许外部直接把标准化事件提交给后端。"""

    suggestion = await process_event(event)
    return {
        "accepted": True,
        "event_id": event.event_id,
        "suggestion": suggestion.model_dump() if suggestion else None,
    }


@app.get("/api/events/stream")
async def stream_events(room_id: str | None = None):
    """SSE 实时事件流接口。

    默认按房间过滤推送内容，只有模型状态目前是全局状态，不做房间过滤。
    """

    target_room_id = (room_id or settings.room_id).strip()

    async def event_generator():
        # 每个客户端各自订阅一个独立队列，互不影响消费进度。
        queue = broker.subscribe()
        try:
            yield "retry: 1500\n\n"
            while True:
                payload = await queue.get()
                payload_room_id = ""
                if isinstance(payload.get("data"), dict):
                    payload_room_id = str(payload["data"].get("room_id", "")).strip()

                if (
                    target_room_id
                    and payload["type"] != "model_status"
                    and payload_room_id != target_room_id
                ):
                    continue

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
    """WebSocket 版本的实时推送接口。"""

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
