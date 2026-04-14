# Memory Pipeline Verifier Design

## Goal

新增一个仓库内自检工具 `tool/verify_memory_pipeline.py`，用于验证“评论提炼观众记忆 -> 落 SQLite -> 写入向量索引 -> 语义召回”这条链路是否正常，并在需要时补充一次自动拉起后端的端到端校验。

## Current Context

- 当前观众记忆抽取逻辑在 [backend/services/memory_extractor.py](H:\DouYin_llm\backend\services\memory_extractor.py)，只对符合条件的 `comment` 事件提炼 `memory_text`、`memory_type`、`confidence`。
- 当前长期存储逻辑在 [backend/memory/long_term.py](H:\DouYin_llm\backend\memory\long_term.py)，负责写入 `events`、`viewer_profiles`、`viewer_memories` 等 SQLite 表。
- 当前向量能力在 [backend/memory/vector_store.py](H:\DouYin_llm\backend\memory\vector_store.py)，既支持 Chroma，也支持 in-process fallback 索引。
- 当前端到端事件入口在 [backend/app.py](H:\DouYin_llm\backend\app.py)，可以通过 `/api/events` 注入测试事件，通过 `/api/viewer` 查询观众详情。
- 目前仓库里已有 `test_vector_store.py`、`test_agent.py`、`test_rebuild_embeddings.py` 等单元测试，但没有一个面向开发者日常排查的“一键自检脚本”。

## Chosen Approach

采用“单脚本双模式”的方案，在 `tool/verify_memory_pipeline.py` 里提供：

- `internal` 模式：
  直接在 Python 进程内验证抽取器、SQLite 持久化和向量召回，不依赖已启动的 HTTP 服务。
- `e2e` 模式：
  先尝试连接本地后端；如果后端未启动，则由脚本临时拉起 `uvicorn`，随后通过 HTTP 接口完成事件注入和 viewer 查询，再在脚本结束时自动关闭由它拉起的后端进程。

默认输出采用“逐步打印每一步过程和结果”的形式，方便肉眼排查，不额外引入测试框架或 CLI 依赖。

## Script Responsibilities

`tool/verify_memory_pipeline.py` 的职责限定为：

- 读取现有项目配置并打印关键运行上下文
- 构造一条稳定可复现的中文测试评论
- 验证 `ViewerMemoryExtractor.extract()` 是否能提炼出候选 memory
- 验证测试事件是否能进入 SQLite 的 `events`、`viewer_profiles`、`viewer_memories`
- 验证相近语义查询是否能通过 `VectorMemory.similar_memories()` 召回刚写入的 memory
- 在 `e2e` 模式下验证 `/api/events` 与 `/api/viewer` 的行为
- 汇总每一步的 PASS/FAIL，并用退出码表达整体结果

明确不负责：

- 自动清理数据库中的历史测试记录
- 修改业务逻辑或修复抽取规则
- 替代现有单元测试
- 校验前端页面展示

## Modes

### Internal Mode

`internal` 模式用于快速验证核心链路，步骤如下：

1. 加载 `Settings`、`LongTermStore`、`EmbeddingService`、`VectorMemory`
2. 打印当前数据库路径、embedding mode、Chroma 目录、LLM mode
3. 用固定测试事件直接调用 `ViewerMemoryExtractor.extract()`
4. 将测试事件通过现有持久化逻辑写入 SQLite
5. 将提炼出的 memory 保存到 `viewer_memories`
6. 重建/补充当前进程内 `VectorMemory`
7. 用语义相近的新查询执行 `similar_memories()`
8. 校验召回结果是否包含刚保存的 memory

### End-to-End Mode

`e2e` 模式在 `internal` 基础上补一层接口校验：

1. 检查 `http://127.0.0.1:8010/health`
2. 若不可达，则脚本临时启动 `python -m uvicorn backend.app:app --host 127.0.0.1 --port 8010`
3. 轮询等待 `/health` 返回成功
4. 向 `/api/events` 注入测试事件
5. 调用 `/api/viewer?room_id=...&viewer_id=...` 查询观众详情
6. 校验 viewer 详情中的 `memories` 是否包含目标 memory
7. 若后端由脚本拉起，则结束前自动关闭该进程

## Test Data Strategy

脚本使用固定且稳定的 Unicode 测试数据，避免 PowerShell 中文编码导致的误判：

- `room_id`: `verify-memory-room`
- `viewer_id`: `id:verify-memory-viewer`
- `nickname`: `验证用户`
- 评论文本：`我在杭州上班，最近总是熬夜，周末想补补皮肤状态`
- 召回查询：`最近熬夜皮肤状态不太好`

选择该文本的原因：

- 能命中当前 `ViewerMemoryExtractor` 的关键词规则
- 既包含上下文信息，也包含计划/状态信息
- 与后续召回查询语义接近但非完全相同，适合验证语义检索而不是字面匹配

## Output Format

脚本默认逐步打印结果，每一步至少包含：

- 当前步骤名称
- 正在做什么
- 关键中间值（如抽取出的 memory、查询命中的结果数量、是否启动了后端）
- PASS/FAIL 结论

末尾汇总：

- `overall: PASS` 或 `overall: FAIL`
- 失败步骤名称列表
- 非 0 退出码用于 CI/脚本调用方判断失败

## Error Handling

- 任一步失败后，不立刻崩溃退出；脚本会尽量继续收集后续可获取信息，帮助定位问题。
- 如果依赖初始化失败（如数据库路径不可写、模块导入失败），脚本标记该步骤失败，并跳过依赖该步骤的后续检查。
- `e2e` 模式下若自动拉起后端失败，脚本会打印启动日志摘要并标记接口层检查失败。
- 若 viewer 接口返回 404，但 SQLite 中已有目标 viewer profile，则脚本将其归类为“接口层异常”而不是“数据写入失败”。
- 只有由脚本自己启动的后端进程才会被自动关闭；已存在的用户后端实例不受影响。

## File Changes

- Create: `H:\DouYin_llm\tool\verify_memory_pipeline.py`
  - 实现双模式自检脚本、逐步日志输出、退出码约定
- Create: `H:\DouYin_llm\tests\test_verify_memory_pipeline.py`
  - 覆盖测试数据、步骤协调、关键判定函数与自动拉起后端逻辑中的纯函数部分

如有需要，可在实现时小幅修改：

- `H:\DouYin_llm\README.md`
  - 添加一段“如何运行 memory pipeline 自检”说明

## Testing Strategy

实现时至少覆盖两类验证：

1. 单元测试
- 固定测试文本能命中预期抽取结果
- 结果汇总函数能在步骤成功/失败时返回正确状态
- 端到端模式的后端启动判定、超时判定和结果格式化逻辑可独立测试

2. 手工运行验证
- `python tool/verify_memory_pipeline.py --mode internal`
- `python tool/verify_memory_pipeline.py --mode e2e`

期望：

- internal 模式能打印抽取成功、SQLite 落库成功、向量召回成功
- e2e 模式能在后端未启动时自动启动后端，并完成 `/api/events` 与 `/api/viewer` 检查

## Scope Guard

本次只做一个开发者自检工具，不扩展成通用测试平台。

明确不包含：

- 清理历史验证数据的完整生命周期管理
- 自动生成 HTML 报告
- 前端页面联动检查
- 多房间、多观众批量压测
- 自动修复数据库/向量索引问题
