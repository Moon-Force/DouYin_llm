import websocket
import json
import threading
import time

try:
    from config import ROOM_ID, HOST, PORT
except ImportError:
    ROOM_ID = "516466932480"
    HOST = "127.0.0.1"
    PORT = 1088


class DouyinLiveClient:
    def __init__(self, room_id, host="127.0.0.1", port=1088):
        self.room_id = room_id
        self.host = host
        self.port = port
        self.ws = None
        self.ping_thread = None
        self.running = False

    def on_message(self, ws, message):
        try:
            data = json.loads(message)
            self.handle_message(data)
        except json.JSONDecodeError:
            if message == "pong":
                print("收到 pong 响应")
            else:
                print(f"收到未知消息: {message}")

    def on_error(self, ws, error):
        print(f"WebSocket 错误: {error}")

    def on_close(self, ws, close_status_code, close_msg):
        print(f"连接关闭, 状态码: {close_status_code}, 消息: {close_msg}")
        self.running = False

    def on_open(self, ws):
        print("已连接到直播间")
        self.running = True
        self.start_ping()

    def handle_message(self, data):
        method = data.get("common", {}).get("method")
        livename = data.get("livename", "未知直播间")

        if method == "WebcastChatMessage":
            nickname = data.get("user", {}).get("nickname", "未知用户")
            content = data.get("content", "")
            print(f"[{livename}] 弹幕: {nickname} - {content}")
        elif method == "WebcastGiftMessage":
            nickname = data.get("user", {}).get("nickname", "未知用户")
            gift_name = data.get("gift", {}).get("name", "未知礼物")
            print(f"[{livename}] 礼物: {nickname} 赠送了 {gift_name}")
        elif method == "WebcastLikeMessage":
            nickname = data.get("user", {}).get("nickname", "未知用户")
            print(f"[{livename}] 点赞: {nickname} 点赞了直播间")
        elif method == "WebcastMemberMessage":
            nickname = data.get("user", {}).get("nickname", "未知用户")
            print(f"[{livename}] 进场: {nickname} 进入了直播间")
        elif method == "WebcastSocialMessage":
            nickname = data.get("user", {}).get("nickname", "未知用户")
            print(f"[{livename}] 关注: {nickname} 关注了主播")
        else:
            print(f"[{livename}] 其他消息: {method}")

    def start_ping(self):
        def ping():
            while self.running:
                try:
                    if self.ws and self.ws.sock and self.ws.sock.connected:
                        self.ws.send("ping")
                        print("发送 ping")
                    time.sleep(30)
                except Exception as e:
                    print(f"Ping 错误: {e}")
                    break

        self.ping_thread = threading.Thread(target=ping, daemon=True)
        self.ping_thread.start()

    def connect(self):
        url = f"ws://{self.host}:{self.port}/ws/{self.room_id}"
        print(f"正在连接: {url}")

        self.ws = websocket.WebSocketApp(
            url,
            on_open=self.on_open,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close,
        )

        self.ws.run_forever()

    def disconnect(self):
        self.running = False
        if self.ws:
            self.ws.close()


def main():
    import sys

    if len(sys.argv) > 1:
        room_id = sys.argv[1]
        host = sys.argv[2] if len(sys.argv) > 2 else HOST
        port = int(sys.argv[3]) if len(sys.argv) > 3 else PORT
    else:
        room_id = ROOM_ID
        host = HOST
        port = PORT

    client = DouyinLiveClient(room_id, host, port)

    try:
        client.connect()
    except KeyboardInterrupt:
        print("\n正在断开连接...")
        client.disconnect()


if __name__ == "__main__":
    main()
