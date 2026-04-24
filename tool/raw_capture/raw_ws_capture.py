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
DEFAULT_ROOM_ID = "334732862395"
DEFAULT_OUTPUT_DIR = Path("tool") / "raw_capture" / "collector_debug"


def build_ws_url(room_id, host=DEFAULT_HOST, port=DEFAULT_PORT):
    return f"ws://{host}:{int(port)}/ws/{room_id}"


def build_output_path(room_id, output_dir=DEFAULT_OUTPUT_DIR, now=None):
    current = now or datetime.now()
    target_dir = Path(output_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    return target_dir / f"raw_ws_{room_id}_{current.strftime('%Y%m%d_%H%M%S')}.jsonl"


def record_raw_message(raw_message, output_path):
    if raw_message == "pong":
        return False

    payload = json.loads(raw_message)
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with output_file.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n")
    return True


def parse_args():
    parser = argparse.ArgumentParser(description="Capture raw douyinLive websocket messages.")
    parser.add_argument(
        "room_id",
        nargs="?",
        default=DEFAULT_ROOM_ID,
        help=f"Target live room id, default: {DEFAULT_ROOM_ID}",
    )
    parser.add_argument("--host", default=DEFAULT_HOST, help=f"WebSocket host, default: {DEFAULT_HOST}")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help=f"WebSocket port, default: {DEFAULT_PORT}")
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help=f"Directory for JSONL logs, default: {DEFAULT_OUTPUT_DIR}",
    )
    parser.add_argument(
        "--ping-interval",
        type=float,
        default=30.0,
        help="Text ping interval in seconds, default: 30",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    output_path = build_output_path(args.room_id, output_dir=Path(args.output_dir))
    ws_url = build_ws_url(args.room_id, host=args.host, port=args.port)
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

    def on_close(ws, close_status_code, close_msg):
        stop_event.set()
        print("连接关闭")

    def on_error(ws, error):
        print(f"WebSocket 错误: {error}", file=sys.stderr)

    ws = websocket.WebSocketApp(
        ws_url,
        on_open=on_open,
        on_message=on_message,
        on_close=on_close,
        on_error=on_error,
    )

    def ping_loop():
        while not stop_event.is_set():
            time.sleep(args.ping_interval)
            if stop_event.is_set():
                break
            if ws.sock and ws.sock.connected:
                try:
                    ws.send("ping")
                except Exception as exc:
                    print(f"发送 ping 失败: {exc}", file=sys.stderr)
                    stop_event.set()
                    break

    threading.Thread(target=ping_loop, name="raw-ws-capture-ping", daemon=True).start()
    print(f"连接地址: {ws_url}")
    ws.run_forever()


if __name__ == "__main__":
    main()
