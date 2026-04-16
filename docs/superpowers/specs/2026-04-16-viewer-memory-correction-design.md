# 观众记忆人工纠偏设计

## 目标

给当前项目补上“观众记忆人工纠偏”能力，让主播或运营能直接在观众工作台里对观众记忆做人工管理，并且确保这些人工操作会真实影响后续语义召回，而不是只改前端展示。

本次设计要同时解决四个问题：

- 当前 `viewer_memories` 只能读，不能人工新增、编辑、删除或失效处理。
- 自动抽取出的错误记忆会长期污染后续召回结果。
- 前端只能看到记忆结果，看不到一条记忆经历过哪些处理动作。
- 记忆一旦被人工纠偏，SQLite 主表状态和向量召回索引必须保持一致。

## 适用范围

包含：

- 给观众记忆增加人工新增、编辑、删除、标记无效、恢复有效、置顶能力。
- 区分自动来源和人工来源。
- 给被人工干预过的记忆记录纠偏原因、最后操作信息和操作日志。
- 在观众工作台中展示当前记忆状态与精简时间线，并支持展开完整时间线。
- 保证记忆变更后，向量召回结果同步生效。

不包含：

- 新做独立的“记忆管理后台”或批量运营面板。
- 引入复杂审批流、多角色权限系统或多级审核。
- 改造现有记忆抽取算法本身。
- 改造评论处理主时间线之外的其他业务面板。

## 现状上下文

- 前端观众工作台入口在 [ViewerWorkbench.vue](/H:/DouYin_llm/frontend/src/components/ViewerWorkbench.vue)，目前已支持观众详情展示和备注 CRUD。
- 观众工作台状态在 [live.js](/H:/DouYin_llm/frontend/src/stores/live.js)，已具备打开面板、刷新详情、保存备注、删除备注的完整状态流。
- 后端接口入口在 [app.py](/H:/DouYin_llm/backend/app.py)，目前观众记忆只有查询接口：
  - `GET /api/viewer`
  - `GET /api/viewer/memories`
- 长时存储在 [long_term.py](/H:/DouYin_llm/backend/memory/long_term.py)，当前只提供：
  - `list_viewer_memories`
  - `get_viewer_memory`
  - `save_viewer_memory`
  - `touch_viewer_memories`
- 向量召回在 [vector_store.py](/H:/DouYin_llm/backend/memory/vector_store.py)，当前只支持新增记忆 `add_memory` 和相似召回 `similar_memories`，没有更新和删除流程。
- 自动抽取逻辑在 [memory_extractor.py](/H:/DouYin_llm/backend/services/memory_extractor.py)，会把评论启发式写入 `viewer_memories`。

这意味着现在的系统只支持“自动抽取 + 召回”，不支持“人工修正 + 召回同步”。

## 方案比较

### 方案一：只改主表，不记录独立日志

做法：

- 在 `viewer_memories` 上补状态字段。
- 每次人工变更都直接覆盖当前记录。

优点：

- 实现最快。
- 对现有接口改动最小。

缺点：

- 无法满足“处理轨迹可见”。
- 后续难以解释一条记忆为什么变成现在这样。
- 无法为前端时间线提供可信数据来源。

### 方案二：主表保存当前状态，独立日志表记录轨迹

做法：

- `viewer_memories` 保存当前生效状态。
- 新增 `viewer_memory_logs` 保存每次创建、编辑、失效、恢复、置顶、删除等操作。

优点：

- 同时满足“当前状态清晰”和“操作轨迹可追溯”。
- 最贴合当前 SQLite + 向量库双存储结构。
- 前端既能展示当前有效记忆，也能展开看完整时间线。

缺点：

- 需要维护主表和日志表双写。

### 方案三：纯事件溯源，当前状态由日志回放得到

做法：

- 所有记忆变化都只写日志。
- 当前记忆列表实时通过日志重建。

优点：

- 审计完整，理论上最灵活。

缺点：

- 对当前项目来说过重。
- 存储层、API、前端、召回同步都会明显复杂化。

### 推荐方案

