import { computed, ref } from "vue";
import { defineStore } from "pinia";

const MAX_EVENTS = 30;
const MAX_SUGGESTIONS = 12;
const VISIBLE_EVENT_TYPES = new Set(["comment", "gift"]);

export const useLiveStore = defineStore("live", () => {
  const roomId = ref("32137571630");
  const connectionState = ref("connecting");
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

  async function bootstrap() {
    const response = await fetch("/api/bootstrap");
    const payload = await response.json();
    roomId.value = payload.room_id;
    stats.value = payload.stats;
    modelStatus.value = payload.model_status || modelStatus.value;
    events.value = (payload.recent_events || []).filter((event) =>
      VISIBLE_EVENT_TYPES.has(event.event_type),
    );
    suggestions.value = payload.recent_suggestions || [];
  }

  function ingestEvent(event) {
    if (!VISIBLE_EVENT_TYPES.has(event.event_type)) {
      return;
    }
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

  return {
    roomId,
    connectionState,
    modelStatus,
    stats,
    events,
    suggestions,
    activeSuggestion,
    bootstrap,
    connect,
  };
});
