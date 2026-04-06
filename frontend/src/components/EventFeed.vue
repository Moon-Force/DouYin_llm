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

const emit = defineEmits(["toggle-filter", "select-all-filters", "clear-events"]);

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

function primaryContent(event) {
  return event.content || event.metadata?.gift_name || event.method;
}

function eventCardStyle(eventType) {
  switch (eventType) {
    case "comment":
      return {
        borderColor: "rgba(56, 189, 248, 0.42)",
        backgroundColor: "rgba(56, 189, 248, 0.18)",
      };
    case "gift":
      return {
        borderColor: "rgba(245, 158, 11, 0.46)",
        backgroundColor: "rgba(245, 158, 11, 0.18)",
      };
    case "follow":
      return {
        borderColor: "rgba(16, 185, 129, 0.42)",
        backgroundColor: "rgba(16, 185, 129, 0.18)",
      };
    case "member":
      return {
        borderColor: "rgba(217, 70, 239, 0.42)",
        backgroundColor: "rgba(217, 70, 239, 0.18)",
      };
    case "like":
      return {
        borderColor: "rgba(244, 63, 94, 0.42)",
        backgroundColor: "rgba(244, 63, 94, 0.18)",
      };
    default:
      return {
        borderColor: "rgb(var(--color-line) / 0.12)",
        backgroundColor: "rgb(var(--color-panel-soft) / 0.72)",
      };
  }
}
</script>

<template>
  <section
    class="flex min-h-0 flex-col rounded-[28px] border border-line/14 bg-panel-soft/88 p-6 shadow-[var(--shadow-elev)]"
  >
    <div class="flex flex-wrap items-center justify-between gap-3">
      <p class="text-[11px] uppercase tracking-[0.3em] text-muted">Live Feed</p>
      <div class="flex flex-wrap items-center gap-2">
        <button
          type="button"
          class="rounded-full border border-line/16 bg-panel px-3 py-1 text-[11px] uppercase tracking-[0.18em] text-muted transition hover:border-rose-400/35 hover:text-rose-500"
          :disabled="events.length === 0"
          @click="emit('clear-events')"
        >
          Clear
        </button>
        <button
          type="button"
          class="rounded-full border px-3 py-1 text-[11px] uppercase tracking-[0.18em] transition"
          :class="
            areAllEventTypesSelected
              ? 'border-line/16 bg-panel text-muted'
              : 'border-accent/60 bg-accent/10 text-accent'
          "
          :disabled="areAllEventTypesSelected"
          @click="emit('select-all-filters')"
        >
          Show All
        </button>
      </div>
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
            : 'border-line/16 bg-panel text-muted'
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

    <div class="mt-5 max-h-[60vh] overflow-y-auto pr-2 xl:max-h-[calc(100vh-260px)]">
      <div class="space-y-3">
        <article
          v-for="event in events.slice(0, 10)"
          :key="event.event_id"
          class="rounded-2xl border p-4"
          :style="eventCardStyle(event.event_type)"
        >
          <div class="flex items-center justify-between gap-3 text-[11px] uppercase tracking-[0.2em] text-muted">
            <span class="rounded-full border border-line/16 bg-panel px-2 py-1 shadow-sm">
              {{ badge(event.event_type) }}
            </span>
            <span>{{ event.method }}</span>
          </div>

          <div class="mt-3 grid gap-3 sm:grid-cols-[180px_minmax(0,1fr)]">
            <div class="rounded-2xl border border-line/14 bg-panel/92 px-3 py-3 shadow-sm">
              <p class="text-xs uppercase tracking-[0.18em] text-accent-soft">用户</p>
              <p class="mt-2 text-sm font-medium leading-6 text-paper">
                {{ event.user.nickname || "未知用户" }}
              </p>
            </div>

            <div class="rounded-2xl border border-line/14 bg-panel/92 px-3 py-3 shadow-sm">
              <p class="text-xs uppercase tracking-[0.18em] text-muted">内容</p>
              <p class="mt-2 text-sm leading-6 text-paper/90">
                {{ primaryContent(event) }}
              </p>
            </div>
          </div>
        </article>

        <p
          v-if="events.length === 0"
          class="rounded-2xl border border-line/14 bg-panel/92 p-4 text-sm text-muted shadow-sm"
        >
          当前筛选下没有消息。
        </p>
      </div>
    </div>
  </section>
</template>
