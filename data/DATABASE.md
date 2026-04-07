# 数据库说明

当前长期存储文件：`data/live_prompter.db`

面向主播侧的核心表现在是：

1. `events`
2. `viewer_profiles`
3. `viewer_gifts`
4. `live_sessions`
5. `viewer_notes`
6. `suggestions`

旧表 `user_profiles` 仍保留做历史兼容，不再作为主读表。

## 1. events

事件流水表，保留每一条评论、进房、礼物等原始记录。

关键字段：

- `event_id`: 事件主键
- `room_id`: 当前系统房间号
- `source_room_id`: 原始消息里的真实 `roomId`
- `session_id`: 新增，从现在开始写入，表示这条事件属于哪一场直播
- `viewer_id`: 观众唯一标识，规则为 `user.id -> secUid -> shortId -> nickname`
- `user_id` / `short_id` / `sec_uid` / `nickname`: 原始用户身份字段
- `event_type`: `comment` / `member` / `gift` / `like` / `follow` / `system`
- `content`: 评论或事件文本
- `gift_name` / `gift_id` / `gift_count` / `gift_diamond_count`: 礼物相关字段
- `metadata_json` / `raw_json`: 标准化附加信息和原始消息

## 2. viewer_profiles

按 `(room_id, viewer_id)` 聚合的观众画像表。

关键字段：

- `total_event_count`
- `comment_count`
- `join_count`
- `gift_event_count`
- `total_gift_count`
- `total_diamond_count`
- `first_seen_at`
- `last_seen_at`
- `last_session_id`
- `last_comment`
- `last_join_at`
- `last_gift_name`
- `last_gift_at`

## 3. viewer_gifts

按 `(room_id, viewer_id, gift_name)` 聚合礼物历史。

关键字段：

- `gift_event_count`
- `total_gift_count`
- `total_diamond_count`
- `first_sent_at`
- `last_sent_at`

## 4. live_sessions

直播场次表。当前会在新事件写入时自动创建活动场次，并在切房或服务关闭时结束。

关键字段：

- `session_id`
- `room_id`
- `source_room_id`
- `livename`
- `status`: `active` / `ended`
- `started_at`
- `last_event_at`
- `ended_at`
- `event_count`
- `comment_count`
- `gift_event_count`
- `join_count`

说明：历史旧事件不会被强行伪造场次，`session_id` 从这次改造之后的新事件开始稳定写入。

## 5. viewer_notes

给主播或运营写观众备注。

关键字段：

- `note_id`
- `room_id`
- `viewer_id`
- `author`
- `content`
- `is_pinned`
- `created_at`
- `updated_at`

## 常用查询

查一个观众的总体画像：

```sql
SELECT *
FROM viewer_profiles
WHERE room_id = '841354217566'
  AND viewer_id = 'id:101789573293';
```

查一个观众的历史评论：

```sql
SELECT event_id, session_id, content, ts
FROM events
WHERE room_id = '841354217566'
  AND viewer_id = 'id:101789573293'
  AND event_type = 'comment'
ORDER BY ts DESC;
```

查一个观众送过的礼物聚合：

```sql
SELECT gift_name, gift_event_count, total_gift_count, total_diamond_count, last_sent_at
FROM viewer_gifts
WHERE room_id = '841354217566'
  AND viewer_id = 'id:101789573293'
ORDER BY last_sent_at DESC;
```

查当前活动场次：

```sql
SELECT *
FROM live_sessions
WHERE room_id = '841354217566'
  AND status = 'active';
```

查一个观众的备注：

```sql
SELECT author, content, is_pinned, updated_at
FROM viewer_notes
WHERE room_id = '841354217566'
  AND viewer_id = 'id:101789573293'
ORDER BY is_pinned DESC, updated_at DESC;
```
