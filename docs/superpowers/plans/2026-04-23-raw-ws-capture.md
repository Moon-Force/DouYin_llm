# Raw WS Capture Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a Python utility that connects to the local `douyinLive` WebSocket service and writes raw JSON messages to `tool/raw_capture/collector_debug/` as JSONL logs.

**Architecture:** Keep the runtime script small and push deterministic parts into testable helper functions. The script owns CLI parsing and WebSocket wiring; helpers own URL building, output path naming, and raw-message persistence.

**Tech Stack:** Python, `websocket-client`, `unittest`, PowerShell

---

### Task 1: Add Failing Tests For Raw Capture Helpers

**Files:**
- Create: `tests/test_raw_ws_capture.py`
- Test: `tests/test_raw_ws_capture.py`

- [ ] **Step 1: Write the failing test**

```python
import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from tool.raw_capture.raw_ws_capture import build_output_path, record_raw_message


class RawWsCaptureTests(unittest.TestCase):
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
            wrote = record_raw_message('{"method":"WebcastChatMessage","content":"hello"}', output_path)
            ignored = record_raw_message("pong", output_path)
            lines = output_path.read_text(encoding="utf-8").splitlines()

        self.assertTrue(wrote)
        self.assertFalse(ignored)
        self.assertEqual(len(lines), 1)
        self.assertEqual(json.loads(lines[0])["content"], "hello")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_raw_ws_capture -v`
Expected: FAIL with `ModuleNotFoundError` or missing function import from `tool.raw_capture.raw_ws_capture`

- [ ] **Step 3: Write minimal implementation**

```python
from datetime import datetime
from pathlib import Path
import json


def build_output_path(room_id, output_dir=Path("tool") / "collector_debug", now=None):
    current = now or datetime.now()
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir / f"raw_ws_{room_id}_{current.strftime('%Y%m%d_%H%M%S')}.jsonl"


def record_raw_message(raw_message, output_path):
    if raw_message == "pong":
        return False
    payload = json.loads(raw_message)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n")
    return True
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m unittest tests.test_raw_ws_capture -v`
Expected: PASS

### Task 2: Implement CLI Script And Output Directory Rules

**Files:**
- Create: `tool/raw_capture/raw_ws_capture.py`
- Create: `tool/raw_capture/collector_debug/.gitkeep`
- Modify: `.gitignore`
- Test: `tests/test_raw_ws_capture.py`

- [ ] **Step 1: Extend the failing test coverage for URL building**

```python
from tool.raw_capture.raw_ws_capture import build_ws_url

    def test_build_ws_url_uses_host_port_and_room_id(self):
        self.assertEqual(
            build_ws_url("516466932480", host="127.0.0.1", port=1088),
            "ws://127.0.0.1:1088/ws/516466932480",
        )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_raw_ws_capture -v`
Expected: FAIL because `build_ws_url` does not exist yet

- [ ] **Step 3: Write minimal implementation**

```python
import argparse
import json
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

import websocket


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 1088
DEFAULT_OUTPUT_DIR = Path("tool") / "raw_capture" / "collector_debug"


def build_ws_url(room_id, host=DEFAULT_HOST, port=DEFAULT_PORT):
    return f"ws://{host}:{int(port)}/ws/{room_id}"


def parse_args():
    parser = argparse.ArgumentParser(description="Capture raw douyinLive websocket messages.")
    parser.add_argument("room_id", help="Target live room id")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--ping-interval", type=float, default=30.0)
    return parser.parse_args()


def main():
    args = parse_args()
    output_path = build_output_path(args.room_id, output_dir=Path(args.output_dir))
    url = build_ws_url(args.room_id, host=args.host, port=args.port)
    stop_event = threading.Event()

    def on_open(ws):
        print("已连接")
        print(f"日志文件: {output_path}")

    def on_message(ws, message):
        try:
            wrote = record_raw_message(message, output_path)
        except json.JSONDecodeError as exc:
            print(f"无效 JSON，已跳过: {exc}", file=sys.stderr)
            return
        if wrote:
            print("收到消息")

    def on_close(ws, status_code, close_msg):
        stop_event.set()
        print("连接关闭")

    def on_error(ws, error):
        print(f"WebSocket 错误: {error}", file=sys.stderr)

    ws = websocket.WebSocketApp(
        url,
        on_open=on_open,
        on_message=on_message,
        on_close=on_close,
        on_error=on_error,
    )

    def ping_loop():
        while not stop_event.is_set():
            time.sleep(args.ping_interval)
            if ws.sock and ws.sock.connected:
                try:
                    ws.send("ping")
                except Exception:
                    stop_event.set()
                    return

    threading.Thread(target=ping_loop, daemon=True).start()
    ws.run_forever()


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Add ignore rules and placeholder directory**

```gitignore
tool/raw_capture/collector_debug/*
!tool/raw_capture/collector_debug/.gitkeep
```

```text
tool/raw_capture/collector_debug/.gitkeep
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m unittest tests.test_raw_ws_capture -v`
Expected: PASS

### Task 3: Final Verification

**Files:**
- Modify: none
- Test: `tests/test_raw_ws_capture.py`

- [ ] **Step 1: Run the focused unit test suite**

Run: `python -m unittest tests.test_raw_ws_capture -v`
Expected: PASS

- [ ] **Step 2: Run a script-level help check**

Run: `python tool/raw_capture/raw_ws_capture.py --help`
Expected: exit code 0 and help text containing `room_id`, `--host`, `--port`, `--output-dir`

- [ ] **Step 3: Spot-check the output directory rule**

Run: `git check-ignore -v tool/raw_capture/collector_debug/example.jsonl`
Expected: output shows `.gitignore` rule for `tool/raw_capture/collector_debug/*`
