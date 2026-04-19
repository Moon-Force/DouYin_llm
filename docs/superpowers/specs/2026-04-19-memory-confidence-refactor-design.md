# 观众记忆置信度重构设计

日期：2026-04-19

## 目标

把当前“单一、偏机械”的 `confidence` 打分，升级为“多维质量评分 + 生命周期动态更新”的机制，让记忆置信度更接近真实业务价值，而不是长度、类型或表面关键词的近似分。

本次设计主要解决三件事：

- 让 `confidence` 更真实反映长期稳定性和提词价值
- 让记忆在 `merge / upgrade / supersede` 后能动态更新分数
- 让召回排序和人工纠偏可以使用更细粒度的质量信号

## 背景

当前系统已经具备：

- LLM 记忆抽取
- `memory_text_raw / memory_text_canonical`
- `memory_type / polarity / temporal_scope`
- 保存前 `create / merge / upgrade / supersede`
- `evidence_count / first_confirmed_at / last_confirmed_at / superseded_by`

但当前 `confidence` 仍然比较粗糙：

- LLM 路径主要按 `memory_type` 给固定分
- 规则路径主要按长度、关键词和第一人称等表面特征给分
- `merge / upgrade / supersede` 虽然已经接入，但分数还没有真正随记忆生命周期变化

这会导致几个问题：

1. 高价值记忆和低价值记忆可能分数接近  
   例如“不能吃辣”与“今天刚下班看到你直播”在业务价值上差很多，但当前机制不一定能拉开。

2. 多次确认的记忆缺少持续增信  
   一条被多次说到、被不同评论反复证实的记忆，理论上应该比只出现过一次的记忆更可信。

3. 召回排序无法充分利用真实质量  
   现在召回排序更多依赖语义分和少量元数据，`confidence` 还不够有解释力。

## 非目标

本次不做以下内容：

- 不让 LLM 直接输出最终浮点 `confidence`
- 不引入 reinforcement learning 或线上点击学习
- 不调整现有向量检索主算法
- 不实现长期/短期双池存储
- 不接入礼物、回访、复购等新记忆源

## 方案比较

### 方案一：继续用单一总分，但改规则

做法：

- 保留 `confidence` 一个字段
- 用更复杂的规则直接输出新总分

优点：

- 改动最小
- 兼容现有接口

缺点：

- 可解释性弱
- 后续想分析“为什么高分/低分”很难
- 很容易再次演化成新的“大杂烩规则”

### 方案二：引入多维子分，再合成为总分

做法：

- 新增多维评分：
  - `stability_score`
  - `interaction_value_score`
  - `clarity_score`
  - `evidence_score`
- `confidence` 变成这些子分的加权和

优点：

- 可解释
- 易调权重
- 易扩展到召回 rerank

缺点：

- 要补字段和计算逻辑
- 需要给每一维单独设计规则

### 方案三：LLM 输出结构化质量标签

做法：

- LLM 除抽取字段外，再输出：
  - `stability=high/medium/low`
  - `interaction_value=high/medium/low`
  - `clarity=high/medium/low`
- 后端映射成分数

优点：

- 对复杂自然语言边界更有潜力

缺点：

- 增加 prompt 和推理复杂度
- 第一版不够稳
- 难以和现有测试体系快速闭环

### 推荐方案

采用方案二：多维子分 + 后端合成总分。

原因：

- 能明显提高可解释性
- 不引入额外模型依赖
- 最适合当前已经存在的 `merge / evidence_count / last_confirmed_at` 元数据
- 后续如果要接入 LLM 结构化质量标签，也可以平滑演进

## 总体设计

`confidence` 不再被视为“创建时一次性算出的静态分数”，而是记忆对象在生命周期中的一个动态结果。

引入四个子分：

1. `stability_score`
2. `interaction_value_score`
3. `clarity_score`
4. `evidence_score`

最终：

```text
confidence =
0.35 * stability_score +
0.35 * interaction_value_score +
0.15 * clarity_score +
0.15 * evidence_score
```

第一版取值范围统一为 `0.0 ~ 1.0`。

## 一、四个子分定义

### 1. `stability_score`

定义：

- 这条信息像不像长期稳定事实、长期偏好或稳定背景

高分例子：

- `不太能吃辣`
- `租房住在公司附近`
- `一直都只用安卓手机`

低分例子：

- `这周都在上海出差`
- `今天刚下班`
- `最近在加班`

第一版信号：

- `temporal_scope=long_term` 基础高分
- 含明显短期词降分
- 偏好/稳定背景/长期事实高于短期状态

### 2. `interaction_value_score`

定义：

- 这条记忆未来是否真的有助于主播接话、推荐、避雷或识别关系

高分例子：

- `不太能吃辣`
- `喜欢豚骨拉面`
- `家里养了两只猫`
- `住公司附近`

低分例子：

- `今天路过看到你直播`
- `刚刚下班`
- `最近挺忙`

第一版信号：

- 明显可用于推荐、追问、关系延续的信息给高分
- 弱复用、弱个性化、弱长期价值的信息给低分

### 3. `clarity_score`

定义：

- `memory_text_canonical` 是否短、清晰、可复用、没有壳子污染

高分例子：

- `不太能吃辣`
- `租房住在公司附近`

低分例子：

- `我其实平时吧都不太能吃辣`
- `是不是不太能吃辣啊`
- 过长整句、互动句、问句壳子残留

