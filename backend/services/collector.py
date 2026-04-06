"""抖音直播消息采集器。

这个模块负责：
- 连接本地 `douyinLive` 暴露的 WebSocket
- 解析原始消息
- 转成统一的 `LiveEvent`
- 把事件提交给后端主循环处理
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

# 原始抖音消息类型到系统统一事件类型的映射。
METHOD_EVENT_TYPE_MAP = {
    "WebcastChatMessage": "comment",
    "WebcastGiftMessage": "gift",
    "WebcastLikeMessage": "like",
    "WebcastMemberMessage": "member",
    "WebcastSocialMessage": "follow",
}


class DouyinCollector:
    def __init__(
        self,
        settings: Settings,
        event_handler: Callable[[LiveEvent], Awaitable[None]],
    ):
        """初始化采集器，但此时还不会真正发起连接。"""

        self.settings = settings
        self.event_handler = event_handler
        self.loop: asyncio.AbstractEventLoop | None = None
        self.thread: threading.Thread | None = None
        self.ping_thread: threading.Thread | None = None
        self.ping_stop_event: threading.Event | None = None
        self.ws: websocket.WebSocketApp | None = None
        self.running = False
        self.stop_event = threading.Event()

    @property
    def url(self) -> str:
        """根据当前配置动态生成采集目标 WebSocket 地址。"""

        return (
            f"ws://{self.settings.collector_host}:"
            f"{self.settings.collector_port}/ws/{self.settings.room_id}"
        )

    def start(self, loop: asyncio.AbstractEventLoop) -> bool:
        """启动采集线程。"""

        if not self.settings.collector_enabled:
            logger.info("Douyin collector disabled by configuration")
            return False

        if not self.settings.room_id:
            logger.warning("Douyin collector skipped because ROOM_ID is empty")
            return False

        if self.thread and self.thread.is_alive():
            return True

        self.loop = loop
        self.stop_event.clear()
        self.thread = threading.Thread(target=self._run, name="douyin-collector", daemon=True)
        self.thread.start()
        logger.info("Douyin collector started for room %s", self.settings.room_id)
        return True

    def switch_room(self, room_id: str) -> bool:
        """切换采集房间。

        做法是先停掉旧连接，再更新 `settings.room_id`，最后按新房间重启。
        """

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
        """停止采集线程和保活线程，并关闭当前 WebSocket。"""

        self.stop_event.set()
        self.running = False
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
        """采集线程主体。

        当连接断开时会按配置自动重连，除非外部显式要求停止。
        """

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
                self.ws.run_forever()
            except Exception:
                logger.exception("Douyin collector crashed")

            if self.stop_event.is_set():
                break

            delay = self.settings.collector_reconnect_delay_seconds
            logger.warning("Douyin collector disconnected, retrying in %.1fs", delay)
            time.sleep(delay)

    def _on_open(self, ws) -> None:
        """WebSocket 连接建立后的回调。"""

        logger.info("Douyin collector connected")
        self.running = True
        self._start_ping_loop()

    def _on_message(self, ws, message: str) -> None:
        """收到原始消息后的回调。"""

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

        self._submit_event(event)

    def _on_error(self, ws, error) -> None:
        """WebSocket 错误回调。"""

        if self.stop_event.is_set():
            return

        logger.warning("Douyin collector websocket error: %s", error)

    def _on_close(self, ws, close_status_code, close_msg) -> None:
        """WebSocket 关闭回调。"""

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

    def _start_ping_loop(self) -> None:
        """启动一个独立线程定时发送 ping，维持连接活性。"""

        ping_stop_event = threading.Event()
        self.ping_stop_event = ping_stop_event

        def ping() -> None:
            while self.running and not self.stop_event.is_set() and not ping_stop_event.is_set():
                try:
                    if self.ws and self.ws.sock and self.ws.sock.connected:
                        self.ws.send("ping")
                    time.sleep(self.settings.collector_ping_interval_seconds)
                except Exception:
                    if not self.stop_event.is_set():
                        logger.exception("Douyin collector ping failed")
                    break

        self.ping_thread = threading.Thread(target=ping, name="douyin-collector-ping", daemon=True)
        self.ping_thread.start()

    def _submit_event(self, event: LiveEvent) -> None:
        """把采集线程里的事件安全地投递回 FastAPI 主事件循环。"""

        if not self.loop:
            logger.warning("Dropping Douyin event because backend loop is unavailable")
            return

        future = asyncio.run_coroutine_threadsafe(self.event_handler(event), self.loop)
        future.add_done_callback(self._log_handler_result)

    @staticmethod
    def _log_handler_result(future) -> None:
        """统一记录异步事件处理结果中的异常。"""

        try:
            future.result()
        except Exception:
            logger.exception("Douyin event handling failed")

    def normalize_event(self, data: dict) -> LiveEvent | None:
        """把抖音原始消息标准化成系统内部统一事件格式。"""

        common = data.get("common", {})
        method = common.get("method", "unknown")
        user = data.get("user", {})
        event_type = METHOD_EVENT_TYPE_MAP.get(method, "system")

        content = data.get("content", "")
        metadata = {
            "method": method,
            "livename": data.get("livename", ""),
        }

        if method == "WebcastGiftMessage":
            metadata["gift_name"] = data.get("gift", {}).get("name", "")
        elif method == "WebcastLikeMessage":
            metadata["action"] = "like"
        elif method == "WebcastMemberMessage":
            metadata["action"] = "join"
        elif method == "WebcastSocialMessage":
            metadata["action"] = "follow"

        if not content and "gift_name" in metadata:
            content = metadata["gift_name"]

        try:
            return LiveEvent(
                event_id=common.get("msgId") or f"local-{int(time.time() * 1000)}",
                room_id=self.settings.room_id,
                platform="douyin",
                event_type=event_type,
                method=method,
                livename=data.get("livename", ""),
                ts=int(common.get("createTime") or time.time() * 1000),
                user={
                    "id": user.get("id") or user.get("secUid") or "",
                    "nickname": user.get("nickname", ""),
                },
                content=content,
                metadata=metadata,
                raw=data,
            )
        except Exception:
            logger.exception("Failed to normalize Douyin message")
            return None
