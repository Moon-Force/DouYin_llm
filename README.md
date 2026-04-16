# Live Prompter Stack

一个面向抖音直播场景的实时提词与观众记忆工作台。

它的核心目标不是“自动开播”，而是给主播提供一套实时辅助系统：接收直播间事件，沉淀观众长期记忆，做真实语义召回，再把可操作的信息反馈到前端工作台，帮助主播更自然地接话、识别老观众、维护互动关系。

## 项目定位

这个项目更适合下面这类直播场景：

- 聊天型直播
- 陪伴型直播
- 人设型直播
- 需要“记住观众、理解上下文、给出下一句建议”的互动场景

当前版本已经移除了“历史事件向量召回”，只保留“观众记忆召回”这条主语义链路。

## 当前已实现

- 直播事件采集：接入 `douyinLive` 的 WebSocket 事件流，归一化为统一 `LiveEvent`
- 后端实时处理：FastAPI 负责事件入库、观众画像聚合、记忆抽取、语义召回、提词生成与 SSE/WebSocket 推送
- 长期记忆存储：`SQLite + Chroma` 保存观众记忆、观众备注、会话数据
- 真语义召回链路：支持真实 embedding 与向量检索，不再依赖“历史事件召回”
- embedding 严格模式：`EMBEDDING_STRICT=true` 时，禁用 hash fallback，确保不是“口头上的语义召回”
- 评论处理状态可视化：前端可看到每条评论是否入库、是否写入观众记忆、是否参与召回、是否生成提词
- 观众记忆人工纠偏：前端工作台支持人工新增、编辑、失效、恢复、置顶、删除和查看时间线
- 记忆状态同步召回：只有有效记忆参与语义召回；失效/删除记忆不会再被召回；人工新增和置顶记忆在排序上优先
- 模型设置面板：前端可直接在线修改模型名和系统提示词

## 架构总览

```mermaid
graph LR
  A["douyinLive.exe\n(tool/)"] -->|WebSocket| B["Collector\nbackend/services/collector.py"]
  B --> C["FastAPI"]
  C --> D["SessionMemory\nRedis/内存"]
  C --> E["LongTermStore\nSQLite"]
  C --> F["VectorMemory\nChroma"]
  C --> G["LivePromptAgent\nLLM + 规则"]
  G --> H["SSE / WebSocket"]
  H --> I["Vue 3 前端"]
```

## 观众记忆纠偏工作流

在右侧 `ViewerWorkbench` 中，现在已经可以对单个观众记忆执行完整纠偏：

- 人工新增记忆
- 编辑自动抽取或人工新增的记忆文本
- 标记记忆失效
- 恢复失效记忆
- 置顶高优先级记忆
- 删除错误记忆
- 查看单条记忆的处理时间线

语义召回规则：

- `active` 记忆才会参与语义召回
- `invalid` 和 `deleted` 记忆不会参与语义召回
- 人工新增记忆和置顶记忆在排序时优先级更高

## 评论处理状态

针对“新进入系统并被实时处理的评论”，前端事件流会展示处理轨迹：

- 是否已入库
- 是否成功保存为观众记忆
- 是否参与语义召回
- 是否命中观众记忆召回
- 是否生成提词建议

展开后还能看到：

- `saved_memory_ids`
- `recalled_memory_ids`
- `suggestion_id`
- 未生成建议时的阻断原因

说明：

- 这套状态主要覆盖新进入系统的评论
- 历史 bootstrap 事件允许没有 `processing_status`
- 当前召回只针对观众记忆，不再包含历史事件相似召回

## 快速启动

1. 启动采集器

```powershell
.\tool\douyinLive-windows-amd64.exe
```

2. 复制环境变量

```powershell
Copy-Item .env.example .env
```

至少需要配置：

- `ROOM_ID`
- `LLM_API_KEY` 或 `DASHSCOPE_API_KEY`
- 如果使用云端 embedding，再配置 `EMBEDDING_API_KEY`

3. 安装后端依赖

```powershell
pip install -r requirements.txt
```

4. 启动后端

```powershell
python -m uvicorn backend.app:app --host 127.0.0.1 --port 8010 --reload
```

5. 启动前端

```powershell
cd frontend
npm install
npm run dev -- --host 127.0.0.1 --strictPort --port 5173
```

6. 或者直接使用脚本

```powershell
.\start_all.ps1
```

默认访问地址：

- 前端：`http://127.0.0.1:5173`
- 健康检查：`http://127.0.0.1:8010/health`

## 关键配置

### LLM 相关

- `LLM_MODE`
- `LLM_BASE_URL`
- `LLM_MODEL`
- `LLM_API_KEY`
- `DASHSCOPE_API_KEY`
- `LLM_TIMEOUT_SECONDS`
- `LLM_TEMPERATURE`
- `LLM_MAX_TOKENS`

### 向量与 embedding 相关

- `DATA_DIR`
- `DATABASE_PATH`
- `CHROMA_DIR`
- `EMBEDDING_MODE`
- `EMBEDDING_MODEL`
- `EMBEDDING_BASE_URL`
- `EMBEDDING_API_KEY`
- `LOCAL_EMBEDDING_DEVICE`
- `LOCAL_EMBEDDING_BATCH_SIZE`
- `SEMANTIC_*`

