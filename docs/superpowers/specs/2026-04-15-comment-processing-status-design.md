# 评论处理状态设计

## 目标

在前端事件流中展示每一条新评论的处理轨迹，让操作人能直接看出这条评论进入后端后经历了什么。

这个功能以“评论”为中心，不以“观众整体”为中心。前端需要回答这几个问题：

- 这条评论有没有成功落库？
- 这条评论有没有产出观众记忆？
- 这条评论有没有参与记忆召回？
- 这条评论有没有生成提词？

## 范围

本设计只覆盖前端事件流中“新进入系统的评论事件”。

在范围内：

- 给实时推送出去的评论事件附加逐条处理状态
- 在前端事件流中为评论渲染简洁的处理状态标签
- 提供可展开的调试细节字段

不在范围内：

- 给已经存量落在 SQLite 里的历史评论补回处理状态
- 为状态追踪单独新增一张数据库表
- 展示“某个观众整体处理状态”的聚合视图

## 推荐方案

沿用 `backend/app.py` 里现有的实时处理链路，在 `process_event()` 执行过程中构造一份逐条评论的 `processing_status` 对象，并直接挂到 SSE / WebSocket 推送出去的事件 payload 上。

推荐理由：

- 它最直接表达“这条评论后来发生了什么”
- 不需要为了偏调试性质的状态信息引入新的持久化结构
- 前端改动可以局限在现有事件流和事件卡片上

## 数据结构

每条实时推送的事件都应允许携带一个 `processing_status` 对象，结构建议如下：

```json
{
  "received": true,
  "persisted": true,
  "memory_extraction_attempted": true,
  "memory_saved": true,
  "saved_memory_ids": ["mem-1"],
  "memory_recall_attempted": true,
  "memory_recalled": true,
  "recalled_memory_ids": ["mem-9"],
  "suggestion_generated": true,
  "suggestion_id": "sug-1"
}
```

字段含义：

- `received`：后端已经接收并开始处理这条评论
- `persisted`：评论事件已经成功写入 SQLite
- `memory_extraction_attempted`：已经对这条评论执行过记忆抽取
- `memory_saved`：这条评论至少保存出了一条观众记忆
- `saved_memory_ids`：本条评论新保存出来的观众记忆 ID 列表
- `memory_recall_attempted`：提词生成过程中已经尝试做观众记忆召回
- `memory_recalled`：这条评论在生成上下文时命中了至少一条观众记忆
- `recalled_memory_ids`：命中的观众记忆 ID 列表
- `suggestion_generated`：这条评论最终生成了提词
- `suggestion_id`：生成的提词 ID

## 后端改动

### 事件处理链路

更新 `backend/app.py` 里的 `process_event()`，在处理评论时逐步累积状态：

1. 开始处理时写入 `received=true`
2. `persist_event()` 成功后写入 `persisted=true`
3. 进入记忆提取前写入 `memory_extraction_attempted=true`
4. 如果成功保存记忆，则填充 `memory_saved` 和 `saved_memory_ids`
5. 当 agent 构建上下文并执行记忆召回时，填充 `memory_recall_attempted`、`memory_recalled`、`recalled_memory_ids`
6. 如果生成了 suggestion，则填充 `suggestion_generated` 和 `suggestion_id`

### 召回结果回传

当前 agent 在构建上下文时已经知道命中了哪些观众记忆。它需要把这部分信息用一个很轻量的方式回传给调用方，这样 `process_event()` 才能把召回状态写进 `processing_status`。

推荐实现方式：

- 保持现有 suggestion 输出结构不变
- 增加一条轻量的 recall metadata 返回路径，或者在单次生成流程中记录当前事件命中的 recall 结果

这里不允许重新引入事件历史召回，因为系统现在只保留观众记忆召回。

### 接口契约

不要新增独立的状态流。

而是直接增强现有事件推送 payload：

- `GET /api/events/stream`
- `GET /ws/live`

对于 bootstrap 拉到的历史事件，可以允许没有 `processing_status`。只有“新进入系统并被实时处理的评论”必须保证带上这个字段。

## 前端改动

在事件流里仅对“评论事件”渲染处理状态。

默认显示 4 组紧凑标签：

- `已落库`
- `已保存记忆` 或 `未产出记忆`
- `命中召回` 或 `未命中召回`
- `已生成提词` 或 `未生成提词`

展开后的调试细节：

- `saved_memory_ids`
- `recalled_memory_ids`
- `suggestion_id`

展示规则：

- 只有评论事件显示这组处理状态标签
- 默认行态保持紧凑，不让状态信息压过评论正文
- 展开详情只用于调试，不作为主视觉重点

## 异常与边界处理

如果处理中途失败，前端仍然应该看到“已经成功完成到哪一步”，而不是整个状态缺失。

如果因为某条评论走的是跳过召回的路径，那么应设置：

- `memory_recall_attempted=false`
- `memory_recalled=false`
- `recalled_memory_ids=[]`

如果执行了记忆提取，但没有抽出可保存内容，那么应设置：

- `memory_extraction_attempted=true`
- `memory_saved=false`
- `saved_memory_ids=[]`

## 测试

后端：

- 验证评论在落库、保存记忆、命中召回、生成提词后，`processing_status` 是否正确
- 验证没有抽取出记忆的评论，仍然会显示“已尝试提取记忆”
- 验证跳过召回的路径会正确标记“未尝试召回”

前端：

- 验证评论卡片能根据 `processing_status` 正确渲染 4 个核心标签
- 验证展开详情时能显示相关 ID
- 验证非评论事件不显示评论处理状态标签

回归：

- 原有提词、记忆、事件流逻辑保持通过

## 完成标准

当满足下面这些条件时，功能算完成：

- 新进入系统的一条评论，在前端事件流中可以直接看出处理结果
- 操作人能区分“未处理”“处理了但没产出记忆”“处理了且命中召回”
- 不需要为了这个功能额外新增一套状态持久化层
