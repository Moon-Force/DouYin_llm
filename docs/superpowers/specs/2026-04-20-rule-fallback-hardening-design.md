# 观众记忆规则兜底质量提升设计

日期：2026-04-20

## 目标

在不改变“规则兜底只在 LLM 异常时触发”这个前提下，提升规则兜底产物质量，避免 LLM 异常期间把明显粗糙、整句原样或互动壳子过重的内容直接写入长期记忆池。

本次设计主要解决四件事：

- 扩充高置信规则模板，但保持兜底范围可控
- 给规则兜底补一个保守版 canonical 提纯层
- 给规则兜底补更合理的默认 `polarity / clarity / confidence`
- 用测试把“仅异常时兜底、兜底质量低于 LLM、兜底不存问句”钉住

## 背景

当前系统已经具备：

- `LLMBackedViewerMemoryExtractor`
- `memory_text_raw / memory_text_canonical`
- `polarity / temporal_scope`
- `merge / upgrade / supersede`
- 多维置信度评分
- 生命周期管理
- feature rerank

规则兜底目前已经被限制为：

- 仅在 LLM 调用异常时触发
- 主要通过 `extract_high_confidence()` 保底

这比之前已经安全很多，但仍然存在几个质量问题：

1. 模板覆盖面有限  
   一旦 LLM 异常，能被安全接住的表达类型仍然偏少。

2. 原句整存风险仍然存在  
   规则兜底目前常常：
   - `memory_text = memory_text_raw = memory_text_canonical`
   - 不做真正的最小可复用提纯

3. polarity 仍偏保守  
   规则兜底路径现在基本默认 `neutral`，对明显的负向偏好/限制表达没有充分利用已有语义。

4. 兜底结果和 LLM 结果的质量差异没有被明确拉开  
   虽然当前排序上已经能部分拉开，但规则兜底仍需要更明确的“天然降权”。

## 非目标

本次不做以下内容：

- 不让规则兜底覆盖所有自然语言表达
- 不让规则兜底成为第二主通路
- 不引入 LLM 二次修复规则兜底结果
- 不改变 LLM 正常返回时的主抽取路径
- 不接入新的事件源

## 方案比较

### 方案一：扩大规则模板，但不做提纯

优点：

- 改动最小

缺点：

- 原句整存问题依然存在
- 模板越多，错误文本越容易直接入库

### 方案二：高置信模板 + 保守 canonicalizer

做法：

- 保持只有高置信模板能放行
- 对放行结果再做轻量、保守的规则提纯

优点：

- 提升质量但不至于过度猜测
- 与现有 `memory_text_raw / canonical` 结构兼容

缺点：

- 需要维护一层提纯规则

### 方案三：规则兜底后再调用一个轻量 LLM 修复

优点：

- 提纯潜力高

缺点：

- 与“LLM 异常时兜底”目标矛盾
- 会把兜底链路重新变复杂

### 推荐方案

采用方案二：高置信模板 + 保守 canonicalizer。

原因：

- 不依赖额外模型
- 风险可控
- 能明显改善规则兜底质量

## 总体设计

规则兜底保持三层：

1. 仅 LLM 异常时触发
2. 仅高置信模板放行
3. 放行后再做保守 canonical 提纯和默认降权

最终规则兜底产物仍然要输出完整结构：

- `memory_text_raw`
- `memory_text_canonical`
- `memory_type`
- `polarity`
- `temporal_scope`
- `confidence`
- `extraction_source=rule_fallback`

## 一、高置信模板扩展

### 1. 保留现有高置信模板

现有这几类继续保留：

- `我在...上班`
- `我家里养了...`
- `我一直都只用...`
- `我(租房)住在...附近`

### 2. 新增优先扩展的模板类型

第一版建议新增：

- 明显饮食限制
  - `我不太能吃...`
  - `我不能吃...`
  - `我忌口...`
- 明显负向偏好
  - `我不喜欢...`
- 明显稳定偏好
  - `我一直都喜欢...`
  - `我平时都喝...`
