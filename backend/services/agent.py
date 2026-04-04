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


class LivePromptAgent:
    def __init__(self, settings, vector_memory, long_term_store):
        self.settings = settings
        self.vector_memory = vector_memory
        self.long_term_store = long_term_store
        self._status = {
            "mode": settings.llm_mode,
            "model": settings.resolved_llm_model() if settings.llm_mode != "heuristic" else "heuristic",
            "backend": settings.resolved_llm_base_url() if settings.llm_mode != "heuristic" else "local",
            "last_result": "idle",
            "last_error": "",
            "updated_at": 0,
        }

    def current_status(self):
        return dict(self._status)

    def _mark_status(self, result, error=""):
        self._status = {
            "mode": self.settings.llm_mode,
            "model": self.settings.resolved_llm_model() if self.settings.llm_mode != "heuristic" else "heuristic",
            "backend": self.settings.resolved_llm_base_url() if self.settings.llm_mode != "heuristic" else "local",
            "last_result": result,
            "last_error": error,
            "updated_at": int(time.time() * 1000),
        }

    def build_context(self, event, recent_events):
        similar = self.vector_memory.similar(event.content, limit=3)
        profile = self.long_term_store.get_user_profile(event.room_id, event.user.nickname)
        return {
            "recent_events": [item.model_dump() for item in recent_events[:8]],
            "similar_history": similar,
            "user_profile": profile,
        }

    def maybe_generate(self, event, recent_events):
        if event.event_type not in {"comment", "gift", "follow"}:
            return None

        context = self.build_context(event, recent_events)
        payload = self._generate_payload(event, context)
        return Suggestion(
            suggestion_id=str(uuid.uuid4()),
            room_id=event.room_id,
            event_id=event.event_id,
            priority=payload["priority"],
            reply_text=payload["reply_text"],
            tone=payload["tone"],
            reason=payload["reason"],
            confidence=payload["confidence"],
            references=context["similar_history"],
            source_events=[event.event_id],
            created_at=int(time.time() * 1000),
        )

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
        return self._generate_heuristic(event, context)

    def _generate_heuristic(self, event, context):
        nickname = event.user.nickname
        if event.event_type == "gift":
            gift_name = event.metadata.get("gift_name", event.content or "礼物")
            return {
                "priority": "high",
                "reply_text": f"感谢{nickname}送来的{gift_name}，这份支持我收到了。",
                "tone": "热情感谢",
                "reason": "礼物消息优先级高，适合立即感谢并放大互动。",
                "confidence": 0.91,
            }

        if event.event_type == "follow":
            return {
                "priority": "medium",
                "reply_text": f"欢迎{nickname}关注直播间，后面有想听的话题可以直接说。",
                "tone": "欢迎互动",
                "reason": "关注行为适合用轻量欢迎话术承接。",
                "confidence": 0.83,
            }

        content = event.content.strip() or "这条评论"
        if any(keyword in content for keyword in ("价格", "多少钱", "链接", "怎么买")):
            return {
                "priority": "high",
                "reply_text": "这类问题优先直接给结论，再补购买方式和限制条件。",
                "tone": "明确直接",
                "reason": "评论显式询问转化信息，适合马上回答价格或购买路径。",
                "confidence": 0.88,
            }

        if any(keyword in content for keyword in ("减", "瘦", "胖", "体重", "健身")):
            return {
                "priority": "medium",
                "reply_text": "先接住目标，再给一个可执行的小步骤，别一上来把压力拉满。",
                "tone": "温和鼓励",
                "reason": "评论带有体重或自我目标表达，适合给低压力建议。",
                "confidence": 0.8,
            }

        if context["similar_history"]:
            return {
                "priority": "medium",
                "reply_text": "这类话题以前有过高互动，可以先复用熟悉的回应节奏，再补一句追问。",
                "tone": "延续语境",
                "reason": "向量检索命中了相似互动，适合沿用已验证的回答路径。",
                "confidence": 0.76,
            }

        return {
            "priority": "low",
            "reply_text": f"先复述{nickname}的关键信息，再抛一个短追问，把对话继续拉住。",
            "tone": "自然接话",
            "reason": "普通评论优先追求自然承接和继续互动。",
            "confidence": 0.68,
        }

    def _generate_with_openai_compatible(self, event, context):
        prompt = {
            "event": event.model_dump(),
            "context": context,
            "instruction": (
                "你是直播提词器助手。请只输出一个 JSON 对象，不要输出解释、前后缀或 markdown。"
                "JSON 必须包含 priority, reply_text, tone, reason, confidence。"
                "reply_text 必须简短、口语化、适合主播直接念。"
            ),
        }
        headers = {"Content-Type": "application/json"}
        if self.settings.llm_api_key:
            headers["Authorization"] = f"Bearer {self.settings.llm_api_key}"

        request = urllib.request.Request(
            f"{self.settings.resolved_llm_base_url()}/chat/completions",
            data=json.dumps(
                {
                    "model": self.settings.resolved_llm_model(),
                    "temperature": self.settings.llm_temperature,
                    "messages": [
                        {
                            "role": "system",
                            "content": (
                                "你是直播间实时提词器，擅长中文短句口播。"
                                "输出必须是合法 JSON，不要使用 markdown 代码块。"
                            ),
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
            "priority": priority,
            "reply_text": str(parsed["reply_text"]).strip(),
            "tone": str(parsed["tone"]).strip(),
            "reason": str(parsed["reason"]).strip(),
            "confidence": confidence,
        }
