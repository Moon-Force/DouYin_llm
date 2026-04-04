import { computed, ref } from "vue";
import { defineStore } from "pinia";

const MAX_EVENTS = 30;
const MAX_SUGGESTIONS = 12;
const DEFAULT_VISIBLE_EVENT_TYPES = ["comment", "gift"];
const EVENT_FILTERS = [
  { value: "comment", label: "弹幕" },
  { value: "gift", label: "礼物" },
  { value: "follow", label: "关注" },
  { value: "member", label: "进场" },
  { value: "like", label: "点赞" },
  { value: "system", label: "系统" },
];

export const useLiveStore = defineStore("live", () => {
  const roomId = ref("32137571630");
  const connectionState = ref("connecting");
  const selectedEventTypes = ref([...DEFAULT_VISIBLE_EVENT_TYPES]);
  const modelStatus = ref({
    mode: "heuristic",
    model: "heuristic",
    backend: "local",
    last_result: "idle",
    last_error: "",
    updated_at: 0,
  });
  const stats = ref({
    room_id: roomId.value,
    total_events: 0,
    comments: 0,
    gifts: 0,
    likes: 0,
    members: 0,
    follows: 0,
  });
  const events = ref([]);
  const suggestions = ref([]);
  let eventSource;

  const activeSuggestion = computed(() => suggestions.value[0] || null);
  const filteredEvents = computed(() =>
    events.value.filter((event) => selectedEventTypes.value.includes(event.event_type)),
  );

  async function bootstrap() {
    const response = await fetch("/api/bootstrap");
    const payload = await response.json();
    roomId.value = payload.room_id;
    stats.value = payload.stats;
    modelStatus.value = payload.model_status || modelStatus.value;
    events.value = payload.recent_events || [];
    suggestions.value = payload.recent_suggestions || [];
  }

  function ingestEvent(event) {
    events.value = [event, ...events.value].slice(0, MAX_EVENTS);
  }

  function ingestSuggestion(suggestion) {
    suggestions.value = [suggestion, ...suggestions.value].slice(0, MAX_SUGGESTIONS);
  }

  function connect() {
    if (eventSource) {
      eventSource.close();
    }

    eventSource = new EventSource("/api/events/stream");
    connectionState.value = "connecting";

    eventSource.onopen = () => {
      connectionState.value = "live";
    };

    eventSource.onerror = () => {
      connectionState.value = "reconnecting";
    };

    eventSource.addEventListener("event", (message) => {
      ingestEvent(JSON.parse(message.data));
    });

    eventSource.addEventListener("suggestion", (message) => {
      ingestSuggestion(JSON.parse(message.data));
    });

    eventSource.addEventListener("stats", (message) => {
      stats.value = JSON.parse(message.data);
    });

    eventSource.addEventListener("model_status", (message) => {
      modelStatus.value = JSON.parse(message.data);
    });
  }

  function toggleEventType(eventType) {
    if (selectedEventTypes.value.includes(eventType)) {
      selectedEventTypes.value = selectedEventTypes.value.filter((value) => value !== eventType);
      return;
    }

    selectedEventTypes.value = [...selectedEventTypes.value, eventType];
  }

  return {
    roomId,
    connectionState,
    selectedEventTypes,
    eventFilters: EVENT_FILTERS,
    modelStatus,
    stats,
    events,
    filteredEvents,
    suggestions,
    activeSuggestion,
    bootstrap,
    connect,
    toggleEventType,
  };
});
