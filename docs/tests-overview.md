# Tests Overview

本文档汇总根目录 `tests/` 下各测试文件的主要职责，便于快速判断每个测试覆盖的模块和用途。

## 测试文件说明

### `tests/test_agent.py`

用于测试 `backend.services.agent.LivePromptAgent` 的核心行为，主要覆盖：

- `build_context()` 是否正确压缩最近事件、历史相似事件和观众记忆
- 礼物事件是否跳过 LLM，直接走启发式回复
- OpenAI 兼容接口调用时是否带上 `max_tokens` 等关键参数

### `tests/test_embedding_service.py`

用于测试 `backend.memory.embedding_service.EmbeddingService` 的嵌入生成逻辑，主要覆盖：

- 云端模式是否正确请求 `/embeddings` 接口
- 本地模式是否正确调用 `SentenceTransformer`
- 云端调用失败时是否退回到 hash embedding fallback

### `tests/test_empty_room_bootstrap.py`

用于测试空房间场景下的启动行为，主要覆盖：

- 未设置 `ROOM_ID` 时默认配置是否为空
- `DouyinCollector` 在空房间下是否不会启动采集线程
- 后续切换房间时是否可以正常启动采集器
- WebSocket 是否使用 ping frame 而不是文本 ping

### `tests/test_llm_settings.py`

用于测试 LLM 设置的持久化与读取逻辑，主要覆盖：

- `LongTermStore.save_llm_settings()` 是否正确保存模型和系统提示词
- 空白系统提示词是否会退回默认值
- `LivePromptAgent` 是否能读到运行时覆盖后的模型配置

### `tests/test_long_term.py`

用于测试 `backend.memory.long_term.LongTermStore` 的底层 SQLite 连接行为，主要覆盖：

- `_connect()` 是否使用正确的 sqlite 连接参数
- 是否切换到 `PRAGMA journal_mode=TRUNCATE`
- 返回连接对象时是否设置了预期的 `row_factory`

### `tests/test_rebuild_embeddings.py`

用于测试 `backend.memory.rebuild_embeddings.rebuild_embeddings()` 的重建流程，主要覆盖：

- `dry_run` 模式下是否只统计、不写入向量库
- `drop_existing=True` 时是否先删除旧 collection 再重建
- 正式执行时是否生成 `index_manifest.json`

### `tests/test_vector_store.py`

用于测试 `backend.memory.vector_store.VectorMemory` 的向量存储和召回行为，主要覆盖：

- collection 名称是否带 embedding signature
- `add_event()` 是否正确调用 embedding service 和 upsert
- `similar()` 是否按阈值过滤结果并返回结构化数据
- `similar_memories()` 在分数接近时是否优先高 confidence 的记忆

### `tests/test_verify_memory_pipeline.py`

用于测试 memory pipeline verifier 工具本身，主要覆盖：

- verifier 的基础工具函数，如模式解析、状态汇总、命令行参数解析
- 批量测试数据是否能稳定生成 50 条以上样本
- 测试夹具文件是否能正确导出
- 批量 SQLite 统计是否正确汇总
- `run_internal_verification()` 在批量模式下是否能输出正确的提取、落库和召回统计

## 相关脚本

### `tests/verify_memory_pipeline.py`

这个文件不是单元测试，而是 memory pipeline 的命令行入口脚本。它会调用：

- `tests/memory_pipeline_verifier/runner.py`
- `tests/memory_pipeline_verifier/datasets.py`

常见执行方式：

```powershell
python tests/verify_memory_pipeline.py --mode internal
python tests/verify_memory_pipeline.py --mode internal --dataset tests/fixtures/memory_pipeline_events.json
python tests/verify_memory_pipeline.py --mode e2e
```

## 总结

当前根目录 `tests/*.py` 没有明显功能完全重复、可以直接删除的测试文件。

它们分别覆盖：

- 提词代理
- 嵌入服务
- 空房间启动
- LLM 设置
- 长期存储连接
- 向量索引重建
- 向量存储召回
- memory pipeline 验证工具

如果后续要继续整理，比较适合做的是“按模块合并命名”，而不是简单删除。
