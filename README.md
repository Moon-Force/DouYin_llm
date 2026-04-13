# Live Prompter Stack

Live Prompter Stack 是一个面向抖音直播间的实时提词工作栈，由本地采集工具、FastAPI 后端与 Vue 3 前端组成。它可以把 douyinLive WebSocket 流里的评论、礼物与关注事件转成结构化 `LiveEvent`，在 SQLite/Chroma 中沉淀观众记忆，并通过 LLM 或启发式规则生成提词建议，最后以前端仪表板的形式推送给主持人。

## 架构总览

```mermaid
graph LR
  A[douyinLive.exe\n(tool/)] -->|WebSocket| B[Collector\nbackend/services/collector.py]
  B --> C[FastAPI]
  C --> D[SessionMemory\nRedis/内存]
  C --> E[LongTermStore\nSQLite]
  C --> F[VectorMemory\nChroma]
  C --> G[LivePromptAgent\nLLM+规则]
  G --> H[SSE & WebSocket]
  H --> I[Vue 3 前端]
```

- `tool/douyinLive-windows-amd64.exe` 负责从抖音直播间抓取实时流并落地成本地 WebSocket。
- `backend/` 内的 FastAPI 进程负责事件归一化、持久化、记忆抽取、提词生成与 SSE/WebSocket 推送。
- `frontend/` 通过 Pinia Store 与 StatusStrip/Teleprompter/ViewerWorkbench 等组件展示模型状态、事件流与观众工单。

## 功能亮点

- **直播事件采集**：Collector 将 douyinLive 原始消息规范为单一 `LiveEvent`，并自动补齐观众 ID 与礼物元数据。
- **语义记忆系统**：`LongTermStore` + `VectorMemory` 组合在 SQLite/Chroma 中保存短期会话、长期记忆与观众笔记。
- **LLM/规则双通道提词**：`LivePromptAgent` 先尝试走 OpenAI 兼容模型，失败后退回启发式规则，保障时延与稳定性。
- **多面板前端**：StatusStrip 展示连接/模型/统计状态，Teleprompter 聚焦当前建议，EventFeed 支持筛选与清空，ViewerWorkbench 提供观众画像+笔记，LlmSettingsPanel 支持在线编辑模型名与系统提示词。
- **可选依赖**：Redis 只在需要跨进程共享 SessionMemory 时启用；Chroma 与云端 Embedding 也可以按需关闭。
- **脚本化启动**：`start_all.ps1`、`start_backend_qwen.ps1`、`start_frontend.ps1` 简化本地双端启动。

## 目录结构

| 路径 | 说明 |
| --- | --- |
| `backend/app.py` | FastAPI 入口，提供 REST/SSE/WebSocket 接口。
| `backend/services/collector.py` | 与 douyinLive WebSocket 对接，转换并派发 `LiveEvent`。
| `backend/services/agent.py` | LLM+启发式提词引擎，以及模型状态上报。
| `backend/memory/` | SessionMemory、SQLite LongTermStore、Chroma VectorMemory 与 EmbeddingService。
| `frontend/src/App.vue` | 前端布局，挂载 StatusStrip、Teleprompter、EventFeed、ViewerWorkbench、LlmSettingsPanel。
| `frontend/src/stores/live.js` | Pinia Store，管理事件流、筛选、主题/语言、ViewerWorkbench 与 LLM 设置状态。
| `tool/` | douyinLive 可执行文件与采集配置示例。
| `tests/` | Python 单元测试：agent、记忆、嵌入、LLM 设置等。
| `docs/` | 设计稿与实施计划（`docs/superpowers/specs`, `docs/superpowers/plans`）。

## 运行要求

- Windows 10/11（采集端依赖 `tool/douyinLive-windows-amd64.exe`）。
- Python 3.10+，推荐 3.11。
- Node.js 18+（Vite 4 与原生 ES 模块）。
- Qwen / OpenAI 兼容 API Key（若启用 LLM）。
- 可选：Redis 6+（共享 SessionMemory）、Chroma 0.5+（向量索引）。

## 快速上手

1. **启动采集器**
   ```powershell
   .\tool\douyinLive-windows-amd64.exe
   ```
   默认会监听 `ws://127.0.0.1:1088/ws/{ROOM_ID}`，确保抖音 Cookie 已配置在 `tool/config.yaml`（如需登录态）。

