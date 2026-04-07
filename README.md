# Live Prompter Stack

这是一个面向抖音直播场景的实时提词项目。当前主链路由三部分组成：

1. `tool/` 下的 `douyinLive-windows-amd64.exe`
   负责连接直播间，并在本地暴露 WebSocket 消息源。
2. `backend/` + `frontend/`
   负责事件采集、短期记忆、长期存储、向量检索、提词建议生成和前端展示。
3. `deprecated/`
   保留旧版脚本，仅用于历史参考和排障，不再是当前主流程的一部分。

## 当前能力

- 从本地 `douyinLive` WebSocket 持续接收直播事件
- 将原始消息标准化为统一 `LiveEvent`
- 保存最近会话数据、长期历史数据和相似事件索引
- 基于启发式规则或 OpenAI 兼容接口生成提词建议
- 通过 SSE / WebSocket 向前端实时推送事件、建议、统计和模型状态
- 前端支持房间切换、事件筛选、实时提词展示、主题切换

## 目录结构

| 路径 | 说明 |
| --- | --- |
| `backend/app.py` | FastAPI 入口，提供 REST、SSE、WebSocket 接口 |
| `backend/config.py` | `.env` 读取和运行配置解析 |
| `backend/services/collector.py` | 内置抖音消息采集器，连接本地 `douyinLive` WebSocket |
| `backend/services/agent.py` | 提词建议生成器，支持 `heuristic` 和 OpenAI 兼容模式 |
| `backend/memory/` | 短期记忆、SQLite 长期存储、向量检索 |
| `frontend/` | Vue 3 + Pinia + Tailwind 前端 |
| `tool/` | `douyinLive` 可执行文件及相关说明 |
| `deprecated/` | 已废弃的旧脚本和旧配置 |
| `data/` | 运行期生成的数据目录，包含 SQLite 和 Chroma 数据 |

## 架构概览

```text
douyinLive.exe
  -> ws://127.0.0.1:1088/ws/{room_id}
  -> backend/services/collector.py
  -> FastAPI
     -> SessionMemory
     -> SQLite LongTermStore
     -> Chroma VectorMemory
     -> LivePromptAgent
  -> SSE / WebSocket
  -> Vue 3 frontend
```

## 运行要求

- Windows 环境
- Python 3.10+
- Node.js 18+
- 可选：Redis
- 可选：Chroma 相关依赖

`requirements.txt` 当前包含：

- `websocket-client`
- `fastapi`
- `uvicorn`
- `redis`
- `chromadb`

## 快速开始

### 1. 启动抖音消息源

先单独启动本地消息源程序：

```powershell
.\tool\douyinLive-windows-amd64.exe
```

默认情况下，后端会连接：

```text
ws://127.0.0.1:1088/ws/{ROOM_ID}
```

### 2. 配置环境变量

复制示例配置：

```powershell
Copy-Item .env.example .env
```

然后至少填写：

- `ROOM_ID`
- `DASHSCOPE_API_KEY` 或 `LLM_API_KEY`

### 3. 安装后端依赖

```powershell
pip install -r requirements.txt
```

### 4. 启动后端

```powershell
python -m uvicorn backend.app:app --host 127.0.0.1 --port 8010 --reload
```

### 5. 启动前端

```powershell
cd frontend
npm install
npm run dev -- --host 127.0.0.1 --strictPort --port 5173
```

### 6. 使用项目自带脚本启动

如果使用仓库自带脚本：

```powershell
.\start_all.ps1
```

也可以分别启动：

```powershell
.\start_backend_qwen.ps1
.\start_frontend.ps1
```

前端默认地址：

```text
http://127.0.0.1:5173
```

后端默认地址：

```text
http://127.0.0.1:8010
```

## 配置说明

项目启动时会优先读取根目录 `.env`，不存在时再读取当前 shell 环境变量。

### 直播与采集

```env
ROOM_ID=32137571630
COLLECTOR_ENABLED=true
COLLECTOR_HOST=127.0.0.1
COLLECTOR_PORT=1088
COLLECTOR_PING_INTERVAL_SECONDS=30
COLLECTOR_RECONNECT_DELAY_SECONDS=3
```

