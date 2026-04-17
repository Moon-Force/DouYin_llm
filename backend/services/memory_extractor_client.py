"""Transport client for OpenAI-compatible memory extraction endpoints."""

from __future__ import annotations

import json
from typing import Protocol
import urllib.error
import urllib.request


class MemoryExtractorSettings(Protocol):
    memory_extractor_base_url: str
    memory_extractor_model: str
    memory_extractor_max_tokens: int
    memory_extractor_timeout_seconds: float
    memory_extractor_api_key: str


class MemoryExtractorClient:
    """Thin HTTP wrapper around an OpenAI-compatible chat completions endpoint."""

    def __init__(self, settings: MemoryExtractorSettings):
        self._base_url = str(settings.memory_extractor_base_url or "").strip().rstrip("/")
        self._model = str(settings.memory_extractor_model or "").strip()
        self._max_tokens = int(settings.memory_extractor_max_tokens)
        self._timeout_seconds = float(settings.memory_extractor_timeout_seconds)
        self._api_key = str(settings.memory_extractor_api_key or "").strip()

        if not self._base_url:
            raise ValueError("memory_extractor_base_url must not be blank")
        if not self._model:
            raise ValueError("memory_extractor_model must not be blank")
        if self._max_tokens <= 0:
            raise ValueError("memory_extractor_max_tokens must be > 0")
        if self._timeout_seconds <= 0:
            raise ValueError("memory_extractor_timeout_seconds must be > 0")

    def infer_json(self, system_prompt, user_prompt):
        endpoint = f"{self._base_url}/chat/completions"
        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "max_tokens": self._max_tokens,
            "temperature": 0,
        }
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")

        headers = {
            "Content-Type": "application/json; charset=utf-8",
            "Accept": "application/json",
        }
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"

        request = urllib.request.Request(
            endpoint,
            data=data,
            headers=headers,
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=self._timeout_seconds) as response:
                raw_body = response.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as exc:
            body = self._read_http_error_body(exc)
            message = f"memory extractor request failed for {endpoint}: HTTP {exc.code}"
            if body:
                message = f"{message}; body: {self._snippet(body)}"
            raise ValueError(message) from exc
        except urllib.error.URLError as exc:
            raise ValueError(f"memory extractor request failed for {endpoint}: {exc.reason}") from exc
        except OSError as exc:
            raise ValueError(f"memory extractor request failed for {endpoint}: {exc}") from exc

        try:
            response_payload = json.loads(raw_body)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"memory extractor response was not valid JSON for {endpoint}; body: {self._snippet(raw_body)}"
            ) from exc

        try:
            content = response_payload["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ValueError(
                f"memory extractor response missing choices[0].message.content for {endpoint}; "
                f"body: {self._snippet(raw_body)}"
            ) from exc

        if not isinstance(content, str):
            raise ValueError(
                f"memory extractor response missing choices[0].message.content for {endpoint}; "
                f"body: {self._snippet(raw_body)}"
            )

        try:
            json.loads(content)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"assistant message content is not valid JSON text for {endpoint}; "
                f"content: {self._snippet(content)}"
            ) from exc

        return content

    @staticmethod
    def _read_http_error_body(error: urllib.error.HTTPError):
        try:
            raw = error.read()
        except Exception:
            return ""
        if not raw:
            return ""
        return raw.decode("utf-8", errors="replace")

    @staticmethod
    def _snippet(text, limit=200):
        return str(text).strip().replace("\r", " ").replace("\n", " ")[:limit]
