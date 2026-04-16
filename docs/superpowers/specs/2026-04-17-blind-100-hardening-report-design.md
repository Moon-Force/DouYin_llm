# blind_100 难度升级与 Markdown 全量报告设计

日期：2026-04-17

## 背景

当前仓库已经有 `tests/fixtures/semantic_recall/blind_100.json`，并且 `tests.memory_pipeline_verifier.runner` 支持通过：

```bash
python -u -m tests.memory_pipeline_verifier.runner --mode internal --task semantic-recall --dataset tests/fixtures/semantic_recall/blind_100.json
```

直接跑出 `top1/top3` 结果。

现阶段存在两个不足：

1. `blind_100` 每条 case 的 `memory_texts` 只有 4 条，单个 viewer 的记忆池偏浅，误召压力还不够大。
2. 评测结果主要在终端输出，不利于逐条检查每个 case 的召回表现，也不方便后续留档对比。

因此需要在不改变数据集名称的前提下，直接升级现有 `blind_100.json` 的难度，并让现有语义召回命令在运行后自动产出一份可读的 Markdown 全量报告。

## 目标

本次改动要实现以下目标：

1. 直接升级 `tests/fixtures/semantic_recall/blind_100.json`。
2. 保持 `100` 条 case 和现有 5 类标签结构不变。
3. 把每条 case 的 `memory_texts` 提升到 `10` 条。
4. 新增的记忆要优先构造成高相似干扰项，提升“不能召错”的难度。
5. 继续复用现有 `semantic-recall` 命令，不新增新的必填命令参数。
6. 命令执行后自动生成一份 Markdown 报告。
7. 报告需要包含每一条 case 的完整召回明细，而不是只给摘要。

## 非目标

本次不做以下工作：

1. 不修改生产环境的真实召回服务逻辑。
2. 不新增前端展示。
3. 不要求本次同时输出 JSON 报告。
4. 不扩展新的评测任务类型，仍然只在 `semantic-recall` 下工作。
5. 不修改 `blind_100.json` 之外的评测集命名策略。

## 设计原则

1. 继续保持一条命令即可运行评测并查看结果。
2. 优先提升“同一 viewer 内部高相似记忆竞争”的误召难度，而不是只靠增加 case 数量制造难度。
3. 保留现有 `label` / `tags` / `query` / `expected_memory_text` schema，避免破坏已有数据加载逻辑。
4. 报告输出要固定、可重复定位，便于多次对比。
5. 报告既要有摘要，也要有全量 case 明细，但以全量明细为主体。

## 数据集升级设计

### 数据文件

继续使用：

```text
tests/fixtures/semantic_recall/blind_100.json
```

不新增平行版本文件，不保留旧版 blind_100 作为默认对照。

### 样本规模

保持：

1. 总量 `100` 条。
2. `5` 个标签类别，每类 `20` 条。

类别仍为：

1. `["typo"]`
2. `["spoken"]`
3. `["fragment"]`
4. `["typo", "spoken", "fragment", "mixed_noise"]`
5. `["distractor"]`

### 单条 case 结构要求

每条 case 保持现有 schema：

```json
{
  "label": "blind-001",
  "tags": ["typo"],
  "room_id": "semantic-blind-room",
  "viewer_id": "id:semantic-blind-viewer-001",
  "memory_texts": [
    "... 共 10 条 ..."
  ],
  "query": "...",
  "expected_memory_text": "..."
}
```

新增约束：

1. `memory_texts` 必须达到 `10` 条。
2. `expected_memory_text` 必须仍然出现在 `memory_texts` 中。
3. `query` 不允许与 `expected_memory_text` 完全相同。
4. 10 条记忆里至少要有多条与目标记忆主题非常接近的干扰项。

### 难度提升方式

本次难度提升的核心是“同一个 viewer 的记忆池更深、干扰更近”。

对每条 case：

1. 原有目标记忆保留。
2. 原有 3 条干扰项保留或重写。
3. 再补充 6 条新干扰项，把总数拉到 10。
4. 新干扰项应尽量围绕同一主题、同一时间、同一生活域或同一偏好域构造。

示例：

如果目标是“我在杭州做前端开发，最近连续两周都在加班赶需求”，新增干扰项不应该是无关宠物或饮食，而应优先使用类似：

1. “我最近在赶一个移动端重构项目，这两周经常改到半夜。”
2. “我们组这个月一直在冲版本，晚上开会和改页面都特别频繁。”
3. “我白天写后台联调，晚上还得补前端交互细节。”

这样测试的重点会从“能不能大致召回同类话题”提升为“能不能在多个相似选项里召对目标”。

## 报告输出设计

### 输出方式

继续使用现有 `semantic-recall` 命令，不新增新的必填参数。

运行结束后，除了终端摘要外，自动落一份 Markdown 报告。

### 输出路径

建议固定输出到：

```text
artifacts/semantic_recall_reports/blind_100.md
```

如果后续传入别的数据集，则可按数据集文件名派生输出名；本次只要求 `blind_100.json` 路径稳定可预期。

### 报告内容

报告至少包含以下 3 个部分：

#### 1. 总体摘要

展示：

1. 数据集路径
2. case 总数
3. memory 总数
4. `top1`
5. `top3`
6. `top1_rate`
7. `top3_rate`
8. 生成时间

#### 2. 标签维度摘要

