from typing import Any

from pydantic import BaseModel, Field


class Actor(BaseModel):
    id: str = ""
    nickname: str = "未知用户"


class LiveEvent(BaseModel):
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
    suggestion_id: str
    room_id: str
    event_id: str
    priority: str
    reply_text: str
    tone: str
    reason: str
    confidence: float
    source_events: list[str] = Field(default_factory=list)
    references: list[str] = Field(default_factory=list)
    created_at: int


class SessionStats(BaseModel):
    room_id: str
    total_events: int = 0
    comments: int = 0
    gifts: int = 0
    likes: int = 0
    members: int = 0
    follows: int = 0


class SessionSnapshot(BaseModel):
    room_id: str
    recent_events: list[LiveEvent] = Field(default_factory=list)
    recent_suggestions: list[Suggestion] = Field(default_factory=list)
    stats: SessionStats
