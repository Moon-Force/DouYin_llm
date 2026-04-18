# 记忆抽取协议修复与离线评测设计

日期：2026-04-18

## 目标

围绕当前观众记忆抽取链路，先解决“模型实际没有产出可解析结果”的协议问题，再补一套真正可复用的离线标注评测集，用于持续验证记忆抽取模型质量。

本次设计要同时满足三件事：

- 修复当前 Ollama/OpenAI-compatible 返回与现有抽取协议不匹配的问题
- 为记忆抽取 prompt 增加通用但高覆盖的 few-shot 示例
- 建立离线评测入口，能稳定衡量 `should_extract`、`memory_type`、`polarity`、`temporal_scope` 等关键质量指标

## 背景

当前项目的观众记忆抽取链路分为三层：

1. [backend/services/memory_extractor_client.py](H:\DouYin_llm\backend\services\memory_extractor_client.py)
   - 负责向 OpenAI-compatible `/chat/completions` 发请求
2. [backend/services/llm_memory_extractor.py](H:\DouYin_llm\backend\services\llm_memory_extractor.py)
   - 负责 prompt、JSON 解析、字段校验和候选记忆规范化
3. [backend/services/memory_extractor.py](H:\DouYin_llm\backend\services\memory_extractor.py)
   - 负责 LLM 优先、规则兜底的组合逻辑

当前真实配置中：

- `MEMORY_EXTRACTOR_MODEL=qwen3.5:0.8b`
- `MEMORY_EXTRACTOR_BASE_URL=http://127.0.0.1:11434/v1`

实际调用暴露出两个问题：

1. `choices[0].message.content` 为空字符串，但 `reasoning` 字段里有大量思维过程
2. `finish_reason=length`，说明模型回答被截断

这会导致当前 [backend/services/llm_memory_extractor.py](H:\DouYin_llm\backend\services\llm_memory_extractor.py) 在 `json.loads()` 前就拿到空串，最终退回规则抽取。换句话说，当前链路还没有真正评估到 LLM 抽取效果。

## 非目标

本次不做以下事情：

- 不改动提词生成模型和语义 embedding 配置
- 不修改 `viewer_memories` 表结构
- 不引入复杂的 prompt 管理平台
- 不一次性扩展到礼物、点赞、系统事件的记忆抽取
- 不在本轮设计里决定最终长期使用哪一个 Ollama 模型

## 方案比较

### 方案一：先修协议，再加 few-shot，再做离线评测

优点：

- 先确认模型真的被测到，而不是继续 silent fallback
- few-shot 能直接改善小模型的边界判断
- 修复和评测分层清晰，结果可比较

缺点：

- 需要同时改客户端、prompt 和验证资产

### 方案二：先做离线评测，不修协议

优点：

- 可以更早搭起评测框架

缺点：

- 测到的主要会是规则兜底，不是当前 LLM 模型
- 会混淆“协议问题”和“模型能力问题”

### 方案三：直接换模型，再做评测

优点：

- 如果当前模型明显不适合，可能更快达成可用状态

缺点：

- 无法确认根因到底是协议、prompt 还是模型
- 容易把问题混在一起，后续不好回归验证

### 推荐方案

采用方案一：

- 先修协议观测与错误分类
- 再加入通用高覆盖 few-shot
- 最后建立正式离线评测集和评测命令

## 总体设计

本次设计拆成两个子系统：

1. 协议与运行时诊断层
2. 离线标注评测层

两者职责分离：

- 协议层回答“模型有没有正确返回结构化结果”
- 评测层回答“模型在正确接入后效果到底怎么样”

## 一、协议修复设计

### 1. 当前问题定义

当前客户端默认假设响应必然满足：

```json
{
  "choices": [
    {
      "message": {
        "content": "{...json...}"
      }
    }
  ]
}
```

但当前 Ollama 模型返回可能是：

- `content=""`
- `reasoning="大量推理文本"`
- `finish_reason="length"`

如果继续把空 `content` 当成正常返回，调用方只会看到 JSON 解析失败，无法区分：

- 模型没按协议输出
- 输出被截断
- 服务端字段映射异常

### 2. 目标行为

[backend/services/memory_extractor_client.py](H:\DouYin_llm\backend\services\memory_extractor_client.py) 需要把响应拆成明确的协议状态：

1. 正常返回：
   - `content` 是非空字符串
2. 空内容异常：
   - `content` 为空且 `reasoning` 也为空
3. reasoning-only 异常：
   - `content` 为空，但 `reasoning` 非空
