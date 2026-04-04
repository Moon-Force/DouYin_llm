
# 配置文件

# 抖音直播间标识
ROOM_ID = "418446414087"

# WebSocket 服务主机
HOST = "127.0.0.1"

# WebSocket 服务端口
PORT = 1088

# 日志保存目录
LOG_DIR = "logs"

# 是否把采集到的消息转发到本地业务后端
FORWARD_EVENTS = True

# 业务后端的事件接收地址
BACKEND_EVENT_URL = "http://127.0.0.1:8010/api/events"

# 采集端转发超时时间，单位秒
FORWARD_TIMEOUT = 1.5
