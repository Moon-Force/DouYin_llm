<script setup>
defineProps({
  open: {
    type: Boolean,
    required: true,
  },
  viewer: {
    type: Object,
    default: null,
  },
  loading: {
    type: Boolean,
    default: false,
  },
  error: {
    type: String,
    default: "",
  },
  noteDraft: {
    type: String,
    default: "",
  },
  notePinned: {
    type: Boolean,
    default: false,
  },
  saving: {
    type: Boolean,
    default: false,
  },
  editingNoteId: {
    type: String,
    default: "",
  },
});

const emit = defineEmits([
  "close",
  "update-note-draft",
  "toggle-note-pinned",
  "save-note",
  "edit-note",
  "delete-note",
]);
</script>

<template>
  <aside
    v-if="open"
    role="dialog"
    aria-modal="true"
    class="fixed inset-y-4 right-4 z-40 w-[420px] overflow-y-auto rounded-[30px] border border-line/16 bg-panel p-6 shadow-[var(--shadow-elev)]"
  >
    <div class="flex items-center justify-between pb-4">
      <p class="text-lg font-semibold tracking-tight text-paper">Viewer Workbench</p>
      <button
        type="button"
        class="text-sm font-medium text-muted transition hover:text-accent"
        @click="emit('close')"
      >
        Close
      </button>
    </div>

    <div v-if="loading" class="text-sm text-muted">Loading viewer details...</div>
    <p v-else-if="error" class="text-sm text-rose-500">{{ error }}</p>

    <div v-else-if="viewer" class="space-y-5 text-sm text-paper">
      <section class="space-y-2">
        <p class="text-2xl font-semibold">{{ viewer.nickname || "Unknown viewer" }}</p>
        <p class="text-xs uppercase tracking-widest text-muted">{{ viewer.viewer_id }}</p>
        <div class="flex flex-wrap gap-4 text-xs uppercase tracking-wide text-muted">
          <p>Comments {{ viewer.comment_count ?? 0 }}</p>
          <p>Gifts {{ viewer.gift_event_count ?? 0 }}</p>
          <p>Total gifts {{ viewer.total_gift_count ?? 0 }}</p>
          <p>Total diamonds {{ viewer.total_diamond_count ?? 0 }}</p>
        </div>
        <div class="grid gap-2 md:grid-cols-2">
          <p
            v-if="viewer.last_comment"
            class="rounded-xl border border-line/20 bg-surface px-3 py-2 text-xs leading-relaxed text-paper"
          >
            Last comment: {{ viewer.last_comment }}
          </p>
          <p
            v-if="viewer.last_gift_name"
            class="rounded-xl border border-line/20 bg-surface px-3 py-2 text-xs leading-relaxed text-paper"
          >
            Last gift: {{ viewer.last_gift_name }}
          </p>
          <p
            v-if="viewer.first_seen_at"
            class="rounded-xl border border-line/20 bg-surface px-3 py-2 text-xs leading-relaxed text-paper"
          >
            First seen: {{ viewer.first_seen_at }}
          </p>
          <p
            v-if="viewer.last_seen_at"
            class="rounded-xl border border-line/20 bg-surface px-3 py-2 text-xs leading-relaxed text-paper"
          >
            Last seen: {{ viewer.last_seen_at }}
          </p>
        </div>
      </section>

      <section class="space-y-2">
        <p class="text-xs font-semibold uppercase tracking-widest text-muted">Memories</p>
        <article
          v-for="memory in viewer.memories || []"
          :key="memory.memory_id"
          class="rounded-xl border border-line/20 bg-surface px-3 py-2"
        >
          <p class="text-xs leading-relaxed text-paper">{{ memory.memory_text }}</p>
          <div class="mt-2 flex flex-wrap gap-3 text-[11px] uppercase tracking-[0.14em] text-muted">
            <span>{{ memory.memory_type || "fact" }}</span>
            <span>Confidence {{ memory.confidence ?? 0 }}</span>
            <span>Recalled {{ memory.recall_count ?? 0 }}</span>
          </div>
        </article>
        <p v-if="!(viewer.memories && viewer.memories.length)" class="text-xs text-muted">
          No memories recorded yet.
        </p>
      </section>

      <section class="space-y-3">
        <p class="text-xs font-semibold uppercase tracking-widest text-muted">Notes</p>
        <div class="space-y-2 rounded-xl border border-line/20 bg-surface px-3 py-3">
          <textarea
            class="w-full rounded-xl border border-line/40 bg-panel px-3 py-2 text-xs text-paper outline-none transition placeholder:text-muted focus:border-accent"
            rows="3"
            :value="noteDraft"
            placeholder="Write a note..."
            :disabled="saving || !viewer.viewer_id"
            @input="emit('update-note-draft', $event.target.value)"
          ></textarea>

          <div class="flex items-center justify-between gap-3 text-xs text-muted">
            <button
              type="button"
              class="font-semibold text-paper transition hover:text-accent"
              :disabled="saving || !viewer.viewer_id"
              @click="emit('toggle-note-pinned')"
            >
              {{ notePinned ? "Unpin note" : "Pin note" }}
            </button>
            <button
              type="button"
              class="rounded-full bg-accent px-3 py-1 text-[11px] font-semibold text-ink transition hover:bg-accent/90 disabled:opacity-60"
              :disabled="saving || !viewer.viewer_id || !noteDraft.trim()"
              @click="emit('save-note')"
            >
              {{ saving ? "Saving..." : editingNoteId ? "Update note" : "Save note" }}
            </button>
          </div>

          <p v-if="editingNoteId" class="text-[11px] text-muted">
            Editing {{ editingNoteId }}
          </p>
        </div>

        <article
          v-for="note in viewer.notes || []"
          :key="note.note_id"
          class="rounded-xl border border-line/20 bg-surface px-3 py-3"
        >
          <div class="flex items-center justify-between gap-3">
            <p class="text-xs leading-relaxed text-paper">{{ note.content }}</p>
            <span
              v-if="note.is_pinned"
              class="rounded-full border border-accent/50 px-2 py-1 text-[10px] uppercase tracking-[0.18em] text-accent"
            >
              Pinned
            </span>
          </div>
          <div class="mt-3 flex gap-3 text-[11px] text-muted">
            <button
              type="button"
              class="font-semibold text-paper transition hover:text-accent disabled:opacity-60"
              :disabled="saving"
              @click="emit('edit-note', note)"
            >
              Edit
            </button>
            <button
              type="button"
              class="font-semibold text-rose-500 transition hover:text-rose-400 disabled:opacity-60"
              :disabled="saving"
              @click="emit('delete-note', note.note_id)"
            >
              Delete
            </button>
          </div>
        </article>

        <p v-if="!(viewer.notes && viewer.notes.length)" class="text-xs text-muted">
          No notes yet.
        </p>
        <p v-if="!viewer.viewer_id" class="text-xs text-muted">
          Notes require a resolved viewer id.
        </p>
      </section>

      <section class="space-y-2">
        <p class="text-xs font-semibold uppercase tracking-widest text-muted">Recent Comments</p>
        <article
          v-for="comment in viewer.recent_comments || []"
          :key="comment.event_id"
          class="rounded-xl border border-line/20 bg-surface px-3 py-2"
        >
          <p class="text-xs leading-relaxed text-paper">{{ comment.content || "(empty)" }}</p>
        </article>
        <p v-if="!(viewer.recent_comments && viewer.recent_comments.length)" class="text-xs text-muted">
          No recent comments.
        </p>
      </section>

      <section class="space-y-2">
        <p class="text-xs font-semibold uppercase tracking-widest text-muted">Recent Gift Events</p>
        <article
          v-for="gift in viewer.recent_gift_events || []"
          :key="gift.event_id"
          class="rounded-xl border border-line/20 bg-surface px-3 py-2"
        >
          <p class="text-xs leading-relaxed text-paper">
            {{ gift.gift_name || gift.content || "(empty)" }}
          </p>
        </article>
        <p v-if="!(viewer.recent_gift_events && viewer.recent_gift_events.length)" class="text-xs text-muted">
          No recent gift events.
        </p>
      </section>

      <section class="space-y-2">
        <p class="text-xs font-semibold uppercase tracking-widest text-muted">Recent Sessions</p>
        <article
          v-for="session in viewer.recent_sessions || []"
          :key="session.session_id"
          class="rounded-xl border border-line/20 bg-surface px-3 py-2"
        >
          <p class="text-xs leading-relaxed text-paper">
            Session {{ session.session_id }} / comments {{ session.comment_count ?? 0 }} / gifts {{ session.gift_event_count ?? 0 }}
          </p>
        </article>
        <p v-if="!(viewer.recent_sessions && viewer.recent_sessions.length)" class="text-xs text-muted">
          No recent sessions.
        </p>
      </section>
    </div>

    <p v-else class="text-sm text-muted">Select a viewer to see details.</p>
  </aside>
</template>
