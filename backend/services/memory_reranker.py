"""Online reranking helpers for viewer memory recall."""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request


logger = logging.getLogger(__name__)


class GiteeRerankClient:
    def __init__(self, base_url, api_key, model="Qwen3-Reranker-0.6B", timeout_seconds=3.0):
        self.base_url = str(base_url or "").strip().rstrip("/")
        self.api_key = str(api_key or "").strip()
        self.model = str(model or "").strip() or "Qwen3-Reranker-0.6B"
        self.timeout_seconds = float(timeout_seconds or 3.0)
        if not self.base_url:
            raise ValueError("rerank base_url must not be blank")
        if not self.api_key:
            raise ValueError("rerank api_key must not be blank")

    def rerank(self, query, documents, top_n=3):
        query = str(query or "").strip()
        documents = [str(document or "").strip() for document in documents or []]
        if not query or not documents:
            return {}
        payload = {
            "model": self.model,
            "query": query,
            "top_n": max(1, min(int(top_n or 1), len(documents))),
            "documents": documents,
        }
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        request = urllib.request.Request(
            f"{self.base_url}/rerank",
            data=data,
            headers=headers,
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                body = response.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
            raise RuntimeError(f"rerank request failed: HTTP {exc.code}; {detail[:300]}") from exc
        except (urllib.error.URLError, OSError) as exc:
            raise RuntimeError(f"rerank request failed: {exc}") from exc
        try:
            parsed = json.loads(body)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"rerank response is not valid JSON: {body[:300]}") from exc
        return self._scores_from_response(parsed)

    @staticmethod
    def _scores_from_response(payload):
        results = payload.get("results") if isinstance(payload, dict) else None
        if results is None and isinstance(payload, dict):
            results = payload.get("data")
        scores = {}
        for item in results or []:
            if not isinstance(item, dict):
                continue
            try:
                index = int(item.get("index"))
                score = float(item.get("relevance_score", item.get("score")))
            except (TypeError, ValueError):
                continue
            scores[index] = score
        return scores


class MemoryReranker:
    def __init__(self, client=None, enabled=False, provider="gitee"):
        self.client = client
        self.enabled = bool(enabled)
        self.provider = provider

    def rerank(self, query, items, top_n=3):
        items = list(items or [])
        if not self.enabled or not self.client or len(items) <= 1:
            return items
        documents = [self._document(item) for item in items]
        try:
            scores = self.client.rerank(query, documents, top_n=min(len(items), max(int(top_n or 1), 1)))
        except Exception as exc:
            logger.warning("Memory rerank failed; falling back to vector order: %s", exc)
            return items
        if not scores:
            return items
        enriched = []
        for index, item in enumerate(items):
            next_item = dict(item)
            if index in scores:
                next_item["rerank_score"] = scores[index]
                next_item["rerank_provider"] = self.provider
            enriched.append((scores.get(index, float("-inf")), -index, next_item))
        enriched.sort(reverse=True)
        return [item for _, _, item in enriched]

    @staticmethod
    def _document(item):
        metadata = item.get("metadata") or {}
        parts = [
            f"记忆：{item.get('memory_text') or ''}",
            f"召回扩写：{item.get('memory_recall_text') or ''}",
            f"类型：{metadata.get('memory_type') or ''}",
            f"证据分：{metadata.get('evidence_score') or ''}",
            f"互动价值：{metadata.get('interaction_value_score') or ''}",
        ]
        return "\n".join(part for part in parts if part.strip() and not part.endswith("："))