2. **准备环境变量**
   ```powershell
   Copy-Item .env.example .env
   ```
   至少填写 `ROOM_ID` 与 `DASHSCOPE_API_KEY`（或其他 `LLM_API_KEY`）。

3. **安装 Python 依赖**
   ```powershell
   pip install -r requirements.txt
   ```

4. **运行后端**
   ```powershell
   python -m uvicorn backend.app:app --host 127.0.0.1 --port 8010 --reload
   ```

5. **运行前端**
   ```powershell
   cd frontend
   npm install
   npm run dev -- --host 127.0.0.1 --strictPort --port 5173
   ```

6. **使用封装脚本（可选）**
   ```powershell
   .\start_all.ps1
   # 或拆分：
   .\start_backend_qwen.ps1
   .\start_frontend.ps1
   ```

前端默认访问 `http://127.0.0.1:5173`，后端健康检查在 `http://127.0.0.1:8010/health`。

## 配置说明

`.env` > 当前 shell > 代码默认值。常用变量：

### 直播采集

| 变量 | 默认 | 说明 |
| --- | --- | --- |
| `ROOM_ID` | `""` | 当前监听的抖音直播间 ID，必须与 `tool` 采集器保持一致。|
| `COLLECTOR_ENABLED` | `true` | 是否启用内置 DouyinCollector。|
| `COLLECTOR_HOST` / `COLLECTOR_PORT` | `127.0.0.1` / `1088` | douyinLive WebSocket 地址。|
| `COLLECTOR_PING_INTERVAL_SECONDS` | `30` | 向采集器发送 ping 的间隔。|
| `COLLECTOR_RECONNECT_DELAY_SECONDS` | `3` | 断线后重连等待时间。|

### 后端进程

| 变量 | 默认 | 说明 |
| --- | --- | --- |
| `APP_HOST` / `APP_PORT` | `127.0.0.1` / `8010` | FastAPI 监听地址。|
| `SESSION_TTL_SECONDS` | `14400` | SessionMemory 过期时间（秒）。|
| `REDIS_URL` | `""` | 为空使用进程内内存，设置后启用 Redis SessionMemory。|

### 模型与提示词

| 变量 | 默认 | 说明 |
| --- | --- | --- |
| `LLM_MODE` | `heuristic` | `heuristic` / `qwen` / `openai`。|
| `LLM_BASE_URL` | Qwen/OpenAI 兼容地址 | OpenAI 兼容 API Endpoint。|
| `LLM_MODEL` | 依 `LLM_MODE` 推断 | 模型名称，可被前端覆盖。|
| `LLM_API_KEY` / `DASHSCOPE_API_KEY` | `""` | 模型鉴权；若为空会尝试兼容 DashScope Key。|
| `LLM_TIMEOUT_SECONDS` | `6` | 单次推理超时时间。|
| `LLM_TEMPERATURE` | `0.4` | 生成温度。|
| `LLM_MAX_TOKENS` | `120` | 最大输出 token。|

### 向量与嵌入

| 变量 | 默认 | 说明 |
| --- | --- | --- |
| `DATA_DIR` | `data` | 数据目录，包含 SQLite 与 Chroma。|
| `DATABASE_PATH` | `data/live_prompter.db` | SQLite 文件地址。|
| `CHROMA_DIR` | `data/chroma` | Chroma 磁盘存储。|
| `EMBEDDING_MODE` | `cloud` | `cloud` / `local` / 其他 -> hash fallback。|
| `EMBEDDING_MODEL` | `text-embedding-3-small` | 云端/本地嵌入模型名。|
| `EMBEDDING_BASE_URL` / `EMBEDDING_API_KEY` | OpenAI 默认 | 云端嵌入接口与密钥。|
| `LOCAL_EMBEDDING_DEVICE` | `cpu` | SentenceTransformer 运行设备。|
| `LOCAL_EMBEDDING_BATCH_SIZE` | `32` | 本地嵌入批大小。|
| `SEMANTIC_*` 系列 | 参考 `backend/config.py` | 控制相似度筛选与召回数量。|

## 数据流与关键流程

1. **采集**：`DouyinCollector` 通过 `ws://HOST:PORT/ws/{ROOM_ID}` 接收事件，映射成标准 `LiveEvent` 并提交到 asyncio 事件循环。
2. **记忆写入**：`SessionMemory` 保存最近 3 分钟事件与建议，`LongTermStore` 将事件/建议/观众记忆写入 SQLite，`VectorMemory` 同步更新 Chroma。
3. **提词生成**：`LivePromptAgent` 根据事件类型与上下文决定是否命中 LLM；若失败或命中特定关键词则转为启发式规则。
4. **实时推送**：通过 SSE (`/api/events/stream`) 与 WebSocket (`/ws/live`) 向前端广播事件、建议、统计与模型状态。
5. **前端展示**：Pinia Store 维护房间号、过滤器、ViewerWorkbench 状态，组件以响应式方式展示/编辑数据。

