"""LLM-backed viewer memory extraction protocol layer."""

from __future__ import annotations

import json

from backend.schemas.live import LiveEvent


ALLOWED_MEMORY_TYPES = {"preference", "fact", "context"}
# Fixed code-side mapping; we never trust model-provided confidence directly.
CERTAINTY_TO_CONFIDENCE = {
    "high": 0.86,
    "medium": 0.72,
}
ALLOWED_POLARITIES = {"positive", "negative", "neutral"}
NEGATIVE_TEXT_SIGNALS = (
    "不喜欢",
    "不爱",
    "不想",
    "不吃",
    "不喝",
    "不买",
    "不再",
    "讨厌",
    "反感",
    "拒绝",
    "不能吃",
    "不能喝",
    "忌口",
    "接受不了",
)


class LLMBackedViewerMemoryExtractor:
    def __init__(self, settings, runtime):
        self._settings = settings
        self._runtime = runtime

    def extract(self, event: LiveEvent):
        if event.event_type != "comment":
            return []

        viewer_id = event.user.viewer_id
        content = str(event.content or "").strip()
        if not viewer_id or not content:
            return []

        response_text = self._runtime.infer_json(
            system_prompt=self._system_prompt(),
            user_prompt=self._user_prompt(event, viewer_id, content),
        )
        payload = json.loads(response_text)
        return self._normalize(payload)

    def _normalize(self, payload):
        if not isinstance(payload, dict):
            return []
        if payload.get("should_extract") is not True:
            return []
        temporal_scope = str(payload.get("temporal_scope", "")).strip().lower()
        if temporal_scope != "long_term":
            return []

        polarity = payload.get("polarity")
        if not self._is_non_empty_string(polarity):
            return []
        polarity = polarity.strip().lower()
        if polarity not in ALLOWED_POLARITIES:
            return []

        certainty = str(payload.get("certainty", "")).strip().lower()
        if certainty == "low":
            return []

        confidence = CERTAINTY_TO_CONFIDENCE.get(certainty)
        if confidence is None:
            return []

        memory_type = str(payload.get("memory_type", "")).strip().lower()
        if memory_type not in ALLOWED_MEMORY_TYPES:
            return []

        memory_text = payload.get("memory_text")
        if not self._is_non_empty_string(memory_text):
            return []
        memory_text = memory_text.strip()

        reason = payload.get("reason")
        if not self._is_non_empty_string(reason):
            return []
        reason = reason.strip()

        if polarity == "negative" and not self._has_negative_signal(memory_text):
            return []

        return [
            {
                "memory_text": memory_text,
                "memory_type": memory_type,
                "confidence": confidence,
            }
        ]

    @staticmethod
    def _system_prompt():
        return (
            "你是直播场景记忆抽取器。只抽取对主播后续互动有用、可长期复用的观众记忆。"
            "只返回合法 JSON，不要 markdown，不要额外解释。"
            "JSON 字段必须包含 should_extract,memory_text,memory_type,polarity,temporal_scope,certainty,reason。"
        )

    @staticmethod
    def _user_prompt(event: LiveEvent, viewer_id: str, content: str):
        payload = {
            "event": {
                "event_id": event.event_id,
                "room_id": event.room_id,
                "viewer_id": viewer_id,
                "nickname": event.user.nickname,
                "content": content,
                "ts": event.ts,
            }
        }
        return json.dumps(payload, ensure_ascii=False)

    @staticmethod
    def _is_non_empty_string(value):
        return isinstance(value, str) and bool(value.strip())

    @staticmethod
    def _has_negative_signal(text: str):
        return any(signal in text for signal in NEGATIVE_TEXT_SIGNALS)
