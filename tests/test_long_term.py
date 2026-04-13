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


if __name__ == "__main__":
    unittest.main()
