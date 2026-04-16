# 语义召回评测集固化设计

日期：2026-04-16

## 背景

当前项目已经有 `verify_memory_pipeline` 验证入口，可覆盖评论抽取、落库、向量索引和按观众回查的主链路。但现有批量验证主要是“原文回查”或“单观众单条记忆”场景，无法稳定衡量“同一观众存在多条记忆时，改写问法能否召回正确记忆”的真实语义质量。

这会带来两个问题：

1. 工程链路可能全部通过，但语义召回质量仍然不足。
2. 后续切换测试集或扩充样本时，需要临时写脚本，缺少统一入口。

## 目标

把“语义召回评测集”正式固化到仓库，并接入现有 `verify_memory_pipeline` 命令，使其可以直接输出 `top1/top3` 指标，且后续切换测试集时只需替换数据文件。

## 非目标

本次不做以下事情：

1. 不修改生产召回策略本身。
2. 不引入复杂插件系统或注册中心。
3. 不把所有验证逻辑完全重构为通用框架。

## 方案概览

在现有 `tests.memory_pipeline_verifier.runner` 中新增任务分发能力，保留原有 `pipeline` 验证逻辑，并增加 `semantic-recall` 任务。语义评测集使用独立 JSON fixture 存放，每条样本描述“同一观众已有的候选记忆、多义改写查询、期望命中的目标记忆”。运行命令时由 runner 读取 fixture，构造临时 SQLite 与临时 Chroma 索引，执行召回并统计 `top1/top3`。

## 命令设计

继续沿用现有命令入口：

```bash
python -m tests.memory_pipeline_verifier.runner --mode internal --task pipeline
python -m tests.memory_pipeline_verifier.runner --mode internal --task semantic-recall --dataset tests/fixtures/semantic_recall/default.json
```

命令约束：

1. `--task` 默认值为 `pipeline`，保证现有行为不变。
2. `--task semantic-recall` 时要求提供 `--dataset`。
3. `--mode e2e` 仅支持既有链路验证；语义评测先限定在 `internal`。

## 数据集设计

新增目录：

```text
tests/fixtures/semantic_recall/
```

默认数据集文件：

```text
tests/fixtures/semantic_recall/default.json
```

单条样本结构：

```json
{
  "label": "工作熬夜",
  "room_id": "semantic-eval-room",
  "viewer_id": "id:semantic-eval-viewer-001",
  "memory_texts": [
    "我在杭州做前端开发，最近连续两周都在加班赶需求。",
    "我周末常去西湖边夜跑，一次差不多十公里。",
    "我皮肤偏干，换季的时候脸上很容易起皮。"
  ],
  "query": "最近写页面经常熬夜赶进度",
  "expected_memory_text": "我在杭州做前端开发，最近连续两周都在加班赶需求。"
}
```

字段要求：

1. `label`：样本标签，便于输出失败案例。
2. `room_id`：可选；未提供时使用默认房间。
3. `viewer_id`：可选；未提供时使用按索引生成的稳定观众 ID。
4. `memory_texts`：该观众已存在的多条记忆。
5. `query`：用于召回的改写问法。
6. `expected_memory_text`：期望在结果中命中的记忆文本，必须出现在 `memory_texts` 中。

## Runner 改造

在 `runner.py` 中新增以下职责：

1. `parse_args()` 增加 `--task` 参数。
2. 增加 `normalize_task()`，统一校验合法任务。
3. 新增 `run_semantic_recall_verification(dataset_path)`。
4. `main()` 根据 `mode + task` 分发。

`run_semantic_recall_verification()` 的执行流程：

1. 读取 JSON fixture。
2. 校验样本格式。
3. 为每条样本创建独立观众记忆集合。
4. 使用真实 `EmbeddingService` + `VectorMemory` 建立索引。
5. 调用 `similar_memories(query, room_id, viewer_id, limit=3)`。
6. 统计：
   - `cases`
   - `top1_hits`
   - `top3_hits`
   - `top1_rate`
   - `top3_rate`
7. 收集有限数量的失败案例并打印，便于人工排查。

## 输出设计

继续沿用 `StepResult` 风格，新增以下步骤：

1. `dataset`
2. `index_memories`
3. `semantic_recall`

`semantic_recall.details` 格式：

```text
cases=15 top1=1/15 top3=4/15 top1_rate=0.0667 top3_rate=0.2667
```

若存在失败样本，控制台额外打印简短失败案例，包含：

1. `label`
2. `query`
3. `expected_memory_text`
4. `top_texts`

## 测试策略

先补测试，再写实现。

新增或扩展测试覆盖：

1. `parse_args` 能解析 `--task semantic-recall`。
2. `normalize_task` 能限制合法值。
3. 语义评测能正确统计 `top1/top3`。
4. 缺少 `--dataset` 时，语义评测会明确失败。
5. 默认不带 `--task` 时，仍走原有 `pipeline` 流程。
6. 数据集加载与样本格式校验可被单测覆盖。

## 兼容性

该设计是增量扩展：

1. 默认命令行为不变。
2. 原有 `internal/e2e` 代码路径继续保留。
3. 后续新增测试集只需增加 JSON 文件，不需要改动 runner 主逻辑。

## 风险与缓解

风险一：语义评测运行较慢。

缓解：

1. 默认数据集规模控制在可接受范围。
2. 优先复用批量建索引而非逐条即时写入。

风险二：Windows 下临时 Chroma 目录可能清理不及时。

缓解：

1. 评测继续使用临时目录隔离真实数据。
2. 后续若句柄问题持续，再单独补充资源释放修复。

## 验收标准

满足以下条件即可认为本功能完成：

1. 仓库内存在正式语义评测集 fixture。
2. `verify_memory_pipeline` 可通过 `--task semantic-recall --dataset <path>` 直接运行。
3. 命令输出包含 `top1/top3` 指标。
4. 可以通过替换 dataset 路径切换测试集。
5. 原有 pipeline 验证命令不回归。
