"""Deterministic datasets for memory pipeline verification."""

from __future__ import annotations

import json
from pathlib import Path

from backend.schemas.live import LiveEvent


DEFAULT_DATASET_SIZE = 50
DEFAULT_ROOM_ID = "verify-memory-room"
DEFAULT_LIVE_NAME = "verify-room"
DEFAULT_PLATFORM = "douyin"
DEFAULT_METHOD = "WebcastChatMessage"

# 轮换城市和话题，确保批量样本既稳定又覆盖不同语义。
_CITIES = [
    "杭州",
    "上海",
    "苏州",
    "南京",
    "宁波",
    "合肥",
    "武汉",
    "长沙",
    "成都",
    "重庆",
]

_TOPICS = [
    ("上班", "最近总是熬夜，周末想补觉"),
    ("跑步", "最近准备挑战半马，晚上都在练"),
    ("咖啡", "下午下班前总要喝一杯美式"),
    ("火锅", "周末打算和同事去吃九宫格"),
    ("护肤", "换季时脸容易发干，最近一直在补水"),
]


def build_memory_dataset(count: int = DEFAULT_DATASET_SIZE) -> list[dict]:
    """Build a deterministic set of comment events that all produce memories."""

    normalized_count = max(int(count), DEFAULT_DATASET_SIZE)
    dataset = []
    base_ts = 1_710_000_000_000
    for index in range(normalized_count):
        city = _CITIES[index % len(_CITIES)]
        topic, detail = _TOPICS[index % len(_TOPICS)]
        event_number = index + 1
        dataset.append(
            {
                "event_id": f"verify-memory-batch-{event_number:04d}",
                "room_id": DEFAULT_ROOM_ID,
                "platform": DEFAULT_PLATFORM,
                "event_type": "comment",
                "method": DEFAULT_METHOD,
                "livename": DEFAULT_LIVE_NAME,
                "ts": base_ts + event_number,
                "user": {
                    "id": f"verify-memory-viewer-{event_number:04d}",
                    "nickname": f"验证用户{event_number:04d}",
                },
                "content": f"我在{city}{topic}，{detail}，今天还想顺便看看直播间推荐。",
                "metadata": {"dataset": "memory_pipeline", "index": event_number},
                "raw": {},
            }
        )
    return dataset


def export_dataset_fixture(output_path: str | Path, dataset: list[dict] | None = None) -> Path:
    """Write the dataset to a stable JSON fixture file."""

    target_path = Path(output_path)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    # 默认导出内建数据集，方便直接生成回归测试夹具。
    payload = dataset if dataset is not None else build_memory_dataset()
    target_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return target_path


def load_dataset_fixture(input_path: str | Path) -> list[dict]:
    """Load a dataset fixture from disk."""

    return json.loads(Path(input_path).read_text(encoding="utf-8"))


_CLIENT_CASE_GAP_MS = {
    "3_weeks": 21 * 24 * 60 * 60 * 1000,
    "1_month": 31 * 24 * 60 * 60 * 1000,
    "2_months": 60 * 24 * 60 * 60 * 1000,
    "3_months": 91 * 24 * 60 * 60 * 1000,
    "6_months": 182 * 24 * 60 * 60 * 1000,
}

_CLIENT_CASE_BASE_TS = 1_704_067_200_000
_RECENT_CONTEXT_BASE_TS = 1_710_000_000_000


def _build_client_case_event(case_index: int, stage: str, content: str, nickname: str, ts: int) -> dict:
    normalized_stage = str(stage or "").strip().lower() or "history"
    case_number = int(case_index)
    return {
        "event_id": f"client-case-{case_number:02d}-{normalized_stage}",
        "room_id": "verify-client-room",
        "source_room_id": "verify-client-room",
        "session_id": f"client-case-{case_number:02d}-session-{normalized_stage}",
        "platform": "douyin",
        "event_type": "comment",
        "method": "WebcastChatMessage",
        "livename": "verify-live",
        "ts": int(ts),
        "user": {
            "id": f"viewer-client-{case_number:02d}",
            "nickname": str(nickname or f"观众{case_number:02d}"),
        },
        "content": str(content or "").strip(),
        "metadata": {
            "case_id": f"client-case-{case_number:02d}",
            "stage": normalized_stage,
        },
        "raw": {},
    }


