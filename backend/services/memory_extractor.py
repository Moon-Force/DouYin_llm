"""Heuristics for extracting reusable viewer memories from comments."""

import logging
import re

from backend.schemas.live import LiveEvent


LOW_SIGNAL_EXACT = {
    "来了",
    "来了来了",
    "在",
    "收到",
    "好的",
    "好",
    "嗯",
    "哈哈",
    "哈哈哈",
    "支持",
    "支持主播",
    "点赞",
    "下单了",
    "买了",
    "666",
}

TRANSACTIONAL_KEYWORDS = (
    "多少钱",
    "价格",
    "链接",
    "怎么买",
    "有货吗",
    "能便宜吗",
    "包邮",
)

MEMORY_HINT_KEYWORDS = (
    "我",
    "我们",
    "公司",
    "附近",
    "家",
    "上班",
    "下班",
    "同事",
    "朋友",
    "今天",
    "今晚",
    "明天",
    "周末",
    "最近",
    "刚",
    "发现",
    "一直",
    "喜欢",
    "爱吃",
    "想吃",
    "准备",
    "打算",
    "去了",
    "在吃",
    "工作",
)

logger = logging.getLogger(__name__)

REPETITIVE_FILLER_CHARS = set("哈啊嗯哦哇呀6")
ALLOWED_MEMORY_TYPES = {"preference", "fact", "context"}
HIGH_CONFIDENCE_RULE_PATTERNS = (
    (re.compile(r"^我在.+上班$"), "context"),
    (re.compile(r"^我家里养了.+$"), "fact"),
    (re.compile(r"^我一直都?只用.+$"), "preference"),
    (re.compile(r"^我(?:租房)?住在.+附近$"), "context"),
)
SHORT_TERM_HINTS = ("今天", "今晚", "明天", "这周", "最近", "下周", "下个月")


def clean_comment_text(text):
    cleaned = re.sub(r"\s+", " ", str(text or "")).strip()
    return cleaned.strip("，。！？!?,.~～")


def is_obvious_non_memory_comment(content):
    normalized = clean_comment_text(content)
    if not normalized:
        return True
    if normalized in LOW_SIGNAL_EXACT:
        return True
    if any(keyword in normalized for keyword in TRANSACTIONAL_KEYWORDS) and len(normalized) <= 18:
        return True

    compact = re.sub(r"[，。！？!?,.~～\s]", "", normalized)
    if compact and len(compact) <= 8 and all(char in REPETITIVE_FILLER_CHARS for char in compact):
        return True
    repeated_match = re.fullmatch(r"(.{1,2})\1{2,}", compact or "")
    if repeated_match:
        seed = repeated_match.group(1)
        if all(char in REPETITIVE_FILLER_CHARS for char in seed):
            return True

    return False


