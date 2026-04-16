export function getViewerMemoryBadges(memory) {
  const badges = [
    memory?.source_kind === "manual"
      ? "viewerWorkbench.memorySource.manual"
      : "viewerWorkbench.memorySource.auto",
    memory?.status === "invalid"
      ? "viewerWorkbench.memoryStatus.invalid"
      : "viewerWorkbench.memoryStatus.active",
  ];

  if (memory?.is_pinned) {
    badges.push("viewerWorkbench.memoryPinned");
  }
  if (memory?.last_operation) {
    badges.push(`viewerWorkbench.memoryOperation.${memory.last_operation}`);
  }

  return badges;
}

export function getViewerMemoryTimelinePreview(memory) {
  return {
    labelKey: `viewerWorkbench.timeline.${memory?.last_operation || "created"}`,
    reason: memory?.correction_reason || "",
  };
}

export function canTogglePinViewerMemory(memory) {
  return memory?.status === "active";
}

export function canReactivateViewerMemory(memory) {
  return memory?.status === "invalid";
}
