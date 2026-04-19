"""SQLite long-term storage layer."""

import json
import sqlite3
import time
import uuid

from backend.schemas.live import Actor, LiveEvent, SessionSnapshot, SessionStats, Suggestion, ViewerMemory


def current_millis():
    return int(time.time() * 1000)


def safe_text(value):
    if value is None:
        return ""
    return str(value).strip()


def safe_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def viewer_id_from_identity(user_id="", sec_uid="", short_id="", nickname=""):
    for prefix, value in (("id", user_id), ("sec", sec_uid), ("short", short_id), ("nick", nickname)):
        normalized = safe_text(value)
        if normalized:
            return f"{prefix}:{normalized}"
    return ""


class ClosingConnection(sqlite3.Connection):
    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            return super().__exit__(exc_type, exc_val, exc_tb)
        finally:
            self.close()


class LongTermStore:
    def __init__(self, database_path):
        self.database_path = str(database_path)
        self._setup()

    def _connect(self):
        connection = sqlite3.connect(self.database_path, factory=ClosingConnection)
        # Some Windows-mounted drives fail writes under SQLite's default DELETE journal mode.
        connection.execute("PRAGMA journal_mode=TRUNCATE").fetchone()
        connection.row_factory = sqlite3.Row
        return connection

    def _table_columns(self, connection, table_name):
        rows = connection.execute(f"PRAGMA table_info({table_name})").fetchall()
        return {row[1] for row in rows}

    def close(self):
        return None

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

                CREATE TABLE IF NOT EXISTS viewer_profiles (
                    room_id TEXT NOT NULL,
                    viewer_id TEXT NOT NULL,
                    source_room_id TEXT,
                    user_id TEXT,
                    short_id TEXT,
                    sec_uid TEXT,
                    nickname TEXT,
                    total_event_count INTEGER NOT NULL DEFAULT 0,
                    comment_count INTEGER NOT NULL DEFAULT 0,
                    join_count INTEGER NOT NULL DEFAULT 0,
                    gift_event_count INTEGER NOT NULL DEFAULT 0,
                    total_gift_count INTEGER NOT NULL DEFAULT 0,
                    total_diamond_count INTEGER NOT NULL DEFAULT 0,
                    first_seen_at INTEGER NOT NULL,
                    last_seen_at INTEGER NOT NULL,
                    last_session_id TEXT,
                    last_comment TEXT,
                    last_join_at INTEGER,
                    last_gift_name TEXT,
                    last_gift_at INTEGER,
                    PRIMARY KEY (room_id, viewer_id)
                );

                CREATE TABLE IF NOT EXISTS viewer_gifts (
                    room_id TEXT NOT NULL,
                    viewer_id TEXT NOT NULL,
                    gift_name TEXT NOT NULL,
                    source_room_id TEXT,
                    user_id TEXT,
                    short_id TEXT,
                    sec_uid TEXT,
                    nickname TEXT,
                    gift_id TEXT,
                    gift_event_count INTEGER NOT NULL DEFAULT 0,
                    total_gift_count INTEGER NOT NULL DEFAULT 0,
                    total_diamond_count INTEGER NOT NULL DEFAULT 0,
                    first_sent_at INTEGER NOT NULL,
                    last_sent_at INTEGER NOT NULL,
                    PRIMARY KEY (room_id, viewer_id, gift_name)
                );

                CREATE TABLE IF NOT EXISTS live_sessions (
                    session_id TEXT PRIMARY KEY,
                    room_id TEXT NOT NULL,
                    source_room_id TEXT,
                    livename TEXT,
                    status TEXT NOT NULL,
                    started_at INTEGER NOT NULL,
                    last_event_at INTEGER NOT NULL,
                    ended_at INTEGER,
                    event_count INTEGER NOT NULL DEFAULT 0,
                    comment_count INTEGER NOT NULL DEFAULT 0,
                    gift_event_count INTEGER NOT NULL DEFAULT 0,
                    join_count INTEGER NOT NULL DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS viewer_notes (
                    note_id TEXT PRIMARY KEY,
                    room_id TEXT NOT NULL,
                    viewer_id TEXT NOT NULL,
                    author TEXT NOT NULL,
                    content TEXT NOT NULL,
                    is_pinned INTEGER NOT NULL DEFAULT 0,
                    created_at INTEGER NOT NULL,
                    updated_at INTEGER NOT NULL
                );

                CREATE TABLE IF NOT EXISTS viewer_memories (
                    memory_id TEXT PRIMARY KEY,
                    room_id TEXT NOT NULL,
                    viewer_id TEXT NOT NULL,
                    source_event_id TEXT,
                    memory_text TEXT NOT NULL,
                    memory_type TEXT NOT NULL,
                    confidence REAL NOT NULL DEFAULT 0,
                    created_at INTEGER NOT NULL,
                    updated_at INTEGER NOT NULL,
                    last_recalled_at INTEGER,
                    recall_count INTEGER NOT NULL DEFAULT 0,
                    source_kind TEXT NOT NULL DEFAULT 'auto',
                    status TEXT NOT NULL DEFAULT 'active',
                    is_pinned INTEGER NOT NULL DEFAULT 0,
                    correction_reason TEXT NOT NULL DEFAULT '',
                    corrected_by TEXT NOT NULL DEFAULT '',
                    last_operation TEXT NOT NULL DEFAULT 'created',
                    last_operation_at INTEGER NOT NULL DEFAULT 0,
                    memory_text_raw_latest TEXT NOT NULL DEFAULT '',
                    evidence_count INTEGER NOT NULL DEFAULT 1,
                    first_confirmed_at INTEGER NOT NULL DEFAULT 0,
                    last_confirmed_at INTEGER NOT NULL DEFAULT 0,
                    superseded_by TEXT NOT NULL DEFAULT '',
                    merge_parent_id TEXT NOT NULL DEFAULT ''
                );

                CREATE TABLE IF NOT EXISTS viewer_memory_logs (
                    log_id TEXT PRIMARY KEY,
                    memory_id TEXT NOT NULL,
                    room_id TEXT NOT NULL,
                    viewer_id TEXT NOT NULL,
                    operation TEXT NOT NULL,
                    operator TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    old_memory_text TEXT NOT NULL,
                    new_memory_text TEXT NOT NULL,
                    old_memory_type TEXT NOT NULL,
                    new_memory_type TEXT NOT NULL,
                    old_status TEXT NOT NULL,
                    new_status TEXT NOT NULL,
                    old_is_pinned INTEGER NOT NULL DEFAULT 0,
                    new_is_pinned INTEGER NOT NULL DEFAULT 0,
                    created_at INTEGER NOT NULL
                );

                CREATE TABLE IF NOT EXISTS app_settings (
                    setting_key TEXT PRIMARY KEY,
                    setting_value TEXT NOT NULL,
                    updated_at INTEGER NOT NULL
                );
                """
            )
            self._ensure_event_columns(connection)
            self._ensure_viewer_profile_columns(connection)
            self._ensure_viewer_memory_columns(connection)
            self._create_indexes(connection)
            self._backfill_event_columns(connection)
            self._rebuild_viewer_aggregates(connection)
    def _ensure_event_columns(self, connection):
        existing_columns = self._table_columns(connection, "events")
        required_columns = {
            "source_room_id": "TEXT",
            "viewer_id": "TEXT",
            "short_id": "TEXT",
            "sec_uid": "TEXT",
            "gift_name": "TEXT",
            "gift_id": "TEXT",
            "gift_count": "INTEGER NOT NULL DEFAULT 0",
            "gift_diamond_count": "INTEGER NOT NULL DEFAULT 0",
            "session_id": "TEXT",
        }
        for column_name, column_type in required_columns.items():
            if column_name not in existing_columns:
                connection.execute(f"ALTER TABLE events ADD COLUMN {column_name} {column_type}")

    def _ensure_viewer_profile_columns(self, connection):
        existing_columns = self._table_columns(connection, "viewer_profiles")
        required_columns = {
            "total_gift_count": "INTEGER NOT NULL DEFAULT 0",
            "total_diamond_count": "INTEGER NOT NULL DEFAULT 0",
            "last_session_id": "TEXT",
        }
        for column_name, column_type in required_columns.items():
            if column_name not in existing_columns:
                connection.execute(f"ALTER TABLE viewer_profiles ADD COLUMN {column_name} {column_type}")

    def _ensure_viewer_memory_columns(self, connection):
        existing_columns = self._table_columns(connection, "viewer_memories")
        required_columns = {
            "source_kind": "TEXT NOT NULL DEFAULT 'auto'",
            "status": "TEXT NOT NULL DEFAULT 'active'",
            "is_pinned": "INTEGER NOT NULL DEFAULT 0",
            "correction_reason": "TEXT NOT NULL DEFAULT ''",
            "corrected_by": "TEXT NOT NULL DEFAULT ''",
            "last_operation": "TEXT NOT NULL DEFAULT 'created'",
            "last_operation_at": "INTEGER NOT NULL DEFAULT 0",
            "memory_text_raw_latest": "TEXT NOT NULL DEFAULT ''",
            "evidence_count": "INTEGER NOT NULL DEFAULT 1",
            "first_confirmed_at": "INTEGER NOT NULL DEFAULT 0",
            "last_confirmed_at": "INTEGER NOT NULL DEFAULT 0",
            "superseded_by": "TEXT NOT NULL DEFAULT ''",
            "merge_parent_id": "TEXT NOT NULL DEFAULT ''",
        }
        for column_name, column_type in required_columns.items():
            if column_name not in existing_columns:
                connection.execute(f"ALTER TABLE viewer_memories ADD COLUMN {column_name} {column_type}")

    def _create_indexes(self, connection):
        connection.executescript(
            """
            CREATE INDEX IF NOT EXISTS idx_events_room_ts ON events(room_id, ts DESC);
            CREATE INDEX IF NOT EXISTS idx_events_room_viewer_ts ON events(room_id, viewer_id, ts DESC);
            CREATE INDEX IF NOT EXISTS idx_events_room_event_type_ts ON events(room_id, event_type, ts DESC);
            CREATE INDEX IF NOT EXISTS idx_events_session_id ON events(session_id);
            CREATE INDEX IF NOT EXISTS idx_viewer_profiles_room_nickname ON viewer_profiles(room_id, nickname);
            CREATE INDEX IF NOT EXISTS idx_viewer_gifts_room_viewer_last_sent ON viewer_gifts(room_id, viewer_id, last_sent_at DESC);
            CREATE INDEX IF NOT EXISTS idx_live_sessions_room_status_last_event ON live_sessions(room_id, status, last_event_at DESC);
            CREATE INDEX IF NOT EXISTS idx_viewer_notes_room_viewer_updated ON viewer_notes(room_id, viewer_id, updated_at DESC);
            CREATE INDEX IF NOT EXISTS idx_viewer_memories_room_viewer_updated ON viewer_memories(room_id, viewer_id, updated_at DESC);
            CREATE INDEX IF NOT EXISTS idx_viewer_memory_logs_memory_created ON viewer_memory_logs(memory_id, created_at DESC);
            """
        )

    def _extract_gift_fields(self, raw, metadata, event_type):
        gift = raw.get("gift", {}) if isinstance(raw, dict) else {}
        gift_name = safe_text(metadata.get("gift_name") or gift.get("name"))
        gift_id = safe_text(metadata.get("gift_id") or gift.get("id") or raw.get("giftId"))
        gift_count = max(
            safe_int(metadata.get("gift_count")),
            safe_int(raw.get("repeatCount")),
            safe_int(raw.get("comboCount")),
            safe_int(raw.get("groupCount")),
            1 if event_type == "gift" and gift_name else 0,
        )
        gift_diamond_count = max(safe_int(metadata.get("gift_diamond_count")), safe_int(gift.get("diamondCount")), 0)
        return {
            "gift_name": gift_name,
            "gift_id": gift_id,
            "gift_count": gift_count,
            "gift_diamond_count": gift_diamond_count,
        }

    def _event_record_from_event(self, event: LiveEvent):
        metadata = dict(event.metadata or {})
        raw = dict(event.raw or {})
        gift_fields = self._extract_gift_fields(raw, metadata, event.event_type)
        source_room_id = safe_text(event.source_room_id) or safe_text(metadata.get("source_room_id")) or event.room_id
        return {
            "event_id": event.event_id,
            "room_id": event.room_id,
            "source_room_id": source_room_id,
            "session_id": safe_text(event.session_id),
            "platform": event.platform,
            "viewer_id": event.user.viewer_id,
            "event_type": event.event_type,
            "method": event.method,
            "livename": event.livename,
            "user_id": safe_text(event.user.id),
            "short_id": safe_text(event.user.short_id),
            "sec_uid": safe_text(event.user.sec_uid),
            "nickname": safe_text(event.user.nickname),
            "content": event.content,
            "gift_name": gift_fields["gift_name"],
            "gift_id": gift_fields["gift_id"],
            "gift_count": gift_fields["gift_count"],
            "gift_diamond_count": gift_fields["gift_diamond_count"],
            "ts": event.ts,
            "metadata_json": json.dumps(metadata, ensure_ascii=False),
            "raw_json": json.dumps(raw, ensure_ascii=False),
        }

    def _backfill_event_columns(self, connection):
        rows = connection.execute(
            """
            SELECT event_id, room_id, source_room_id, viewer_id, user_id, short_id, sec_uid,
                   nickname, event_type, gift_name, gift_id, gift_count, gift_diamond_count,
                   metadata_json, raw_json
            FROM events
            """
        ).fetchall()
        for row in rows:
            metadata = json.loads(row["metadata_json"] or "{}")
            raw = json.loads(row["raw_json"] or "{}")
            common = raw.get("common", {}) if isinstance(raw, dict) else {}
            user = raw.get("user", {}) if isinstance(raw, dict) else {}
            updates = {
                "source_room_id": safe_text(row["source_room_id"]) or safe_text(metadata.get("source_room_id")) or safe_text(common.get("roomId")) or safe_text(row["room_id"]),
                "user_id": safe_text(row["user_id"]) or safe_text(user.get("id")),
                "short_id": safe_text(row["short_id"]) or safe_text(user.get("shortId") or user.get("displayId")),
                "sec_uid": safe_text(row["sec_uid"]) or safe_text(user.get("secUid")),
                "nickname": safe_text(row["nickname"]) or safe_text(user.get("nickname")),
            }
            updates["viewer_id"] = safe_text(row["viewer_id"]) or viewer_id_from_identity(
                user_id=updates["user_id"], sec_uid=updates["sec_uid"], short_id=updates["short_id"], nickname=updates["nickname"]
            )
            updates.update(self._extract_gift_fields(raw, metadata, row["event_type"]))
            changed = [column_name for column_name, value in updates.items() if row[column_name] != value]
            if not changed:
                continue
            assignments = ", ".join(f"{column_name} = ?" for column_name in changed)
            values = [updates[column_name] for column_name in changed] + [row["event_id"]]
            connection.execute(f"UPDATE events SET {assignments} WHERE event_id = ?", values)
    def _create_live_session(self, connection, event_record):
        session_id = f"live:{event_record['room_id']}:{event_record['ts']}:{uuid.uuid4().hex[:8]}"
        connection.execute(
            """
            INSERT INTO live_sessions (
                session_id, room_id, source_room_id, livename, status,
                started_at, last_event_at, ended_at, event_count, comment_count, gift_event_count, join_count
            ) VALUES (?, ?, ?, ?, 'active', ?, ?, NULL, 0, 0, 0, 0)
            """,
            (session_id, event_record["room_id"], event_record["source_room_id"], event_record["livename"], event_record["ts"], event_record["ts"]),
        )
        return session_id

    def _ensure_active_session(self, connection, event_record):
        active_session = connection.execute(
            """
            SELECT session_id FROM live_sessions
            WHERE room_id = ? AND status = 'active'
            ORDER BY started_at DESC LIMIT 1
            """,
            (event_record["room_id"],),
        ).fetchone()
        if active_session:
            return active_session["session_id"]
        return self._create_live_session(connection, event_record)

    def _touch_live_session(self, connection, event_record):
        connection.execute(
            """
            UPDATE live_sessions
            SET source_room_id = CASE WHEN ? <> '' THEN ? ELSE source_room_id END,
                livename = CASE WHEN ? <> '' THEN ? ELSE livename END,
                last_event_at = CASE WHEN last_event_at >= ? THEN last_event_at ELSE ? END,
                event_count = event_count + 1,
                comment_count = comment_count + ?,
                gift_event_count = gift_event_count + ?,
                join_count = join_count + ?
            WHERE session_id = ?
            """,
            (
                event_record["source_room_id"], event_record["source_room_id"],
                event_record["livename"], event_record["livename"],
                event_record["ts"], event_record["ts"],
                1 if event_record["event_type"] == "comment" else 0,
                1 if event_record["event_type"] == "gift" else 0,
                1 if event_record["event_type"] == "member" else 0,
                event_record["session_id"],
            ),
        )

    def _upsert_viewer_profile(self, connection, event_record):
        viewer_id = safe_text(event_record["viewer_id"])
        if not viewer_id:
            return
        is_comment = event_record["event_type"] == "comment"
        is_member = event_record["event_type"] == "member"
        is_gift = event_record["event_type"] == "gift"
        gift_count = safe_int(event_record["gift_count"]) if is_gift else 0
        total_diamond_count = gift_count * safe_int(event_record["gift_diamond_count"]) if is_gift else 0
        connection.execute(
            """
            INSERT INTO viewer_profiles (
                room_id, viewer_id, source_room_id, user_id, short_id, sec_uid, nickname,
                total_event_count, comment_count, join_count, gift_event_count,
                total_gift_count, total_diamond_count, first_seen_at, last_seen_at,
                last_session_id, last_comment, last_join_at, last_gift_name, last_gift_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(room_id, viewer_id) DO UPDATE SET
                source_room_id = CASE WHEN excluded.source_room_id <> '' THEN excluded.source_room_id ELSE viewer_profiles.source_room_id END,
                user_id = CASE WHEN excluded.user_id <> '' THEN excluded.user_id ELSE viewer_profiles.user_id END,
                short_id = CASE WHEN excluded.short_id <> '' THEN excluded.short_id ELSE viewer_profiles.short_id END,
                sec_uid = CASE WHEN excluded.sec_uid <> '' THEN excluded.sec_uid ELSE viewer_profiles.sec_uid END,
                nickname = CASE WHEN excluded.nickname <> '' THEN excluded.nickname ELSE viewer_profiles.nickname END,
                total_event_count = viewer_profiles.total_event_count + 1,
                comment_count = viewer_profiles.comment_count + excluded.comment_count,
                join_count = viewer_profiles.join_count + excluded.join_count,
                gift_event_count = viewer_profiles.gift_event_count + excluded.gift_event_count,
                total_gift_count = viewer_profiles.total_gift_count + excluded.total_gift_count,
                total_diamond_count = viewer_profiles.total_diamond_count + excluded.total_diamond_count,
                first_seen_at = CASE WHEN viewer_profiles.first_seen_at <= excluded.first_seen_at THEN viewer_profiles.first_seen_at ELSE excluded.first_seen_at END,
                last_seen_at = CASE WHEN viewer_profiles.last_seen_at >= excluded.last_seen_at THEN viewer_profiles.last_seen_at ELSE excluded.last_seen_at END,
                last_session_id = CASE WHEN excluded.last_session_id <> '' THEN excluded.last_session_id ELSE viewer_profiles.last_session_id END,
                last_comment = CASE WHEN excluded.last_comment <> '' THEN excluded.last_comment ELSE viewer_profiles.last_comment END,
                last_join_at = CASE WHEN excluded.last_join_at IS NOT NULL THEN excluded.last_join_at ELSE viewer_profiles.last_join_at END,
                last_gift_name = CASE WHEN excluded.last_gift_name <> '' THEN excluded.last_gift_name ELSE viewer_profiles.last_gift_name END,
                last_gift_at = CASE WHEN excluded.last_gift_at IS NOT NULL THEN excluded.last_gift_at ELSE viewer_profiles.last_gift_at END
            """,
            (
                event_record["room_id"], viewer_id, event_record["source_room_id"], event_record["user_id"], event_record["short_id"], event_record["sec_uid"], event_record["nickname"],
                1 if is_comment else 0, 1 if is_member else 0, 1 if is_gift else 0,
                gift_count, total_diamond_count, event_record["ts"], event_record["ts"], event_record["session_id"],
                event_record["content"] if is_comment else "", event_record["ts"] if is_member else None,
                event_record["gift_name"] if is_gift else "", event_record["ts"] if is_gift else None,
            ),
        )

    def _upsert_viewer_gift(self, connection, event_record):
        viewer_id = safe_text(event_record["viewer_id"])
        gift_name = safe_text(event_record["gift_name"])
        if not viewer_id or not gift_name:
            return
        gift_count = max(safe_int(event_record["gift_count"]), 1)
        total_diamond_count = gift_count * max(safe_int(event_record["gift_diamond_count"]), 0)
        connection.execute(
            """
            INSERT INTO viewer_gifts (
                room_id, viewer_id, gift_name, source_room_id, user_id, short_id, sec_uid,
                nickname, gift_id, gift_event_count, total_gift_count, total_diamond_count, first_sent_at, last_sent_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?, ?)
            ON CONFLICT(room_id, viewer_id, gift_name) DO UPDATE SET
                source_room_id = CASE WHEN excluded.source_room_id <> '' THEN excluded.source_room_id ELSE viewer_gifts.source_room_id END,
                user_id = CASE WHEN excluded.user_id <> '' THEN excluded.user_id ELSE viewer_gifts.user_id END,
                short_id = CASE WHEN excluded.short_id <> '' THEN excluded.short_id ELSE viewer_gifts.short_id END,
                sec_uid = CASE WHEN excluded.sec_uid <> '' THEN excluded.sec_uid ELSE viewer_gifts.sec_uid END,
                nickname = CASE WHEN excluded.nickname <> '' THEN excluded.nickname ELSE viewer_gifts.nickname END,
                gift_id = CASE WHEN excluded.gift_id <> '' THEN excluded.gift_id ELSE viewer_gifts.gift_id END,
                gift_event_count = viewer_gifts.gift_event_count + 1,
                total_gift_count = viewer_gifts.total_gift_count + excluded.total_gift_count,
                total_diamond_count = viewer_gifts.total_diamond_count + excluded.total_diamond_count,
                first_sent_at = CASE WHEN viewer_gifts.first_sent_at <= excluded.first_sent_at THEN viewer_gifts.first_sent_at ELSE excluded.first_sent_at END,
                last_sent_at = CASE WHEN viewer_gifts.last_sent_at >= excluded.last_sent_at THEN viewer_gifts.last_sent_at ELSE excluded.last_sent_at END
            """,
            (
                event_record["room_id"], viewer_id, gift_name, event_record["source_room_id"], event_record["user_id"], event_record["short_id"], event_record["sec_uid"],
                event_record["nickname"], event_record["gift_id"], gift_count, total_diamond_count, event_record["ts"], event_record["ts"],
            ),
        )

    def _rebuild_viewer_aggregates(self, connection):
        connection.execute("DELETE FROM viewer_profiles")
        connection.execute("DELETE FROM viewer_gifts")
        rows = connection.execute(
            """
            SELECT event_id, room_id, source_room_id, session_id, platform, viewer_id, event_type, method, livename,
                   user_id, short_id, sec_uid, nickname, content, gift_name, gift_id, gift_count, gift_diamond_count,
                   ts, metadata_json, raw_json
            FROM events ORDER BY ts ASC, event_id ASC
            """
        ).fetchall()
        for row in rows:
            event_record = dict(row)
            self._upsert_viewer_profile(connection, event_record)
            if event_record["event_type"] == "gift":
                self._upsert_viewer_gift(connection, event_record)
    def persist_event(self, event: LiveEvent):
        event_record = self._event_record_from_event(event)
        with self._connect() as connection:
            existing_row = connection.execute(
                "SELECT event_id, session_id FROM events WHERE event_id = ?",
                (event_record["event_id"],),
            ).fetchone()
            if existing_row and safe_text(existing_row["session_id"]):
                event_record["session_id"] = safe_text(existing_row["session_id"])
            else:
                event_record["session_id"] = self._ensure_active_session(connection, event_record)
            connection.execute(
                """
                INSERT OR REPLACE INTO events (
                    event_id, room_id, source_room_id, session_id, platform, viewer_id, event_type, method,
                    livename, user_id, short_id, sec_uid, nickname, content, gift_name, gift_id,
                    gift_count, gift_diamond_count, ts, metadata_json, raw_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event_record["event_id"], event_record["room_id"], event_record["source_room_id"], event_record["session_id"], event_record["platform"],
                    event_record["viewer_id"], event_record["event_type"], event_record["method"], event_record["livename"], event_record["user_id"],
                    event_record["short_id"], event_record["sec_uid"], event_record["nickname"], event_record["content"], event_record["gift_name"],
                    event_record["gift_id"], event_record["gift_count"], event_record["gift_diamond_count"], event_record["ts"], event_record["metadata_json"], event_record["raw_json"],
                ),
            )
            if existing_row:
                self._rebuild_viewer_aggregates(connection)
            else:
                self._touch_live_session(connection, event_record)
                self._upsert_viewer_profile(connection, event_record)
                if event_record["event_type"] == "gift":
                    self._upsert_viewer_gift(connection, event_record)
        event.session_id = event_record["session_id"]
        return event_record["session_id"]

    def persist_suggestion(self, suggestion: Suggestion):
        with self._connect() as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO suggestions (
                    suggestion_id, room_id, event_id, priority, reply_text, tone, reason, confidence, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (suggestion.suggestion_id, suggestion.room_id, suggestion.event_id, suggestion.priority, suggestion.reply_text, suggestion.tone, suggestion.reason, suggestion.confidence, suggestion.created_at),
            )

    def recent_events(self, room_id, limit=30):
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT event_id, room_id, source_room_id, session_id, platform, event_type, method, livename,
                       user_id, short_id, sec_uid, nickname, content, ts, metadata_json, raw_json
                FROM events WHERE room_id = ? ORDER BY ts DESC LIMIT ?
                """,
                (room_id, limit),
            ).fetchall()
        return [
            LiveEvent(
                event_id=row["event_id"], room_id=row["room_id"], source_room_id=row["source_room_id"] or row["room_id"], session_id=row["session_id"] or "",
                platform=row["platform"], event_type=row["event_type"], method=row["method"], livename=row["livename"], ts=row["ts"],
                user=Actor(id=row["user_id"] or "", short_id=row["short_id"] or "", sec_uid=row["sec_uid"] or "", nickname=row["nickname"] or Actor().nickname),
                content=row["content"] or "", metadata=json.loads(row["metadata_json"] or "{}"), raw=json.loads(row["raw_json"] or "{}"),
            )
            for row in rows
        ]

    def recent_suggestions(self, room_id, limit=10):
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT suggestion_id, room_id, event_id, priority, reply_text, tone, reason, confidence, created_at
                FROM suggestions WHERE room_id = ? ORDER BY created_at DESC LIMIT ?
                """,
                (room_id, limit),
            ).fetchall()
        return [
            Suggestion(
                suggestion_id=row["suggestion_id"], room_id=row["room_id"], event_id=row["event_id"], source="heuristic", priority=row["priority"],
                reply_text=row["reply_text"], tone=row["tone"], reason=row["reason"], confidence=row["confidence"], source_events=[row["event_id"]], references=[], created_at=row["created_at"],
            )
            for row in rows
        ]

    def stats(self, room_id):
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT COUNT(*) AS total_events,
                       SUM(CASE WHEN event_type = 'comment' THEN 1 ELSE 0 END) AS comments,
                       SUM(CASE WHEN event_type = 'gift' THEN 1 ELSE 0 END) AS gifts,
                       SUM(CASE WHEN event_type = 'like' THEN 1 ELSE 0 END) AS likes,
                       SUM(CASE WHEN event_type = 'member' THEN 1 ELSE 0 END) AS members,
                       SUM(CASE WHEN event_type = 'follow' THEN 1 ELSE 0 END) AS follows
                FROM events WHERE room_id = ?
                """,
                (room_id,),
            ).fetchone()
        if not row or not row["total_events"]:
            return SessionStats(room_id=room_id)
        return SessionStats(room_id=room_id, total_events=row["total_events"] or 0, comments=row["comments"] or 0, gifts=row["gifts"] or 0, likes=row["likes"] or 0, members=row["members"] or 0, follows=row["follows"] or 0)

    def snapshot(self, room_id):
        return SessionSnapshot(room_id=room_id, recent_events=self.recent_events(room_id, limit=30), recent_suggestions=self.recent_suggestions(room_id, limit=10), stats=self.stats(room_id))

    def _find_viewer_profile(self, connection, room_id, viewer_id="", nickname=""):
        row = None
        if viewer_id:
            row = connection.execute(
                """
                SELECT room_id, viewer_id, source_room_id, user_id, short_id, sec_uid, nickname,
                       total_event_count, comment_count, join_count, gift_event_count, total_gift_count,
                       total_diamond_count, first_seen_at, last_seen_at, last_session_id, last_comment,
                       last_join_at, last_gift_name, last_gift_at
                FROM viewer_profiles WHERE room_id = ? AND viewer_id = ?
                """,
                (room_id, viewer_id),
            ).fetchone()
        if not row and nickname:
            row = connection.execute(
                """
                SELECT room_id, viewer_id, source_room_id, user_id, short_id, sec_uid, nickname,
                       total_event_count, comment_count, join_count, gift_event_count, total_gift_count,
                       total_diamond_count, first_seen_at, last_seen_at, last_session_id, last_comment,
                       last_join_at, last_gift_name, last_gift_at
                FROM viewer_profiles WHERE room_id = ? AND nickname = ? ORDER BY last_seen_at DESC LIMIT 1
                """,
                (room_id, nickname),
            ).fetchone()
        if row:
            return row
        tables = {table_row[0] for table_row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if not nickname or "user_profiles" not in tables:
            return None
        return connection.execute(
            """
            SELECT room_id, '' AS viewer_id, '' AS source_room_id, user_id, '' AS short_id, '' AS sec_uid,
                   nickname, interaction_count AS total_event_count, 0 AS comment_count, 0 AS join_count,
                   0 AS gift_event_count, 0 AS total_gift_count, 0 AS total_diamond_count,
                   updated_at AS first_seen_at, updated_at AS last_seen_at, '' AS last_session_id,
                   latest_content AS last_comment, NULL AS last_join_at, NULL AS last_gift_name, NULL AS last_gift_at
            FROM user_profiles WHERE room_id = ? AND nickname = ? LIMIT 1
            """,
            (room_id, nickname),
        ).fetchone()

    def viewer_event_history(self, room_id, viewer_id, event_type=None, limit=20):
        if not viewer_id:
            return []
        with self._connect() as connection:
            if event_type:
                rows = connection.execute(
                    """
                    SELECT event_id, session_id, event_type, method, content, gift_name, gift_count, gift_diamond_count, ts
                    FROM events WHERE room_id = ? AND viewer_id = ? AND event_type = ? ORDER BY ts DESC LIMIT ?
                    """,
                    (room_id, viewer_id, event_type, limit),
                ).fetchall()
            else:
                rows = connection.execute(
                    """
                    SELECT event_id, session_id, event_type, method, content, gift_name, gift_count, gift_diamond_count, ts
                    FROM events WHERE room_id = ? AND viewer_id = ? ORDER BY ts DESC LIMIT ?
                    """,
                    (room_id, viewer_id, limit),
                ).fetchall()
        return [dict(row) for row in rows]
    def viewer_gift_history(self, room_id, viewer_id, limit=10):
        if not viewer_id:
            return []
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT gift_name, gift_id, gift_event_count, total_gift_count, total_diamond_count, first_sent_at, last_sent_at
                FROM viewer_gifts WHERE room_id = ? AND viewer_id = ? ORDER BY last_sent_at DESC, gift_name ASC LIMIT ?
                """,
                (room_id, viewer_id, limit),
            ).fetchall()
        return [dict(row) for row in rows]

    def viewer_session_history(self, room_id, viewer_id, limit=10):
        if not viewer_id:
            return []
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT e.session_id, COALESCE(ls.status, '') AS status, COALESCE(ls.started_at, MIN(e.ts)) AS started_at,
                       ls.ended_at, MAX(e.ts) AS last_viewer_event_at,
                       SUM(CASE WHEN e.event_type = 'comment' THEN 1 ELSE 0 END) AS comment_count,
                       SUM(CASE WHEN e.event_type = 'gift' THEN 1 ELSE 0 END) AS gift_event_count,
                       SUM(CASE WHEN e.event_type = 'member' THEN 1 ELSE 0 END) AS join_count
                FROM events e LEFT JOIN live_sessions ls ON ls.session_id = e.session_id
                WHERE e.room_id = ? AND e.viewer_id = ? AND COALESCE(e.session_id, '') <> ''
                GROUP BY e.session_id, ls.status, ls.started_at, ls.ended_at
                ORDER BY MAX(e.ts) DESC LIMIT ?
                """,
                (room_id, viewer_id, limit),
            ).fetchall()
        return [dict(row) for row in rows]

    def list_viewer_notes(self, room_id, viewer_id, limit=20):
        if not viewer_id:
            return []
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT note_id, room_id, viewer_id, author, content, is_pinned, created_at, updated_at
                FROM viewer_notes WHERE room_id = ? AND viewer_id = ?
                ORDER BY is_pinned DESC, updated_at DESC LIMIT ?
                """,
                (room_id, viewer_id, limit),
            ).fetchall()
        return [dict(row) for row in rows]

    def get_viewer_note(self, note_id):
        with self._connect() as connection:
            row = connection.execute(
                "SELECT note_id, room_id, viewer_id, author, content, is_pinned, created_at, updated_at FROM viewer_notes WHERE note_id = ?",
                (note_id,),
            ).fetchone()
        return dict(row) if row else {}

    def _viewer_memory_from_row(self, row):
        if not row:
            return None
        return ViewerMemory(
            memory_id=row["memory_id"],
            room_id=row["room_id"],
            viewer_id=row["viewer_id"],
            source_event_id=row["source_event_id"] or "",
            memory_text=row["memory_text"],
            memory_type=row["memory_type"] or "fact",
            confidence=row["confidence"] or 0.0,
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            last_recalled_at=row["last_recalled_at"],
            recall_count=row["recall_count"] or 0,
            source_kind=row["source_kind"] or "auto",
            status=row["status"] or "active",
            is_pinned=bool(row["is_pinned"]),
            correction_reason=row["correction_reason"] or "",
            corrected_by=row["corrected_by"] or "",
            last_operation=row["last_operation"] or "created",
            last_operation_at=row["last_operation_at"] or row["updated_at"],
            memory_text_raw_latest=row["memory_text_raw_latest"] or "",
            evidence_count=row["evidence_count"] or 0,
            first_confirmed_at=row["first_confirmed_at"] or 0,
            last_confirmed_at=row["last_confirmed_at"] or 0,
            superseded_by=row["superseded_by"] or "",
            merge_parent_id=row["merge_parent_id"] or "",
        )

    def list_all_viewer_memories(self, limit=5000):
        limit = max(1, min(int(limit), 20000))
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT memory_id, room_id, viewer_id, source_event_id, memory_text, memory_type,
                       confidence, created_at, updated_at, last_recalled_at, recall_count,
                       source_kind, status, is_pinned, correction_reason, corrected_by,
                       last_operation, last_operation_at, memory_text_raw_latest, evidence_count,
                       first_confirmed_at, last_confirmed_at, superseded_by, merge_parent_id
                FROM viewer_memories
                WHERE status <> 'deleted'
                ORDER BY updated_at DESC LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [self._viewer_memory_from_row(row) for row in rows if row]

    def list_viewer_memories(self, room_id, viewer_id, limit=20):
        if not viewer_id:
            return []
        limit = max(1, min(int(limit), 200))
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT memory_id, room_id, viewer_id, source_event_id, memory_text, memory_type,
                       confidence, created_at, updated_at, last_recalled_at, recall_count,
                       source_kind, status, is_pinned, correction_reason, corrected_by,
                       last_operation, last_operation_at, memory_text_raw_latest, evidence_count,
                       first_confirmed_at, last_confirmed_at, superseded_by, merge_parent_id
                FROM viewer_memories
                WHERE room_id = ? AND viewer_id = ? AND status <> 'deleted'
                ORDER BY is_pinned DESC, updated_at DESC LIMIT ?
                """,
                (room_id, viewer_id, limit),
            ).fetchall()
        return [dict(row) for row in rows]

    def get_viewer_memory(self, memory_id):
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT memory_id, room_id, viewer_id, source_event_id, memory_text, memory_type,
                       confidence, created_at, updated_at, last_recalled_at, recall_count,
                       source_kind, status, is_pinned, correction_reason, corrected_by,
                       last_operation, last_operation_at, memory_text_raw_latest, evidence_count,
                       first_confirmed_at, last_confirmed_at, superseded_by, merge_parent_id
                FROM viewer_memories WHERE memory_id = ?
                """,
                (memory_id,),
            ).fetchone()
        return self._viewer_memory_from_row(row)

    def _append_viewer_memory_log(
        self,
        connection,
        memory_id,
        room_id,
        viewer_id,
        operation,
        operator="",
        reason="",
        old_memory_text="",
        new_memory_text="",
        old_memory_type="",
        new_memory_type="",
        old_status="",
        new_status="",
        old_is_pinned=False,
        new_is_pinned=False,
    ):
        connection.execute(
            """
            INSERT INTO viewer_memory_logs (
                log_id, memory_id, room_id, viewer_id, operation, operator, reason,
                old_memory_text, new_memory_text, old_memory_type, new_memory_type,
                old_status, new_status, old_is_pinned, new_is_pinned, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid.uuid4()),
                memory_id,
                room_id,
                viewer_id,
                operation,
                operator,
                reason,
                old_memory_text,
                new_memory_text,
                old_memory_type,
                new_memory_type,
                old_status,
                new_status,
                1 if old_is_pinned else 0,
                1 if new_is_pinned else 0,
                current_millis(),
            ),
        )

    def save_viewer_memory(
        self,
        room_id,
        viewer_id,
        memory_text,
        source_event_id="",
        memory_type="fact",
        confidence=0.0,
        source_kind="auto",
        status="active",
        is_pinned=False,
        correction_reason="",
        corrected_by="",
        operation="created",
        raw_memory_text="",
        evidence_count=1,
        first_confirmed_at=0,
        last_confirmed_at=0,
        superseded_by="",
        merge_parent_id="",
    ):
        room_id = safe_text(room_id)
        viewer_id = safe_text(viewer_id)
        memory_text = safe_text(memory_text)
        source_event_id = safe_text(source_event_id)
        memory_type = safe_text(memory_type) or "fact"
        source_kind = safe_text(source_kind) or "auto"
        status = safe_text(status) or "active"
        correction_reason = safe_text(correction_reason)
        corrected_by = safe_text(corrected_by)
        operation = safe_text(operation) or "created"
        raw_memory_text = safe_text(raw_memory_text)
        superseded_by = safe_text(superseded_by)
        merge_parent_id = safe_text(merge_parent_id)
        if not room_id or not viewer_id or not memory_text:
            return None

        try:
            confidence = float(confidence)
        except (TypeError, ValueError):
            confidence = 0.0
        confidence = max(0.0, min(confidence, 1.0))
        evidence_count = max(0, safe_int(evidence_count, 1))
        timestamp = current_millis()
        first_confirmed_at = safe_int(first_confirmed_at, timestamp if evidence_count else 0)
        last_confirmed_at = safe_int(last_confirmed_at, timestamp if evidence_count else 0)

        with self._connect() as connection:
            existing = connection.execute(
                """
                SELECT memory_id, created_at, last_recalled_at, recall_count,
                       memory_text_raw_latest, evidence_count, first_confirmed_at,
                       last_confirmed_at, superseded_by, merge_parent_id
                FROM viewer_memories
                WHERE room_id = ? AND viewer_id = ? AND source_event_id = ? AND memory_text = ?
                LIMIT 1
                """,
                (room_id, viewer_id, source_event_id, memory_text),
            ).fetchone()
            memory_id = existing["memory_id"] if existing else str(uuid.uuid4())
            created_at = existing["created_at"] if existing else timestamp
            last_recalled_at = existing["last_recalled_at"] if existing else None
            recall_count = existing["recall_count"] if existing else 0
            memory_text_raw_latest = raw_memory_text if raw_memory_text else (
                existing["memory_text_raw_latest"] if existing else ""
            )
            persisted_evidence_count = evidence_count if existing is None else max(
                evidence_count,
                safe_int(existing["evidence_count"], evidence_count),
            )
            persisted_first_confirmed_at = first_confirmed_at if existing is None else safe_int(
                existing["first_confirmed_at"], first_confirmed_at
            )
            persisted_last_confirmed_at = last_confirmed_at if existing is None else max(
                last_confirmed_at,
                safe_int(existing["last_confirmed_at"], last_confirmed_at),
            )
            persisted_superseded_by = superseded_by if superseded_by else (existing["superseded_by"] if existing else "")
            persisted_merge_parent_id = merge_parent_id if merge_parent_id else (existing["merge_parent_id"] if existing else "")
            connection.execute(
                """
                INSERT OR REPLACE INTO viewer_memories (
                    memory_id, room_id, viewer_id, source_event_id, memory_text, memory_type,
                    confidence, created_at, updated_at, last_recalled_at, recall_count,
                    source_kind, status, is_pinned, correction_reason, corrected_by,
                    last_operation, last_operation_at, memory_text_raw_latest, evidence_count,
                    first_confirmed_at, last_confirmed_at, superseded_by, merge_parent_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    memory_id,
                    room_id,
                    viewer_id,
                    source_event_id,
                    memory_text,
                    memory_type,
                    confidence,
                    created_at,
                    timestamp,
                    last_recalled_at,
                    recall_count,
                    source_kind,
                    status,
                    1 if is_pinned else 0,
                    correction_reason,
                    corrected_by,
                    operation,
                    timestamp,
                    memory_text_raw_latest,
                    persisted_evidence_count,
                    persisted_first_confirmed_at,
                    persisted_last_confirmed_at,
                    persisted_superseded_by,
                    persisted_merge_parent_id,
                ),
            )
            self._append_viewer_memory_log(
                connection,
                memory_id=memory_id,
                room_id=room_id,
                viewer_id=viewer_id,
                operation=operation,
                operator=corrected_by,
                reason=correction_reason,
                new_memory_text=memory_text,
                new_memory_type=memory_type,
                new_status=status,
                new_is_pinned=is_pinned,
            )
        return self.get_viewer_memory(memory_id)

    def update_viewer_memory(self, memory_id, memory_text="", memory_type="", is_pinned=False, correction_reason="", corrected_by="主播"):
        existing = self.get_viewer_memory(memory_id)
        if not existing or existing.status == "deleted":
            return None

        timestamp = current_millis()
        next_text = safe_text(memory_text) or existing.memory_text
        next_type = safe_text(memory_type) or existing.memory_type
        next_reason = safe_text(correction_reason)
        next_is_pinned = bool(is_pinned) and existing.status == "active"

        with self._connect() as connection:
            connection.execute(
                """
                UPDATE viewer_memories
                SET memory_text = ?, memory_type = ?, is_pinned = ?, correction_reason = ?,
                    corrected_by = ?, updated_at = ?, last_operation = ?, last_operation_at = ?
                WHERE memory_id = ?
                """,
                (
                    next_text,
                    next_type,
                    1 if next_is_pinned else 0,
                    next_reason,
                    safe_text(corrected_by),
                    timestamp,
                    "edited",
                    timestamp,
                    memory_id,
                ),
            )
            self._append_viewer_memory_log(
                connection,
                memory_id=existing.memory_id,
                room_id=existing.room_id,
                viewer_id=existing.viewer_id,
                operation="edited",
                operator=safe_text(corrected_by),
                reason=next_reason,
                old_memory_text=existing.memory_text,
                new_memory_text=next_text,
                old_memory_type=existing.memory_type,
                new_memory_type=next_type,
                old_status=existing.status,
                new_status=existing.status,
                old_is_pinned=existing.is_pinned,
                new_is_pinned=next_is_pinned,
            )
        return self.get_viewer_memory(memory_id)

    def merge_viewer_memory_evidence(self, memory_id, raw_memory_text="", confidence=0.0, source_event_id=""):
        existing = self.get_viewer_memory(memory_id)
        if not existing or existing.status != "active":
            return None

        timestamp = current_millis()
        next_raw_text = safe_text(raw_memory_text) or existing.memory_text_raw_latest
        try:
            next_confidence = max(float(confidence), float(existing.confidence))
        except (TypeError, ValueError):
            next_confidence = existing.confidence

        with self._connect() as connection:
            connection.execute(
                """
                UPDATE viewer_memories
                SET memory_text_raw_latest = ?, confidence = ?, evidence_count = ?, last_confirmed_at = ?,
                    updated_at = ?, last_operation = ?, last_operation_at = ?
                WHERE memory_id = ?
                """,
                (
                    next_raw_text,
                    next_confidence,
                    max(1, existing.evidence_count) + 1,
                    timestamp,
                    timestamp,
                    "merged",
                    timestamp,
                    memory_id,
                ),
            )
            self._append_viewer_memory_log(
                connection,
                memory_id=existing.memory_id,
                room_id=existing.room_id,
                viewer_id=existing.viewer_id,
                operation="merged",
                operator="system",
                reason=safe_text(source_event_id),
                old_memory_text=existing.memory_text,
                new_memory_text=existing.memory_text,
                old_memory_type=existing.memory_type,
                new_memory_type=existing.memory_type,
                old_status=existing.status,
                new_status=existing.status,
                old_is_pinned=existing.is_pinned,
                new_is_pinned=existing.is_pinned,
            )
        return self.get_viewer_memory(memory_id)

    def upgrade_viewer_memory(self, memory_id, memory_text="", raw_memory_text="", confidence=0.0, source_event_id=""):
        existing = self.get_viewer_memory(memory_id)
        if not existing or existing.status != "active":
            return None

        timestamp = current_millis()
        next_text = safe_text(memory_text) or existing.memory_text
        next_raw_text = safe_text(raw_memory_text) or existing.memory_text_raw_latest
        try:
            next_confidence = max(float(confidence), float(existing.confidence))
        except (TypeError, ValueError):
            next_confidence = existing.confidence

        with self._connect() as connection:
            connection.execute(
                """
                UPDATE viewer_memories
                SET memory_text = ?, memory_text_raw_latest = ?, confidence = ?, evidence_count = ?, last_confirmed_at = ?,
                    updated_at = ?, last_operation = ?, last_operation_at = ?
                WHERE memory_id = ?
                """,
                (
                    next_text,
                    next_raw_text,
                    next_confidence,
                    max(1, existing.evidence_count) + 1,
                    timestamp,
                    timestamp,
                    "upgraded",
                    timestamp,
                    memory_id,
                ),
            )
            self._append_viewer_memory_log(
                connection,
                memory_id=existing.memory_id,
                room_id=existing.room_id,
                viewer_id=existing.viewer_id,
                operation="upgraded",
                operator="system",
                reason=safe_text(source_event_id),
                old_memory_text=existing.memory_text,
                new_memory_text=next_text,
                old_memory_type=existing.memory_type,
                new_memory_type=existing.memory_type,
                old_status=existing.status,
                new_status=existing.status,
                old_is_pinned=existing.is_pinned,
                new_is_pinned=existing.is_pinned,
            )
        return self.get_viewer_memory(memory_id)

    def supersede_viewer_memory(
        self,
        memory_id,
        room_id,
        viewer_id,
        memory_text,
        raw_memory_text="",
        source_event_id="",
        memory_type="fact",
        confidence=0.0,
    ):
        existing = self.get_viewer_memory(memory_id)
        if not existing or existing.status != "active":
            return None, None

        timestamp = current_millis()
        new_memory = self.save_viewer_memory(
            room_id=room_id,
            viewer_id=viewer_id,
            memory_text=memory_text,
            source_event_id=source_event_id,
            memory_type=memory_type,
            confidence=confidence,
            source_kind="auto",
            status="active",
            is_pinned=False,
            correction_reason="",
            corrected_by="system",
            operation="created",
            raw_memory_text=raw_memory_text,
            evidence_count=1,
            first_confirmed_at=timestamp,
            last_confirmed_at=timestamp,
            superseded_by="",
            merge_parent_id="",
        )
        if new_memory is None:
            return None, None

        with self._connect() as connection:
            connection.execute(
                """
                UPDATE viewer_memories
                SET status = ?, is_pinned = 0, superseded_by = ?, updated_at = ?, last_operation = ?, last_operation_at = ?
                WHERE memory_id = ?
                """,
                (
                    "invalid",
                    new_memory.memory_id,
                    timestamp,
                    "superseded",
                    timestamp,
                    memory_id,
                ),
            )
            self._append_viewer_memory_log(
                connection,
                memory_id=existing.memory_id,
                room_id=existing.room_id,
                viewer_id=existing.viewer_id,
                operation="superseded",
                operator="system",
                reason=f"superseded_by:{new_memory.memory_id}",
                old_memory_text=existing.memory_text,
                new_memory_text=existing.memory_text,
                old_memory_type=existing.memory_type,
                new_memory_type=existing.memory_type,
                old_status=existing.status,
                new_status="invalid",
                old_is_pinned=existing.is_pinned,
                new_is_pinned=False,
            )
        return self.get_viewer_memory(memory_id), self.get_viewer_memory(new_memory.memory_id)

    def _set_viewer_memory_status(self, memory_id, status, reason="", corrected_by="主播", operation="invalidated"):
        existing = self.get_viewer_memory(memory_id)
        if not existing or existing.status == "deleted":
            return None

        timestamp = current_millis()
        next_status = safe_text(status) or existing.status
        next_reason = safe_text(reason)
        next_is_pinned = existing.is_pinned if next_status == "active" else False

        with self._connect() as connection:
            connection.execute(
                """
                UPDATE viewer_memories
                SET status = ?, is_pinned = ?, correction_reason = ?, corrected_by = ?,
                    updated_at = ?, last_operation = ?, last_operation_at = ?
                WHERE memory_id = ?
                """,
                (
                    next_status,
                    1 if next_is_pinned else 0,
                    next_reason,
                    safe_text(corrected_by),
                    timestamp,
                    operation,
                    timestamp,
                    memory_id,
                ),
            )
            self._append_viewer_memory_log(
                connection,
                memory_id=existing.memory_id,
                room_id=existing.room_id,
                viewer_id=existing.viewer_id,
                operation=operation,
                operator=safe_text(corrected_by),
                reason=next_reason,
                old_memory_text=existing.memory_text,
                new_memory_text=existing.memory_text,
                old_memory_type=existing.memory_type,
                new_memory_type=existing.memory_type,
                old_status=existing.status,
                new_status=next_status,
                old_is_pinned=existing.is_pinned,
                new_is_pinned=next_is_pinned,
            )
        return self.get_viewer_memory(memory_id)

    def invalidate_viewer_memory(self, memory_id, reason="", corrected_by="主播"):
        return self._set_viewer_memory_status(
            memory_id,
            status="invalid",
            reason=reason,
            corrected_by=corrected_by,
            operation="invalidated",
        )

    def reactivate_viewer_memory(self, memory_id, reason="", corrected_by="主播"):
        return self._set_viewer_memory_status(
            memory_id,
            status="active",
            reason=reason,
            corrected_by=corrected_by,
            operation="reactivated",
        )

    def delete_viewer_memory(self, memory_id, reason="", corrected_by="主播"):
        return self._set_viewer_memory_status(
            memory_id,
            status="deleted",
            reason=reason,
            corrected_by=corrected_by,
            operation="deleted",
        )

    def list_viewer_memory_logs(self, memory_id, limit=20):
        limit = max(1, min(int(limit), 100))
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT log_id, memory_id, room_id, viewer_id, operation, operator, reason,
                       old_memory_text, new_memory_text, old_memory_type, new_memory_type,
                       old_status, new_status, old_is_pinned, new_is_pinned, created_at
                FROM viewer_memory_logs
                WHERE memory_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (memory_id, limit),
            ).fetchall()
        return [dict(row) for row in rows]

    def touch_viewer_memories(self, memory_ids, recalled_at=None):
        normalized_ids = [safe_text(memory_id) for memory_id in memory_ids if safe_text(memory_id)]
        if not normalized_ids:
            return 0
        recalled_at = safe_int(recalled_at, current_millis())
        placeholders = ", ".join("?" for _ in normalized_ids)
        with self._connect() as connection:
            cursor = connection.execute(
                f"UPDATE viewer_memories SET recall_count = recall_count + 1, last_recalled_at = ? WHERE memory_id IN ({placeholders})",
                (recalled_at, *normalized_ids),
            )
        return cursor.rowcount

    def save_viewer_note(self, room_id, viewer_id, content, author="主播", is_pinned=False, note_id=""):
        note_id = safe_text(note_id) or str(uuid.uuid4())
        timestamp = current_millis()
        with self._connect() as connection:
            existing = connection.execute("SELECT created_at FROM viewer_notes WHERE note_id = ?", (note_id,)).fetchone()
            created_at = existing["created_at"] if existing else timestamp
            connection.execute(
                """
                INSERT OR REPLACE INTO viewer_notes (
                    note_id, room_id, viewer_id, author, content, is_pinned, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (note_id, room_id, viewer_id, author or "主播", content, 1 if is_pinned else 0, created_at, timestamp),
            )
        return self.get_viewer_note(note_id)

    def delete_viewer_note(self, note_id):
        with self._connect() as connection:
            cursor = connection.execute("DELETE FROM viewer_notes WHERE note_id = ?", (note_id,))
        return cursor.rowcount > 0

    def get_setting(self, key):
        key = safe_text(key)
        if not key:
            return ""
        with self._connect() as connection:
            row = connection.execute(
                "SELECT setting_value FROM app_settings WHERE setting_key = ?",
                (key,),
            ).fetchone()
        return row["setting_value"] if row else ""

    def set_setting(self, key, value):
        key = safe_text(key)
        if not key:
            return False
        with self._connect() as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO app_settings (setting_key, setting_value, updated_at)
                VALUES (?, ?, ?)
                """,
                (key, str(value or ""), current_millis()),
            )
        return True

    def delete_setting(self, key):
        key = safe_text(key)
        if not key:
            return False
        with self._connect() as connection:
            cursor = connection.execute("DELETE FROM app_settings WHERE setting_key = ?", (key,))
        return cursor.rowcount > 0

    def get_llm_settings(self, default_model, default_system_prompt):
        model_override = self.get_setting("llm_model_override")
        prompt_override = self.get_setting("system_prompt_override")
        model = model_override or safe_text(default_model)
        system_prompt = prompt_override if safe_text(prompt_override) else str(default_system_prompt or "")
        return {
            "model": model,
            "system_prompt": system_prompt,
            "default_model": safe_text(default_model),
            "default_system_prompt": str(default_system_prompt or ""),
        }

    def save_llm_settings(self, model, system_prompt):
        normalized_model = safe_text(model)
        if not normalized_model:
            raise ValueError("model is required")
        self.set_setting("llm_model_override", normalized_model)
        normalized_prompt = str(system_prompt or "")
        if normalized_prompt.strip():
            self.set_setting("system_prompt_override", normalized_prompt)
        else:
            self.delete_setting("system_prompt_override")
        return self.get_llm_settings(normalized_model, normalized_prompt)

    def list_live_sessions(self, room_id="", status="", limit=20):
        conditions = []
        values = []
        room_id = safe_text(room_id)
        status = safe_text(status)
        limit = max(1, min(int(limit), 200))
        if room_id:
            conditions.append("room_id = ?")
            values.append(room_id)
        if status:
            conditions.append("status = ?")
            values.append(status)
        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        with self._connect() as connection:
            rows = connection.execute(
                f"""
                SELECT session_id, room_id, source_room_id, livename, status, started_at, last_event_at, ended_at,
                       event_count, comment_count, gift_event_count, join_count
                FROM live_sessions {where_clause}
                ORDER BY last_event_at DESC LIMIT ?
                """,
                (*values, limit),
            ).fetchall()
        return [dict(row) for row in rows]

    def get_active_session(self, room_id):
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT session_id, room_id, source_room_id, livename, status, started_at, last_event_at, ended_at,
                       event_count, comment_count, gift_event_count, join_count
                FROM live_sessions WHERE room_id = ? AND status = 'active' ORDER BY started_at DESC LIMIT 1
                """,
                (room_id,),
            ).fetchone()
        return dict(row) if row else {}

    def close_active_session(self, room_id, ended_at=None):
        room_id = safe_text(room_id)
        if not room_id:
            return False
        ended_at = safe_int(ended_at, current_millis())
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE live_sessions
                SET status = 'ended',
                    ended_at = CASE WHEN ended_at IS NOT NULL AND ended_at >= ? THEN ended_at ELSE ? END,
                    last_event_at = CASE WHEN last_event_at >= ? THEN last_event_at ELSE ? END
                WHERE room_id = ? AND status = 'active'
                """,
                (ended_at, ended_at, ended_at, ended_at, room_id),
            )
        return cursor.rowcount > 0

    def get_user_profile(self, room_id, actor_or_nickname):
        if isinstance(actor_or_nickname, Actor):
            viewer_id = actor_or_nickname.viewer_id
            nickname = safe_text(actor_or_nickname.nickname)
        else:
            nickname = safe_text(actor_or_nickname)
            viewer_id = ""
        with self._connect() as connection:
            row = self._find_viewer_profile(connection, room_id, viewer_id=viewer_id, nickname=nickname)
        if not row:
            return {}
        profile = dict(row)
        resolved_viewer_id = safe_text(profile.get("viewer_id"))
        profile["recent_comments"] = self.viewer_event_history(room_id, resolved_viewer_id, event_type="comment", limit=5)
        profile["gift_history"] = self.viewer_gift_history(room_id, resolved_viewer_id, limit=10)
        profile["recent_sessions"] = self.viewer_session_history(room_id, resolved_viewer_id, limit=3)
        profile["memories"] = self.list_viewer_memories(room_id, resolved_viewer_id, limit=10)
        return profile

    def get_viewer_detail(self, room_id, viewer_id="", nickname=""):
        with self._connect() as connection:
            row = self._find_viewer_profile(connection, room_id, viewer_id=safe_text(viewer_id), nickname=safe_text(nickname))
        if not row:
            return {}
        profile = dict(row)
        resolved_viewer_id = safe_text(profile.get("viewer_id"))
        profile["recent_comments"] = self.viewer_event_history(room_id, resolved_viewer_id, event_type="comment", limit=20)
        profile["recent_joins"] = self.viewer_event_history(room_id, resolved_viewer_id, event_type="member", limit=20)
        profile["recent_gift_events"] = self.viewer_event_history(room_id, resolved_viewer_id, event_type="gift", limit=20)
        profile["gift_history"] = self.viewer_gift_history(room_id, resolved_viewer_id, limit=20)
        profile["recent_sessions"] = self.viewer_session_history(room_id, resolved_viewer_id, limit=10)
        profile["memories"] = self.list_viewer_memories(room_id, resolved_viewer_id, limit=20)
        profile["notes"] = self.list_viewer_notes(room_id, resolved_viewer_id, limit=20)
        return profile
