"""Deterministic datasets for memory pipeline verification."""

from __future__ import annotations

import json
from pathlib import Path


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
