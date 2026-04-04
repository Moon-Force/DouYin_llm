import json
import sqlite3

from backend.schemas.live import LiveEvent, Suggestion


class LongTermStore:
    def __init__(self, database_path):
        self.database_path = str(database_path)
        self._setup()

    def _connect(self):
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _setup(self):
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

    def get_user_profile(self, room_id, nickname):
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
