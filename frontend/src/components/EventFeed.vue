<script setup>
import { ref } from "vue";
import { translate } from "../i18n.js";
import {
  getCommentProcessingDetails,
  getCommentProcessingTimeline,
} from "./event-feed-processing-presenter.js";

const props = defineProps({
  locale: {
    type: String,
    required: true,
  },
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

const emit = defineEmits([
  "toggle-filter",
  "select-all-filters",
  "clear-events",
  "select-viewer",
]);

const expandedEventIds = ref(new Set());

function t(key, params) {
  return translate(props.locale, key, params);
}

function badge(eventType) {
  const match = props.eventFilters.find((filter) => filter.value === eventType);
  return match?.label ?? t("feed.eventType.system");
}

function isSelected(eventType) {
  return props.selectedEventTypes.includes(eventType);
}

function isLockedSelected(eventType) {
  return isSelected(eventType) && props.selectedEventTypes.length === 1;
}

function primaryContent(event) {
  return event.content || event.metadata?.gift_name || event.method || t("common.noData");
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

function selectViewer(event) {
  if (!event?.room_id) {
    return;
  }

  const viewerId = event.user?.viewer_id;
  const nickname = event.user?.nickname;
  if (!viewerId && !nickname) {
    return;
  }

  emit("select-viewer", {
    roomId: event.room_id,
    viewerId: viewerId || "",
    nickname: nickname || "",
  });
}

function processingTimeline(event) {
  return getCommentProcessingTimeline(event).map((item) => ({
    ...item,
    label: t(item.labelKey),
    reason: item.reasonKey ? t(`${item.reasonKey}.short`) : "",
  }));
}

function processingDetails(event) {
  return getCommentProcessingDetails(event).map((item) => ({
    ...item,
    title: t(item.titleKey),
    summary: t(item.summaryKey),
    meta: item.meta.map((metaItem) => ({
      ...metaItem,
      label: t(metaItem.key),
      value: metaItem.valueKey ? t(metaItem.valueKey) : metaItem.value,
    })),
  }));
}

function hasProcessingDetails(event) {
  return processingDetails(event).length > 0;
}

function processingStepTone(state) {
  if (state === "success") {
    return {
      dot: "bg-emerald-300 shadow-[0_0_0_4px_rgba(110,231,183,0.16)]",
      label: "text-paper",
      line: "bg-emerald-300/40",
      panel: "border-emerald-300/24 bg-emerald-400/10",
    };
  }

  if (state === "skipped") {
    return {
      dot: "border border-line/30 bg-panel",
      label: "text-muted",
      line: "border-t border-dashed border-line/18 bg-transparent",
      panel: "border-line/12 bg-panel/45",
    };
  }

  if (state === "failed") {
    return {
      dot: "bg-rose-300 shadow-[0_0_0_4px_rgba(253,164,175,0.16)]",
      label: "text-rose-100",
      line: "bg-rose-300/40",
      panel: "border-rose-300/24 bg-rose-400/12",
    };
  }

  return {
    dot: "bg-amber-200 shadow-[0_0_0_4px_rgba(253,230,138,0.14)]",
    label: "text-paper/84",
    line: "bg-amber-200/30",
    panel: "border-amber-200/20 bg-amber-300/10",
  };
}

function viewerNotesPreview(event) {
  return Array.isArray(event?.metadata?.viewer_notes_preview)
    ? event.metadata.viewer_notes_preview.filter((item) => `${item ?? ""}`.trim())
    : [];
}

function isProcessingExpanded(event) {
  return expandedEventIds.value.has(event.event_id);
}

function toggleProcessingDetails(event) {
  const next = new Set(expandedEventIds.value);
  if (next.has(event.event_id)) {
    next.delete(event.event_id);
  } else {
    next.add(event.event_id);
  }
  expandedEventIds.value = next;
}
</script>

<template>
  <section
    class="flex min-h-0 flex-col rounded-[28px] border border-line/14 bg-panel-soft/88 p-6 shadow-[var(--shadow-elev)]"
  >
    <div class="flex flex-wrap items-center justify-between gap-3">
      <p class="text-[11px] uppercase tracking-[0.3em] text-muted">{{ t("feed.title") }}</p>
      <div class="flex flex-wrap items-center gap-2">
        <button
          type="button"
          class="rounded-full border border-line/16 bg-panel px-3 py-1 text-[11px] uppercase tracking-[0.18em] text-muted transition hover:border-rose-400/35 hover:text-rose-500"
          :disabled="events.length === 0"
          @click="emit('clear-events')"
        >
          {{ t("feed.clear") }}
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
          {{ t("feed.showAll") }}
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
      {{ t("feed.showing", { selected: selectedEventTypes.length, total: eventFilters.length }) }}
    </p>

    <div class="mt-5 flex-1 min-h-0 overflow-y-auto overflow-x-hidden pr-2">
      <div class="space-y-3">
        <article
          v-for="event in events.slice(0, 10)"
          :key="event.event_id"
          class="rounded-2xl border p-4"
          :style="eventCardStyle(event.event_type)"
        >
          <div
            class="flex items-center justify-between gap-3 text-[11px] uppercase tracking-[0.2em] text-muted"
          >
            <span class="rounded-full border border-line/16 bg-panel px-2 py-1 shadow-sm">
              {{ badge(event.event_type) }}
            </span>
            <span>{{ event.method }}</span>
          </div>

          <div class="mt-3 grid gap-3 sm:grid-cols-[180px_minmax(0,1fr)]">
            <div class="rounded-2xl border border-line/14 bg-panel/92 px-3 py-3 shadow-sm">
              <p class="text-xs uppercase tracking-[0.18em] text-accent-soft">
                {{ t("feed.user") }}
              </p>
              <button
                type="button"
                class="mt-2 text-left text-sm font-medium leading-6 text-paper transition hover:text-accent"
                @click="selectViewer(event)"
              >
                {{ event.user?.nickname || t("common.unknownUser") }}
              </button>
              <div
                v-if="viewerNotesPreview(event).length"
                class="mt-3 border-t border-line/12 pt-3"
              >
                <p class="text-[10px] uppercase tracking-[0.18em] text-muted">
                  {{ t("feed.notes") }}
                </p>
                <p
                  v-for="(note, index) in viewerNotesPreview(event)"
                  :key="`${event.event_id}-note-${index}`"
                  class="mt-2 text-xs leading-5 text-paper/88"
                >
                  {{ note }}
                </p>
              </div>
            </div>

            <div class="rounded-2xl border border-line/14 bg-panel/92 px-3 py-3 shadow-sm">
              <p class="text-xs uppercase tracking-[0.18em] text-muted">
                {{ t("feed.content") }}
              </p>
              <p class="mt-2 text-sm leading-6 text-paper/90">
                {{ primaryContent(event) }}
              </p>
              <div
                v-if="processingTimeline(event).length > 0"
                class="mt-4 rounded-2xl border border-line/12 bg-panel-soft/68 px-3 py-3"
              >
                <div class="flex flex-wrap items-start gap-3">
                  <div
                    v-for="(step, index) in processingTimeline(event)"
                    :key="step.key"
                    class="flex min-w-0 flex-[1_1_140px] items-center gap-2"
                  >
                    <div class="flex min-w-0 items-center gap-2">
                      <span
                        class="h-2.5 w-2.5 shrink-0 rounded-full"
                        :class="processingStepTone(step.state).dot"
                      />
                      <div class="min-w-0">
                        <p
                          class="text-[11px] tracking-[0.12em]"
                          :class="processingStepTone(step.state).label"
                        >
                          {{ step.label }}
                        </p>
                        <p v-if="step.reason" class="mt-0.5 truncate text-[10px] text-muted/90">
                          {{ step.reason }}
                        </p>
                      </div>
                    </div>
                    <span
                      v-if="index < processingTimeline(event).length - 1"
                      class="hidden h-px flex-1 lg:block"
                      :class="processingStepTone(step.state).line"
                    />
                  </div>
                </div>
                <button
                  v-if="hasProcessingDetails(event)"
                  type="button"
                  class="mt-3 rounded-full border border-line/16 bg-panel px-2.5 py-1 text-[11px] tracking-[0.12em] text-accent transition hover:border-accent/40"
                  @click="toggleProcessingDetails(event)"
                >
                  {{
                    isProcessingExpanded(event)
                      ? t("feed.processing.hideDetails")
                      : t("feed.processing.showDetails")
                  }}
                </button>
              </div>
              <ol
                v-if="isProcessingExpanded(event)"
                class="mt-3 space-y-3 rounded-2xl border border-line/14 bg-panel-soft/72 px-4 py-4 text-xs"
              >
                <li
                  v-for="detail in processingDetails(event)"
                  :key="detail.key"
                  class="relative border-l border-line/14 pl-4"
                >
                  <span
                    class="absolute -left-[0.34rem] top-1.5 h-2.5 w-2.5 rounded-full"
                    :class="processingStepTone(detail.state).dot"
                  />
                  <div
                    class="rounded-2xl border px-3 py-3"
                    :class="processingStepTone(detail.state).panel"
                  >
                    <p class="text-sm font-medium text-paper">{{ detail.title }}</p>
                    <p class="mt-1 text-xs leading-5 text-muted">{{ detail.summary }}</p>
                    <dl v-if="detail.meta.length > 0" class="mt-2 space-y-1">
                      <div
                        v-for="item in detail.meta"
                        :key="`${detail.key}-${item.key}`"
                        class="text-xs text-paper/88"
                      >
                        <dt class="inline text-muted">{{ item.label }}：</dt>
                        <dd class="inline break-all">{{ item.value }}</dd>
                      </div>
                    </dl>
                  </div>
                </li>
              </ol>
            </div>
          </div>
        </article>

        <p
          v-if="events.length === 0"
          class="rounded-2xl border border-line/14 bg-panel/92 p-4 text-sm text-muted shadow-sm"
        >
          {{ t("feed.empty") }}
        </p>
      </div>
    </div>
  </section>
</template>
