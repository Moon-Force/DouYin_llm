from dataclasses import dataclass
import re


NEGATIVE_SIGNALS = (
    "不喜欢",
    "不能",
    "不吃",
    "不喝",
    "忌口",
    "接受不了",
    "不太能",
)
POSITIVE_SIGNALS = (
    "喜欢",
    "爱吃",
    "爱喝",
    "常吃",
    "常喝",
)


@dataclass
class MemoryMergeDecision:
    action: str
    target_memory_id: str = ""
    reason: str = ""


class ViewerMemoryMergeService:
    def __init__(self, similarity_threshold=0.88, supersede_threshold=0.82):
        self.similarity_threshold = similarity_threshold
        self.supersede_threshold = supersede_threshold

    @staticmethod
    def _normalize(text):
        normalized = str(text or "").strip().lower()
        normalized = re.sub(r"\s+", "", normalized)
        return normalized

    @staticmethod
    def _has_any_signal(text, signals):
        normalized = str(text or "")
        return any(signal in normalized for signal in signals)

    def _find_existing(self, target_memory_id, existing_memories):
        for memory in existing_memories:
            if getattr(memory, "memory_id", "") == target_memory_id:
                return memory
        return None

    def _same_canonical_match(self, incoming_text, existing_memories):
        normalized_incoming = self._normalize(incoming_text)
        for memory in existing_memories:
            if self._normalize(getattr(memory, "memory_text", "")) == normalized_incoming:
                return memory
        return None

    def _best_similar_existing(self, existing_memories, similar_memories, threshold):
        for item in similar_memories or []:
            if float(item.get("score") or 0.0) < threshold:
                continue
            matched = self._find_existing(str(item.get("memory_id") or ""), existing_memories)
            if matched is not None:
                return matched
        return None

    @staticmethod
    def _looks_more_specific(incoming_text, existing_text):
        incoming_normalized = str(incoming_text or "").strip()
        existing_normalized = str(existing_text or "").strip()
        if not incoming_normalized or not existing_normalized:
            return False
        if len(incoming_normalized) <= len(existing_normalized):
            return False
        if existing_normalized in incoming_normalized:
            return True
        if incoming_normalized.startswith(existing_normalized[:2]) and incoming_normalized.endswith(existing_normalized[-2:]):
            return True
        return False

    def decide(self, incoming, existing_memories, similar_memories):
        incoming_text = str(
            incoming.get("memory_text_canonical") or incoming.get("memory_text") or ""
        ).strip()
        if not incoming_text:
            return MemoryMergeDecision(action="create", reason="empty_incoming")

        same_match = self._same_canonical_match(incoming_text, existing_memories)
        if same_match is not None:
            return MemoryMergeDecision(
                action="merge",
                target_memory_id=same_match.memory_id,
                reason="same_canonical",
            )

        supersede_match = self._best_similar_existing(existing_memories, similar_memories, self.supersede_threshold)
        if supersede_match is not None:
            existing_text = str(getattr(supersede_match, "memory_text", "") or "")
            incoming_negative = self._has_any_signal(incoming_text, NEGATIVE_SIGNALS)
            existing_positive = self._has_any_signal(existing_text, POSITIVE_SIGNALS)
            if incoming_negative and existing_positive:
                return MemoryMergeDecision(
                    action="supersede",
                    target_memory_id=supersede_match.memory_id,
                    reason="conflicting_direction",
                )

        upgrade_match = self._best_similar_existing(existing_memories, similar_memories, self.similarity_threshold)
        if upgrade_match is not None:
            existing_text = str(getattr(upgrade_match, "memory_text", "") or "").strip()
            if self._looks_more_specific(incoming_text, existing_text):
                return MemoryMergeDecision(
                    action="upgrade",
                    target_memory_id=upgrade_match.memory_id,
                    reason="more_specific",
                )

        return MemoryMergeDecision(action="create", reason="no_close_match")
