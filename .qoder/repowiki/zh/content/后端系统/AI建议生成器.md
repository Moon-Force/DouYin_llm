# AI建议生成器

<cite>
**本文档引用的文件**
- [backend/services/agent.py](file://backend/services/agent.py)
- [backend/memory/session_memory.py](file://backend/memory/session_memory.py)
- [backend/memory/vector_store.py](file://backend/memory/vector_store.py)
- [backend/memory/long_term.py](file://backend/memory/long_term.py)
- [backend/schemas/live.py](file://backend/schemas/live.py)
- [backend/config.py](file://backend/config.py)
- [backend/app.py](file://backend/app.py)
- [backend/services/broker.py](file://backend/services/broker.py)
- [backend/services/collector.py](file://backend/services/collector.py)
- [tool/config.yaml](file://tool/config.yaml)
- [README.md](file://README.md)
- [requirements.txt](file://requirements.txt)
</cite>

## 目录
1. [简介](#简介)
2. [项目结构](#项目结构)
3. [核心组件](#核心组件)
4. [架构概览](#架构概览)
5. [详细组件分析](#详细组件分析)
6. [依赖关系分析](#依赖关系分析)
7. [性能考虑](#性能考虑)
8. [故障排除指南](#故障排除指南)
9. [结论](#结论)
10. [附录](#附录)

## 简介

AI建议生成器是一个专为抖音直播场景设计的实时提词系统，能够从直播事件流中智能生成主播可直接使用的口头建议。该系统采用双模式支持架构，结合在线AI模型和本地规则引擎，确保在各种网络条件下都能提供稳定的建议服务。

系统的核心功能包括：
- 实时直播事件采集和标准化
- 多层次记忆系统（短期、长期、向量检索）
- 智能上下文构建算法
- 双模式建议生成（AI模型 + 本地规则）
- 实时状态监控和错误统计
- 适配器模式的AI模型集成

## 项目结构

该项目采用清晰的分层架构，主要分为以下模块：

```mermaid
graph TB
subgraph "工具层"
Tool[douyinLive.exe<br/>WebSocket消息源]
end
subgraph "后端服务层"
App[FastAPI应用入口]
Config[配置管理]
Broker[事件总线]
Collector[直播采集器]
end
subgraph "业务逻辑层"
Agent[LivePromptAgent<br/>AI建议生成器]
Services[业务服务]
end
subgraph "数据存储层"
SessionMem[短期记忆<br/>SessionMemory]
LongTerm[长期存储<br/>LongTermStore]
VectorMem[向量检索<br/>VectorMemory]
end
subgraph "前端展示层"
Frontend[Vue.js前端]
end
Tool --> Collector
Collector --> App
App --> SessionMem
App --> LongTerm
App --> VectorMem
App --> Agent
Agent --> SessionMem
Agent --> LongTerm
Agent --> VectorMem
App --> Broker
Broker --> Frontend
```

**图表来源**
- [backend/app.py:1-220](file://backend/app.py#L1-L220)
- [backend/services/agent.py:1-393](file://backend/services/agent.py#L1-L393)

**章节来源**
- [README.md:21-349](file://README.md#L21-L349)

## 核心组件

### LivePromptAgent - AI建议生成器

LivePromptAgent是系统的核心组件，负责智能建议生成。它实现了双模式支持架构，能够在在线AI模型和本地规则引擎之间无缝切换。

#### 主要特性

1. **双模式支持系统**
   - 在线OpenAI兼容接口模式
   - 本地启发式规则模式
   - 自动故障转移机制

2. **智能上下文构建**
   - 最近事件窗口（8个事件）
   - 相似历史片段检索（3个）
   - 用户画像分析

3. **状态监控**
   - 模型运行状态跟踪
   - 错误统计和日志记录
   - 实时性能指标

**章节来源**
- [backend/services/agent.py:23-393](file://backend/services/agent.py#L23-L393)

### 记忆系统

系统实现了多层次的记忆架构，确保能够有效利用历史信息：

1. **短期记忆**（SessionMemory）
   - Redis持久化或进程内内存
   - 最近事件和建议缓存
   - TTL过期管理

2. **长期存储**（LongTermStore）
   - SQLite数据库
   - 用户画像和交互历史
   - 会话管理和统计

3. **向量检索**（VectorMemory）
   - Chroma向量数据库
   - 文本相似度匹配
   - 哈希嵌入函数

**章节来源**
- [backend/memory/session_memory.py:17-113](file://backend/memory/session_memory.py#L17-L113)
- [backend/memory/long_term.py:36-750](file://backend/memory/long_term.py#L36-L750)
- [backend/memory/vector_store.py:52-108](file://backend/memory/vector_store.py#L52-L108)

## 架构概览

系统采用事件驱动的异步架构，通过WebSocket连接实时直播消息源，经过标准化处理后进入建议生成流程。

```mermaid
sequenceDiagram
participant Tool as 抖音消息源
participant Collector as 直播采集器
participant App as FastAPI应用
participant Agent as AI建议生成器
participant Memory as 记忆系统
participant Frontend as 前端展示
Tool->>Collector : WebSocket直播消息
Collector->>App : 标准化LiveEvent
App->>Memory : 存储事件和建议
App->>Agent : 触发建议生成
Agent->>Memory : 构建上下文
Agent->>Agent : 双模式决策
Agent->>App : 返回建议
App->>Memory : 持久化建议
App->>Frontend : 实时推送
App->>Frontend : 状态更新
```

**图表来源**
- [backend/app.py:61-78](file://backend/app.py#L61-L78)
- [backend/services/agent.py:73-114](file://backend/services/agent.py#L73-L114)

## 详细组件分析

### LivePromptAgent实现详解

#### 双模式支持系统

LivePromptAgent实现了智能的双模式切换机制：

```mermaid
flowchart TD
Start([开始建议生成]) --> CheckMode{检查LLM模式}
CheckMode --> |非启发式模式| TryModel[尝试在线模型]
CheckMode --> |启发式模式| UseHeuristic[使用本地规则]
TryModel --> ModelSuccess{模型调用成功?}
ModelSuccess --> |是| MarkOK[标记状态: ok]
ModelSuccess --> |否| MarkFallback[标记状态: fallback]
MarkFallback --> UseHeuristic
UseHeuristic --> GeneratePayload[生成建议负载]
MarkOK --> GeneratePayload
GeneratePayload --> ReturnSuggestion[返回建议对象]
```

**图表来源**
- [backend/services/agent.py:96-114](file://backend/services/agent.py#L96-L114)

#### 上下文构建算法

系统采用多维度上下文构建策略：

```mermaid
classDiagram
class ContextBuilder {
+build_context(event, recent_events) dict
+similar_history_limit : 3
+recent_events_limit : 8
+extract_user_profile() dict
+extract_similar_history() list
+build_final_context() dict
}
class VectorMemory {
+similar(text, limit) list
+add_event(event) void
+embedding_function : HashEmbeddingFunction
}
class LongTermStore {
+get_user_profile(room_id, actor) dict
+viewer_event_history() list
+viewer_gift_history() list
}
ContextBuilder --> VectorMemory : "相似历史检索"
ContextBuilder --> LongTermStore : "用户画像获取"
```

**图表来源**
- [backend/services/agent.py:56-71](file://backend/services/agent.py#L56-L71)
- [backend/memory/vector_store.py:85-108](file://backend/memory/vector_store.py#L85-L108)
- [backend/memory/long_term.py:718-734](file://backend/memory/long_term.py#L718-L734)

#### 建议生成决策流程

系统实现了复杂的决策逻辑，根据不同事件类型和上下文条件生成最优建议：

```mermaid
flowchart TD
EventReceived[事件到达] --> EventType{事件类型检查}
EventType --> |comment| BuildCommentContext[构建评论上下文]
EventType --> |gift| BuildGiftContext[构建礼物上下文]
EventType --> |follow| BuildFollowContext[构建关注上下文]
EventType --> |其他| SkipGeneration[跳过生成]
BuildCommentContext --> CheckKeywords{关键词检测}
CheckKeywords --> |价格相关| PricePriority[高优先级建议]
CheckKeywords --> |健康相关| HealthPriority[中等优先级建议]
CheckKeywords --> |相似历史| SimilarHistory[中等优先级建议]
CheckKeywords --> |普通评论| NormalComment[低优先级建议]
BuildGiftContext --> GiftPriority[高优先级感谢建议]
BuildFollowContext --> FollowPriority[中等优先级欢迎建议]
PricePriority --> GenerateReply[生成回复文本]
HealthPriority --> GenerateReply
SimilarHistory --> GenerateReply
NormalComment --> GenerateReply
GiftPriority --> GenerateReply
FollowPriority --> GenerateReply
GenerateReply --> SetTone[设置语调]
SetTone --> SetConfidence[设置置信度]
SetConfidence --> ReturnSuggestion[返回建议]
```

**图表来源**
- [backend/services/agent.py:115-181](file://backend/services/agent.py#L115-L181)

#### AI模型集成与适配器模式

系统采用适配器模式集成多种AI模型：

```mermaid
classDiagram
class LivePromptAgent {
+settings : Settings
+vector_memory : VectorMemory
+long_term_store : LongTermStore
+_generate_with_openai_compatible(event, context) dict
+_parse_model_json(content) dict
+_normalize_model_payload(parsed) dict
}
class Settings {
+llm_mode : str
+llm_base_url : str
+llm_model : str
+llm_api_key : str
+llm_temperature : float
+resolved_llm_base_url() str
+resolved_llm_model() str
}
class OpenAICompatibleAdapter {
+call_api(request) dict
+validate_response(response) bool
+extract_payload(response) dict
}
LivePromptAgent --> Settings : "使用配置"
LivePromptAgent --> OpenAICompatibleAdapter : "适配器模式"
```

**图表来源**
- [backend/services/agent.py:183-329](file://backend/services/agent.py#L183-L329)
- [backend/config.py:40-94](file://backend/config.py#L40-L94)

**章节来源**
- [backend/services/agent.py:96-393](file://backend/services/agent.py#L96-L393)

### 记忆系统详细分析

#### SessionMemory - 短期记忆

短期记忆系统提供了灵活的存储策略：

```mermaid
flowchart TD
Init[初始化] --> CheckRedis{Redis可用?}
CheckRedis --> |是| UseRedis[使用Redis]
CheckRedis --> |否| UseMemory[使用进程内内存]
UseRedis --> LPush[LPUSH操作]
UseRedis --> LTrim[LTRIM限制]
UseRedis --> Expire[设置TTL]
UseMemory --> AppendLeft[appendleft操作]
UseMemory --> DequeMaxLen[deque最大长度]
LPush --> Return[返回]
LTrim --> Return
Expire --> Return
AppendLeft --> Return
DequeMaxLen --> Return
```

**图表来源**
- [backend/memory/session_memory.py:17-84](file://backend/memory/session_memory.py#L17-L84)

#### VectorMemory - 向量检索

向量检索系统实现了智能降级策略：

```mermaid
flowchart TD
AddEvent[添加事件] --> CheckCollection{Chroma可用?}
CheckCollection --> |是| UseChroma[使用Chroma]
CheckCollection --> |否| UseHash[使用哈希嵌入]
UseChroma --> CreateDocument[创建文档]
UseChroma --> CreateMetadata[创建元数据]
UseChroma --> Embeddings[计算嵌入]
UseChroma --> Upsert[UPsert操作]
UseHash --> ExtractTokens[提取词汇]
UseHash --> HashEmbedding[哈希嵌入]
UseHash --> NormalizeVector[向量归一化]
UseHash --> StoreItems[存储项目]
SimilarQuery[相似查询] --> CheckCollection2{Chroma可用?}
CheckCollection2 --> |是| QueryChroma[查询Chroma]
CheckCollection2 --> |否| TextSimilarity[文本相似度]
QueryChroma --> ReturnResults[返回结果]
TextSimilarity --> ReturnResults
```

**图表来源**
- [backend/memory/vector_store.py:64-108](file://backend/memory/vector_store.py#L64-L108)

**章节来源**
- [backend/memory/session_memory.py:17-113](file://backend/memory/session_memory.py#L17-L113)
- [backend/memory/vector_store.py:19-108](file://backend/memory/vector_store.py#L19-L108)

### 配置管理系统

系统提供了灵活的配置管理机制：

```mermaid
classDiagram
class Settings {
+app_host : str
+app_port : int
+room_id : str
+collector_enabled : bool
+llm_mode : str
+llm_base_url : str
+llm_model : str
+llm_api_key : str
+llm_temperature : float
+llm_timeout_seconds : float
+ensure_dirs() void
+resolved_llm_base_url() str
+resolved_llm_model() str
}
class EnvironmentConfig {
+load_dotenv() void
+read_env_file() void
+parse_env_line(line) tuple
}
Settings --> EnvironmentConfig : "配置加载"
```

**图表来源**
- [backend/config.py:40-94](file://backend/config.py#L40-L94)

**章节来源**
- [backend/config.py:11-94](file://backend/config.py#L11-L94)

## 依赖关系分析

系统采用了松耦合的设计，各组件之间的依赖关系清晰明确：

```mermaid
graph TB
subgraph "核心依赖"
FastAPI[FastAPI框架]
Websocket[WebSocket客户端]
Pydantic[Pydantic数据模型]
end
subgraph "可选依赖"
Redis[Redis缓存]
Chroma[Chroma向量数据库]
Sqlite[SQLite数据库]
end
subgraph "系统组件"
Agent[LivePromptAgent]
Collector[DouyinCollector]
Memory[Memory系统]
Broker[EventBroker]
end
FastAPI --> Agent
Websocket --> Collector
Pydantic --> Agent
Pydantic --> Collector
Pydantic --> Memory
Redis --> Memory
Chroma --> Memory
Sqlite --> Memory
Agent --> Memory
Collector --> Agent
Broker --> Agent
```

**图表来源**
- [requirements.txt:1-6](file://requirements.txt#L1-L6)
- [backend/app.py:13-21](file://backend/app.py#L13-L21)

**章节来源**
- [requirements.txt:1-6](file://requirements.txt#L1-L6)
- [backend/app.py:13-21](file://backend/app.py#L13-L21)

## 性能考虑

### 异步处理架构

系统采用异步编程模式，确保高并发场景下的性能表现：

1. **事件驱动处理**
   - WebSocket消息异步接收
   - 事件处理异步执行
   - 建议生成异步触发

2. **内存优化策略**
   - 事件窗口大小限制
   - 向量检索结果限制
   - 缓存过期管理

3. **网络优化**
   - 连接池管理
   - 超时控制
   - 重连机制

### 缓存策略

系统实现了多层次的缓存机制：

```mermaid
flowchart TD
Request[请求到达] --> CheckSession{检查短期缓存}
CheckSession --> |命中| ReturnSession[返回短期缓存]
CheckSession --> |未命中| CheckLongTerm{检查长期缓存}
CheckLongTerm --> |命中| ReturnLongTerm[返回长期缓存]
CheckLongTerm --> |未命中| GenerateNew[生成新数据]
GenerateNew --> StoreSession[存储到短期缓存]
StoreSession --> StoreLongTerm[存储到长期缓存]
StoreLongTerm --> ReturnNew[返回新数据]
```

### 错误处理和恢复

系统具备完善的错误处理机制：

1. **网络异常处理**
   - 连接超时检测
   - 断线自动重连
   - 重试策略

2. **AI模型异常处理**
   - 请求失败回退
   - 结果格式验证
   - 错误日志记录

3. **内存溢出防护**
   - 队列长度限制
   - 内存使用监控
   - 自动清理机制

## 故障排除指南

### 常见问题诊断

#### AI模型集成问题

**问题症状**：建议生成失败，返回启发式模式

**诊断步骤**：
1. 检查网络连接状态
2. 验证API密钥配置
3. 查看模型响应格式
4. 检查超时设置

**解决方案**：
- 确认网络可达性
- 验证API密钥有效性
- 调整超时参数
- 检查模型兼容性

#### 记忆系统问题

**问题症状**：历史数据丢失或检索异常

**诊断步骤**：
1. 检查Redis连接状态
2. 验证Chroma数据库完整性
3. 查看SQLite表结构
4. 检查磁盘空间

**解决方案**：
- 重启Redis服务
- 重建Chroma集合
- 执行数据库修复
- 清理磁盘空间

#### 前端连接问题

**问题症状**：前端无法接收实时更新

**诊断步骤**：
1. 检查SSE连接状态
2. 验证WebSocket连接
3. 查看事件总线状态
4. 检查CORS配置

**解决方案**：
- 重启后端服务
- 检查防火墙设置
- 验证跨域配置
- 更新前端版本

**章节来源**
- [backend/services/agent.py:222-285](file://backend/services/agent.py#L222-L285)
- [backend/memory/session_memory.py:11-17](file://backend/memory/session_memory.py#L11-L17)

## 结论

AI建议生成器是一个设计精良的实时直播提词系统，具有以下优势：

1. **双模式可靠性**：在线AI模型与本地规则的智能切换确保系统稳定性
2. **多层次记忆**：短期、长期、向量检索的组合提供丰富的上下文信息
3. **适配器模式**：灵活的AI模型集成支持多种服务提供商
4. **异步架构**：高性能的事件驱动处理满足实时性需求
5. **完整监控**：全面的状态跟踪和错误统计便于运维管理

系统在抖音直播场景中表现出色，能够有效提升主播的互动效率和直播质量。通过合理的配置和调优，可以在不同环境下获得最佳的性能表现。

## 附录

### 配置选项说明

#### 基础配置
- `ROOM_ID`: 直播间ID
- `APP_HOST`: 应用监听地址
- `APP_PORT`: 应用监听端口

#### 采集配置
- `COLLECTOR_ENABLED`: 是否启用采集器
- `COLLECTOR_HOST`: 采集器主机地址
- `COLLECTOR_PORT`: 采集器端口
- `COLLECTOR_PING_INTERVAL_SECONDS`: Ping间隔
- `COLLECTOR_RECONNECT_DELAY_SECONDS`: 重连延迟

#### AI模型配置
- `LLM_MODE`: 模式选择（heuristic/qwen/openai）
- `LLM_BASE_URL`: 模型服务地址
- `LLM_MODEL`: 模型名称
- `LLM_API_KEY`: API密钥
- `DASHSCOPE_API_KEY`: DashScope密钥
- `LLM_TEMPERATURE`: 采样温度
- `LLM_TIMEOUT_SECONDS`: 超时时间

#### 存储配置
- `REDIS_URL`: Redis连接URL
- `DATA_DIR`: 数据目录
- `DATABASE_PATH`: SQLite数据库路径
- `CHROMA_DIR`: Chroma存储目录
- `SESSION_TTL_SECONDS`: 会话TTL

### 实际使用示例

#### 启动流程
1. 启动抖音消息源
2. 配置环境变量
3. 安装依赖包
4. 启动后端服务
5. 启动前端界面

#### 建议生成示例
系统支持多种事件类型的智能建议生成，包括评论回复、礼物感谢、关注欢迎等场景。

#### 性能优化建议
1. 合理配置Redis集群提高缓存性能
2. 优化Chroma向量索引提升检索速度
3. 调整事件窗口大小平衡内存使用
4. 监控模型响应时间优化超时设置
5. 实施适当的日志轮转避免磁盘占用