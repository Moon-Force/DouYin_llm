import { computed, ref } from "vue";
import { defineStore } from "pinia";

const MAX_EVENTS = 30;
const MAX_SUGGESTIONS = 12;

const EVENT_FILTERS = [
  { value: "comment", label: "弹幕" },
  { value: "gift", label: "礼物" },
  { value: "follow", label: "关注" },
  { value: "member", label: "进场" },
  { value: "like", label: "点赞" },
  { value: "system", label: "系统" },
];

const DEFAULT_VISIBLE_EVENT_TYPES = EVENT_FILTERS.map((filter) => filter.value);
const FILTER_STORAGE_KEY = "live-prompter:selected-event-types";
const THEME_STORAGE_KEY = "live-prompter:theme";

function createEmptyStats(roomId) {
  return {
    room_id: roomId,
    total_events: 0,
    comments: 0,
    gifts: 0,
    likes: 0,
    members: 0,
    follows: 0,
  };
}

function normalizeSelectedEventTypes(eventTypes) {
  const validValues = new Set(EVENT_FILTERS.map((filter) => filter.value));
  const normalized = Array.isArray(eventTypes)
    ? eventTypes.filter((eventType) => validValues.has(eventType))
    : [];

  return normalized.length > 0 ? [...new Set(normalized)] : [...DEFAULT_VISIBLE_EVENT_TYPES];
}

function loadSelectedEventTypes() {
  if (typeof window === "undefined") {
    return [...DEFAULT_VISIBLE_EVENT_TYPES];
  }

  try {
    const rawValue = window.localStorage.getItem(FILTER_STORAGE_KEY);
    return normalizeSelectedEventTypes(rawValue ? JSON.parse(rawValue) : DEFAULT_VISIBLE_EVENT_TYPES);
  } catch {
    return [...DEFAULT_VISIBLE_EVENT_TYPES];
  }
}

function loadTheme() {
  if (typeof window === "undefined") {
    return "dark";
  }

  return window.localStorage.getItem(THEME_STORAGE_KEY) === "light" ? "light" : "dark";
}

function applyTheme(theme) {
  if (typeof document === "undefined") {
    return;
  }

  document.documentElement.dataset.theme = theme;
}

