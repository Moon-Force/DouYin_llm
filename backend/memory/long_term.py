"""SQLite 长期存储层。

这里负责持久化：
- 直播事件
- 提词建议
- 基础用户画像
"""

import json
import sqlite3

from backend.schemas.live import Actor, LiveEvent, SessionSnapshot, SessionStats, Suggestion


class LongTermStore:
    def __init__(self, database_path):
        self.database_path = str(database_path)
        self._setup()

    def _connect(self):
        """创建一个带字典行访问能力的 SQLite 连接。"""

        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _setup(self):
        """初始化数据库表结构。"""

        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS events (
                    event_id TEXT PRIMARY KEY,
                    room_id TEXT NOT NULL,
                    platform TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    method TEXT NOT NULL,
                    livename TEXT NOT NULL,
                    user_id TEXT,
                    nickname TEXT,
                    content TEXT,
                    ts INTEGER NOT NULL,
                    metadata_json TEXT,
                    raw_json TEXT
                );

                CREATE TABLE IF NOT EXISTS user_profiles (
                    room_id TEXT NOT NULL,
                    nickname TEXT NOT NULL,
                    user_id TEXT,
                    interaction_count INTEGER NOT NULL DEFAULT 0,
                    latest_event_type TEXT,
                    latest_content TEXT,
                    updated_at INTEGER NOT NULL,
                    PRIMARY KEY (room_id, nickname)
                );

                CREATE TABLE IF NOT EXISTS suggestions (
                    suggestion_id TEXT PRIMARY KEY,
                    room_id TEXT NOT NULL,
                    event_id TEXT NOT NULL,
                    priority TEXT NOT NULL,
                    reply_text TEXT NOT NULL,
                    tone TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    created_at INTEGER NOT NULL
                );
                """
            )

    def persist_event(self, event: LiveEvent):
        """持久化一条事件，并同步更新用户画像。"""

        with self._connect() as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO events (
                    event_id, room_id, platform, event_type, method, livename,
                    user_id, nickname, content, ts, metadata_json, raw_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event.event_id,
                    event.room_id,
                    event.platform,
                    event.event_type,
                    event.method,
                    event.livename,
                    event.user.id,
                    event.user.nickname,
                    event.content,
                    event.ts,
                    json.dumps(event.metadata, ensure_ascii=False),
                    json.dumps(event.raw, ensure_ascii=False),
                ),
            )
            connection.execute(
                """
                INSERT INTO user_profiles (
                    room_id, nickname, user_id, interaction_count, latest_event_type,
                    latest_content, updated_at
                ) VALUES (?, ?, ?, 1, ?, ?, ?)
                ON CONFLICT(room_id, nickname) DO UPDATE SET
                    user_id=excluded.user_id,
                    interaction_count=user_profiles.interaction_count + 1,
                    latest_event_type=excluded.latest_event_type,
                    latest_content=excluded.latest_content,
                    updated_at=excluded.updated_at
                """,
                (
                    event.room_id,
                    event.user.nickname,
                    event.user.id,
                    event.event_type,
                    event.content,
                    event.ts,
                ),
            )

    def persist_suggestion(self, suggestion: Suggestion):
        """持久化一条提词建议。"""

        with self._connect() as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO suggestions (
                    suggestion_id, room_id, event_id, priority, reply_text,
                    tone, reason, confidence, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    suggestion.suggestion_id,
                    suggestion.room_id,
                    suggestion.event_id,
                    suggestion.priority,
                    suggestion.reply_text,
                    suggestion.tone,
                    suggestion.reason,
                    suggestion.confidence,
                    suggestion.created_at,
                ),
            )

    def recent_events(self, room_id, limit=30):
        """读取某个房间最近的事件记录。"""

        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT event_id, room_id, platform, event_type, method, livename,
                       user_id, nickname, content, ts, metadata_json, raw_json
                FROM events
                WHERE room_id = ?
                ORDER BY ts DESC
                LIMIT ?
                """,
                (room_id, limit),
            ).fetchall()

        events = []
        for row in rows:
            events.append(
                LiveEvent(
                    event_id=row["event_id"],
                    room_id=row["room_id"],
                    platform=row["platform"],
                    event_type=row["event_type"],
                    method=row["method"],
                    livename=row["livename"],
                    ts=row["ts"],
                    user=Actor(
                        id=row["user_id"] or "",
                        nickname=row["nickname"] or Actor().nickname,
                    ),
                    content=row["content"] or "",
                    metadata=json.loads(row["metadata_json"] or "{}"),
                    raw=json.loads(row["raw_json"] or "{}"),
                )
            )
        return events

    def recent_suggestions(self, room_id, limit=10):
        """读取某个房间最近的建议记录。"""

        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT suggestion_id, room_id, event_id, priority, reply_text,
                       tone, reason, confidence, created_at
                FROM suggestions
                WHERE room_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (room_id, limit),
            ).fetchall()

        suggestions = []
        for row in rows:
            suggestions.append(
                Suggestion(
                    suggestion_id=row["suggestion_id"],
                    room_id=row["room_id"],
                    event_id=row["event_id"],
                    source="heuristic",
                    priority=row["priority"],
                    reply_text=row["reply_text"],
                    tone=row["tone"],
                    reason=row["reason"],
                    confidence=row["confidence"],
                    source_events=[row["event_id"]],
                    references=[],
                    created_at=row["created_at"],
                )
            )
        return suggestions

    def stats(self, room_id):
        """从长期存储里统计某个房间的聚合数据。"""

        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT
                    COUNT(*) AS total_events,
                    SUM(CASE WHEN event_type = 'comment' THEN 1 ELSE 0 END) AS comments,
                    SUM(CASE WHEN event_type = 'gift' THEN 1 ELSE 0 END) AS gifts,
                    SUM(CASE WHEN event_type = 'like' THEN 1 ELSE 0 END) AS likes,
                    SUM(CASE WHEN event_type = 'member' THEN 1 ELSE 0 END) AS members,
                    SUM(CASE WHEN event_type = 'follow' THEN 1 ELSE 0 END) AS follows
                FROM events
                WHERE room_id = ?
                """,
                (room_id,),
            ).fetchone()

        if not row or not row["total_events"]:
            return SessionStats(room_id=room_id)

        return SessionStats(
            room_id=room_id,
            total_events=row["total_events"] or 0,
            comments=row["comments"] or 0,
            gifts=row["gifts"] or 0,
            likes=row["likes"] or 0,
            members=row["members"] or 0,
            follows=row["follows"] or 0,
        )

    def snapshot(self, room_id):
        """直接基于 SQLite 构造一个完整房间快照。"""

        return SessionSnapshot(
            room_id=room_id,
            recent_events=self.recent_events(room_id, limit=30),
            recent_suggestions=self.recent_suggestions(room_id, limit=10),
            stats=self.stats(room_id),
        )

    def get_user_profile(self, room_id, nickname):
        """读取某个房间里某个昵称的画像信息。"""

        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT room_id, nickname, user_id, interaction_count,
                       latest_event_type, latest_content, updated_at
                FROM user_profiles
                WHERE room_id = ? AND nickname = ?
                """,
                (room_id, nickname),
            ).fetchone()

        return dict(row) if row else {}