4. 截断异常：
   - `finish_reason=length`
5. 非法响应异常：
   - `choices/message` 缺失或类型不合法

### 3. 处理原则

- 不把 `reasoning` 当成 `content` 自动复用
- 不在客户端里猜测如何从自然语言中截取 JSON
- 对 `reasoning-only` 和 `length` 给出清晰错误信息
- 仍然让上层 [backend/services/memory_extractor.py](H:\DouYin_llm\backend\services\memory_extractor.py) 执行规则兜底

这样做的原因是：

- 先让问题可观测
- 避免把推理链文本误当成最终结构化输出
- 后续更换模型或调 prompt 时更容易定位问题

### 4. 错误分类约定

客户端错误信息至少要能区分以下标签：

- `empty_content`
- `reasoning_only`
- `response_truncated`
- `invalid_response_shape`
- `invalid_json_body`

这里不要求先引入正式错误类层级，但错误消息必须稳定、可测试、可 grep。

### 5. 协议回归测试

需要补的测试包括：

- `content` 正常返回
- `content` 空且 `reasoning` 非空
- `finish_reason=length`
- `choices[0].message` 缺失
- 返回体不是合法 JSON

这些测试优先放在围绕客户端的单测里，避免每次都通过完整 app wiring 才能发现协议回归。

## 二、Few-shot 设计

### 1. 为什么要加 few-shot

当前 `qwen3.5:0.8b` 这类小模型仅靠 schema 说明，容易出现三类问题：

- 把短期计划误抽成长期记忆
- 把交易问句或低信号互动误抽成事实
- 对负向偏好理解不稳，或者输出格式漂移

few-shot 的目标不是“教模型所有直播业务知识”，而是用最少上下文把关键边界钉死。

### 2. few-shot 原则

本轮使用“通用但高覆盖”的 few-shot，不依赖具体直播间词汇。

约束如下：

- few-shot 数量控制在 `6` 个左右
- 每个样例都采用“输入评论 + 目标 JSON”
- 输出 JSON 必须严格与目标协议一致
- 样例语言口语化，但不要包含过多行业黑话
- few-shot 只做边界教学，代码仍做硬校验

### 3. few-shot 覆盖面

第一版应至少覆盖这 6 类：

1. 长期正向偏好
   - 例：喜欢喝无糖可乐
2. 长期负向偏好
   - 例：一点都不喜欢吃香菜
3. 长期稳定背景信息
   - 例：在杭州做前端开发
4. 短期计划，不抽
   - 例：今晚下班准备去吃火锅
5. 低信号寒暄，不抽
   - 例：来了、哈哈哈
6. 交易型问句，不抽
   - 例：这个多少钱、链接在哪

### 4. prompt 结构

[backend/services/llm_memory_extractor.py](H:\DouYin_llm\backend\services\llm_memory_extractor.py) 里的 prompt 结构应收敛为：

1. system prompt
   - 定义任务、字段、硬约束
2. few-shot examples
   - 若干组输入输出示例
3. real user payload
   - 当前事件 JSON

few-shot 不建议放进用户事件 JSON 内部，而应作为独立示例，让模型明确区分“教学样例”和“真实输入”。

### 5. few-shot 的成功标准

few-shot 加入后，至少要改善以下指标：

- JSON 可解析率不下降
- `short_term` 误抽率下降
- 低信号评论误抽率下降
- 负向偏好方向错误减少

如果 few-shot 让小模型更容易被截断，则优先减少样例数，而不是继续堆例子。

## 三、离线标注评测设计

### 1. 为什么现有资产还不够

当前仓库里已有：

- 嵌入/语义召回评测集
- LLM memory extractor 的协议单测

但还缺少一份真正评估“从评论到结构化记忆”的标注集。现有 `tests/test_llm_memory_extractor.py` 更偏协议与字段校验，不足以衡量模型在真实评论分布上的抽取质量。

### 2. 数据集目录

新建目录：

```text
tests/fixtures/memory_extraction/
```

建议至少包含：

```text
tests/fixtures/memory_extraction/default.json
tests/fixtures/memory_extraction/hard.json
```

其中：

- `default.json` 用于基础回归
- `hard.json` 用于否定、模糊表达、短期/长期边界和噪声混合场景

### 3. 单条标注 schema

建议每条样本使用如下结构：

```json
{
  "label": "negative_preference",
  "content": "我一点都不喜欢吃香菜",
  "expected": {
    "should_extract": true,
    "memory_text": "不喜欢香菜",
    "memory_type": "preference",
    "polarity": "negative",
    "temporal_scope": "long_term"
  }
}
```

