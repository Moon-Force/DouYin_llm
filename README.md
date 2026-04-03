# Python 客户端使用说明

这是 douyinLive 的 Python 客户端，用于连接并接收抖音直播弹幕消息。

## 文件说明

| 文件 | 说明 |
|------|------|
| `config.py` | 配置文件（房间号、端口等） |
| `client.py` | 实用版客户端（已经封装好） |
| `debug_client.py` | 调试版客户端（查看原始数据） |
| `requirements.txt` | Python 依赖库 |

## 安装依赖

```bash
pip install -r requirements.txt
```

或者直接安装：

```bash
pip install websocket-client
```

## 快速开始

### 1. 配置

编辑 `config.py`，修改直播间号：

```python
ROOM_ID = "你的直播间号"  # 改成你的直播间标识
HOST = "127.0.0.1"
PORT = 1088
LOG_DIR = "logs"
```

### 2. 确保服务端运行

先运行 `douyinLive-windows-amd64.exe` 启动服务端。

### 3. 运行客户端

#### 方式一：使用 config.py 配置（推荐）

```bash
python debug_client.py
```

或

```bash
python client.py
```

#### 方式二：命令行传参

```bash
python debug_client.py <直播间标识>
```

示例：

```bash
python debug_client.py 516466932480
```

## 两个客户端的区别

### debug_client.py（调试版）

- 显示完整的原始 JSON 数据
- 自动保存日志到 `logs/` 文件夹
- 适合开发调试，查看数据结构

### client.py（实用版）

- 已经封装好常见消息类型
- 简洁的输出格式
- 适合直接使用

## 支持的消息类型

| 消息类型 | 说明 |
|----------|------|
| WebcastChatMessage | 弹幕 |
| WebcastGiftMessage | 礼物 |
| WebcastLikeMessage | 点赞 |
| WebcastMemberMessage | 进场 |
| WebcastSocialMessage | 关注 |

## 自定义开发

### 修改 client.py

在 `handle_message` 方法中添加你的业务逻辑：

```python
def handle_message(self, data):
    method = data.get("method")
    
    if method == "WebcastChatMessage":
        # 在这里添加你的弹幕处理代码
        pass
```

### 查看原始数据

先用 `debug_client.py` 运行，查看完整的数据结构，了解都有哪些字段可用。

## 日志文件

运行 `debug_client.py` 时会自动在 `logs/` 目录下生成日志文件，文件名格式：

```
douyinlive_20260403_123456.log
```

所有打印的内容都会同时保存到日志文件中。
