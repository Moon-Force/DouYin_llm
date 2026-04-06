<script setup>
defineProps({
  suggestion: {
    type: Object,
    default: null,
  },
  sourceEvent: {
    type: Object,
    default: null,
  },
});

function sourceLabel(source) {
  switch (source) {
    case "model":
      return "模型生成";
    case "heuristic_fallback":
      return "规则兜底";
    case "heuristic":
    default:
      return "规则生成";
  }
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
      <span class="teleprompter-badge inline-flex items-center rounded-full px-4 py-2 text-[11px] font-semibold uppercase tracking-[0.35em]">
        Teleprompter
      </span>
      <p class="teleprompter-muted text-sm font-medium">当前最优先展示的回复建议</p>
    </div>

    <div v-if="suggestion" class="mt-10">
      <div
        v-if="sourceEvent && sourceEventLabel(sourceEvent)"
        class="teleprompter-panel rounded-2xl px-4 py-4"
      >
        <p class="teleprompter-accent text-[11px] uppercase tracking-[0.22em]">原始内容</p>
        <p class="teleprompter-muted mt-2 text-sm">
          {{ sourceEvent.user?.nickname || "未知用户" }}
        </p>
        <p class="teleprompter-text mt-2 text-base leading-7">
          {{ sourceEventLabel(sourceEvent) }}
        </p>
      </div>

      <div class="teleprompter-accent mt-6 flex items-center gap-3 text-xs uppercase tracking-[0.25em]">
        <span>{{ sourceLabel(suggestion.source) }}</span>
        <span>{{ suggestion.priority }}</span>
        <span>{{ suggestion.tone }}</span>
      </div>

      <div class="teleprompter-reply mt-6 rounded-[30px] p-7">
        <p class="teleprompter-accent text-[11px] uppercase tracking-[0.28em]">建议回复</p>
        <p class="teleprompter-headline mt-4 text-4xl leading-tight font-semibold md:text-5xl xl:text-6xl">
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
      等待新的弹幕与建议...
    </div>
  </section>
</template>
