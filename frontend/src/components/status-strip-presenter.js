const CONNECTION_BADGE_MAP = {
  idle: {
    tone: "danger",
    labelKey: "status.connectionState.idle",
    icon: "dot",
  },
  reconnecting: {
    tone: "danger",
    labelKey: "status.connectionState.reconnecting",
    icon: "dot",
  },
  connecting: {
    tone: "warning",
    labelKey: "status.connectionState.connecting",
    icon: "pulse",
  },
  switching: {
    tone: "warning",
    labelKey: "status.connectionState.switching",
    icon: "pulse",
  },
  loading_room_memory: {
    tone: "warning",
    labelKey: "status.connectionState.loadingRoomMemory",
    icon: "pulse",
  },
  live: {
    tone: "success",
    labelKey: "status.connectionState.live",
    icon: "check",
  },
};

export function getConnectionBadgePresentation(connectionState) {
  const badge =
    CONNECTION_BADGE_MAP[connectionState] || CONNECTION_BADGE_MAP.idle;

  return { ...badge };
}