字段说明：

- `label`
  - 稳定样本名，便于汇报失败样本
- `content`
  - 原始直播评论文本
- `expected.should_extract`
  - 是否应该抽取
- `expected.memory_text`
  - 若应抽取，目标记忆文本
- `expected.memory_type`
  - `preference | fact | context`
- `expected.polarity`
  - `positive | negative | neutral`
- `expected.temporal_scope`
  - `long_term | short_term`

如果 `should_extract=false`，则：

- `memory_text` 可为空字符串
- 其余字段仍建议保留期望值，方便错误分桶

### 4. 样本覆盖要求

第一版离线集至少覆盖：

- 长期偏好
- 长期背景
- 长期事实
- 负向偏好
- 短期计划
- 短期情绪
- 低信号互动
- 交易问句
- 含“最近/这两周/一直”等时间线索的边界案例
- 容易误判 polarity 的样例

建议样本规模：

- `default.json`：30-50 条
- `hard.json`：80-120 条

### 5. 评测命令

新增一个记忆抽取离线评测入口，建议仍挂在现有 verifier 体系下，而不是另起完全独立脚本。

推荐目标命令形态：

```bash
python -m tests.memory_pipeline_verifier.runner --mode internal --task memory-extraction --dataset tests/fixtures/memory_extraction/default.json
```

当前 [tests/memory_pipeline_verifier/runner.py](H:\DouYin_llm\tests\memory_pipeline_verifier\runner.py) 尚不支持 `memory-extraction` 任务，因此后续实现要扩展 task 分发。

### 6. 评测输出指标

第一版必须输出：

- `case_count`
- `json_parse_rate`
- `schema_valid_rate`
- `should_extract_precision`
- `should_extract_recall`
- `should_extract_f1`
- `memory_type_accuracy`
- `polarity_accuracy`
- `temporal_scope_accuracy`

额外建议输出：

- `false_positive_count`
- `false_negative_count`
- `short_term_false_positive_count`
- `negative_polarity_mismatch_count`

### 7. 错误样本输出

控制台和报告里至少要保留有限数量失败样本，包含：

- `label`
- `content`
- `expected`
- `actual`
- `error_type`

这样后续调 prompt 时能知道失败主要集中在哪一类，而不是只看抽象分数。

## 四、验收标准

本次设计完成后的验收标准分两层。

### 协议层验收

- 当前客户端能明确报告 `reasoning_only`、`response_truncated` 等协议异常
- 不再把“空 content”误当作正常返回
- 规则兜底仍然生效

### 评测层验收

- 仓库内存在正式的记忆抽取标注集
- 能通过统一命令运行离线评测
- 输出核心质量指标和失败样本
- 可以稳定复现实验结果，用于对比不同模型或不同 few-shot 版本

## 五、风险与缓解

### 风险一：0.8b 小模型加 few-shot 后更容易被截断

缓解：

- few-shot 控制在 6 个左右
- 保持示例短小
- 优先删除冗余解释，而不是删掉边界案例

### 风险二：标注集一开始过小，指标不稳定

缓解：

- 先做小而全的覆盖集
- 后续按错误类型逐步扩样，而不是一次性追求大规模

### 风险三：few-shot 优化了当前模型，但掩盖了协议层问题

缓解：

- 先完成协议可观测化
- 再加 few-shot
- 评测时单独记录协议失败率和质量指标

## 六、文件变化范围

后续实现预期会涉及：

- 修改：[backend/services/memory_extractor_client.py](H:\DouYin_llm\backend\services\memory_extractor_client.py)
- 修改：[backend/services/llm_memory_extractor.py](H:\DouYin_llm\backend\services\llm_memory_extractor.py)
- 修改：[tests/memory_pipeline_verifier/runner.py](H:\DouYin_llm\tests\memory_pipeline_verifier\runner.py)
- 新增：`tests/fixtures/memory_extraction/default.json`
- 新增：`tests/fixtures/memory_extraction/hard.json`
- 新增：围绕协议与离线评测的测试文件

## 七、推荐执行顺序

推荐按以下顺序落地：

1. 先修客户端协议异常分类
2. 补协议回归测试
3. 再给 LLM prompt 加通用高覆盖 few-shot
4. 准备记忆抽取标注集
5. 扩展 verifier 支持 `memory-extraction` 任务
6. 跑离线评测并记录基线结果

这样可以保证每一步都能单独验证，不把问题叠在一起。
