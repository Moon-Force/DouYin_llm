<script setup>
defineProps({
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
  stats: {
    type: Object,
    required: true,
  },
});

defineEmits(["update-room-draft", "switch-room", "toggle-theme"]);
</script>

<template>
  <header
    class="relative grid gap-3 rounded-[28px] border border-line/14 bg-panel/92 p-5 pr-20 shadow-[var(--shadow-elev)] backdrop-blur lg:grid-cols-[1.7fr_repeat(4,minmax(0,1fr))]"
  >
    <button
      type="button"
      class="absolute right-5 top-5 inline-flex h-11 w-11 items-center justify-center rounded-full border border-line/16 bg-panel-soft text-paper shadow-sm transition hover:bg-panel-soft/88"
      :title="nextThemeLabel"
      :aria-label="nextThemeLabel"
      @click="$emit('toggle-theme')"
    >
      <svg
        v-if="theme === 'dark'"
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

    <div>
      <p class="text-[11px] uppercase tracking-[0.3em] text-muted">Room</p>
      <p class="mt-2 text-lg font-medium text-paper">{{ roomId || "未选择房间" }}</p>

      <div class="mt-3 flex flex-col gap-2 sm:flex-row">
        <input
          :value="roomDraft"
          type="text"
          inputmode="numeric"
          placeholder="输入房间号"
          class="w-full rounded-full border border-line/16 bg-panel-soft px-4 py-2 text-sm text-paper shadow-sm outline-none transition placeholder:text-muted focus:border-accent focus:ring-2 focus:ring-accent/20"
          @input="$emit('update-room-draft', $event.target.value)"
          @keyup.enter="$emit('switch-room')"
        />
        <button
          type="button"
          class="rounded-full border border-accent/55 bg-accent/14 px-4 py-2 text-xs uppercase tracking-[0.18em] text-accent shadow-sm transition hover:bg-accent/20 disabled:cursor-not-allowed disabled:opacity-60"
          :disabled="isSwitchingRoom"
          @click="$emit('switch-room')"
        >
          {{ isSwitchingRoom ? "切换中" : "切换房间" }}
        </button>
      </div>

      <div class="mt-2 flex items-center gap-3 text-xs">
        <p v-if="roomError" class="text-rose-500">{{ roomError }}</p>
      </div>
    </div>

    <div>
      <p class="text-[11px] uppercase tracking-[0.3em] text-muted">Connection</p>
      <p class="mt-2 text-lg font-medium text-accent">{{ connectionState }}</p>
    </div>

    <div>
      <p class="text-[11px] uppercase tracking-[0.3em] text-muted">Comments</p>
      <p class="mt-2 text-lg font-medium text-paper">{{ stats.comments }}</p>
    </div>

    <div>
      <p class="text-[11px] uppercase tracking-[0.3em] text-muted">Model</p>
      <p class="mt-2 text-sm font-medium text-paper">
        {{ modelStatus.model }} / {{ modelStatus.last_result }}
      </p>
      <p class="mt-1 text-xs text-muted">
        {{ modelStatus.last_error || modelStatus.mode }}
      </p>
    </div>

    <div>
      <p class="text-[11px] uppercase tracking-[0.3em] text-muted">Total Events</p>
      <p class="mt-2 text-lg font-medium text-paper">{{ stats.total_events }}</p>
    </div>
  </header>
</template>
