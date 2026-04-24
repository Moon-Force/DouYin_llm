"""Douyin live message collector.

This module connects to the local `douyinLive` websocket, normalizes raw
messages into `LiveEvent`, and submits them back into the FastAPI event loop.
"""

import asyncio
import json
import logging
import threading
import time
from collections.abc import Awaitable, Callable

import websocket

from backend.config import Settings
from backend.schemas.live import LiveEvent


logger = logging.getLogger(__name__)

METHOD_EVENT_TYPE_MAP = {
    "WebcastChatMessage": "comment",
    "WebcastGiftMessage": "gift",
    "WebcastLikeMessage": "like",
    "WebcastMemberMessage": "member",
    "WebcastSocialMessage": "follow",
}


def safe_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


class DouyinCollector:
    _RECENT_EVENT_TTL_SECONDS = 15.0

    def __init__(
        self,
        settings: Settings,
        event_handler: Callable[[LiveEvent], Awaitable[None]],
    ):
        self.settings = settings
        self.event_handler = event_handler
        self.loop: asyncio.AbstractEventLoop | None = None
        self.thread: threading.Thread | None = None
        self.ping_thread: threading.Thread | None = None
        self.ping_stop_event: threading.Event | None = None
        self.ws: websocket.WebSocketApp | None = None
        self.running = False
        self.stop_event = threading.Event()
        self._recent_event_ids: dict[str, float] = {}

    @property
    def url(self) -> str:
        return (
            f"ws://{self.settings.collector_host}:"
            f"{self.settings.collector_port}/ws/{self.settings.room_id}"
        )

    def start(self, loop: asyncio.AbstractEventLoop) -> bool:
        self.loop = loop

        if not self.settings.collector_enabled:
            logger.info("Douyin collector disabled by configuration")
            return False

        if not self.settings.room_id:
            logger.warning("Douyin collector skipped because ROOM_ID is empty")
            return False

        if self.thread and self.thread.is_alive():
            return True

        self.stop_event.clear()
        self.thread = threading.Thread(target=self._run, name="douyin-collector", daemon=True)
        self.thread.start()
        logger.info("Douyin collector started for room %s", self.settings.room_id)
        return True

    def switch_room(self, room_id: str) -> bool:
        target_room_id = room_id.strip()
        if not target_room_id:
            raise ValueError("room_id cannot be empty")

        if target_room_id == self.settings.room_id and self.thread and self.thread.is_alive():
            logger.info("Douyin collector already connected to room %s", target_room_id)
            return False

        loop = self.loop
        self.stop()
        self.settings.room_id = target_room_id

        if loop:
            self.start(loop)

        logger.info("Douyin collector switched to room %s", target_room_id)
        return True

    def stop(self) -> None:
        self.stop_event.set()
        self.running = False
        self._recent_event_ids.clear()
        if self.ping_stop_event:
            self.ping_stop_event.set()

        if self.ws:
            try:
                self.ws.close()
            except Exception:
                logger.exception("Failed to close Douyin collector websocket cleanly")

        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=5)

        if self.ping_thread and self.ping_thread.is_alive():
            self.ping_thread.join(timeout=1)

    def _run(self) -> None:
        while not self.stop_event.is_set():
            self.ws = websocket.WebSocketApp(
                self.url,
                on_open=self._on_open,
                on_message=self._on_message,
                on_error=self._on_error,
                on_close=self._on_close,
            )

            try:
                logger.info("Connecting to Douyin websocket at %s", self.url)
                self.ws.run_forever(ping_interval=self.settings.collector_ping_interval_seconds)
            except Exception:
                logger.exception("Douyin collector crashed")

            if self.stop_event.is_set():
                break

            delay = self.settings.collector_reconnect_delay_seconds
            logger.warning("Douyin collector disconnected, retrying in %.1fs", delay)
            time.sleep(delay)

    def _on_open(self, ws) -> None:
        logger.info("Douyin collector connected")
        self.running = True

    def _on_message(self, ws, message: str) -> None:
        if message == "pong":
            return

        try:
            data = json.loads(message)
        except json.JSONDecodeError:
            logger.warning("Ignoring non-JSON Douyin message: %s", message)
            return

        event = self.normalize_event(data)
        if not event:
            return

        if self._remember_recent_event_id(event.event_id):
            logger.info("Ignoring duplicate Douyin event %s", event.event_id)
            return

        self._submit_event(event)

    def _on_error(self, ws, error) -> None:
        if self.stop_event.is_set():
            return

        logger.warning("Douyin collector websocket error: %s", error)

    def _on_close(self, ws, close_status_code, close_msg) -> None:
        self.running = False
        if self.ping_stop_event:
            self.ping_stop_event.set()

        if self.stop_event.is_set():
            logger.info("Douyin collector stopped")
            return

        logger.warning(
            "Douyin collector connection closed: code=%s msg=%s",
            close_status_code,
            close_msg,
        )

    def _submit_event(self, event: LiveEvent) -> None:
        if not self.loop:
            logger.warning("Dropping Douyin event because backend loop is unavailable")
            return

        future = asyncio.run_coroutine_threadsafe(self.event_handler(event), self.loop)
        future.add_done_callback(self._log_handler_result)

    @staticmethod
    def _log_handler_result(future) -> None:
        try:
            future.result()
        except Exception:
            logger.exception("Douyin event handling failed")

    @staticmethod
    def _extract_gift_count(data: dict) -> int:
        counts = [
            safe_int(data.get("repeatCount")),
            safe_int(data.get("comboCount")),
            safe_int(data.get("groupCount")),
        ]
        positive_counts = [count for count in counts if count > 0]
        return max(positive_counts, default=1)

    @classmethod
    def _gift_business_key(cls, data: dict, user: dict, gift: dict) -> str:
        trace_id = str(data.get("traceId") or "").strip()
        if trace_id:
            return f"trace:{trace_id}"

        send_time = str(data.get("sendTime") or "").strip()
        group_id = str(data.get("groupId") or "").strip()
        user_id = str(user.get("id") or "").strip()
        gift_id = str(gift.get("id") or data.get("giftId") or "").strip()
        parts = [part for part in (send_time, group_id, user_id, gift_id) if part]
        return ":".join(parts)

    @classmethod
    def _build_event_id(cls, common: dict, data: dict, user: dict, gift: dict) -> str:
        method = str(common.get("method") or "").strip()
        msg_id = str(common.get("msgId") or "").strip()
        if method != "WebcastGiftMessage":
            return msg_id or f"local-{int(time.time() * 1000)}"

        business_key = cls._gift_business_key(data, user, gift)
        gift_count = cls._extract_gift_count(data)
        if business_key:
            return f"gift:{business_key}:count:{gift_count}"
        return msg_id or f"local-{int(time.time() * 1000)}"

    def _remember_recent_event_id(self, event_id: str) -> bool:
        normalized = str(event_id or "").strip()
        if not normalized:
            return False

        now = time.monotonic()
        cutoff = now - self._RECENT_EVENT_TTL_SECONDS
        expired_ids = [
            cached_id for cached_id, seen_at in self._recent_event_ids.items() if seen_at < cutoff
        ]
        for cached_id in expired_ids:
            self._recent_event_ids.pop(cached_id, None)

        if normalized in self._recent_event_ids:
            return True

        self._recent_event_ids[normalized] = now
        return False

    def normalize_event(self, data: dict) -> LiveEvent | None:
        common = data.get("common", {})
        method = common.get("method", "unknown")
        user = data.get("user", {})
        gift = data.get("gift", {})
        event_type = METHOD_EVENT_TYPE_MAP.get(method, "system")

        source_room_id = str(common.get("roomId") or "").strip()
        user_id = str(user.get("id") or "").strip()
        short_id = str(user.get("shortId") or user.get("displayId") or "").strip()
        sec_uid = str(user.get("secUid") or "").strip()

        content = data.get("content", "")
        metadata = {
            "method": method,
            "livename": data.get("livename", ""),
            "title": data.get("title", ""),
            "source_room_id": source_room_id,
        }

        if method == "WebcastGiftMessage":
            business_key = self._gift_business_key(data, user, gift)
            metadata["gift_name"] = gift.get("name", "")
            metadata["gift_id"] = str(gift.get("id") or data.get("giftId") or "").strip()
            metadata["gift_count"] = self._extract_gift_count(data)
            metadata["gift_diamond_count"] = safe_int(gift.get("diamondCount"))
            metadata["combo_count"] = safe_int(data.get("comboCount"))
            metadata["group_count"] = safe_int(data.get("groupCount"))
            metadata["gift_trace_id"] = str(data.get("traceId") or "").strip()
            metadata["gift_send_time"] = str(data.get("sendTime") or "").strip()
            metadata["gift_group_id"] = str(data.get("groupId") or "").strip()
            metadata["gift_business_key"] = business_key
        elif method == "WebcastLikeMessage":
            metadata["action"] = "like"
        elif method == "WebcastMemberMessage":
            metadata["action"] = "join"
        elif method == "WebcastSocialMessage":
            metadata["action"] = "follow"

        if not content and metadata.get("gift_name"):
            content = metadata["gift_name"]

        try:
            return LiveEvent(
                event_id=self._build_event_id(common, data, user, gift),
                room_id=self.settings.room_id,
                source_room_id=source_room_id or self.settings.room_id,
                platform="douyin",
                event_type=event_type,
                method=method,
                livename=data.get("livename", ""),
                ts=int(common.get("createTime") or time.time() * 1000),
                user={
                    "id": user_id,
                    "short_id": short_id,
                    "sec_uid": sec_uid,
                    "nickname": user.get("nickname", ""),
                },
                content=content,
                metadata=metadata,
                raw=data,
            )
        except Exception:
            logger.exception("Failed to normalize Douyin message")
            return None
