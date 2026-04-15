<script setup>
import { onBeforeUnmount, onMounted } from "vue";
import { storeToRefs } from "pinia";

import EventFeed from "./components/EventFeed.vue";
import LlmSettingsPanel from "./components/LlmSettingsPanel.vue";
import StatusStrip from "./components/StatusStrip.vue";
import TeleprompterCard from "./components/TeleprompterCard.vue";
import ViewerWorkbench from "./components/ViewerWorkbench.vue";
import { useLiveStore } from "./stores/live";

const liveStore = useLiveStore();
const {
  activeSuggestion,
  activeSourceEvent,
  areAllEventTypesSelected,
  connectionState,
  eventFilters,
  filteredEvents,
  isSwitchingRoom,
  modelStatus,
  semanticHealth,
  nextThemeLabel,
  locale,
  roomId,
  roomDraft,
  roomError,
  selectedEventTypes,
  stats,
  theme,
  isViewerWorkbenchOpen,
  viewerWorkbench,
  viewerNoteDraft,
  viewerNotePinned,
  isSavingViewerNote,
  editingViewerNoteId,
  llmSettings,
  llmSettingsDraft,
  isLlmSettingsOpen,
  isSavingLlmSettings,
  llmSettingsError,
} = storeToRefs(liveStore);

const handleBeforeUnload = () => {
  liveStore.closeStream();
};

onMounted(async () => {
  try {
    await liveStore.bootstrap();
    liveStore.connect();
    if (typeof window !== "undefined") {
      window.addEventListener("beforeunload", handleBeforeUnload);
    }
  } catch (error) {
    console.error("Live bootstrap failed", error);
  }
});

onBeforeUnmount(() => {
  liveStore.closeStream();
  if (typeof window !== "undefined") {
    window.removeEventListener("beforeunload", handleBeforeUnload);
  }
});
</script>

<template>
  <main class="mx-auto flex min-h-screen max-w-[1600px] flex-col gap-6 px-4 py-5 md:px-6 xl:px-10">
    <StatusStrip
      :locale="locale"
      :room-id="roomId"
      :room-draft="roomDraft"
      :theme="theme"
      :next-theme-label="nextThemeLabel"
      :is-switching-room="isSwitchingRoom"
      :room-error="roomError"
      :connection-state="connectionState"
      :model-status="modelStatus"
      :semantic-health="semanticHealth"
      :stats="stats"
      @update-room-draft="liveStore.setRoomDraft"
      @switch-room="liveStore.switchRoom"
      @toggle-theme="liveStore.toggleTheme"
      @toggle-locale="liveStore.toggleLocale"
      @open-llm-settings="liveStore.openLlmSettings"
    />

    <section class="grid min-h-0 flex-1 gap-6 xl:grid-cols-[1.75fr_0.85fr]">
      <TeleprompterCard
        :locale="locale"
        :suggestion="activeSuggestion"
        :source-event="activeSourceEvent"
      />
      <EventFeed
        :locale="locale"
        :events="filteredEvents"
        :event-filters="eventFilters"
        :selected-event-types="selectedEventTypes"
        :are-all-event-types-selected="areAllEventTypesSelected"
        @toggle-filter="liveStore.toggleEventType"
        @select-all-filters="liveStore.selectAllEventTypes"
        @clear-events="liveStore.clearEvents"
        @select-viewer="liveStore.openViewerWorkbench"
      />
    </section>
  </main>

  <ViewerWorkbench
    :locale="locale"
    :open="isViewerWorkbenchOpen"
    :viewer="viewerWorkbench.viewer"
    :loading="viewerWorkbench.loading"
    :error="viewerWorkbench.error"
    :note-draft="viewerNoteDraft"
    :note-pinned="viewerNotePinned"
    :saving="isSavingViewerNote"
    :editing-note-id="editingViewerNoteId"
    @close="liveStore.closeViewerWorkbench"
    @update-note-draft="liveStore.setViewerNoteDraft"
    @toggle-note-pinned="liveStore.toggleViewerNotePinned"
    @save-note="liveStore.saveActiveViewerNote"
    @edit-note="liveStore.beginEditingViewerNote"
    @delete-note="liveStore.deleteViewerNote"
  />

  <LlmSettingsPanel
    :locale="locale"
    :open="isLlmSettingsOpen"
    :draft="llmSettingsDraft"
    :defaults="llmSettings"
    :saving="isSavingLlmSettings"
    :error="llmSettingsError"
    @close="liveStore.closeLlmSettings"
    @update-model="liveStore.updateLlmModelDraft"
    @update-system-prompt="liveStore.updateSystemPromptDraft"
    @save="liveStore.saveLlmSettings"
    @reset="liveStore.resetLlmSettings"
  />
</template>
