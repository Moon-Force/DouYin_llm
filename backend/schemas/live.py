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
    processing_status: "CommentProcessingStatus | None" = None


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
    support_kind: str = "context"
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
    memory_recall_text: str = ""
    memory_type: str = "fact"
    polarity: str = "neutral"
    temporal_scope: str = "long_term"
    confidence: float = 0.0
    created_at: int
    updated_at: int
    last_recalled_at: int | None = None
    recall_count: int = 0
    source_kind: str = "auto"
    status: str = "active"
    is_pinned: bool = False
    correction_reason: str = ""
    corrected_by: str = ""
    last_operation: str = "created"
    last_operation_at: int = 0
    memory_text_raw_latest: str = ""
    evidence_count: int = 1
    first_confirmed_at: int = 0
    last_confirmed_at: int = 0
    superseded_by: str = ""
    merge_parent_id: str = ""
    stability_score: float = 0.0
    interaction_value_score: float = 0.0
    clarity_score: float = 0.0
    evidence_score: float = 0.0
    lifecycle_kind: str = "long_term"
    expires_at: int = 0


class ViewerMemoryLog(BaseModel):
    """Audit trail for viewer memory corrections."""

    log_id: str
    memory_id: str
    room_id: str
    viewer_id: str
    operation: str
    operator: str = ""
    reason: str = ""
    old_memory_text: str = ""
    new_memory_text: str = ""
    old_memory_type: str = ""
    new_memory_type: str = ""
    old_status: str = ""
    new_status: str = ""
    old_is_pinned: bool = False
    new_is_pinned: bool = False
    created_at: int


class CommentProcessingStatus(BaseModel):
    """Per-comment runtime processing status shown in the frontend."""

    received: bool = False
    persisted: bool = False
    memory_extraction_attempted: bool = False
    memory_prefiltered: bool = False
    memory_llm_attempted: bool = False
    memory_refined: bool = False
    memory_used_for_current_suggestion: bool = False
    memory_persisted: bool = False
    memory_saved: bool = False
    saved_memory_ids: list[str] = Field(default_factory=list)
    extracted_memory_texts: list[str] = Field(default_factory=list)
    memory_recall_attempted: bool = False
    memory_recalled: bool = False
    recalled_memory_ids: list[str] = Field(default_factory=list)
    recalled_memory_texts: list[str] = Field(default_factory=list)
    suggestion_generated: bool = False
    suggestion_id: str = ""
    suggestion_status: str = ""
    suggestion_block_reason: str = ""
    suggestion_block_detail: str = ""
    suggestion_support_kind: str = ""


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
