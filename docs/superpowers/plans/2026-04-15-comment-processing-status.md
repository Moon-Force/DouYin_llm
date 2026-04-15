# Comment Processing Status Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让前端事件流中的每一条新评论显示其后端处理轨迹，包括落库、记忆抽取/保存、记忆召回、提词生成。

**Architecture:** 后端在 `process_event()` 中构建逐条评论的 `processing_status`，并直接挂到实时推送的事件 payload 上；前端复用现有事件流数据结构，在 `EventFeed` 中为评论渲染紧凑状态标签和可展开详情。历史 bootstrap 事件不做回填，只保证新进入系统的评论有状态。

**Tech Stack:** FastAPI、Pydantic、Vue 3、Pinia、Python unittest、前端现有 presenter/store 测试。

---

## 文件结构

- 修改 [backend/schemas/live.py](/H:/DouYin_llm/backend/schemas/live.py)：为 `LiveEvent` 增加评论处理状态模型字段
- 修改 [backend/services/agent.py](/H:/DouYin_llm/backend/services/agent.py)：暴露本次评论是否命中观众记忆召回以及命中的 memory IDs
- 修改 [backend/app.py](/H:/DouYin_llm/backend/app.py)：在 `process_event()` 中组装 `processing_status`
- 修改 [tests/test_agent.py](/H:/DouYin_llm/tests/test_agent.py)：补 recall metadata 相关单测
- 新增或修改后端事件处理测试文件：验证 `process_event()` 对评论状态的组装
- 修改 [frontend/src/stores/live.js](/H:/DouYin_llm/frontend/src/stores/live.js)：保持事件对象上的 `processing_status`
- 修改 [frontend/src/components/EventFeed.vue](/H:/DouYin_llm/frontend/src/components/EventFeed.vue)：渲染状态标签与详情
- 如有必要，修改 [frontend/src/i18n.js](/H:/DouYin_llm/frontend/src/i18n.js)：补中文/英文状态文案
- 新增或修改前端组件测试：验证评论状态标签与详情展示

### Task 1: 后端数据模型与 Agent 召回元数据

**Files:**
- Modify: [backend/schemas/live.py](/H:/DouYin_llm/backend/schemas/live.py)
- Modify: [backend/services/agent.py](/H:/DouYin_llm/backend/services/agent.py)
- Test: [tests/test_agent.py](/H:/DouYin_llm/tests/test_agent.py)

- [ ] **Step 1: 先写失败测试，约束 Agent 能暴露召回元数据**

```python
def test_build_context_returns_recalled_memory_ids(self):
    vector_memory = MagicMock()
    vector_memory.similar_memories.return_value = [
        {"memory_id": "m1", "memory_text": "likes ramen", "score": 0.9, "metadata": {}},
        {"memory_id": "m2", "memory_text": "from hangzhou", "score": 0.8, "metadata": {}},
    ]
    long_term_store = MagicMock()
    long_term_store.get_user_profile.return_value = {}
    agent = LivePromptAgent(make_settings(), vector_memory, long_term_store)

    context = agent.build_context(make_event(content="I like ramen"), [])

    self.assertEqual(context["recalled_memory_ids"], ["m1", "m2"])
```

- [ ] **Step 2: 运行测试确认失败**

Run: `python -m unittest tests.test_agent -v`

Expected: 新增断言失败，提示 `recalled_memory_ids` 尚不存在。

- [ ] **Step 3: 最小实现**

在 `backend/services/agent.py` 的 `build_context()` 返回结构里增加：

```python
"recalled_memory_ids": [
    item["memory_id"]
    for item in viewer_memories[:2]
    if item.get("memory_id")
],
```

并在 `backend/schemas/live.py` 新增状态模型：

```python
class CommentProcessingStatus(BaseModel):
    received: bool = False
    persisted: bool = False
    memory_extraction_attempted: bool = False
    memory_saved: bool = False
    saved_memory_ids: list[str] = Field(default_factory=list)
    memory_recall_attempted: bool = False
    memory_recalled: bool = False
    recalled_memory_ids: list[str] = Field(default_factory=list)
    suggestion_generated: bool = False
    suggestion_id: str = ""
```

再把 `LiveEvent` 增加：

```python
processing_status: CommentProcessingStatus | None = None
```

- [ ] **Step 4: 运行测试确认通过**

Run: `python -m unittest tests.test_agent -v`

Expected: `tests.test_agent` 全绿。

- [ ] **Step 5: Commit**

```bash
git add backend/schemas/live.py backend/services/agent.py tests/test_agent.py
git commit -m "feat: add comment processing status model"
```

### Task 2: 后端 process_event 组装逐条评论状态

**Files:**
- Modify: [backend/app.py](/H:/DouYin_llm/backend/app.py)
- Test: [tests/test_comment_processing_status.py](/H:/DouYin_llm/tests/test_comment_processing_status.py)

- [ ] **Step 1: 写失败测试，验证评论事件被推送时带完整 processing_status**

```python
async def test_process_event_attaches_processing_status(self):
    event = make_event(content="hello")
    suggestion = SimpleNamespace(suggestion_id="sug-1", model_dump=lambda: {"suggestion_id": "sug-1"})
    app_module.agent.maybe_generate = MagicMock(return_value=suggestion)
    app_module.agent.build_context = MagicMock(return_value={
        "recent_events": [],
        "user_profile": {},
        "viewer_memories": [],
        "viewer_memory_texts": [],
        "recalled_memory_ids": ["mem-9"],
    })
```

测试需要断言推送出去的 `event` envelope 里：

