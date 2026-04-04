<script setup>
defineProps({
  roomId: {
    type: String,
    required: true,
  },
  connectionState: {
    type: String,
    required: true,
  },
  stats: {
    type: Object,
    required: true,
  },
});
</script>

<template>
  <header
    class="grid gap-3 rounded-[28px] border border-white/8 bg-white/4 p-5 backdrop-blur sm:grid-cols-4"
  >
    <div>
      <p class="text-[11px] uppercase tracking-[0.3em] text-muted">Room</p>
      <p class="mt-2 text-lg font-medium text-paper">{{ roomId }}</p>
    </div>
    <div>
      <p class="text-[11px] uppercase tracking-[0.3em] text-muted">Connection</p>
      <p class="mt-2 text-lg font-medium text-accent">{{ connectionState }}</p>
    </div>
    <div>
      <p class="text-[11px] uppercase tracking-[0.3em] text-muted">Comments</p>
      <p class="mt-2 text-lg font-medium text-paper">{{ stats.comments }}</p>
    </div>
    <div>
      <p class="text-[11px] uppercase tracking-[0.3em] text-muted">Total Events</p>
      <p class="mt-2 text-lg font-medium text-paper">{{ stats.total_events }}</p>
    </div>
  </header>
</template>
