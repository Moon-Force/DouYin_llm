"""Transport client for OpenAI-compatible memory extraction endpoints."""

from __future__ import annotations

import json
import urllib.request


class MemoryExtractorClient:
    """Thin HTTP wrapper around an OpenAI-compatible chat completions endpoint."""

    def __init__(self, settings):
        self._base_url = str(settings.memory_extractor_base_url).rstrip("/")
        self._model = str(settings.memory_extractor_model)
        self._max_tokens = int(settings.memory_extractor_max_tokens)
        self._timeout_seconds = float(settings.memory_extractor_timeout_seconds)
        self._api_key = str(settings.memory_extractor_api_key or "")

    def infer_json(self, system_prompt, user_prompt):
        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "max_tokens": self._max_tokens,
        }
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")

        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"

        request = urllib.request.Request(
            f"{self._base_url}/chat/completions",
            data=data,
            headers=headers,
            method="POST",
        )

        with urllib.request.urlopen(request, timeout=self._timeout_seconds) as response:
            return response.read().decode("utf-8")
