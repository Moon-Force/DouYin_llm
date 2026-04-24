<script setup>
import { computed } from "vue";

import { translate, translateError } from "../i18n.js";

const props = defineProps({
  locale: {
    type: String,
    required: true,
  },
  open: {
    type: Boolean,
    required: true,
  },
  draft: {
    type: Object,
    required: true,
  },
  defaults: {
    type: Object,
    required: true,
  },
  saving: {
    type: Boolean,
    default: false,
  },
  error: {
    type: String,
    default: "",
  },
});

const emit = defineEmits([
  "close",
  "update-model",
  "update-embedding-model",
  "update-memory-extractor-model",
  "update-system-prompt",
  "save",
  "reset",
]);

function t(key, params) {
  return translate(props.locale, key, params);
}

const errorMessage = computed(() => translateError(props.locale, props.error));
const defaultModelLabel = computed(() =>
  t("llmSettings.modelDefault", {
    value: props.defaults.defaultModel || t("common.notAvailable"),
  }),
);
const defaultEmbeddingModelLabel = computed(() =>
  t("llmSettings.embeddingModelDefault", {
    value: props.defaults.defaultEmbeddingModel || t("common.notAvailable"),
  }),
);
const defaultMemoryExtractorModelLabel = computed(() =>
  t("llmSettings.memoryExtractorModelDefault", {
    value: props.defaults.defaultMemoryExtractorModel || t("common.notAvailable"),
  }),
);
</script>

<template>
  <aside
    v-if="open"
    class="fixed inset-y-6 left-6 z-40 w-[480px] overflow-y-auto rounded-[30px] border border-line/16 bg-panel p-6 shadow-[var(--shadow-elev)]"
  >
    <div class="flex items-center justify-between pb-4">
      <div>
        <p class="text-lg font-semibold tracking-tight text-paper">{{ t("llmSettings.title") }}</p>
        <p class="mt-1 text-xs text-muted">{{ t("llmSettings.subtitle") }}</p>
      </div>
      <button
        type="button"
        class="text-sm font-medium text-muted transition hover:text-accent"
        @click="emit('close')"
      >
        {{ t("common.close") }}
      </button>
    </div>

    <div class="space-y-5 text-sm text-paper">
      <label class="block space-y-2">
        <span class="text-xs font-semibold uppercase tracking-[0.18em] text-muted">
          {{ t("llmSettings.model") }}
        </span>
        <input
          class="w-full rounded-xl border border-line/40 bg-panel-soft px-3 py-2 text-sm text-paper outline-none transition focus:border-accent"
          :value="draft.model"
          @input="emit('update-model', $event.target.value)"
        />
        <p class="text-[11px] text-muted">{{ defaultModelLabel }}</p>
      </label>

      <label class="block space-y-2">
        <span class="text-xs font-semibold uppercase tracking-[0.18em] text-muted">
          {{ t("llmSettings.embeddingModel") }}
        </span>
        <select
          class="w-full rounded-xl border border-line/40 bg-panel-soft px-3 py-2 text-sm text-paper outline-none transition focus:border-accent"
          :value="draft.embeddingModel"
          @change="emit('update-embedding-model', $event.target.value)"
        >
          <option
            v-for="option in defaults.embeddingModelOptions || []"
            :key="`embedding-${option}`"
            :value="option"
          >
            {{ option }}
          </option>
        </select>
        <p class="text-[11px] text-muted">{{ defaultEmbeddingModelLabel }}</p>
      </label>

      <label class="block space-y-2">
        <span class="text-xs font-semibold uppercase tracking-[0.18em] text-muted">
          {{ t("llmSettings.memoryExtractorModel") }}
        </span>
        <select
          class="w-full rounded-xl border border-line/40 bg-panel-soft px-3 py-2 text-sm text-paper outline-none transition focus:border-accent"
          :value="draft.memoryExtractorModel"
          @change="emit('update-memory-extractor-model', $event.target.value)"
        >
          <option
            v-for="option in defaults.memoryExtractorModelOptions || []"
            :key="`memory-extractor-${option}`"
            :value="option"
          >
            {{ option }}
          </option>
        </select>
        <p class="text-[11px] text-muted">{{ defaultMemoryExtractorModelLabel }}</p>
        <p class="text-[11px] text-muted">{{ t("llmSettings.ollamaOptionsHint") }}</p>
      </label>

      <label class="block space-y-2">
        <span class="text-xs font-semibold uppercase tracking-[0.18em] text-muted">
          {{ t("llmSettings.systemPrompt") }}
        </span>
        <textarea
          class="min-h-[220px] w-full rounded-xl border border-line/40 bg-panel-soft px-3 py-3 text-sm text-paper outline-none transition focus:border-accent"
          :value="draft.systemPrompt"
          @input="emit('update-system-prompt', $event.target.value)"
        ></textarea>
        <p class="text-[11px] text-muted">
          {{ t("llmSettings.promptHint") }}
        </p>
      </label>

      <p v-if="errorMessage" class="text-sm text-rose-500">{{ errorMessage }}</p>

      <div class="flex items-center gap-3">
        <button
          type="button"
          class="rounded-full bg-accent px-4 py-2 text-xs font-semibold uppercase tracking-[0.18em] text-ink transition hover:bg-accent/90 disabled:opacity-60"
          :disabled="saving"
          @click="emit('save')"
        >
          {{ saving ? t("common.saving") : t("common.save") }}
        </button>
        <button
          type="button"
          class="rounded-full border border-line/16 bg-panel-soft px-4 py-2 text-xs font-semibold uppercase tracking-[0.18em] text-muted transition hover:border-accent hover:text-accent disabled:opacity-60"
          :disabled="saving"
          @click="emit('reset')"
        >
          {{ t("common.reset") }}
        </button>
      </div>
    </div>
  </aside>
</template>
