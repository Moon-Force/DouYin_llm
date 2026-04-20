# 提词价值驱动的观众记忆排序设计

日期：2026-04-20

## 目标

把当前观众记忆召回从“语义相似度 + 少量权重修正”升级成“围绕提词价值的 feature rerank”，让真正对主播接话有帮助的记忆稳定排在前面。

本次设计优先解决三件事：

- 让高提词价值的记忆优先于普通背景记忆
- 让多次确认、人工确认、近期再次证实的记忆更容易靠前
- 在不引入新 rerank 模型的前提下，把现有质量信号吃满

## 背景

当前系统已经具备：

- 语义向量召回
- `confidence`
- `interaction_value_score`
- `evidence_score`
- `stability_score`
- 时间衰减
- `source_kind`
- `is_pinned`

当前 `VectorMemory._memory_rank_key()` 已经开始使用其中一部分信号做排序，但还存在两个问题：

1. 业务排序信号利用不充分  
   目前更多是在“相似度附近做少量修正”，而不是明确围绕“对主播接话有没有帮助”排序。

2. 不同类型记忆没有更明确的排序意图  
   例如“不能吃辣”与“刚下班路过看到你直播”，在提词价值上差距很大，但在当前排序逻辑里这种差距还不够稳定。

## 非目标

本次不做以下内容：

- 不引入新的 reranker model
- 不增加第二次 LLM 重排
- 不改向量召回主检索算法
- 不引入复杂在线学习或点击反馈闭环
- 不做前端排序解释 UI

## 方案比较

### 方案一：继续小修补当前 `_memory_rank_key`

做法：

- 在现有公式上继续加几个系数

优点：

- 改动最小

缺点：

- 容易继续堆成“经验公式”
- 不够结构化

### 方案二：明确拆成召回分 + 业务重排分

做法：

- 保留向量召回结果作为 `semantic_score`
- 再计算一个 `business_rerank_score`
- 最终组合成 `final_score`

优点：

- 结构更清晰
- 便于后续调试和扩展

缺点：

- 要补一层明确的 feature 设计

### 方案三：专门上 reranker model

优点：

- 语义排序潜力高

缺点：

- 推理成本高
- 可解释性差
- 在当前数据规模和链路复杂度下不划算

### 推荐方案

采用方案二：召回分 + 业务重排分。

原因：

- 现有信号已经足够支撑一版高质量 feature rerank
- 不需要额外模型
- 可解释性、可调试性最好

## 总体设计

当前流程保持：

1. 向量检索得到候选记忆
2. 对候选记忆做 business rerank
3. 输出 top-k 给建议生成

新增一个更明确的排序结构：

```text
final_score =
0.55 * semantic_score +
0.45 * business_rerank_score
```

其中：

- `semantic_score`：当前向量相似度转换分数
- `business_rerank_score`：由业务特征计算

## 一、业务重排分组成

### 1. `interaction_value_score`

定义：

- 这条记忆对主播未来接话、追问、推荐、避雷的直接帮助程度

排序作用：

- 权重最高

### 2. `evidence_score`

定义：

- 是否被多次确认、最近是否还被证实

排序作用：

- 防止一次性样本压过反复确认的稳定记忆

### 3. `stability_score`

定义：

- 是否像长期稳定事实/偏好

排序作用：

- 长期稳定画像优先于弱时效背景

### 4. `source_kind`

定义：

- `manual` 还是 `auto`

排序作用：

- 人工确认过的内容更可信

### 5. `is_pinned`

定义：

- 是否被人工置顶

排序作用：

- 在业务上保留最高优先级

### 6. `recall_count`

定义：

- 是否已经被系统稳定反复召回过

排序作用：

- 作为弱增益，不喧宾夺主

### 7. `time_decay`

定义：

- 旧记忆在仍未过期的前提下自然降权

排序作用：

- 避免老记忆长期霸榜

## 二、排序公式

### 1. 业务分

建议第一版：

```text
business_rerank_score =
0.35 * interaction_value_score +
0.20 * evidence_score +
0.15 * stability_score +
0.10 * confidence +
0.08 * manual_bonus +
0.07 * pin_bonus +
0.05 * recall_bonus
```

说明：

- `manual_bonus`：`source_kind == manual` 时为 1，否则 0
- `pin_bonus`：`is_pinned` 时为 1，否则 0
- `recall_bonus`：基于 `recall_count` 的 capped score

### 2. 最终分

建议第一版：

```text
final_score =
0.55 * semantic_score +
0.45 * business_rerank_score
```

### 3. 过期与失效优先过滤

在打分前先过滤：

- `status != active`
- `is_expired == true`

也就是说：

- 失效/删除/过期记忆不进入 rerank 阶段

## 三、排序意图

这次排序的目标不是“最像 query 的句子”，而是“最值得主播此刻拿来接话的记忆”。

因此优先顺序应大致体现为：

1. 语义相关且高互动价值的长期偏好/限制
2. 语义相关且被多次确认的稳定背景
3. 语义相关但互动价值一般的背景事实
4. 时效弱、价值弱、证据少的普通背景

## 四、实现落点

主要修改：

- [backend/memory/vector_store.py](H:\DouYin_llm\backend\memory\vector_store.py)

建议把当前 `_memory_rank_key()` 重构成更清晰的内部方法：

- `_semantic_score()`
- `_business_rerank_score()`
- `_final_rank_key()`

这样后续更容易调参与单测。

## 五、测试设计

### 1. 向量排序测试

需要覆盖：

- 相同语义分下，高 `interaction_value_score` 排前
- 相同语义分下，高 `evidence_score` 排前
- `manual` 记忆优先于 `auto`
- `pinned` 记忆优先于普通记忆
- 时间衰减会让旧记忆自然降权

### 2. 回归测试

需要覆盖：

- 不破坏 strict mode 逻辑
- 不破坏 fallback token-match 逻辑
- 不让过期记忆重新回到排序链路

## 六、验收标准

完成后应满足：

1. 高互动价值记忆稳定排在普通背景前
2. 多次确认的记忆稳定排在一次性样本前
3. 人工确认与置顶信号可稳定影响排序
4. 排序逻辑保持可解释，不依赖新模型
5. 现有语义召回能力不被削弱

## 七、文件影响范围

预期会修改：

- [backend/memory/vector_store.py](H:\DouYin_llm\backend\memory\vector_store.py)
- [tests/test_vector_store.py](H:\DouYin_llm\tests\test_vector_store.py)

必要时可补：

- [README.md](H:\DouYin_llm\README.md)

## 八、推荐实施顺序

1. 先把 `_memory_rank_key()` 重构成语义分/业务分/最终分
2. 再补排序测试
3. 再调权重到一版稳定值
4. 最后补 README 说明
