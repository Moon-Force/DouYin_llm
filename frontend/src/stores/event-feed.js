import { computed, ref } from "vue";
import { defineStore } from "pinia";

const MAX_EVENTS = 30;
const MAX_SUGGESTIONS = 12;

export const EVENT_FILTER_DEFS = [
  { value: "comment", labelKey: "feed.eventType.comment" },
  { value: "gift", labelKey: "feed.eventType.gift" },
  { value: "member", labelKey: "feed.eventType.member" },
];

const DEFAULT_VISIBLE_EVENT_TYPES = EVENT_FILTER_DEFS.map((filter) => filter.value);
const VISIBLE_EVENT_TYPE_SET = new Set(DEFAULT_VISIBLE_EVENT_TYPES);
const FILTER_STORAGE_KEY = "live-prompter:selected-event-types";

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
  const validValues = new Set(EVENT_FILTER_DEFS.map((filter) => filter.value));
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

function persistSelectedEventTypes(selectedEventTypes) {
  if (typeof window === "undefined") {
    return;
  }

  try {
    window.localStorage.setItem(FILTER_STORAGE_KEY, JSON.stringify(selectedEventTypes));
  } catch {
    // Ignore storage write failures so filtering still works in restricted environments.
  }
}

function isVisibleEventType(eventType) {
  return VISIBLE_EVENT_TYPE_SET.has(`${eventType ?? ""}`);
}

function sanitizeVisibleEvents(events) {
  return Array.isArray(events) ? events.filter((event) => isVisibleEventType(event?.event_type)) : [];
}

export const useEventFeedStore = defineStore("eventFeed", () => {
  const selectedEventTypes = ref(loadSelectedEventTypes());
  const stats = ref(createEmptyStats(""));
  const events = ref([]);
  const suggestions = ref([]);

  const areAllEventTypesSelected = computed(
    () => selectedEventTypes.value.length === EVENT_FILTER_DEFS.length,
  );
  const filteredEvents = computed(() =>
    events.value.filter((event) => selectedEventTypes.value.includes(event.event_type)),
  );
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

  function hydrateEventFeed(payload) {
    stats.value = payload.stats || createEmptyStats(`${payload.room_id ?? ""}`);
    events.value = sanitizeVisibleEvents(payload.recent_events);
    suggestions.value = payload.recent_suggestions || [];
  }

  function ingestEvent(event) {
    if (!isVisibleEventType(event?.event_type)) {
      return;
    }

    events.value = [event, ...events.value].slice(0, MAX_EVENTS);
  }

  function ingestSuggestion(suggestion) {
    suggestions.value = [suggestion, ...suggestions.value].slice(0, MAX_SUGGESTIONS);
  }

  function updateStats(payload) {
    stats.value = payload;
  }

  function toggleEventType(eventType) {
    if (selectedEventTypes.value.includes(eventType)) {
      if (selectedEventTypes.value.length === 1) {
        return;
      }

      selectedEventTypes.value = selectedEventTypes.value.filter((value) => value !== eventType);
      persistSelectedEventTypes(selectedEventTypes.value);
      return;
    }

    selectedEventTypes.value = normalizeSelectedEventTypes([
      ...selectedEventTypes.value,
      eventType,
    ]);
    persistSelectedEventTypes(selectedEventTypes.value);
  }

  function selectAllEventTypes() {
    selectedEventTypes.value = [...DEFAULT_VISIBLE_EVENT_TYPES];
    persistSelectedEventTypes(selectedEventTypes.value);
  }

  function clearEvents() {
    events.value = [];
  }

  return {
    selectedEventTypes,
    stats,
    events,
    suggestions,
    areAllEventTypesSelected,
    filteredEvents,
    activeSuggestion,
    activeSourceEvent,
    hydrateEventFeed,
    ingestEvent,
    ingestSuggestion,
    updateStats,
    toggleEventType,
    selectAllEventTypes,
    clearEvents,
  };
});