采用方案二：**主表保存当前状态，独立日志表保存完整纠偏轨迹**。

原因：

- 满足用户确认的 C 方案需求：新增、编辑、删除、标记无效、恢复有效、来源区分、置顶、备注原因、操作日志。
- 不会把当前项目推向复杂审批系统。
- 能够直接落在现有观众工作台和现有向量召回链路上。

## 数据模型设计

### `viewer_memories` 扩展字段

当前 `viewer_memories` 继续作为“当前状态表”，在现有字段基础上增加：

- `source_kind`
  - 取值：`auto | manual`
  - 表示这条记忆最初来自自动抽取还是人工新增。
- `status`
  - 取值：`active | invalid | deleted`
  - `active`：展示且参与召回。
  - `invalid`：保留记录但不参与召回。
  - `deleted`：主列表不展示，不参与召回，只保留审计能力。
- `is_pinned`
  - 取值：`0 | 1`
  - 表示是否人工置顶。
- `correction_reason`
  - 最近一次人工纠偏或状态变更的原因说明。
- `corrected_by`
  - 最近一次人工纠偏操作者。
  - 首期固定为 `主播`。
- `last_operation`
  - 最近一次操作类型。
  - 候选值：`created`、`edited`、`invalidated`、`reactivated`、`pinned`、`unpinned`、`deleted`。
- `last_operation_at`
  - 最近一次操作时间戳。

保留现有字段：

- `memory_id`
- `room_id`
- `viewer_id`
- `source_event_id`
- `memory_text`
- `memory_type`
- `confidence`
- `created_at`
- `updated_at`
- `last_recalled_at`
- `recall_count`

### `viewer_memory_logs` 新表

新增一张专门的日志表，用于生成前端时间线并支持追溯：

- `log_id`
- `memory_id`
- `room_id`
- `viewer_id`
- `operation`
- `operator`
- `reason`
- `old_memory_text`
- `new_memory_text`
- `old_memory_type`
- `new_memory_type`
- `old_status`
- `new_status`
- `old_is_pinned`
- `new_is_pinned`
- `created_at`

日志设计原则：

- 系统自动抽取创建记忆时，也写一条 `created` 日志，`operator=system`。
- 人工新增记忆时，也写 `created` 日志，`operator=主播`。
- 每次人工编辑、失效、恢复、置顶、取消置顶、删除都必须追加新日志，不覆盖旧日志。

## 召回规则设计

### 状态与召回的关系

- `active` 才允许参与语义召回。
- `invalid` 和 `deleted` 一律不参与召回。
- 前端主列表默认不展示 `deleted`。
- `deleted` 的日志仍可通过审计或调试接口追溯，但不是工作台主视图默认内容。

### 来源与人工修正的关系

- `source_kind` 表示“最初来源”，不因为人工编辑而改变。
- 自动抽取后被人工编辑的记忆，仍然是 `source_kind=auto`。
- 是否被人工干预，靠日志和 `last_operation` 表达，而不是改写来源。

### 排序与加权

召回排序保留现有相似度、置信度、召回次数等因素，同时增加两类人工信号：

- `manual` 比 `auto` 略高权重。
- `is_pinned=1` 比非置顶更高权重。

约束：

- `pinned` 只对 `active` 记忆生效。
- 如果记忆变成 `invalid` 或 `deleted`，即使此前是置顶，也不再参与召回。

### 与向量索引同步

每次记忆状态变化都必须同步更新向量层：

- 新增记忆：写主表、写日志、写向量索引。
- 编辑记忆文本：写主表、写日志、重建该记忆的 embedding。
- 只改类型或原因：写主表、写日志，不重算 embedding。
- 标记无效：写主表、写日志、从可召回集合移除。
- 恢复有效：写主表、写日志、重新写回向量索引。
- 删除：写主表、写日志、从可召回集合移除。

这里的“删除”是业务软删除，不是物理彻底抹掉数据库痕迹。

## 接口设计

### 现有接口扩展

#### `GET /api/viewer`

继续返回观众详情，但 `memories` 中新增以下字段：

