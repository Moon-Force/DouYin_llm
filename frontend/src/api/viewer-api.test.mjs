import assert from "node:assert/strict";

import {
  deleteViewerMemoryRequest,
  deleteViewerNoteRequest,
  loadViewerDetailsRequest,
  loadViewerMemoryLogsRequest,
  saveViewerMemoryRequest,
  saveViewerNoteRequest,
  updateViewerMemoryStatusRequest,
} from "./viewer-api.js";

const originalFetch = global.fetch;

global.fetch = async (url, options = {}) => ({
  ok: true,
  async json() {
    return { url, options };
  },
});

try {
  const detail = await loadViewerDetailsRequest({
    roomId: "841354217566",
    viewerId: "id:viewer-1",
    nickname: "A Ming",
  });
  assert.equal(
    detail.url,
    "/api/viewer?room_id=841354217566&viewer_id=id%3Aviewer-1&nickname=A+Ming",
  );

  const note = await saveViewerNoteRequest({
    roomId: "841354217566",
    viewerId: "id:viewer-1",
    content: "regular fan",
    isPinned: true,
    noteId: "n1",
  });
  assert.equal(note.url, "/api/viewer/notes");
  assert.equal(note.options.method, "POST");
  assert.deepEqual(JSON.parse(note.options.body), {
    room_id: "841354217566",
    viewer_id: "id:viewer-1",
    content: "regular fan",
    is_pinned: true,
    note_id: "n1",
  });

  const memory = await saveViewerMemoryRequest("/api/viewer/memories", "POST", {
    room_id: "841354217566",
    viewer_id: "id:viewer-1",
    memory_text: "likes ramen",
  });
  assert.equal(memory.options.method, "POST");

  const status = await updateViewerMemoryStatusRequest("m1", "invalidate", "expired");
  assert.equal(status.url, "/api/viewer/memories/m1/invalidate");
  assert.equal(status.options.method, "POST");
  assert.deepEqual(JSON.parse(status.options.body), { reason: "expired" });

  const deletedMemory = await deleteViewerMemoryRequest("m1", "expired");
  assert.equal(deletedMemory.url, "/api/viewer/memories/m1");
  assert.equal(deletedMemory.options.method, "DELETE");

  const deletedNote = await deleteViewerNoteRequest("n1");
  assert.equal(deletedNote.url, "/api/viewer/notes/n1");
  assert.equal(deletedNote.options.method, "DELETE");

  const logs = await loadViewerMemoryLogsRequest("m1");
  assert.equal(logs.url, "/api/viewer/memories/m1/logs?limit=20");
} finally {
  global.fetch = originalFetch;
}
