<script setup>
import { translate } from "../i18n.js";
import {
  getSuggestionConfidenceBand,
  getSuggestionReferencePreview,
  getSuggestionSupportLabel,
} from "./teleprompter-presenter.js";

const props = defineProps({
  locale: {
    type: String,
    required: true,
  },
  suggestion: {
    type: Object,
    default: null,
  },
  sourceEvent: {
    type: Object,
    default: null,
  },
});

function t(key, params) {
  return translate(props.locale, key, params);
}

function sourceLabel(source) {
  const key = `teleprompter.source.${source || "heuristic"}`;
  const translated = translate(props.locale, key);
  return translated === key ? source || "heuristic" : translated;
}

function sourceEventLabel(sourceEvent) {
  if (!sourceEvent) {
    return "";
  }

  return sourceEvent.content || sourceEvent.metadata?.gift_name || sourceEvent.method || "";
}

function suggestionReferences(suggestion) {
  return getSuggestionReferencePreview(suggestion);
}
</script>

<template>
  <section class="teleprompter-shell grain flex min-h-0 flex-col overflow-hidden rounded-[36px] p-8">
    <div class="flex flex-wrap items-center justify-between gap-3">
      <span
        class="teleprompter-badge inline-flex items-center rounded-full px-4 py-2 text-[11px] font-semibold uppercase tracking-[0.35em]"
      >
        {{ t("teleprompter.badge") }}
      </span>
      <p class="teleprompter-muted text-sm font-medium">{{ t("teleprompter.title") }}</p>
    </div>

    <div v-if="suggestion" class="mt-10 min-h-0 flex-1 overflow-y-auto pr-1">
      <div
        v-if="sourceEvent && sourceEventLabel(sourceEvent)"
        class="teleprompter-panel rounded-2xl px-4 py-4"
      >
        <p class="teleprompter-accent text-[11px] uppercase tracking-[0.22em]">
          {{ t("teleprompter.sourceContent") }}
        </p>
        <p class="teleprompter-muted mt-2 text-sm">
          {{ sourceEvent.user?.nickname || t("common.unknownUser") }}
        </p>
        <p class="teleprompter-text mt-2 text-base leading-7">
          {{ sourceEventLabel(sourceEvent) }}
        </p>
      </div>

      <div
        class="teleprompter-accent mt-6 flex items-center gap-3 text-xs uppercase tracking-[0.25em]"
      >
        <span>{{ sourceLabel(suggestion.source) }}</span>
        <span>{{ suggestion.priority }}</span>
        <span>{{ suggestion.tone }}</span>
        <span>{{ t(getSuggestionConfidenceBand(suggestion)) }}</span>
      </div>

      <div class="teleprompter-reply mt-6 rounded-[30px] p-7">
        <p class="teleprompter-accent text-[11px] uppercase tracking-[0.28em]">
          {{ t("teleprompter.suggestionReply") }}
        </p>
        <p
          class="teleprompter-headline mt-4 text-4xl leading-tight font-semibold md:text-5xl xl:text-6xl"
        >
          {{ suggestion.reply_text }}
        </p>
      </div>

      <div class="mt-5 flex flex-wrap gap-2 text-[11px] text-muted">
        <span class="rounded-full border border-line/16 bg-panel px-3 py-1">
          {{ t(getSuggestionSupportLabel(suggestion)) }}
        </span>
        <span
          v-for="reference in suggestionReferences(suggestion)"
          :key="reference"
          class="rounded-full border border-line/16 bg-panel px-3 py-1 text-paper/88"
        >
          {{ reference }}
        </span>
      </div>

      <p class="teleprompter-muted mt-8 max-w-3xl text-sm leading-7">
        {{ suggestion.reason }}
      </p>
    </div>

    <div
      v-else
      class="teleprompter-panel teleprompter-muted mt-10 min-h-0 flex-1 overflow-y-auto rounded-[30px] p-8 text-3xl leading-tight md:text-4xl"
    >
      {{ t("teleprompter.waiting") }}
    </div>
  </section>
</template>