- `source_kind`
- `status`
- `is_pinned`
- `correction_reason`
- `corrected_by`
- `last_operation`
- `last_operation_at`

默认只返回 `active` 和 `invalid` 记忆，不返回 `deleted`。

### 新增接口

#### `POST /api/viewer/memories`

用途：人工新增记忆。

请求字段：

- `room_id`
- `viewer_id`
- `memory_text`
- `memory_type`
- `is_pinned`
- `correction_reason`

服务端默认补充：

- `source_kind=manual`
- `status=active`
- `corrected_by=主播`
- `last_operation=created`

副作用：

- 写 `viewer_memories`
- 写 `viewer_memory_logs`
- 写向量索引

#### `PUT /api/viewer/memories/{memory_id}`

用途：编辑记忆。

允许更新：

- `memory_text`
- `memory_type`
- `is_pinned`
- `correction_reason`

规则：

- 如果 `memory_text` 变化，记 `edited` 日志并重算 embedding。
- 如果只是置顶变化，记 `pinned` 或 `unpinned` 日志，不重算 embedding。
- 如果只是原因变化，也落日志，但不重算 embedding。

#### `POST /api/viewer/memories/{memory_id}/invalidate`

用途：标记无效。

请求字段：

- `reason`

副作用：

- `status=invalid`
- 更新 `correction_reason`
- 更新最后操作字段
- 写 `invalidated` 日志
- 从向量可召回集合移除

#### `POST /api/viewer/memories/{memory_id}/reactivate`

用途：恢复有效。

请求字段：

- `reason`

副作用：

- `status=active`
- 更新最后操作字段
- 写 `reactivated` 日志
- 重新写回向量索引

#### `DELETE /api/viewer/memories/{memory_id}`

用途：删除记忆。

业务语义：

- 软删除，不物理抹掉数据库痕迹。

副作用：

- `status=deleted`
- 更新最后操作字段
- 写 `deleted` 日志
- 从向量可召回集合移除

删除后：

- 不在工作台主列表展示。
- 不允许再直接编辑正文。
- 日志仍可追溯。

#### `GET /api/viewer/memories/{memory_id}/logs`

用途：按需拉取单条记忆的完整时间线。

原因：

- 避免 `GET /api/viewer` 一次返回所有日志，导致面板过重。
- 只有用户展开某条记忆时才加载完整日志。

## 前端交互设计

### 总体结构

沿用现有 [ViewerWorkbench.vue](/H:/DouYin_llm/frontend/src/components/ViewerWorkbench.vue) 作为承载容器，不另做新页面。

观众工作台中的“记忆区”改为混合式展示：

- 主列表展示“当前记忆卡片”。
- 每张卡片显示精简轨迹摘要。
- 用户可展开单条记忆查看完整时间线。

### 记忆主列表卡片

每条记忆卡片展示：

- `memory_text`
- `memory_type`
- `source_kind` 对应中文文案
- `status` 对应中文文案
- `is_pinned` 状态
- 最近一次操作摘要
- 最近一次操作时间

建议中文状态词：

- `自动抽取`
- `人工新增`
- `有效`
- `已失效`
- `已置顶`
- `人工修正`
- `已删除`

最近一次操作摘要示例：

- `4 分钟前人工修正：自动抽取有误`
- `10 分钟前标记失效：信息已过期`
- `刚刚人工新增`

### 卡片操作

对 `active` 记忆显示：

- `编辑`
- `标无效`
- `删除`
- `置顶` 或 `取消置顶`

对 `invalid` 记忆显示：

- `恢复有效`
- `删除`

对 `deleted` 记忆：

- 不出现在主列表中。

### 新增记忆表单

放在记忆区顶部，风格与现有备注编辑区保持一致但更轻量。

字段：

- `memory_text`
- `memory_type`
- `是否置顶`
- `纠偏原因`

行为：

- 点击保存后发起 `POST /api/viewer/memories`
- 成功后刷新当前观众工作台
- 失败时保留输入内容，不清空表单

### 时间线展示

