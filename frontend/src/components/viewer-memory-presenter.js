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
    recalledAt: memory?.last_recalled_at || 0,
  };
}

export function getViewerMemorySourceLabel(memory) {
  const sourceKind = `${memory?.source_kind ?? "auto"}`.trim().toLowerCase();
  if (sourceKind === "manual") {
    return "viewerWorkbench.memorySource.manual";
  }
  if (sourceKind === "rule_fallback") {
    return "viewerWorkbench.memorySource.ruleFallback";
  }
  if (sourceKind === "llm") {
    return "viewerWorkbench.memorySource.llm";
  }
  return "viewerWorkbench.memorySource.auto";
}

export function getViewerMemoryLifecycleLabel(memory) {
  return `${memory?.lifecycle_kind ?? "long_term"}` === "short_term"
    ? "viewerWorkbench.memoryLifecycle.shortTerm"
    : "viewerWorkbench.memoryLifecycle.longTerm";
}

export function canTogglePinViewerMemory(memory) {
  return memory?.status === "active";
}

export function canReactivateViewerMemory(memory) {
  return memory?.status === "invalid";
}
