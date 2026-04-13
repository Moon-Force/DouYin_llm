# Frontend Locale Toggle Design

## Goal

让整个前端界面支持中英切换，默认中文，切换结果仅在当前页面会话内生效，刷新页面后恢复中文。

## Current Context

- 当前前端主要由 [App.vue](H:\DouYin_llm\frontend\src\App.vue) 组合多个组件。
- 文案目前散落在：
  - [StatusStrip.vue](H:\DouYin_llm\frontend\src\components\StatusStrip.vue)
  - [TeleprompterCard.vue](H:\DouYin_llm\frontend\src\components\TeleprompterCard.vue)
  - [EventFeed.vue](H:\DouYin_llm\frontend\src\components\EventFeed.vue)
  - [ViewerWorkbench.vue](H:\DouYin_llm\frontend\src\components\ViewerWorkbench.vue)
  - [LlmSettingsPanel.vue](H:\DouYin_llm\frontend\src\components\LlmSettingsPanel.vue)
- 当前 [live.js](H:\DouYin_llm\frontend\src\stores\live.js) 已管理主题、筛选、viewer workbench、LLM settings 等前端状态，适合作为 locale 状态入口。

## Chosen Approach

采用“前端本地字典 + store 内 `locale` 状态 + 组件统一取文案”的方案。

不采用完整 `vue-i18n` 的原因：

- 当前项目规模不大
- 只需要中英双语
- 需求明确是临时生效，不需要复杂国际化能力

## Persistence Behavior

- 默认语言固定为 `zh`
- 切换到 `en` 后只在当前页面会话内生效
- 不写入 `localStorage`
- 刷新页面后恢复 `zh`

## Frontend State

### [live.js](H:\DouYin_llm\frontend\src\stores\live.js)

新增：

- `locale`
- `setLocale`
- `toggleLocale`

默认值：

- `zh`

## Translation Source

新增一个轻量字典文件，例如：

- [i18n.js](H:\DouYin_llm\frontend\src\i18n.js)

结构：

```javascript
export const messages = {
  zh: { ... },
  en: { ... },
};

export function translate(locale, key) { ... }
```

## Scope

第一版覆盖静态界面文案，不覆盖：

- 数据库内文本
- 直播评论原文
- 模型生成的 suggestion 内容
- 后端返回的原始错误 detail

## Components To Update

第一版至少覆盖：

- [StatusStrip.vue](H:\DouYin_llm\frontend\src\components\StatusStrip.vue)
- [TeleprompterCard.vue](H:\DouYin_llm\frontend\src\components\TeleprompterCard.vue)
- [EventFeed.vue](H:\DouYin_llm\frontend\src\components\EventFeed.vue)
- [ViewerWorkbench.vue](H:\DouYin_llm\frontend\src\components\ViewerWorkbench.vue)
- [LlmSettingsPanel.vue](H:\DouYin_llm\frontend\src\components\LlmSettingsPanel.vue)

## Interaction Entry

在顶部状态条增加语言切换按钮：

- 当前为中文时显示：`EN`
- 当前为英文时显示：`中文`

点击后切换当前 `locale`

## Error Handling

- 前端内部自定义错误提示优先走字典翻译
- 后端返回 detail 暂时保持原样显示，不做强制翻译

## Testing Strategy

前端至少补一个 node-based smoke test，验证：

- 默认 `locale === 'zh'`
- `toggleLocale()` 能切到 `en`
- 再切一次回到 `zh`

## Scope Guard

本次只做：

- 中英双语切换
- 当前页面临时生效
- 静态界面文案覆盖

不做：

- 多语言持久化
- 浏览器语言自动检测
- 动态内容翻译
- `vue-i18n` 引入
