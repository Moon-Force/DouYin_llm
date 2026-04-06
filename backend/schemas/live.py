"""后端共享数据模型。

这些 Pydantic 模型定义了系统内部统一使用的数据结构，
贯穿采集、存储、检索、Agent 和前端接口。
"""

from typing import Any

from pydantic import BaseModel, Field


class Actor(BaseModel):
    """事件里的最小用户身份信息。"""

    id: str = ""
    nickname: str = "未知用户"


class LiveEvent(BaseModel):
    """采集层标准化后的直播事件。"""

    event_id: str
    room_id: str
    platform: str = "douyin"
    event_type: str
    method: str = "unknown"
    livename: str = "未知直播间"
    ts: int
    user: Actor = Field(default_factory=Actor)
    content: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)
    raw: dict[str, Any] = Field(default_factory=dict)


class Suggestion(BaseModel):
    """由事件触发生成的一条提词建议。"""

    suggestion_id: str
    room_id: str
    event_id: str
    source: str = "heuristic"
    priority: str
    reply_text: str
    tone: str
    reason: str
    confidence: float
    source_events: list[str] = Field(default_factory=list)
    references: list[str] = Field(default_factory=list)
    created_at: int


class SessionStats(BaseModel):
    """前端顶部状态条使用的聚合统计。"""

    room_id: str
    total_events: int = 0
    comments: int = 0
    gifts: int = 0
    likes: int = 0
    members: int = 0
    follows: int = 0


class ModelStatus(BaseModel):
    """模型当前状态与最近一次生成结果。"""

    mode: str = "heuristic"
    model: str = "heuristic"
    backend: str = "local"
    last_result: str = "idle"
    last_error: str = ""
    updated_at: int = 0


class SessionSnapshot(BaseModel):
    """前端初始化页面时使用的房间快照。"""

    room_id: str
    recent_events: list[LiveEvent] = Field(default_factory=list)
    recent_suggestions: list[Suggestion] = Field(default_factory=list)
    stats: SessionStats
    model_status: ModelStatus = Field(default_factory=ModelStatus)
