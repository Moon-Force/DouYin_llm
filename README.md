# Live Prompter Stack

这个仓库现在包含三层：

1. `tool/` 里的 `douyinLive-windows-amd64.exe`
   负责连接抖音直播间并在本地暴露 WebSocket 服务。
2. 根目录 `client.py`
   负责从本地 WebSocket 读取直播消息、做标准化，并转发到业务后端。
3. `backend/` + `frontend/`
   负责实时提词、会话记忆、长期存储和极简提词器界面。

## 目录说明

| 路径 | 说明 |
|------|------|
| `config.py` | 采集层配置，包含直播间号、本地 ws 地址、后端转发地址 |
| `client.py` | 采集客户端，读取抖音消息并转发到 FastAPI |
| `debug_client.py` | 调试客户端，打印原始 JSON 并写入日志 |
| `backend/app.py` | FastAPI 后端入口，提供 REST、SSE、WebSocket |
| `backend/memory/` | 短期记忆、长期存储、向量检索 |
| `backend/services/agent.py` | 轻量级直播提词 Agent |
| `frontend/` | Vue3 + Tailwind 极简提词器 |
| `tool/` | 预编译 douyinLive 服务端 |

## 架构

```text
douyinLive.exe
  -> ws://127.0.0.1:1088/ws/{room_id}
  -> client.py 标准化消息
  -> POST /api/events
  -> FastAPI 写 Redis/SQLite/Chroma
  -> 生成建议
  -> SSE/WebSocket 推给 Vue3 提词器
```

## 消息格式

实际消息类型字段在 `common.method`，不是顶层 `method`。

采集端会标准化为统一事件：

```json
{
  "event_id": "7624505524721748020",
  "room_id": "32137571630",
  "platform": "douyin",
  "event_type": "comment",
  "method": "WebcastChatMessage",
  "livename": "直播间名称",
  "ts": 1775218578225,
  "user": {
    "id": "",
    "nickname": "观众昵称"
  },
  "content": "评论内容",
  "metadata": {},
  "raw": {}
}
```

## 后端能力

- FastAPI 实时事件入口
- SSE `GET /api/events/stream`
- WebSocket `GET /ws/live`
- 短期记忆：Redis 优先，缺失时退化到进程内内存
- 长期记忆：SQLite
- 向量检索：Chroma 优先，缺失时退化到轻量文本相似度
- 轻量 Agent：
  - 默认 `heuristic`
  - 也支持 OpenAI 兼容接口模式
  - 现在内置 `qwen` 模式，默认指向在线官方百炼兼容接口

## 前端风格

- Vue 3 + Tailwind CSS
- 极简提词器布局
- 主区只突出一条建议
- 侧栏展示最近弹幕
- 使用 SSE 接收实时推送

## 运行方式

### 1. 启动抖音消息服务

```bash
tool\douyinLive-windows-amd64.exe
```

### 2. 安装 Python 依赖

```bash
pip install -r requirements.txt
```

### 3. 启动后端

```bash
uvicorn backend.app:app --reload
```

### 4. 启动采集客户端

```bash
python client.py
```

### 5. 启动前端

```bash
cd frontend
npm install
npm run dev
```

### 6. 调试原始消息

```bash
python debug_client.py
```

## 配置

编辑 `config.py`：

```python
ROOM_ID = "你的直播间号"
HOST = "127.0.0.1"
PORT = 1088
LOG_DIR = "logs"
FORWARD_EVENTS = True
BACKEND_EVENT_URL = "http://127.0.0.1:8000/api/events"
FORWARD_TIMEOUT = 1.5
```

`tool/config.yaml` 里的 `cookie.douyin` 只保留示例空值；如果你本地需要真实 Cookie，直接本地填写，但不要提交到仓库。

可选环境变量：

```bash
set LLM_MODE=openai
set LLM_BASE_URL=https://api.openai.com/v1
set LLM_MODEL=gpt-4.1-mini
set LLM_API_KEY=your_api_key
set REDIS_URL=redis://127.0.0.1:6379/0
```

如果你要接在线 Qwen，推荐直接用内置 `qwen` 模式：

```bash
set LLM_MODE=qwen
set DASHSCOPE_API_KEY=your_dashscope_api_key
set LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
set LLM_MODEL=qwen-plus-latest
set LLM_TIMEOUT_SECONDS=6
```

如果你想显式使用统一变量名，也可以这样写：

```bash
set LLM_API_KEY=your_dashscope_api_key
```

如果接其他在线 OpenAI 兼容网关，比如 GLM：

```bash
set LLM_MODE=openai
set LLM_BASE_URL=http://127.0.0.1:8001/v1
set LLM_MODEL=glm-4-flash
```

## 当前实现边界

- 这版已经能跑通采集 -> 后端 -> 前端展示的主链路。
- Agent 当前以低延迟启发式策略为默认模式。
- Redis 和 Chroma 是可选增强，不安装时会自动退化。
- 当前还没有做多房间隔离 UI、权限体系和完整运营后台。
