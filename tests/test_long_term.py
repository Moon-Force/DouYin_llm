import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from backend.memory.long_term import LongTermStore
from backend.schemas.live import LiveEvent


class LongTermStoreConnectTests(unittest.TestCase):
    def test_connect_switches_sqlite_to_truncate_journal_mode(self):
        store = LongTermStore.__new__(LongTermStore)
        store.database_path = "data/test.db"

        connection = MagicMock()

        with patch("backend.memory.long_term.sqlite3.connect", return_value=connection) as connect_mock:
            result = store._connect()

        connect_mock.assert_called_once()
        self.assertEqual(connect_mock.call_args.args[0], "data/test.db")
        self.assertEqual(
            connect_mock.call_args.kwargs["factory"].__name__,
            "ClosingConnection",
        )
        connection.execute.assert_any_call("PRAGMA journal_mode=TRUNCATE")
        self.assertIs(result, connection)
        self.assertEqual(connection.row_factory, unittest.mock.ANY)

    def test_setup_adds_title_column_to_existing_live_sessions_table(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            database_path = os.path.join(tmpdir, "legacy.db")
            legacy_store = LongTermStore.__new__(LongTermStore)
            legacy_store.database_path = database_path
            with legacy_store._connect() as connection:
                connection.execute(
                    """
                    CREATE TABLE live_sessions (
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
                    )
                    """
                )

            store = LongTermStore(database_path)
            with store._connect() as connection:
                columns = [row[1] for row in connection.execute("PRAGMA table_info(live_sessions)").fetchall()]

        self.assertIn("title", columns)


class LiveSessionStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_path = os.path.join(self.temp_dir.name, "sessions.db")
        self.store = LongTermStore(self.database_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_persist_event_saves_and_updates_live_session_title_and_livename(self):
        first_event = LiveEvent(
            event_id="evt-1",
            room_id="room-1",
            source_room_id="source-room-1",
            platform="douyin",
            event_type="comment",
            method="WebcastChatMessage",
            livename="第一直播间名",
            ts=1000,
            user={"id": "user-1", "nickname": "Alice"},
            content="hello",
            metadata={"title": "第一直播标题", "livename": "第一直播间名"},
            raw={},
        )
        second_event = LiveEvent(
            event_id="evt-2",
            room_id="room-1",
            source_room_id="source-room-1",
            platform="douyin",
            event_type="gift",
            method="WebcastGiftMessage",
            livename="第二直播间名",
            ts=2000,
            user={"id": "user-1", "nickname": "Alice"},
            content="gift",
            metadata={"title": "第二直播标题", "livename": "第二直播间名"},
            raw={},
        )

        self.store.persist_event(first_event)
        self.store.persist_event(second_event)

        current = self.store.get_active_session("room-1")
        listed = self.store.list_live_sessions("room-1", "active", limit=10)

        self.assertEqual(current["livename"], "第二直播间名")
        self.assertEqual(current["title"], "第二直播标题")
        self.assertEqual(listed[0]["title"], "第二直播标题")


class ViewerMemoryCorrectionStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_path = os.path.join(self.temp_dir.name, "memory.db")
        self.store = LongTermStore(self.database_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_save_manual_memory_persists_extended_fields_and_created_log(self):
        memory = self.store.save_viewer_memory(
            room_id="room-1",
            viewer_id="viewer-1",
            memory_text="喜欢豚骨拉面",
            source_event_id="",
            memory_type="preference",
            confidence=0.96,
            source_kind="manual",
            status="active",
            is_pinned=True,
            correction_reason="主播手动补充",
            corrected_by="主播",
            operation="created",
        )

        self.assertEqual(memory.source_kind, "manual")
        self.assertEqual(memory.status, "active")
        self.assertTrue(memory.is_pinned)
        self.assertEqual(memory.correction_reason, "主播手动补充")
        self.assertEqual(memory.corrected_by, "主播")
        self.assertEqual(memory.last_operation, "created")

        listed = self.store.list_viewer_memories("room-1", "viewer-1", limit=10)
        self.assertEqual(len(listed), 1)
        self.assertEqual(listed[0]["memory_id"], memory.memory_id)

        logs = self.store.list_viewer_memory_logs(memory.memory_id, limit=10)
        self.assertEqual([log["operation"] for log in logs], ["created"])
        self.assertEqual(logs[0]["operator"], "主播")
        self.assertEqual(logs[0]["new_memory_text"], "喜欢豚骨拉面")

    def test_update_invalidate_reactivate_and_delete_change_state_and_logs(self):
        memory = self.store.save_viewer_memory(
            room_id="room-1",
            viewer_id="viewer-1",
            memory_text="喜欢拉面",
            source_event_id="evt-1",
            memory_type="preference",
            confidence=0.88,
            source_kind="auto",
            status="active",
            is_pinned=False,
            correction_reason="",
            corrected_by="system",
            operation="created",
        )

        edited = self.store.update_viewer_memory(
            memory_id=memory.memory_id,
            memory_text="喜欢豚骨拉面",
            memory_type="preference",
            is_pinned=True,
            correction_reason="自动抽取过于笼统",
            corrected_by="主播",
        )
        self.assertEqual(edited.memory_text, "喜欢豚骨拉面")
        self.assertTrue(edited.is_pinned)
        self.assertEqual(edited.last_operation, "edited")

        invalidated = self.store.invalidate_viewer_memory(
            memory.memory_id,
            reason="信息过期",
            corrected_by="主播",
        )
        self.assertEqual(invalidated.status, "invalid")
        self.assertEqual(invalidated.last_operation, "invalidated")

        reactivated = self.store.reactivate_viewer_memory(
            memory.memory_id,
            reason="重新确认仍然有效",
            corrected_by="主播",
        )
        self.assertEqual(reactivated.status, "active")
        self.assertEqual(reactivated.last_operation, "reactivated")

        deleted = self.store.delete_viewer_memory(
            memory.memory_id,
            reason="彻底删除错误记忆",
            corrected_by="主播",
        )
        self.assertEqual(deleted.status, "deleted")
        self.assertEqual(deleted.last_operation, "deleted")

        visible = self.store.list_viewer_memories("room-1", "viewer-1", limit=10)
        self.assertEqual(visible, [])

        logs = self.store.list_viewer_memory_logs(memory.memory_id, limit=10)
        self.assertEqual(
            [log["operation"] for log in logs],
            ["deleted", "reactivated", "invalidated", "edited", "created"],
        )

    def test_save_viewer_memory_persists_merge_metadata_defaults(self):
        memory = self.store.save_viewer_memory(
            room_id="room-1",
            viewer_id="viewer-1",
            memory_text="租房住在公司附近",
            source_event_id="evt-1",
            memory_type="context",
            confidence=0.78,
            source_kind="auto",
            status="active",
            raw_memory_text="我租房住在公司附近，这样通勤方便点",
            evidence_count=1,
            first_confirmed_at=111,
            last_confirmed_at=111,
            superseded_by="",
            merge_parent_id="",
        )

        self.assertEqual(memory.memory_text_raw_latest, "我租房住在公司附近，这样通勤方便点")
        self.assertEqual(memory.evidence_count, 1)
        self.assertEqual(memory.first_confirmed_at, 111)
        self.assertEqual(memory.last_confirmed_at, 111)
        self.assertEqual(memory.superseded_by, "")
        self.assertEqual(memory.merge_parent_id, "")

        fetched = self.store.get_viewer_memory(memory.memory_id)
        self.assertEqual(fetched.memory_text_raw_latest, "我租房住在公司附近，这样通勤方便点")
        self.assertEqual(fetched.evidence_count, 1)
        self.assertEqual(fetched.first_confirmed_at, 111)
        self.assertEqual(fetched.last_confirmed_at, 111)
        self.assertEqual(fetched.superseded_by, "")
        self.assertEqual(fetched.merge_parent_id, "")

    def test_save_viewer_memory_persists_recall_text(self):
        memory = self.store.save_viewer_memory(
            room_id="room-1",
            viewer_id="viewer-1",
            memory_text="likes ramen",
            memory_recall_text="viewer likes ramen, noodles, tonkotsu ramen, food preference",
            source_event_id="evt-1",
            memory_type="preference",
            confidence=0.78,
        )

        self.assertEqual(
            memory.memory_recall_text,
            "viewer likes ramen, noodles, tonkotsu ramen, food preference",
        )

        fetched = self.store.get_viewer_memory(memory.memory_id)
        self.assertEqual(
            fetched.memory_recall_text,
            "viewer likes ramen, noodles, tonkotsu ramen, food preference",
        )

        listed = self.store.list_viewer_memories("room-1", "viewer-1", limit=10)
        self.assertEqual(
            listed[0]["memory_recall_text"],
            "viewer likes ramen, noodles, tonkotsu ramen, food preference",
        )

    def test_viewer_memory_recall_text_defaults_to_memory_text(self):
        memory = self.store.save_viewer_memory(
            room_id="room-1",
            viewer_id="viewer-1",
            memory_text="likes ramen",
            source_event_id="evt-1",
            memory_type="preference",
            confidence=0.78,
        )

        self.assertEqual(memory.memory_recall_text, "likes ramen")

        with self.store._connect() as connection:
            connection.execute("UPDATE viewer_memories SET memory_recall_text = '' WHERE memory_id = ?", (memory.memory_id,))

        fetched = self.store.get_viewer_memory(memory.memory_id)
        self.assertEqual(fetched.memory_recall_text, "likes ramen")

    def test_existing_viewer_memory_rows_get_merge_metadata_defaults(self):
        memory = self.store.save_viewer_memory(
            room_id="room-1",
            viewer_id="viewer-1",
            memory_text="喜欢拉面",
            source_event_id="evt-1",
            memory_type="preference",
            confidence=0.88,
        )

        with self.store._connect() as connection:
            connection.execute("UPDATE viewer_memories SET memory_text_raw_latest = '' WHERE memory_id = ?", (memory.memory_id,))
            connection.execute("UPDATE viewer_memories SET evidence_count = 0 WHERE memory_id = ?", (memory.memory_id,))
            connection.execute("UPDATE viewer_memories SET first_confirmed_at = 0 WHERE memory_id = ?", (memory.memory_id,))
            connection.execute("UPDATE viewer_memories SET last_confirmed_at = 0 WHERE memory_id = ?", (memory.memory_id,))
            connection.execute("UPDATE viewer_memories SET superseded_by = '' WHERE memory_id = ?", (memory.memory_id,))
            connection.execute("UPDATE viewer_memories SET merge_parent_id = '' WHERE memory_id = ?", (memory.memory_id,))

        fetched = self.store.get_viewer_memory(memory.memory_id)
        self.assertEqual(fetched.memory_text_raw_latest, "")
        self.assertEqual(fetched.evidence_count, 0)
        self.assertEqual(fetched.first_confirmed_at, 0)
        self.assertEqual(fetched.last_confirmed_at, 0)
        self.assertEqual(fetched.superseded_by, "")
        self.assertEqual(fetched.merge_parent_id, "")

    def test_merge_viewer_memory_evidence_updates_evidence_and_raw_text(self):
        memory = self.store.save_viewer_memory(
            room_id="room-1",
            viewer_id="viewer-1",
            memory_text="喜欢拉面",
            source_event_id="evt-1",
            memory_type="preference",
            confidence=0.74,
            raw_memory_text="我喜欢拉面",
            evidence_count=1,
            first_confirmed_at=100,
            last_confirmed_at=100,
        )

        merged = self.store.merge_viewer_memory_evidence(
            memory.memory_id,
            raw_memory_text="我还是很喜欢拉面",
            confidence=0.86,
            source_event_id="evt-2",
        )

        self.assertEqual(merged.memory_id, memory.memory_id)
        self.assertEqual(merged.memory_text, "喜欢拉面")
        self.assertEqual(merged.memory_text_raw_latest, "我还是很喜欢拉面")
        self.assertEqual(merged.evidence_count, 2)
        self.assertEqual(merged.first_confirmed_at, 100)
        self.assertGreaterEqual(merged.last_confirmed_at, 100)
        self.assertEqual(merged.last_operation, "merged")
        self.assertGreater(merged.evidence_score, 0.0)

    def test_upgrade_viewer_memory_replaces_text_and_refreshes_metadata(self):
        memory = self.store.save_viewer_memory(
            room_id="room-1",
            viewer_id="viewer-1",
            memory_text="喜欢拉面",
            source_event_id="evt-1",
            memory_type="preference",
            confidence=0.74,
            raw_memory_text="我喜欢拉面",
            evidence_count=1,
            first_confirmed_at=100,
            last_confirmed_at=100,
            clarity_score=0.2,
        )

        upgraded = self.store.upgrade_viewer_memory(
            memory.memory_id,
            memory_text="喜欢豚骨拉面",
            raw_memory_text="我超爱豚骨拉面",
            confidence=0.86,
            source_event_id="evt-2",
        )

        self.assertEqual(upgraded.memory_id, memory.memory_id)
        self.assertEqual(upgraded.memory_text, "喜欢豚骨拉面")
        self.assertEqual(upgraded.memory_text_raw_latest, "我超爱豚骨拉面")
        self.assertEqual(upgraded.evidence_count, 2)
        self.assertEqual(upgraded.first_confirmed_at, 100)
        self.assertGreaterEqual(upgraded.last_confirmed_at, 100)
        self.assertEqual(upgraded.last_operation, "upgraded")
        self.assertGreater(upgraded.confidence, 0.74)
        self.assertGreater(upgraded.clarity_score, 0.2)

    def test_supersede_viewer_memory_marks_old_invalid_and_links_new_id(self):
        old_memory = self.store.save_viewer_memory(
            room_id="room-1",
            viewer_id="viewer-1",
            memory_text="喜欢吃辣",
            source_event_id="evt-1",
            memory_type="preference",
            confidence=0.74,
            raw_memory_text="我喜欢吃辣",
        )

        old, new = self.store.supersede_viewer_memory(
            old_memory.memory_id,
            room_id="room-1",
            viewer_id="viewer-1",
            memory_text="不太能吃辣",
            raw_memory_text="我平时不太能吃辣",
            memory_type="preference",
            confidence=0.86,
            source_event_id="evt-2",
        )

        self.assertEqual(old.memory_id, old_memory.memory_id)
        self.assertEqual(old.status, "invalid")
        self.assertEqual(old.last_operation, "superseded")
        self.assertEqual(old.superseded_by, new.memory_id)
        self.assertEqual(new.memory_text, "不太能吃辣")
        self.assertEqual(new.memory_text_raw_latest, "我平时不太能吃辣")
        self.assertEqual(new.evidence_count, 1)
        self.assertEqual(new.status, "active")

    def test_save_viewer_memory_persists_confidence_subscores(self):
        memory = self.store.save_viewer_memory(
            room_id="room-1",
            viewer_id="viewer-1",
            memory_text="不太能吃辣",
            source_event_id="evt-1",
            memory_type="preference",
            confidence=0.82,
            stability_score=0.95,
            interaction_value_score=0.9,
            clarity_score=0.8,
            evidence_score=0.4,
        )

        self.assertEqual(memory.stability_score, 0.95)
        self.assertEqual(memory.interaction_value_score, 0.9)
        self.assertEqual(memory.clarity_score, 0.8)
        self.assertEqual(memory.evidence_score, 0.4)

        fetched = self.store.get_viewer_memory(memory.memory_id)
        self.assertEqual(fetched.stability_score, 0.95)
        self.assertEqual(fetched.interaction_value_score, 0.9)
        self.assertEqual(fetched.clarity_score, 0.8)
        self.assertEqual(fetched.evidence_score, 0.4)

    def test_existing_rows_default_confidence_subscores_to_zero(self):
        memory = self.store.save_viewer_memory(
            room_id="room-1",
            viewer_id="viewer-1",
            memory_text="喜欢拉面",
            source_event_id="evt-1",
            memory_type="preference",
            confidence=0.88,
        )

        with self.store._connect() as connection:
            connection.execute("UPDATE viewer_memories SET stability_score = 0 WHERE memory_id = ?", (memory.memory_id,))
            connection.execute(
                "UPDATE viewer_memories SET interaction_value_score = 0 WHERE memory_id = ?",
                (memory.memory_id,),
            )
            connection.execute("UPDATE viewer_memories SET clarity_score = 0 WHERE memory_id = ?", (memory.memory_id,))
            connection.execute("UPDATE viewer_memories SET evidence_score = 0 WHERE memory_id = ?", (memory.memory_id,))

        fetched = self.store.get_viewer_memory(memory.memory_id)
        self.assertEqual(fetched.stability_score, 0.0)
        self.assertEqual(fetched.interaction_value_score, 0.0)
        self.assertEqual(fetched.clarity_score, 0.0)
        self.assertEqual(fetched.evidence_score, 0.0)

    def test_save_viewer_memory_persists_polarity_and_temporal_scope(self):
        memory = self.store.save_viewer_memory(
            room_id="room-1",
            viewer_id="viewer-1",
            memory_text="不太能吃辣",
            source_event_id="evt-1",
            memory_type="preference",
            confidence=0.82,
            polarity="negative",
            temporal_scope="long_term",
        )

        self.assertEqual(memory.polarity, "negative")
        self.assertEqual(memory.temporal_scope, "long_term")

        fetched = self.store.get_viewer_memory(memory.memory_id)
        self.assertEqual(fetched.polarity, "negative")
        self.assertEqual(fetched.temporal_scope, "long_term")

    def test_existing_rows_default_polarity_and_temporal_scope(self):
        memory = self.store.save_viewer_memory(
            room_id="room-1",
            viewer_id="viewer-1",
            memory_text="喜欢拉面",
            source_event_id="evt-1",
            memory_type="preference",
            confidence=0.88,
        )

        with self.store._connect() as connection:
            connection.execute("UPDATE viewer_memories SET polarity = 'neutral' WHERE memory_id = ?", (memory.memory_id,))
            connection.execute("UPDATE viewer_memories SET temporal_scope = 'long_term' WHERE memory_id = ?", (memory.memory_id,))

        fetched = self.store.get_viewer_memory(memory.memory_id)
        self.assertEqual(fetched.polarity, "neutral")
        self.assertEqual(fetched.temporal_scope, "long_term")

    def test_save_viewer_memory_defaults_to_long_term_lifecycle(self):
        memory = self.store.save_viewer_memory(
            room_id="room-1",
            viewer_id="viewer-1",
            memory_text="租房住在公司附近",
            source_event_id="evt-1",
            memory_type="context",
            confidence=0.78,
        )

        self.assertEqual(memory.lifecycle_kind, "long_term")
        self.assertEqual(memory.expires_at, 0)

    def test_save_viewer_memory_persists_short_term_expiry(self):
        memory = self.store.save_viewer_memory(
            room_id="room-1",
            viewer_id="viewer-1",
            memory_text="这周都在上海出差",
            source_event_id="evt-1",
            memory_type="context",
            confidence=0.5,
            lifecycle_kind="short_term",
            expires_at=999999,
        )

        self.assertEqual(memory.lifecycle_kind, "short_term")
        self.assertEqual(memory.expires_at, 999999)

    def test_list_viewer_memories_excludes_expired_records(self):
        active = self.store.save_viewer_memory(
            room_id="room-1",
            viewer_id="viewer-1",
            memory_text="租房住在公司附近",
            source_event_id="evt-1",
            memory_type="context",
            confidence=0.78,
            lifecycle_kind="long_term",
            expires_at=0,
        )
        self.store.save_viewer_memory(
            room_id="room-1",
            viewer_id="viewer-1",
            memory_text="这周都在上海出差",
            source_event_id="evt-2",
            memory_type="context",
            confidence=0.5,
            lifecycle_kind="short_term",
            expires_at=1,
        )

        memories = self.store.list_viewer_memories("room-1", "viewer-1", limit=10, now_ms=1000)

        self.assertEqual([item["memory_id"] for item in memories], [active.memory_id])

    def test_list_all_viewer_memories_excludes_expired_records(self):
        active = self.store.save_viewer_memory(
            room_id="room-1",
            viewer_id="viewer-1",
            memory_text="租房住在公司附近",
            source_event_id="evt-1",
            memory_type="context",
            confidence=0.78,
            lifecycle_kind="long_term",
            expires_at=0,
        )
        self.store.save_viewer_memory(
            room_id="room-1",
            viewer_id="viewer-1",
            memory_text="这周都在上海出差",
            source_event_id="evt-2",
            memory_type="context",
            confidence=0.5,
            lifecycle_kind="short_term",
            expires_at=1,
        )

        memories = self.store.list_all_viewer_memories(limit=100, now_ms=1000)

        self.assertEqual([item.memory_id for item in memories], [active.memory_id])


if __name__ == "__main__":
    unittest.main()
