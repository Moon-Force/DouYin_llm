async function readErrorMessage(response, fallback) {
  try {
    const payload = await response.json();
    if (payload?.detail) {
      return String(payload.detail);
    }
  } catch {
    // Ignore JSON parsing failures and fall back to status text.
  }

  return response.statusText || fallback;
}

export async function bootstrapLiveState(roomId = "") {
  const normalizedRoomId = `${roomId ?? ""}`.trim();
  const url = normalizedRoomId
    ? `/api/bootstrap?${new URLSearchParams({ room_id: normalizedRoomId }).toString()}`
    : "/api/bootstrap";
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(response.statusText || "Failed to bootstrap live state");
  }
  return response.json();
}

export async function switchLiveRoom(roomId) {
  const response = await fetch("/api/room", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ room_id: roomId }),
  });

  if (!response.ok) {
    throw new Error(await readErrorMessage(response, "errors.roomSwitchFailed"));
  }

  return response.json();
}

export async function loadLlmSettingsRequest() {
  const response = await fetch("/api/settings/llm");
  if (!response.ok) {
    throw new Error("errors.llmSettingsLoadFailed");
  }
  return response.json();
}

export async function saveLlmSettingsRequest({
  model,
  systemPrompt,
  embeddingModel,
  memoryExtractorModel,
}) {
  const response = await fetch("/api/settings/llm", {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      model,
      system_prompt: systemPrompt,
      embedding_model: embeddingModel,
      memory_extractor_model: memoryExtractorModel,
    }),
  });

  if (!response.ok) {
    throw new Error(await readErrorMessage(response, "errors.llmSettingsSaveFailed"));
  }

  return response.json();
}
