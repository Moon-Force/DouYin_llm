import { ref } from "vue";
import { defineStore } from "pinia";

import {
  deleteViewerMemoryRequest,
  deleteViewerNoteRequest,
  loadViewerDetailsRequest,
  loadViewerMemoryLogsRequest,
  saveViewerMemoryRequest,
  saveViewerNoteRequest,
  updateViewerMemoryStatusRequest,
} from "../api/viewer-api.js";

export const useViewerWorkbenchStore = defineStore("viewerWorkbench", () => {
  const isViewerWorkbenchOpen = ref(false);
  const viewerWorkbench = ref({
    viewer: null,
    loading: false,
    error: "",
  });
  const viewerNoteDraft = ref("");
  const viewerNotePinned = ref(false);
  const editingViewerNoteId = ref("");
  const isViewerNoteEditorOpen = ref(false);
  const isSavingViewerNote = ref(false);
  const viewerMemoryDraft = ref({
    memoryText: "",
    memoryType: "fact",
    isPinned: false,
    correctionReason: "",
  });
  const editingViewerMemoryId = ref("");
  const isViewerMemoryEditorOpen = ref(false);
  const isSavingViewerMemory = ref(false);
  const viewerMemoryLogsById = ref({});
  let viewerWorkbenchRequestId = 0;

  function isViewerRequestStale(requestId) {
    return requestId !== viewerWorkbenchRequestId;
  }

  function getViewerErrorMessage(error, fallback) {
    return error instanceof Error ? error.message : fallback;
  }

  function resetViewerNoteEditor() {
    viewerNoteDraft.value = "";
    viewerNotePinned.value = false;
    editingViewerNoteId.value = "";
    isViewerNoteEditorOpen.value = false;
  }

  function resetViewerMemoryEditor() {
    viewerMemoryDraft.value = {
      memoryText: "",
      memoryType: "fact",
      isPinned: false,
      correctionReason: "",
    };
    editingViewerMemoryId.value = "";
    isViewerMemoryEditorOpen.value = false;
  }

  function resetViewerWorkbenchState() {
    viewerWorkbench.value.viewer = null;
    viewerWorkbench.value.loading = false;
    viewerWorkbench.value.error = "";
    resetViewerNoteEditor();
    resetViewerMemoryEditor();
    viewerMemoryLogsById.value = {};
  }

  async function loadViewerDetails(payload, requestId, options = {}) {
    const {
      clearError = true,
      resetEditor = false,
      resetViewer = true,
      showLoading = true,
    } = options;

    if (isViewerRequestStale(requestId)) {
      return null;
    }

    if (showLoading) {
      viewerWorkbench.value.loading = true;
    }

    if (clearError) {
      viewerWorkbench.value.error = "";
    }

    if (resetViewer) {
      viewerWorkbench.value.viewer = null;
    }

    if (resetEditor) {
      resetViewerNoteEditor();
      resetViewerMemoryEditor();
      viewerMemoryLogsById.value = {};
    }

    try {
      if (isViewerRequestStale(requestId)) {
        return null;
      }

      const viewer = await loadViewerDetailsRequest({
        roomId: payload.roomId,
        viewerId: payload.viewerId,
        nickname: payload.nickname ?? "",
      });

      if (isViewerRequestStale(requestId)) {
        return null;
      }

      viewerWorkbench.value.viewer = viewer;
      return viewer;
    } catch (error) {
      if (isViewerRequestStale(requestId)) {
        return null;
      }

      viewerWorkbench.value.error = getViewerErrorMessage(error, "errors.viewerLoadFailed");
      return null;
    } finally {
      if (!isViewerRequestStale(requestId)) {
        viewerWorkbench.value.loading = false;
      }
    }
  }

  async function refreshViewerWorkbench() {
    if (!isViewerWorkbenchOpen.value || !viewerWorkbench.value.viewer) {
      return;
    }

    const currentViewer = viewerWorkbench.value.viewer;
    const requestId = ++viewerWorkbenchRequestId;

    await loadViewerDetails(
      {
        roomId: currentViewer.room_id,
        viewerId: currentViewer.viewer_id,
        nickname: currentViewer.nickname ?? "",
      },
      requestId,
      {
        clearError: true,
        resetEditor: false,
        resetViewer: false,
        showLoading: false,
      },
    );
  }

  async function openViewerWorkbench({ roomId, viewerId, nickname }) {
    isViewerWorkbenchOpen.value = true;
    const requestId = ++viewerWorkbenchRequestId;

    await loadViewerDetails(
      { roomId, viewerId, nickname },
      requestId,
      { clearError: true, resetEditor: true, resetViewer: true, showLoading: true },
    );
  }

  async function saveViewerNote(payload) {
    return saveViewerNoteRequest(payload);
  }

  function closeViewerWorkbench() {
    isViewerWorkbenchOpen.value = false;
    viewerWorkbenchRequestId += 1;
    resetViewerWorkbenchState();
  }

  function setViewerNoteDraft(value) {
    viewerNoteDraft.value = `${value ?? ""}`;
  }

  function toggleViewerNotePinned() {
    if (isSavingViewerNote.value) {
      return;
    }
    viewerNotePinned.value = !viewerNotePinned.value;
  }

  function openNewViewerNote() {
    if (isSavingViewerNote.value) {
      return;
    }
    viewerNoteDraft.value = "";
    viewerNotePinned.value = false;
    editingViewerNoteId.value = "";
    isViewerNoteEditorOpen.value = true;
  }

  function closeViewerNoteEditor() {
    if (isSavingViewerNote.value) {
      return;
    }
    resetViewerNoteEditor();
  }

  function beginEditingViewerNote(note) {
    if (isSavingViewerNote.value) {
      return;
    }

    if (!note) {
      resetViewerNoteEditor();
      return;
    }

    viewerNoteDraft.value = note.content || "";
    viewerNotePinned.value = Boolean(note.is_pinned);
    editingViewerNoteId.value = note.note_id || "";
    isViewerNoteEditorOpen.value = true;
  }

  function setViewerMemoryDraft(patch) {
    viewerMemoryDraft.value = {
      ...viewerMemoryDraft.value,
      ...patch,
    };
  }

  function openNewViewerMemory() {
    if (isSavingViewerMemory.value) {
      return;
    }
    viewerMemoryDraft.value = {
      memoryText: "",
      memoryType: "fact",
      isPinned: false,
      correctionReason: "",
    };
    editingViewerMemoryId.value = "";
    isViewerMemoryEditorOpen.value = true;
  }

  function closeViewerMemoryEditor() {
    if (isSavingViewerMemory.value) {
      return;
    }
    resetViewerMemoryEditor();
  }

  function beginEditingViewerMemory(memory) {
    if (isSavingViewerMemory.value) {
      return;
    }

    if (!memory) {
      resetViewerMemoryEditor();
      return;
    }

    editingViewerMemoryId.value = memory.memory_id || "";
    viewerMemoryDraft.value = {
      memoryText: memory.memory_text || "",
      memoryType: memory.memory_type || "fact",
      isPinned: Boolean(memory.is_pinned),
      correctionReason: memory.correction_reason || "",
    };
    isViewerMemoryEditorOpen.value = true;
  }

  async function saveActiveViewerNote() {
    if (!viewerWorkbench.value.viewer || isSavingViewerNote.value) {
      return;
    }

    const currentViewer = viewerWorkbench.value.viewer;
    if (!currentViewer.viewer_id) {
      viewerWorkbench.value.error = "errors.viewerIdRequiredToSaveNotes";
      return;
    }
    if (!viewerNoteDraft.value.trim()) {
      viewerWorkbench.value.error = "errors.viewerNoteRequired";
      return;
    }
    const requestId = viewerWorkbenchRequestId;
    isSavingViewerNote.value = true;
    viewerWorkbench.value.error = "";

    try {
      await saveViewerNote({
        roomId: currentViewer.room_id,
        viewerId: currentViewer.viewer_id,
        nickname: currentViewer.nickname ?? "",
        content: viewerNoteDraft.value,
        isPinned: viewerNotePinned.value,
        noteId: editingViewerNoteId.value || undefined,
      });
      if (
        isViewerRequestStale(requestId) ||
        !viewerWorkbench.value.viewer ||
        viewerWorkbench.value.viewer.viewer_id !== currentViewer.viewer_id
      ) {
        return;
      }
      resetViewerNoteEditor();
      await refreshViewerWorkbench();
    } catch (error) {
      if (!isViewerRequestStale(requestId)) {
        viewerWorkbench.value.error = getViewerErrorMessage(error, "errors.viewerNoteSaveFailed");
      }
    } finally {
      isSavingViewerNote.value = false;
    }
  }

  async function deleteViewerNote(noteId) {
    if (!noteId || !viewerWorkbench.value.viewer || isSavingViewerNote.value) {
      return;
    }

    const currentViewer = viewerWorkbench.value.viewer;
    if (!currentViewer.viewer_id) {
      viewerWorkbench.value.error = "errors.viewerIdRequiredToDeleteNotes";
      return;
    }
    const requestId = viewerWorkbenchRequestId;
    isSavingViewerNote.value = true;
    viewerWorkbench.value.error = "";

    try {
      await deleteViewerNoteRequest(noteId);
      if (
        isViewerRequestStale(requestId) ||
        !viewerWorkbench.value.viewer ||
        viewerWorkbench.value.viewer.viewer_id !== currentViewer.viewer_id
      ) {
        return;
      }
      if (editingViewerNoteId.value === noteId) {
        resetViewerNoteEditor();
      }
      await refreshViewerWorkbench();
    } catch (error) {
      if (!isViewerRequestStale(requestId)) {
        viewerWorkbench.value.error = getViewerErrorMessage(error, "errors.viewerNoteDeleteFailed");
      }
    } finally {
      isSavingViewerNote.value = false;
    }
  }

  async function saveActiveViewerMemory() {
    if (!viewerWorkbench.value.viewer || isSavingViewerMemory.value) {
      return;
    }

    const currentViewer = viewerWorkbench.value.viewer;
    if (!currentViewer.viewer_id) {
      viewerWorkbench.value.error = "errors.viewerIdRequiredToSaveMemories";
      return;
    }
    if (!viewerMemoryDraft.value.memoryText.trim()) {
      viewerWorkbench.value.error = "errors.viewerMemoryRequired";
      return;
    }

    const url = editingViewerMemoryId.value
      ? `/api/viewer/memories/${editingViewerMemoryId.value}`
      : "/api/viewer/memories";
    const method = editingViewerMemoryId.value ? "PUT" : "POST";
    const body = editingViewerMemoryId.value
      ? {
          memory_text: viewerMemoryDraft.value.memoryText,
          memory_type: viewerMemoryDraft.value.memoryType,
          is_pinned: viewerMemoryDraft.value.isPinned,
          correction_reason: viewerMemoryDraft.value.correctionReason,
        }
      : {
          room_id: currentViewer.room_id,
          viewer_id: currentViewer.viewer_id,
          memory_text: viewerMemoryDraft.value.memoryText,
          memory_type: viewerMemoryDraft.value.memoryType,
          is_pinned: viewerMemoryDraft.value.isPinned,
          correction_reason: viewerMemoryDraft.value.correctionReason,
        };

    const requestId = viewerWorkbenchRequestId;
    isSavingViewerMemory.value = true;
    viewerWorkbench.value.error = "";

    try {
      await saveViewerMemoryRequest(url, method, body);
      if (
        isViewerRequestStale(requestId) ||
        !viewerWorkbench.value.viewer ||
        viewerWorkbench.value.viewer.viewer_id !== currentViewer.viewer_id
      ) {
        return;
      }
      resetViewerMemoryEditor();
      await refreshViewerWorkbench();
    } catch (error) {
      if (!isViewerRequestStale(requestId)) {
        viewerWorkbench.value.error = getViewerErrorMessage(error, "errors.viewerMemorySaveFailed");
      }
    } finally {
      isSavingViewerMemory.value = false;
    }
  }

  async function updateViewerMemoryStatus(memoryId, action, reason) {
    if (!memoryId || !viewerWorkbench.value.viewer || isSavingViewerMemory.value) {
      return;
    }

    const requestId = viewerWorkbenchRequestId;
    isSavingViewerMemory.value = true;
    viewerWorkbench.value.error = "";

    try {
      await updateViewerMemoryStatusRequest(memoryId, action, reason);
      if (!isViewerRequestStale(requestId)) {
        await refreshViewerWorkbench();
      }
    } catch (error) {
      if (!isViewerRequestStale(requestId)) {
        viewerWorkbench.value.error = getViewerErrorMessage(error, "errors.viewerMemoryStatusFailed");
      }
    } finally {
      isSavingViewerMemory.value = false;
    }
  }

  async function invalidateViewerMemory(memoryId, reason) {
    await updateViewerMemoryStatus(memoryId, "invalidate", reason);
  }

  async function reactivateViewerMemory(memoryId, reason) {
    await updateViewerMemoryStatus(memoryId, "reactivate", reason);
  }

  async function deleteViewerMemory(memoryId, reason) {
    if (!memoryId || !viewerWorkbench.value.viewer || isSavingViewerMemory.value) {
      return;
    }

    const currentViewer = viewerWorkbench.value.viewer;
    const requestId = viewerWorkbenchRequestId;
    isSavingViewerMemory.value = true;
    viewerWorkbench.value.error = "";

    try {
      await deleteViewerMemoryRequest(memoryId, reason);
      if (
        isViewerRequestStale(requestId) ||
        !viewerWorkbench.value.viewer ||
        viewerWorkbench.value.viewer.viewer_id !== currentViewer.viewer_id
      ) {
        return;
      }
      if (editingViewerMemoryId.value === memoryId) {
        resetViewerMemoryEditor();
      }
      await refreshViewerWorkbench();
    } catch (error) {
      if (!isViewerRequestStale(requestId)) {
        viewerWorkbench.value.error = getViewerErrorMessage(error, "errors.viewerMemoryDeleteFailed");
      }
    } finally {
      isSavingViewerMemory.value = false;
    }
  }

  async function toggleViewerMemoryPin(memory) {
    if (!memory) {
      return;
    }
    beginEditingViewerMemory(memory);
    setViewerMemoryDraft({ isPinned: !Boolean(memory.is_pinned) });
    await saveActiveViewerMemory();
  }

  async function loadViewerMemoryLogs(memoryId) {
    if (!memoryId) {
      return;
    }

    if (viewerMemoryLogsById.value[memoryId]) {
      const nextLogs = { ...viewerMemoryLogsById.value };
      delete nextLogs[memoryId];
      viewerMemoryLogsById.value = nextLogs;
      return;
    }

    viewerMemoryLogsById.value = {
      ...viewerMemoryLogsById.value,
      [memoryId]: {
        ...(viewerMemoryLogsById.value[memoryId] || {}),
        loading: true,
        error: "",
        items: viewerMemoryLogsById.value[memoryId]?.items || [],
      },
    };

    try {
      const payload = await loadViewerMemoryLogsRequest(memoryId);
      viewerMemoryLogsById.value = {
        ...viewerMemoryLogsById.value,
        [memoryId]: {
          loading: false,
          error: "",
          items: payload.items || [],
        },
      };
    } catch (error) {
      viewerMemoryLogsById.value = {
        ...viewerMemoryLogsById.value,
        [memoryId]: {
          loading: false,
          error: getViewerErrorMessage(error, "errors.viewerMemoryLogsLoadFailed"),
          items: [],
        },
      };
    }
  }

  return {
    isViewerWorkbenchOpen,
    viewerWorkbench,
    viewerNoteDraft,
    viewerNotePinned,
    editingViewerNoteId,
    isViewerNoteEditorOpen,
    isSavingViewerNote,
    viewerMemoryDraft,
    editingViewerMemoryId,
    isViewerMemoryEditorOpen,
    isSavingViewerMemory,
    viewerMemoryLogsById,
    saveViewerNote,
    openViewerWorkbench,
    closeViewerWorkbench,
    setViewerNoteDraft,
    toggleViewerNotePinned,
    openNewViewerNote,
    closeViewerNoteEditor,
    beginEditingViewerNote,
    saveActiveViewerNote,
    deleteViewerNote,
    setViewerMemoryDraft,
    openNewViewerMemory,
    closeViewerMemoryEditor,
    beginEditingViewerMemory,
    saveActiveViewerMemory,
    invalidateViewerMemory,
    reactivateViewerMemory,
    deleteViewerMemory,
    toggleViewerMemoryPin,
    loadViewerMemoryLogs,
  };
});
