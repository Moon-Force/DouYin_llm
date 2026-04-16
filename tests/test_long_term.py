import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from backend.memory.long_term import LongTermStore


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


if __name__ == "__main__":
    unittest.main()
