# 数据库说明

当前项目的长期存储默认使用 SQLite。

数据库文件位置：

- [live_prompter.db](D:/总的ai分析/确定版/data/live_prompter.db)

对应代码：

- [backend/memory/long_term.py](D:/总的ai分析/确定版/backend/memory/long_term.py)

这份文档只描述当前已经落地的表，不讨论未来扩展表。

## 数据流

消息进入数据库的流程是：

1. `tool/douyinLive-windows-amd64.exe` 抓取抖音直播消息
2. `client.py` 标准化事件后转发给后端
3. `backend/app.py` 收到 `/api/events`
4. `LongTermStore.persist_event(...)` 写入事件和用户画像
5. 如果生成了提词建议，`LongTermStore.persist_suggestion(...)` 写入建议

## 当前数据库文件

- `data/live_prompter.db`

只要后端在运行，新的事件和建议就会持续写入这个文件。

## 表结构总览

当前有 3 张核心表：

1. `events`
2. `user_profiles`
3. `suggestions`

---

## 1. events

用途：

- 保存每一条进入系统的直播事件
- 包括弹幕、关注、进场、系统消息等

主要字段：

- `event_id`
  - 事件唯一 ID
  - 主键

- `room_id`
  - 直播间标识

- `platform`
  - 平台名称
  - 当前固定为 `douyin`

- `event_type`
  - 标准化后的事件类型
  - 例如：
    - `comment`
    - `follow`
    - `member`
    - `gift`
    - `system`

- `method`
  - 原始抖音消息类型
  - 例如：
    - `WebcastChatMessage`
    - `WebcastMemberMessage`
    - `WebcastSocialMessage`

- `livename`
  - 直播间名称

- `user_id`
  - 用户 ID
  - 某些消息可能为空

- `nickname`
  - 用户昵称

- `content`
  - 消息内容
  - 对评论类事件最有意义

- `ts`
  - 时间戳

- `metadata_json`
  - 标准化后的附加信息
  - 例如动作类型、礼物名等

- `raw_json`
  - 原始事件 JSON
  - 用于调试和回溯

适合用来做什么：

- 回看直播消息历史
- 按房间过滤消息
- 按用户查最近发言
- 调试字段结构

---

## 2. user_profiles

用途：

- 保存用户画像雏形
- 当前是最简结构，不是完整 CRM

主键：

- `(room_id, nickname)`

注意：

- 当前按 `room_id + nickname` 做唯一键
- 这对“最简可跑版本”够用
- 但昵称理论上可能变化，所以它不是长期最稳的业务主键

主要字段：

- `room_id`
  - 所属直播间

- `nickname`
  - 用户昵称

- `user_id`
  - 用户 ID

- `interaction_count`
  - 该用户累计互动次数

- `latest_event_type`
  - 最近一次互动类型

- `latest_content`
  - 最近一次互动内容

- `updated_at`
  - 最近更新时间

适合用来做什么：

- 判断某用户是不是老观众
- 给模型提供最小用户历史
- 看最近一次说了什么

当前大模型确实会读取这里的数据：

- [backend/services/agent.py](D:/总的ai分析/确定版/backend/services/agent.py)

---

## 3. suggestions

用途：

- 保存系统生成的提词建议
- 不管来自在线 Qwen 还是规则兜底，都会落库

主要字段：

- `suggestion_id`
  - 建议唯一 ID
  - 主键

- `room_id`
  - 所属直播间

- `event_id`
  - 这条建议对应哪条事件

- `priority`
  - 优先级
  - 例如：
    - `high`
    - `medium`
    - `low`

- `reply_text`
  - 提词文本

- `tone`
  - 语气标签

- `reason`
  - 生成原因

- `confidence`
  - 置信度

- `created_at`
  - 建议创建时间

适合用来做什么：

- 回看系统给过什么建议
- 对比真实消息与生成话术
- 后续做反馈分析

---

## 当前版本的限制

这份数据库设计是“最简可跑版”，所以有几个明显限制：

1. 没有迁移系统
   - 当前是启动时直接建表

2. `user_profiles` 还比较薄
   - 只有最小用户历史

3. `suggestions` 表还没记录“是否被主播采用”
   - 只是把建议存下来了

4. 没有专门的 `sessions` 表
   - 当前没有单独记录每次开播场次

5. 没有索引优化
   - 数据量大后查询效率会下降

但对当前版本来说已经足够：

- 能长期保存消息
- 能长期保存建议
- 能给模型提供最基础的历史用户记录

## 如何查看数据库

你可以用任意 SQLite 工具打开：

- `data/live_prompter.db`

也可以直接用 Python 或 sqlite3 查询。

例如看最近 20 条事件：

```sql
SELECT room_id, event_type, nickname, content, ts
FROM events
ORDER BY ts DESC
LIMIT 20;
```

例如看最近 20 条建议：

```sql
SELECT room_id, priority, reply_text, tone, reason, confidence, created_at
FROM suggestions
ORDER BY created_at DESC
LIMIT 20;
```

例如看某个用户画像：

```sql
SELECT room_id, nickname, interaction_count, latest_event_type, latest_content, updated_at
FROM user_profiles
WHERE nickname = '某个昵称';
```

## 当前结论

当前数据库已经承担了“长期记忆”的最简版本职责：

- `events` 负责存消息历史
- `user_profiles` 负责存用户历史摘要
- `suggestions` 负责存提词历史

如果后面不扩复杂功能，这套结构已经够当前项目使用。
