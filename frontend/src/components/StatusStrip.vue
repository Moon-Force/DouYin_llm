<script setup>
import { computed } from "vue";

import { translate, translateError } from "../i18n.js";
import { getConnectionBadgePresentation } from "./status-strip-presenter.js";

const props = defineProps({
  locale: {
    type: String,
    required: true,
  },
  roomId: {
    type: String,
    required: true,
  },
  roomDraft: {
    type: String,
    required: true,
  },
  theme: {
    type: String,
    required: true,
  },
  nextThemeLabel: {
    type: String,
    required: true,
  },
  isSwitchingRoom: {
    type: Boolean,
    required: true,
  },
  roomError: {
    type: String,
    default: "",
  },
  connectionState: {
    type: String,
    required: true,
  },
  modelStatus: {
    type: Object,
    required: true,
  },
  semanticHealth: {
    type: Object,
    required: true,
  },
  stats: {
    type: Object,
    required: true,
  },
});

defineEmits([
  "update-room-draft",
  "switch-room",
  "toggle-theme",
  "toggle-locale",
  "open-llm-settings",
]);

function t(key, params) {
  return translate(props.locale, key, params);
}

function translateEnum(baseKey, value) {
  const key = `${baseKey}.${value}`;
  const translated = translate(props.locale, key);
  return translated === key ? value : translated;
}

const roomLabel = computed(() => props.roomId || t("status.noRoomSelected"));
const roomErrorMessage = computed(() => translateError(props.locale, props.roomError));
const connectionBadge = computed(() =>
  getConnectionBadgePresentation(props.connectionState),
);
const connectionBadgeLabel = computed(() => t(connectionBadge.value.labelKey));
const modelResultLabel = computed(() =>
  translateEnum("status.modelResult", props.modelStatus.last_result),
);
const modelModeLabel = computed(() =>
  translateEnum("status.modelMode", props.modelStatus.mode),
);
const semanticStatusLabel = computed(() =>
  t(props.semanticHealth.ready ? "status.semantic.ready" : "status.semantic.unavailable"),
);
const semanticReasonLabel = computed(() =>
  props.semanticHealth.reason || t("common.noData"),
);
const localeToggleLabel = computed(() =>
  props.locale === "zh" ? t("locale.switchToEnglish") : t("locale.switchToChinese"),
);
const localeBadgeLabel = computed(() => (props.locale === "zh" ? "EN" : "\u4E2D"));
const toolsCardLabel = computed(() => (props.locale === "zh" ? "\u5DE5\u5177" : "Tools"));
const switchRoomLabel = computed(() =>
  props.isSwitchingRoom ? t("status.switching") : t("status.switchRoom"),
);
const modelDetailLabel = computed(() => props.modelStatus.last_error || modelModeLabel.value);
const semanticCardClass = computed(() =>
  props.semanticHealth.ready
    ? "border-emerald-400/20 bg-emerald-500/10"
    : "border-amber-300/30 bg-amber-500/12",
);

const connectionBadgeClass = computed(() => {
  switch (connectionBadge.value.tone) {
    case "success":
      return "bg-emerald-500/12 text-emerald-300 ring-1 ring-inset ring-emerald-400/25";
    case "warning":
      return "bg-amber-500/12 text-amber-200 ring-1 ring-inset ring-amber-400/25";
    default:
      return "bg-rose-500/12 text-rose-200 ring-1 ring-inset ring-rose-400/25";
  }
});

const localeButtonClass = computed(() =>
  props.theme === "dark"
    ? "border-white/90 bg-white/[0.03] text-accent hover:bg-accent/14 hover:border-white"
    : "border-line/18 bg-panel-soft text-ink/90 hover:border-accent/35 hover:text-accent",
);

const themeButtonClass = computed(() =>
  props.theme === "dark"
    ? "border-white/90 bg-white/[0.03] text-accent hover:bg-accent/14 hover:border-white"
    : "border-line/18 bg-panel-soft text-paper hover:border-accent/35 hover:text-accent",
);
</script>