```python
payload["processing_status"]["persisted"] is True
payload["processing_status"]["memory_recall_attempted"] is True
payload["processing_status"]["recalled_memory_ids"] == ["mem-9"]
payload["processing_status"]["suggestion_generated"] is True
```

- [ ] **Step 2: 运行测试确认失败**

Run: `python -m unittest tests.test_comment_processing_status -v`

Expected: 失败，提示 `processing_status` 缺失或字段不完整。

- [ ] **Step 3: 最小实现**

在 `backend/app.py` 的 `process_event()` 中：

1. 初始化状态对象
2. 落库后标记 `persisted`
3. 对评论事件调用 agent 时获取 recall metadata
4. 记忆抽取前标记 `memory_extraction_attempted`
5. 保存记忆后写入 `memory_saved` 和 `saved_memory_ids`
6. 生成 suggestion 后写入 `suggestion_generated` 和 `suggestion_id`
7. 在发布 `event` 前把状态挂到 `event.processing_status`

建议骨架：

```python
processing_status = CommentProcessingStatus(received=True)
long_term_store.persist_event(event)
processing_status.persisted = True
...
event.processing_status = processing_status
await broker.publish(event_envelope("event", event.model_dump()))
```

如果某条评论走跳过召回路径，则保持：

```python
processing_status.memory_recall_attempted = False
processing_status.memory_recalled = False
processing_status.recalled_memory_ids = []
```

- [ ] **Step 4: 运行测试确认通过**

Run: `python -m unittest tests.test_comment_processing_status -v`

Expected: 新测试通过。

- [ ] **Step 5: Commit**

```bash
git add backend/app.py tests/test_comment_processing_status.py
git commit -m "feat: attach per-comment processing status"
```

### Task 3: 前端事件流展示评论处理状态

**Files:**
- Modify: [frontend/src/components/EventFeed.vue](/H:/DouYin_llm/frontend/src/components/EventFeed.vue)
- Modify: [frontend/src/stores/live.js](/H:/DouYin_llm/frontend/src/stores/live.js)
- Modify: [frontend/src/i18n.js](/H:/DouYin_llm/frontend/src/i18n.js)
- Test: [frontend/src/components/event-feed-processing-status.test.mjs](/H:/DouYin_llm/frontend/src/components/event-feed-processing-status.test.mjs)

- [ ] **Step 1: 写失败测试，约束评论事件渲染 4 个核心标签**

```javascript
assert.match(html, /已落库/)
assert.match(html, /已保存记忆/)
assert.match(html, /命中召回/)
assert.match(html, /已生成提词/)
```

同时再写一条非评论事件断言：

```javascript
assert.doesNotMatch(html, /已落库/)
```

- [ ] **Step 2: 运行测试确认失败**

Run: `node frontend/src/components/event-feed-processing-status.test.mjs`

Expected: 失败，当前组件还没有这些标签。

- [ ] **Step 3: 最小实现**

在 `EventFeed.vue` 里增加：

- 判断是否是评论事件且存在 `processing_status`
- 根据状态渲染四组 badge
- 增加一个轻量详情展开区，显示 `saved_memory_ids`、`recalled_memory_ids`、`suggestion_id`

建议提取辅助函数：

```javascript
function commentProcessingBadges(event) {
  const status = event.processing_status;
  if (event.event_type !== "comment" || !status) {
    return [];
  }
  return [
    status.persisted ? t("feed.processing.persisted") : t("feed.processing.notPersisted"),
    status.memory_saved ? t("feed.processing.memorySaved") : t("feed.processing.noMemorySaved"),
    status.memory_recalled ? t("feed.processing.memoryRecalled") : t("feed.processing.noMemoryRecalled"),
    status.suggestion_generated ? t("feed.processing.suggestionGenerated") : t("feed.processing.noSuggestionGenerated"),
  ];
}
```

在 `i18n.js` 增加对应中英文键。

`live.js` 保持事件对象原样写入 `events.value`，不要剥离 `processing_status`。

- [ ] **Step 4: 运行测试确认通过**

Run: `node frontend/src/components/event-feed-processing-status.test.mjs`

Expected: 新测试通过。

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/EventFeed.vue frontend/src/stores/live.js frontend/src/i18n.js frontend/src/components/event-feed-processing-status.test.mjs
git commit -m "feat: show comment processing status in event feed"
```

### Task 4: 全量回归验证

**Files:**
- Verify only

- [ ] **Step 1: 跑后端测试**

Run:

```bash
python -m unittest tests.test_agent tests.test_comment_processing_status tests.test_vector_store tests.test_rebuild_embeddings tests.test_llm_settings tests.test_empty_room_bootstrap tests.test_embedding_service
```

Expected: 全部通过。

- [ ] **Step 2: 跑前端相关测试**

Run:

```bash
node frontend/src/components/event-feed-processing-status.test.mjs
node frontend/src/components/status-strip-presenter.test.mjs
node frontend/src/stores/live.test.mjs
```

Expected: 全部通过。

- [ ] **Step 3: 手动检查说明文档是否需要补充**

如果前端交互或后端 payload 字段发生用户可见变化，补充到：

- [README.md](/H:/DouYin_llm/README.md)

- [ ] **Step 4: Commit**

```bash
git add README.md
git commit -m "docs: document comment processing status"
```

## 自检

- 规格要求“只处理新评论、挂在现有事件流、显示四个核心标签、可展开详情、不新增状态表”，以上任务都已覆盖。
- 计划中没有使用 `TODO`、`TBD` 或“自行处理”这类占位语句。
- 字段名在任务间保持一致，统一使用 `processing_status`、`saved_memory_ids`、`recalled_memory_ids`、`suggestion_id`。
