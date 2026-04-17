"""Heuristics for extracting reusable viewer memories from comments."""

import logging
import re

from backend.schemas.live import LiveEvent


LOW_SIGNAL_EXACT = {
    "来了",
    "在",
    "收到",
    "好的",
    "好",
    "嗯",
    "哈哈",
    "哈哈哈",
    "支持",
    "点赞",
    "下单了",
    "买了",
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


class RuleFallbackMemoryExtractor:
    def _clean_text(self, text):
        cleaned = re.sub(r"\s+", " ", str(text or "")).strip()
        return cleaned.strip("，。！？!?,.~～")

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
                "memory_type": self._memory_type(content),
                "confidence": self._confidence(content),
            }
        ]


class ViewerMemoryExtractor:
    def __init__(self, settings=None, llm_extractor=None, rule_extractor=None):
        self._settings = settings
        self._llm_extractor = llm_extractor
        self._rule_extractor = rule_extractor or RuleFallbackMemoryExtractor()

    def extract(self, event: LiveEvent):
        if self._llm_extractor is None:
            return self._rule_extractor.extract(event)

        try:
            llm_candidates = self._llm_extractor.extract(event)
        except Exception:
            logger.exception("LLM memory extraction failed and falling back to rules.")
            return self._rule_extractor.extract(event)

        if llm_candidates:
            return llm_candidates

        return self._rule_extractor.extract(event)