class RuleFallbackMemoryExtractor:
    def _clean_text(self, text):
        return clean_comment_text(text)

    def _is_low_signal(self, content):
        if not content:
            return True
        if len(content) <= 4:
            return True
        if content in LOW_SIGNAL_EXACT:
            return True
        if any(keyword in content for keyword in TRANSACTIONAL_KEYWORDS) and len(content) <= 18:
            return True
        return False

    def _memory_type(self, content):
        if any(keyword in content for keyword in ("喜欢", "爱吃", "一直用", "常买")):
            return "preference"
        if any(keyword in content for keyword in ("今晚", "明天", "周末", "准备", "打算", "要去")):
            return "plan"
        if any(keyword in content for keyword in ("公司", "附近", "家里", "上班", "下班")):
            return "context"
        return "fact"

    def _confidence(self, content):
        confidence = 0.45
        if len(content) >= 10:
            confidence += 0.1
        if len(content) >= 18:
            confidence += 0.1
        if any(keyword in content for keyword in MEMORY_HINT_KEYWORDS):
            confidence += 0.15
        if "我" in content:
            confidence += 0.1
        return min(confidence, 0.92)

    def extract(self, event: LiveEvent):
        if event.event_type != "comment":
            return []

        viewer_id = event.user.viewer_id
        content = self._clean_text(event.content)
        if not viewer_id or self._is_low_signal(content):
            return []

        if not any(keyword in content for keyword in MEMORY_HINT_KEYWORDS) and len(content) < 14:
            return []

        return [
            {
                "memory_text": content,
                "memory_text_raw": content,
                "memory_text_canonical": content,
                "memory_type": self._memory_type(content),
                "confidence": self._confidence(content),
                "extraction_source": "rule",
            }
        ]

    def extract_high_confidence(self, event: LiveEvent):
        if event.event_type != "comment":
            return []

        viewer_id = event.user.viewer_id
        content = self._clean_text(event.content)
        if not viewer_id or self._is_low_signal(content):
            return []
        if any(keyword in content for keyword in SHORT_TERM_HINTS):
            return []
        if any(token in content for token in ("?", "？", "吗", "嘛", "呢")):
            return []

        for pattern, memory_type in HIGH_CONFIDENCE_RULE_PATTERNS:
            if not pattern.fullmatch(content):
                continue
            return [
                {
                    "memory_text": content,
                    "memory_text_raw": content,
                    "memory_text_canonical": content,
                    "memory_type": memory_type,
                    "confidence": max(self._confidence(content), 0.88),
                    "extraction_source": "rule_fallback",
                }
            ]
        return []


class ViewerMemoryExtractor:
    def __init__(self, settings=None, llm_extractor=None, rule_extractor=None):
        self._settings = settings
        self._llm_extractor = llm_extractor
        self._rule_extractor = rule_extractor or RuleFallbackMemoryExtractor()
        self._last_extraction_metadata = self._build_metadata()

    @staticmethod
    def _build_metadata(
        *,
        memory_prefiltered=False,
        memory_llm_attempted=False,
        memory_refined=False,
        fallback_used=False,
    ):
        return {
            "memory_prefiltered": bool(memory_prefiltered),
            "memory_llm_attempted": bool(memory_llm_attempted),
            "memory_refined": bool(memory_refined),
            "fallback_used": bool(fallback_used),
        }

    def consume_last_extraction_metadata(self):
        metadata = dict(self._last_extraction_metadata)
        self._last_extraction_metadata = self._build_metadata()
        return metadata

    def _should_prefilter(self, event: LiveEvent):
        if event.event_type != "comment":
            return False
        return is_obvious_non_memory_comment(event.content)

    @staticmethod
    def _should_attempt_llm(event: LiveEvent):
        if event.event_type != "comment":
            return False
        if not str(event.content or "").strip():
            return False
        return bool(event.user.viewer_id)

    def extract(self, event: LiveEvent):
        if self._should_prefilter(event):
            self._last_extraction_metadata = self._build_metadata(memory_prefiltered=True)
            return []

        if self._llm_extractor is None:
            self._last_extraction_metadata = self._build_metadata()
            return self._rule_extractor.extract(event)

        llm_attempted = self._should_attempt_llm(event)

        try:
            llm_candidates = self._llm_extractor.extract(event)
        except Exception:
            logger.exception("LLM memory extraction failed and falling back to rules.")
            self._last_extraction_metadata = self._build_metadata(
                memory_llm_attempted=llm_attempted,
                fallback_used=True,
            )
            high_confidence_extract = getattr(self._rule_extractor, "extract_high_confidence", None)
            if callable(high_confidence_extract):
                return high_confidence_extract(event)
            return self._rule_extractor.extract(event)

        if llm_candidates:
            self._last_extraction_metadata = self._build_metadata(
                memory_llm_attempted=llm_attempted,
                memory_refined=True,
            )
            return llm_candidates

        self._last_extraction_metadata = self._build_metadata(memory_llm_attempted=llm_attempted)
        return []