按 `tags` 组合做小结，展示每类：

1. case 数
2. top1 命中数
3. top3 命中数
4. top1_rate
5. top3_rate

#### 3. 全量 case 明细

每条 case 都展开，至少包含：

1. `label`
2. `tags`
3. `query`
4. `expected_memory_text`
5. 实际召回的 `top3 memory_texts`
6. 是否命中 `top1`
7. 是否命中 `top3`
8. 若未命中 `top1`，要能看出第一名错召到了什么
9. 若未命中 `top3`，要明确标记为严重失败

建议每条 case 使用 Markdown 小节，例如：

```markdown
## blind-001

- Tags: typo
- Query: 最近写页面经常熬页赶进度
- Expected: 我在杭州做前端开发，最近连续两周都在加班赶需求。
- Top1 Hit: yes
- Top3 Hit: yes

Top 3:
1. 我在杭州做前端开发，最近连续两周都在加班赶需求。
2. 我最近在赶一个移动端重构项目，这两周经常改到半夜。
3. 我们组这个月一直在冲版本，晚上开会和改页面都特别频繁。
```

## Runner 改造设计

### 总体思路

`run_semantic_recall_verification` 目前已经能：

1. 加载数据集
2. 建索引
3. 执行召回
4. 输出 `StepResult`

本次在不破坏其现有终端行为的前提下，补充一个内部“语义评测结果对象”。

建议流程：

1. 对每个 case 生成结构化结果记录。
2. 先基于结构化结果统计整体 `top1/top3`。
3. 再基于同一份结果渲染 Markdown 报告。
4. 终端摘要继续沿用现有 `StepResult`。

### 结构化结果字段

每条 case 的内部结果建议至少包含：

1. `label`
2. `tags`
3. `query`
4. `expected_memory_text`
5. `top_texts`
6. `top1_hit`
7. `top3_hit`

整次运行的结果建议包含：

1. `dataset_path`
2. `total_cases`
3. `total_memories`
4. `top1_hits`
5. `top3_hits`
6. `per_tag_summary`
7. `case_results`
8. `report_path`

这样一来，后面即使用户又想要 JSON 报告或前端展示，也不需要重写核心统计逻辑。

## 文件改动范围

预计涉及：

1. `tests/fixtures/semantic_recall/blind_100.json`
   - 升级为每条 10 条记忆的更难版本。
2. `tests/memory_pipeline_verifier/runner.py`
   - 增加结构化结果收集与 Markdown 报告写出。
3. `tests/test_verify_memory_pipeline.py`
   - 更新数据约束测试，并增加报告生成测试。

如有必要，可新增一个小的渲染辅助函数，但优先放在现有 `runner.py` 内部，避免本次过度拆分。

## 测试策略

### 数据约束测试

更新 `tests/test_verify_memory_pipeline.py`，至少校验：

1. `blind_100.json` 至少有 `100` 条。
2. `label` 唯一。
3. 每条 `tags` 非空。
4. 每条 `memory_texts` 至少 `10` 条。
5. `expected_memory_text` 在 `memory_texts` 中。
6. `query` 不直接等于 `expected_memory_text`。
7. `5` 类标签仍然各 `20` 条。

### 报告生成测试

新增最小必要覆盖：

1. 运行语义评测后会返回或记录报告路径。
2. 报告文件成功写出。
3. 报告文本包含摘要标题。
4. 报告文本包含至少一个 case 明细标题，例如 `## blind-001`。
5. 报告文本包含 `Top1 Hit` / `Top3 Hit` 之类的字段。

### 端到端验证

至少运行：

```bash
python -m unittest tests.test_verify_memory_pipeline -v
python -u -m tests.memory_pipeline_verifier.runner --mode internal --task semantic-recall --dataset tests/fixtures/semantic_recall/blind_100.json
```

验收时不仅看命令退出成功，也要确认 Markdown 报告文件真实生成。

## 风险与缓解

### 风险 1：数据集变难后分数大幅下降

这是预期风险，不应把“分数下降”直接当成数据集有问题。

缓解：

1. 报告里保留每条 case 的 `top3` 明细，便于看出是“完全没理解”还是“被相似干扰项压住了”。
2. 报告里加入标签维度小结，帮助定位最脆弱的类别。

### 风险 2：报告只有文本堆砌，不方便看

缓解：

1. 先给总体摘要。
2. 再给标签摘要。
3. 最后给全量 case 明细，顺序从整体到局部。

### 风险 3：一次性把 100 条 x 10 记忆都手工改写，容易引入重复或低质量干扰

缓解：

1. 尽量基于现有 `hard.json` 与 `blind_100.json` 的主题骨架扩展。
2. 测试里先卡住结构合法性。
3. 报告生成后，先人工 spot check 若干失败 case，确认难度是真难而不是脏数据误伤。

## 验收标准

满足以下条件即可视为本次完成：

1. `blind_100.json` 已被直接升级，而不是新增平行文件。
2. 每条 case 的 `memory_texts` 达到 `10` 条。
3. 现有 `semantic-recall` 命令仍可直接运行。
4. 命令运行后会生成固定路径的 Markdown 报告。
5. 报告包含总体摘要、标签摘要和全量 case 明细。
6. `tests.test_verify_memory_pipeline` 通过。
7. 使用 `blind_100.json` 跑正式命令时，评测和报告生成都成功完成。
