"""Transport client for OpenAI-compatible memory extraction endpoints."""

from __future__ import annotations

import json
import urllib.request


class MemoryExtractorClient:
    """Thin HTTP wrapper around an OpenAI-compatible chat completions endpoint."""

    def __init__(self, settings):
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
            f"{self._base_url}/chat/completions",
            data=data,
            headers=headers,
            method="POST",
        )

        with urllib.request.urlopen(request, timeout=self._timeout_seconds) as response:
            response_payload = json.loads(response.read().decode("utf-8"))
        try:
            return response_payload["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ValueError("response missing choices[0].message.content") from exc
