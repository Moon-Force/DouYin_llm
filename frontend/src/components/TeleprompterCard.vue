<script setup>
import { translate } from "../i18n.js";

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
</script>

<template>
  <section class="teleprompter-shell grain rounded-[36px] p-8">
    <div class="flex flex-wrap items-center justify-between gap-3">
      <span
        class="teleprompter-badge inline-flex items-center rounded-full px-4 py-2 text-[11px] font-semibold uppercase tracking-[0.35em]"
      >
        {{ t("teleprompter.badge") }}
      </span>
      <p class="teleprompter-muted text-sm font-medium">{{ t("teleprompter.title") }}</p>
    </div>

    <div v-if="suggestion" class="mt-10">
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

      <p class="teleprompter-muted mt-8 max-w-3xl text-sm leading-7">
        {{ suggestion.reason }}
      </p>
    </div>

    <div
      v-else
      class="teleprompter-panel teleprompter-muted mt-10 rounded-[30px] p-8 text-3xl leading-tight md:text-4xl"
    >
      {{ t("teleprompter.waiting") }}
    </div>
  </section>
</template>
