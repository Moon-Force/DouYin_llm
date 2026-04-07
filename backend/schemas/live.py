"""Backend shared data models."""

from typing import Any

from pydantic import BaseModel, Field


class Actor(BaseModel):
    """Minimal user identity stored on each live event."""

    id: str = ""
    short_id: str = ""
    sec_uid: str = ""
    nickname: str = "未知用户"

    @property
    def viewer_id(self) -> str:
        if self.id:
            return f"id:{self.id}"
        if self.sec_uid:
            return f"sec:{self.sec_uid}"
        if self.short_id:
            return f"short:{self.short_id}"

        nickname = self.nickname.strip()
        return f"nick:{nickname}" if nickname else ""


class LiveEvent(BaseModel):
    """Normalized live event used across collection, storage and APIs."""

    event_id: str
    room_id: str
    source_room_id: str = ""
    session_id: str = ""
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
    """Prompt suggestion generated from a live event."""

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


class ViewerMemory(BaseModel):
    """Semantic memory attached to a specific viewer."""

    memory_id: str
    room_id: str
    viewer_id: str
    source_event_id: str = ""
    memory_text: str
    memory_type: str = "fact"
    confidence: float = 0.0
    created_at: int
    updated_at: int
    last_recalled_at: int | None = None
    recall_count: int = 0


class SessionStats(BaseModel):
    """Lightweight room stats shown in the frontend."""

    room_id: str
    total_events: int = 0
    comments: int = 0
    gifts: int = 0
    likes: int = 0
    members: int = 0
    follows: int = 0


class ModelStatus(BaseModel):
    """Current model backend status."""

    mode: str = "heuristic"
    model: str = "heuristic"
    backend: str = "local"
    last_result: str = "idle"
    last_error: str = ""
    updated_at: int = 0


class SessionSnapshot(BaseModel):
    """Bootstrap payload returned to the frontend."""

    room_id: str
    recent_events: list[LiveEvent] = Field(default_factory=list)
    recent_suggestions: list[Suggestion] = Field(default_factory=list)
    stats: SessionStats
    model_status: ModelStatus = Field(default_factory=ModelStatus)
