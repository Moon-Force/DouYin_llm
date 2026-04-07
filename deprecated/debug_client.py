"""Deprecated raw websocket debug client.

This script is optional and not required for normal project startup.
Use it only when you need to inspect raw messages from `douyinLive`.
"""

import json
import os
import sys
from datetime import datetime

import websocket

os.environ["PYTHONIOENCODING"] = "utf-8"
os.environ["PYTHONUTF8"] = "1"

try:
    from config import ROOM_ID, HOST, PORT, LOG_DIR
except ImportError:
    ROOM_ID = "516466932480"
    HOST = "127.0.0.1"
    PORT = 1088
    LOG_DIR = "logs"


def configure_console_encoding():
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        if stream and hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass


def ensure_log_dir():
    if not os.path.exists(LOG_DIR):
        os.makedirs(LOG_DIR)


def get_log_filename():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return os.path.join(LOG_DIR, f"douyinlive_{timestamp}.log")


class Logger:
    def __init__(self, log_file):
        self.log_file = log_file
        self.terminal = sys.stdout

    def write(self, message):
        try:
            self.terminal.write(message)
        except (UnicodeEncodeError, UnicodeDecodeError):
            safe_msg = message.encode("utf-8", errors="replace").decode("utf-8")
            self.terminal.write(safe_msg)

        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(message)

    def flush(self):
        try:
            self.terminal.flush()
        except Exception:
            pass


def on_message(ws, message):
    print("\n" + "=" * 80)
    print("收到消息:")
    print("-" * 80)

    try:
        data = json.loads(message)
        print(json.dumps(data, ensure_ascii=False, indent=4))

        method = data.get("common", {}).get("method", "未知 method")
        print("-" * 80)
        print(f"消息类型: {method}")
        print(f"直播间: {data.get('livename', '未知')}")
    except json.JSONDecodeError:
        print(f"原始文本: {message}")

    print("=" * 80 + "\n")


def on_error(ws, error):
    print(f"错误: {error}")


def on_close(ws, close_status_code, close_msg):
    print(f"连接关闭: 状态码={close_status_code}, 消息={close_msg}")


def on_open(ws):
    print("已连接成功")
    print("等待接收消息...\n")


def main():
    configure_console_encoding()

    if len(sys.argv) > 1:
        room_id = sys.argv[1]
        host = sys.argv[2] if len(sys.argv) > 2 else HOST
        port = int(sys.argv[3]) if len(sys.argv) > 3 else PORT
    else:
        room_id = ROOM_ID
        host = HOST
        port = PORT

    ensure_log_dir()
    log_file = get_log_filename()
    print(f"日志将保存到: {log_file}\n")

    sys.stdout = Logger(log_file)
    configure_console_encoding()

    url = f"ws://{host}:{port}/ws/{room_id}"
    print(f"正在连接: {url}")

    ws = websocket.WebSocketApp(
        url,
        on_open=on_open,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close,
    )

    try:
        ws.run_forever()
    except KeyboardInterrupt:
        print("\n正在断开连接...")
        ws.close()


if __name__ == "__main__":
    main()
