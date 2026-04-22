# Raw WS Capture Design

**Goal**

Add a standalone Python debugging script that connects directly to the local `douyinLive` WebSocket service, prints connection/runtime status, and writes each raw JSON message to a dedicated subdirectory under `tool/raw_capture/`.

**Scope**

- Command-line `room_id` input
- Default host `127.0.0.1`, default port `1088`
- Dedicated output directory: `tool/raw_capture/collector_debug/`
- Output format: JSON Lines (`.jsonl`), one raw message per line
- Ignore text `pong` frames

**Files**

- Add: `tool/raw_capture/raw_ws_capture.py`
- Add: `tests/test_raw_ws_capture.py`
- Add: `tool/raw_capture/collector_debug/.gitkeep`
- Modify: `.gitignore`

**Behavior**

The script will connect to `ws://<host>:<port>/ws/<room_id>`, create an output file named with `room_id` plus a timestamp, and append each parsed JSON payload as a compact UTF-8 JSON line. Runtime output will stay simple: connect, file path, received message notice, close, and error.

**Error Handling**

- Invalid JSON payloads are reported to stderr and skipped
- `pong` text frames are ignored
- Output directory is created automatically
- A periodic text `ping` is sent while the socket remains open

**Testing**

Tests will cover deterministic output path naming and raw message recording behavior, including `pong` suppression and JSONL writing.
