# 观众记忆去重、合并与覆盖更新设计

日期：2026-04-19

## 目标

在现有“评论抽取 -> 提纯 -> 即时注入当前建议 -> 持久化长期记忆”的链路上，补上一层“保存前记忆归并”能力，把系统从“持续追加句子”升级成“维护观众画像”。

本次设计要解决四件事：

- 避免同一观众的近义记忆不断重复入库
- 允许新证据补强旧记忆，而不是每次都新增
- 允许更具体的新表达升级旧记忆文本
- 当新旧记忆明显冲突时，用 `supersede` 替代简单共存

## 背景

当前系统已经具备：

- 评论预筛
- LLM 双字段抽取：`memory_text_raw / memory_text_canonical`
- `polarity / temporal_scope / memory_type` 标注
- 当前评论即时注入当前建议上下文
- 长期记忆写入 `viewer_memories`
- 语义召回依赖 `SQLite + Chroma`

但当前长期记忆仍然存在三个明显问题：

1. 同义记忆持续累积  
   例如“我挺喜欢拉面”“我超爱豚骨拉面”会更像两条独立记忆，而不是同一偏好的多次确认或升级。

2. 新证据无法更新旧画像  
   例如“住公司附近”之后又说“租房住公司附近”，当前更像新增，而不是把旧记忆升级为更完整表达。

3. 冲突记忆缺少显式覆盖关系  
   例如旧记忆是“喜欢辣”，新记忆是“不太能吃辣”，当前没有稳定的“旧记忆被新记忆覆盖”语义，只能并存或靠人工纠偏。

## 非目标

本次不做以下内容：

- 不引入短期/长期双池存储
- 不引入 LLM 参与合并判定
- 不修改现有向量召回主算法
- 不做跨观众记忆合并
- 不做礼物、复购、回访等非评论信号接入
- 不做批量运营审核 UI

## 方案比较

### 方案一：纯规则判定

流程：

1. 新记忆进入保存前阶段
2. 按 `viewer_id + memory_type + polarity` 查旧记忆
3. 用 canonical 精确匹配、包含关系、少量冲突规则判定
4. 输出 `create / merge / upgrade / supersede`

优点：

- 可控
- 好测
- 实现成本低

缺点：

- 对近义表达、口语化表达和轻微改写覆盖弱

### 方案二：规则 + 向量相似度联合判定

流程：

1. 先用结构条件筛候选旧记忆
2. 再用 canonical 文本规则和 embedding 相似度联合判定
3. 输出 `create / merge / upgrade / supersede`

优点：

- 能覆盖“同义但不完全同字面”的表达
- 不引入 LLM 裁决，延迟和可控性较好
- 与现有 `SQLite + Chroma` 架构最匹配

缺点：

- 需要补一层判定服务和阈值管理

### 方案三：规则 + 向量 + LLM 裁决

优点：

- 理论上边界判定最好

缺点：

- 延迟更高
- 成本更高
- 可解释性和稳定性变差
- 第一版容易过度设计

### 推荐方案

采用方案二：规则 + 向量相似度联合判定。

原因：

- 第一版已经足够解决大部分近义重复入库问题
- 复杂度明显低于引入 LLM 裁决
- 可直接复用现有 `VectorMemory`
- 便于后续逐步扩充规则和阈值，而不是一次上重模型

## 总体设计

在当前 `process_event` 的“提纯完成、准备落库”阶段之前，增加一层 `memory_merge_service`：

1. 新记忆候选进入持久化前阶段
2. 查询同观众活跃长期记忆
3. 先做结构筛选
4. 再做规则和向量联合判定
5. 输出动作：
   - `create`
   - `merge`
   - `upgrade`
   - `supersede`
6. 执行动作并同步 `viewer_memories + viewer_memory_logs + Chroma`

## 一、动作语义

### 1. `create`

条件：

- 没找到足够相近的旧记忆
- 或候选旧记忆都不满足同义/覆盖条件

效果：

- 新建一条长期记忆

### 2. `merge`

条件：

- 新旧记忆本质是同一条
- 新表达没有明显更完整，也没有冲突