export const useLiveStore = defineStore("live", () => {
  const roomId = ref("");
  const roomDraft = ref("");
  const theme = ref(loadTheme());
  const isSwitchingRoom = ref(false);
  const roomError = ref("");
  const connectionState = ref("idle");
  const eventFilters = ref(EVENT_FILTERS);
  const selectedEventTypes = ref(loadSelectedEventTypes());
  const modelStatus = ref({
    mode: "heuristic",
    model: "heuristic",
    backend: "local",
    last_result: "idle",
    last_error: "",
    updated_at: 0,
  });
  const stats = ref(createEmptyStats(""));
  const events = ref([]);
  const suggestions = ref([]);
  let eventSource;

  const activeSuggestion = computed(() => suggestions.value[0] || null);
  const activeSourceEvent = computed(() => {
    if (!activeSuggestion.value) {
      return null;
    }

    const sourceEventIds = new Set([
      activeSuggestion.value.event_id,
      ...(activeSuggestion.value.source_events || []),
    ]);

    return events.value.find((event) => sourceEventIds.has(event.event_id)) || null;
  });
  const nextThemeLabel = computed(() => (theme.value === "dark" ? "切换白色" : "切换黑色"));
  const areAllEventTypesSelected = computed(
    () => selectedEventTypes.value.length === EVENT_FILTERS.length,
  );
  const filteredEvents = computed(() =>
    events.value.filter((event) => selectedEventTypes.value.includes(event.event_type)),
  );

  function persistSelectedEventTypes() {
    if (typeof window === "undefined") {
      return;
    }

    window.localStorage.setItem(FILTER_STORAGE_KEY, JSON.stringify(selectedEventTypes.value));
  }

  function persistTheme() {
    if (typeof window === "undefined") {
      return;
    }

    window.localStorage.setItem(THEME_STORAGE_KEY, theme.value);
  }

  function hydrateSnapshot(payload) {
    roomId.value = `${payload.room_id ?? ""}`;
    stats.value = payload.stats || createEmptyStats(roomId.value);
    modelStatus.value = payload.model_status || modelStatus.value;
    events.value = payload.recent_events || [];
    suggestions.value = payload.recent_suggestions || [];
    if (!roomId.value) {
      connectionState.value = "idle";
    }
  }

  function closeStream() {
    if (eventSource) {
      eventSource.close();
      eventSource = undefined;
    }
  }

  function setRoomDraft(value) {
    roomDraft.value = `${value ?? ""}`;
  }

  function setTheme(nextTheme) {
    theme.value = nextTheme === "light" ? "light" : "dark";
    applyTheme(theme.value);
    persistTheme();
  }

  function toggleTheme() {
    setTheme(theme.value === "dark" ? "light" : "dark");
  }

  async function bootstrap(targetRoomId = roomId.value) {
    const normalizedRoomId = `${targetRoomId ?? ""}`.trim();
    const url = normalizedRoomId
      ? `/api/bootstrap?${new URLSearchParams({ room_id: normalizedRoomId }).toString()}`
      : "/api/bootstrap";
    const response = await fetch(url);
    const payload = await response.json();
    hydrateSnapshot(payload);
  }

  function ingestEvent(event) {
    events.value = [event, ...events.value].slice(0, MAX_EVENTS);
  }

  function ingestSuggestion(suggestion) {
    suggestions.value = [suggestion, ...suggestions.value].slice(0, MAX_SUGGESTIONS);
  }

  function connect(targetRoomId = roomId.value) {
    closeStream();
    const normalizedRoomId = `${targetRoomId ?? ""}`.trim();
    if (!normalizedRoomId) {
      connectionState.value = "idle";
      return;
    }

    const query = new URLSearchParams({ room_id: normalizedRoomId });
    eventSource = new EventSource(`/api/events/stream?${query.toString()}`);

    connectionState.value = "connecting";

    eventSource.onopen = () => {
      connectionState.value = "live";
      roomError.value = "";
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

  async function switchRoom(nextRoomId = roomDraft.value) {
    const targetRoomId = `${nextRoomId ?? ""}`.trim();
    if (!targetRoomId) {
      roomError.value = "请输入房间号";
      return;
    }

    if (targetRoomId === roomId.value) {
      roomDraft.value = "";
      roomError.value = "";
      return;
    }

    isSwitchingRoom.value = true;
    roomError.value = "";
    connectionState.value = "switching";
    closeStream();

    try {
      const response = await fetch("/api/room", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ room_id: targetRoomId }),
      });

      if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        throw new Error(payload.detail || "切换房间失败");
      }

      const payload = await response.json();
      hydrateSnapshot(payload);
      roomDraft.value = "";
      connect(payload.room_id || targetRoomId);
    } catch (error) {
      roomError.value = error instanceof Error ? error.message : "切换房间失败";
      await bootstrap(roomId.value);
      connect(roomId.value);
    } finally {
      isSwitchingRoom.value = false;
    }
  }

  function toggleEventType(eventType) {
    if (selectedEventTypes.value.includes(eventType)) {
      if (selectedEventTypes.value.length === 1) {
        return;
      }

      selectedEventTypes.value = selectedEventTypes.value.filter((value) => value !== eventType);
      persistSelectedEventTypes();
      return;
    }

    selectedEventTypes.value = normalizeSelectedEventTypes([
      ...selectedEventTypes.value,
      eventType,
    ]);
    persistSelectedEventTypes();
  }

  function selectAllEventTypes() {
    selectedEventTypes.value = [...DEFAULT_VISIBLE_EVENT_TYPES];
    persistSelectedEventTypes();
  }

  function clearEvents() {
    events.value = [];
  }

  applyTheme(theme.value);

  return {
    roomId,
    roomDraft,
    theme,
    nextThemeLabel,
    isSwitchingRoom,
    roomError,
    connectionState,
    selectedEventTypes,
    eventFilters,
    modelStatus,
    stats,
    areAllEventTypesSelected,
    events,
    filteredEvents,
    suggestions,
    activeSuggestion,
    activeSourceEvent,
    bootstrap,
    connect,
    setRoomDraft,
    setTheme,
    toggleTheme,
    switchRoom,
    toggleEventType,
    selectAllEventTypes,
    clearEvents,
  };
});
