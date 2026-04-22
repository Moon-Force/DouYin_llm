"""LLM-backed viewer memory extraction protocol layer."""

from __future__ import annotations

import json
import re

from backend.schemas.live import LiveEvent
from backend.services.memory_extractor import is_question_like_comment


ALLOWED_MEMORY_TYPES = {"preference", "fact", "context"}
ALLOWED_POLARITIES = {"positive", "negative", "neutral"}
MEMORY_TYPE_CONFIDENCE = {
    "preference": 0.86,
    "context": 0.78,
    "fact": 0.74,
}
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
INTERACTION_SHELL_PATTERNS = (
    re.compile(r"[?？]"),
    re.compile(r"(吗|嘛|呢)$"),
    re.compile(r"^(是不是|有没有|能不能|可不可以)"),
)

BASE_SYSTEM_PROMPT = """
你是直播场景观众记忆抽取器。
只抽取对主播后续互动有用、可长期复用的观众记忆。
只返回合法 JSON，不要 markdown，不要解释。

JSON 字段必须包含：
- should_extract
- memory_text_raw
- memory_text_canonical
- memory_type
- polarity
- temporal_scope
- reason

规则：
- 如果内容是寒暄、刷屏、交易问句、短期计划、短期状态、短期情绪，返回 should_extract=false。
- memory_text_raw 在 should_extract=true 时必须保留原句核心表达。
- memory_text_canonical 在 should_extract=true 时必须是最小可复用表达，用于当前建议、长期落库和后续召回。
- memory_text_canonical 不能保留问句壳子、互动壳子、情绪壳子。
- temporal_scope 只允许 long_term 或 short_term。
- memory_type 只允许 preference、fact、context。
- polarity 只允许 positive、negative、neutral。
- 长期稳定饮食限制、回避项、明确喜欢/不喜欢，应优先标成 preference。
- 稳定身份、居住、工作、家庭背景，应优先标成 context。
- 长期事实、习惯、能力、身体条件，应优先标成 fact。

示例 1：
输入：我其实平时吧都不太能吃辣
输出：{"should_extract":true,"memory_text_raw":"我其实平时吧都不太能吃辣","memory_text_canonical":"不太能吃辣","memory_type":"preference","polarity":"negative","temporal_scope":"long_term","reason":"稳定饮食限制，对后续推荐有复用价值"}

示例 2：
输入：我租房住在公司附近，这样通勤方便点
输出：{"should_extract":true,"memory_text_raw":"我租房住在公司附近，这样通勤方便点","memory_text_canonical":"租房住在公司附近","memory_type":"context","polarity":"neutral","temporal_scope":"long_term","reason":"稳定居住背景信息，可长期复用"}

示例 3：
输入：这周我可能都在上海出差
输出：{"should_extract":false,"memory_text_raw":"","memory_text_canonical":"","memory_type":"context","polarity":"neutral","temporal_scope":"short_term","reason":"带有明确时间边界的短期状态，不适合长期记忆"}

示例 4：
输入：来了哈哈哈
输出：{"should_extract":false,"memory_text_raw":"","memory_text_canonical":"","memory_type":"fact","polarity":"neutral","temporal_scope":"short_term","reason":"低信息量互动语，不适合长期记忆"}
""".strip()

COT_SUFFIX = """

在作答前请先在内部完成以下检查：
1. 先判断这条信息是否值得长期记忆。
2. 如果值得保留，再抽取原句核心表达作为 memory_text_raw。
3. 再把它提纯成最小可复用表达作为 memory_text_canonical。
4. 最后检查所有字段是否合法。
不要暴露思考过程，只输出一个 JSON 对象。
""".rstrip()


class LLMBackedViewerMemoryExtractor:
    def __init__(self, settings, runtime):
        self._settings = settings
        self._runtime = runtime

    def extract(self, event: LiveEvent):
        payload = self.extract_payload(event)
        return self._normalize(payload)

    def extract_payload(self, event: LiveEvent):
        if event.event_type != "comment":
            return {}

        viewer_id = event.user.viewer_id
        content = str(event.content or "").strip()
        if not viewer_id or not content:
            return {}

        response_text = self._runtime.infer_json(
            system_prompt=self._system_prompt(),
            user_prompt=self._user_prompt(event, viewer_id, content),
        )
        return json.loads(response_text)

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

        memory_type = str(payload.get("memory_type", "")).strip().lower()
        if memory_type not in ALLOWED_MEMORY_TYPES:
            return []

        raw_text = payload.get("memory_text_raw")
        canonical_text = payload.get("memory_text_canonical")
        if not self._is_non_empty_string(raw_text) or not self._is_non_empty_string(canonical_text):
            return []
        raw_text = raw_text.strip()
        canonical_text = canonical_text.strip()
        if self._looks_like_interaction_shell(canonical_text):
            return []

        reason = payload.get("reason")
        if not self._is_non_empty_string(reason):
            return []

        if polarity == "negative" and not self._has_negative_signal(f"{raw_text} {canonical_text}"):
            return []

        confidence = MEMORY_TYPE_CONFIDENCE[memory_type]
        return [
            {
                "memory_text": canonical_text,
                "memory_text_raw": raw_text,
                "memory_text_canonical": canonical_text,
                "memory_type": memory_type,
                "polarity": polarity,
                "temporal_scope": temporal_scope,
                "confidence": confidence,
                "extraction_source": "llm",
            }
        ]

    def _system_prompt(self):
        if self._prompt_variant() == "baseline":
            return BASE_SYSTEM_PROMPT
        return BASE_SYSTEM_PROMPT + COT_SUFFIX

    def _prompt_variant(self):
        variant = str(getattr(self._settings, "memory_extractor_prompt_variant", "cot") or "").strip().lower()
        if variant == "baseline":
            return "baseline"
        return "cot"

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

    @staticmethod
    def _looks_like_interaction_shell(text: str):
        normalized = str(text or "").strip()
        if not normalized:
            return True
        if is_question_like_comment(normalized):
            return True
        return any(pattern.search(normalized) for pattern in INTERACTION_SHELL_PATTERNS)
