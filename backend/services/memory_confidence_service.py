import re


class MemoryConfidenceService:
    SHORT_TERM_HINTS = ("今天", "今晚", "这周", "最近", "下周", "下个月")
    HIGH_VALUE_HINTS = ("不能吃", "不太能吃", "忌口", "喜欢", "职业", "上班", "租房", "住在", "养了", "安卓")
    NOISY_SHELL_TOKENS = ("是不是", "其实", "吧", "啊", "呢", "吗")

    @staticmethod
    def _clamp(value):
        return max(0.0, min(float(value), 1.0))

    @staticmethod
    def _text(value):
        return str(value or "").strip()

    def _score_stability(self, candidate):
        temporal_scope = self._text(candidate.get("temporal_scope")).lower()
        canonical = self._text(candidate.get("memory_text_canonical") or candidate.get("memory_text"))
        score = 0.35
        if temporal_scope == "long_term":
            score += 0.45
        if any(token in canonical for token in self.SHORT_TERM_HINTS):
            score -= 0.35
        if self._text(candidate.get("memory_type")).lower() == "preference":
            score += 0.1
        return self._clamp(score)

    def _score_interaction_value(self, candidate):
        canonical = self._text(candidate.get("memory_text_canonical") or candidate.get("memory_text"))
        score = 0.25
        if any(token in canonical for token in self.HIGH_VALUE_HINTS):
            score += 0.5
        if len(canonical) <= 16:
            score += 0.1
        return self._clamp(score)

    def _score_clarity(self, candidate):
        canonical = self._text(candidate.get("memory_text_canonical") or candidate.get("memory_text"))
        score = 0.3
        if 4 <= len(canonical) <= 16:
            score += 0.45
        elif len(canonical) <= 24:
            score += 0.25
        if any(token in canonical for token in self.NOISY_SHELL_TOKENS):
            score -= 0.25
        if re.search(r"[?？]", canonical):
            score -= 0.25
        return self._clamp(score)

    def _score_evidence(self, evidence_count, last_confirmed_at):
        score = 0.2 + (0.15 * min(int(evidence_count or 1), 4))
        if last_confirmed_at:
            score += 0.05
        return self._clamp(score)

    def _compose_confidence(self, stability_score, interaction_value_score, clarity_score, evidence_score):
        return round(
            (0.35 * stability_score)
            + (0.35 * interaction_value_score)
            + (0.15 * clarity_score)
            + (0.15 * evidence_score),
            4,
        )

    def score_new_memory(self, candidate: dict) -> dict:
        stability_score = self._score_stability(candidate)
        interaction_value_score = self._score_interaction_value(candidate)
        clarity_score = self._score_clarity(candidate)
        evidence_score = self._score_evidence(1, candidate.get("last_confirmed_at") or 0)
        confidence = self._compose_confidence(
            stability_score,
            interaction_value_score,
            clarity_score,
            evidence_score,
        )
        return {
            "stability_score": stability_score,
            "interaction_value_score": interaction_value_score,
            "clarity_score": clarity_score,
            "evidence_score": evidence_score,
            "confidence": confidence,
        }

    def score_existing_memory_update(self, memory, *, evidence_increment=0, candidate: dict | None = None, upgraded_text: str = "") -> dict:
        candidate = dict(candidate or {})
        candidate.setdefault("memory_text", upgraded_text or getattr(memory, "memory_text", ""))
        candidate.setdefault("memory_text_canonical", upgraded_text or getattr(memory, "memory_text", ""))
        candidate.setdefault("memory_type", getattr(memory, "memory_type", "fact"))
        candidate.setdefault("temporal_scope", "long_term")

        stability_score = max(float(getattr(memory, "stability_score", 0.0) or 0.0), self._score_stability(candidate))
        interaction_value_score = max(
            float(getattr(memory, "interaction_value_score", 0.0) or 0.0),
            self._score_interaction_value(candidate),
        )
        clarity_score = max(
            float(getattr(memory, "clarity_score", 0.0) or 0.0),
            self._score_clarity(candidate),
        )
        evidence_score = self._score_evidence(
            int(getattr(memory, "evidence_count", 1) or 1) + int(evidence_increment or 0),
            getattr(memory, "last_confirmed_at", 0) or 1,
        )
        confidence = self._compose_confidence(
            stability_score,
            interaction_value_score,
            clarity_score,
            evidence_score,
        )
        return {
            "stability_score": self._clamp(stability_score),
            "interaction_value_score": self._clamp(interaction_value_score),
            "clarity_score": self._clamp(clarity_score),
            "evidence_score": evidence_score,
            "confidence": confidence,
        }
