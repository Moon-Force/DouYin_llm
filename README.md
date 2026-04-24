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
- 真语义召回链路：支持真实 embedding 与向量检索，不再依赖"历史事件召回"
- embedding 后端：只接受真实 embedding，生成失败时直接报错，不再使用 hash fallback
- LLM 记忆抽取：通过 Ollama / OpenAI-compatible 接口调用 LLM 做语义理解，支持 `memory_text_raw / memory_text_canonical` 双字段提纯、`polarity / temporal_scope` 标注、问句壳子过滤、负面偏好校验，仅异常时回退到规则兜底
- 记忆合并与冲突处理：抽取后查询已有记忆 + 语义召回，由 `ViewerMemoryMergeService` 决策 `merge / upgrade / supersede / create` 四种动作，避免重复记忆和方向冲突
- 多维置信度打分：`MemoryConfidenceService` 从稳定性、互动价值、清晰度、证据量四个维度打分并加权合成 `confidence`，merge/upgrade 后动态刷新
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
- `SEMANTIC_*`

### 记忆 rerank 相关

`VectorMemory` 会先用 embedding/Chroma 召回候选，再可选调用在线 reranker 对候选重排。默认关闭；未配置 key 或接口异常时，会自动回退到原向量排序，不阻断直播主链路。

- `MEMORY_RERANK_ENABLED`：是否启用在线重排，默认 `false`
- `MEMORY_RERANK_BASE_URL`：OpenAI-compatible rerank 服务地址，默认 `https://ai.gitee.com/v1`
- `MEMORY_RERANK_MODEL`：默认 `Qwen3-Reranker-0.6B`
- `MEMORY_RERANK_API_KEY`：rerank API key，不要提交到仓库
- `MEMORY_RERANK_TIMEOUT_SECONDS`：单次重排超时，默认 `0.8`
- `MEMORY_RERANK_TOP_N`：传给 reranker 的候选上限，默认 `3`

### 本地模型目录约定

项目根目录保留了 `model/` 作为本地模型存放目录，方便团队成员统一放置不提交到仓库的大模型文件：

| 路径 | 用途 |
| --- | --- |
### 观众记忆抽取（Ollama）

观众记忆抽取现在使用 Ollama / OpenAI-compatible chat 接口，推荐按以下方式配置：

1. 启动 Ollama 服务
2. 拉取一个用于记忆抽取的模型
3. 设置 `MEMORY_EXTRACTOR_ENABLED=true`
4. 设置 `MEMORY_EXTRACTOR_BASE_URL=http://127.0.0.1:11434/v1`
5. 设置 `MEMORY_EXTRACTOR_MODEL=<your ollama model name>`

说明：之前的 in-process GGUF runtime 路径已移除。

### Embedding

embedding 现在通过 Ollama / OpenAI-compatible `/embeddings` 接口调用，不再走应用内本地 SentenceTransformer 直连。

### 严格语义模式

如果你要求的是“真实 embedding + 真实语义召回”，建议显式开启：

```powershell
EMBEDDING_STRICT=true
```

开启后：

- embedding 生成本身已经不会回退到 hash embedding，失败时会直接抛错
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

### `live_prompter.db` 业务表说明

| 表名 | 作用 | 关键内容 |
| --- | --- | --- |
| `events` | 直播事件总表，也是最底层原始流水 | 评论、进场、点赞、送礼、关注、系统事件；包含 `event_type`、`content`、`viewer_id`、`session_id`、`raw_json` |
| `viewer_profiles` | 观众行为聚合画像表，不是语义画像 | 累计评论数、进场数、礼物数、最近评论、首次/最近出现时间 |
| `viewer_gifts` | 观众送礼聚合表 | 按 `room_id + viewer_id + gift_name` 聚合礼物次数、总数量、总钻石数、最近送礼时间 |
| `live_sessions` | 直播场次表 | 一场直播一个 `session_id`，记录开始/结束时间、事件数、评论数、进场数、礼物数 |
| `suggestions` | AI 提词建议表 | 每次为某条事件生成的建议回复、优先级、语气、原因、置信度 |
| `viewer_memories` | 观众长期记忆表，是语义召回的核心业务表 | 从评论中抽取出的 `memory_text`、`memory_type`、`confidence`、`status`、`source_kind`、`recall_count` |
| `viewer_memory_logs` | 观众记忆操作日志表 | 记录记忆的创建、编辑、失效、恢复、删除、置顶等前后变化，适合做时间线审计 |
| `viewer_notes` | 主播/运营人工备注表 | 与自动抽取记忆分开存放，保存人工写入的备注内容和置顶状态 |
| `app_settings` | 轻量应用设置表 | 简单键值配置，例如模型相关设置 |

说明：

- 语义召回主链路直接相关的表主要是 `viewer_memories`，对应的向量索引存放在 `data/chroma/`。
- `viewer_profiles` 当前主要是行为统计画像，不等同于结构化语义画像。
- SQLite 本身不支持像 MySQL 那样在表结构上原生写 `COMMENT`，所以这里用 README 维护数据字典。

如果需要重建观众记忆向量索引：

```powershell
python backend/memory/rebuild_embeddings.py
```

## 当前记忆抽取仍然存在的问题