### 后端服务

```env
APP_HOST=127.0.0.1
APP_PORT=8010
```

### 模型相关

默认示例使用 Qwen 在线模式：

```env
LLM_MODE=qwen
DASHSCOPE_API_KEY=your_dashscope_api_key
LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
LLM_MODEL=qwen-plus-latest
LLM_TIMEOUT_SECONDS=6
LLM_TEMPERATURE=0.4
```

说明：

- `LLM_MODE=heuristic` 时，不调用远程模型，只走本地规则
- `LLM_MODE=qwen` 时，默认回退到 DashScope OpenAI 兼容接口
- `LLM_MODE=openai` 时，可接任意 OpenAI 兼容网关
- `LLM_API_KEY` 为空时，会自动回退读取 `DASHSCOPE_API_KEY`

例如接自定义 OpenAI 兼容服务：

```env
LLM_MODE=openai
LLM_BASE_URL=http://127.0.0.1:8001/v1
LLM_MODEL=glm-4-flash
LLM_API_KEY=your_api_key
```

### 存储与记忆

```env
REDIS_URL=
DATA_DIR=data
DATABASE_PATH=data/live_prompter.db
CHROMA_DIR=data/chroma
SESSION_TTL_SECONDS=14400
```

说明：

- `REDIS_URL` 为空时，短期记忆退化为进程内内存
- Chroma 不可用时，向量检索会退化为轻量文本相似策略

## 后端接口

### 健康检查

```http
GET /health
```

返回服务状态和当前房间号。

### 获取前端初始化快照

```http
GET /api/bootstrap?room_id=32137571630
```

返回：

- 最近事件
- 最近建议
- 当前统计
- 当前模型状态

### 切换当前采集房间

```http
POST /api/room
Content-Type: application/json
```

请求体：

```json
{
  "room_id": "32137571630"
}
```

### 手动注入标准化事件

```http
POST /api/events
Content-Type: application/json
```

可用于联调或替换采集端。

### SSE 实时流

```http
GET /api/events/stream?room_id=32137571630
```

事件类型包括：

- `event`
- `suggestion`
- `stats`
- `model_status`

### WebSocket 实时流

```http
GET /ws/live
```

连接后会先收到一次 `bootstrap` 快照。

## 标准事件格式

采集器会把抖音原始消息统一转换为如下结构：

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

当前内置事件类型映射：

- `WebcastChatMessage` -> `comment`
- `WebcastGiftMessage` -> `gift`
- `WebcastLikeMessage` -> `like`
- `WebcastMemberMessage` -> `member`
- `WebcastSocialMessage` -> `follow`
- 其他类型 -> `system`

## 建议生成逻辑

当前 `backend/services/agent.py` 的逻辑是：

1. 仅对 `comment`、`gift`、`follow` 事件生成建议
2. 构造最近事件、相似历史、用户画像上下文
3. 优先调用 OpenAI 兼容模型
4. 模型失败时回退到本地启发式规则
5. 将建议和模型状态实时推送给前端

## 前端功能

前端基于 Vue 3、Pinia、Tailwind，当前包括：

- 主提词卡片
- 最近事件流
- 事件类型筛选
- 房间切换
- 连接状态展示
- 模型状态展示
- 浅色 / 深色主题切换

## 已知边界

- 当前依赖本地 `douyinLive` 程序提供 WebSocket 消息源
- 房间切换支持已接入，但整体仍以单实例单采集链路为主
- Redis、Chroma 都是可选增强，不安装也能运行基本流程
- `deprecated/` 中保留了一些旧脚本，不代表当前推荐用法
- 仓库里仍有部分历史文件注释存在乱码，但主流程可运行

## 相关文档

- `USAGE.md`
- `tool/README.md`
- `deprecated/README.md`

## 致谢

特别感谢 [jwwsjlm/douyinLive](https://github.com/jwwsjlm/douyinLive)。

本项目当前依赖 `tool/` 目录下的 `douyinLive` 可执行文件作为本地直播消息源。