def validate_client_case_fixture(cases: list[dict]) -> None:
    """Validate client-form memory cases before pipeline verification."""

    if not cases:
        raise ValueError("client case dataset is empty")

    seen_labels = set()
    for index, case in enumerate(cases, start=1):
        label = str(case.get("label") or "").strip()
        nickname = str(case.get("nickname") or "").strip()
        history = str(case.get("history") or "").strip()
        followup = str(case.get("followup") or "").strip()
        gap = str(case.get("gap") or "").strip().lower()
        prompt_hint = str(case.get("prompt_hint") or "").strip()

        if not label:
            raise ValueError(f"case {index} label is required")
        if label in seen_labels:
            raise ValueError(f"case {index} label must be unique")
        seen_labels.add(label)
        if not nickname:
            raise ValueError(f"case {index} nickname is required")
        if not history:
            raise ValueError(f"case {index} history is required")
        if not followup:
            raise ValueError(f"case {index} followup is required")
        if gap not in _CLIENT_CASE_GAP_MS:
            raise ValueError(f"case {index} gap is invalid")
        if not prompt_hint:
            raise ValueError(f"case {index} prompt_hint is required")


def load_client_case_fixture(input_path: str | Path) -> list[dict]:
    """Load client mock cases and expand them into actual API payload shape."""

    source_cases = json.loads(Path(input_path).read_text(encoding="utf-8"))
    validate_client_case_fixture(source_cases)

    expanded_cases = []
    for index, case in enumerate(source_cases, start=1):
        history_ts = _CLIENT_CASE_BASE_TS + ((index - 1) * 86_400_000)
        followup_ts = history_ts + _CLIENT_CASE_GAP_MS[str(case["gap"]).strip().lower()]
        history_event = _build_client_case_event(index, "history", case["history"], case["nickname"], history_ts)
        followup_event = _build_client_case_event(index, "followup", case["followup"], case["nickname"], followup_ts)

        LiveEvent(**history_event)
        LiveEvent(**followup_event)

        expanded_cases.append(
            {
                "label": str(case["label"]).strip(),
                "history_event": history_event,
                "followup_event": followup_event,
                "expected": {
                    "history_should_extract": True,
                    "followup_should_recall": True,
                    "suggestion_should_generate": True,
                    "prompt_hint": str(case["prompt_hint"]).strip(),
                },
            }
        )

    return expanded_cases


def validate_recent_context_fixture(cases: list[dict]) -> None:
    """Validate recent-context source cases before event expansion."""

    if not cases:
        raise ValueError("recent context dataset is empty")

    seen_labels = set()
    for index, case in enumerate(cases, start=1):
        label = str(case.get("label") or "").strip()
        nickname = str(case.get("nickname") or "").strip()
        recent = case.get("recent")
        current = str(case.get("current") or "").strip()
        prompt_hint = str(case.get("prompt_hint") or "").strip()

        if not label:
            raise ValueError(f"case {index} label is required")
        if label in seen_labels:
            raise ValueError(f"case {index} label must be unique")
        seen_labels.add(label)
        if not nickname:
            raise ValueError(f"case {index} nickname is required")
        if not isinstance(recent, list) or len(recent) < 2:
            raise ValueError(f"case {index} recent must contain at least 2 comments")
        if not all(str(item or "").strip() for item in recent):
            raise ValueError(f"case {index} recent comments must be non-empty strings")
        if not current:
            raise ValueError(f"case {index} current is required")
        if not prompt_hint:
            raise ValueError(f"case {index} prompt_hint is required")


def load_recent_context_fixture(input_path: str | Path) -> list[dict]:
    """Load recent-context cases and expand them into actual event payload shape."""

    source_cases = json.loads(Path(input_path).read_text(encoding="utf-8"))
    validate_recent_context_fixture(source_cases)

    expanded_cases = []
    for index, case in enumerate(source_cases, start=1):
        case_number = int(index)
        base_ts = _RECENT_CONTEXT_BASE_TS + ((case_number - 1) * 86_400_000)
        nickname = str(case["nickname"]).strip()
        recent_events = []
        for offset, content in enumerate(case["recent"], start=1):
            recent_events.append(
                _build_client_case_event(
                    case_number,
                    f"recent-{offset}",
                    str(content).strip(),
                    nickname,
                    base_ts + (offset * 1000),
                )
            )
        current_event = _build_client_case_event(
            case_number,
            "current",
            str(case["current"]).strip(),
            nickname,
            base_ts + ((len(recent_events) + 1) * 1000),
        )

        for payload in recent_events:
            LiveEvent(**payload)
        LiveEvent(**current_event)

        expanded_cases.append(
            {
                "label": str(case["label"]).strip(),
                "recent_events": recent_events,
                "current_event": current_event,
                "expected": {
                    "suggestion_should_generate": True,
                    "prompt_hint": str(case["prompt_hint"]).strip(),
                },
            }
        )

    return expanded_cases


