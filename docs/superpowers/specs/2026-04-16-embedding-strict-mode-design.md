# 嵌入严格模式设计

## 目标

把当前“embedding 后端失败时自动退回 hash embedding / 词项匹配”的行为，改造成一个**可配置的严格模式**。

开启严格模式后，系统必须满足以下原则：

- 语义向量写入必须使用真实 embedding
- 语义召回必须依赖真实向量检索
- 任一语义链路失败时直接报错，不允许静默降级

本设计的核心目标不是“系统尽量可用”，而是“保证语义召回是真的语义召回，而不是假装在召回”。

## 背景问题

当前项目存在两条会让“真语义召回”失真的降级路径：

1. `backend/memory/embedding_service.py`
   当云端 embedding 或本地 embedding 失败时，会自动退回 `HashEmbeddingFunction`

2. `backend/memory/vector_store.py`
   当 Chroma 不可用或查询失败时，会退回内存词项匹配逻辑

这两条路径都能在开发期提供兜底能力，但在强调语义质量的场景下，会带来一个严重问题：

- 系统看起来仍然“有召回结果”
- 但结果已经不再来自真实 embedding + 真实向量检索

因此必须提供一个硬约束配置，让用户能够明确声明：

> 只接受真实 embedding 和真实语义召回，不接受任何伪语义 fallback。

## 适用范围

包含：

- embedding 生成链路
- viewer memory 向量写入链路
- viewer memory 语义召回链路
- embedding 重建脚本
- 启动日志和健康状态暴露

不包含：

- LLM 生成链路改造
- 前端 viewer workbench 的交互改版
- 新增多套向量数据库实现
- 修改 Chroma 以外的存储架构

## 方案比较

### 方案一：启动即硬失败

只要 embedding 模型、embedding API 或 Chroma 任何一环不满足要求，就直接阻止后端启动。

优点：

- 最硬
- 运行期不会出现“部分功能才发现不可用”

缺点：

- 运维容错太差
- 与当前期望“后端可启动，但语义链路必须真实”不完全一致

### 方案二：推荐方案，运行期语义链路硬失败

系统可启动，但只要进入 embedding、向量写入、向量召回或重建 embedding 的语义链路，一旦真实能力不可用，就立即报错，不允许退回 hash embedding 或词项匹配。

优点：

- 最符合“必须是真语义召回”的目标
- 不会把整个系统的其他能力都绑定到 embedding 可用性上
- 更容易区分“真实未命中”和“语义链路损坏”

缺点：

- 需要收口多处 fallback 逻辑

### 方案三：软禁用语义能力

后端可启动，但在检测到 embedding / Chroma 不可用时，仅禁用语义能力并通过日志提示。

优点：

- 使用体验更温和
- 对非语义功能影响小

缺点：

- 约束不够硬
- 容易再次出现“看起来在跑，实际上没有真语义召回”

### 推荐方案

采用方案二：**后端可启动，但语义链路硬失败**。

## 配置设计

新增配置项：

- `EMBEDDING_STRICT`

建议默认值：

- `false`

取值语义：

- `false`：保留当前开发期兜底逻辑
- `true`：启用嵌入严格模式

严格模式开启后：

- 禁止使用 `HashEmbeddingFunction` 作为 embedding fallback
- 禁止在 Chroma 查询失败后退回词项匹配
- 禁止在重建向量时使用伪 embedding 继续写入

## 行为定义

### 1. EmbeddingService

涉及文件：

- `backend/memory/embedding_service.py`

当前行为：

- `embedding_mode=cloud/local` 失败时自动退回 hash embedding

严格模式目标行为：

- 如果 `EMBEDDING_STRICT=true`
- 且 `cloud/local` embedding 失败
- 则直接抛出明确异常
- 日志必须说明是“严格模式阻止了 fallback”

非严格模式下：

- 保持现有 hash fallback 行为不变

### 2. VectorMemory 初始化与写入

涉及文件：

- `backend/memory/vector_store.py`
- `backend/app.py`

当前行为：

- 若 `chromadb` 不可用，可退回进程内内存索引
- 写入和召回仍能看起来“正常工作”

严格模式目标行为：

- 若严格模式开启且 Chroma 不可用
- 则语义向量能力视为不可用
- 不允许把 viewer memory 当作“已具备语义检索能力”来继续运行

建议处理方式：

