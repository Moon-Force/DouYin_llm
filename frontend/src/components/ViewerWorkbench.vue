<script setup>
import { computed } from "vue";

import { translate, translateError } from "../i18n.js";
import {
  canReactivateViewerMemory,
  canTogglePinViewerMemory,
  getViewerMemoryBadges,
  getViewerMemoryLifecycleLabel,
  getViewerMemorySourceLabel,
  getViewerMemoryTimelinePreview,
} from "./viewer-memory-presenter.js";

const props = defineProps({
  locale: {
    type: String,
    required: true,
  },
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
  memoryDraft: {
    type: Object,
    default: () => ({
      memoryText: "",
      memoryType: "fact",
      isPinned: false,
      correctionReason: "",
    }),
  },
  editingMemoryId: {
    type: String,
    default: "",
  },
  memoryLogsById: {
    type: Object,
    default: () => ({}),
  },
});

const emit = defineEmits([
  "close",
  "update-note-draft",
  "toggle-note-pinned",
  "save-note",
  "edit-note",
  "delete-note",
  "update-memory-draft",
  "save-memory",
  "edit-memory",
  "invalidate-memory",
  "reactivate-memory",
  "delete-memory",
  "toggle-memory-pin",
  "load-memory-logs",
]);

function t(key, params) {
  return translate(props.locale, key, params);
}

