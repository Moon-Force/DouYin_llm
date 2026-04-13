<script setup>
defineProps({
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
  "update-system-prompt",
  "save",
  "reset",
]);
</script>

<template>
  <aside
    v-if="open"
    class="fixed inset-y-6 left-6 z-40 w-[480px] overflow-y-auto rounded-[30px] border border-line/16 bg-panel p-6 shadow-[var(--shadow-elev)]"
  >
    <div class="flex items-center justify-between pb-4">
      <div>
        <p class="text-lg font-semibold tracking-tight text-paper">LLM Settings</p>
        <p class="mt-1 text-xs text-muted">Persisted in SQLite and applied to future suggestions.</p>
      </div>
      <button
        type="button"
        class="text-sm font-medium text-muted transition hover:text-accent"
        @click="emit('close')"
      >
        Close
      </button>
    </div>

    <div class="space-y-5 text-sm text-paper">
      <label class="block space-y-2">
        <span class="text-xs font-semibold uppercase tracking-[0.18em] text-muted">Model</span>
        <input
          class="w-full rounded-xl border border-line/40 bg-panel-soft px-3 py-2 text-sm text-paper outline-none transition focus:border-accent"
          :value="draft.model"
          @input="emit('update-model', $event.target.value)"
        />
        <p class="text-[11px] text-muted">Default: {{ defaults.defaultModel || "N/A" }}</p>
      </label>

      <label class="block space-y-2">
        <span class="text-xs font-semibold uppercase tracking-[0.18em] text-muted">System Prompt</span>
        <textarea
          class="min-h-[220px] w-full rounded-xl border border-line/40 bg-panel-soft px-3 py-3 text-sm text-paper outline-none transition focus:border-accent"
          :value="draft.systemPrompt"
          @input="emit('update-system-prompt', $event.target.value)"
        ></textarea>
        <p class="text-[11px] text-muted">
          Reset returns to the default prompt from the backend.
        </p>
      </label>

      <p v-if="error" class="text-sm text-rose-500">{{ error }}</p>

      <div class="flex items-center gap-3">
        <button
          type="button"
          class="rounded-full bg-accent px-4 py-2 text-xs font-semibold uppercase tracking-[0.18em] text-ink transition hover:bg-accent/90 disabled:opacity-60"
          :disabled="saving"
          @click="emit('save')"
        >
          {{ saving ? "Saving..." : "Save" }}
        </button>
        <button
          type="button"
          class="rounded-full border border-line/16 bg-panel-soft px-4 py-2 text-xs font-semibold uppercase tracking-[0.18em] text-muted transition hover:border-accent hover:text-accent disabled:opacity-60"
          :disabled="saving"
          @click="emit('reset')"
        >
          Reset
        </button>
      </div>
    </div>
  </aside>
</template>
