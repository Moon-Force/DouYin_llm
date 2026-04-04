<script setup>
const props = defineProps({
  events: {
    type: Array,
    required: true,
  },
  eventFilters: {
    type: Array,
    required: true,
  },
  selectedEventTypes: {
    type: Array,
    required: true,
  },
  areAllEventTypesSelected: {
    type: Boolean,
    required: true,
  },
});

const emit = defineEmits(["toggle-filter", "select-all-filters"]);

function badge(eventType) {
  switch (eventType) {
    case "comment":
      return "弹幕";
    case "gift":
      return "礼物";
    case "follow":
      return "关注";
    case "member":
      return "进场";
    case "like":
      return "点赞";
    default:
      return "系统";
  }
}

function isSelected(eventType) {
  return props.selectedEventTypes.includes(eventType);
}

function isLockedSelected(eventType) {
  return isSelected(eventType) && props.selectedEventTypes.length === 1;
}
</script>

<template>
  <section class="rounded-[28px] border border-white/8 bg-panel-soft/80 p-6">
    <div class="flex flex-wrap items-center justify-between gap-3">
      <p class="text-[11px] uppercase tracking-[0.3em] text-muted">Live Feed</p>
      <button
        type="button"
        class="rounded-full border px-3 py-1 text-[11px] uppercase tracking-[0.18em] transition"
        :class="
          areAllEventTypesSelected
            ? 'border-white/10 bg-white/4 text-muted'
            : 'border-accent/60 bg-accent/10 text-accent'
        "
        :disabled="areAllEventTypesSelected"
        @click="emit('select-all-filters')"
      >
        Show All
      </button>
    </div>

    <div class="mt-4 flex flex-wrap gap-2">
      <button
        v-for="filter in eventFilters"
        :key="filter.value"
        type="button"
        class="rounded-full border px-3 py-1 text-xs tracking-[0.15em] transition disabled:cursor-not-allowed disabled:opacity-60"
        :class="
          isSelected(filter.value)
            ? 'border-accent bg-accent text-ink'
            : 'border-white/10 bg-white/4 text-muted'
        "
        :disabled="isLockedSelected(filter.value)"
        @click="emit('toggle-filter', filter.value)"
      >
        {{ filter.label }}
      </button>
    </div>

    <p class="mt-3 text-xs text-muted">
      Showing {{ selectedEventTypes.length }} / {{ eventFilters.length }} event types
    </p>

    <div class="mt-5 space-y-3">
      <article
        v-for="event in events.slice(0, 10)"
        :key="event.event_id"
        class="rounded-2xl border border-white/6 bg-white/4 p-4"
      >
        <div class="flex items-center justify-between gap-3 text-xs uppercase tracking-[0.2em] text-muted">
          <span>{{ badge(event.event_type) }}</span>
          <span>{{ event.user.nickname }}</span>
        </div>
        <p class="mt-3 text-sm leading-6 text-paper">
          {{ event.content || event.metadata?.gift_name || event.method }}
        </p>
      </article>
      <p v-if="events.length === 0" class="rounded-2xl border border-white/6 bg-white/4 p-4 text-sm text-muted">
        当前筛选下没有消息。
      </p>
    </div>
  </section>
</template>
