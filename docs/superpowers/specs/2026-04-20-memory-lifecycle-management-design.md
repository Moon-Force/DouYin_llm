# 观众记忆生命周期管理设计

日期：2026-04-20

## 目标

给当前观众记忆链路补上最小可落地的生命周期管理，避免具有明显时效性的记忆长期留在 `active` 池中持续参与召回。

本次设计优先解决三件事：

- 让短期记忆不会长期污染长期记忆池
- 让已入库记忆具备基本的过期/失活能力
- 让召回阶段能稳定排除“已经过期但仍在库中”的记忆

## 背景

当前系统已经具备：

- `memory_text_raw / memory_text_canonical`
- `memory_type / polarity / temporal_scope`
- `merge / upgrade / supersede`
- 多维置信度评分
- 时间衰减排序

但仍有一个结构性缺口：

- 记忆一旦进入 `viewer_memories`，通常会长期保持 `active`
- `temporal_scope` 目前主要用于抽取阶段的入库前门控，而不是完整生命周期管理
- 时间衰减只能“降权”，不能真正“过期”或“迁移”

这意味着：

- 明显短期的信息如果误入库，会长期干扰召回
- 系统没有“这条记忆什么时候失效”的统一语义
- 排序层只能靠时间衰减兜底，不能替代真正的状态管理

## 非目标

本次不做以下内容：

- 不做完整的 long-term / short-term 双数据库或双表架构
- 不引入独立的 short-term 向量索引
- 不做复杂的后台调度系统
- 不接入新的行为信号源
- 不做前端批量管理 UI

## 方案比较

### 方案一：只做时间衰减，不改状态

做法：

- 保持所有记忆都在 `viewer_memories`
- 只靠排序中的时间衰减慢慢降权

优点：

- 改动最小

缺点：

- 不能真正防止过时记忆被召回
- 无法表达“已过期但保留审计”

### 方案二：在现有表上增加过期字段和状态过滤

做法：

- `viewer_memories` 增加：
  - `expires_at`
  - `lifecycle_kind`
- 查询和召回时排除已过期记忆
- 必要时把过期记忆自动视为不参与召回

优点：

- 改动可控
- 不需要新表
- 能立刻补上生命周期语义

缺点：

- 还不是真正的双层记忆架构

### 方案三：直接拆 long-term / short-term 双池

优点：

- 结构最清晰

缺点：

- 工程量大
- 涉及存储、召回、前端、管理接口一起调整
- 超出当前最小可落地范围

### 推荐方案

采用方案二：在现有 `viewer_memories` 表上增加过期字段和生命周期语义。

原因：

- 可以最小代价解决“短期记忆长期污染”的核心问题
- 与当前链路最兼容
- 后续如果要扩成真正双池，也能平滑迁移

## 总体设计

在 `viewer_memories` 上增加两个字段：

- `lifecycle_kind`
- `expires_at`

并定义：

- `lifecycle_kind = long_term | short_term`
- `expires_at = 0` 代表不过期

核心策略：

1. 默认长期记忆：
   - `lifecycle_kind=long_term`
   - `expires_at=0`

2. 短期记忆：
   - `lifecycle_kind=short_term`
   - `expires_at=created_at + ttl`

3. 查询与召回：
   - 只允许未过期记忆参与召回
   - 已过期记忆仍保留审计，不参与主链路

## 一、字段设计

### 1. `lifecycle_kind`

类型：

- `TEXT NOT NULL DEFAULT 'long_term'`

取值：

- `long_term`
- `short_term`

语义：

- `long_term`：稳定画像，默认长期有效
- `short_term`：具备明显时效性，需要在过期后退出召回

### 2. `expires_at`

类型：

- `INTEGER NOT NULL DEFAULT 0`

语义：

- `0`：不过期
- `>0`：在该毫秒时间戳之后视为过期

## 二、创建策略

### 1. 长期记忆

当满足以下条件时：

