"""短期会话内存层。

优先使用 Redis 保存最近事件和建议；如果没有安装 Redis 或没有配置地址，
就自动退化到进程内 deque，保证项目仍然能正常运行。
"""

import logging
from collections import defaultdict, deque

from backend.schemas.live import LiveEvent, SessionSnapshot, SessionStats, Suggestion

try:
    import redis
except ImportError:  # pragma: no cover - optional dependency
    redis = None


class SessionMemory:
    def __init__(self, redis_url="", ttl_seconds=14400):
        """初始化短期内存。

        `ttl_seconds` 只在 Redis 模式下生效，用来控制热数据生命周期。
        """

        self.ttl_seconds = ttl_seconds
        self.redis_client = None
        self._events = defaultdict(lambda: deque(maxlen=120))
        self._suggestions = defaultdict(lambda: deque(maxlen=40))

        if redis and redis_url:
            try:
                self.redis_client = redis.Redis.from_url(redis_url, decode_responses=True)
            except Exception:
                logging.warning("Redis connection failed for %s, falling back to local memory", redis_url)
                self.redis_client = None

    def _events_key(self, room_id):
        """Redis 中某个房间事件列表的 key。"""

        return f"room:{room_id}:events"

    def _suggestions_key(self, room_id):
        """Redis 中某个房间建议列表的 key。"""

        return f"room:{room_id}:suggestions"

    def add_event(self, event: LiveEvent):
        """写入一条最近事件。"""

        if self.redis_client:
            payload = event.model_dump_json()
            self.redis_client.lpush(self._events_key(event.room_id), payload)
            self.redis_client.ltrim(self._events_key(event.room_id), 0, 119)
            self.redis_client.expire(self._events_key(event.room_id), self.ttl_seconds)
            return

        self._events[event.room_id].appendleft(event)

    def add_suggestion(self, suggestion: Suggestion):
        """写入一条最近建议。"""

        if self.redis_client:
            payload = suggestion.model_dump_json()
            self.redis_client.lpush(self._suggestions_key(suggestion.room_id), payload)
            self.redis_client.ltrim(self._suggestions_key(suggestion.room_id), 0, 39)
            self.redis_client.expire(self._suggestions_key(suggestion.room_id), self.ttl_seconds)
            return

        self._suggestions[suggestion.room_id].appendleft(suggestion)

    def recent_events(self, room_id, limit=30):
        """读取某个房间最近事件。"""

        if self.redis_client:
            values = self.redis_client.lrange(self._events_key(room_id), 0, max(limit - 1, 0))
            return [LiveEvent.model_validate_json(value) for value in values]

        return list(self._events[room_id])[:limit]

    def recent_suggestions(self, room_id, limit=10):
        """读取某个房间最近建议。"""

        if self.redis_client:
            values = self.redis_client.lrange(
                self._suggestions_key(room_id), 0, max(limit - 1, 0)
            )
            return [Suggestion.model_validate_json(value) for value in values]

        return list(self._suggestions[room_id])[:limit]

    def stats(self, room_id):
        """基于短期事件窗口生成轻量统计。"""

        events = self.recent_events(room_id, limit=120)
        stats = SessionStats(room_id=room_id, total_events=len(events))
        for event in events:
            if event.event_type == "comment":
                stats.comments += 1
            elif event.event_type == "gift":
                stats.gifts += 1
            elif event.event_type == "like":
                stats.likes += 1
            elif event.event_type == "member":
                stats.members += 1
            elif event.event_type == "follow":
                stats.follows += 1
        return stats

    def snapshot(self, room_id):
        """构造基于短期内存的房间快照。"""

        return SessionSnapshot(
            room_id=room_id,
            recent_events=self.recent_events(room_id, limit=30),
            recent_suggestions=self.recent_suggestions(room_id, limit=10),
            stats=self.stats(room_id),
        )
