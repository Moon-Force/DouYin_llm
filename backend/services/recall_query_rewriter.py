"""Rewrite live comments into recall-friendly memory queries."""

from __future__ import annotations

import json
import re


class RecallQueryRewriter:
    def __init__(self, client=None, max_chars=260):
        self.client = client
        self.max_chars = int(max_chars)

    def rewrite(self, query_text, room_id="", viewer_id=""):
        query_text = self._clean(query_text)
        if not query_text:
            return ""
        llm_text = self._rewrite_with_llm(query_text, room_id, viewer_id)
        if self._is_valid(llm_text, query_text):
            return self._join(query_text, llm_text)
        return self._join(query_text, self._fallback(query_text))

    def _rewrite_with_llm(self, query_text, room_id, viewer_id):
        if not self.client:
            return ""
        system_prompt = (
            "你负责把直播间观众当前发言改写成长期记忆召回查询。"
            "只输出 JSON，字段为 query_recall_text。"
            "保留原意，不回答用户，不添加事实；补充可能要召回的偏好、忌口、购买、身份、场景关键词。"
        )
        user_prompt = json.dumps(
            {
                "comment": query_text,
                "room_id": room_id,
                "viewer_id": viewer_id,
                "constraints": "query_recall_text 30-160 中文字以内，适合语义检索。",
            },
            ensure_ascii=False,
        )
        try:
            payload = json.loads(self.client.infer_json(system_prompt, user_prompt))
        except Exception:
            return ""
        if not isinstance(payload, dict):
            return ""
        return self._clean(payload.get("query_recall_text"))

    def _fallback(self, query_text):
        text = query_text.lower()
        parts = ["长期记忆召回", "观众偏好", "用户画像"]
        if "辣" in text:
            parts.extend(["吃辣", "忌口", "口味", "饮食偏好"])
        if "面" in text or "拉面" in text:
            parts.extend(["拉面", "面条", "日式拉面", "食物偏好"])
        if "咖啡" in text:
            parts.extend(["咖啡", "饮品", "口味偏好"])
        if "护肤" in text or "敏感" in text:
            parts.extend(["护肤", "肤质", "敏感肌", "产品偏好"])
        if "不" in text or "别" in text or "不能" in text:
            parts.extend(["负向偏好", "避免", "不喜欢"])
        return "；".join(self._dedupe(parts))

    def _is_valid(self, rewrite_text, query_text):
        if not rewrite_text:
            return False
        if len(rewrite_text) > self.max_chars:
            return False
        query_tokens = self._tokens(query_text)
        rewrite_tokens = self._tokens(rewrite_text)
        return not query_tokens or bool(query_tokens & rewrite_tokens)

    def _join(self, query_text, rewrite_text):
        items = self._dedupe([query_text, rewrite_text])
        return self._clean("；".join(items))[: self.max_chars]

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