### 严格语义模式

如果你要求的是“真实 embedding + 真实语义召回”，建议显式开启：

```powershell
EMBEDDING_STRICT=true
```

开启后：

- embedding 生成失败时，不再回退到 hash embedding
- 向量召回失败时，不再回退到词项匹配
- `rebuild_embeddings.py` 不会写入伪 embedding 结果

`GET /health` 里可查看：

- `embedding_strict`
- `semantic_backend_ready`
- `semantic_backend_reason`

这能区分“确实没有召回到记忆”和“语义后端本身不可用”。

## 目录结构

| 路径 | 说明 |
| --- | --- |
| `backend/app.py` | FastAPI 入口，提供 REST、SSE、WebSocket 接口 |
| `backend/services/collector.py` | 对接 douyinLive WebSocket，转换并分发事件 |
| `backend/services/agent.py` | 提词生成、语义召回上下文拼装、模型状态输出 |
| `backend/memory/` | SessionMemory、SQLite LongTermStore、Chroma VectorMemory、EmbeddingService |
| `frontend/src/App.vue` | 前端主布局 |
| `frontend/src/stores/live.js` | Pinia Store，管理事件流、状态、ViewerWorkbench、LLM 设置 |
| `frontend/src/components/ViewerWorkbench.vue` | 观众详情、备注、记忆纠偏与时间线 UI |
| `tests/` | Python 单元测试 |
| `docs/` | 设计稿与实施计划 |

## 后端接口速览

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `GET /health` | 健康状态、房间号、strict mode、语义后端状态 |
| `GET /api/bootstrap?room_id=` | 前端初始化数据 |
| `POST /api/room` | 切换房间 |
| `POST /api/events` | 手动注入事件 |
| `GET /api/viewer` | 获取观众画像、记忆、备注、近期互动 |
| `POST /api/viewer/memories` | 新增观众记忆 |
| `PUT /api/viewer/memories/{memory_id}` | 更新观众记忆 |
| `POST /api/viewer/memories/{memory_id}/invalidate` | 标记记忆失效 |
| `POST /api/viewer/memories/{memory_id}/reactivate` | 恢复记忆有效 |
| `DELETE /api/viewer/memories/{memory_id}` | 删除观众记忆 |
| `GET /api/viewer/memories/{memory_id}/logs` | 获取单条记忆时间线 |
| `GET /api/viewer/notes` / `POST /api/viewer/notes` / `DELETE /api/viewer/notes/{id}` | 观众备注 CRUD |
| `GET /api/settings/llm` / `PUT /api/settings/llm` | 获取/保存模型设置 |
| `GET /api/events/stream` | SSE 实时流 |
| `GET /ws/live` | WebSocket 实时流 |

## 测试

前端：

```powershell
node frontend/src/components/event-feed-processing-presenter.test.mjs
node frontend/src/components/viewer-memory-presenter.test.mjs
node frontend/src/stores/viewer-workbench.test.mjs
npm --prefix frontend run build
```

后端：

```powershell
python -m unittest `
  tests.test_comment_processing_status `
  tests.test_long_term `
  tests.test_vector_store `
  tests.test_viewer_memory_api
```

语义链路自检：

```powershell
python tests/verify_memory_pipeline.py --mode internal
python tests/verify_memory_pipeline.py --mode e2e
python -m unittest tests.test_verify_memory_pipeline
```

## 数据文件

- `data/live_prompter.db`：事件、建议、观众记忆、观众备注、LLM 设置、会话记录
- `data/chroma/`：观众记忆向量索引
- `logs/`：调试日志

如果需要重建观众记忆向量索引：

```powershell
python backend/memory/rebuild_embeddings.py
```

## 还可以继续改进的点

1. 语义链路可观测性
   现在已经能看到 strict mode 和评论处理轨迹，但还缺少 embedding 成功率、召回命中率、失败原因聚合、恢复建议等运维级指标。

2. 后端初始化副作用收敛
   当前 `backend.app` 在导入阶段仍会做较多初始化，影响测试隔离、启动时序和调试体验。

3. 失败恢复与告警
   现在前端能看到“为什么没生成提词”，但缺少连续失败告警、自动恢复提示、值守视角的排障面板。

4. 多房间与权限体系
   当前更适合单人、本地、单直播间使用，还没有多房间并行、多操作者协作、登录鉴权等能力。

5. 人工纠偏的批量能力
   现在已经能单条纠偏，但还没有批量失效、批量审核、筛选待纠偏记忆、人工确认队列这类更强的运营入口。

## 已知限制

1. 采集端当前仍依赖 Windows 可执行文件 `tool/douyinLive-windows-amd64.exe`
2. 当前默认是单房间串行接入，不支持多直播间并行监听
3. 尚未实现登录鉴权与多租户隔离，不适合直接暴露公网
4. 观众记忆人工纠偏已经可用，但批量审核和运营工作流仍不完整
5. 系统级观测与告警能力仍偏弱，定位问题还比较依赖人工查看日志

## 致谢

- [jwwsjlm/douyinLive](https://github.com/jwwsjlm/douyinLive)
- 所有在 issue / PR 中持续推动这个项目演进的贡献者
