import { computed, ref } from "vue";
import { defineStore } from "pinia";

const MAX_EVENTS = 30;
const MAX_SUGGESTIONS = 12;

const EVENT_FILTERS = [
  { value: "comment", label: "弹幕" },
  { value: "gift", label: "礼物" },
  { value: "follow", label: "关注" },
  { value: "member", label: "进场" },
  { value: "like", label: "点赞" },
  { value: "system", label: "系统" },
];

const DEFAULT_VISIBLE_EVENT_TYPES = EVENT_FILTERS.map((filter) => filter.value);
const FILTER_STORAGE_KEY = "live-prompter:selected-event-types";
const THEME_STORAGE_KEY = "live-prompter:theme";

function createEmptyStats(roomId) {
  return {
    room_id: roomId,
    total_events: 0,
    comments: 0,
    gifts: 0,
    likes: 0,
    members: 0,
    follows: 0,
  };
}

function normalizeSelectedEventTypes(eventTypes) {
  const validValues = new Set(EVENT_FILTERS.map((filter) => filter.value));
  const normalized = Array.isArray(eventTypes)
    ? eventTypes.filter((eventType) => validValues.has(eventType))
    : [];

  return normalized.length > 0 ? [...new Set(normalized)] : [...DEFAULT_VISIBLE_EVENT_TYPES];
}

function loadSelectedEventTypes() {
  if (typeof window === "undefined") {
    return [...DEFAULT_VISIBLE_EVENT_TYPES];
  }

  try {
    const rawValue = window.localStorage.getItem(FILTER_STORAGE_KEY);
    return normalizeSelectedEventTypes(rawValue ? JSON.parse(rawValue) : DEFAULT_VISIBLE_EVENT_TYPES);
  } catch {
    return [...DEFAULT_VISIBLE_EVENT_TYPES];
  }
}

function loadTheme() {
  if (typeof window === "undefined") {
    return "dark";
  }

  try {
    return window.localStorage.getItem(THEME_STORAGE_KEY) === "light" ? "light" : "dark";
  } catch {
    return "dark";
  }
}

function applyTheme(theme) {
  if (typeof document === "undefined") {
    return;
  }

  document.documentElement.dataset.theme = theme;
}