效果：

- 不新增新记录
- 只更新旧记录的证据和时间信息

典型例子：

- 旧：`喜欢拉面`
- 新：`喜欢拉面`

### 3. `upgrade`

条件：

- 新旧记忆本质一致
- 但新表达更具体、更可复用或限制条件更完整

效果：

- 不新建记录
- 更新旧记录的 canonical 文本和最近原始证据

典型例子：

- 旧：`住公司附近`
- 新：`租房住在公司附近`

### 4. `supersede`

条件：

- 新旧记忆主题接近
- 但含义明显冲突，且新记忆更可信或更具体

效果：

- 新建一条新记忆作为当前有效版本
- 旧记忆保留审计，但退出召回
- 旧记忆标记为“被覆盖”

典型例子：

- 旧：`喜欢吃辣`
- 新：`不太能吃辣`

## 二、数据模型调整

### 1. `viewer_memories` 新增字段

建议新增：

- `memory_text_raw_latest`
- `evidence_count`
- `first_confirmed_at`
- `last_confirmed_at`
- `superseded_by`
- `merge_parent_id`

字段语义：

- `memory_text_raw_latest`
  - 最近一次支持该记忆的原始表达
- `evidence_count`
  - 该记忆被系统再次确认过的次数
- `first_confirmed_at`
  - 第一次建立该记忆的时间
- `last_confirmed_at`
  - 最近一次被确认或升级的时间
- `superseded_by`
  - 若该记忆被新记忆覆盖，则记录新记忆 `memory_id`
- `merge_parent_id`
  - 保留扩展位，用于以后追踪被合并来源；第一版可以为空

### 2. 状态约定

现有 `status` 继续保留：

- `active`
- `invalid`
- `deleted`

本次不新增 `superseded` 状态，而是采用：

- `status='invalid'`
- `last_operation='superseded'`
- `superseded_by=<new_memory_id>`

原因：

- 兼容现有“只有 `active` 参与召回”的逻辑
- 避免改动过多前端和召回过滤逻辑

## 三、候选旧记忆检索

### 1. 粗筛

仅在以下范围里找候选旧记忆：

- 同 `room_id`
- 同 `viewer_id`
- `status='active'`
- 同 `memory_type`

`polarity` 第一版不入库为独立字段，因此不作为 SQL 粗筛条件；极性用 canonical 文本和冲突规则判定。

### 2. 精筛

对候选记忆做两层排序：

- 文本规则优先
  - canonical 完全相等
  - 新包含旧 / 旧包含新
  - 共享关键主语和限制词
- 向量相似度补充
  - 只在同 `viewer_id` 范围内做 top-k 相似检索

### 3. 候选数量

第一版建议：

- SQL 粗筛取最近 20 条
- 向量相似度保留 top 5
- 最终进入判定器的候选上限为 5

## 四、判定规则

### 1. `merge` 判定

满足任一条件即可进入 `merge` 候选：

- canonical 完全相同
- 标准化后文本几乎相同
- 相似度高于高阈值，且无“更具体”证据、无冲突信号

### 2. `upgrade` 判定

满足以下条件：

- 新旧记忆高相似
- 新文本包含旧文本的主要语义
- 新文本提供额外限制条件、场景或更明确主语

例如：

- `喜欢拉面` -> `喜欢豚骨拉面`
- `住公司附近` -> `租房住在公司附近`

### 3. `supersede` 判定

满足以下条件：

- 新旧记忆高相似或主题强相关
- 但在偏好方向或限制条件上明显冲突

第一版冲突信号包括：

- 明确否定词：`不喜欢 / 不能 / 不吃 / 不喝 / 忌口 / 接受不了`
- 旧文本和新文本在“可/不可”“喜欢/不喜欢”方向上相反

### 4. `create` 判定

当候选旧记忆都不满足以上条件时，执行 `create`。

## 五、写入行为

### 1. `create`

- 新建一条 `viewer_memories`
- `evidence_count=1`
- `first_confirmed_at=created_at`
- `last_confirmed_at=created_at`

### 2. `merge`