当前版本已经接入 LLM 记忆抽取（`LLMBackedViewerMemoryExtractor`），支持 `memory_text_raw / memory_text_canonical` 双字段提纯、`polarity / temporal_scope` 门控、评论预筛、仅异常时规则兜底。抽取后由 `ViewerMemoryMergeService` 决策合并策略，由 `MemoryConfidenceService` 做四维置信度打分，`VectorMemory` 负责 feature rerank 与生命周期过滤。主链路已经比较完整，但从直播提词和长期记忆维护的角度看，仍然有这些问题：

1. 记忆生命周期管理已经起步，但还不够完整
   当前 `viewer_memories` 已经增加 `lifecycle_kind / expires_at`，存储查询和向量召回也会过滤过期记忆，`VectorMemory` 仍保留时间衰减排序作为补充。但这还不是完整的 long-term / short-term 双层架构，也没有独立的短期记忆池、自动迁移和更丰富的生命周期策略。

2. 规则驱动的质量判断仍然偏启发式
   无论是 `interaction_value_score`，还是 `MemoryConfidenceService` 中的 `stability_score / interaction_value_score / clarity_score / evidence_score`，当前都主要依赖手工规则和关键词启发。它们已经能覆盖明显样本，但对复杂表达、弱信号、边界语义和真实业务反馈的利用还不够充分。

3. 规则兜底已经做了保守提纯和降权，但覆盖范围仍有限
   当前 `extract_high_confidence` 已经支持一小批高置信模板、保守 canonical 提纯、明显负向限制的 `polarity=negative` 推断，以及 `rule_fallback` 的质量降权，不再默认把原句完整写入长期记忆池。但这条路径仍然只覆盖有限模板，复杂表达在 LLM 异常时仍然容易被放弃，而不是像主 LLM 路径那样稳定理解。

4. 记忆合并对近义和弱冲突的覆盖不够
   当前 `ViewerMemoryMergeService` 能处理同 canonical 精确匹配（merge）、更具体表达（upgrade）、方向冲突（supersede），但对近义但不完全相同的表达、弱冲突偏好变化的覆盖还不够，长期仍可能出现冗余记忆。

5. 召回排序已经支持 feature rerank + 可选模型 rerank
   当前召回排序已经把 `semantic_score` 与业务特征分开处理，并系统使用 `interaction_value_score`、`evidence_score`、`stability_score`、`confidence`、`source_kind`、`is_pinned` 和时间衰减等信号做 feature rerank，不再只依赖纯向量相似度。线上还可以通过 `MEMORY_RERANK_ENABLED=true` 接入专门 reranker model 对候选二次重排；后续仍可继续接入业务反馈闭环和更细的召回可观测指标。

6. 抽取评测和高并发保护仍不够完善
   当前已经有抽取相关测试和离线验证（`tests/fixtures/memory_extraction/`、`artifacts/memory_extraction_reports/`），也已经有严格模式和召回回归测试。但还缺少问句误入库率、短期状态误入库率、重复记忆生成率等持续指标，同时记忆抽取仍然是同步阻塞调用（`extract_method(event)`），没有异步队列、batch 或速率限制。当前单房间直播场景下影响不大，但如果未来扩展到多房间或高频场景，可能造成事件堆积。

## 还可以继续改进的点

1. 长期/短期双层记忆
   当前已经能识别短期内容，但还没有正式的 short-term memory 层。后续可以把"本场直播有效"与"长期稳定画像"分开存储、分开召回、分开衰减。

2. 已入库记忆衰减与过期
   在双层记忆的基础上，给长期记忆增加时间衰减函数，让过时时效信息自动降权或迁移，避免"准备去日本"半年后仍被召回。

3. 提词价值驱动的记忆排序
   在召回阶段把"是否人工确认过、是否近期再次被证实、是否对主播接话更有帮助"纳入 rerank 和建议生成上下文排序。

4. 语义链路可观测性
   现在已经能看到 strict mode 和评论处理轨迹，但还缺少 embedding 成功率、召回命中率、抽取误入库率、失败原因聚合、恢复建议等更完整的运维级指标。

5. 失败恢复与告警
   现在前端能看到"为什么没生成提词"，但缺少连续失败告警、自动恢复提示、值守视角的排障面板。

6. 多房间与权限体系
   当前更适合单人、本地、单直播间使用，还没有多房间并行、多操作者协作、登录鉴权等能力。

7. 人工纠偏的批量能力
   现在已经能单条纠偏，但还没有批量失效、批量审核、筛选待纠偏记忆、人工确认队列这类更强的运营入口。

8. 后端初始化副作用收敛
   当前 `backend.app` 在导入阶段仍会做较多初始化，影响测试隔离、启动时序和调试体验。

## 已知限制

1. 采集端当前仍依赖 Windows 可执行文件 `tool/douyinLive-windows-amd64.exe`
2. 当前默认是单房间串行接入，不支持多直播间并行监听
3. 尚未实现登录鉴权与多租户隔离，不适合直接暴露公网
4. 观众记忆人工纠偏已经可用，但批量审核和运营工作流仍不完整
5. 系统级观测与告警能力仍偏弱，定位问题还比较依赖人工查看日志

## 致谢

- [jwwsjlm/douyinLive](https://github.com/jwwsjlm/douyinLive)
- 所有在 issue / PR 中持续推动这个项目演进的贡献者