精简时间线显示在卡片摘要区，只展示最近一次关键动作。

展开完整时间线时，按时间倒序展示：

- `自动抽取`
- `人工新增`
- `人工修正`
- `标记失效`
- `恢复有效`
- `置顶`
- `取消置顶`
- `删除`

每个节点展示：

- 操作名称
- 操作者
- 时间
- 原因
- 必要时展示变更前后文本

### store 改造方向

在 [live.js](/H:/DouYin_llm/frontend/src/stores/live.js) 中补充：

- 记忆新增表单状态
- 记忆编辑中的草稿状态
- 单条记忆时间线加载状态
- 记忆操作中的 saving/loading/error 状态
- 与备注状态隔离，避免互相污染

保持现有工作模式：

- 操作成功后刷新当前观众详情。
- 请求失败后只在观众工作台范围内显示错误，不影响主事件流和提词区。

## 边界规则

- `invalid` 和 `deleted` 一律不参与召回。
- 前端主列表默认不展示 `deleted`。
- `deleted` 记忆不能再直接编辑。
- `invalid` 记忆允许恢复成 `active`。
- `is_pinned` 只在 `active` 状态下对召回生效。
- 人工新增默认 `source_kind=manual`、`status=active`。
- 自动抽取默认 `source_kind=auto`、`status=active`。
- 改 `memory_text` 或 `memory_type` 视为一次 `edited`。
- 改 `correction_reason` 也记录日志，但不重算 embedding。
- 改 `is_pinned` 记录为单独的 `pinned` 或 `unpinned`。
- 自动来源的记忆即使被人工编辑，也不改写 `source_kind`。

## 错误处理与一致性策略

### 数据一致性

主表变更和日志写入必须放在同一个数据库事务中。

向量同步策略：

- 如果数据库写成功、向量更新失败，在严格模式下必须报错并回滚。
- 不允许出现“数据库看起来改成功了，但召回实际上没改”的静默成功状态。

这是首期设计中“真语义召回”要求的一部分，不做口头保证。

### 前端错误处理

- 操作进行中，当前按钮禁用，避免重复提交。
- 请求失败时，在观众工作台顶部显示错误。
- 编辑失败时，保留当前输入内容，不自动清空。
- 时间线加载失败时，只影响这条记忆的展开区，不影响整个工作台。

## 测试设计

### 后端存储层

至少覆盖：

- 新增记忆会写主表和日志。
- 编辑记忆正文会更新主表并追加日志。
- 标记无效会更新状态并追加日志。
- 恢复有效会更新状态并追加日志。
- 删除会把状态改为 `deleted` 并追加日志。
- 默认查询不会返回 `deleted`。

### 后端向量同步

至少覆盖：

- 新增后可召回。
- 编辑文本后旧文本不再作为当前召回文本，新文本可召回。
- 标记无效后不可召回。
- 删除后不可召回。
- 恢复后重新可召回。

### 前端 store 与组件

至少覆盖：

- 工作台能显示记忆的新字段。
- 新增、编辑、失效、恢复、删除、置顶会发出正确请求。
- 失败时错误展示正确，且不清空草稿。
- 展开时间线时能正确请求和渲染日志。
- `deleted` 不出现在主列表。
- `invalid` 记忆会显示“恢复有效”动作。

## 实施顺序建议

建议按以下顺序拆实现和提交：

1. 后端数据模型与存储层扩展。
2. 向量索引增删改同步。
3. 观众记忆 API 路由。
4. 前端 store 状态流扩展。
5. 观众工作台记忆卡片与时间线 UI。
6. 测试补齐。
7. README 对齐。

## 完成标准

满足以下条件即可视为完成：

- 观众工作台可以人工新增、编辑、失效、恢复、删除、置顶记忆。
- 当前记忆状态与完整操作时间线都可见。
- `invalid` 和 `deleted` 记忆不会参与后续语义召回。
- 记忆变更会真实同步到底层向量索引。
- 自动来源与人工来源可区分，人工干预轨迹可追溯。
- 有覆盖关键路径的后端与前端测试。
