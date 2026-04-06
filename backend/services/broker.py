"""进程内事件广播器。

后端处理完事件后，会先发到这里，再由 SSE / WebSocket 订阅端分发出去。
"""

import asyncio
from typing import Any


class EventBroker:
    def __init__(self):
        """维护当前所有订阅队列。"""

        self._subscribers: set[asyncio.Queue] = set()

    def subscribe(self) -> asyncio.Queue:
        """创建一个新的订阅队列并加入广播列表。"""

        queue: asyncio.Queue = asyncio.Queue()
        self._subscribers.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue):
        """移除一个订阅队列。"""

        self._subscribers.discard(queue)

    async def publish(self, payload: dict[str, Any]):
        """把消息广播给所有订阅者。"""

        stale_queues = []
        for queue in list(self._subscribers):
            try:
                queue.put_nowait(payload)
            except asyncio.QueueFull:
                stale_queues.append(queue)

        for queue in stale_queues:
            self.unsubscribe(queue)
