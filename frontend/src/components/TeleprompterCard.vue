<script setup>
defineProps({
  suggestion: {
    type: Object,
    default: null,
  },
});
</script>

<template>
  <section class="grain rounded-[36px] border border-white/8 bg-panel/80 p-8 shadow-2xl">
    <p class="text-[11px] uppercase tracking-[0.35em] text-muted">Teleprompter</p>

    <div v-if="suggestion" class="mt-10">
      <div class="flex items-center gap-3 text-xs uppercase tracking-[0.25em] text-accent-soft">
        <span>{{ suggestion.priority }}</span>
        <span>{{ suggestion.tone }}</span>
      </div>
      <p class="mt-6 text-4xl leading-tight font-medium text-paper md:text-5xl xl:text-6xl">
        {{ suggestion.reply_text }}
      </p>
      <p class="mt-8 max-w-3xl text-sm leading-7 text-muted">
        {{ suggestion.reason }}
      </p>
    </div>

    <div v-else class="mt-10 text-3xl leading-tight text-muted md:text-4xl">
      等待新的弹幕与建议...
    </div>
  </section>
</template>