- 明显稳定职业/身份背景
  - `我在...做...`

### 3. 继续严格限制

以下仍然一律不放行：

- 问句
- 反问
- 短期表达
- 情绪表达
- 互动壳子明显重于内容的句子

## 二、保守 canonicalizer

### 1. 目标

规则兜底不再直接把 `content` 原样作为 canonical，而是做最小可复用提纯。

### 2. 保守规则

允许做的提纯：

- 去掉前后口头语
  - `其实`
  - `吧`
  - `啊`
  - `呢`
- 去掉明显问句壳子
- 去掉“这样通勤方便点”这类附属解释尾巴
- 尽量保留核心主语与限制条件

### 3. 例子

- `我其实吧不太能吃辣`
  - raw：`我其实吧不太能吃辣`
  - canonical：`不太能吃辣`

- `我租房住在公司附近，这样通勤方便点`
  - raw：`我租房住在公司附近，这样通勤方便点`
  - canonical：`租房住在公司附近`

- `我家里养了两只猫`
  - raw：`我家里养了两只猫`
  - canonical：`家里养了两只猫`

### 4. 原则

- 宁可少裁，不要误裁
- 不能因为想“提纯”而删掉关键限制信息

## 三、polarity 和默认质量策略

### 1. polarity

规则兜底不再一律 `neutral`。

第一版规则：

- 明显负向限制 / 负向偏好：
  - `不喜欢`
  - `不能吃`
  - `不太能吃`
  - `忌口`
  => `polarity=negative`

- 其他高置信模板默认：
  - `polarity=neutral`

### 2. temporal_scope

规则兜底继续只允许：

- `temporal_scope=long_term`

短期内容即使匹配表面模式，也不放行。

### 3. confidence 与子分降权

规则兜底需要比 LLM 主路径天然更保守。

建议：

- 最终 `confidence` 上限低于 LLM 常规结果
- `clarity_score` 默认不超过 LLM 提纯结果
- `interaction_value_score` 默认适中而非极高

即：

- 规则兜底是“可用但保守”
- 排序时天然落后于同等质量的 LLM 结果

## 四、MemoryConfidenceService 配合

当前已有：

- `MemoryConfidenceService`

规则兜底改造后，建议在评分时显式识别：

- `extraction_source=rule_fallback`

第一版可通过简单降权实现：

- 对 `rule_fallback` 候选的：
  - `clarity_score`
  - `interaction_value_score`
  - `confidence`
  做保守上限

## 五、测试设计

### 1. 单测

需要覆盖：

- LLM 正常返回空结果时，不走规则兜底
- 只有 LLM 异常时才走规则兜底
- 规则兜底不放行问句
- 规则兜底能把明显负向限制识别为 `negative`
- 规则兜底会生成比 raw 更短的 canonical（在可提纯样本上）

### 2. 回归测试

需要覆盖：

- `rule_fallback` 的 `confidence` 不高于常规 LLM 高质量结果
- `rule_fallback` 元数据在排序中自然落后于等价 LLM 结果

## 六、验收标准

完成后应满足：

1. 规则兜底仍然只在 LLM 异常时触发
2. 兜底放行模板范围更实用，但仍可控
3. 兜底结果不再默认原句整存
4. 明显负向偏好/限制能在兜底中正确标成 `negative`
5. 规则兜底结果在质量排序上天然低于同等 LLM 结果

## 七、文件影响范围

预期会修改：

- [backend/services/memory_extractor.py](H:\DouYin_llm\backend\services\memory_extractor.py)
- [backend/services/memory_confidence_service.py](H:\DouYin_llm\backend\services\memory_confidence_service.py)
- [tests/test_llm_memory_extractor.py](H:\DouYin_llm\tests\test_llm_memory_extractor.py)

必要时补：

- [README.md](H:\DouYin_llm\README.md)

## 八、推荐实施顺序

1. 先补规则兜底行为测试
2. 再扩高置信模板
3. 再加保守 canonicalizer
4. 再接入 fallback 降权
5. 最后更新 README