export const useLiveStore = defineStore("live", () => {
  const roomId = ref("");
  const roomDraft = ref("");
  const theme = ref(loadTheme());
  const isSwitchingRoom = ref(false);
  const roomError = ref("");
  const connectionState = ref("idle");
  const eventFilters = ref(EVENT_FILTERS);
  const selectedEventTypes = ref(loadSelectedEventTypes());
  const modelStatus = ref({
    mode: "heuristic",
    model: "heuristic",
    backend: "local",
    last_result: "idle",
    last_error: "",
    updated_at: 0,
  });
  const stats = ref(createEmptyStats(""));
  const events = ref([]);
  const suggestions = ref([]);
  const isViewerWorkbenchOpen = ref(false);
  const viewerWorkbench = ref({
    viewer: null,
    loading: false,
    error: "",
  });
  const viewerNoteDraft = ref("");
  const viewerNotePinned = ref(false);
  const editingViewerNoteId = ref("");
  const isSavingViewerNote = ref(false);
  let eventSource;
  let viewerWorkbenchRequestId = 0;
  let hotCleanupRegistered = false;

  const activeSuggestion = computed(() => suggestions.value[0] || null);
  const activeSourceEvent = computed(() => {
    if (!activeSuggestion.value) {
      return null;
    }

    const sourceEventIds = new Set([
      activeSuggestion.value.event_id,
      ...(activeSuggestion.value.source_events || []),
    ]);

    return events.value.find((event) => sourceEventIds.has(event.event_id)) || null;
  });
  const nextThemeLabel = computed(() => (theme.value === "dark" ? "切换白色" : "切换黑色"));
  const areAllEventTypesSelected = computed(
    () => selectedEventTypes.value.length === EVENT_FILTERS.length,
  );
  const filteredEvents = computed(() =>
    events.value.filter((event) => selectedEventTypes.value.includes(event.event_type)),
  );

  function persistSelectedEventTypes() {
    if (typeof window === "undefined") {
      return;
    }

    try {
      window.localStorage.setItem(FILTER_STORAGE_KEY, JSON.stringify(selectedEventTypes.value));
    } catch {
      // Ignore storage write failures so filtering still works in restricted environments.
    }
  }

  function persistTheme() {
    if (typeof window === "undefined") {
      return;
    }

    try {
      window.localStorage.setItem(THEME_STORAGE_KEY, theme.value);
    } catch {
      // Ignore storage write failures so theme toggling still works in restricted environments.
    }
  }

  function hydrateSnapshot(payload) {
    roomId.value = `${payload.room_id ?? ""}`;
    stats.value = payload.stats || createEmptyStats(roomId.value);
    modelStatus.value = payload.model_status || modelStatus.value;
    events.value = payload.recent_events || [];
    suggestions.value = payload.recent_suggestions || [];
    if (!roomId.value) {
      connectionState.value = "idle";
    }
  }

  function closeStream() {
    if (eventSource) {
      eventSource.close();
      eventSource = undefined;
    }
  }

  function isViewerRequestStale(requestId) {
    return requestId !== viewerWorkbenchRequestId;
  }

  function getViewerErrorMessage(error, fallback) {
    return error instanceof Error ? error.message : fallback;
  }

  async function getResponseError(response, fallback) {
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
    }

    const query = new URLSearchParams({
      room_id: payload.roomId,
      viewer_id: payload.viewerId,
      nickname: payload.nickname ?? "",
    });

    try {
      if (isViewerRequestStale(requestId)) {
        return null;
      }

      const response = await fetch(`/api/viewer?${query.toString()}`);

      if (isViewerRequestStale(requestId)) {
        return null;
      }

      if (!response.ok) {
        throw new Error(await getResponseError(response, "Failed to load viewer"));
      }

      const viewer = await response.json();

      if (isViewerRequestStale(requestId)) {
        return null;
      }

      viewerWorkbench.value.viewer = viewer;
      return viewer;
    } catch (error) {
      if (isViewerRequestStale(requestId)) {
        return null;
      }

      viewerWorkbench.value.error = getViewerErrorMessage(error, "Failed to load viewer");
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

  function setRoomDraft(value) {
    roomDraft.value = `${value ?? ""}`;
  }

  function setTheme(nextTheme) {
    theme.value = nextTheme === "light" ? "light" : "dark";
    applyTheme(theme.value);
    persistTheme();
  }

  function toggleTheme() {
    setTheme(theme.value === "dark" ? "light" : "dark");
  }

  async function bootstrap(targetRoomId = roomId.value) {
    const normalizedRoomId = `${targetRoomId ?? ""}`.trim();
    const url = normalizedRoomId
      ? `/api/bootstrap?${new URLSearchParams({ room_id: normalizedRoomId }).toString()}`
      : "/api/bootstrap";
    const response = await fetch(url);
    if (!response.ok) {
      throw new Error(response.statusText || "Failed to bootstrap live state");
    }
    const payload = await response.json();
    hydrateSnapshot(payload);
  }

  function ingestEvent(event) {
    events.value = [event, ...events.value].slice(0, MAX_EVENTS);
  }

  function ingestSuggestion(suggestion) {
    suggestions.value = [suggestion, ...suggestions.value].slice(0, MAX_SUGGESTIONS);
  }

  function parseSseData(rawData, label) {
    if (typeof rawData !== "string") {
      return null;
    }

    try {
      return JSON.parse(rawData);
    } catch (error) {
      console.error(`Failed to parse ${label || "SSE"} payload`, error);
      return null;
    }
  }

  function connect(targetRoomId = roomId.value) {
    closeStream();
    const normalizedRoomId = `${targetRoomId ?? ""}`.trim();
    if (!normalizedRoomId) {
      connectionState.value = "idle";
      return;
    }

    const query = new URLSearchParams({ room_id: normalizedRoomId });
    eventSource = new EventSource(`/api/events/stream?${query.toString()}`);

    connectionState.value = "connecting";

    eventSource.onopen = () => {
      connectionState.value = "live";
      roomError.value = "";
    };

    eventSource.onerror = () => {
      connectionState.value = "reconnecting";
    };

    eventSource.addEventListener("event", (message) => {
      const payload = parseSseData(message.data, "event");
      if (payload) {
        ingestEvent(payload);
      }
    });

    eventSource.addEventListener("suggestion", (message) => {
      const payload = parseSseData(message.data, "suggestion");
      if (payload) {
        ingestSuggestion(payload);
      }
    });

    eventSource.addEventListener("stats", (message) => {
      const payload = parseSseData(message.data, "stats");
      if (payload) {
        stats.value = payload;
      }
    });

    eventSource.addEventListener("model_status", (message) => {
      const payload = parseSseData(message.data, "model_status");
      if (payload) {
        modelStatus.value = payload;
      }
    });
  }

  async function switchRoom(nextRoomId = roomDraft.value) {
    const targetRoomId = `${nextRoomId ?? ""}`.trim();
    if (!targetRoomId) {
      roomError.value = "请输入房间号";
      return;
    }

    if (targetRoomId === roomId.value) {
      roomDraft.value = "";
      roomError.value = "";
      return;
    }

    isSwitchingRoom.value = true;
    roomError.value = "";
    connectionState.value = "switching";
    closeStream();

    try {
      const response = await fetch("/api/room", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ room_id: targetRoomId }),
      });

      if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        throw new Error(payload.detail || "切换房间失败");
      }

      const payload = await response.json();
      closeViewerWorkbench();
      hydrateSnapshot(payload);
      roomDraft.value = "";
      connect(payload.room_id || targetRoomId);
    } catch (error) {
      roomError.value = error instanceof Error ? error.message : "切换房间失败";
      await bootstrap(roomId.value);
      connect(roomId.value);
    } finally {
      isSwitchingRoom.value = false;
    }
  }

  function toggleEventType(eventType) {
    if (selectedEventTypes.value.includes(eventType)) {
      if (selectedEventTypes.value.length === 1) {
        return;
      }

      selectedEventTypes.value = selectedEventTypes.value.filter((value) => value !== eventType);
      persistSelectedEventTypes();
      return;
    }

    selectedEventTypes.value = normalizeSelectedEventTypes([
      ...selectedEventTypes.value,
      eventType,
    ]);
    persistSelectedEventTypes();
  }

  function selectAllEventTypes() {
    selectedEventTypes.value = [...DEFAULT_VISIBLE_EVENT_TYPES];
    persistSelectedEventTypes();
  }

  function clearEvents() {
    events.value = [];
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
    const body = {
      room_id: payload.roomId,
      viewer_id: payload.viewerId,
      content: payload.content,
      is_pinned: payload.isPinned ?? false,
    };

    if (payload.noteId) {
      body.note_id = payload.noteId;
    }

    const response = await fetch("/api/viewer/notes", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      const errorText = await getResponseError(response, "Failed to save viewer note");
      throw new Error(errorText);
    }

    return response.json();
  }

  function resetViewerNoteEditor() {
    viewerNoteDraft.value = "";
    viewerNotePinned.value = false;
    editingViewerNoteId.value = "";
  }

  function resetViewerWorkbenchState() {
    viewerWorkbench.value.viewer = null;
    viewerWorkbench.value.loading = false;
    viewerWorkbench.value.error = "";
    resetViewerNoteEditor();
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
  }

  async function saveActiveViewerNote() {
    if (!viewerWorkbench.value.viewer || isSavingViewerNote.value) {
      return;
    }

    const currentViewer = viewerWorkbench.value.viewer;
    if (!currentViewer.viewer_id) {
      viewerWorkbench.value.error = "Viewer id is required to save notes";
      return;
    }
    if (!viewerNoteDraft.value.trim()) {
      viewerWorkbench.value.error = "Note content is required";
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
        viewerWorkbench.value.error = getViewerErrorMessage(error, "Failed to save viewer note");
      }
    } finally {
      isSavingViewerNote.value = false;
    }
  }

  async function deleteViewerNoteRequest(noteId) {
    const response = await fetch(`/api/viewer/notes/${noteId}`, {
      method: "DELETE",
    });

    if (!response.ok) {
      const errorText = await getResponseError(response, "Failed to delete viewer note");
      throw new Error(errorText);
    }
  }

  async function deleteViewerNote(noteId) {
    if (!noteId || !viewerWorkbench.value.viewer || isSavingViewerNote.value) {
      return;
    }

    const currentViewer = viewerWorkbench.value.viewer;
    if (!currentViewer.viewer_id) {
      viewerWorkbench.value.error = "Viewer id is required to delete notes";
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
        viewerWorkbench.value.error = getViewerErrorMessage(error, "Failed to delete viewer note");
      }
    } finally {
      isSavingViewerNote.value = false;
    }
  }

  if (
    typeof import.meta !== "undefined" &&
    import.meta.hot &&
    !hotCleanupRegistered
  ) {
    hotCleanupRegistered = true;
    import.meta.hot.dispose(() => {
      closeStream();
    });
  }

  applyTheme(theme.value);

  return {
    roomId,
    roomDraft,
    theme,
    nextThemeLabel,
    isSwitchingRoom,
    roomError,
    connectionState,
    selectedEventTypes,
    eventFilters,
    modelStatus,
    stats,
    areAllEventTypesSelected,
    events,
    filteredEvents,
    suggestions,
    activeSuggestion,
    activeSourceEvent,
    bootstrap,
    connect,
    setRoomDraft,
    setTheme,
    toggleTheme,
    switchRoom,
    toggleEventType,
    selectAllEventTypes,
    clearEvents,
    isViewerWorkbenchOpen,
    viewerWorkbench,
    openViewerWorkbench,
    saveViewerNote,
    closeViewerWorkbench,
    closeStream,
    viewerNoteDraft,
    viewerNotePinned,
    editingViewerNoteId,
    isSavingViewerNote,
    setViewerNoteDraft,
    toggleViewerNotePinned,
    beginEditingViewerNote,
    saveActiveViewerNote,
    deleteViewerNote,
  };
});
