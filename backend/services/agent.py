"""Generate live prompt suggestions from events and viewer context."""

import json
import logging
import re
import time
import traceback
import urllib.error
import urllib.request
import uuid

from backend.schemas.live import Suggestion


logger = logging.getLogger(__name__)

DEFAULT_SYSTEM_PROMPT = (
    "你是直播间实时提词器，擅长中文短句口播。"
    "输出必须是合法 JSON，不要使用 markdown 代码块。"
)


class LivePromptAgent:
    def __init__(self, settings, vector_memory, long_term_store):
        self.settings = settings
        self.vector_memory = vector_memory
        self.long_term_store = long_term_store
        self._last_generation_metadata = {}
        self._status = {
            "mode": settings.llm_mode,
            "model": settings.resolved_llm_model() if settings.llm_mode != "heuristic" else "heuristic",
            "backend": settings.resolved_llm_base_url() if settings.llm_mode != "heuristic" else "local",
            "last_result": "idle",
            "last_error": "",
            "updated_at": 0,
        }

    def current_status(self):
        status = dict(self._status)
        status["model"] = self.current_model()
        return status

    def current_model(self):
        return self.current_llm_settings()["model"]

    def current_system_prompt(self):
        return self.current_llm_settings()["system_prompt"]

    def current_llm_settings(self):
        if not self.long_term_store:
            return {
                "model": self.settings.resolved_llm_model(),
                "system_prompt": DEFAULT_SYSTEM_PROMPT,
                "default_model": self.settings.resolved_llm_model(),
                "default_system_prompt": DEFAULT_SYSTEM_PROMPT,
            }
        return self.long_term_store.get_llm_settings(
            self.settings.resolved_llm_model(),
            DEFAULT_SYSTEM_PROMPT,
        )

    def consume_last_generation_metadata(self):
        metadata = dict(self._last_generation_metadata)
        self._last_generation_metadata = {}
        return metadata

    def _mark_status(self, result, error=""):
        self._status = {
            "mode": self.settings.llm_mode,
            "model": self.current_model() if self.settings.llm_mode != "heuristic" else "heuristic",
            "backend": self.settings.resolved_llm_base_url() if self.settings.llm_mode != "heuristic" else "local",
            "last_result": result,
            "last_error": error,
            "updated_at": int(time.time() * 1000),
        }

    @staticmethod
    def _build_generation_metadata(
        suggestion_status,
        suggestion_block_reason="",
        suggestion_block_detail="",
        memory_recall_attempted=False,
        memory_recalled=False,
        recalled_memory_ids=None,
        current_comment_memory_used=False,
    ):
        return {
            "suggestion_status": suggestion_status,
            "suggestion_block_reason": suggestion_block_reason,
            "suggestion_block_detail": suggestion_block_detail,
            "memory_recall_attempted": bool(memory_recall_attempted),
            "memory_recalled": bool(memory_recalled),
            "recalled_memory_ids": list(recalled_memory_ids or []),
            "current_comment_memory_used": bool(current_comment_memory_used),
        }

    @staticmethod
    def _is_strict_vector_recall_runtime_error(exc):
        message = str(exc or "")
        return (
            "strict mode blocked fallback" in message
            and ("Vector recall" in message or "Embedding strict mode" in message)
        )

    @staticmethod
    def _dedupe_preserve_order(values):
        seen = set()
        ordered = []
        for value in values:
            text = str(value or "").strip()
            if not text or text in seen:
                continue
            seen.add(text)
            ordered.append(text)
        return ordered

    def build_context(self, event, recent_events, current_comment_memories=None):
        viewer_memories = self.vector_memory.similar_memories(
            event.content,
            room_id=event.room_id,
            viewer_id=event.user.viewer_id,
            limit=2,
        )
        profile = self._compact_user_profile(self.long_term_store.get_user_profile(event.room_id, event.user))
        current_comment_texts = self._dedupe_preserve_order(
            [item.get("memory_text") for item in (current_comment_memories or [])]
        )
        recalled_memory_texts = [item["memory_text"] for item in viewer_memories[:2]]
        return {
            "recent_events": [self._compact_recent_event(item) for item in recent_events[:3]],
            "user_profile": profile,
            "viewer_memories": viewer_memories,
            "current_comment_memories": list(current_comment_memories or []),
            "current_comment_memory_texts": current_comment_texts,
            "viewer_memory_texts": self._dedupe_preserve_order(current_comment_texts + recalled_memory_texts),
            "recalled_memory_ids": [item["memory_id"] for item in viewer_memories[:2] if item.get("memory_id")],
        }

    def maybe_generate(self, event, recent_events, current_comment_memories=None):
        if event.event_type not in {"comment", "gift", "follow"}:
            self._mark_status("idle")
            self._last_generation_metadata = self._build_generation_metadata(
                suggestion_status="skipped",
                suggestion_block_reason="rule_skipped",
                suggestion_block_detail="事件类型不支持，未生成建议。",
            )
            return None

        if event.event_type == "comment" and not str(event.content or "").strip():
            self._mark_status("idle")
            self._last_generation_metadata = self._build_generation_metadata(
                suggestion_status="skipped",
                suggestion_block_reason="no_generation_needed",
                suggestion_block_detail="评论内容为空，未生成建议。",
            )
            return None

        context = {
            "recent_events": [],
            "user_profile": {},
            "viewer_memories": [],
            "current_comment_memories": [],
            "current_comment_memory_texts": [],
            "viewer_memory_texts": [],
            "recalled_memory_ids": [],
        }
        generation_metadata = self._build_generation_metadata(suggestion_status="generated")
        if self._should_short_circuit_with_heuristic(event):
            payload = self._generate_heuristic(event, context, source="heuristic")
        else:
            try:
                context = self.build_context(event, recent_events, current_comment_memories=current_comment_memories)
            except RuntimeError as exc:
                if not self._is_strict_vector_recall_runtime_error(exc):
                    raise
                self._mark_status("error", "semantic_backend_unavailable")
                self._last_generation_metadata = self._build_generation_metadata(
                    suggestion_status="failed",
                    suggestion_block_reason="semantic_backend_unavailable",
                    suggestion_block_detail="语义召回后端不可用，未生成建议。",
                    memory_recall_attempted=True,
                )
                return None
            generation_metadata = self._build_generation_metadata(
                suggestion_status="generated",
                suggestion_block_reason="",
                suggestion_block_detail="",
                memory_recall_attempted=True,
                memory_recalled=bool(context["recalled_memory_ids"]),
                recalled_memory_ids=context["recalled_memory_ids"],
                current_comment_memory_used=bool(context["current_comment_memory_texts"]),
            )
            payload = self._generate_payload(event, context)
        self._last_generation_metadata = generation_metadata

        memory_ids = [item["memory_id"] for item in context["viewer_memories"] if item.get("memory_id")]
        if memory_ids:
            self.long_term_store.touch_viewer_memories(memory_ids)

        references = self._dedupe_preserve_order(
            context["viewer_memory_texts"]
        )
        return Suggestion(
            suggestion_id=str(uuid.uuid4()),
            room_id=event.room_id,
            event_id=event.event_id,
            source=payload["source"],
            priority=payload["priority"],
            reply_text=payload["reply_text"],
            tone=payload["tone"],
            reason=payload["reason"],
            confidence=payload["confidence"],
            references=references,
            source_events=[event.event_id],
            created_at=int(time.time() * 1000),
        )

    @staticmethod
    def _compact_recent_event(event):
        return {
            "event_type": event.event_type,
            "nickname": event.user.nickname,
            "content": event.content or event.metadata.get("gift_name", ""),
        }

    @staticmethod
    def _compact_user_profile(profile):
        if not profile:
            return {}

        compact = {}
        for key in (
            "nickname",
            "comment_count",
            "gift_event_count",
            "total_gift_count",
            "last_comment",
            "last_gift_name",
        ):
            value = profile.get(key)
            if value not in (None, "", [], {}):
                compact[key] = value
        return compact

    @staticmethod
    def _should_short_circuit_with_heuristic(event):
        if event.event_type in {"gift", "follow"}:
            return True

        content = str(event.content or "").strip()
        return any(keyword in content for keyword in ("价格", "多少钱", "链接", "怎么买", "减", "瘦", "胖", "体重", "健身"))

    def _build_prompt_payload(self, event, context):
        return {
            "event": {
                "event_type": event.event_type,
                "nickname": event.user.nickname,
                "content": event.content,
                "gift_name": event.metadata.get("gift_name", ""),
            },
            "context": {
                "recent_events": context["recent_events"],
                "user_profile": context["user_profile"],
                "viewer_memories": context["viewer_memory_texts"],
            },
            "instruction": (
                "你是直播提词助手。请只输出一个 JSON 对象，不要输出解释、前后缀或 markdown。"
                "JSON 必须包含 priority, reply_text, tone, reason, confidence。"
                "如果命中了同一观众的历史记忆，优先给主播一条能自然延续旧话题的中文短句。"
            ),
        }

    def _generate_payload(self, event, context):
        if self.settings.llm_mode != "heuristic":
            result = self._generate_with_openai_compatible(event, context)
            if result:
                self._mark_status("ok")
                return result
            self._mark_status("fallback", "llm_generation_failed")
            logger.warning(
                "LLM generation failed, falling back to heuristic mode: room_id=%s event_id=%s model=%s",
                event.room_id,
                event.event_id,
                self.settings.resolved_llm_model(),
            )

        self._mark_status("heuristic")
        fallback_source = "heuristic_fallback" if self.settings.llm_mode != "heuristic" else "heuristic"
        return self._generate_heuristic(event, context, source=fallback_source)

    def _memory_follow_up(self, event, memory_text):
        snippet = str(memory_text or "").strip()
        if len(snippet) > 36:
            snippet = f"{snippet[:36]}..."

        if "拉面" in memory_text and "面" in event.content:
            return f"可以接一句：你上次说{snippet}，今晚是不是去那家？"

        return f"可以顺着他上次提到的“{snippet}”接一句，确认是不是同一件事。"

    def _generate_heuristic(self, event, context, source="heuristic"):
        nickname = event.user.nickname or "这位观众"
        if event.event_type == "gift":
            gift_name = event.metadata.get("gift_name", event.content or "礼物")
            return {
                "source": source,
                "priority": "high",
                "reply_text": f"感谢{nickname}送来的{gift_name}，这份支持我收到了。",
                "tone": "热情感谢",
                "reason": "礼物消息优先级高，适合立即感谢并放大互动。",
                "confidence": 0.91,
            }

        if event.event_type == "follow":
            return {
                "source": source,
                "priority": "medium",
                "reply_text": f"欢迎{nickname}关注直播间，后面有想听的话题可以直接说。",
                "tone": "欢迎互动",
                "reason": "关注行为适合用轻量欢迎话术承接。",
                "confidence": 0.83,
            }

        content = event.content.strip() or "这条评论"
        if any(keyword in content for keyword in ("价格", "多少钱", "链接", "怎么买")):
            return {
                "source": source,
                "priority": "high",
                "reply_text": "先直接回答价格，再补下单方式和优惠信息。",
                "tone": "明确直接",
                "reason": "这是明显的转化型问题，先给结论再补路径更稳。",
                "confidence": 0.88,
            }

        if any(keyword in content for keyword in ("减", "瘦", "胖", "体重", "健身")):
            return {
                "source": source,
                "priority": "medium",
                "reply_text": "先接住他的目标，再给一个能马上执行的小建议。",
                "tone": "温和鼓励",
                "reason": "涉及身材或目标类评论，适合低压力承接。",
                "confidence": 0.8,
            }

        if context["viewer_memory_texts"]:
            memory_text = context["viewer_memory_texts"][0]
            return {
                "source": source,
                "priority": "high",
                "reply_text": self._memory_follow_up(event, memory_text),
                "tone": "延续对话",
                "reason": "命中了同一观众的历史语义记忆，适合顺着旧话题继续聊。",
                "confidence": 0.86,
            }

        return {
            "source": source,
            "priority": "low",
            "reply_text": f"先复述{nickname}的关键信息，再抛一个短追问把对话接住。",
            "tone": "自然接话",
            "reason": "普通评论优先追求自然承接和继续互动。",
            "confidence": 0.68,
        }

    def _generate_with_openai_compatible(self, event, context):
        llm_settings = self.current_llm_settings()
        prompt = self._build_prompt_payload(event, context)
        headers = {"Content-Type": "application/json"}
        if self.settings.llm_api_key:
            headers["Authorization"] = f"Bearer {self.settings.llm_api_key}"

        request = urllib.request.Request(
            f"{self.settings.resolved_llm_base_url()}/chat/completions",
            data=json.dumps(
                {
                    "model": llm_settings["model"],
                    "temperature": self.settings.llm_temperature,
                    "max_tokens": self.settings.llm_max_tokens,
                    "messages": [
                        {
                            "role": "system",
                            "content": llm_settings["system_prompt"],
                        },
                        {"role": "user", "content": json.dumps(prompt, ensure_ascii=False)},
                    ],
                },
                ensure_ascii=False,
            ).encode("utf-8"),
            headers=headers,
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=self.settings.llm_timeout_seconds) as response:
                raw_body = response.read().decode("utf-8")
                payload = json.loads(raw_body)
        except urllib.error.HTTPError as exc:
            error_body = ""
            try:
                error_body = exc.read().decode("utf-8", errors="replace")
            except Exception:
                pass
            logger.error(
                "LLM HTTP error: mode=%s model=%s status=%s reason=%s body=%s",
                self.settings.llm_mode,
                self.settings.resolved_llm_model(),
                exc.code,
                exc.reason,
                error_body[:500],
            )
            self._mark_status("error", f"http_{exc.code}")
            return None
        except urllib.error.URLError as exc:
            logger.error(
                "LLM network error: mode=%s model=%s reason=%s",
                self.settings.llm_mode,
                self.settings.resolved_llm_model(),
                exc.reason,
            )
            self._mark_status("error", "network_error")
            return None
        except TimeoutError:
            logger.error(
                "LLM timeout: mode=%s model=%s timeout=%s",
                self.settings.llm_mode,
                self.settings.resolved_llm_model(),
                self.settings.llm_timeout_seconds,
            )
            self._mark_status("error", "timeout")
            return None
        except json.JSONDecodeError:
            logger.error(
                "LLM returned invalid JSON envelope: mode=%s model=%s",
                self.settings.llm_mode,
                self.settings.resolved_llm_model(),
            )
            self._mark_status("error", "invalid_json_envelope")
            return None
        except OSError as exc:
            logger.error(
                "LLM OS/network failure: mode=%s model=%s error=%s",
                self.settings.llm_mode,
                self.settings.resolved_llm_model(),
                exc,
            )
            self._mark_status("error", "os_error")
            return None
        except Exception:
            logger.error(
                "LLM unexpected exception: mode=%s model=%s traceback=%s",
                self.settings.llm_mode,
                self.settings.resolved_llm_model(),
                traceback.format_exc(),
            )
            self._mark_status("error", "unexpected_exception")
            return None

        try:
            content = payload["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError):
            logger.error(
                "LLM response missing choices/message/content: mode=%s model=%s keys=%s",
                self.settings.llm_mode,
                self.settings.resolved_llm_model(),
                list(payload.keys()) if isinstance(payload, dict) else type(payload).__name__,
            )
            self._mark_status("error", "missing_content")
            return None

        parsed = self._parse_model_json(content)
        if not parsed:
            logger.error(
                "LLM content could not be parsed into JSON payload: mode=%s model=%s content=%s",
                self.settings.llm_mode,
                self.settings.resolved_llm_model(),
                content[:500],
            )
            self._mark_status("error", "invalid_json_payload")
            return None

        normalized = self._normalize_model_payload(parsed)
        if not normalized:
            logger.error(
                "LLM payload missing required fields or had invalid types: mode=%s model=%s payload=%s",
                self.settings.llm_mode,
                self.settings.resolved_llm_model(),
                json.dumps(parsed, ensure_ascii=False)[:500],
            )
            self._mark_status("error", "invalid_payload_shape")
            return None

        logger.info(
            "LLM suggestion generated: room_id=%s event_id=%s model=%s priority=%s confidence=%.2f",
            event.room_id,
            event.event_id,
            self.settings.resolved_llm_model(),
            normalized["priority"],
            normalized["confidence"],
        )
        return normalized

    def _parse_model_json(self, content):
        candidates = [content.strip()]
        fenced = re.findall(r"```(?:json)?\s*(\{.*?\})\s*```", content, flags=re.S)
        candidates.extend(fenced)

        start = content.find("{")
        end = content.rfind("}")
        if start != -1 and end != -1 and end > start:
            candidates.append(content[start : end + 1].strip())

        for candidate in candidates:
            try:
                parsed = json.loads(candidate)
            except json.JSONDecodeError:
                continue
            if isinstance(parsed, dict):
                return parsed

        return None

    def _normalize_model_payload(self, parsed):
        required = {"priority", "reply_text", "tone", "reason", "confidence"}
        if not required.issubset(parsed):
            return None

        priority = parsed["priority"]
        if isinstance(priority, (int, float)):
            if priority >= 3:
                priority = "high"
            elif priority >= 2:
                priority = "medium"
            else:
                priority = "low"
        else:
            priority = str(priority).strip().lower()
            if priority not in {"low", "medium", "high"}:
                if any(token in priority for token in ("高", "urgent", "critical")):
                    priority = "high"
                elif any(token in priority for token in ("中", "normal")):
                    priority = "medium"
                else:
                    priority = "low"

        try:
            confidence = float(parsed["confidence"])
        except (TypeError, ValueError):
            return None

        confidence = max(0.0, min(1.0, confidence))
        return {
            "source": "model",
            "priority": priority,
            "reply_text": str(parsed["reply_text"]).strip(),
            "tone": str(parsed["tone"]).strip(),
            "reason": str(parsed["reason"]).strip(),
            "confidence": confidence,
        }