<template>
  <header
    class="rounded-[28px] border border-line/14 bg-panel/92 p-4 shadow-[var(--shadow-elev)] backdrop-blur sm:p-5"
  >
    <div class="grid gap-4 xl:grid-cols-[minmax(0,1.4fr)_minmax(320px,1fr)]">
      <section
        class="rounded-[24px] border border-line/12 bg-panel-soft/72 p-5 shadow-[inset_0_1px_0_rgba(255,255,255,0.03)]"
      >
        <div class="flex flex-col gap-5">
          <div class="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
            <div class="min-w-0">
              <p class="text-[11px] uppercase tracking-[0.3em] text-muted">
                {{ t("status.room") }}
              </p>
              <p class="mt-3 truncate text-2xl font-semibold tracking-tight text-paper md:text-[30px]">
                {{ roomLabel }}
              </p>
            </div>

            <div class="flex flex-col items-start gap-2 sm:items-end">
              <p class="text-[11px] uppercase tracking-[0.3em] text-muted">
                {{ t("status.connection") }}
              </p>
              <span
                class="inline-flex items-center gap-2 rounded-full px-3 py-1.5 text-xs font-medium"
                :class="connectionBadgeClass"
              >
                <span
                  v-if="connectionBadge.icon === 'pulse'"
                  aria-hidden="true"
                  class="relative flex h-2.5 w-2.5"
                >
                  <span class="absolute inline-flex h-full w-full animate-ping rounded-full bg-current opacity-60" />
                  <span class="relative inline-flex h-2.5 w-2.5 rounded-full bg-current" />
                </span>
                <svg
                  v-else-if="connectionBadge.icon === 'check'"
                  aria-hidden="true"
                  xmlns="http://www.w3.org/2000/svg"
                  viewBox="0 0 16 16"
                  fill="none"
                  stroke="currentColor"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="1.8"
                  class="h-3.5 w-3.5"
                >
                  <path d="M3.5 8.5 6.5 11.5 12.5 4.5" />
                </svg>
                <span
                  v-else
                  aria-hidden="true"
                  class="h-2.5 w-2.5 rounded-full bg-current"
                />
                {{ connectionBadgeLabel }}
              </span>
            </div>
          </div>

          <div class="flex flex-col gap-2 lg:flex-row">
            <input
              :value="roomDraft"
              type="text"
              inputmode="numeric"
              :placeholder="t('status.roomPlaceholder')"
              class="w-full rounded-full border border-line/16 bg-panel px-4 py-3 text-sm text-paper shadow-sm outline-none transition placeholder:text-muted focus:border-accent focus:ring-2 focus:ring-accent/20"
              @input="$emit('update-room-draft', $event.target.value)"
              @keyup.enter="$emit('switch-room')"
            />
            <button
              type="button"
              class="rounded-full border border-accent/55 bg-accent/14 px-5 py-3 text-xs font-semibold uppercase tracking-[0.18em] text-accent shadow-sm transition hover:bg-accent/20 disabled:cursor-not-allowed disabled:opacity-60"
              :disabled="isSwitchingRoom"
              @click="$emit('switch-room')"
            >
              {{ switchRoomLabel }}
            </button>
          </div>

          <div class="min-h-[1.25rem] text-xs">
            <p v-if="roomErrorMessage" class="text-rose-400">{{ roomErrorMessage }}</p>
          </div>
        </div>
      </section>

      <section class="grid gap-3 md:grid-cols-4">
        <article class="rounded-[22px] border border-line/12 bg-panel-soft/60 p-4">
          <p class="text-[11px] uppercase tracking-[0.28em] text-muted">
            {{ t("common.comments") }}
          </p>
          <div class="mt-4 grid grid-cols-2 gap-3">
            <div>
              <p class="text-2xl font-semibold text-paper">{{ stats.comments }}</p>
              <p class="mt-1 text-[11px] uppercase tracking-[0.18em] text-muted">
                {{ t("common.comments") }}
              </p>
            </div>
            <div>
              <p class="text-2xl font-semibold text-paper">{{ stats.total_events }}</p>
              <p class="mt-1 text-[11px] uppercase tracking-[0.18em] text-muted">
                {{ t("status.totalEvents") }}
              </p>
            </div>
          </div>
        </article>

        <article class="rounded-[22px] border border-line/12 bg-panel-soft/60 p-4">
          <p class="text-[11px] uppercase tracking-[0.28em] text-muted">
            {{ t("status.model") }}
          </p>
          <p class="mt-4 break-words text-sm font-semibold leading-6 text-paper">
            {{ modelStatus.model }}
          </p>
          <p class="mt-2 text-xs font-medium text-accent">
            {{ modelResultLabel }}
          </p>
          <p class="mt-2 min-h-[2.5rem] break-words text-xs leading-5 text-muted">
            {{ modelDetailLabel }}
          </p>
          <button
            type="button"
            class="mt-4 rounded-full border border-line/16 bg-panel px-3 py-1.5 text-[11px] uppercase tracking-[0.18em] text-muted transition hover:border-accent hover:text-accent"
            @click="$emit('open-llm-settings')"
          >
            {{ t("common.settings") }}
          </button>
        </article>

        <article class="rounded-[22px] border p-4" :class="semanticCardClass">
          <p class="text-[11px] uppercase tracking-[0.28em] text-muted">
            {{ t("status.semantic.title") }}
          </p>
          <p class="mt-4 text-sm font-semibold text-paper">
            {{ semanticStatusLabel }}
          </p>
          <p
            v-if="semanticHealth.embeddingStrict"
            class="mt-2 text-xs font-medium text-accent"
          >
            {{ t("status.semantic.strictEnabled") }}
          </p>
          <p class="mt-2 break-words text-xs leading-5 text-muted">
            <span class="font-medium text-paper/85">{{ t("status.semantic.reason") }}：</span>
            {{ semanticReasonLabel }}
          </p>
        </article>

        <article class="rounded-[22px] border border-line/12 bg-panel-soft/60 p-4">
          <p class="text-[11px] uppercase tracking-[0.28em] text-muted">{{ toolsCardLabel }}</p>
          <div class="mt-4 grid gap-2">
            <button
              type="button"
              class="flex items-center justify-between rounded-2xl border px-3 py-2 text-left transition"
              :class="localeButtonClass"
              :title="localeToggleLabel"
              :aria-label="localeToggleLabel"
              @click="$emit('toggle-locale')"
            >
              <span class="text-[11px] uppercase tracking-[0.18em] text-muted">
                {{ localeToggleLabel }}
              </span>
              <span
                aria-hidden="true"
                class="inline-flex min-w-[2.25rem] items-center justify-center rounded-full bg-black/10 px-2 py-1 text-[11px] font-semibold tracking-[0.12em]"
              >
                {{ localeBadgeLabel }}
              </span>
            </button>

            <button
              type="button"
              class="flex items-center justify-between rounded-2xl border px-3 py-2 text-left transition"
              :class="themeButtonClass"
              :title="nextThemeLabel"
              :aria-label="nextThemeLabel"
              @click="$emit('toggle-theme')"
            >
              <span class="text-[11px] uppercase tracking-[0.18em] text-muted">
                {{ nextThemeLabel }}
              </span>
              <svg
                v-if="theme === 'dark'"
                aria-hidden="true"
                xmlns="http://www.w3.org/2000/svg"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="1.8"
                class="h-5 w-5 text-accent"
              >
                <circle cx="12" cy="12" r="4" />
                <path d="M12 2v2.5" />
                <path d="M12 19.5V22" />
                <path d="M4.93 4.93l1.77 1.77" />
                <path d="M17.3 17.3l1.77 1.77" />
                <path d="M2 12h2.5" />
                <path d="M19.5 12H22" />
                <path d="M4.93 19.07l1.77-1.77" />
                <path d="M17.3 6.7l1.77-1.77" />
              </svg>
              <svg
                v-else
                aria-hidden="true"
                xmlns="http://www.w3.org/2000/svg"
                viewBox="0 0 24 24"
                fill="currentColor"
                class="h-5 w-5 text-paper"
              >
                <path
                  d="M20.8 14.2A8.8 8.8 0 0 1 9.8 3.2a.75.75 0 0 0-.95-.95A10.3 10.3 0 1 0 21.75 15.15a.75.75 0 0 0-.95-.95Z"
                />
              </svg>
            </button>
          </div>
        </article>
      </section>
    </div>
  </header>
</template>
