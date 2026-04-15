# 语义健康状态可见性设计

## 目标

把“严格模式已启用、语义后端是否真实可用、不可用原因是什么”这组关键信息，补到项目文档和前端状态栏里。

本设计要解决两个问题：

- 配置层已经支持 `EMBEDDING_STRICT`，但 README 和 `.env.example` 还没有把它讲清楚
- 后端 `/health` 已经返回语义健康字段，但前端看不到，用户无法第一时间知道当前是不是在用真实语义召回

## 适用范围

包含：

- 更新 `README.md`
- 更新 `.env.example`
- 前端 store 接收语义健康字段
- `StatusStrip` 展示语义后端状态和错误原因

不包含：

- 禁用前端其他依赖语义召回的功能区
- 新增更复杂的运维诊断页
- 修改后端语义健康字段结构

## 设计原则

- 优先回答“当前语义后端到底是不是可用”
- 当后端不可用时，前端要明确告警，而不是埋在日志里
- 告警信息要直接展示原因，不要求用户去翻后端返回
- 不把状态栏做成沉重的错误面板

## 方案比较

### 方案一：只补文档

仅更新 README 和 `.env.example`，不改前端。

优点：

- 改动最小
- 风险最低

缺点：

- strict mode 仍然只停留在“知道的人会配”
- 运行时不可见

### 方案二：推荐方案，文档 + 状态栏告警

同时补文档和前端状态栏：

- README 说明 `EMBEDDING_STRICT`
- `.env.example` 增加配置项
- 状态栏新增“语义后端状态”
- `semantic_backend_ready=false` 时高亮告警，并直接展示 `semantic_backend_reason`

优点：

- 配置说明和运行态观察形成闭环
- 用户能第一时间知道当前是不是在用真语义后端
- 改动范围可控

缺点：

- 比纯文档多改几处前端文件

### 方案三：文档 + 状态栏 + 全局禁用态

除状态栏告警外，再把相关前端区域统一显示为“语义后端不可用”。

优点：

- 约束更强

缺点：

- 超出当前需求
- 会把前端交互复杂度拉高

### 推荐方案

采用方案二：**文档补齐 + 状态栏告警**。

## 文档设计

### `README.md`

补充以下内容：

- `EMBEDDING_STRICT` 的作用
- 开启后会阻止哪些 fallback
- 推荐在追求真实语义召回时显式开启
- `/health` 里新增字段的含义

建议文案重点：

- `EMBEDDING_STRICT=false`：开发期可保留兜底
- `EMBEDDING_STRICT=true`：要求真实 embedding 与真实向量检索，失败时直接报错

### `.env.example`

增加：

- `EMBEDDING_STRICT=false`

并放在 embedding 配置区域，避免与 LLM 配置混在一起。

## 前端设计

### 展示位置

在 `StatusStrip` 中新增一块“语义后端状态”区域。

推荐放在现有状态卡片区，与“模型状态”并列显示，作为新的状态卡片，而不是塞进连接状态 badge 里。

原因：

- 连接状态和语义状态不是一个维度
- 把语义状态单独成块更容易扫读
- 后续若补充召回指标，也更容易扩展

### 展示规则

当 `semantic_backend_ready=true` 时：

- 显示“语义后端正常”
- 若 `embedding_strict=true`，补一句“严格模式已开启”

当 `semantic_backend_ready=false` 时：

- 高亮显示“语义后端异常”
- 直接展示 `semantic_backend_reason`
- 若 `embedding_strict=true`，明确这是严格模式下的阻断条件

### 视觉层级

成功态：

- 使用与当前状态栏一致的低饱和成功色

异常态：

- 使用较明显的告警色
- 但不要比连接断开还更夸张

原因说明：

- 使用 1 到 2 行小字展示
- 保证不截断到完全不可读

## 数据流设计

### 后端返回字段

后端已提供：

- `embedding_strict`
- `semantic_backend_ready`
- `semantic_backend_reason`

本设计不修改后端字段结构，只消费现有返回。

### Store

`frontend/src/stores/live.js` 需要：

- 在状态中保存这三个字段
- 在 bootstrap 时接收
- 在切房后新快照中同步

### 组件

`frontend/src/components/StatusStrip.vue` 只负责展示，不负责推断。

如果需要整理文案或状态色映射，可在 presenter 层新增一个很轻量的 helper，但不强制拆分新文件。

## i18n 设计

需要在 `frontend/src/i18n.js` 中新增文案：

- `status.semantic.title`
- `status.semantic.ready`
- `status.semantic.unavailable`
- `status.semantic.strictEnabled`
- `status.semantic.reason`

中英文都要补齐，保证切换语言时语义状态不会退回 key。

## 测试设计

至少覆盖以下内容：

### `frontend/src/stores/live.test.mjs`

- bootstrap 返回语义健康字段时，store 能正确接收
- 空房间下不连 SSE 的现有逻辑不回退

### `frontend/src/components/status-strip-layout.test.mjs`

- `StatusStrip.vue` 中存在语义状态区域的结构标记
- 语义状态文案 key 被引用
- 原有布局断言仍通过

## 完成标准

满足以下条件即可视为完成：

- `README.md` 明确说明 `EMBEDDING_STRICT`
- `.env.example` 包含 `EMBEDDING_STRICT`
- 前端状态栏能展示语义后端健康状态
- 当语义后端异常时，前端能直接显示原因
- store 和状态栏测试覆盖新增字段
- 该功能单独提交，不与其他未完成改动混在一起
