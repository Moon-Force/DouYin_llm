<script setup>
import { onMounted } from "vue";
import { storeToRefs } from "pinia";

import EventFeed from "./components/EventFeed.vue";
import StatusStrip from "./components/StatusStrip.vue";
import TeleprompterCard from "./components/TeleprompterCard.vue";
import { useLiveStore } from "./stores/live";

const liveStore = useLiveStore();
const { activeSuggestion, connectionState, events, modelStatus, roomId, stats } = storeToRefs(liveStore);

onMounted(async () => {
  await liveStore.bootstrap();
  liveStore.connect();
});
</script>

<template>
  <main class="mx-auto flex min-h-screen max-w-[1600px] flex-col gap-6 px-4 py-5 md:px-6 xl:px-10">
    <StatusStrip
      :room-id="roomId"
      :connection-state="connectionState"
      :model-status="modelStatus"
      :stats="stats"
    />

    <section class="grid flex-1 gap-6 xl:grid-cols-[1.75fr_0.85fr]">
      <TeleprompterCard :suggestion="activeSuggestion" />
      <EventFeed :events="events" />
    </section>
  </main>
</template>