- 更新旧记录：
  - `evidence_count += 1`
  - `last_confirmed_at = now`
  - `memory_text_raw_latest = new.memory_text_raw`
  - `updated_at = now`
  - `last_operation = 'merged'`

### 3. `upgrade`

- 更新旧记录：
  - `memory_text = new.memory_text_canonical`
  - `memory_text_raw_latest = new.memory_text_raw`
  - `confidence = max(old, new)`
  - `evidence_count += 1`
  - `last_confirmed_at = now`
  - `updated_at = now`
  - `last_operation = 'upgraded'`

### 4. `supersede`

- 新建新记录
- 将旧记录更新为：
  - `status='invalid'`
  - `superseded_by=<new_memory_id>`
  - `last_operation='superseded'`
  - `updated_at = now`
- 新记录正常写入 `active`

## 六、日志与审计

`viewer_memory_logs` 需要支持新增操作名：

- `merged`
- `upgraded`
- `superseded`

记录要求：

- `merged`
  - 记录旧值不变、新证据来源写入 reason 或扩展字段
- `upgraded`
  - 记录 `old_memory_text -> new_memory_text`
- `superseded`
  - 记录旧记忆从 `active -> invalid`
  - 记录覆盖目标 `superseded_by`

第一版如果不扩日志表结构，可先把覆盖目标写进 `reason`。

## 七、向量索引同步

### 1. `create`

- 新增向量

### 2. `merge`

- 通常无需重建向量内容
- 只需保持记录元数据更新
- 若当前 Chroma 元数据需要同步，可以执行一次 `sync_memory`

### 3. `upgrade`

- 需要更新文档文本和元数据
- 执行 `vector_memory.sync_memory(updated_memory)`

### 4. `supersede`

- 旧记忆从向量索引移除
- 新记忆加入向量索引

## 八、测试设计

### 1. 单测

需要覆盖：

- canonical 完全相同触发 `merge`
- 新文本更具体触发 `upgrade`
- 冲突偏好触发 `supersede`
- 无相似候选触发 `create`
- `supersede` 后旧记忆不再参与召回

### 2. 存储层测试

需要覆盖：

- 新字段迁移与默认值
- `merge / upgrade / supersede` 的日志落库
- `superseded_by` 正确写入

### 3. 流程测试

需要覆盖：

- 当前评论建议仍可即时吃到新记忆
- 合并或升级时不产生多余重复长期记忆
- 覆盖后向量召回只命中新记忆

## 九、验收标准

完成后应满足：

1. 同一观众的明显同义长期记忆不会持续重复入库
2. 更具体的新表达会升级旧记忆，而不是并存
3. 明显冲突的新记忆会创建新记录并覆盖旧记录
4. 被覆盖旧记录不再参与召回，但保留审计痕迹
5. 整个流程不引入 LLM 合并裁决，仍保持第一版可控性

## 十、文件影响范围

预期会修改：

- [backend/app.py](H:\DouYin_llm\backend\app.py)
- [backend/memory/long_term.py](H:\DouYin_llm\backend\memory\long_term.py)
- [backend/memory/vector_store.py](H:\DouYin_llm\backend\memory\vector_store.py)
- [backend/schemas/live.py](H:\DouYin_llm\backend\schemas\live.py)
- [backend/services/agent.py](H:\DouYin_llm\backend\services\agent.py)

预期会新增：

- [backend/services/memory_merge_service.py](H:\DouYin_llm\backend\services\memory_merge_service.py)
- [tests/test_memory_merge_service.py](H:\DouYin_llm\tests\test_memory_merge_service.py)
- [tests/test_viewer_memory_merge_flow.py](H:\DouYin_llm\tests\test_viewer_memory_merge_flow.py)

## 十一、推荐实施顺序

1. 先补 `viewer_memories` 新字段和迁移
2. 再实现 `memory_merge_service` 的纯规则判定骨架
3. 再接入同观众候选旧记忆检索
4. 再把 `create / merge / upgrade / supersede` 接入 `process_event`
5. 最后补向量同步、日志测试和流程回归测试
