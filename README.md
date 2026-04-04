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

### 5.5 推荐的一键启动方式

先复制配置：

```bash
copy .env.example .env
```

然后填写 `.env` 里的 `DASHSCOPE_API_KEY`，再运行：

```powershell
.\start_all.ps1
```

如果只想单独启动后端或前端：

```powershell
.\start_backend_qwen.ps1
.\start_frontend.ps1
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
BACKEND_EVENT_URL = "http://127.0.0.1:8010/api/events"
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

项目根目录支持 `.env` 文件。后端启动时会自动读取 `.env`，不存在时才回退到当前 shell 环境变量。

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

## 待办事项

- [ ] 在 SQLite 中完整持久化 suggestion 字段，包括 `source`、`references`、`source_events`，避免重启后模型建议被错误标记。
- [ ] 让直播统计变成真实总量，而不是只统计最近一段内存窗口。
- [ ] 给 SSE / WebSocket broker 增加有界队列或明确的丢弃策略，避免慢连接导致内存持续增长。
- [ ] 按 `room_id` 隔离向量检索结果，避免不同直播间之间的相似历史串线。
- [ ] 清理旧的 collector 路径和文档，让说明和“后端内置采集器”的现状保持一致。
- [ ] 继续补强 `.gitignore`，覆盖更多运行日志和调试产物。
- [ ] 把文档和界面里剩余的乱码文本统一修复成正常的 UTF-8 中文。
- [ ] 为后端入库、事件处理、前端筛选等核心流程补基础回归测试。

## 路线图

### 第一阶段：把当前版本产品化

- [ ] 增加轻量控制面板，支持暂停/恢复建议、重连采集器、清空当前会话视图。
- [ ] 为建议增加反馈动作，比如“已使用”“忽略”“不合适”。
- [ ] 支持多直播间，在采集、存储、检索、前端切换上都按房间隔离。

### 第二阶段：提升建议质量

- [ ] 让 Prompt 模板可配置，支持电商、闲聊、健身、情感陪伴等不同直播场景。
- [ ] 扩充用户画像，加入最近出现时间、重复问题、高价值互动标记等信息。
- [ ] 对重复事件和近似建议做去重与节流。
- [ ] 将建议类型细分为直接回复、追问建议、转化提示、场控提示、风险提示等。

### 第三阶段：直播转化与风控能力

- [ ] 识别购买意图信号，例如价格、链接、发货、适用人群等问题。
- [ ] 高亮高价值事件，例如大礼物、重复互动、关注、强烈负面情绪等。
- [ ] 增加敏感内容和风险话术检测，降低违规回复风险。
- [ ] 增加场控建议，例如节奏提醒、卖点重复、福利引导、口播时机提示。

### 第四阶段：复盘与分析

- [ ] 生成直播结束后的复盘报告，包括高频问题、互动高峰、建议有效性等。
- [ ] 增加更完整的数据面板，展示弹幕量、礼物峰值、关注增长、模型成功率、fallback 率等。
- [ ] 支持导出事件、建议、用户画像和复盘总结。

### 第五阶段：工程与平台化

- [ ] 增加设置/管理页面，让房间号、模型参数、Prompt 配置不再只依赖 `.env`。
- [ ] 增加历史事件回放工具，方便复现实验和调试模型行为。
- [ ] 如果前端要给多人使用，补上基本鉴权能力。
- [ ] 将采集层逐步抽象成可插拔适配器，支持未来接入更多平台，不只限于抖音。

## 致谢

特别感谢 [jwwsjlm/douyinLive](https://github.com/jwwsjlm/douyinLive)。本项目依赖 `tool/` 目录下的 `douyinLive` 可执行文件作为本地抖音直播消息源。

## Star 历史

[![Star History Chart](https://api.star-history.com/svg?repos=Moon-Force/DouYin_llm&type=Timeline)](https://star-history.com/#Moon-Force/DouYin_llm&Timeline)