import { computed, ref } from "vue";
import { defineStore, storeToRefs } from "pinia";
import { loadLlmSettingsRequest, saveLlmSettingsRequest } from "../api/live-api.js";
import { translate } from "../i18n.js";
import { useConnectionStore } from "./connection.js";
import { EVENT_FILTER_DEFS, useEventFeedStore } from "./event-feed.js";
import { useViewerWorkbenchStore } from "./viewer-workbench.js";
const THEME_STORAGE_KEY = "live-prompter:theme";

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
  const theme = ref(loadTheme());
  const eventFeedStore = useEventFeedStore();
  const eventFilters = computed(() =>
    EVENT_FILTER_DEFS.map((filter) => ({
      ...filter,
      label: translate(locale.value, filter.labelKey),
    })),
  );
  const connectionStore = useConnectionStore();
  const {
    roomId,
    roomDraft,
    isSwitchingRoom,
    roomError,
    connectionState,
    modelStatus,
    semanticHealth,
  } = storeToRefs(connectionStore);
  const {
    selectedEventTypes,
    stats,
    events,
    suggestions,
    areAllEventTypesSelected,
    filteredEvents,
    activeSuggestion,
    activeSourceEvent,
  } = storeToRefs(eventFeedStore);
  const llmSettings = ref({
    model: "",
    systemPrompt: "",
    defaultModel: "",
    defaultSystemPrompt: "",
    embeddingModel: "",
    memoryExtractorModel: "",
    defaultEmbeddingModel: "",
    defaultMemoryExtractorModel: "",
    embeddingModelOptions: [],
    memoryExtractorModelOptions: [],
  });
  const llmSettingsDraft = ref({
    model: "",
    systemPrompt: "",
    embeddingModel: "",
    memoryExtractorModel: "",
  });
  const isLlmSettingsOpen = ref(false);
  const isSavingLlmSettings = ref(false);
  const llmSettingsError = ref("");
  const viewerWorkbenchStore = useViewerWorkbenchStore();
  const {
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
  } = storeToRefs(viewerWorkbenchStore);
  let hotCleanupRegistered = false;

  const nextThemeLabel = computed(() =>
    translate(locale.value, theme.value === "dark" ? "theme.switchToLight" : "theme.switchToDark"),
  );

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
    eventFeedStore.hydrateEventFeed(payload);
    if (!roomId.value) {
      connectionState.value = "idle";
    }
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
      embeddingModel: payload.embeddingModel || "",
      memoryExtractorModel: payload.memoryExtractorModel || "",
    };
  }

  function applyLlmSettings(payload) {
    llmSettings.value = {
      model: payload.model || "",
      systemPrompt: payload.systemPrompt || "",
      defaultModel: payload.defaultModel || "",
      defaultSystemPrompt: payload.defaultSystemPrompt || "",
      embeddingModel: payload.embeddingModel || "",
      memoryExtractorModel: payload.memoryExtractorModel || "",
      defaultEmbeddingModel: payload.defaultEmbeddingModel || "",
      defaultMemoryExtractorModel: payload.defaultMemoryExtractorModel || "",
      embeddingModelOptions: [...(payload.embeddingModelOptions || [])],
      memoryExtractorModelOptions: [...(payload.memoryExtractorModelOptions || [])],
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
    const payload = await loadLlmSettingsRequest();
    applyLlmSettings({
      model: payload.model,
      systemPrompt: payload.system_prompt,
      defaultModel: payload.default_model,
      defaultSystemPrompt: payload.default_system_prompt,
      embeddingModel: payload.embedding_model,
      memoryExtractorModel: payload.memory_extractor_model,
      defaultEmbeddingModel: payload.default_embedding_model,
      defaultMemoryExtractorModel: payload.default_memory_extractor_model,
      embeddingModelOptions: payload.embedding_model_options,
      memoryExtractorModelOptions: payload.memory_extractor_model_options,
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

  function updateEmbeddingModelDraft(value) {
    llmSettingsDraft.value = {
      ...llmSettingsDraft.value,
      embeddingModel: `${value ?? ""}`,
    };
  }

  function updateMemoryExtractorModelDraft(value) {
    llmSettingsDraft.value = {
      ...llmSettingsDraft.value,
      memoryExtractorModel: `${value ?? ""}`,
    };
  }

  async function saveLlmSettings() {
    isSavingLlmSettings.value = true;
    llmSettingsError.value = "";
    try {
      const payload = await saveLlmSettingsRequest({
        model: llmSettingsDraft.value.model,
        systemPrompt: llmSettingsDraft.value.systemPrompt,
        embeddingModel: llmSettingsDraft.value.embeddingModel,
        memoryExtractorModel: llmSettingsDraft.value.memoryExtractorModel,
      });
      applyLlmSettings({
        model: payload.model,
        systemPrompt: payload.system_prompt,
        defaultModel: payload.default_model,
        defaultSystemPrompt: payload.default_system_prompt,
        embeddingModel: payload.embedding_model,
        memoryExtractorModel: payload.memory_extractor_model,
        defaultEmbeddingModel: payload.default_embedding_model,
        defaultMemoryExtractorModel: payload.default_memory_extractor_model,
        embeddingModelOptions: payload.embedding_model_options,
        memoryExtractorModelOptions: payload.memory_extractor_model_options,
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
      embeddingModel: llmSettings.value.defaultEmbeddingModel,
      memoryExtractorModel: llmSettings.value.defaultMemoryExtractorModel,
    };
  }

  async function bootstrap(targetRoomId = roomId.value) {
    const payload = await connectionStore.bootstrap(targetRoomId);
    hydrateSnapshot(payload);
  }

  function connect(targetRoomId = roomId.value) {
    connectionStore.connect(targetRoomId, {
      onEvent: eventFeedStore.ingestEvent,
      onSuggestion: eventFeedStore.ingestSuggestion,
      onStats(payload) {
        eventFeedStore.updateStats(payload);
      },
    });
  }

  async function switchRoom(nextRoomId = roomDraft.value) {
    try {
      const targetRoomId = `${nextRoomId ?? ""}`.trim();
      const payload = await connectionStore.switchRoom(targetRoomId);
      if (!payload?.room_id) {
        return;
      }
      viewerWorkbenchStore.closeViewerWorkbench();
      hydrateSnapshot(payload);
      roomDraft.value = "";
      connect(payload.room_id || targetRoomId);
    } catch {
      await bootstrap(roomId.value);
      connect(roomId.value);
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
    setRoomDraft: connectionStore.setRoomDraft,
    setLocale,
    toggleLocale,
    setTheme,
    toggleTheme,
    loadLlmSettings,
    openLlmSettings,
    closeLlmSettings,
    updateLlmModelDraft,
    updateSystemPromptDraft,
    updateEmbeddingModelDraft,
    updateMemoryExtractorModelDraft,
    saveLlmSettings,
    resetLlmSettings,
    switchRoom,
    toggleEventType: eventFeedStore.toggleEventType,
    selectAllEventTypes: eventFeedStore.selectAllEventTypes,
    clearEvents: eventFeedStore.clearEvents,
    isViewerWorkbenchOpen,
    viewerWorkbench,
    openViewerWorkbench: viewerWorkbenchStore.openViewerWorkbench,
    saveViewerNote: viewerWorkbenchStore.saveViewerNote,
    closeViewerWorkbench: viewerWorkbenchStore.closeViewerWorkbench,
    closeStream: connectionStore.closeStream,
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
    setViewerNoteDraft: viewerWorkbenchStore.setViewerNoteDraft,
    toggleViewerNotePinned: viewerWorkbenchStore.toggleViewerNotePinned,
    openNewViewerNote: viewerWorkbenchStore.openNewViewerNote,
    closeViewerNoteEditor: viewerWorkbenchStore.closeViewerNoteEditor,
    beginEditingViewerNote: viewerWorkbenchStore.beginEditingViewerNote,
    saveActiveViewerNote: viewerWorkbenchStore.saveActiveViewerNote,
    deleteViewerNote: viewerWorkbenchStore.deleteViewerNote,
    setViewerMemoryDraft: viewerWorkbenchStore.setViewerMemoryDraft,
    openNewViewerMemory: viewerWorkbenchStore.openNewViewerMemory,
    closeViewerMemoryEditor: viewerWorkbenchStore.closeViewerMemoryEditor,
    beginEditingViewerMemory: viewerWorkbenchStore.beginEditingViewerMemory,
    saveActiveViewerMemory: viewerWorkbenchStore.saveActiveViewerMemory,
    invalidateViewerMemory: viewerWorkbenchStore.invalidateViewerMemory,
    reactivateViewerMemory: viewerWorkbenchStore.reactivateViewerMemory,
    deleteViewerMemory: viewerWorkbenchStore.deleteViewerMemory,
    toggleViewerMemoryPin: viewerWorkbenchStore.toggleViewerMemoryPin,
    loadViewerMemoryLogs: viewerWorkbenchStore.loadViewerMemoryLogs,
  };
});