- `VectorMemory` 初始化时保留对象创建能力
- 但记录当前 `semantic_backend_ready=false`
- 当发生 `add_memory()` 或 `similar_memories()` 等语义链路调用时直接抛错

这样可以满足：

- 后端整体仍能启动
- 但语义链路不会偷偷退回伪实现

### 3. VectorMemory 查询

当前行为：

- 若 Chroma 查询报错，则退回 token overlap 的词项匹配排序

严格模式目标行为：

- 一旦 Chroma 查询失败，直接报错
- 不允许执行词项 fallback

结果上要清楚区分：

- 正常召回但无命中：返回空列表
- 语义链路故障：抛异常

### 4. Embedding 重建脚本

涉及文件：

- `backend/memory/rebuild_embeddings.py`

严格模式目标行为：

- 当 `EmbeddingService.embed_texts()` 失败时，整个重建任务直接失败
- 不允许写入 hash embedding 结果

这样才能保证“重建后的向量库”也是真实 embedding 产物。

### 5. 健康状态与日志

涉及文件：

- `backend/app.py`
- 可能补充 `GET /health`

建议增加以下可见信息：

- `embedding_strict`: 当前是否开启严格模式
- `semantic_backend_ready`: 当前真实 embedding + Chroma 是否处于可用状态
- `semantic_backend_reason`: 若不可用，给出简短原因

说明：

- 这里的健康状态不是“严格模式关闭时一切都健康”
- 而是帮助区分“当前到底是可用真语义，还是只是系统启动了”

## 错误语义

为了避免调试时混淆，严格模式下应明确区分两类错误：

### 初始化期错误

例如：

- `sentence-transformers` 未安装
- 本地 embedding 模型无法加载
- embedding API key 缺失
- Chroma 依赖不可用

这类错误不要求阻止整个服务启动，但必须能通过健康状态或日志快速看见。

### 运行期错误

例如：

- 云端 embedding 超时
- embedding API 返回异常
- Chroma 查询失败
- Chroma upsert 失败

这类错误在严格模式下必须：

- 直接抛出
- 日志显式标注 strict mode 阻断 fallback
- 不允许伪装成“无召回结果”

## 组件职责

### `backend/config.py`

职责：

- 增加 `embedding_strict` 配置项

### `backend/memory/embedding_service.py`

职责：

- 判断当前是否允许 fallback
- 在严格模式下抛出明确异常

### `backend/memory/vector_store.py`

职责：

- 统一收口语义检索相关 fallback
- 在严格模式下，Chroma 缺失或失败时直接报错
- 暴露真实语义后端是否 ready 的状态

### `backend/app.py`

职责：

- 暴露 semantic backend 状态
- 在 health 或启动日志中清晰说明当前模式

### `backend/memory/rebuild_embeddings.py`

职责：

- 重建任务沿用严格模式语义
- 保证不会把伪 embedding 写入向量集合

## 测试设计

至少覆盖以下场景：

### `tests/test_embedding_service.py`

- 非严格模式下，cloud embedding 失败会退回 hash embedding
- 严格模式下，cloud embedding 失败直接抛错
- 严格模式下，local embedding 缺依赖直接抛错

### `tests/test_vector_store.py`

- 非严格模式下，Chroma 查询失败仍可退回词项匹配
- 严格模式下，Chroma 查询失败直接抛错
- 严格模式下，若 Chroma 不可用，`similar_memories()` 不允许继续走伪召回

### `tests/test_rebuild_embeddings.py`

- 非严格模式下，现有 rebuild 行为保持兼容
- 严格模式下，embedding 失败时 rebuild 直接失败

### `tests/test_app.py` 或相邻测试

- `/health` 或初始化状态中能看见 `embedding_strict`
- `/health` 或初始化状态中能看见 `semantic_backend_ready`

## 向后兼容

为避免一次性破坏已有本地调试流程：

- 默认 `EMBEDDING_STRICT=false`
- 只有显式开启时才强制执行严格约束

这意味着：

- 现有开发体验不会被突然打断
- 需要真语义召回的场景可以明确开启硬约束

## 完成标准

满足以下条件即可视为完成：

- 存在可配置开关控制 embedding 严格模式
- 严格模式开启后，embedding 失败不再退回 hash embedding
- 严格模式开启后，向量查询失败不再退回词项匹配
- 严格模式开启后，embedding rebuild 不再写入伪 embedding
- 健康状态或日志可明确看见当前是否具备真实语义能力
- 测试能区分严格模式和非严格模式两套行为
