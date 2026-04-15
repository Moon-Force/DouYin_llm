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
