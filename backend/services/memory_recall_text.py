"""Generate recall-optimized text for viewer memories."""

from __future__ import annotations

import json
import re


class MemoryRecallTextService:
    def __init__(self, client=None, max_chars=420):
        self.client = client
        self.max_chars = int(max_chars)

    def expand_memory(self, memory_text, raw_memory_text="", memory_type="fact", polarity="neutral", temporal_scope=""):
        memory_text = self._clean(memory_text)
        raw_memory_text = self._clean(raw_memory_text)
        memory_type = self._clean(memory_type) or "fact"
        polarity = self._clean(polarity) or "neutral"
        temporal_scope = self._clean(temporal_scope)
        if not memory_text:
            return ""

        llm_text = self._expand_with_llm(memory_text, raw_memory_text, memory_type, polarity, temporal_scope)
        if self._is_valid_expansion(llm_text, memory_text, raw_memory_text):
            return self._truncate(llm_text)
        return self._fallback(memory_text, raw_memory_text, memory_type, polarity, temporal_scope)

    def _expand_with_llm(self, memory_text, raw_memory_text, memory_type, polarity, temporal_scope):
        if not self.client:
            return ""
        system_prompt = (
            "你负责为直播观众长期记忆生成向量召回文本。"
            "只输出 JSON，字段为 recall_text。"
            "不要添加新事实，不要改变极性；可以补充同义词、相关场景词、用户可能的表达方式。"
        )
        user_prompt = json.dumps(
            {
                "memory_text": memory_text,
                "raw_memory_text": raw_memory_text,
                "memory_type": memory_type,
                "polarity": polarity,
                "temporal_scope": temporal_scope,
                "constraints": "recall_text 80-220 中文字以内，必须包含原始记忆核心词。",
            },
            ensure_ascii=False,
        )
        try:
            payload = json.loads(self.client.infer_json(system_prompt, user_prompt))
        except Exception:
            return ""
        if not isinstance(payload, dict):
            return ""
        return self._clean(payload.get("recall_text"))

    def _fallback(self, memory_text, raw_memory_text, memory_type, polarity, temporal_scope):
        parts = [memory_text, self._memory_type_label(memory_type), self._polarity_label(polarity)]
        if temporal_scope:
            parts.append(self._scope_label(temporal_scope))
        if raw_memory_text and raw_memory_text != memory_text:
            parts.append(raw_memory_text)
        parts.extend(self._rule_keywords(memory_text, raw_memory_text, memory_type, polarity))
        return self._truncate("；".join(self._dedupe(parts)))

    def _rule_keywords(self, memory_text, raw_memory_text, memory_type, polarity):
        text = f"{memory_text} {raw_memory_text}".lower()
        keywords = ["用户记忆", "观众画像", "直播互动"]
        if "辣" in text:
            keywords.extend(["吃辣", "忌口", "口味", "饮食偏好"])
        if "拉面" in text or "面条" in text or "noodle" in text or "ramen" in text:
            keywords.extend(["拉面", "面条", "日式拉面", "食物偏好"])
        if "咖啡" in text:
            keywords.extend(["咖啡", "饮品", "提神", "口味偏好"])
        if "护肤" in text or "敏感" in text or "skin" in text or "cream" in text or "face cream" in text:
            keywords.extend(["护肤", "肤质", "敏感肌", "产品偏好", "面霜", "皮肤护理"])
        if polarity == "negative":
            keywords.extend(["不喜欢", "不能", "避免", "负向偏好"])
        return keywords

    @staticmethod
    def _memory_type_label(memory_type):
        labels = {"preference": "偏好", "context": "背景信息", "fact": "事实", "behavior": "行为习惯"}
        return labels.get(str(memory_type or "").strip().lower(), "记忆信息")

    @staticmethod
    def _polarity_label(polarity):
        labels = {"positive": "正向", "negative": "负向", "neutral": "中性"}
        return labels.get(str(polarity or "").strip().lower(), "中性")

    @staticmethod
    def _scope_label(temporal_scope):
        labels = {"long_term": "长期记忆", "short_term": "短期记忆"}
        return labels.get(str(temporal_scope or "").strip().lower(), "长期记忆")

    def _is_valid_expansion(self, recall_text, memory_text, raw_memory_text):
        if not recall_text or len(recall_text) < len(memory_text):
            return False
        source_tokens = self._tokens(memory_text) | self._tokens(raw_memory_text)
        recall_tokens = self._tokens(recall_text)
        if not source_tokens:
            return memory_text in recall_text
        return bool(source_tokens & recall_tokens)

    @staticmethod
    def _tokens(text):
        text = str(text or "").lower()
        tokens = set(re.findall(r"[a-z0-9]+", text))
        for run in re.findall(r"[\u4e00-\u9fff]+", text):
            tokens.update(run[index : index + 2] for index in range(len(run) - 1))
            if len(run) <= 8:
                tokens.add(run)
        return {token for token in tokens if token}

    @staticmethod
    def _dedupe(values):
        seen = set()
        result = []
        for value in values:
            value = str(value or "").strip()
            if not value or value in seen:
                continue
            seen.add(value)
            result.append(value)
        return result

    @staticmethod
    def _clean(value):
        return re.sub(r"\s+", " ", str(value or "")).strip()

    def _truncate(self, text):
        text = self._clean(text)
        if len(text) <= self.max_chars:
            return text
        return text[: self.max_chars].rstrip("；,，。 ")
