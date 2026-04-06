<script setup>
import { onMounted } from "vue";
import { storeToRefs } from "pinia";

import EventFeed from "./components/EventFeed.vue";
import StatusStrip from "./components/StatusStrip.vue";
import TeleprompterCard from "./components/TeleprompterCard.vue";
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
  nextThemeLabel,
  roomId,
  roomDraft,
  roomError,
  selectedEventTypes,
  stats,
  theme,
} = storeToRefs(liveStore);

onMounted(async () => {
  await liveStore.bootstrap();
  liveStore.connect();
});
</script>

<template>
  <main class="mx-auto flex min-h-screen max-w-[1600px] flex-col gap-6 px-4 py-5 md:px-6 xl:px-10">
    <StatusStrip
      :room-id="roomId"
      :room-draft="roomDraft"
      :theme="theme"
      :next-theme-label="nextThemeLabel"
      :is-switching-room="isSwitchingRoom"
      :room-error="roomError"
      :connection-state="connectionState"
      :model-status="modelStatus"
      :stats="stats"
      @update-room-draft="liveStore.setRoomDraft"
      @switch-room="liveStore.switchRoom"
      @toggle-theme="liveStore.toggleTheme"
    />

    <section class="grid min-h-0 flex-1 gap-6 xl:grid-cols-[1.75fr_0.85fr]">
      <TeleprompterCard :suggestion="activeSuggestion" :source-event="activeSourceEvent" />
      <EventFeed
        :events="filteredEvents"
        :event-filters="eventFilters"
        :selected-event-types="selectedEventTypes"
        :are-all-event-types-selected="areAllEventTypesSelected"
        @toggle-filter="liveStore.toggleEventType"
        @select-all-filters="liveStore.selectAllEventTypes"
        @clear-events="liveStore.clearEvents"
      />
    </section>
  </main>
</template>
