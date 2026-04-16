import { computed, ref } from "vue";
import { defineStore } from "pinia";
import { translate } from "../i18n.js";

const MAX_EVENTS = 30;
const MAX_SUGGESTIONS = 12;

const EVENT_FILTERS = [
  { value: "comment", labelKey: "feed.eventType.comment" },
  { value: "gift", labelKey: "feed.eventType.gift" },
  { value: "follow", labelKey: "feed.eventType.follow" },
  { value: "member", labelKey: "feed.eventType.member" },
  { value: "like", labelKey: "feed.eventType.like" },
  { value: "system", labelKey: "feed.eventType.system" },
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
  const locale = ref("zh");
  const roomId = ref("");
  const roomDraft = ref("");
  const theme = ref(loadTheme());
  const isSwitchingRoom = ref(false);
  const roomError = ref("");
  const connectionState = ref("idle");
  const eventFilters = computed(() =>
    EVENT_FILTERS.map((filter) => ({
      ...filter,
      label: translate(locale.value, filter.labelKey),
    })),
  );
  const selectedEventTypes = ref(loadSelectedEventTypes());
  const modelStatus = ref({
    mode: "heuristic",
    model: "heuristic",
    backend: "local",
    last_result: "idle",
    last_error: "",
    updated_at: 0,
  });
  const semanticHealth = ref({
    embeddingStrict: false,
    ready: true,
    reason: "",
  });
  const llmSettings = ref({
    model: "",
    systemPrompt: "",
    defaultModel: "",
    defaultSystemPrompt: "",
  });
  const llmSettingsDraft = ref({
    model: "",
    systemPrompt: "",
  });
  const isLlmSettingsOpen = ref(false);
  const isSavingLlmSettings = ref(false);
  const llmSettingsError = ref("");
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
  const viewerMemoryDraft = ref({
    memoryText: "",
    memoryType: "fact",
    isPinned: false,
    correctionReason: "",
  });
  const editingViewerMemoryId = ref("");
  const isSavingViewerMemory = ref(false);
  const viewerMemoryLogsById = ref({});
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
  const nextThemeLabel = computed(() =>
    translate(locale.value, theme.value === "dark" ? "theme.switchToLight" : "theme.switchToDark"),
  );
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
    semanticHealth.value = {
      embeddingStrict: Boolean(payload.embedding_strict),
      ready: payload.semantic_backend_ready !== false,
      reason: `${payload.semantic_backend_reason ?? ""}`,
    };
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
      resetViewerMemoryEditor();
      viewerMemoryLogsById.value = {};
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
        throw new Error(await getResponseError(response, "errors.viewerLoadFailed"));
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

  function setLocale(nextLocale) {
    locale.value = nextLocale === "en" ? "en" : "zh";
  }

  function toggleLocale() {
    setLocale(locale.value === "zh" ? "en" : "zh");
  }

  function syncLlmSettingsDraft(payload) {
    llmSettingsDraft.value = {
      model: payload.model || "",
      systemPrompt: payload.systemPrompt || "",
    };
  }

  function applyLlmSettings(payload) {
    llmSettings.value = {
      model: payload.model || "",
      systemPrompt: payload.systemPrompt || "",
      defaultModel: payload.defaultModel || "",
      defaultSystemPrompt: payload.defaultSystemPrompt || "",
    };
    syncLlmSettingsDraft(llmSettings.value);
    if (llmSettings.value.model) {
      modelStatus.value = {
        ...modelStatus.value,
        model: llmSettings.value.model,
      };
    }
  }

  async function loadLlmSettings() {
    llmSettingsError.value = "";
    const response = await fetch("/api/settings/llm");
    if (!response.ok) {
      throw new Error("errors.llmSettingsLoadFailed");
    }
    const payload = await response.json();
    applyLlmSettings({
      model: payload.model,
      systemPrompt: payload.system_prompt,
      defaultModel: payload.default_model,
      defaultSystemPrompt: payload.default_system_prompt,
    });
    return llmSettings.value;
  }

  async function openLlmSettings() {
    isLlmSettingsOpen.value = true;
    llmSettingsError.value = "";
    try {
      await loadLlmSettings();
    } catch (error) {
      llmSettingsError.value =
        error instanceof Error ? error.message : "errors.llmSettingsLoadFailed";
    }
  }

  function closeLlmSettings() {
    isLlmSettingsOpen.value = false;
    llmSettingsError.value = "";
  }

  function updateLlmModelDraft(value) {
    llmSettingsDraft.value = {
      ...llmSettingsDraft.value,
      model: `${value ?? ""}`,
    };
  }

  function updateSystemPromptDraft(value) {
    llmSettingsDraft.value = {
      ...llmSettingsDraft.value,
      systemPrompt: `${value ?? ""}`,
    };
  }

  async function saveLlmSettings() {
    isSavingLlmSettings.value = true;
    llmSettingsError.value = "";
    try {
      const response = await fetch("/api/settings/llm", {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          model: llmSettingsDraft.value.model,
          system_prompt: llmSettingsDraft.value.systemPrompt,
        }),
      });
      if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        throw new Error(payload.detail || "errors.llmSettingsSaveFailed");
      }
      const payload = await response.json();
      applyLlmSettings({
        model: payload.model,
        systemPrompt: payload.system_prompt,
        defaultModel: payload.default_model,
        defaultSystemPrompt: payload.default_system_prompt,
      });
    } catch (error) {
      llmSettingsError.value =
        error instanceof Error ? error.message : "errors.llmSettingsSaveFailed";
    } finally {
      isSavingLlmSettings.value = false;
    }
  }

  async function resetLlmSettings() {
    llmSettingsDraft.value = {
      model: llmSettings.value.defaultModel,
      systemPrompt: llmSettings.value.defaultSystemPrompt,
    };
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
      roomError.value = "errors.roomRequired";
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
        throw new Error(payload.detail || "errors.roomSwitchFailed");
      }

      const payload = await response.json();
      closeViewerWorkbench();
      hydrateSnapshot(payload);
      roomDraft.value = "";
      connect(payload.room_id || targetRoomId);
    } catch (error) {
      roomError.value = error instanceof Error ? error.message : "errors.roomSwitchFailed";
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
      const errorText = await getResponseError(response, "errors.viewerNoteSaveFailed");
      throw new Error(errorText);
    }

    return response.json();
  }

  function resetViewerNoteEditor() {
    viewerNoteDraft.value = "";
    viewerNotePinned.value = false;
    editingViewerNoteId.value = "";
  }

  function resetViewerMemoryEditor() {
    viewerMemoryDraft.value = {
      memoryText: "",
      memoryType: "fact",
      isPinned: false,
      correctionReason: "",
    };
    editingViewerMemoryId.value = "";
  }

  function resetViewerWorkbenchState() {
    viewerWorkbench.value.viewer = null;
    viewerWorkbench.value.loading = false;
    viewerWorkbench.value.error = "";
    resetViewerNoteEditor();
    resetViewerMemoryEditor();
    viewerMemoryLogsById.value = {};
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

  function setViewerMemoryDraft(patch) {
    viewerMemoryDraft.value = {
      ...viewerMemoryDraft.value,
      ...patch,
    };
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

  async function deleteViewerNoteRequest(noteId) {
    const response = await fetch(`/api/viewer/notes/${noteId}`, {
      method: "DELETE",
    });

    if (!response.ok) {
      const errorText = await getResponseError(response, "errors.viewerNoteDeleteFailed");
      throw new Error(errorText);
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
      const response = await fetch(url, {
        method,
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(body),
      });
      if (!response.ok) {
        throw new Error(await getResponseError(response, "errors.viewerMemorySaveFailed"));
      }
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
      const response = await fetch(`/api/viewer/memories/${memoryId}/${action}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ reason }),
      });
      if (!response.ok) {
        throw new Error(await getResponseError(response, "errors.viewerMemoryStatusFailed"));
      }
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
      const response = await fetch(`/api/viewer/memories/${memoryId}`, {
        method: "DELETE",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ reason }),
      });
      if (!response.ok) {
        throw new Error(await getResponseError(response, "errors.viewerMemoryDeleteFailed"));
      }
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
      const response = await fetch(`/api/viewer/memories/${memoryId}/logs?limit=20`);
      if (!response.ok) {
        throw new Error(await getResponseError(response, "errors.viewerMemoryLogsLoadFailed"));
      }
      const payload = await response.json();
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
    locale,
    roomDraft,
    theme,
    nextThemeLabel,
    isSwitchingRoom,
    roomError,
    connectionState,
    selectedEventTypes,
    eventFilters,
    modelStatus,
    semanticHealth,
    llmSettings,
    llmSettingsDraft,
    isLlmSettingsOpen,
    isSavingLlmSettings,
    llmSettingsError,
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
    setLocale,
    toggleLocale,
    setTheme,
    toggleTheme,
    loadLlmSettings,
    openLlmSettings,
    closeLlmSettings,
    updateLlmModelDraft,
    updateSystemPromptDraft,
    saveLlmSettings,
    resetLlmSettings,
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
    viewerMemoryDraft,
    editingViewerMemoryId,
    isSavingViewerMemory,
    viewerMemoryLogsById,
    setViewerNoteDraft,
    toggleViewerNotePinned,
    beginEditingViewerNote,
    saveActiveViewerNote,
    deleteViewerNote,
    setViewerMemoryDraft,
    beginEditingViewerMemory,
    saveActiveViewerMemory,
    invalidateViewerMemory,
    reactivateViewerMemory,
    deleteViewerMemory,
    toggleViewerMemoryPin,
    loadViewerMemoryLogs,
  };
});
