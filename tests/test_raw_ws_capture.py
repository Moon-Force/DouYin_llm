import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from tool.raw_capture.raw_ws_capture import (
    build_output_path,
    build_ws_url,
    parse_args,
    record_raw_message,
)


class RawWsCaptureTests(unittest.TestCase):
    def test_parse_args_uses_default_room_id_when_not_provided(self):
        with patch("sys.argv", ["raw_ws_capture.py"]):
            args = parse_args()

        self.assertEqual(args.room_id, "334732862395")

    def test_build_ws_url_uses_host_port_and_room_id(self):
        self.assertEqual(
            build_ws_url("334732862395", host="127.0.0.1", port=1088),
            "ws://127.0.0.1:1088/ws/334732862395",
        )

    def test_build_output_path_uses_room_id_and_timestamp(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = build_output_path(
                "516466932480",
                output_dir=Path(tmpdir),
                now=datetime(2026, 4, 23, 3, 15, 0),
            )

        self.assertEqual(path.name, "raw_ws_516466932480_20260423_031500.jsonl")

    def test_record_raw_message_writes_one_json_line_and_ignores_pong(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "capture.jsonl"
            wrote = record_raw_message(
                '{"method":"WebcastChatMessage","content":"hello"}',
                output_path,
            )
            ignored = record_raw_message("pong", output_path)
            lines = output_path.read_text(encoding="utf-8").splitlines()

        self.assertTrue(wrote)
        self.assertFalse(ignored)
        self.assertEqual(len(lines), 1)
        self.assertEqual(json.loads(lines[0])["content"], "hello")


if __name__ == "__main__":
    unittest.main()
