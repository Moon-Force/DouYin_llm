# 100 条混合脏输入盲测集设计

日期：2026-04-17

## 背景

当前项目已经具备语义召回评测能力，并且仓库里已有基础集 `default.json` 与混合困难集 `hard.json`。这些评测集可以证明当前实现在线性、干净表达和中等复杂干扰条件下的召回能力，但仍然不足以代表真实直播评论场景。

真实直播评论常见的问题包括：

1. 错别字、近音字、漏字。
2. 口语化表达和直播腔。
3. 半句、碎片化、主语省略。
4. 一条评论同时混合噪声与干扰信息。
5. 多条相似记忆并存时容易召错。

因此需要一份更残酷、更接近真实输入分布的盲测数据集，用于评估系统在噪声条件下的稳健性。

## 目标

新增一份 `100` 条的“混合式盲测脏数据集”，保持与现有语义评测命令兼容，让它可以直接通过已有命令运行并输出 `top1/top3`。

## 非目标

本次不做以下工作：

1. 不修改生产召回逻辑。
2. 不修改 runner 的统计结构去按标签自动分组汇总。
3. 不引入新的命令参数。
4. 不新增前端展示。

## 设计原则

1. 保持与现有 `semantic-recall` 数据格式兼容。
2. 优先通过数据集设计体现难度，不靠修改评测代码制造复杂性。
3. 为后续扩展保留分析空间，因此允许每条样本带 `tags` 字段。

## 数据文件设计

新增文件：

```text
tests/fixtures/semantic_recall/blind_100.json
```

保留现有文件：

```text
tests/fixtures/semantic_recall/default.json
tests/fixtures/semantic_recall/hard.json
```

## 数据结构

在现有语义召回 case schema 基础上，增加一个可选字段 `tags`：

```json
{
  "label": "blind-001",
  "tags": ["typo", "spoken", "fragment"],
  "room_id": "semantic-blind-room",
  "viewer_id": "id:semantic-blind-viewer-001",
  "memory_texts": [
    "我乳糖不耐，喝牛奶就容易肚子不舒服。",
    "我早饭一般只喝美式咖啡，不怎么吃甜的。",
    "我最近在减脂，晚饭尽量不吃米饭和面。",
    "我喜欢吃重辣火锅，但是一点都不吃香菜。"
  ],
  "query": "喝牛乃就容易胃不苏服",
  "expected_memory_text": "我乳糖不耐，喝牛奶就容易肚子不舒服。"
}
```

字段要求：

1. `label`：唯一。
2. `tags`：可选，但本次盲测集每条都应填写，便于后续人工分析。
3. `room_id`：可复用统一房间，例如 `semantic-blind-room`。
4. `viewer_id`：稳定唯一。
5. `memory_texts`：至少 `4` 条。
6. `expected_memory_text`：必须出现在 `memory_texts` 中。

## 100 条样本分层

总量：`100` 条。

分成 `5` 类，每类 `20` 条：

### 1. 错别字 / 近音字

标签示例：

```json
["typo"]
```

特点：

1. 查询中故意引入轻度错别字。
2. 不改变核心语义。
3. 保证仍是人类评论里会真实出现的错误，不做离谱乱码。

### 2. 口语化 / 直播腔

标签示例：

```json
["spoken"]
```

特点：

1. 使用“就那个”“反正”“就是那种”之类口语。
2. 含语气词，但核心语义要保留。
3. 不能退化成完全没信息的废话。

### 3. 半句 / 省略主语

标签示例：

```json
["fragment"]
```

特点：

1. 省略主语或宾语。
2. 评论像真实直播弹幕一样短。
3. 仍能唯一指向目标记忆。

### 4. 多噪声混合

标签示例：

```json
["typo", "spoken", "fragment", "mixed_noise"]
```

特点：

1. 一条 query 同时包含错别字、口语和省略。
2. 难度接近真实脏输入。

### 5. 强干扰竞争

标签示例：

```json
["distractor"]
```

特点：

1. `memory_texts` 中至少有 `2` 条高相似干扰项。
2. 测试点不只是“能召回”，而是“不能召错”。

## 样本约束

每条 case 必须满足：

1. `memory_texts` 至少 `4` 条。
2. 至少 `2` 条干扰项与目标记忆足够接近。
3. `query` 不允许直接复制 `expected_memory_text`。
4. `expected_memory_text` 必须唯一成立。
5. `label` 全集唯一。
6. `tags` 至少一个。

## 实现方式

本次只新增数据和最小校验测试，不修改现有 runner 逻辑。

原因：

1. 现有 runner 已可通过 `--dataset` 切换测试集。
2. 盲测目标是先拿到真实分数，不是先扩工具复杂度。
3. `tags` 可以先用于人工分析，等确有必要再做按标签汇总。

## 测试策略

在 `tests/test_verify_memory_pipeline.py` 中增加最少必要断言：

1. `blind_100.json` 至少有 `100` 条。
2. `label` 唯一。
3. `tags` 存在且非空。
4. 每条 `memory_texts` 至少 `4` 条。
5. `expected_memory_text` 在 `memory_texts` 中。

验证命令：

```bash
python -m unittest tests.test_verify_memory_pipeline -v
python -u -m tests.memory_pipeline_verifier.runner --mode internal --task semantic-recall --dataset tests/fixtures/semantic_recall/blind_100.json
```

## 风险与缓解

风险一：100 条全是“手工顺着系统能力写”的伪困难集。

缓解：

1. 引入更多自然错字、碎片、直播腔。
2. 保证每类至少 20 条，避免只靠少数模式凑分。

风险二：只看总 `top1/top3` 不足以解释薄弱点。

缓解：

1. 每条补充 `tags`。
2. 本次先不改 runner，后续需要时可基于 `tags` 做分组统计。

## 验收标准

满足以下条件即可认为本次设计落地完成：

1. 仓库新增 `tests/fixtures/semantic_recall/blind_100.json`。
2. 数据集规模达到 `100` 条。
3. 保持兼容现有 `semantic-recall` 命令。
4. 基础合法性测试通过。
5. 能通过已有命令直接跑出盲测集的 `top1/top3` 结果。
