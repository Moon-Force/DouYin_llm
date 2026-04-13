# LLM Settings Design

## Goal

让前端可以直接修改当前使用的模型名和系统提示词，并把改动持久化保存，保证后端重启后仍然生效。

## Current Context

- 当前模型配置来自 [config.py](H:\DouYin_llm\backend\config.py) 和 [`.env`](H:\DouYin_llm\.env)。
- 提词逻辑在 [agent.py](H:\DouYin_llm\backend\services\agent.py)，系统提示词仍然是代码内固定字符串。
- 前端当前有状态条 [StatusStrip.vue](H:\DouYin_llm\frontend\src\components\StatusStrip.vue)，但还没有“模型设置”入口。
- 项目已经使用 SQLite 做长期持久化，因此最适合把运行时可改配置也放进 SQLite，而不是直接回写 `.env`。

## Chosen Approach

采用“SQLite 配置表 + 后端设置接口 + 前端设置面板”的方案。

不采用直接写 `.env` 的原因：

- `.env` 不适合频繁更新的大文本提示词
- 文件写入的编码、并发和恢复都更脆弱
- 项目已经有 SQLite，放在数据库里更统一

## Persistence Model

新增一个运行时配置表，例如：

- `app_settings`

字段采用简单键值形式：

- `setting_key`
- `setting_value`
- `updated_at`

第一版只存这两个键：

- `llm_model_override`
- `system_prompt_override`

## Resolution Priority

后端读取实际生效配置时，优先级如下：

1. SQLite 中的 override
2. `.env` / `Settings` 里的默认值
3. 代码里的兜底默认值

这样可以保证：

- 前端保存后立即生效
- 重启后依旧生效
- 删除 override 后还能回退到 `.env`

## Backend Changes

### [long_term.py](H:\DouYin_llm\backend\memory\long_term.py)

新增对 `app_settings` 的读写支持：

- `get_setting(key)`
- `set_setting(key, value)`
- `delete_setting(key)`
- `get_llm_settings()`
- `save_llm_settings(model, system_prompt)`

### [app.py](H:\DouYin_llm\backend\app.py)

新增接口：

- `GET /api/settings/llm`
  - 返回当前生效的模型名、系统提示词、来源信息

- `PUT /api/settings/llm`
  - 保存前端传来的模型名和系统提示词
  - 成功后立即影响后续新生成的 suggestion

### [agent.py](H:\DouYin_llm\backend\services\agent.py)

不再把系统提示词完全写死。

改成：

- 模型名从“当前生效配置”读取
- system prompt 从“当前生效配置”读取

同时保留默认 prompt 作为兜底。

## Frontend Changes

### [live.js](H:\DouYin_llm\frontend\src\stores\live.js)

新增 LLM 设置状态：

- `llmSettings`
- `llmSettingsDraft`
- `isSavingLlmSettings`
- `llmSettingsError`
- `isLlmSettingsOpen`

新增动作：

- `loadLlmSettings`
- `openLlmSettings`
- `closeLlmSettings`
- `updateLlmModelDraft`
- `updateSystemPromptDraft`
- `saveLlmSettings`
- `resetLlmSettings`

### [StatusStrip.vue](H:\DouYin_llm\frontend\src\components\StatusStrip.vue)

新增入口按钮，例如：

- `Model Settings`

### New component

新增一个设置面板组件，例如：

- [LlmSettingsPanel.vue](H:\DouYin_llm\frontend\src\components\LlmSettingsPanel.vue)

内容包括：

- 模型名输入框
- 系统提示词多行文本框
- 保存按钮
- 重置为默认值按钮
- 错误提示

## Runtime Behavior

- 前端保存后，后端后续新生成的 suggestion 直接使用新配置
- 已经生成的 suggestion 不会回溯重算
- 重启后继续从 SQLite 中读取 override

## Error Handling

- 如果模型名为空：
  - 后端返回 400

- 如果 system prompt 为空：
  - 允许为空时回退默认 prompt
  - 或保存为空字符串并在 agent 端回退默认 prompt

第一版建议：

- 模型名必填
- system prompt 可为空，空则回退默认 prompt

## Scope Guard

本次只做：

- 模型名编辑
- 系统提示词编辑
- SQLite 持久化
- 前端可视化设置入口

不做：

- 多套 prompt 模板管理
- 按房间区分 prompt
- 按观众区分 prompt
- prompt 版本历史