## 后端接口速查

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `GET /health` | 运行状况与当前房间。|
| `GET /api/bootstrap?room_id=` | 前端初始化数据，包含最近事件/建议、统计与模型状态。|
| `POST /api/room` | 切换房间，并返回新的快照。|
| `POST /api/events` | 手动注入 `LiveEvent`（联调/回放）。|
| `GET /api/viewer` | 获取指定观众画像、记忆、笔记与近期互动。|
| `GET /api/viewer/notes` / `POST /api/viewer/notes` / `DELETE /api/viewer/notes/{id}` | 观众笔记 CRUD。|
| `GET /api/settings/llm` / `PUT /api/settings/llm` | 获取/保存当前模型与系统提示词（保存在 `app_settings`）。|
| `GET /api/events/stream` | SSE 实时流（可附带 `room_id`）。|
| `GET /ws/live` | WebSocket 实时流（先下发 `bootstrap`）。|

详见 `backend/app.py` 与 `tests/` 中的接口覆盖。

## 前端开发与测试

- 开发：`npm run dev`
- 生产构建：`npm run build`
- 关键 Store/Presenter 测试：
  ```powershell
  node frontend/src/stores/viewer-workbench.test.mjs
  node frontend/src/stores/llm-settings.test.mjs
  node frontend/src/stores/locale.test.mjs
  node frontend/src/components/status-strip-presenter.test.mjs
  node frontend/src/stores/live.test.mjs
  ```

## Python 测试

```powershell
python -m unittest \
  tests.test_agent \
  tests.test_llm_settings \
  tests.test_embedding_service \
  tests.test_vector_store \
  tests.test_empty_room_bootstrap \
  tests.test_long_term \
  tests.test_rebuild_embeddings
```

## 数据与日志

- `data/live_prompter.db`：事件、建议、观众记忆、观众笔记、LLM 设置、会话记录。
- `data/chroma/`：语义向量索引（可清空重新构建，配合 `backend/memory/rebuild_embeddings.py`）。
- `logs/`：历史调试输出（`deprecated/debug_client.py` 可复现原始事件并写入此处）。

## 文档与设计

- `USAGE.md`：简化的运行指南。
- `docs/superpowers/specs/*.md`：最新的前端/后端设计稿。
- `docs/superpowers/plans/*.md`：针对单个特性的实施计划与拆解步骤。

## 已知限制 & 下一步

1. **采集端仍是 Windows 可执行文件**：仓库只附带 `tool/douyinLive-windows-amd64.exe`，尚未提供 Linux/macOS 二进制或容器镜像，需要手动从 [jwwsjlm/douyinLive](https://github.com/jwwsjlm/douyinLive) 获取其它平台版本。
2. **单房间串行接入**：`DouyinCollector` 仅维护一个 `ROOM_ID`（参见 `backend/services/collector.py`），虽可通过 `/api/room` 切换，但无法并行拉多间直播流。
3. **无鉴权/多租户**：FastAPI 与前端目前完全公开，未实现登录、权限与多操作员隔离，适合单人本地排练，不适合直接暴露到公网。
4. **观众记忆仅支持自动抽取**：`ViewerWorkbench` 只能增删笔记，`ViewerMemory` 尚无前端可见的编辑入口；若需要更细粒度的语义管理，需要扩展 API 与 UI。
5. **运维观测薄弱**：仅通过标准日志排查状态，没有事件追踪、指标或告警（可考虑 Prometheus/Grafana 或 APM 集成）。

欢迎在完成上述基础能力后继续扩展多房间调度、跨平台采集、观测面与模型管理策略。

## Star 趋势

[![Star History Chart](https://api.star-history.com/svg?repos=Moon-Force/DouYin_llm&type=Date)](https://star-history.com/#Moon-Force/DouYin_llm&Date)

## 致谢

- [jwwsjlm/douyinLive](https://github.com/jwwsjlm/douyinLive) 为采集层提供核心能力。
- 所有贡献者在 issue / PR 中的讨论帮助项目快速迭代。
