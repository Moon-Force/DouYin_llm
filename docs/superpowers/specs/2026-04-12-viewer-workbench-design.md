# Viewer Workbench Design

## Goal

在当前直播主界面中补一个“点击事件流里的观众后，在右侧打开详情面板”的工作台，让主播能快速查看观众画像、系统记忆、最近互动，并直接管理手工备注与置顶备注。

## Existing Context

- 主界面目前由提词卡和事件流两列构成，入口在 [frontend/src/App.vue](H:\DouYin_llm\frontend\src\App.vue)。
- 事件流组件在 [frontend/src/components/EventFeed.vue](H:\DouYin_llm\frontend\src\components\EventFeed.vue)，当前只展示事件，不支持选中观众。
- 前端状态集中在 [frontend/src/stores/live.js](H:\DouYin_llm\frontend\src\stores\live.js)。
- 后端已经提供观众详情、记忆、备注相关接口，入口在 [backend/app.py](H:\DouYin_llm\backend\app.py)：
  - `GET /api/viewer`
  - `GET /api/viewer/memories`
  - `GET /api/viewer/notes`
  - `POST /api/viewer/notes`
  - `DELETE /api/viewer/notes/{note_id}`

## Chosen Approach

采用“点击事件流中的观众姓名，在右侧滑出详情工作台”的方案。

原因：

- 不打断现有提词主流程，主播仍能保留对主提词卡的关注。
- 复用现有页面布局，不需要改成全新信息架构。
- 与现有后端 API 能自然对接，第一版不用新增复杂后端能力。

## UI Structure

右侧工作台采用抽屉式面板，覆盖在事件流区域上方或贴靠右侧展开。

工作台分为 4 个区块：

1. Header
- 观众昵称
- `viewer_id`
- 关闭按钮
- 基础状态文案，例如“最近来过”“累计评论数”“送礼次数”

2. Profile Summary
- 首次出现时间
- 最近出现时间
- 评论数
- 礼物事件数
- 总礼物数
- 总钻石数
- 最近一句评论
- 最近一个礼物名

3. Semantic Memory
- 展示系统提取的 `viewer_memories`
- 每条显示：
  - `memory_text`
  - `memory_type`
  - `confidence`
  - `last_recalled_at`
  - `recall_count`
- 第一版只读，不支持前端直接编辑语义记忆

4. Notes Workspace
- 手工备注列表
- 支持新增备注
- 支持编辑已有备注
- 支持置顶 / 取消置顶
- 支持删除备注
- 置顶备注始终排在前面

5. Activity History
- 最近评论
- 最近送礼事件
- 最近场次
- 每块先限制条数，避免面板无限拉长

## Data Flow

### Open panel

1. 用户点击事件流中某条事件里的观众昵称
2. 前端从事件对象中拿到：
- `room_id`
- `viewer_id`
- `nickname`
3. Store 设置当前选中观众
4. 前端请求 `GET /api/viewer`
5. 将返回结果填充到工作台

### Notes actions

1. 新增/编辑备注时调用 `POST /api/viewer/notes`
2. 删除备注时调用 `DELETE /api/viewer/notes/{note_id}`
3. 成功后刷新当前观众详情，保证 notes 和 profile 同步

## Frontend Changes

### [frontend/src/components/EventFeed.vue](H:\DouYin_llm\frontend\src\components\EventFeed.vue)

- 给观众昵称加点击能力
- 抛出新事件，例如 `select-viewer`
- 事件载荷至少包含：
  - `roomId`
  - `viewerId`
  - `nickname`

### [frontend/src/stores/live.js](H:\DouYin_llm\frontend\src\stores\live.js)

- 增加当前选中观众状态
- 增加工作台开关状态
- 增加观众详情加载状态和错误状态
- 增加请求方法：
  - `openViewerWorkbench`
  - `closeViewerWorkbench`
  - `loadViewerDetail`
  - `saveViewerNote`
  - `deleteViewerNote`

### [frontend/src/App.vue](H:\DouYin_llm\frontend\src\App.vue)

- 将 `select-viewer` 事件接到 store
- 新增工作台组件挂载位

### New component

新增一个工作台组件，例如：

- [frontend/src/components/ViewerWorkbench.vue](H:\DouYin_llm\frontend\src\components\ViewerWorkbench.vue)

职责：

- 渲染抽屉 UI
- 展示画像、记忆、历史、备注
- 处理备注编辑交互

## Backend Changes

第一版尽量不新增接口。

优先直接复用现有 [backend/app.py](H:\DouYin_llm\backend\app.py) 中的接口。如果在实现时发现返回字段不足，再补最小后端增强，但不扩展到新的独立子系统。

## Error Handling

- 观众详情请求失败时，工作台显示明确错误态，不影响提词区和事件流继续运行。
- 当事件缺少 `viewer_id` 但有昵称时，允许以前端携带 `nickname` 回查。
- 备注保存失败时，保留输入内容并显示错误消息。
- 删除失败时保留当前列表状态，不清空工作台。

## Testing Strategy

前端至少覆盖：

- 点击事件流观众会打开工作台
- 工作台能加载观众详情
- 新增备注成功后列表刷新
- 编辑备注成功后内容更新
- 置顶备注排序正确
- 删除备注成功后从列表消失

后端如需补字段，追加针对接口返回结构的回归测试。

## Scope Guard

本次只做“单个观众详情工作台”。

明确不包含：

- 语义记忆编辑器
- 多观众批量管理
- 观众搜索页
- 反馈训练系统
- 新的向量召回/重排改造
