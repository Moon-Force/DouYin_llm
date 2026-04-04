<script setup>
defineProps({
  events: {
    type: Array,
    required: true,
  },
});

function badge(eventType) {
  switch (eventType) {
    case "comment":
      return "弹幕";
    case "gift":
      return "礼物";
    case "follow":
      return "关注";
    case "member":
      return "进场";
    case "like":
      return "点赞";
    default:
      return "系统";
  }
}
</script>

<template>
  <section class="rounded-[28px] border border-white/8 bg-panel-soft/80 p-6">
    <p class="text-[11px] uppercase tracking-[0.3em] text-muted">Live Feed</p>
    <div class="mt-5 space-y-3">
      <article
        v-for="event in events.slice(0, 10)"
        :key="event.event_id"
        class="rounded-2xl border border-white/6 bg-white/4 p-4"
      >
        <div class="flex items-center justify-between gap-3 text-xs uppercase tracking-[0.2em] text-muted">
          <span>{{ badge(event.event_type) }}</span>
          <span>{{ event.user.nickname }}</span>
        </div>
        <p class="mt-3 text-sm leading-6 text-paper">
          {{ event.content || event.metadata?.gift_name || event.method }}
        </p>
      </article>
    </div>
  </section>
</template>
