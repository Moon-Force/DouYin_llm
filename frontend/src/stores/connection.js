import { ref } from "vue";
import { defineStore } from "pinia";

import { bootstrapLiveState, switchLiveRoom } from "../api/live-api.js";

function createDefaultModelStatus() {
  return {
    mode: "heuristic",
    model: "heuristic",
    backend: "local",
    last_result: "idle",
    last_error: "",
    updated_at: 0,
  };
}

function createDefaultSemanticHealth() {
  return {
    embeddingStrict: false,
    ready: true,
    reason: "",
  };
}

function parseSseData(rawData, label) {
  if (typeof rawData !== "string") {
    return null;
  }

  try {
    return JSON.parse(rawData);
  } catch (error) {
    console.error(`Failed to parse ${label || "SSE"} payload`, error);
    return null;
  }
}

export const useConnectionStore = defineStore("connection", () => {
  const roomId = ref("");
  const roomDraft = ref("");
  const isSwitchingRoom = ref(false);
  const roomError = ref("");
  const connectionState = ref("idle");
  const modelStatus = ref(createDefaultModelStatus());
  const semanticHealth = ref(createDefaultSemanticHealth());
  let eventSource;

  function hydrateConnectionSnapshot(payload) {
    roomId.value = `${payload.room_id ?? ""}`;
    modelStatus.value = payload.model_status || createDefaultModelStatus();
    semanticHealth.value = {
      embeddingStrict: Boolean(payload.embedding_strict),
      ready: payload.semantic_backend_ready !== false,
      reason: `${payload.semantic_backend_reason ?? ""}`,
    };
    if (!roomId.value) {
      connectionState.value = "idle";
    }
  }

  function setRoomDraft(value) {
    roomDraft.value = `${value ?? ""}`;
  }

  function closeStream() {
    if (eventSource) {
      eventSource.close();
      eventSource = undefined;
    }
  }

  async function bootstrap(targetRoomId = roomId.value) {
    const payload = await bootstrapLiveState(targetRoomId);
    hydrateConnectionSnapshot(payload);
    return payload;
  }

  function connect(targetRoomId = roomId.value, handlers = {}) {
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
      const payload = parseSseData(message.data, "event");
      if (payload && typeof handlers.onEvent === "function") {
        handlers.onEvent(payload);
      }
    });

    eventSource.addEventListener("suggestion", (message) => {
      const payload = parseSseData(message.data, "suggestion");
      if (payload && typeof handlers.onSuggestion === "function") {
        handlers.onSuggestion(payload);
      }
    });

    eventSource.addEventListener("stats", (message) => {
      const payload = parseSseData(message.data, "stats");
      if (payload && typeof handlers.onStats === "function") {
        handlers.onStats(payload);
      }
    });

    eventSource.addEventListener("model_status", (message) => {
      const payload = parseSseData(message.data, "model_status");
      if (payload) {
        modelStatus.value = payload;
      }
    });
  }

  async function switchRoom(nextRoomId = roomDraft.value) {
    const targetRoomId = `${nextRoomId ?? ""}`.trim();
    if (!targetRoomId) {
      roomError.value = "errors.roomRequired";
      return null;
    }

    if (targetRoomId === roomId.value) {
      roomDraft.value = "";
      roomError.value = "";
      return { room_id: targetRoomId };
    }

    isSwitchingRoom.value = true;
    roomError.value = "";
    connectionState.value = "loading_room_memory";
    closeStream();

    try {
      const payload = await switchLiveRoom(targetRoomId);
      hydrateConnectionSnapshot(payload);
      roomDraft.value = "";
      return payload;
    } catch (error) {
      roomError.value = error instanceof Error ? error.message : "errors.roomSwitchFailed";
      throw error;
    } finally {
      isSwitchingRoom.value = false;
    }
  }

  return {
    roomId,
    roomDraft,
    isSwitchingRoom,
    roomError,
    connectionState,
    modelStatus,
    semanticHealth,
    setRoomDraft,
    closeStream,
    bootstrap,
    connect,
    switchRoom,
  };
});