- `temporal_scope=long_term`
- 没有明显短期表达

写入：

- `lifecycle_kind='long_term'`
- `expires_at=0`

### 2. 短期记忆

第一版不改变当前“短期内容尽量不入长期记忆”的主原则，但为后续兼容保留落点：

- 如果未来允许部分短期内容入库，则：
  - `lifecycle_kind='short_term'`
  - `expires_at=created_at + ttl`

第一版建议 TTL：

- `MEMORY_SHORT_TERM_TTL_HOURS=72`

## 三、过期判定

统一规则：

```text
is_expired = (expires_at > 0 and now_ms >= expires_at)
```

### 1. 不要求物理删除

过期记忆：

- 仍保留在 `viewer_memories`
- 保留审计能力
- 默认不参与召回

### 2. 状态兼容

第一版不新增 `expired` 状态列值，而是保持：

- `status='active'`
- 但查询和召回时增加 `expires_at` 过滤

原因：

- 最小改动
- 不破坏现有失效/删除语义

后续如果需要再引入显式 `expired` 状态。

## 四、查询与召回变更

### 1. `list_viewer_memories`

当前只过滤：

- `status <> 'deleted'`

需要改成：

- `status <> 'deleted'`
- 且未过期

或在需要显示全部时，允许带参数决定是否包含过期记忆。

### 2. `list_all_viewer_memories`

供索引重建和后台查看时：

- 默认只返回未删除且未过期
- 若后续需要审计模式，可加开关

### 3. `VectorMemory.similar_memories`

当前已经检查：

- `status == active`

需要再补：

- `expires_at == 0 or expires_at > now`

### 4. `prime_memory_index`

构建索引时：

- 只把未删除且未过期的记忆放入向量索引

## 五、与现有衰减排序的关系

现在已有时间衰减排序，这一层保留，但职责收窄：

- `expires_at` 负责“是否还能参与召回”
- `time decay` 负责“在还能参与召回时，旧记忆如何自然降权”

两者关系：

- 先过滤过期
- 再对未过期记忆做衰减排序

## 六、配置设计

建议新增：

- `MEMORY_SHORT_TERM_TTL_HOURS=72`

放在 [backend/config.py](H:\DouYin_llm\backend\config.py)

对应字段：

- `memory_short_term_ttl_hours`

## 七、测试设计

### 1. 存储层测试

需要覆盖：

- 新字段默认值正确
- 长期记忆 `expires_at=0`
- 短期记忆能写入未来过期时间

### 2. 查询层测试

需要覆盖：

- 已过期记忆不会出现在 `list_viewer_memories`
- 已过期记忆不会出现在 `list_all_viewer_memories`

### 3. 向量召回测试

需要覆盖：

- 已过期记忆不参与 `similar_memories`
- 未过期记忆仍能正常排序

## 八、验收标准

完成后应满足：

1. `viewer_memories` 具备生命周期字段
2. 已过期记忆不会参与主召回链路
3. 时间衰减和过期机制职责分离，不再互相替代
4. 现有 active/invalid/deleted 状态语义不被破坏
5. 后续如需扩展双层记忆，可基于该设计平滑迁移

## 九、文件影响范围

预期会修改：

- [backend/config.py](H:\DouYin_llm\backend\config.py)
- [backend/schemas/live.py](H:\DouYin_llm\backend\schemas\live.py)
- [backend/memory/long_term.py](H:\DouYin_llm\backend\memory\long_term.py)
- [backend/memory/vector_store.py](H:\DouYin_llm\backend\memory\vector_store.py)

预期会新增或修改测试：

- [tests/test_long_term.py](H:\DouYin_llm\tests\test_long_term.py)
- [tests/test_vector_store.py](H:\DouYin_llm\tests\test_vector_store.py)

## 十、推荐实施顺序

1. 先补 schema 和配置
2. 再补存储查询过滤
3. 再补向量索引与召回过滤
4. 最后补测试和 README 更新