function formatTimestamp(value) {
  const timestamp = Number(value);
  if (!timestamp) {
    return "";
  }

  const date = new Date(timestamp);
  if (Number.isNaN(date.getTime())) {
    return "";
  }

  return new Intl.DateTimeFormat(props.locale === "en" ? "en-US" : "zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

const errorMessage = computed(() => translateError(props.locale, props.error));
</script>

<template>
  <aside
    v-if="open"
    role="dialog"
    aria-modal="true"
    class="fixed inset-y-4 right-4 z-40 w-[420px] overflow-y-auto rounded-[30px] border border-line/16 bg-panel p-6 shadow-[var(--shadow-elev)]"
  >
    <div class="flex items-center justify-between pb-4">
      <p class="text-lg font-semibold tracking-tight text-paper">
        {{ t("viewerWorkbench.title") }}
      </p>
      <button
        type="button"
        class="text-sm font-medium text-muted transition hover:text-accent"
        @click="emit('close')"
      >
        {{ t("common.close") }}
      </button>
    </div>

    <div v-if="loading" class="text-sm text-muted">{{ t("viewerWorkbench.loading") }}</div>
    <p v-else-if="errorMessage" class="text-sm text-rose-500">{{ errorMessage }}</p>

    <div v-else-if="viewer" class="space-y-5 text-sm text-paper">
      <section class="space-y-2">
        <p class="text-2xl font-semibold">{{ viewer.nickname || t("common.unknownUser") }}</p>
        <p class="text-xs uppercase tracking-widest text-muted">{{ viewer.viewer_id }}</p>
        <div class="flex flex-wrap gap-4 text-xs uppercase tracking-wide text-muted">
          <p>{{ t("common.comments") }} {{ viewer.comment_count ?? 0 }}</p>
          <p>{{ t("common.gifts") }} {{ viewer.gift_event_count ?? 0 }}</p>
          <p>{{ t("common.totalGifts") }} {{ viewer.total_gift_count ?? 0 }}</p>
          <p>{{ t("common.totalDiamonds") }} {{ viewer.total_diamond_count ?? 0 }}</p>
        </div>
        <div class="grid gap-2 md:grid-cols-2">
          <p
            v-if="viewer.last_comment"
            class="rounded-xl border border-line/20 bg-surface px-3 py-2 text-xs leading-relaxed text-paper"
          >
            {{ t("common.lastComment") }}: {{ viewer.last_comment }}
          </p>
          <p
            v-if="viewer.last_gift_name"
            class="rounded-xl border border-line/20 bg-surface px-3 py-2 text-xs leading-relaxed text-paper"
          >
            {{ t("common.lastGift") }}: {{ viewer.last_gift_name }}
          </p>
          <p
            v-if="viewer.first_seen_at"
            class="rounded-xl border border-line/20 bg-surface px-3 py-2 text-xs leading-relaxed text-paper"
          >
            {{ t("common.firstSeen") }}: {{ viewer.first_seen_at }}
          </p>
          <p
            v-if="viewer.last_seen_at"
            class="rounded-xl border border-line/20 bg-surface px-3 py-2 text-xs leading-relaxed text-paper"
          >
            {{ t("common.lastSeen") }}: {{ viewer.last_seen_at }}
          </p>
        </div>
      </section>

      <section class="space-y-3">
        <p class="text-xs font-semibold uppercase tracking-widest text-muted">
          {{ t("viewerWorkbench.memories") }}
        </p>

        <div class="space-y-2 rounded-xl border border-line/20 bg-surface px-3 py-3">
          <textarea
            class="w-full rounded-xl border border-line/40 bg-panel px-3 py-2 text-xs text-paper outline-none transition placeholder:text-muted focus:border-accent"
            rows="3"
            :value="memoryDraft.memoryText"
            :placeholder="t('viewerWorkbench.memoryPlaceholder')"
            :disabled="saving || !viewer.viewer_id"
            @input="emit('update-memory-draft', { memoryText: $event.target.value })"
          ></textarea>

          <input
            class="w-full rounded-xl border border-line/40 bg-panel px-3 py-2 text-xs text-paper outline-none transition placeholder:text-muted focus:border-accent"
            :value="memoryDraft.memoryType"
            :placeholder="t('viewerWorkbench.memoryTypePlaceholder')"
            :disabled="saving || !viewer.viewer_id"
            @input="emit('update-memory-draft', { memoryType: $event.target.value })"
          />

          <input
            class="w-full rounded-xl border border-line/40 bg-panel px-3 py-2 text-xs text-paper outline-none transition placeholder:text-muted focus:border-accent"
            :value="memoryDraft.correctionReason"
            :placeholder="t('viewerWorkbench.memoryReasonPlaceholder')"
            :disabled="saving || !viewer.viewer_id"
            @input="emit('update-memory-draft', { correctionReason: $event.target.value })"
          />

          <div class="flex items-center justify-between gap-3 text-xs text-muted">
            <button
              type="button"
              class="font-semibold text-paper transition hover:text-accent"
              :disabled="saving || !viewer.viewer_id"
              @click="emit('update-memory-draft', { isPinned: !memoryDraft.isPinned })"
            >
              {{ memoryDraft.isPinned ? t("viewerWorkbench.unpinMemory") : t("viewerWorkbench.pinMemory") }}
            </button>
            <button
              type="button"
              class="rounded-full bg-accent px-3 py-1 text-[11px] font-semibold text-ink transition hover:bg-accent/90 disabled:opacity-60"
              :disabled="saving || !viewer.viewer_id || !memoryDraft.memoryText.trim()"
              @click="emit('save-memory')"
            >
              {{
                saving
                  ? t("common.saving")
                  : editingMemoryId
                    ? t("viewerWorkbench.updateMemory")
                    : t("viewerWorkbench.saveMemory")
              }}
            </button>
          </div>
        </div>

        <article
          v-for="memory in viewer.memories || []"
          :key="memory.memory_id"
          class="rounded-xl border border-line/20 bg-surface px-3 py-3"
        >
          <p class="text-xs leading-relaxed text-paper">{{ memory.memory_text }}</p>
          <div class="mt-2 flex flex-wrap gap-2 text-[11px] uppercase tracking-[0.14em] text-muted">
            <span v-for="badgeKey in getViewerMemoryBadges(memory)" :key="badgeKey">
              {{ t(badgeKey) }}
            </span>
            <span>{{ t(getViewerMemorySourceLabel(memory)) }}</span>
            <span>{{ t(getViewerMemoryLifecycleLabel(memory)) }}</span>
            <span>{{ memory.memory_type || "fact" }}</span>
            <span>{{ t("viewerWorkbench.memoryConfidence") }} {{ memory.confidence ?? 0 }}</span>
            <span>{{ t("viewerWorkbench.memoryRecall") }} {{ memory.recall_count ?? 0 }}</span>
          </div>
          <p class="mt-2 text-[11px] text-muted">
            {{ t(getViewerMemoryTimelinePreview(memory).labelKey) }}
            <span v-if="getViewerMemoryTimelinePreview(memory).reason">
              ：{{ getViewerMemoryTimelinePreview(memory).reason }}
            </span>
          </p>
          <p
            v-if="getViewerMemoryTimelinePreview(memory).recalledAt"
            class="mt-1 text-[11px] text-muted"
          >
            {{ t("viewerWorkbench.lastRecalledAt") }}:
            {{ formatTimestamp(getViewerMemoryTimelinePreview(memory).recalledAt) }}
          </p>
          <div class="mt-3 flex flex-wrap gap-3 text-[11px] text-muted">
            <button
              type="button"
              class="font-semibold text-paper transition hover:text-accent disabled:opacity-60"
              :disabled="saving"
              @click="emit('edit-memory', memory)"
            >
              {{ t("common.edit") }}
            </button>
            <button
              v-if="memory.status === 'active'"
              type="button"
              class="font-semibold text-paper transition hover:text-accent disabled:opacity-60"
              :disabled="saving"
              @click="emit('invalidate-memory', memory.memory_id, memory.correction_reason || t('viewerWorkbench.defaultInvalidateReason'))"
            >
              {{ t("viewerWorkbench.invalidateMemory") }}
            </button>
            <button
              v-if="canReactivateViewerMemory(memory)"
              type="button"
              class="font-semibold text-paper transition hover:text-accent disabled:opacity-60"
              :disabled="saving"
              @click="emit('reactivate-memory', memory.memory_id, memory.correction_reason || t('viewerWorkbench.defaultReactivateReason'))"
            >
              {{ t("viewerWorkbench.reactivateMemory") }}
            </button>
            <button
              v-if="canTogglePinViewerMemory(memory)"
              type="button"
              class="font-semibold text-paper transition hover:text-accent disabled:opacity-60"
              :disabled="saving"
              @click="emit('toggle-memory-pin', memory)"
            >
              {{ memory.is_pinned ? t("viewerWorkbench.unpinMemory") : t("viewerWorkbench.pinMemory") }}
            </button>
            <button
              type="button"
              class="font-semibold text-rose-500 transition hover:text-rose-400 disabled:opacity-60"
              :disabled="saving"
              @click="emit('delete-memory', memory.memory_id, memory.correction_reason || t('viewerWorkbench.defaultDeleteReason'))"
            >
              {{ t("common.delete") }}
            </button>
            <button
              type="button"
              class="font-semibold text-paper transition hover:text-accent disabled:opacity-60"
              :disabled="saving"
              @click="emit('load-memory-logs', memory.memory_id)"
            >
              {{ t("viewerWorkbench.loadMemoryTimeline") }}
            </button>
          </div>

          <div
            v-if="memoryLogsById[memory.memory_id]"
            class="mt-3 rounded-2xl border border-line/20 bg-panel/60 px-3 py-3"
          >
            <p class="text-[10px] font-semibold uppercase tracking-[0.18em] text-muted">
              {{ t("viewerWorkbench.memoryTimelineTitle") }}
            </p>
            <p
              v-if="memoryLogsById[memory.memory_id]?.loading"
              class="mt-2 text-[11px] text-muted"
            >
              {{ t("viewerWorkbench.memoryTimelineLoading") }}
            </p>
            <p
              v-else-if="memoryLogsById[memory.memory_id]?.error"
              class="mt-2 text-[11px] text-rose-500"
            >
              {{ memoryLogsById[memory.memory_id].error }}
            </p>
            <div
              v-else-if="memoryLogsById[memory.memory_id]?.items?.length"
              class="mt-3 space-y-3 border-l border-line/30 pl-4"
            >
              <div
                v-for="log in memoryLogsById[memory.memory_id].items"
                :key="log.log_id"
                class="relative pl-1 text-[11px] text-muted"
              >
                <span
                  class="absolute -left-[21px] top-1.5 h-2.5 w-2.5 rounded-full bg-accent"
                ></span>
                <p class="font-semibold text-paper">
                  {{ t(`viewerWorkbench.timeline.${log.operation}`) }}
                </p>
                <p class="mt-1 text-[10px] uppercase tracking-[0.14em] text-muted">
                  <span v-if="formatTimestamp(log.created_at)">
                    {{ formatTimestamp(log.created_at) }}
                  </span>
                  <span v-if="log.operator">
                    {{ formatTimestamp(log.created_at) ? " · " : "" }}
                    {{ t("viewerWorkbench.memoryTimelineOperator") }} {{ log.operator }}
                  </span>
                </p>
                <p v-if="log.reason" class="mt-1 leading-relaxed">{{ log.reason }}</p>
              </div>
            </div>
            <p v-else class="mt-2 text-[11px] text-muted">
              {{ t("viewerWorkbench.memoryTimelineEmpty") }}
            </p>
          </div>
        </article>

        <p v-if="!(viewer.memories && viewer.memories.length)" class="text-xs text-muted">
          {{ t("viewerWorkbench.noMemories") }}
        </p>
      </section>

      <section class="space-y-3">
        <p class="text-xs font-semibold uppercase tracking-widest text-muted">
          {{ t("viewerWorkbench.notes") }}
        </p>
        <div class="space-y-2 rounded-xl border border-line/20 bg-surface px-3 py-3">
          <textarea
            class="w-full rounded-xl border border-line/40 bg-panel px-3 py-2 text-xs text-paper outline-none transition placeholder:text-muted focus:border-accent"
            rows="3"
            :value="noteDraft"
            :placeholder="t('viewerWorkbench.notePlaceholder')"
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
              {{ notePinned ? t("viewerWorkbench.unpinNote") : t("viewerWorkbench.pinNote") }}
            </button>
            <button
              type="button"
              class="rounded-full bg-accent px-3 py-1 text-[11px] font-semibold text-ink transition hover:bg-accent/90 disabled:opacity-60"
              :disabled="saving || !viewer.viewer_id || !noteDraft.trim()"
              @click="emit('save-note')"
            >
              {{
                saving
                  ? t("common.saving")
                  : editingNoteId
                    ? t("viewerWorkbench.updateNote")
                    : t("viewerWorkbench.saveNote")
              }}
            </button>
          </div>

          <p v-if="editingNoteId" class="text-[11px] text-muted">
            {{ t("viewerWorkbench.editing") }} {{ editingNoteId }}
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
              {{ t("common.pinned") }}
            </span>
          </div>
          <div class="mt-3 flex gap-3 text-[11px] text-muted">
            <button
              type="button"
              class="font-semibold text-paper transition hover:text-accent disabled:opacity-60"
              :disabled="saving"
              @click="emit('edit-note', note)"
            >
              {{ t("common.edit") }}
            </button>
            <button
              type="button"
              class="font-semibold text-rose-500 transition hover:text-rose-400 disabled:opacity-60"
              :disabled="saving"
              @click="emit('delete-note', note.note_id)"
            >
              {{ t("common.delete") }}
            </button>
          </div>
        </article>

        <p v-if="!(viewer.notes && viewer.notes.length)" class="text-xs text-muted">
          {{ t("viewerWorkbench.noNotes") }}
        </p>
        <p v-if="!viewer.viewer_id" class="text-xs text-muted">
          {{ t("viewerWorkbench.notesNeedViewerId") }}
        </p>
      </section>

      <section class="space-y-2">
        <p class="text-xs font-semibold uppercase tracking-widest text-muted">
          {{ t("viewerWorkbench.recentComments") }}
        </p>
        <article
          v-for="comment in viewer.recent_comments || []"
          :key="comment.event_id"
          class="rounded-xl border border-line/20 bg-surface px-3 py-2"
        >
          <p class="text-xs leading-relaxed text-paper">
            {{ comment.content || t("viewerWorkbench.emptyContent") }}
          </p>
        </article>
        <p
          v-if="!(viewer.recent_comments && viewer.recent_comments.length)"
          class="text-xs text-muted"
        >
          {{ t("viewerWorkbench.noRecentComments") }}
        </p>
      </section>

      <section class="space-y-2">
        <p class="text-xs font-semibold uppercase tracking-widest text-muted">
          {{ t("viewerWorkbench.recentGiftEvents") }}
        </p>
        <article
          v-for="gift in viewer.recent_gift_events || []"
          :key="gift.event_id"
          class="rounded-xl border border-line/20 bg-surface px-3 py-2"
        >
          <p class="text-xs leading-relaxed text-paper">
            {{ gift.gift_name || gift.content || t("viewerWorkbench.emptyContent") }}
          </p>
        </article>
        <p
          v-if="!(viewer.recent_gift_events && viewer.recent_gift_events.length)"
          class="text-xs text-muted"
        >
          {{ t("viewerWorkbench.noRecentGiftEvents") }}
        </p>
      </section>

      <section class="space-y-2">
        <p class="text-xs font-semibold uppercase tracking-widest text-muted">
          {{ t("viewerWorkbench.recentSessions") }}
        </p>
        <article
          v-for="session in viewer.recent_sessions || []"
          :key="session.session_id"
          class="rounded-xl border border-line/20 bg-surface px-3 py-2"
        >
          <p class="text-xs leading-relaxed text-paper">
            {{
              t("viewerWorkbench.sessionSummary", {
                sessionId: session.session_id,
                comments: session.comment_count ?? 0,
                gifts: session.gift_event_count ?? 0,
              })
            }}
          </p>
        </article>
        <p
          v-if="!(viewer.recent_sessions && viewer.recent_sessions.length)"
          class="text-xs text-muted"
        >
          {{ t("viewerWorkbench.noRecentSessions") }}
        </p>
      </section>
    </div>

    <p v-else class="text-sm text-muted">{{ t("viewerWorkbench.selectHint") }}</p>
  </aside>
</template>