def validate_memory_extraction_cases(cases: list[dict]) -> None:
    """Validate labeled memory extraction cases before offline evaluation."""

    if not cases:
        raise ValueError("memory extraction dataset is empty")

    seen_labels = set()
    allowed_memory_types = {"preference", "fact", "context"}
    allowed_polarities = {"positive", "negative", "neutral"}
    allowed_temporal_scopes = {"long_term", "short_term"}

    for index, case in enumerate(cases, start=1):
        label = str(case.get("label", "")).strip()
        content = str(case.get("content", "")).strip()
        expected = case.get("expected")

        if not label:
            raise ValueError(f"case {index} label is required")
        if label in seen_labels:
            raise ValueError(f"case {index} label must be unique")
        seen_labels.add(label)
        if not content:
            raise ValueError(f"case {index} content is required")
        if not isinstance(expected, dict):
            raise ValueError(f"case {index} expected must be an object")

        should_extract = expected.get("should_extract")
        memory_text = expected.get("memory_text")
        memory_text_raw = expected.get("memory_text_raw")
        memory_text_canonical = expected.get("memory_text_canonical")
        memory_type = str(expected.get("memory_type", "")).strip()
        polarity = str(expected.get("polarity", "")).strip()
        temporal_scope = str(expected.get("temporal_scope", "")).strip()

        if not isinstance(should_extract, bool):
            raise ValueError(f"case {index} expected.should_extract must be a boolean")
        if memory_text is not None and not isinstance(memory_text, str):
            raise ValueError(f"case {index} expected.memory_text must be a string")
        if memory_text_raw is not None and not isinstance(memory_text_raw, str):
            raise ValueError(f"case {index} expected.memory_text_raw must be a string")
        if memory_text_canonical is not None and not isinstance(memory_text_canonical, str):
            raise ValueError(f"case {index} expected.memory_text_canonical must be a string")
        if memory_type not in allowed_memory_types:
            raise ValueError(f"case {index} expected.memory_type is invalid")
        if polarity not in allowed_polarities:
            raise ValueError(f"case {index} expected.polarity is invalid")
        if temporal_scope not in allowed_temporal_scopes:
            raise ValueError(f"case {index} expected.temporal_scope is invalid")
        expected_effective_text = str(memory_text_canonical or memory_text or "").strip()
        if should_extract and not expected_effective_text:
            raise ValueError(
                f"case {index} expected.memory_text_canonical or expected.memory_text is required when should_extract is true"
            )


def load_memory_extraction_fixture(input_path: str | Path) -> list[dict]:
    """Load and validate labeled memory extraction cases from disk."""

    cases = json.loads(Path(input_path).read_text(encoding="utf-8"))
    validate_memory_extraction_cases(cases)
    return cases


def validate_semantic_recall_cases(cases: list[dict]) -> None:
    """Validate semantic recall fixture cases before running evaluation."""

    if not cases:
        raise ValueError("semantic recall dataset is empty")

    for index, case in enumerate(cases, start=1):
        memory_texts = [str(item or "").strip() for item in case.get("memory_texts", [])]
        query = str(case.get("query", "")).strip()
        expected = str(case.get("expected_memory_text", "")).strip()
        label = str(case.get("label", "")).strip()

        if len(memory_texts) < 2:
            raise ValueError(f"case {index} must contain at least 2 memory_texts")
        if not query:
            raise ValueError(f"case {index} query is required")
        if not expected:
            raise ValueError(f"case {index} expected_memory_text is required")
        if expected not in memory_texts:
            raise ValueError(f"case {index} expected_memory_text must exist in memory_texts")
        if not label:
            raise ValueError(f"case {index} label is required")


def load_semantic_recall_fixture(input_path: str | Path) -> list[dict]:
    """Load and validate semantic recall fixture cases from disk."""

    cases = json.loads(Path(input_path).read_text(encoding="utf-8"))
    validate_semantic_recall_cases(cases)
    return cases
