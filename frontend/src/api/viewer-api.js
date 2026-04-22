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

export async function loadViewerDetailsRequest({ roomId, viewerId, nickname }) {
  const query = new URLSearchParams({
    room_id: roomId,
    viewer_id: viewerId,
    nickname: nickname ?? "",
  });
  const response = await fetch(`/api/viewer?${query.toString()}`);

  if (!response.ok) {
    throw new Error(await readErrorMessage(response, "errors.viewerLoadFailed"));
  }

  return response.json();
}

export async function saveViewerNoteRequest({ roomId, viewerId, content, isPinned = false, noteId }) {
  const body = {
    room_id: roomId,
    viewer_id: viewerId,
    content,
    is_pinned: isPinned,
  };

  if (noteId) {
    body.note_id = noteId;
  }

  const response = await fetch("/api/viewer/notes", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    throw new Error(await readErrorMessage(response, "errors.viewerNoteSaveFailed"));
  }

  return response.json();
}

export async function deleteViewerNoteRequest(noteId) {
  const response = await fetch(`/api/viewer/notes/${noteId}`, {
    method: "DELETE",
  });

  if (!response.ok) {
    throw new Error(await readErrorMessage(response, "errors.viewerNoteDeleteFailed"));
  }

  return response.json();
}

export async function saveViewerMemoryRequest(url, method, body) {
  const response = await fetch(url, {
    method,
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    throw new Error(await readErrorMessage(response, "errors.viewerMemorySaveFailed"));
  }

  return response.json();
}

export async function updateViewerMemoryStatusRequest(memoryId, action, reason) {
  const response = await fetch(`/api/viewer/memories/${memoryId}/${action}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ reason }),
  });

  if (!response.ok) {
    throw new Error(await readErrorMessage(response, "errors.viewerMemoryStatusFailed"));
  }

  return response.json();
}

export async function deleteViewerMemoryRequest(memoryId, reason) {
  const response = await fetch(`/api/viewer/memories/${memoryId}`, {
    method: "DELETE",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ reason }),
  });

  if (!response.ok) {
    throw new Error(await readErrorMessage(response, "errors.viewerMemoryDeleteFailed"));
  }

  return response.json();
}

export async function loadViewerMemoryLogsRequest(memoryId) {
  const response = await fetch(`/api/viewer/memories/${memoryId}/logs?limit=20`);

  if (!response.ok) {
    throw new Error(await readErrorMessage(response, "errors.viewerMemoryLogsLoadFailed"));
  }

  return response.json();
}