第一版信号：

- canonical 长度适中加分
- 问句、口头语、互动壳子降分
- 原句整存倾向降分

### 4. `evidence_score`

定义：

- 这条记忆是否被反复确认过，最近是否仍被证实

高分例子：

- `evidence_count >= 3`
- `last_confirmed_at` 很新

低分例子：

- 只出现过一次
- 很久未再确认

第一版信号：

- `evidence_count`
- `last_confirmed_at`
- `merge / upgrade` 后增信

## 二、存储设计

### 1. `viewer_memories` 新增字段

建议新增：

- `stability_score`
- `interaction_value_score`
- `clarity_score`
- `evidence_score`

并保留现有：

- `confidence`

关系：

- `confidence` 为对外兼容字段
- 四个子分用于解释、排序和后续调参

### 2. 默认值

新增字段默认值统一为 `0.0`，避免老数据迁移出错。

## 三、创建时评分

### 1. 创建入口

在 `save_viewer_memory()` 之前或内部统一计算初始评分。

建议新增一个服务：

- `backend/services/memory_confidence_service.py`

接口示意：

```python
class MemoryConfidenceService:
    def score_new_memory(self, candidate: dict) -> dict:
        return {
            "stability_score": ...,
            "interaction_value_score": ...,
            "clarity_score": ...,
            "evidence_score": ...,
            "confidence": ...,
        }
```

### 2. 第一版规则

#### `stability_score`

- `temporal_scope=long_term`：高基础分
- 包含明显短期词：降分
- `context / fact / preference` 均可高分，但 preference 在稳定表达时略高

#### `interaction_value_score`

- 饮食限制、偏好、职业、居住、宠物、设备选择：高分
- 弱复用背景、低互动价值生活流水：低分

#### `clarity_score`

- canonical 长度在合理区间：加分
- 过长：降分
- 问句或互动壳子：显著降分

#### `evidence_score`

- 初次创建默认中低分，例如 `0.35`

## 四、生命周期动态更新

### 1. `merge`

行为：

- `evidence_count += 1`
- `last_confirmed_at = now`
- 提升 `evidence_score`
- 重新计算总分

### 2. `upgrade`

行为：

- 更新 canonical
- 提升 `clarity_score`
- `evidence_score` 也同步上升
- 重新计算总分

### 3. `supersede`

行为：

- 旧记忆失效，不再参与召回
- 新记忆按“新建记忆”重新评分
- 旧记忆保留原分用于审计，但退出线上主链路

### 4. 长期衰减

第一版不做自动衰减任务，但保留规则接口。

后续可基于：

- `last_confirmed_at`
- `updated_at`

对 `evidence_score` 或总分做轻微衰减。

## 五、召回与排序使用方式

当前 `similar_memories()` 已经会参考：

- `confidence`
- `recall_count`
- `source_kind`
- `is_pinned`

改造后建议：

- `confidence` 继续参与排序
- 后续可单独引入：
  - `interaction_value_score`
  - `evidence_score`

做更细粒度 rerank

第一版不强制改 `VectorMemory` 排序逻辑，只先把更真实的 `confidence` 算出来。

## 六、测试设计

### 1. 单测

需要覆盖：

- 长期稳定偏好的 `stability_score` 高于短期状态
- 高互动价值记忆的 `interaction_value_score` 高于流水句
- 更短更清晰 canonical 的 `clarity_score` 更高
- `merge` 后 `evidence_score` 增长
- `upgrade` 后 `clarity_score` 增长

### 2. 存储层测试

需要覆盖：

- 新评分字段迁移默认值正确
- 创建时四个子分和总分正确落库
- `merge / upgrade` 后分数被刷新

### 3. 评测扩展

离线评测建议新增统计：

- 高价值记忆平均分
- 低价值记忆平均分
- 长期/短期样本分布差异
- canonical 清晰度相关指标

## 七、验收标准

完成后应满足：

1. `confidence` 不再只是类型映射或表面规则分
2. 记忆在 `merge / upgrade` 后分数会动态更新
3. 高稳定、高提词价值记忆整体分数显著高于低价值流水句
4. 评分可解释，能拆成至少四个子分观察
5. 现有召回链路兼容，不需要一次性大改排序算法

## 八、文件影响范围

预期会修改：

- [backend/memory/long_term.py](H:\DouYin_llm\backend\memory\long_term.py)
- [backend/services/llm_memory_extractor.py](H:\DouYin_llm\backend\services\llm_memory_extractor.py)
- [backend/services/memory_extractor.py](H:\DouYin_llm\backend\services\memory_extractor.py)
- [backend/services/memory_merge_service.py](H:\DouYin_llm\backend\services\memory_merge_service.py)
- [backend/memory/vector_store.py](H:\DouYin_llm\backend\memory\vector_store.py)
- [backend/schemas/live.py](H:\DouYin_llm\backend\schemas\live.py)

预期会新增：

- [backend/services/memory_confidence_service.py](H:\DouYin_llm\backend\services\memory_confidence_service.py)
- [tests/test_memory_confidence_service.py](H:\DouYin_llm\tests\test_memory_confidence_service.py)

## 九、推荐实施顺序

1. 先补四个子分字段和迁移
2. 再实现 `memory_confidence_service`
3. 再接入新建记忆评分
4. 再接入 `merge / upgrade` 动态更新
5. 最后补测试和离线评测指标
