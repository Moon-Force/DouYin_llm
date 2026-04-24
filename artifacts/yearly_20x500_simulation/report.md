# 20 位观众一年 10,000 条发言模拟测试报告

## 测试目标

验证在 20 个观众、每人 500 条跨一年发言的压力下，系统是否能把有价值记忆从大量闲聊中稳定沉淀、去重合并，并通过 `memory_recall_text` 与查询重写提升真实语义召回。

## 数据设计

- 观众数：20 位
- 每位发言：500 条
- 总发言：10000 条
- 跨越时间：364 天
- 有记忆价值发言：480 条
- 闲聊/无营养发言：9520 条
- 预期唯一长期记忆：160 条

## 测试指标

- 存储召回率：最终 active 记忆覆盖预期唯一记忆的比例，目标 100%。
- 存储精确率：最终 active 记忆中属于预期唯一记忆的比例，目标 100%。
- 重复记忆数：同一观众同一记忆重复 active 行数，目标 0。
- 合并动作分布：首次出现应 create，后续重复证据应 merge。
- 语义召回 Top1/Top3：对每条 active 记忆构造业务问题，检查真实 embedding 召回是否命中目标记忆。

## 结果摘要

- Active 记忆数：160 / 预期 160
- 存储召回率：100.00%
- 存储精确率：100.00%
- 重复分组：0 组，重复行：0 行
- 合并动作：{"create": 160, "merge": 320}
- Hash Top1/Top3：30.00% / 38.75%
- Real Embedding `bge-m3:latest` Top1/Top3：44.38% / 62.50%
- 相比上一轮真实 embedding：Top1 +44.38%，Top3 +62.50%
- 总耗时：185.365 秒；真实 embedding 召回耗时：37.337 秒

## 结论

- 记忆沉淀目标达成：所有预期长期记忆均被保留，且没有重复 active 记忆。
- 合并目标达成：重复证据进入 merge，没有再次制造重复记忆行。
- 召回质量有提升空间：扩写与查询重写让召回文本更丰富，但真实 embedding Top3 是否足够用于生产仍需结合主播容忍度和后续 rerank 策略判断。

## 输出文件

- 摘要 JSON：`H:\DouYin_llm\artifacts\yearly_20x500_simulation\summary.json`
- 真实 embedding case：`H:\DouYin_llm\artifacts\yearly_20x500_simulation\semantic_cases_real_embedding.json`
- 重复记忆明细：`H:\DouYin_llm\artifacts\yearly_20x500_simulation\duplicate_groups.json`
- 本报告：`H:\DouYin_llm\artifacts\yearly_20x500_simulation\report.md`
