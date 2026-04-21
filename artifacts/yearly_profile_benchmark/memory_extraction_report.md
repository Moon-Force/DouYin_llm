# Memory Extraction Report

## Summary

- Dataset: `artifacts/yearly_profile_benchmark/extraction_cases.json`
- Reasoning Effort: none
- Prompt Variant: cot
- Cases: 288
- JSON Parse Rate: 1.0000
- Schema Valid Rate: 1.0000
- Should Extract Precision: 0.7194
- Should Extract Recall: 0.8393
- Should Extract F1: 0.7747
- Memory Type Accuracy: 0.7202
- Polarity Accuracy: 0.7381
- Temporal Scope Accuracy: 0.8393
- False Positives: 55
- False Negatives: 27
- Short-Term False Positives: 55
- Negative Polarity Mismatches: 5

## viewer-yearly-001-extract-01

- Error Type: mismatch

**Content**

> 我在杭州做前端开发，最近项目一直在赶需求

**Expected**

```json
{
  "should_extract": true,
  "memory_text": "在杭州做前端开发",
  "memory_type": "context",
  "polarity": "neutral",
  "temporal_scope": "long_term"
}
```

**Actual**

```json
{
  "memory_text": "在杭州做前端开发，项目赶需求",
  "memory_text_raw": "我在杭州做前端开发，最近项目一直在赶需求",
  "memory_text_canonical": "在杭州做前端开发，项目赶需求",
  "memory_type": "fact",
  "polarity": "neutral",
  "temporal_scope": "long_term",
  "confidence": 0.74,
  "extraction_source": "llm"
}
```

## viewer-yearly-001-extract-02

- Error Type: mismatch

**Content**

> 我平时都要喝美式咖啡，不然下午根本顶不住

**Expected**

```json
{
  "should_extract": true,
  "memory_text": "平时都喝美式咖啡",
  "memory_type": "preference",
  "polarity": "positive",
  "temporal_scope": "long_term"
}
```

**Actual**

```json
{
  "memory_text": "平时喝美式咖啡",
  "memory_text_raw": "我平时都要喝美式咖啡，不然下午根本顶不住",
  "memory_text_canonical": "平时喝美式咖啡",
  "memory_type": "preference",
  "polarity": "positive",
  "temporal_scope": "long_term",
  "confidence": 0.86,
  "extraction_source": "llm"
}
```

## viewer-yearly-001-extract-03

- Error Type: mismatch

**Content**

> 我不太能吃辣，吃多了胃会不舒服

**Expected**

```json
{
  "should_extract": true,
  "memory_text": "不太能吃辣",
  "memory_type": "preference",
  "polarity": "negative",
  "temporal_scope": "long_term"
}
```

**Actual**

```json
{}
```

## viewer-yearly-001-extract-05

- Error Type: mismatch

**Content**

> 我家里养了两只猫，晚上回去还得铲屎

**Expected**

```json
{
  "should_extract": true,
  "memory_text": "家里养了两只猫",
  "memory_type": "fact",
  "polarity": "neutral",
  "temporal_scope": "long_term"
}
```

**Actual**

```json
{
  "memory_text": "养猫",
  "memory_text_raw": "我家里养了两只猫，晚上回去还得铲屎",
  "memory_text_canonical": "养猫",
  "memory_type": "fact",
  "polarity": "positive",
  "temporal_scope": "long_term",
  "confidence": 0.74,
  "extraction_source": "llm"
}
```

## viewer-yearly-001-extract-06

- Error Type: mismatch

**Content**

> 我一直都喜欢吃豚骨拉面，周末经常去那家店

**Expected**

```json
{
  "should_extract": true,
  "memory_text": "一直都喜欢吃豚骨拉面",
  "memory_type": "preference",
  "polarity": "positive",
  "temporal_scope": "long_term"
}
```

**Actual**

```json
{
  "memory_text": "喜欢吃豚骨拉面",
  "memory_text_raw": "我一直都喜欢吃豚骨拉面，周末经常去那家店",
  "memory_text_canonical": "喜欢吃豚骨拉面",
  "memory_type": "preference",
  "polarity": "positive",
  "temporal_scope": "long_term",
  "confidence": 0.86,
  "extraction_source": "llm"
}
```

## viewer-yearly-001-extract-07

- Error Type: mismatch

**Content**

> 我平时都是凌晨一点以后才睡，作息有点乱

**Expected**

```json
{
  "should_extract": true,
  "memory_text": "平时凌晨一点以后才睡",
  "memory_type": "fact",
  "polarity": "neutral",
  "temporal_scope": "long_term"
}
```

**Actual**

```json
{}
```

## viewer-yearly-001-extract-08

- Error Type: mismatch

**Content**

> 这周我准备连续夜跑，把作息拉回来

**Expected**

```json
{
  "should_extract": false,
  "memory_text": "",
  "memory_type": "context",
  "polarity": "neutral",
  "temporal_scope": "short_term"
}
```

**Actual**

```json
{
  "memory_text": "连续夜跑",
  "memory_text_raw": "这周我准备连续夜跑，把作息拉回来",
  "memory_text_canonical": "连续夜跑",
  "memory_type": "fact",
  "polarity": "positive",
  "temporal_scope": "long_term",
  "confidence": 0.74,
  "extraction_source": "llm"
}
```

## viewer-yearly-001-extract-10

- Error Type: mismatch

**Content**

> 今晚下班还想去吃面，最近就馋这口

**Expected**

```json
{
  "should_extract": false,
  "memory_text": "",
  "memory_type": "context",
  "polarity": "neutral",
  "temporal_scope": "short_term"
}
```

**Actual**

```json
{
  "memory_text": "下班想吃面",
  "memory_text_raw": "今晚下班还想去吃面，最近就馋这口",
  "memory_text_canonical": "下班想吃面",
  "memory_type": "preference",
  "polarity": "positive",
  "temporal_scope": "long_term",
  "confidence": 0.86,
  "extraction_source": "llm"
}
```

## viewer-yearly-002-extract-01

- Error Type: mismatch

**Content**

> 我最近在备考雅思，晚上下班后会背单词做听力

**Expected**

```json
{
  "should_extract": true,
  "memory_text": "最近在备考雅思",
  "memory_type": "fact",
  "polarity": "neutral",
  "temporal_scope": "long_term"
}
```

**Actual**

```json
{
  "memory_text": "备考雅思，晚上下班后背单词",
  "memory_text_raw": "我最近在备考雅思，晚上下班后会背单词做听力",
  "memory_text_canonical": "备考雅思，晚上下班后背单词",
  "memory_type": "fact",
  "polarity": "positive",
  "temporal_scope": "long_term",
  "confidence": 0.74,
  "extraction_source": "llm"
}
```

## viewer-yearly-002-extract-02

- Error Type: mismatch

**Content**

> 我平时都住在苏州，公司在园区那边

**Expected**

```json
{
  "should_extract": true,
  "memory_text": "平时住在苏州",
  "memory_type": "context",
  "polarity": "neutral",
  "temporal_scope": "long_term"
}
```

**Actual**

```json
{
  "memory_text": "住在苏州，公司位置",
  "memory_text_raw": "我平时都住在苏州，公司在园区那边",
  "memory_text_canonical": "住在苏州，公司位置",
  "memory_type": "context",
  "polarity": "neutral",
  "temporal_scope": "long_term",
  "confidence": 0.78,
  "extraction_source": "llm"
}
```

## viewer-yearly-002-extract-04

- Error Type: mismatch

**Content**

> 我一直都喜欢喝无糖可乐，复习的时候会来一瓶

**Expected**

```json
{
  "should_extract": true,
  "memory_text": "一直都喜欢喝无糖可乐",
  "memory_type": "preference",
  "polarity": "positive",
  "temporal_scope": "long_term"
}
```

**Actual**

```json
{
  "memory_text": "喜欢喝无糖可乐",
  "memory_text_raw": "我一直都喜欢喝无糖可乐，复习的时候会来一瓶",
  "memory_text_canonical": "喜欢喝无糖可乐",
  "memory_type": "preference",
  "polarity": "positive",
  "temporal_scope": "long_term",
  "confidence": 0.86,
  "extraction_source": "llm"
}
```

## viewer-yearly-002-extract-05

- Error Type: mismatch

**Content**

> 我家里还有个弟弟，今年刚上高三

**Expected**

```json
{
  "should_extract": true,
  "memory_text": "家里有个弟弟",
  "memory_type": "fact",
  "polarity": "neutral",
  "temporal_scope": "long_term"
}
```

**Actual**

```json
{
  "memory_text": "家里有个弟弟，刚上高三",
  "memory_text_raw": "我家里还有个弟弟，今年刚上高三",
  "memory_text_canonical": "家里有个弟弟，刚上高三",
  "memory_type": "fact",
  "polarity": "neutral",
  "temporal_scope": "long_term",
  "confidence": 0.74,
  "extraction_source": "llm"
}
```

## viewer-yearly-002-extract-06

- Error Type: mismatch

**Content**

> 我平时都骑电动车通勤，单程差不多四十分钟

**Expected**

```json
{
  "should_extract": true,
  "memory_text": "平时骑电动车通勤",
  "memory_type": "fact",
  "polarity": "neutral",
  "temporal_scope": "long_term"
}
```

**Actual**

```json
{
  "memory_text": "骑电动车通勤",
  "memory_text_raw": "我平时都骑电动车通勤，单程差不多四十分钟",
  "memory_text_canonical": "骑电动车通勤",
  "memory_type": "fact",
  "polarity": "neutral",
  "temporal_scope": "long_term",
  "confidence": 0.74,
  "extraction_source": "llm"
}
```

## viewer-yearly-002-extract-07

- Error Type: mismatch

**Content**

> 我一直都想去英国读传媒，申请学校还在准备

**Expected**

```json
{
  "should_extract": true,
  "memory_text": "一直都想去英国读传媒",
  "memory_type": "fact",
  "polarity": "neutral",
  "temporal_scope": "long_term"
}
```

**Actual**

```json
{
  "memory_text": "想去英国读传媒",
  "memory_text_raw": "我一直都想去英国读传媒，申请学校还在准备",
  "memory_text_canonical": "想去英国读传媒",
  "memory_type": "preference",
  "polarity": "positive",
  "temporal_scope": "long_term",
  "confidence": 0.86,
  "extraction_source": "llm"
}
```

## viewer-yearly-002-extract-08

- Error Type: mismatch

**Content**

> 这周我要连着上三天口语课，时间有点满

**Expected**

```json
{
  "should_extract": false,
  "memory_text": "",
  "memory_type": "context",
  "polarity": "neutral",
  "temporal_scope": "short_term"
}
```

**Actual**

```json
{
  "memory_text": "连着上三天口语课",
  "memory_text_raw": "这周我要连着上三天口语课，时间有点满",
  "memory_text_canonical": "连着上三天口语课",
  "memory_type": "fact",
  "polarity": "positive",
  "temporal_scope": "long_term",
  "confidence": 0.74,
  "extraction_source": "llm"
}
```

## viewer-yearly-002-extract-10

- Error Type: mismatch

**Content**

> 明天又要去上口语课，希望这次能顺一点

**Expected**

```json
{
  "should_extract": false,
  "memory_text": "",
  "memory_type": "context",
  "polarity": "neutral",
  "temporal_scope": "short_term"
}
```

**Actual**

```json
{
  "memory_text": "明天口语课",
  "memory_text_raw": "明天又要去上口语课，希望这次能顺一点",
  "memory_text_canonical": "明天口语课",
  "memory_type": "fact",
  "polarity": "positive",
  "temporal_scope": "long_term",
  "confidence": 0.74,
  "extraction_source": "llm"
}
```

## viewer-yearly-003-extract-01

- Error Type: mismatch

**Content**

> 我一直都在减脂，晚饭尽量不吃米饭和面

**Expected**

```json
{
  "should_extract": true,
  "memory_text": "一直都在减脂",
  "memory_type": "fact",
  "polarity": "neutral",
  "temporal_scope": "long_term"
}
```

**Actual**

```json
{
  "memory_text": "减脂，不吃米饭和面",
  "memory_text_raw": "我一直都在减脂，晚饭尽量不吃米饭和面",
  "memory_text_canonical": "减脂，不吃米饭和面",
  "memory_type": "preference",
  "polarity": "negative",
  "temporal_scope": "long_term",
  "confidence": 0.86,
  "extraction_source": "llm"
}
```

## viewer-yearly-003-extract-02

- Error Type: mismatch

**Content**

> 我平时都去公司附近那家健身房，器械还挺全

**Expected**

```json
{
  "should_extract": true,
  "memory_text": "平时去公司附近那家健身房",
  "memory_type": "context",
  "polarity": "neutral",
  "temporal_scope": "long_term"
}
```

**Actual**

```json
{
  "memory_text": "公司附近健身房",
  "memory_text_raw": "我平时都去公司附近那家健身房，器械还挺全",
  "memory_text_canonical": "公司附近健身房",
  "memory_type": "context",
  "polarity": "neutral",
  "temporal_scope": "long_term",
  "confidence": 0.78,
  "extraction_source": "llm"
}
```

## viewer-yearly-003-extract-03

- Error Type: mismatch

**Content**

> 我不能喝纯牛奶，乳糖不耐一喝就肚子疼

**Expected**

```json
{
  "should_extract": true,
  "memory_text": "不能喝纯牛奶",
  "memory_type": "preference",
  "polarity": "negative",
  "temporal_scope": "long_term"
}
```

**Actual**

```json
{
  "memory_text": "乳糖不耐受",
  "memory_text_raw": "我不能喝纯牛奶，乳糖不耐一喝就肚子疼",
  "memory_text_canonical": "乳糖不耐受",
  "memory_type": "fact",
  "polarity": "negative",
  "temporal_scope": "long_term",
  "confidence": 0.74,
  "extraction_source": "llm"
}
```

## viewer-yearly-003-extract-04

- Error Type: mismatch

**Content**

> 我一直都喜欢吃鸡胸和玉米，做饭也方便

**Expected**

```json
{
  "should_extract": true,
  "memory_text": "一直都喜欢吃鸡胸和玉米",
  "memory_type": "preference",
  "polarity": "positive",
  "temporal_scope": "long_term"
}
```

**Actual**

```json
{
  "memory_text": "喜欢吃鸡胸和玉米，做饭方便",
  "memory_text_raw": "我一直都喜欢吃鸡胸和玉米，做饭也方便",
  "memory_text_canonical": "喜欢吃鸡胸和玉米，做饭方便",
  "memory_type": "preference",
  "polarity": "positive",
  "temporal_scope": "long_term",
  "confidence": 0.86,
  "extraction_source": "llm"
}
```

## viewer-yearly-003-extract-06

- Error Type: mismatch

**Content**

> 我平时都习惯早上空腹称体重，看看有没有掉

**Expected**

```json
{
  "should_extract": true,
  "memory_text": "平时早上空腹称体重",
  "memory_type": "fact",
  "polarity": "neutral",
  "temporal_scope": "long_term"
}
```

**Actual**

```json
{
  "memory_text": "习惯空腹称体重",
  "memory_text_raw": "我平时都习惯早上空腹称体重，看看有没有掉",
  "memory_text_canonical": "习惯空腹称体重",
  "memory_type": "fact",
  "polarity": "neutral",
  "temporal_scope": "long_term",
  "confidence": 0.74,
  "extraction_source": "llm"
}
```

## viewer-yearly-003-extract-08

- Error Type: mismatch

**Content**

> 这周我准备冲一下半马配速，训练量会大一点

**Expected**

```json
{
  "should_extract": false,
  "memory_text": "",
  "memory_type": "context",
  "polarity": "neutral",
  "temporal_scope": "short_term"
}
```

**Actual**

```json
{
  "memory_text": "准备冲半马配速",
  "memory_text_raw": "这周我准备冲一下半马配速，训练量会大一点",
  "memory_text_canonical": "准备冲半马配速",
  "memory_type": "fact",
  "polarity": "positive",
  "temporal_scope": "long_term",
  "confidence": 0.74,
  "extraction_source": "llm"
}
```

## viewer-yearly-003-extract-09

- Error Type: mismatch

**Content**

> 我今天腿练完直接酸到楼梯都不想走

**Expected**

```json
{
  "should_extract": false,
  "memory_text": "",
  "memory_type": "context",
  "polarity": "neutral",
  "temporal_scope": "short_term"
}
```

**Actual**

```json
{
  "memory_text": "腿练后酸软",
  "memory_text_raw": "我今天腿练完直接酸到楼梯都不想走",
  "memory_text_canonical": "腿练后酸软",
  "memory_type": "fact",
  "polarity": "negative",
  "temporal_scope": "long_term",
  "confidence": 0.74,
  "extraction_source": "llm"
}
```

## viewer-yearly-003-extract-10

- Error Type: mismatch

**Content**

> 今晚练完准备去吃个轻食碗，别再放纵了

**Expected**

```json
{
  "should_extract": false,
  "memory_text": "",
  "memory_type": "context",
  "polarity": "neutral",
  "temporal_scope": "short_term"
}
```

**Actual**

```json
{
  "memory_text": "练完准备吃轻食碗",
  "memory_text_raw": "今晚练完准备去吃个轻食碗，别再放纵了",
  "memory_text_canonical": "练完准备吃轻食碗",
  "memory_type": "preference",
  "polarity": "positive",
  "temporal_scope": "long_term",
  "confidence": 0.86,
  "extraction_source": "llm"
}
```

## viewer-yearly-003-extract-12

- Error Type: mismatch

**Content**

> 明天想试试新的跑步计划

**Expected**

```json
{
  "should_extract": false,
  "memory_text": "",
  "memory_type": "context",
  "polarity": "neutral",
  "temporal_scope": "short_term"
}
```

**Actual**

```json
{
  "memory_text": "想尝试新的跑步计划",
  "memory_text_raw": "明天想试试新的跑步计划",
  "memory_text_canonical": "想尝试新的跑步计划",
  "memory_type": "preference",
  "polarity": "positive",
  "temporal_scope": "long_term",
  "confidence": 0.86,
  "extraction_source": "llm"
}
```

## viewer-yearly-004-extract-01

- Error Type: mismatch

**Content**

> 我做亚马逊跨境电商，最近一直在看广告数据

**Expected**

```json
{
  "should_extract": true,
  "memory_text": "做亚马逊跨境电商",
  "memory_type": "fact",
  "polarity": "neutral",
  "temporal_scope": "long_term"
}
```

**Actual**

```json
{}
```

## viewer-yearly-004-extract-02

- Error Type: mismatch

**Content**

> 我平时住在深圳，仓库也在这边

**Expected**

```json
{
  "should_extract": true,
  "memory_text": "平时住在深圳",
  "memory_type": "context",
  "polarity": "neutral",
  "temporal_scope": "long_term"
}
```

**Actual**

```json
{
  "memory_text": "住在深圳",
  "memory_text_raw": "我平时住在深圳，仓库也在这边",
  "memory_text_canonical": "住在深圳",
  "memory_type": "context",
  "polarity": "neutral",
  "temporal_scope": "long_term",
  "confidence": 0.78,
  "extraction_source": "llm"
}
```

## viewer-yearly-004-extract-03

- Error Type: mismatch

**Content**

> 我不喜欢一大早开会，脑子根本没开机

**Expected**

```json
{
  "should_extract": true,
  "memory_text": "不喜欢开早会",
  "memory_type": "preference",
  "polarity": "negative",
  "temporal_scope": "long_term"
}
```

**Actual**

```json
{
  "memory_text": "不喜欢开会",
  "memory_text_raw": "我不喜欢一大早开会，脑子根本没开机",
  "memory_text_canonical": "不喜欢开会",
  "memory_type": "preference",
  "polarity": "negative",
  "temporal_scope": "long_term",
  "confidence": 0.86,
  "extraction_source": "llm"
}
```

## viewer-yearly-004-extract-04

- Error Type: mismatch

**Content**

> 我一直都喜欢喝冰美式，特别是盯报表的时候

**Expected**

```json
{
  "should_extract": true,
  "memory_text": "一直都喜欢喝冰美式",
  "memory_type": "preference",
  "polarity": "positive",
  "temporal_scope": "long_term"
}
```

**Actual**

```json
{
  "memory_text": "喜欢冰美式",
  "memory_text_raw": "我一直都喜欢喝冰美式，特别是盯报表的时候",
  "memory_text_canonical": "喜欢冰美式",
  "memory_type": "preference",
  "polarity": "positive",
  "temporal_scope": "long_term",
  "confidence": 0.86,
  "extraction_source": "llm"
}
```

## viewer-yearly-004-extract-05

- Error Type: mismatch

**Content**

> 我经常熬夜看美国站数据，时差真难受

**Expected**

```json
{
  "should_extract": true,
  "memory_text": "经常熬夜看美国站数据",
  "memory_type": "fact",
  "polarity": "neutral",
  "temporal_scope": "long_term"
}
```

**Actual**

```json
{}
```

## viewer-yearly-004-extract-10

- Error Type: mismatch

**Content**

> 明天还得去仓库盘点库存

**Expected**

```json
{
  "should_extract": false,
  "memory_text": "",
  "memory_type": "context",
  "polarity": "neutral",
  "temporal_scope": "short_term"
}
```

**Actual**

```json
{
  "memory_text": "去仓库盘点库存",
  "memory_text_raw": "明天还得去仓库盘点库存",
  "memory_text_canonical": "去仓库盘点库存",
  "memory_type": "fact",
  "polarity": "neutral",
  "temporal_scope": "long_term",
  "confidence": 0.74,
  "extraction_source": "llm"
}
```

## viewer-yearly-004-extract-12

- Error Type: mismatch

**Content**

> 今晚准备把 listing 再优化一下

**Expected**

```json
{
  "should_extract": false,
  "memory_text": "",
  "memory_type": "context",
  "polarity": "neutral",
  "temporal_scope": "short_term"
}
```

**Actual**

```json
{
  "memory_text": "今晚优化 listing",
  "memory_text_raw": "今晚准备把 listing 再优化一下",
  "memory_text_canonical": "今晚优化 listing",
  "memory_type": "preference",
  "polarity": "positive",
  "temporal_scope": "long_term",
  "confidence": 0.86,
  "extraction_source": "llm"
}
```

## viewer-yearly-005-extract-01

- Error Type: mismatch

**Content**

> 我刚当妈妈没多久，现在还在摸索节奏

**Expected**

```json
{
  "should_extract": true,
  "memory_text": "刚当妈妈",
  "memory_type": "fact",
  "polarity": "neutral",
  "temporal_scope": "long_term"
}
```

**Actual**

```json
{
  "memory_text": "刚当妈妈不久，还在摸索节奏",
  "memory_text_raw": "我刚当妈妈没多久，现在还在摸索节奏",
  "memory_text_canonical": "刚当妈妈不久，还在摸索节奏",
  "memory_type": "fact",
  "polarity": "neutral",
  "temporal_scope": "long_term",
  "confidence": 0.74,
  "extraction_source": "llm"
}
```

## viewer-yearly-005-extract-02

- Error Type: mismatch

**Content**

> 我平时住在南京，爸妈偶尔会来帮忙

**Expected**

```json
{
  "should_extract": true,
  "memory_text": "平时住在南京",
  "memory_type": "context",
  "polarity": "neutral",
  "temporal_scope": "long_term"
}
```

**Actual**

```json
{
  "memory_text": "住在南京，父母偶尔帮忙",
  "memory_text_raw": "我平时住在南京，爸妈偶尔会来帮忙",
  "memory_text_canonical": "住在南京，父母偶尔帮忙",
  "memory_type": "context",
  "polarity": "neutral",
  "temporal_scope": "long_term",
  "confidence": 0.78,
  "extraction_source": "llm"
}
```

## viewer-yearly-005-extract-03

- Error Type: mismatch

**Content**

> 我不喜欢香精味太重的护肤品，闻着头晕

**Expected**

```json
{
  "should_extract": true,
  "memory_text": "不喜欢香精味太重的护肤品",
  "memory_type": "preference",
  "polarity": "negative",
  "temporal_scope": "long_term"
}
```

**Actual**

```json
{
  "memory_text": "不喜欢香精味重的护肤品",
  "memory_text_raw": "我不喜欢香精味太重的护肤品，闻着头晕",
  "memory_text_canonical": "不喜欢香精味重的护肤品",
  "memory_type": "preference",
  "polarity": "negative",
  "temporal_scope": "long_term",
  "confidence": 0.86,
  "extraction_source": "llm"
}
```

## viewer-yearly-005-extract-04

- Error Type: mismatch

**Content**

> 我一直都喜欢喝温豆浆，早上比较舒服

**Expected**

```json
{
  "should_extract": true,
  "memory_text": "一直都喜欢喝温豆浆",
  "memory_type": "preference",
  "polarity": "positive",
  "temporal_scope": "long_term"
}
```

**Actual**

```json
{
  "memory_text": "喜欢喝温豆浆",
  "memory_text_raw": "我一直都喜欢喝温豆浆，早上比较舒服",
  "memory_text_canonical": "喜欢喝温豆浆",
  "memory_type": "preference",
  "polarity": "positive",
  "temporal_scope": "long_term",
  "confidence": 0.86,
  "extraction_source": "llm"
}
```

## viewer-yearly-005-extract-05

- Error Type: mismatch

**Content**

> 我晚上经常要起夜喂奶，睡眠一直断断续续

**Expected**

```json
{
  "should_extract": true,
  "memory_text": "晚上经常要起夜喂奶",
  "memory_type": "fact",
  "polarity": "neutral",
  "temporal_scope": "long_term"
}
```

**Actual**

```json
{}
```

## viewer-yearly-005-extract-07

- Error Type: mismatch

**Content**

> 我平时喜欢囤湿巾和纸尿裤，怕突然不够用

**Expected**

```json
{
  "should_extract": true,
  "memory_text": "平时喜欢囤湿巾和纸尿裤",
  "memory_type": "preference",
  "polarity": "positive",
  "temporal_scope": "long_term"
}
```

**Actual**

```json
{
  "memory_text": "喜欢囤湿巾和纸尿裤",
  "memory_text_raw": "我平时喜欢囤湿巾和纸尿裤，怕突然不够用",
  "memory_text_canonical": "喜欢囤湿巾和纸尿裤",
  "memory_type": "preference",
  "polarity": "positive",
  "temporal_scope": "long_term",
  "confidence": 0.86,
  "extraction_source": "llm"
}
```

## viewer-yearly-005-extract-09

- Error Type: mismatch

**Content**

> 今天终于睡了个整觉，太不容易了

**Expected**

```json
{
  "should_extract": false,
  "memory_text": "",
  "memory_type": "context",
  "polarity": "neutral",
  "temporal_scope": "short_term"
}
```

**Actual**

```json
{
  "memory_text": "整觉",
  "memory_text_raw": "今天终于睡了个整觉，太不容易了",
  "memory_text_canonical": "整觉",
  "memory_type": "fact",
  "polarity": "positive",
  "temporal_scope": "long_term",
  "confidence": 0.74,
  "extraction_source": "llm"
}
```

## viewer-yearly-005-extract-10

- Error Type: mismatch

**Content**

> 明天要带宝宝去打疫苗

**Expected**

```json
{
  "should_extract": false,
  "memory_text": "",
  "memory_type": "context",
  "polarity": "neutral",
  "temporal_scope": "short_term"
}
```

**Actual**

```json
{
  "memory_text": "带宝宝去打疫苗",
  "memory_text_raw": "明天要带宝宝去打疫苗",
  "memory_text_canonical": "带宝宝去打疫苗",
  "memory_type": "fact",
  "polarity": "positive",
  "temporal_scope": "long_term",
  "confidence": 0.74,
  "extraction_source": "llm"
}
```

## viewer-yearly-006-extract-01

- Error Type: mismatch

**Content**

> 我在杭州做前端开发，最近项目一直在赶需求

**Expected**

```json
{
  "should_extract": true,
  "memory_text": "在杭州做前端开发",
  "memory_type": "context",
  "polarity": "neutral",
  "temporal_scope": "long_term"
}
```

**Actual**

```json
{
  "memory_text": "在杭州做前端开发，项目赶需求",
  "memory_text_raw": "我在杭州做前端开发，最近项目一直在赶需求",
  "memory_text_canonical": "在杭州做前端开发，项目赶需求",
  "memory_type": "fact",
  "polarity": "neutral",
  "temporal_scope": "long_term",
  "confidence": 0.74,
  "extraction_source": "llm"
}
```

## viewer-yearly-006-extract-02

- Error Type: mismatch

**Content**

> 我平时都要喝美式咖啡，不然下午根本顶不住

**Expected**

```json
{
  "should_extract": true,
  "memory_text": "平时都喝美式咖啡",
  "memory_type": "preference",
  "polarity": "positive",
  "temporal_scope": "long_term"
}
```

**Actual**

```json
{
  "memory_text": "平时喝美式咖啡",
  "memory_text_raw": "我平时都要喝美式咖啡，不然下午根本顶不住",
  "memory_text_canonical": "平时喝美式咖啡",
  "memory_type": "preference",
  "polarity": "positive",
  "temporal_scope": "long_term",
  "confidence": 0.86,
  "extraction_source": "llm"
}
```

## viewer-yearly-006-extract-03

- Error Type: mismatch

**Content**

> 我不太能吃辣，吃多了胃会不舒服

**Expected**

```json
{
  "should_extract": true,
  "memory_text": "不太能吃辣",
  "memory_type": "preference",
  "polarity": "negative",
  "temporal_scope": "long_term"
}
```

**Actual**

```json
{}
```

## viewer-yearly-006-extract-05

- Error Type: mismatch

**Content**

> 我家里养了两只猫，晚上回去还得铲屎

**Expected**

```json
{
  "should_extract": true,
  "memory_text": "家里养了两只猫",
  "memory_type": "fact",
  "polarity": "neutral",
  "temporal_scope": "long_term"
}
```

**Actual**

```json
{
  "memory_text": "养猫",
  "memory_text_raw": "我家里养了两只猫，晚上回去还得铲屎",
  "memory_text_canonical": "养猫",
  "memory_type": "fact",
  "polarity": "neutral",
  "temporal_scope": "long_term",
  "confidence": 0.74,
  "extraction_source": "llm"
}
```

## viewer-yearly-006-extract-06

- Error Type: mismatch

**Content**

> 我一直都喜欢吃豚骨拉面，周末经常去那家店

**Expected**

```json
{
  "should_extract": true,
  "memory_text": "一直都喜欢吃豚骨拉面",
  "memory_type": "preference",
  "polarity": "positive",
  "temporal_scope": "long_term"
}
```

**Actual**

```json
{
  "memory_text": "喜欢吃豚骨拉面",
  "memory_text_raw": "我一直都喜欢吃豚骨拉面，周末经常去那家店",
  "memory_text_canonical": "喜欢吃豚骨拉面",
  "memory_type": "preference",
  "polarity": "positive",
  "temporal_scope": "long_term",
  "confidence": 0.86,
  "extraction_source": "llm"
}
```

## viewer-yearly-006-extract-07

- Error Type: mismatch

**Content**

> 我平时都是凌晨一点以后才睡，作息有点乱

**Expected**

```json
{
  "should_extract": true,
  "memory_text": "平时凌晨一点以后才睡",
  "memory_type": "fact",
  "polarity": "neutral",
  "temporal_scope": "long_term"
}
```

**Actual**

```json
{}
```

## viewer-yearly-006-extract-08

- Error Type: mismatch

**Content**

> 这周我准备连续夜跑，把作息拉回来

**Expected**

```json
{
  "should_extract": false,
  "memory_text": "",
  "memory_type": "context",
  "polarity": "neutral",
  "temporal_scope": "short_term"
}
```

**Actual**

```json
{
  "memory_text": "连续夜跑",
  "memory_text_raw": "这周我准备连续夜跑，把作息拉回来",
  "memory_text_canonical": "连续夜跑",
  "memory_type": "fact",
  "polarity": "positive",
  "temporal_scope": "long_term",
  "confidence": 0.74,
  "extraction_source": "llm"
}
```

## viewer-yearly-006-extract-10

- Error Type: mismatch

**Content**

> 今晚下班还想去吃面，最近就馋这口

**Expected**

```json
{
  "should_extract": false,
  "memory_text": "",
  "memory_type": "context",
  "polarity": "neutral",
  "temporal_scope": "short_term"
}
```

**Actual**

```json
{
  "memory_text": "下班想吃面",
  "memory_text_raw": "今晚下班还想去吃面，最近就馋这口",
  "memory_text_canonical": "下班想吃面",
  "memory_type": "preference",
  "polarity": "positive",
  "temporal_scope": "long_term",
  "confidence": 0.86,
  "extraction_source": "llm"
}
```

## viewer-yearly-007-extract-01

- Error Type: mismatch

**Content**

> 我最近在备考雅思，晚上下班后会背单词做听力

**Expected**

```json
{
  "should_extract": true,
  "memory_text": "最近在备考雅思",
  "memory_type": "fact",
  "polarity": "neutral",
  "temporal_scope": "long_term"
}
```

**Actual**

```json
{
  "memory_text": "备考雅思，晚上下班后背单词",
  "memory_text_raw": "我最近在备考雅思，晚上下班后会背单词做听力",
  "memory_text_canonical": "备考雅思，晚上下班后背单词",
  "memory_type": "fact",
  "polarity": "positive",
  "temporal_scope": "long_term",
  "confidence": 0.74,
  "extraction_source": "llm"
}
```

## viewer-yearly-007-extract-02

- Error Type: mismatch

**Content**

> 我平时都住在苏州，公司在园区那边

**Expected**

```json
{
  "should_extract": true,
  "memory_text": "平时住在苏州",
  "memory_type": "context",
  "polarity": "neutral",
  "temporal_scope": "long_term"
}
```

**Actual**

```json
{
  "memory_text": "住在苏州，公司位于园区",
  "memory_text_raw": "我平时都住在苏州，公司在园区那边",
  "memory_text_canonical": "住在苏州，公司位于园区",
  "memory_type": "context",
  "polarity": "neutral",
  "temporal_scope": "long_term",
  "confidence": 0.78,
  "extraction_source": "llm"
}
```

## viewer-yearly-007-extract-04

- Error Type: mismatch

**Content**

> 我一直都喜欢喝无糖可乐，复习的时候会来一瓶

**Expected**

```json
{
  "should_extract": true,
  "memory_text": "一直都喜欢喝无糖可乐",
  "memory_type": "preference",
  "polarity": "positive",
  "temporal_scope": "long_term"
}
```

**Actual**

```json
{
  "memory_text": "喜欢喝无糖可乐",
  "memory_text_raw": "我一直都喜欢喝无糖可乐，复习的时候会来一瓶",
  "memory_text_canonical": "喜欢喝无糖可乐",
  "memory_type": "preference",
  "polarity": "positive",
  "temporal_scope": "long_term",
  "confidence": 0.86,
  "extraction_source": "llm"
}
```

## viewer-yearly-007-extract-05

- Error Type: mismatch

**Content**

> 我家里还有个弟弟，今年刚上高三

**Expected**

```json
{
  "should_extract": true,
  "memory_text": "家里有个弟弟",
  "memory_type": "fact",
  "polarity": "neutral",
  "temporal_scope": "long_term"
}
```

**Actual**

```json
{
  "memory_text": "家里有个弟弟，刚上高三",
  "memory_text_raw": "我家里还有个弟弟，今年刚上高三",
  "memory_text_canonical": "家里有个弟弟，刚上高三",
  "memory_type": "fact",
  "polarity": "neutral",
  "temporal_scope": "long_term",
  "confidence": 0.74,
  "extraction_source": "llm"
}
```

## viewer-yearly-007-extract-06

- Error Type: mismatch

**Content**

> 我平时都骑电动车通勤，单程差不多四十分钟

**Expected**

```json
{
  "should_extract": true,
  "memory_text": "平时骑电动车通勤",
  "memory_type": "fact",
  "polarity": "neutral",
  "temporal_scope": "long_term"
}
```

**Actual**

```json
{
  "memory_text": "骑电动车通勤",
  "memory_text_raw": "我平时都骑电动车通勤，单程差不多四十分钟",
  "memory_text_canonical": "骑电动车通勤",
  "memory_type": "fact",
  "polarity": "neutral",
  "temporal_scope": "long_term",
  "confidence": 0.74,
  "extraction_source": "llm"
}
```

## viewer-yearly-007-extract-07

- Error Type: mismatch

**Content**

> 我一直都想去英国读传媒，申请学校还在准备

**Expected**

```json
{
  "should_extract": true,
  "memory_text": "一直都想去英国读传媒",
  "memory_type": "fact",
  "polarity": "neutral",
  "temporal_scope": "long_term"
}
```

**Actual**

```json
{
  "memory_text": "想去英国读传媒",
  "memory_text_raw": "我一直都想去英国读传媒，申请学校还在准备",
  "memory_text_canonical": "想去英国读传媒",
  "memory_type": "preference",
  "polarity": "positive",
  "temporal_scope": "long_term",
  "confidence": 0.86,
  "extraction_source": "llm"
}
```

## viewer-yearly-007-extract-08

- Error Type: mismatch

**Content**

> 这周我要连着上三天口语课，时间有点满

**Expected**

```json
{
  "should_extract": false,
  "memory_text": "",
  "memory_type": "context",
  "polarity": "neutral",
  "temporal_scope": "short_term"
}
```

**Actual**

```json
{
  "memory_text": "连着上三天口语课",
  "memory_text_raw": "这周我要连着上三天口语课，时间有点满",
  "memory_text_canonical": "连着上三天口语课",
  "memory_type": "fact",
  "polarity": "positive",
  "temporal_scope": "long_term",
  "confidence": 0.74,
  "extraction_source": "llm"
}
```

## viewer-yearly-007-extract-10

- Error Type: mismatch

**Content**

> 明天又要去上口语课，希望这次能顺一点

**Expected**

```json
{
  "should_extract": false,
  "memory_text": "",
  "memory_type": "context",
  "polarity": "neutral",
  "temporal_scope": "short_term"
}
```

**Actual**

```json
{
  "memory_text": "明天口语课",
  "memory_text_raw": "明天又要去上口语课，希望这次能顺一点",
  "memory_text_canonical": "明天口语课",
  "memory_type": "fact",
  "polarity": "positive",
  "temporal_scope": "long_term",
  "confidence": 0.74,
  "extraction_source": "llm"
}
```

## viewer-yearly-008-extract-01

- Error Type: mismatch

**Content**

> 我一直都在减脂，晚饭尽量不吃米饭和面

**Expected**

```json
{
  "should_extract": true,
  "memory_text": "一直都在减脂",
  "memory_type": "fact",
  "polarity": "neutral",
  "temporal_scope": "long_term"
}
```

**Actual**

```json
{
  "memory_text": "减脂，不吃米饭和面",
  "memory_text_raw": "我一直都在减脂，晚饭尽量不吃米饭和面",
  "memory_text_canonical": "减脂，不吃米饭和面",
  "memory_type": "preference",
  "polarity": "negative",
  "temporal_scope": "long_term",
  "confidence": 0.86,
  "extraction_source": "llm"
}
```

## viewer-yearly-008-extract-02

- Error Type: mismatch

**Content**

> 我平时都去公司附近那家健身房，器械还挺全

**Expected**

```json
{
  "should_extract": true,
  "memory_text": "平时去公司附近那家健身房",
  "memory_type": "context",
  "polarity": "neutral",
  "temporal_scope": "long_term"
}
```

**Actual**

```json
{
  "memory_text": "公司附近健身房",
  "memory_text_raw": "我平时都去公司附近那家健身房，器械还挺全",
  "memory_text_canonical": "公司附近健身房",
  "memory_type": "context",
  "polarity": "neutral",
  "temporal_scope": "long_term",
  "confidence": 0.78,
  "extraction_source": "llm"
}
```

## viewer-yearly-008-extract-03

- Error Type: mismatch

**Content**

> 我不能喝纯牛奶，乳糖不耐一喝就肚子疼

**Expected**

```json
{
  "should_extract": true,
  "memory_text": "不能喝纯牛奶",
  "memory_type": "preference",
  "polarity": "negative",
  "temporal_scope": "long_term"
}
```

**Actual**

```json
{
  "memory_text": "乳糖不耐受",
  "memory_text_raw": "我不能喝纯牛奶，乳糖不耐一喝就肚子疼",
  "memory_text_canonical": "乳糖不耐受",
  "memory_type": "fact",
  "polarity": "negative",
  "temporal_scope": "long_term",
  "confidence": 0.74,
  "extraction_source": "llm"
}
```

## viewer-yearly-008-extract-04

- Error Type: mismatch

**Content**

> 我一直都喜欢吃鸡胸和玉米，做饭也方便

**Expected**

```json
{
  "should_extract": true,
  "memory_text": "一直都喜欢吃鸡胸和玉米",
  "memory_type": "preference",
  "polarity": "positive",
  "temporal_scope": "long_term"
}
```

**Actual**

```json
{
  "memory_text": "喜欢吃鸡胸和玉米，做饭方便",
  "memory_text_raw": "我一直都喜欢吃鸡胸和玉米，做饭也方便",
  "memory_text_canonical": "喜欢吃鸡胸和玉米，做饭方便",
  "memory_type": "preference",
  "polarity": "positive",
  "temporal_scope": "long_term",
  "confidence": 0.86,
  "extraction_source": "llm"
}
```

## viewer-yearly-008-extract-06

- Error Type: mismatch

**Content**

> 我平时都习惯早上空腹称体重，看看有没有掉

**Expected**

```json
{
  "should_extract": true,
  "memory_text": "平时早上空腹称体重",
  "memory_type": "fact",
  "polarity": "neutral",
  "temporal_scope": "long_term"
}
```

**Actual**

```json
{
  "memory_text": "习惯空腹称体重",
  "memory_text_raw": "我平时都习惯早上空腹称体重，看看有没有掉",
  "memory_text_canonical": "习惯空腹称体重",
  "memory_type": "fact",
  "polarity": "neutral",
  "temporal_scope": "long_term",
  "confidence": 0.74,
  "extraction_source": "llm"
}
```

## viewer-yearly-008-extract-08

- Error Type: mismatch

**Content**

> 这周我准备冲一下半马配速，训练量会大一点

**Expected**

```json
{
  "should_extract": false,
  "memory_text": "",
  "memory_type": "context",
  "polarity": "neutral",
  "temporal_scope": "short_term"
}
```

**Actual**

```json
{
  "memory_text": "准备冲半马配速",
  "memory_text_raw": "这周我准备冲一下半马配速，训练量会大一点",
  "memory_text_canonical": "准备冲半马配速",
  "memory_type": "fact",
  "polarity": "positive",
  "temporal_scope": "long_term",
  "confidence": 0.74,
  "extraction_source": "llm"
}
```

## viewer-yearly-008-extract-09

- Error Type: mismatch

**Content**

> 我今天腿练完直接酸到楼梯都不想走

**Expected**

```json
{
  "should_extract": false,
  "memory_text": "",
  "memory_type": "context",
  "polarity": "neutral",
  "temporal_scope": "short_term"
}
```

**Actual**

```json
{
  "memory_text": "腿练后酸软",
  "memory_text_raw": "我今天腿练完直接酸到楼梯都不想走",
  "memory_text_canonical": "腿练后酸软",
  "memory_type": "fact",
  "polarity": "negative",
  "temporal_scope": "long_term",
  "confidence": 0.74,
  "extraction_source": "llm"
}
```

## viewer-yearly-008-extract-10

- Error Type: mismatch

**Content**

> 今晚练完准备去吃个轻食碗，别再放纵了

**Expected**

```json
{
  "should_extract": false,
  "memory_text": "",
  "memory_type": "context",
  "polarity": "neutral",
  "temporal_scope": "short_term"
}
```

**Actual**

```json
{
  "memory_text": "练完准备吃轻食碗",
  "memory_text_raw": "今晚练完准备去吃个轻食碗，别再放纵了",
  "memory_text_canonical": "练完准备吃轻食碗",
  "memory_type": "preference",
  "polarity": "positive",
  "temporal_scope": "long_term",
  "confidence": 0.86,
  "extraction_source": "llm"
}
```

## viewer-yearly-008-extract-11

- Error Type: mismatch

**Content**

> 这两天在控制碳水，状态有点一般

**Expected**

```json
{
  "should_extract": false,
  "memory_text": "",
  "memory_type": "context",
  "polarity": "neutral",
  "temporal_scope": "short_term"
}
```

**Actual**

```json
{
  "memory_text": "控制碳水，状态一般",
  "memory_text_raw": "这两天在控制碳水，状态有点一般",
  "memory_text_canonical": "控制碳水，状态一般",
  "memory_type": "fact",
  "polarity": "neutral",
  "temporal_scope": "long_term",
  "confidence": 0.74,
  "extraction_source": "llm"
}
```

## viewer-yearly-008-extract-12

- Error Type: mismatch

**Content**

> 明天想试试新的跑步计划

**Expected**

```json
{
  "should_extract": false,
  "memory_text": "",
  "memory_type": "context",
  "polarity": "neutral",
  "temporal_scope": "short_term"
}
```

**Actual**

```json
{
  "memory_text": "想尝试新的跑步计划",
  "memory_text_raw": "明天想试试新的跑步计划",
  "memory_text_canonical": "想尝试新的跑步计划",
  "memory_type": "preference",
  "polarity": "positive",
  "temporal_scope": "long_term",
  "confidence": 0.86,
  "extraction_source": "llm"
}
```

## viewer-yearly-009-extract-01

- Error Type: mismatch

**Content**

> 我做亚马逊跨境电商，最近一直在看广告数据

**Expected**

```json
{
  "should_extract": true,
  "memory_text": "做亚马逊跨境电商",
  "memory_type": "fact",
  "polarity": "neutral",
  "temporal_scope": "long_term"
}
```

**Actual**

```json
{}
```

## viewer-yearly-009-extract-02

- Error Type: mismatch

**Content**

> 我平时住在深圳，仓库也在这边

**Expected**

```json
{
  "should_extract": true,
  "memory_text": "平时住在深圳",
  "memory_type": "context",
  "polarity": "neutral",
  "temporal_scope": "long_term"
}
```

**Actual**

```json
{
  "memory_text": "住在深圳",
  "memory_text_raw": "我平时住在深圳，仓库也在这边",
  "memory_text_canonical": "住在深圳",
  "memory_type": "context",
  "polarity": "neutral",
  "temporal_scope": "long_term",
  "confidence": 0.78,
  "extraction_source": "llm"
}
```

## viewer-yearly-009-extract-03

- Error Type: mismatch

**Content**

> 我不喜欢一大早开会，脑子根本没开机

**Expected**

```json
{
  "should_extract": true,
  "memory_text": "不喜欢开早会",
  "memory_type": "preference",
  "polarity": "negative",
  "temporal_scope": "long_term"
}
```

**Actual**

```json
{
  "memory_text": "不喜欢开会",
  "memory_text_raw": "我不喜欢一大早开会，脑子根本没开机",
  "memory_text_canonical": "不喜欢开会",
  "memory_type": "preference",
  "polarity": "negative",
  "temporal_scope": "long_term",
  "confidence": 0.86,
  "extraction_source": "llm"
}
```

## viewer-yearly-009-extract-04

- Error Type: mismatch

**Content**

> 我一直都喜欢喝冰美式，特别是盯报表的时候

**Expected**

```json
{
  "should_extract": true,
  "memory_text": "一直都喜欢喝冰美式",
  "memory_type": "preference",
  "polarity": "positive",
  "temporal_scope": "long_term"
}
```

**Actual**

```json
{
  "memory_text": "喜欢冰美式",
  "memory_text_raw": "我一直都喜欢喝冰美式，特别是盯报表的时候",
  "memory_text_canonical": "喜欢冰美式",
  "memory_type": "preference",
  "polarity": "positive",
  "temporal_scope": "long_term",
  "confidence": 0.86,
  "extraction_source": "llm"
}
```

## viewer-yearly-009-extract-05

- Error Type: mismatch

**Content**

> 我经常熬夜看美国站数据，时差真难受

**Expected**

```json
{
  "should_extract": true,
  "memory_text": "经常熬夜看美国站数据",
  "memory_type": "fact",
  "polarity": "neutral",
  "temporal_scope": "long_term"
}
```

**Actual**

```json
{}
```

## viewer-yearly-009-extract-10

- Error Type: mismatch

**Content**

> 明天还得去仓库盘点库存

**Expected**

```json
{
  "should_extract": false,
  "memory_text": "",
  "memory_type": "context",
  "polarity": "neutral",
  "temporal_scope": "short_term"
}
```

**Actual**

```json
{
  "memory_text": "去仓库盘点库存",
  "memory_text_raw": "明天还得去仓库盘点库存",
  "memory_text_canonical": "去仓库盘点库存",
  "memory_type": "fact",
  "polarity": "neutral",
  "temporal_scope": "long_term",
  "confidence": 0.74,
  "extraction_source": "llm"
}
```

## viewer-yearly-009-extract-12

- Error Type: mismatch

**Content**

> 今晚准备把 listing 再优化一下

**Expected**

```json
{
  "should_extract": false,
  "memory_text": "",
  "memory_type": "context",
  "polarity": "neutral",
  "temporal_scope": "short_term"
}
```

**Actual**

```json
{
  "memory_text": "准备优化 listing",
  "memory_text_raw": "今晚准备把 listing 再优化一下",
  "memory_text_canonical": "准备优化 listing",
  "memory_type": "preference",
  "polarity": "positive",
  "temporal_scope": "long_term",
  "confidence": 0.86,
  "extraction_source": "llm"
}
```

## viewer-yearly-010-extract-01

- Error Type: mismatch

**Content**

> 我刚当妈妈没多久，现在还在摸索节奏

**Expected**

```json
{
  "should_extract": true,
  "memory_text": "刚当妈妈",
  "memory_type": "fact",
  "polarity": "neutral",
  "temporal_scope": "long_term"
}
```

**Actual**

```json
{}
```

## viewer-yearly-010-extract-02

- Error Type: mismatch

**Content**

> 我平时住在南京，爸妈偶尔会来帮忙

**Expected**

```json
{
  "should_extract": true,
  "memory_text": "平时住在南京",
  "memory_type": "context",
  "polarity": "neutral",
  "temporal_scope": "long_term"
}
```

**Actual**

```json
{
  "memory_text": "住在南京，父母偶尔帮忙",
  "memory_text_raw": "我平时住在南京，爸妈偶尔会来帮忙",
  "memory_text_canonical": "住在南京，父母偶尔帮忙",
  "memory_type": "context",
  "polarity": "neutral",
  "temporal_scope": "long_term",
  "confidence": 0.78,
  "extraction_source": "llm"
}
```

## viewer-yearly-010-extract-03

- Error Type: mismatch

**Content**

> 我不喜欢香精味太重的护肤品，闻着头晕

**Expected**

```json
{
  "should_extract": true,
  "memory_text": "不喜欢香精味太重的护肤品",
  "memory_type": "preference",
  "polarity": "negative",
  "temporal_scope": "long_term"
}
```

**Actual**

```json
{
  "memory_text": "不喜欢香精味重的护肤品",
  "memory_text_raw": "我不喜欢香精味太重的护肤品，闻着头晕",
  "memory_text_canonical": "不喜欢香精味重的护肤品",
  "memory_type": "preference",
  "polarity": "negative",
  "temporal_scope": "long_term",
  "confidence": 0.86,
  "extraction_source": "llm"
}
```

## viewer-yearly-010-extract-04

- Error Type: mismatch

**Content**

> 我一直都喜欢喝温豆浆，早上比较舒服

**Expected**

```json
{
  "should_extract": true,
  "memory_text": "一直都喜欢喝温豆浆",
  "memory_type": "preference",
  "polarity": "positive",
  "temporal_scope": "long_term"
}
```

**Actual**

```json
{
  "memory_text": "喜欢喝温豆浆",
  "memory_text_raw": "我一直都喜欢喝温豆浆，早上比较舒服",
  "memory_text_canonical": "喜欢喝温豆浆",
  "memory_type": "preference",
  "polarity": "positive",
  "temporal_scope": "long_term",
  "confidence": 0.86,
  "extraction_source": "llm"
}
```

## viewer-yearly-010-extract-05

- Error Type: mismatch

**Content**

> 我晚上经常要起夜喂奶，睡眠一直断断续续

**Expected**

```json
{
  "should_extract": true,
  "memory_text": "晚上经常要起夜喂奶",
  "memory_type": "fact",
  "polarity": "neutral",
  "temporal_scope": "long_term"
}
```

**Actual**

```json
{}
```

## viewer-yearly-010-extract-07

- Error Type: mismatch

**Content**

> 我平时喜欢囤湿巾和纸尿裤，怕突然不够用

**Expected**

```json
{
  "should_extract": true,
  "memory_text": "平时喜欢囤湿巾和纸尿裤",
  "memory_type": "preference",
  "polarity": "positive",
  "temporal_scope": "long_term"
}
```

**Actual**

```json
{
  "memory_text": "喜欢囤湿巾和纸尿裤",
  "memory_text_raw": "我平时喜欢囤湿巾和纸尿裤，怕突然不够用",
  "memory_text_canonical": "喜欢囤湿巾和纸尿裤",
  "memory_type": "preference",
  "polarity": "positive",
  "temporal_scope": "long_term",
  "confidence": 0.86,
  "extraction_source": "llm"
}
```

## viewer-yearly-010-extract-09

- Error Type: mismatch

**Content**

> 今天终于睡了个整觉，太不容易了

**Expected**

```json
{
  "should_extract": false,
  "memory_text": "",
  "memory_type": "context",
  "polarity": "neutral",
  "temporal_scope": "short_term"
}
```

**Actual**

```json
{
  "memory_text": "整觉",
  "memory_text_raw": "今天终于睡了个整觉，太不容易了",
  "memory_text_canonical": "整觉",
  "memory_type": "fact",
  "polarity": "positive",
  "temporal_scope": "long_term",
  "confidence": 0.74,
  "extraction_source": "llm"
}
```

## viewer-yearly-010-extract-10

- Error Type: mismatch

**Content**

> 明天要带宝宝去打疫苗

**Expected**

```json
{
  "should_extract": false,
  "memory_text": "",
  "memory_type": "context",
  "polarity": "neutral",
  "temporal_scope": "short_term"
}
```

**Actual**

```json
{
  "memory_text": "带宝宝去打疫苗",
  "memory_text_raw": "明天要带宝宝去打疫苗",
  "memory_text_canonical": "带宝宝去打疫苗",
  "memory_type": "fact",
  "polarity": "positive",
  "temporal_scope": "long_term",
  "confidence": 0.74,
  "extraction_source": "llm"
}
```

## viewer-yearly-011-extract-01

- Error Type: mismatch

**Content**

> 我在杭州做前端开发，最近项目一直在赶需求

**Expected**

```json
{
  "should_extract": true,
  "memory_text": "在杭州做前端开发",
  "memory_type": "context",
  "polarity": "neutral",
  "temporal_scope": "long_term"
}
```

**Actual**

```json
{
  "memory_text": "在杭州做前端开发，项目赶需求",
  "memory_text_raw": "我在杭州做前端开发，最近项目一直在赶需求",
  "memory_text_canonical": "在杭州做前端开发，项目赶需求",
  "memory_type": "fact",
  "polarity": "neutral",
  "temporal_scope": "long_term",
  "confidence": 0.74,
  "extraction_source": "llm"
}
```

## viewer-yearly-011-extract-02

- Error Type: mismatch

**Content**

> 我平时都要喝美式咖啡，不然下午根本顶不住

**Expected**

```json
{
  "should_extract": true,
  "memory_text": "平时都喝美式咖啡",
  "memory_type": "preference",
  "polarity": "positive",
  "temporal_scope": "long_term"
}
```

**Actual**

```json
{
  "memory_text": "平时喝美式咖啡",
  "memory_text_raw": "我平时都要喝美式咖啡，不然下午根本顶不住",
  "memory_text_canonical": "平时喝美式咖啡",
  "memory_type": "preference",
  "polarity": "positive",
  "temporal_scope": "long_term",
  "confidence": 0.86,
  "extraction_source": "llm"
}
```

## viewer-yearly-011-extract-03

- Error Type: mismatch

**Content**

> 我不太能吃辣，吃多了胃会不舒服

**Expected**

```json
{
  "should_extract": true,
  "memory_text": "不太能吃辣",
  "memory_type": "preference",
  "polarity": "negative",
  "temporal_scope": "long_term"
}
```

**Actual**

```json
{}
```

## viewer-yearly-011-extract-05

- Error Type: mismatch

**Content**

> 我家里养了两只猫，晚上回去还得铲屎

**Expected**

```json
{
  "should_extract": true,
  "memory_text": "家里养了两只猫",
  "memory_type": "fact",
  "polarity": "neutral",
  "temporal_scope": "long_term"
}
```

**Actual**

```json
{
  "memory_text": "养猫",
  "memory_text_raw": "我家里养了两只猫，晚上回去还得铲屎",
  "memory_text_canonical": "养猫",
  "memory_type": "fact",
  "polarity": "neutral",
  "temporal_scope": "long_term",
  "confidence": 0.74,
  "extraction_source": "llm"
}
```

## viewer-yearly-011-extract-06

- Error Type: mismatch

**Content**

> 我一直都喜欢吃豚骨拉面，周末经常去那家店

**Expected**

```json
{
  "should_extract": true,
  "memory_text": "一直都喜欢吃豚骨拉面",
  "memory_type": "preference",
  "polarity": "positive",
  "temporal_scope": "long_term"
}
```

**Actual**

```json
{
  "memory_text": "喜欢吃豚骨拉面",
  "memory_text_raw": "我一直都喜欢吃豚骨拉面，周末经常去那家店",
  "memory_text_canonical": "喜欢吃豚骨拉面",
  "memory_type": "preference",
  "polarity": "positive",
  "temporal_scope": "long_term",
  "confidence": 0.86,
  "extraction_source": "llm"
}
```

## viewer-yearly-011-extract-07

- Error Type: mismatch

**Content**

> 我平时都是凌晨一点以后才睡，作息有点乱

**Expected**

```json
{
  "should_extract": true,
  "memory_text": "平时凌晨一点以后才睡",
  "memory_type": "fact",
  "polarity": "neutral",
  "temporal_scope": "long_term"
}
```

**Actual**

```json
{}
```

## viewer-yearly-011-extract-08

- Error Type: mismatch

**Content**

> 这周我准备连续夜跑，把作息拉回来

**Expected**

```json
{
  "should_extract": false,
  "memory_text": "",
  "memory_type": "context",
  "polarity": "neutral",
  "temporal_scope": "short_term"
}
```

**Actual**

```json
{
  "memory_text": "连续夜跑",
  "memory_text_raw": "这周我准备连续夜跑，把作息拉回来",
  "memory_text_canonical": "连续夜跑",
  "memory_type": "fact",
  "polarity": "positive",
  "temporal_scope": "long_term",
  "confidence": 0.74,
  "extraction_source": "llm"
}
```

## viewer-yearly-011-extract-10

- Error Type: mismatch

**Content**

> 今晚下班还想去吃面，最近就馋这口

**Expected**

```json
{
  "should_extract": false,
  "memory_text": "",
  "memory_type": "context",
  "polarity": "neutral",
  "temporal_scope": "short_term"
}
```

**Actual**

```json
{
  "memory_text": "下班想吃面",
  "memory_text_raw": "今晚下班还想去吃面，最近就馋这口",
  "memory_text_canonical": "下班想吃面",
  "memory_type": "preference",
  "polarity": "positive",
  "temporal_scope": "long_term",
  "confidence": 0.86,
  "extraction_source": "llm"
}
```

## viewer-yearly-012-extract-01

- Error Type: mismatch

**Content**

> 我最近在备考雅思，晚上下班后会背单词做听力

**Expected**

```json
{
  "should_extract": true,
  "memory_text": "最近在备考雅思",
  "memory_type": "fact",
  "polarity": "neutral",
  "temporal_scope": "long_term"
}
```

**Actual**

```json
{
  "memory_text": "备考雅思，晚上下班后背单词",
  "memory_text_raw": "我最近在备考雅思，晚上下班后会背单词做听力",
  "memory_text_canonical": "备考雅思，晚上下班后背单词",
  "memory_type": "fact",
  "polarity": "positive",
  "temporal_scope": "long_term",
  "confidence": 0.74,
  "extraction_source": "llm"
}
```

## viewer-yearly-012-extract-02

- Error Type: mismatch

**Content**

> 我平时都住在苏州，公司在园区那边

**Expected**

```json
{
  "should_extract": true,
  "memory_text": "平时住在苏州",
  "memory_type": "context",
  "polarity": "neutral",
  "temporal_scope": "long_term"
}
```

**Actual**

```json
{
  "memory_text": "住在苏州，公司位置",
  "memory_text_raw": "我平时都住在苏州，公司在园区那边",
  "memory_text_canonical": "住在苏州，公司位置",
  "memory_type": "context",
  "polarity": "neutral",
  "temporal_scope": "long_term",
  "confidence": 0.78,
  "extraction_source": "llm"
}
```

## viewer-yearly-012-extract-04

- Error Type: mismatch

**Content**

> 我一直都喜欢喝无糖可乐，复习的时候会来一瓶

**Expected**

```json
{
  "should_extract": true,
  "memory_text": "一直都喜欢喝无糖可乐",
  "memory_type": "preference",
  "polarity": "positive",
  "temporal_scope": "long_term"
}
```

**Actual**

```json
{
  "memory_text": "喜欢喝无糖可乐",
  "memory_text_raw": "我一直都喜欢喝无糖可乐，复习的时候会来一瓶",
  "memory_text_canonical": "喜欢喝无糖可乐",
  "memory_type": "preference",
  "polarity": "positive",
  "temporal_scope": "long_term",
  "confidence": 0.86,
  "extraction_source": "llm"
}
```

## viewer-yearly-012-extract-05

- Error Type: mismatch

**Content**

> 我家里还有个弟弟，今年刚上高三

**Expected**

```json
{
  "should_extract": true,
  "memory_text": "家里有个弟弟",
  "memory_type": "fact",
  "polarity": "neutral",
  "temporal_scope": "long_term"
}
```

**Actual**

```json
{
  "memory_text": "家里有个弟弟，刚上高三",
  "memory_text_raw": "我家里还有个弟弟，今年刚上高三",
  "memory_text_canonical": "家里有个弟弟，刚上高三",
  "memory_type": "fact",
  "polarity": "neutral",
  "temporal_scope": "long_term",
  "confidence": 0.74,
  "extraction_source": "llm"
}
```

## viewer-yearly-012-extract-06

- Error Type: mismatch

**Content**

> 我平时都骑电动车通勤，单程差不多四十分钟

**Expected**

```json
{
  "should_extract": true,
  "memory_text": "平时骑电动车通勤",
  "memory_type": "fact",
  "polarity": "neutral",
  "temporal_scope": "long_term"
}
```

**Actual**

```json
{
  "memory_text": "骑电动车通勤",
  "memory_text_raw": "我平时都骑电动车通勤，单程差不多四十分钟",
  "memory_text_canonical": "骑电动车通勤",
  "memory_type": "fact",
  "polarity": "neutral",
  "temporal_scope": "long_term",
  "confidence": 0.74,
  "extraction_source": "llm"
}
```

## viewer-yearly-012-extract-07

- Error Type: mismatch

**Content**

> 我一直都想去英国读传媒，申请学校还在准备

**Expected**

```json
{
  "should_extract": true,
  "memory_text": "一直都想去英国读传媒",
  "memory_type": "fact",
  "polarity": "neutral",
  "temporal_scope": "long_term"
}
```

**Actual**

```json
{
  "memory_text": "想去英国读传媒",
  "memory_text_raw": "我一直都想去英国读传媒，申请学校还在准备",
  "memory_text_canonical": "想去英国读传媒",
  "memory_type": "preference",
  "polarity": "positive",
  "temporal_scope": "long_term",
  "confidence": 0.86,
  "extraction_source": "llm"
}
```

## viewer-yearly-012-extract-08

- Error Type: mismatch

**Content**

> 这周我要连着上三天口语课，时间有点满

**Expected**

```json
{
  "should_extract": false,
  "memory_text": "",
  "memory_type": "context",
  "polarity": "neutral",
  "temporal_scope": "short_term"
}
```

**Actual**

```json
{
  "memory_text": "连着上三天口语课",
  "memory_text_raw": "这周我要连着上三天口语课，时间有点满",
  "memory_text_canonical": "连着上三天口语课",
  "memory_type": "fact",
  "polarity": "positive",
  "temporal_scope": "long_term",
  "confidence": 0.74,
  "extraction_source": "llm"
}
```

## viewer-yearly-012-extract-10

- Error Type: mismatch

**Content**

> 明天又要去上口语课，希望这次能顺一点

**Expected**

```json
{
  "should_extract": false,
  "memory_text": "",
  "memory_type": "context",
  "polarity": "neutral",
  "temporal_scope": "short_term"
}
```

**Actual**

```json
{
  "memory_text": "明天口语课",
  "memory_text_raw": "明天又要去上口语课，希望这次能顺一点",
  "memory_text_canonical": "明天口语课",
  "memory_type": "fact",
  "polarity": "positive",
  "temporal_scope": "long_term",
  "confidence": 0.74,
  "extraction_source": "llm"
}
```

## viewer-yearly-013-extract-01

- Error Type: mismatch

**Content**

> 我一直都在减脂，晚饭尽量不吃米饭和面

**Expected**

```json
{
  "should_extract": true,
  "memory_text": "一直都在减脂",
  "memory_type": "fact",
  "polarity": "neutral",
  "temporal_scope": "long_term"
}
```

**Actual**

```json
{
  "memory_text": "减脂，不吃米饭和面",
  "memory_text_raw": "我一直都在减脂，晚饭尽量不吃米饭和面",
  "memory_text_canonical": "减脂，不吃米饭和面",
  "memory_type": "preference",
  "polarity": "negative",
  "temporal_scope": "long_term",
  "confidence": 0.86,
  "extraction_source": "llm"
}
```

## viewer-yearly-013-extract-02

- Error Type: mismatch

**Content**

> 我平时都去公司附近那家健身房，器械还挺全

**Expected**

```json
{
  "should_extract": true,
  "memory_text": "平时去公司附近那家健身房",
  "memory_type": "context",
  "polarity": "neutral",
  "temporal_scope": "long_term"
}
```

**Actual**

```json
{
  "memory_text": "公司附近健身房",
  "memory_text_raw": "我平时都去公司附近那家健身房，器械还挺全",
  "memory_text_canonical": "公司附近健身房",
  "memory_type": "context",
  "polarity": "neutral",
  "temporal_scope": "long_term",
  "confidence": 0.78,
  "extraction_source": "llm"
}
```

## viewer-yearly-013-extract-03

- Error Type: mismatch

**Content**

> 我不能喝纯牛奶，乳糖不耐一喝就肚子疼

**Expected**

```json
{
  "should_extract": true,
  "memory_text": "不能喝纯牛奶",
  "memory_type": "preference",
  "polarity": "negative",
  "temporal_scope": "long_term"
}
```

**Actual**

```json
{
  "memory_text": "乳糖不耐受",
  "memory_text_raw": "我不能喝纯牛奶，乳糖不耐一喝就肚子疼",
  "memory_text_canonical": "乳糖不耐受",
  "memory_type": "fact",
  "polarity": "negative",
  "temporal_scope": "long_term",
  "confidence": 0.74,
  "extraction_source": "llm"
}
```

## viewer-yearly-013-extract-04

- Error Type: mismatch

**Content**

> 我一直都喜欢吃鸡胸和玉米，做饭也方便

**Expected**

```json
{
  "should_extract": true,
  "memory_text": "一直都喜欢吃鸡胸和玉米",
  "memory_type": "preference",
  "polarity": "positive",
  "temporal_scope": "long_term"
}
```

**Actual**

```json
{
  "memory_text": "喜欢吃鸡胸和玉米，做饭方便",
  "memory_text_raw": "我一直都喜欢吃鸡胸和玉米，做饭也方便",
  "memory_text_canonical": "喜欢吃鸡胸和玉米，做饭方便",
  "memory_type": "preference",
  "polarity": "positive",
  "temporal_scope": "long_term",
  "confidence": 0.86,
  "extraction_source": "llm"
}
```

## viewer-yearly-013-extract-06

- Error Type: mismatch

**Content**

> 我平时都习惯早上空腹称体重，看看有没有掉

**Expected**

```json
{
  "should_extract": true,
  "memory_text": "平时早上空腹称体重",
  "memory_type": "fact",
  "polarity": "neutral",
  "temporal_scope": "long_term"
}
```

**Actual**

```json
{
  "memory_text": "习惯空腹称体重",
  "memory_text_raw": "我平时都习惯早上空腹称体重，看看有没有掉",
  "memory_text_canonical": "习惯空腹称体重",
  "memory_type": "fact",
  "polarity": "neutral",
  "temporal_scope": "long_term",
  "confidence": 0.74,
  "extraction_source": "llm"
}
```

## viewer-yearly-013-extract-08

- Error Type: mismatch

**Content**

> 这周我准备冲一下半马配速，训练量会大一点

**Expected**

```json
{
  "should_extract": false,
  "memory_text": "",
  "memory_type": "context",
  "polarity": "neutral",
  "temporal_scope": "short_term"
}
```

**Actual**

```json
{
  "memory_text": "准备冲半马配速",
  "memory_text_raw": "这周我准备冲一下半马配速，训练量会大一点",
  "memory_text_canonical": "准备冲半马配速",
  "memory_type": "fact",
  "polarity": "positive",
  "temporal_scope": "long_term",
  "confidence": 0.74,
  "extraction_source": "llm"
}
```

## viewer-yearly-013-extract-09

- Error Type: mismatch

**Content**

> 我今天腿练完直接酸到楼梯都不想走

**Expected**

```json
{
  "should_extract": false,
  "memory_text": "",
  "memory_type": "context",
  "polarity": "neutral",
  "temporal_scope": "short_term"
}
```

**Actual**

```json
{
  "memory_text": "腿练后酸软",
  "memory_text_raw": "我今天腿练完直接酸到楼梯都不想走",
  "memory_text_canonical": "腿练后酸软",
  "memory_type": "fact",
  "polarity": "negative",
  "temporal_scope": "long_term",
  "confidence": 0.74,
  "extraction_source": "llm"
}
```

## viewer-yearly-013-extract-10

- Error Type: mismatch

**Content**

> 今晚练完准备去吃个轻食碗，别再放纵了

**Expected**

```json
{
  "should_extract": false,
  "memory_text": "",
  "memory_type": "context",
  "polarity": "neutral",
  "temporal_scope": "short_term"
}
```

**Actual**

```json
{
  "memory_text": "练完准备吃轻食碗",
  "memory_text_raw": "今晚练完准备去吃个轻食碗，别再放纵了",
  "memory_text_canonical": "练完准备吃轻食碗",
  "memory_type": "preference",
  "polarity": "positive",
  "temporal_scope": "long_term",
  "confidence": 0.86,
  "extraction_source": "llm"
}
```

## viewer-yearly-013-extract-12

- Error Type: mismatch

**Content**

> 明天想试试新的跑步计划

**Expected**

```json
{
  "should_extract": false,
  "memory_text": "",
  "memory_type": "context",
  "polarity": "neutral",
  "temporal_scope": "short_term"
}
```

**Actual**

```json
{
  "memory_text": "想尝试新的跑步计划",
  "memory_text_raw": "明天想试试新的跑步计划",
  "memory_text_canonical": "想尝试新的跑步计划",
  "memory_type": "preference",
  "polarity": "positive",
  "temporal_scope": "long_term",
  "confidence": 0.86,
  "extraction_source": "llm"
}
```

## viewer-yearly-014-extract-01

- Error Type: mismatch

**Content**

> 我做亚马逊跨境电商，最近一直在看广告数据

**Expected**

```json
{
  "should_extract": true,
  "memory_text": "做亚马逊跨境电商",
  "memory_type": "fact",
  "polarity": "neutral",
  "temporal_scope": "long_term"
}
```

**Actual**

```json
{}
```

## viewer-yearly-014-extract-02

- Error Type: mismatch

**Content**

> 我平时住在深圳，仓库也在这边

**Expected**

```json
{
  "should_extract": true,
  "memory_text": "平时住在深圳",
  "memory_type": "context",
  "polarity": "neutral",
  "temporal_scope": "long_term"
}
```

**Actual**

```json
{
  "memory_text": "住在深圳",
  "memory_text_raw": "我平时住在深圳，仓库也在这边",
  "memory_text_canonical": "住在深圳",
  "memory_type": "context",
  "polarity": "neutral",
  "temporal_scope": "long_term",
  "confidence": 0.78,
  "extraction_source": "llm"
}
```

## viewer-yearly-014-extract-03

- Error Type: mismatch

**Content**

> 我不喜欢一大早开会，脑子根本没开机

**Expected**

```json
{
  "should_extract": true,
  "memory_text": "不喜欢开早会",
  "memory_type": "preference",
  "polarity": "negative",
  "temporal_scope": "long_term"
}
```

**Actual**

```json
{
  "memory_text": "不喜欢开会",
  "memory_text_raw": "我不喜欢一大早开会，脑子根本没开机",
  "memory_text_canonical": "不喜欢开会",
  "memory_type": "preference",
  "polarity": "negative",
  "temporal_scope": "long_term",
  "confidence": 0.86,
  "extraction_source": "llm"
}
```

## viewer-yearly-014-extract-04

- Error Type: mismatch

**Content**

> 我一直都喜欢喝冰美式，特别是盯报表的时候

**Expected**

```json
{
  "should_extract": true,
  "memory_text": "一直都喜欢喝冰美式",
  "memory_type": "preference",
  "polarity": "positive",
  "temporal_scope": "long_term"
}
```

**Actual**

```json
{
  "memory_text": "喜欢冰美式",
  "memory_text_raw": "我一直都喜欢喝冰美式，特别是盯报表的时候",
  "memory_text_canonical": "喜欢冰美式",
  "memory_type": "preference",
  "polarity": "positive",
  "temporal_scope": "long_term",
  "confidence": 0.86,
  "extraction_source": "llm"
}
```

## viewer-yearly-014-extract-05

- Error Type: mismatch

**Content**

> 我经常熬夜看美国站数据，时差真难受

**Expected**

```json
{
  "should_extract": true,
  "memory_text": "经常熬夜看美国站数据",
  "memory_type": "fact",
  "polarity": "neutral",
  "temporal_scope": "long_term"
}
```

**Actual**

```json
{}
```

## viewer-yearly-014-extract-10

- Error Type: mismatch

**Content**

> 明天还得去仓库盘点库存

**Expected**

```json
{
  "should_extract": false,
  "memory_text": "",
  "memory_type": "context",
  "polarity": "neutral",
  "temporal_scope": "short_term"
}
```

**Actual**

```json
{
  "memory_text": "去仓库盘点库存",
  "memory_text_raw": "明天还得去仓库盘点库存",
  "memory_text_canonical": "去仓库盘点库存",
  "memory_type": "fact",
  "polarity": "neutral",
  "temporal_scope": "long_term",
  "confidence": 0.74,
  "extraction_source": "llm"
}
```

## viewer-yearly-015-extract-01

- Error Type: mismatch

**Content**

> 我刚当妈妈没多久，现在还在摸索节奏

**Expected**

```json
{
  "should_extract": true,
  "memory_text": "刚当妈妈",
  "memory_type": "fact",
  "polarity": "neutral",
  "temporal_scope": "long_term"
}
```

**Actual**

```json
{}
```

## viewer-yearly-015-extract-02

- Error Type: mismatch

**Content**

> 我平时住在南京，爸妈偶尔会来帮忙

**Expected**

```json
{
  "should_extract": true,
  "memory_text": "平时住在南京",
  "memory_type": "context",
  "polarity": "neutral",
  "temporal_scope": "long_term"
}
```

**Actual**

```json
{
  "memory_text": "住在南京，父母偶尔帮忙",
  "memory_text_raw": "我平时住在南京，爸妈偶尔会来帮忙",
  "memory_text_canonical": "住在南京，父母偶尔帮忙",
  "memory_type": "context",
  "polarity": "neutral",
  "temporal_scope": "long_term",
  "confidence": 0.78,
  "extraction_source": "llm"
}
```

## viewer-yearly-015-extract-03

- Error Type: mismatch

**Content**

> 我不喜欢香精味太重的护肤品，闻着头晕

**Expected**

```json
{
  "should_extract": true,
  "memory_text": "不喜欢香精味太重的护肤品",
  "memory_type": "preference",
  "polarity": "negative",
  "temporal_scope": "long_term"
}
```

**Actual**

```json
{
  "memory_text": "不喜欢香精味重的护肤品",
  "memory_text_raw": "我不喜欢香精味太重的护肤品，闻着头晕",
  "memory_text_canonical": "不喜欢香精味重的护肤品",
  "memory_type": "preference",
  "polarity": "negative",
  "temporal_scope": "long_term",
  "confidence": 0.86,
  "extraction_source": "llm"
}
```

## viewer-yearly-015-extract-04

- Error Type: mismatch

**Content**

> 我一直都喜欢喝温豆浆，早上比较舒服

**Expected**

```json
{
  "should_extract": true,
  "memory_text": "一直都喜欢喝温豆浆",
  "memory_type": "preference",
  "polarity": "positive",
  "temporal_scope": "long_term"
}
```

**Actual**

```json
{
  "memory_text": "喜欢喝温豆浆",
  "memory_text_raw": "我一直都喜欢喝温豆浆，早上比较舒服",
  "memory_text_canonical": "喜欢喝温豆浆",
  "memory_type": "preference",
  "polarity": "positive",
  "temporal_scope": "long_term",
  "confidence": 0.86,
  "extraction_source": "llm"
}
```

## viewer-yearly-015-extract-05

- Error Type: mismatch

**Content**

> 我晚上经常要起夜喂奶，睡眠一直断断续续

**Expected**

```json
{
  "should_extract": true,
  "memory_text": "晚上经常要起夜喂奶",
  "memory_type": "fact",
  "polarity": "neutral",
  "temporal_scope": "long_term"
}
```

**Actual**

```json
{}
```

## viewer-yearly-015-extract-07

- Error Type: mismatch

**Content**

> 我平时喜欢囤湿巾和纸尿裤，怕突然不够用

**Expected**

```json
{
  "should_extract": true,
  "memory_text": "平时喜欢囤湿巾和纸尿裤",
  "memory_type": "preference",
  "polarity": "positive",
  "temporal_scope": "long_term"
}
```

**Actual**

```json
{
  "memory_text": "喜欢囤湿巾和纸尿裤",
  "memory_text_raw": "我平时喜欢囤湿巾和纸尿裤，怕突然不够用",
  "memory_text_canonical": "喜欢囤湿巾和纸尿裤",
  "memory_type": "preference",
  "polarity": "positive",
  "temporal_scope": "long_term",
  "confidence": 0.86,
  "extraction_source": "llm"
}
```

## viewer-yearly-015-extract-09

- Error Type: mismatch

**Content**

> 今天终于睡了个整觉，太不容易了

**Expected**

```json
{
  "should_extract": false,
  "memory_text": "",
  "memory_type": "context",
  "polarity": "neutral",
  "temporal_scope": "short_term"
}
```

**Actual**

```json
{
  "memory_text": "整觉",
  "memory_text_raw": "今天终于睡了个整觉，太不容易了",
  "memory_text_canonical": "整觉",
  "memory_type": "fact",
  "polarity": "positive",
  "temporal_scope": "long_term",
  "confidence": 0.74,
  "extraction_source": "llm"
}
```

## viewer-yearly-015-extract-10

- Error Type: mismatch

**Content**

> 明天要带宝宝去打疫苗

**Expected**

```json
{
  "should_extract": false,
  "memory_text": "",
  "memory_type": "context",
  "polarity": "neutral",
  "temporal_scope": "short_term"
}
```

**Actual**

```json
{
  "memory_text": "带宝宝去打疫苗",
  "memory_text_raw": "明天要带宝宝去打疫苗",
  "memory_text_canonical": "带宝宝去打疫苗",
  "memory_type": "fact",
  "polarity": "positive",
  "temporal_scope": "long_term",
  "confidence": 0.74,
  "extraction_source": "llm"
}
```

## viewer-yearly-016-extract-01

- Error Type: mismatch

**Content**

> 我在杭州做前端开发，最近项目一直在赶需求

**Expected**

```json
{
  "should_extract": true,
  "memory_text": "在杭州做前端开发",
  "memory_type": "context",
  "polarity": "neutral",
  "temporal_scope": "long_term"
}
```

**Actual**

```json
{
  "memory_text": "在杭州做前端开发，项目赶需求",
  "memory_text_raw": "我在杭州做前端开发，最近项目一直在赶需求",
  "memory_text_canonical": "在杭州做前端开发，项目赶需求",
  "memory_type": "fact",
  "polarity": "neutral",
  "temporal_scope": "long_term",
  "confidence": 0.74,
  "extraction_source": "llm"
}
```

## viewer-yearly-016-extract-02

- Error Type: mismatch

**Content**

> 我平时都要喝美式咖啡，不然下午根本顶不住

**Expected**

```json
{
  "should_extract": true,
  "memory_text": "平时都喝美式咖啡",
  "memory_type": "preference",
  "polarity": "positive",
  "temporal_scope": "long_term"
}
```

**Actual**

```json
{
  "memory_text": "平时喝美式咖啡",
  "memory_text_raw": "我平时都要喝美式咖啡，不然下午根本顶不住",
  "memory_text_canonical": "平时喝美式咖啡",
  "memory_type": "preference",
  "polarity": "positive",
  "temporal_scope": "long_term",
  "confidence": 0.86,
  "extraction_source": "llm"
}
```

## viewer-yearly-016-extract-03

- Error Type: mismatch

**Content**

> 我不太能吃辣，吃多了胃会不舒服

**Expected**

```json
{
  "should_extract": true,
  "memory_text": "不太能吃辣",
  "memory_type": "preference",
  "polarity": "negative",
  "temporal_scope": "long_term"
}
```

**Actual**

```json
{}
```

## viewer-yearly-016-extract-05

- Error Type: mismatch

**Content**

> 我家里养了两只猫，晚上回去还得铲屎

**Expected**

```json
{
  "should_extract": true,
  "memory_text": "家里养了两只猫",
  "memory_type": "fact",
  "polarity": "neutral",
  "temporal_scope": "long_term"
}
```

**Actual**

```json
{
  "memory_text": "养猫",
  "memory_text_raw": "我家里养了两只猫，晚上回去还得铲屎",
  "memory_text_canonical": "养猫",
  "memory_type": "fact",
  "polarity": "neutral",
  "temporal_scope": "long_term",
  "confidence": 0.74,
  "extraction_source": "llm"
}
```

## viewer-yearly-016-extract-06

- Error Type: mismatch

**Content**

> 我一直都喜欢吃豚骨拉面，周末经常去那家店

**Expected**

```json
{
  "should_extract": true,
  "memory_text": "一直都喜欢吃豚骨拉面",
  "memory_type": "preference",
  "polarity": "positive",
  "temporal_scope": "long_term"
}
```

**Actual**

```json
{
  "memory_text": "喜欢吃豚骨拉面",
  "memory_text_raw": "我一直都喜欢吃豚骨拉面，周末经常去那家店",
  "memory_text_canonical": "喜欢吃豚骨拉面",
  "memory_type": "preference",
  "polarity": "positive",
  "temporal_scope": "long_term",
  "confidence": 0.86,
  "extraction_source": "llm"
}
```

## viewer-yearly-016-extract-07

- Error Type: mismatch

**Content**

> 我平时都是凌晨一点以后才睡，作息有点乱

**Expected**

```json
{
  "should_extract": true,
  "memory_text": "平时凌晨一点以后才睡",
  "memory_type": "fact",
  "polarity": "neutral",
  "temporal_scope": "long_term"
}
```

**Actual**

```json
{}
```

## viewer-yearly-016-extract-08

- Error Type: mismatch

**Content**

> 这周我准备连续夜跑，把作息拉回来

**Expected**

```json
{
  "should_extract": false,
  "memory_text": "",
  "memory_type": "context",
  "polarity": "neutral",
  "temporal_scope": "short_term"
}
```

**Actual**

```json
{
  "memory_text": "连续夜跑",
  "memory_text_raw": "这周我准备连续夜跑，把作息拉回来",
  "memory_text_canonical": "连续夜跑",
  "memory_type": "fact",
  "polarity": "positive",
  "temporal_scope": "long_term",
  "confidence": 0.74,
  "extraction_source": "llm"
}
```

## viewer-yearly-016-extract-10

- Error Type: mismatch

**Content**

> 今晚下班还想去吃面，最近就馋这口

**Expected**

```json
{
  "should_extract": false,
  "memory_text": "",
  "memory_type": "context",
  "polarity": "neutral",
  "temporal_scope": "short_term"
}
```

**Actual**

```json
{
  "memory_text": "下班想吃面",
  "memory_text_raw": "今晚下班还想去吃面，最近就馋这口",
  "memory_text_canonical": "下班想吃面",
  "memory_type": "preference",
  "polarity": "positive",
  "temporal_scope": "long_term",
  "confidence": 0.86,
  "extraction_source": "llm"
}
```

## viewer-yearly-017-extract-01

- Error Type: mismatch

**Content**

> 我最近在备考雅思，晚上下班后会背单词做听力

**Expected**

```json
{
  "should_extract": true,
  "memory_text": "最近在备考雅思",
  "memory_type": "fact",
  "polarity": "neutral",
  "temporal_scope": "long_term"
}
```

**Actual**

```json
{
  "memory_text": "备考雅思，晚上下班后背单词",
  "memory_text_raw": "我最近在备考雅思，晚上下班后会背单词做听力",
  "memory_text_canonical": "备考雅思，晚上下班后背单词",
  "memory_type": "fact",
  "polarity": "positive",
  "temporal_scope": "long_term",
  "confidence": 0.74,
  "extraction_source": "llm"
}
```

## viewer-yearly-017-extract-02

- Error Type: mismatch

**Content**

> 我平时都住在苏州，公司在园区那边

**Expected**

```json
{
  "should_extract": true,
  "memory_text": "平时住在苏州",
  "memory_type": "context",
  "polarity": "neutral",
  "temporal_scope": "long_term"
}
```

**Actual**

```json
{
  "memory_text": "住在苏州，公司位于园区",
  "memory_text_raw": "我平时都住在苏州，公司在园区那边",
  "memory_text_canonical": "住在苏州，公司位于园区",
  "memory_type": "context",
  "polarity": "neutral",
  "temporal_scope": "long_term",
  "confidence": 0.78,
  "extraction_source": "llm"
}
```

## viewer-yearly-017-extract-04

- Error Type: mismatch

**Content**

> 我一直都喜欢喝无糖可乐，复习的时候会来一瓶

**Expected**

```json
{
  "should_extract": true,
  "memory_text": "一直都喜欢喝无糖可乐",
  "memory_type": "preference",
  "polarity": "positive",
  "temporal_scope": "long_term"
}
```

**Actual**

```json
{
  "memory_text": "喜欢喝无糖可乐",
  "memory_text_raw": "我一直都喜欢喝无糖可乐，复习的时候会来一瓶",
  "memory_text_canonical": "喜欢喝无糖可乐",
  "memory_type": "preference",
  "polarity": "positive",
  "temporal_scope": "long_term",
  "confidence": 0.86,
  "extraction_source": "llm"
}
```

## viewer-yearly-017-extract-05

- Error Type: mismatch

**Content**

> 我家里还有个弟弟，今年刚上高三

**Expected**

```json
{
  "should_extract": true,
  "memory_text": "家里有个弟弟",
  "memory_type": "fact",
  "polarity": "neutral",
  "temporal_scope": "long_term"
}
```

**Actual**

```json
{
  "memory_text": "家里有个弟弟，刚上高三",
  "memory_text_raw": "我家里还有个弟弟，今年刚上高三",
  "memory_text_canonical": "家里有个弟弟，刚上高三",
  "memory_type": "fact",
  "polarity": "neutral",
  "temporal_scope": "long_term",
  "confidence": 0.74,
  "extraction_source": "llm"
}
```

## viewer-yearly-017-extract-06

- Error Type: mismatch

**Content**

> 我平时都骑电动车通勤，单程差不多四十分钟

**Expected**

```json
{
  "should_extract": true,
  "memory_text": "平时骑电动车通勤",
  "memory_type": "fact",
  "polarity": "neutral",
  "temporal_scope": "long_term"
}
```

**Actual**

```json
{
  "memory_text": "骑电动车通勤",
  "memory_text_raw": "我平时都骑电动车通勤，单程差不多四十分钟",
  "memory_text_canonical": "骑电动车通勤",
  "memory_type": "fact",
  "polarity": "neutral",
  "temporal_scope": "long_term",
  "confidence": 0.74,
  "extraction_source": "llm"
}
```

## viewer-yearly-017-extract-07

- Error Type: mismatch

**Content**

> 我一直都想去英国读传媒，申请学校还在准备

**Expected**

```json
{
  "should_extract": true,
  "memory_text": "一直都想去英国读传媒",
  "memory_type": "fact",
  "polarity": "neutral",
  "temporal_scope": "long_term"
}
```

**Actual**

```json
{
  "memory_text": "想去英国读传媒",
  "memory_text_raw": "我一直都想去英国读传媒，申请学校还在准备",
  "memory_text_canonical": "想去英国读传媒",
  "memory_type": "preference",
  "polarity": "positive",
  "temporal_scope": "long_term",
  "confidence": 0.86,
  "extraction_source": "llm"
}
```

## viewer-yearly-017-extract-08

- Error Type: mismatch

**Content**

> 这周我要连着上三天口语课，时间有点满

**Expected**

```json
{
  "should_extract": false,
  "memory_text": "",
  "memory_type": "context",
  "polarity": "neutral",
  "temporal_scope": "short_term"
}
```

**Actual**

```json
{
  "memory_text": "连着上三天口语课",
  "memory_text_raw": "这周我要连着上三天口语课，时间有点满",
  "memory_text_canonical": "连着上三天口语课",
  "memory_type": "fact",
  "polarity": "positive",
  "temporal_scope": "long_term",
  "confidence": 0.74,
  "extraction_source": "llm"
}
```

## viewer-yearly-017-extract-10

- Error Type: mismatch

**Content**

> 明天又要去上口语课，希望这次能顺一点

**Expected**

```json
{
  "should_extract": false,
  "memory_text": "",
  "memory_type": "context",
  "polarity": "neutral",
  "temporal_scope": "short_term"
}
```

**Actual**

```json
{
  "memory_text": "明天口语课",
  "memory_text_raw": "明天又要去上口语课，希望这次能顺一点",
  "memory_text_canonical": "明天口语课",
  "memory_type": "fact",
  "polarity": "positive",
  "temporal_scope": "long_term",
  "confidence": 0.74,
  "extraction_source": "llm"
}
```

## viewer-yearly-018-extract-01

- Error Type: mismatch

**Content**

> 我一直都在减脂，晚饭尽量不吃米饭和面

**Expected**

```json
{
  "should_extract": true,
  "memory_text": "一直都在减脂",
  "memory_type": "fact",
  "polarity": "neutral",
  "temporal_scope": "long_term"
}
```

**Actual**

```json
{
  "memory_text": "减脂，不吃米饭和面",
  "memory_text_raw": "我一直都在减脂，晚饭尽量不吃米饭和面",
  "memory_text_canonical": "减脂，不吃米饭和面",
  "memory_type": "preference",
  "polarity": "negative",
  "temporal_scope": "long_term",
  "confidence": 0.86,
  "extraction_source": "llm"
}
```

## viewer-yearly-018-extract-02

- Error Type: mismatch

**Content**

> 我平时都去公司附近那家健身房，器械还挺全

**Expected**

```json
{
  "should_extract": true,
  "memory_text": "平时去公司附近那家健身房",
  "memory_type": "context",
  "polarity": "neutral",
  "temporal_scope": "long_term"
}
```

**Actual**

```json
{
  "memory_text": "公司附近健身房",
  "memory_text_raw": "我平时都去公司附近那家健身房，器械还挺全",
  "memory_text_canonical": "公司附近健身房",
  "memory_type": "context",
  "polarity": "neutral",
  "temporal_scope": "long_term",
  "confidence": 0.78,
  "extraction_source": "llm"
}
```

## viewer-yearly-018-extract-03

- Error Type: mismatch

**Content**

> 我不能喝纯牛奶，乳糖不耐一喝就肚子疼

**Expected**

```json
{
  "should_extract": true,
  "memory_text": "不能喝纯牛奶",
  "memory_type": "preference",
  "polarity": "negative",
  "temporal_scope": "long_term"
}
```

**Actual**

```json
{
  "memory_text": "乳糖不耐受",
  "memory_text_raw": "我不能喝纯牛奶，乳糖不耐一喝就肚子疼",
  "memory_text_canonical": "乳糖不耐受",
  "memory_type": "fact",
  "polarity": "negative",
  "temporal_scope": "long_term",
  "confidence": 0.74,
  "extraction_source": "llm"
}
```

## viewer-yearly-018-extract-04

- Error Type: mismatch

**Content**

> 我一直都喜欢吃鸡胸和玉米，做饭也方便

**Expected**

```json
{
  "should_extract": true,
  "memory_text": "一直都喜欢吃鸡胸和玉米",
  "memory_type": "preference",
  "polarity": "positive",
  "temporal_scope": "long_term"
}
```

**Actual**

```json
{
  "memory_text": "喜欢吃鸡胸和玉米，做饭方便",
  "memory_text_raw": "我一直都喜欢吃鸡胸和玉米，做饭也方便",
  "memory_text_canonical": "喜欢吃鸡胸和玉米，做饭方便",
  "memory_type": "preference",
  "polarity": "positive",
  "temporal_scope": "long_term",
  "confidence": 0.86,
  "extraction_source": "llm"
}
```

## viewer-yearly-018-extract-06

- Error Type: mismatch

**Content**

> 我平时都习惯早上空腹称体重，看看有没有掉

**Expected**

```json
{
  "should_extract": true,
  "memory_text": "平时早上空腹称体重",
  "memory_type": "fact",
  "polarity": "neutral",
  "temporal_scope": "long_term"
}
```

**Actual**

```json
{
  "memory_text": "习惯空腹称体重",
  "memory_text_raw": "我平时都习惯早上空腹称体重，看看有没有掉",
  "memory_text_canonical": "习惯空腹称体重",
  "memory_type": "fact",
  "polarity": "neutral",
  "temporal_scope": "long_term",
  "confidence": 0.74,
  "extraction_source": "llm"
}
```

## viewer-yearly-018-extract-08

- Error Type: mismatch

**Content**

> 这周我准备冲一下半马配速，训练量会大一点

**Expected**

```json
{
  "should_extract": false,
  "memory_text": "",
  "memory_type": "context",
  "polarity": "neutral",
  "temporal_scope": "short_term"
}
```

**Actual**

```json
{
  "memory_text": "准备冲半马配速",
  "memory_text_raw": "这周我准备冲一下半马配速，训练量会大一点",
  "memory_text_canonical": "准备冲半马配速",
  "memory_type": "fact",
  "polarity": "positive",
  "temporal_scope": "long_term",
  "confidence": 0.74,
  "extraction_source": "llm"
}
```

## viewer-yearly-018-extract-09

- Error Type: mismatch

**Content**

> 我今天腿练完直接酸到楼梯都不想走

**Expected**

```json
{
  "should_extract": false,
  "memory_text": "",
  "memory_type": "context",
  "polarity": "neutral",
  "temporal_scope": "short_term"
}
```

**Actual**

```json
{
  "memory_text": "腿练后酸软",
  "memory_text_raw": "我今天腿练完直接酸到楼梯都不想走",
  "memory_text_canonical": "腿练后酸软",
  "memory_type": "fact",
  "polarity": "negative",
  "temporal_scope": "long_term",
  "confidence": 0.74,
  "extraction_source": "llm"
}
```

## viewer-yearly-018-extract-10

- Error Type: mismatch

**Content**

> 今晚练完准备去吃个轻食碗，别再放纵了

**Expected**

```json
{
  "should_extract": false,
  "memory_text": "",
  "memory_type": "context",
  "polarity": "neutral",
  "temporal_scope": "short_term"
}
```

**Actual**

```json
{
  "memory_text": "练完吃轻食碗",
  "memory_text_raw": "今晚练完准备去吃个轻食碗，别再放纵了",
  "memory_text_canonical": "练完吃轻食碗",
  "memory_type": "preference",
  "polarity": "positive",
  "temporal_scope": "long_term",
  "confidence": 0.86,
  "extraction_source": "llm"
}
```

## viewer-yearly-018-extract-12

- Error Type: mismatch

**Content**

> 明天想试试新的跑步计划

**Expected**

```json
{
  "should_extract": false,
  "memory_text": "",
  "memory_type": "context",
  "polarity": "neutral",
  "temporal_scope": "short_term"
}
```

**Actual**

```json
{
  "memory_text": "想尝试新的跑步计划",
  "memory_text_raw": "明天想试试新的跑步计划",
  "memory_text_canonical": "想尝试新的跑步计划",
  "memory_type": "preference",
  "polarity": "positive",
  "temporal_scope": "long_term",
  "confidence": 0.86,
  "extraction_source": "llm"
}
```

## viewer-yearly-019-extract-01

- Error Type: mismatch

**Content**

> 我做亚马逊跨境电商，最近一直在看广告数据

**Expected**

```json
{
  "should_extract": true,
  "memory_text": "做亚马逊跨境电商",
  "memory_type": "fact",
  "polarity": "neutral",
  "temporal_scope": "long_term"
}
```

**Actual**

```json
{}
```

## viewer-yearly-019-extract-02

- Error Type: mismatch

**Content**

> 我平时住在深圳，仓库也在这边

**Expected**

```json
{
  "should_extract": true,
  "memory_text": "平时住在深圳",
  "memory_type": "context",
  "polarity": "neutral",
  "temporal_scope": "long_term"
}
```

**Actual**

```json
{
  "memory_text": "住在深圳",
  "memory_text_raw": "我平时住在深圳，仓库也在这边",
  "memory_text_canonical": "住在深圳",
  "memory_type": "context",
  "polarity": "neutral",
  "temporal_scope": "long_term",
  "confidence": 0.78,
  "extraction_source": "llm"
}
```

## viewer-yearly-019-extract-03

- Error Type: mismatch

**Content**

> 我不喜欢一大早开会，脑子根本没开机

**Expected**

```json
{
  "should_extract": true,
  "memory_text": "不喜欢开早会",
  "memory_type": "preference",
  "polarity": "negative",
  "temporal_scope": "long_term"
}
```

**Actual**

```json
{
  "memory_text": "不喜欢开会",
  "memory_text_raw": "我不喜欢一大早开会，脑子根本没开机",
  "memory_text_canonical": "不喜欢开会",
  "memory_type": "preference",
  "polarity": "negative",
  "temporal_scope": "long_term",
  "confidence": 0.86,
  "extraction_source": "llm"
}
```

## viewer-yearly-019-extract-04

- Error Type: mismatch

**Content**

> 我一直都喜欢喝冰美式，特别是盯报表的时候

**Expected**

```json
{
  "should_extract": true,
  "memory_text": "一直都喜欢喝冰美式",
  "memory_type": "preference",
  "polarity": "positive",
  "temporal_scope": "long_term"
}
```

**Actual**

```json
{
  "memory_text": "喜欢冰美式",
  "memory_text_raw": "我一直都喜欢喝冰美式，特别是盯报表的时候",
  "memory_text_canonical": "喜欢冰美式",
  "memory_type": "preference",
  "polarity": "positive",
  "temporal_scope": "long_term",
  "confidence": 0.86,
  "extraction_source": "llm"
}
```

## viewer-yearly-019-extract-05

- Error Type: mismatch

**Content**

> 我经常熬夜看美国站数据，时差真难受

**Expected**

```json
{
  "should_extract": true,
  "memory_text": "经常熬夜看美国站数据",
  "memory_type": "fact",
  "polarity": "neutral",
  "temporal_scope": "long_term"
}
```

**Actual**

```json
{}
```

## viewer-yearly-019-extract-10

- Error Type: mismatch

**Content**

> 明天还得去仓库盘点库存

**Expected**

```json
{
  "should_extract": false,
  "memory_text": "",
  "memory_type": "context",
  "polarity": "neutral",
  "temporal_scope": "short_term"
}
```

**Actual**

```json
{
  "memory_text": "去仓库盘点库存",
  "memory_text_raw": "明天还得去仓库盘点库存",
  "memory_text_canonical": "去仓库盘点库存",
  "memory_type": "fact",
  "polarity": "neutral",
  "temporal_scope": "long_term",
  "confidence": 0.74,
  "extraction_source": "llm"
}
```

## viewer-yearly-020-extract-01

- Error Type: mismatch

**Content**

> 我刚当妈妈没多久，现在还在摸索节奏

**Expected**

```json
{
  "should_extract": true,
  "memory_text": "刚当妈妈",
  "memory_type": "fact",
  "polarity": "neutral",
  "temporal_scope": "long_term"
}
```

**Actual**

```json
{}
```

## viewer-yearly-020-extract-02

- Error Type: mismatch

**Content**

> 我平时住在南京，爸妈偶尔会来帮忙

**Expected**

```json
{
  "should_extract": true,
  "memory_text": "平时住在南京",
  "memory_type": "context",
  "polarity": "neutral",
  "temporal_scope": "long_term"
}
```

**Actual**

```json
{
  "memory_text": "住在南京，父母偶尔帮忙",
  "memory_text_raw": "我平时住在南京，爸妈偶尔会来帮忙",
  "memory_text_canonical": "住在南京，父母偶尔帮忙",
  "memory_type": "context",
  "polarity": "neutral",
  "temporal_scope": "long_term",
  "confidence": 0.78,
  "extraction_source": "llm"
}
```

## viewer-yearly-020-extract-03

- Error Type: mismatch

**Content**

> 我不喜欢香精味太重的护肤品，闻着头晕

**Expected**

```json
{
  "should_extract": true,
  "memory_text": "不喜欢香精味太重的护肤品",
  "memory_type": "preference",
  "polarity": "negative",
  "temporal_scope": "long_term"
}
```

**Actual**

```json
{
  "memory_text": "不喜欢香精味重的护肤品",
  "memory_text_raw": "我不喜欢香精味太重的护肤品，闻着头晕",
  "memory_text_canonical": "不喜欢香精味重的护肤品",
  "memory_type": "preference",
  "polarity": "negative",
  "temporal_scope": "long_term",
  "confidence": 0.86,
  "extraction_source": "llm"
}
```

## viewer-yearly-020-extract-04

- Error Type: mismatch

**Content**

> 我一直都喜欢喝温豆浆，早上比较舒服

**Expected**

```json
{
  "should_extract": true,
  "memory_text": "一直都喜欢喝温豆浆",
  "memory_type": "preference",
  "polarity": "positive",
  "temporal_scope": "long_term"
}
```

**Actual**

```json
{
  "memory_text": "喜欢喝温豆浆",
  "memory_text_raw": "我一直都喜欢喝温豆浆，早上比较舒服",
  "memory_text_canonical": "喜欢喝温豆浆",
  "memory_type": "preference",
  "polarity": "positive",
  "temporal_scope": "long_term",
  "confidence": 0.86,
  "extraction_source": "llm"
}
```

## viewer-yearly-020-extract-05

- Error Type: mismatch

**Content**

> 我晚上经常要起夜喂奶，睡眠一直断断续续

**Expected**

```json
{
  "should_extract": true,
  "memory_text": "晚上经常要起夜喂奶",
  "memory_type": "fact",
  "polarity": "neutral",
  "temporal_scope": "long_term"
}
```

**Actual**

```json
{}
```

## viewer-yearly-020-extract-07

- Error Type: mismatch

**Content**

> 我平时喜欢囤湿巾和纸尿裤，怕突然不够用

**Expected**

```json
{
  "should_extract": true,
  "memory_text": "平时喜欢囤湿巾和纸尿裤",
  "memory_type": "preference",
  "polarity": "positive",
  "temporal_scope": "long_term"
}
```

**Actual**

```json
{
  "memory_text": "喜欢囤湿巾和纸尿裤",
  "memory_text_raw": "我平时喜欢囤湿巾和纸尿裤，怕突然不够用",
  "memory_text_canonical": "喜欢囤湿巾和纸尿裤",
  "memory_type": "preference",
  "polarity": "positive",
  "temporal_scope": "long_term",
  "confidence": 0.86,
  "extraction_source": "llm"
}
```

## viewer-yearly-020-extract-10

- Error Type: mismatch

**Content**

> 明天要带宝宝去打疫苗

**Expected**

```json
{
  "should_extract": false,
  "memory_text": "",
  "memory_type": "context",
  "polarity": "neutral",
  "temporal_scope": "short_term"
}
```

**Actual**

```json
{
  "memory_text": "带宝宝去打疫苗",
  "memory_text_raw": "明天要带宝宝去打疫苗",
  "memory_text_canonical": "带宝宝去打疫苗",
  "memory_type": "fact",
  "polarity": "positive",
  "temporal_scope": "long_term",
  "confidence": 0.74,
  "extraction_source": "llm"
}
```

## viewer-yearly-021-extract-01

- Error Type: mismatch

**Content**

> 我在杭州做前端开发，最近项目一直在赶需求

**Expected**

```json
{
  "should_extract": true,
  "memory_text": "在杭州做前端开发",
  "memory_type": "context",
  "polarity": "neutral",
  "temporal_scope": "long_term"
}
```

**Actual**

```json
{
  "memory_text": "在杭州做前端开发，项目赶需求",
  "memory_text_raw": "我在杭州做前端开发，最近项目一直在赶需求",
  "memory_text_canonical": "在杭州做前端开发，项目赶需求",
  "memory_type": "fact",
  "polarity": "neutral",
  "temporal_scope": "long_term",
  "confidence": 0.74,
  "extraction_source": "llm"
}
```

## viewer-yearly-021-extract-02

- Error Type: mismatch

**Content**

> 我平时都要喝美式咖啡，不然下午根本顶不住

**Expected**

```json
{
  "should_extract": true,
  "memory_text": "平时都喝美式咖啡",
  "memory_type": "preference",
  "polarity": "positive",
  "temporal_scope": "long_term"
}
```

**Actual**

```json
{
  "memory_text": "平时喝美式咖啡",
  "memory_text_raw": "我平时都要喝美式咖啡，不然下午根本顶不住",
  "memory_text_canonical": "平时喝美式咖啡",
  "memory_type": "preference",
  "polarity": "positive",
  "temporal_scope": "long_term",
  "confidence": 0.86,
  "extraction_source": "llm"
}
```

## viewer-yearly-021-extract-03

- Error Type: mismatch

**Content**

> 我不太能吃辣，吃多了胃会不舒服

**Expected**

```json
{
  "should_extract": true,
  "memory_text": "不太能吃辣",
  "memory_type": "preference",
  "polarity": "negative",
  "temporal_scope": "long_term"
}
```

**Actual**

```json
{}
```

## viewer-yearly-021-extract-05

- Error Type: mismatch

**Content**

> 我家里养了两只猫，晚上回去还得铲屎

**Expected**

```json
{
  "should_extract": true,
  "memory_text": "家里养了两只猫",
  "memory_type": "fact",
  "polarity": "neutral",
  "temporal_scope": "long_term"
}
```

**Actual**

```json
{
  "memory_text": "养猫",
  "memory_text_raw": "我家里养了两只猫，晚上回去还得铲屎",
  "memory_text_canonical": "养猫",
  "memory_type": "fact",
  "polarity": "positive",
  "temporal_scope": "long_term",
  "confidence": 0.74,
  "extraction_source": "llm"
}
```

## viewer-yearly-021-extract-06

- Error Type: mismatch

**Content**

> 我一直都喜欢吃豚骨拉面，周末经常去那家店

**Expected**

```json
{
  "should_extract": true,
  "memory_text": "一直都喜欢吃豚骨拉面",
  "memory_type": "preference",
  "polarity": "positive",
  "temporal_scope": "long_term"
}
```

**Actual**

```json
{
  "memory_text": "喜欢吃豚骨拉面",
  "memory_text_raw": "我一直都喜欢吃豚骨拉面，周末经常去那家店",
  "memory_text_canonical": "喜欢吃豚骨拉面",
  "memory_type": "preference",
  "polarity": "positive",
  "temporal_scope": "long_term",
  "confidence": 0.86,
  "extraction_source": "llm"
}
```

## viewer-yearly-021-extract-07

- Error Type: mismatch

**Content**

> 我平时都是凌晨一点以后才睡，作息有点乱

**Expected**

```json
{
  "should_extract": true,
  "memory_text": "平时凌晨一点以后才睡",
  "memory_type": "fact",
  "polarity": "neutral",
  "temporal_scope": "long_term"
}
```

**Actual**

```json
{}
```

## viewer-yearly-021-extract-08

- Error Type: mismatch

**Content**

> 这周我准备连续夜跑，把作息拉回来

**Expected**

```json
{
  "should_extract": false,
  "memory_text": "",
  "memory_type": "context",
  "polarity": "neutral",
  "temporal_scope": "short_term"
}
```

**Actual**

```json
{
  "memory_text": "连续夜跑",
  "memory_text_raw": "这周我准备连续夜跑，把作息拉回来",
  "memory_text_canonical": "连续夜跑",
  "memory_type": "fact",
  "polarity": "positive",
  "temporal_scope": "long_term",
  "confidence": 0.74,
  "extraction_source": "llm"
}
```

## viewer-yearly-021-extract-10

- Error Type: mismatch

**Content**

> 今晚下班还想去吃面，最近就馋这口

**Expected**

```json
{
  "should_extract": false,
  "memory_text": "",
  "memory_type": "context",
  "polarity": "neutral",
  "temporal_scope": "short_term"
}
```

**Actual**

```json
{
  "memory_text": "下班想吃面",
  "memory_text_raw": "今晚下班还想去吃面，最近就馋这口",
  "memory_text_canonical": "下班想吃面",
  "memory_type": "preference",
  "polarity": "positive",
  "temporal_scope": "long_term",
  "confidence": 0.86,
  "extraction_source": "llm"
}
```

## viewer-yearly-022-extract-01

- Error Type: mismatch

**Content**

> 我最近在备考雅思，晚上下班后会背单词做听力

**Expected**

```json
{
  "should_extract": true,
  "memory_text": "最近在备考雅思",
  "memory_type": "fact",
  "polarity": "neutral",
  "temporal_scope": "long_term"
}
```

**Actual**

```json
{
  "memory_text": "备考雅思，晚上下班后背单词",
  "memory_text_raw": "我最近在备考雅思，晚上下班后会背单词做听力",
  "memory_text_canonical": "备考雅思，晚上下班后背单词",
  "memory_type": "fact",
  "polarity": "positive",
  "temporal_scope": "long_term",
  "confidence": 0.74,
  "extraction_source": "llm"
}
```

## viewer-yearly-022-extract-02

- Error Type: mismatch

**Content**

> 我平时都住在苏州，公司在园区那边

**Expected**

```json
{
  "should_extract": true,
  "memory_text": "平时住在苏州",
  "memory_type": "context",
  "polarity": "neutral",
  "temporal_scope": "long_term"
}
```

**Actual**

```json
{
  "memory_text": "住在苏州，公司位置",
  "memory_text_raw": "我平时都住在苏州，公司在园区那边",
  "memory_text_canonical": "住在苏州，公司位置",
  "memory_type": "context",
  "polarity": "neutral",
  "temporal_scope": "long_term",
  "confidence": 0.78,
  "extraction_source": "llm"
}
```

## viewer-yearly-022-extract-04

- Error Type: mismatch

**Content**

> 我一直都喜欢喝无糖可乐，复习的时候会来一瓶

**Expected**

```json
{
  "should_extract": true,
  "memory_text": "一直都喜欢喝无糖可乐",
  "memory_type": "preference",
  "polarity": "positive",
  "temporal_scope": "long_term"
}
```

**Actual**

```json
{
  "memory_text": "喜欢喝无糖可乐",
  "memory_text_raw": "我一直都喜欢喝无糖可乐，复习的时候会来一瓶",
  "memory_text_canonical": "喜欢喝无糖可乐",
  "memory_type": "preference",
  "polarity": "positive",
  "temporal_scope": "long_term",
  "confidence": 0.86,
  "extraction_source": "llm"
}
```

## viewer-yearly-022-extract-05

- Error Type: mismatch

**Content**

> 我家里还有个弟弟，今年刚上高三

**Expected**

```json
{
  "should_extract": true,
  "memory_text": "家里有个弟弟",
  "memory_type": "fact",
  "polarity": "neutral",
  "temporal_scope": "long_term"
}
```

**Actual**

```json
{
  "memory_text": "家里有个弟弟，刚上高三",
  "memory_text_raw": "我家里还有个弟弟，今年刚上高三",
  "memory_text_canonical": "家里有个弟弟，刚上高三",
  "memory_type": "fact",
  "polarity": "neutral",
  "temporal_scope": "long_term",
  "confidence": 0.74,
  "extraction_source": "llm"
}
```

## viewer-yearly-022-extract-06

- Error Type: mismatch

**Content**

> 我平时都骑电动车通勤，单程差不多四十分钟

**Expected**

```json
{
  "should_extract": true,
  "memory_text": "平时骑电动车通勤",
  "memory_type": "fact",
  "polarity": "neutral",
  "temporal_scope": "long_term"
}
```

**Actual**

```json
{
  "memory_text": "骑电动车通勤",
  "memory_text_raw": "我平时都骑电动车通勤，单程差不多四十分钟",
  "memory_text_canonical": "骑电动车通勤",
  "memory_type": "fact",
  "polarity": "neutral",
  "temporal_scope": "long_term",
  "confidence": 0.74,
  "extraction_source": "llm"
}
```

## viewer-yearly-022-extract-07

- Error Type: mismatch

**Content**

> 我一直都想去英国读传媒，申请学校还在准备

**Expected**

```json
{
  "should_extract": true,
  "memory_text": "一直都想去英国读传媒",
  "memory_type": "fact",
  "polarity": "neutral",
  "temporal_scope": "long_term"
}
```

**Actual**

```json
{
  "memory_text": "想去英国读传媒",
  "memory_text_raw": "我一直都想去英国读传媒，申请学校还在准备",
  "memory_text_canonical": "想去英国读传媒",
  "memory_type": "preference",
  "polarity": "positive",
  "temporal_scope": "long_term",
  "confidence": 0.86,
  "extraction_source": "llm"
}
```

## viewer-yearly-022-extract-08

- Error Type: mismatch

**Content**

> 这周我要连着上三天口语课，时间有点满

**Expected**

```json
{
  "should_extract": false,
  "memory_text": "",
  "memory_type": "context",
  "polarity": "neutral",
  "temporal_scope": "short_term"
}
```

**Actual**

```json
{
  "memory_text": "连着上三天口语课",
  "memory_text_raw": "这周我要连着上三天口语课，时间有点满",
  "memory_text_canonical": "连着上三天口语课",
  "memory_type": "fact",
  "polarity": "positive",
  "temporal_scope": "long_term",
  "confidence": 0.74,
  "extraction_source": "llm"
}
```

## viewer-yearly-022-extract-10

- Error Type: mismatch

**Content**

> 明天又要去上口语课，希望这次能顺一点

**Expected**

```json
{
  "should_extract": false,
  "memory_text": "",
  "memory_type": "context",
  "polarity": "neutral",
  "temporal_scope": "short_term"
}
```

**Actual**

```json
{
  "memory_text": "明天口语课",
  "memory_text_raw": "明天又要去上口语课，希望这次能顺一点",
  "memory_text_canonical": "明天口语课",
  "memory_type": "fact",
  "polarity": "positive",
  "temporal_scope": "long_term",
  "confidence": 0.74,
  "extraction_source": "llm"
}
```

## viewer-yearly-023-extract-01

- Error Type: mismatch

**Content**

> 我一直都在减脂，晚饭尽量不吃米饭和面

**Expected**

```json
{
  "should_extract": true,
  "memory_text": "一直都在减脂",
  "memory_type": "fact",
  "polarity": "neutral",
  "temporal_scope": "long_term"
}
```

**Actual**

```json
{
  "memory_text": "减脂，不吃米饭和面",
  "memory_text_raw": "我一直都在减脂，晚饭尽量不吃米饭和面",
  "memory_text_canonical": "减脂，不吃米饭和面",
  "memory_type": "preference",
  "polarity": "negative",
  "temporal_scope": "long_term",
  "confidence": 0.86,
  "extraction_source": "llm"
}
```

## viewer-yearly-023-extract-02

- Error Type: mismatch

**Content**

> 我平时都去公司附近那家健身房，器械还挺全

**Expected**

```json
{
  "should_extract": true,
  "memory_text": "平时去公司附近那家健身房",
  "memory_type": "context",
  "polarity": "neutral",
  "temporal_scope": "long_term"
}
```

**Actual**

```json
{
  "memory_text": "公司附近健身房",
  "memory_text_raw": "我平时都去公司附近那家健身房，器械还挺全",
  "memory_text_canonical": "公司附近健身房",
  "memory_type": "context",
  "polarity": "neutral",
  "temporal_scope": "long_term",
  "confidence": 0.78,
  "extraction_source": "llm"
}
```

## viewer-yearly-023-extract-03

- Error Type: mismatch

**Content**

> 我不能喝纯牛奶，乳糖不耐一喝就肚子疼

**Expected**

```json
{
  "should_extract": true,
  "memory_text": "不能喝纯牛奶",
  "memory_type": "preference",
  "polarity": "negative",
  "temporal_scope": "long_term"
}
```

**Actual**

```json
{
  "memory_text": "乳糖不耐受",
  "memory_text_raw": "我不能喝纯牛奶，乳糖不耐一喝就肚子疼",
  "memory_text_canonical": "乳糖不耐受",
  "memory_type": "fact",
  "polarity": "negative",
  "temporal_scope": "long_term",
  "confidence": 0.74,
  "extraction_source": "llm"
}
```

## viewer-yearly-023-extract-04

- Error Type: mismatch

**Content**

> 我一直都喜欢吃鸡胸和玉米，做饭也方便

**Expected**

```json
{
  "should_extract": true,
  "memory_text": "一直都喜欢吃鸡胸和玉米",
  "memory_type": "preference",
  "polarity": "positive",
  "temporal_scope": "long_term"
}
```

**Actual**

```json
{
  "memory_text": "喜欢吃鸡胸和玉米，做饭方便",
  "memory_text_raw": "我一直都喜欢吃鸡胸和玉米，做饭也方便",
  "memory_text_canonical": "喜欢吃鸡胸和玉米，做饭方便",
  "memory_type": "preference",
  "polarity": "positive",
  "temporal_scope": "long_term",
  "confidence": 0.86,
  "extraction_source": "llm"
}
```

## viewer-yearly-023-extract-06

- Error Type: mismatch

**Content**

> 我平时都习惯早上空腹称体重，看看有没有掉

**Expected**

```json
{
  "should_extract": true,
  "memory_text": "平时早上空腹称体重",
  "memory_type": "fact",
  "polarity": "neutral",
  "temporal_scope": "long_term"
}
```

**Actual**

```json
{
  "memory_text": "习惯空腹称体重",
  "memory_text_raw": "我平时都习惯早上空腹称体重，看看有没有掉",
  "memory_text_canonical": "习惯空腹称体重",
  "memory_type": "fact",
  "polarity": "neutral",
  "temporal_scope": "long_term",
  "confidence": 0.74,
  "extraction_source": "llm"
}
```

## viewer-yearly-023-extract-08

- Error Type: mismatch

**Content**

> 这周我准备冲一下半马配速，训练量会大一点

**Expected**

```json
{
  "should_extract": false,
  "memory_text": "",
  "memory_type": "context",
  "polarity": "neutral",
  "temporal_scope": "short_term"
}
```

**Actual**

```json
{
  "memory_text": "准备冲半马配速",
  "memory_text_raw": "这周我准备冲一下半马配速，训练量会大一点",
  "memory_text_canonical": "准备冲半马配速",
  "memory_type": "fact",
  "polarity": "positive",
  "temporal_scope": "long_term",
  "confidence": 0.74,
  "extraction_source": "llm"
}
```

## viewer-yearly-023-extract-09

- Error Type: mismatch

**Content**

> 我今天腿练完直接酸到楼梯都不想走

**Expected**

```json
{
  "should_extract": false,
  "memory_text": "",
  "memory_type": "context",
  "polarity": "neutral",
  "temporal_scope": "short_term"
}
```

**Actual**

```json
{
  "memory_text": "腿练后酸软",
  "memory_text_raw": "我今天腿练完直接酸到楼梯都不想走",
  "memory_text_canonical": "腿练后酸软",
  "memory_type": "fact",
  "polarity": "negative",
  "temporal_scope": "long_term",
  "confidence": 0.74,
  "extraction_source": "llm"
}
```

## viewer-yearly-023-extract-10

- Error Type: mismatch

**Content**

> 今晚练完准备去吃个轻食碗，别再放纵了

**Expected**

```json
{
  "should_extract": false,
  "memory_text": "",
  "memory_type": "context",
  "polarity": "neutral",
  "temporal_scope": "short_term"
}
```

**Actual**

```json
{
  "memory_text": "练完准备吃轻食碗",
  "memory_text_raw": "今晚练完准备去吃个轻食碗，别再放纵了",
  "memory_text_canonical": "练完准备吃轻食碗",
  "memory_type": "preference",
  "polarity": "positive",
  "temporal_scope": "long_term",
  "confidence": 0.86,
  "extraction_source": "llm"
}
```

## viewer-yearly-023-extract-12

- Error Type: mismatch

**Content**

> 明天想试试新的跑步计划

**Expected**

```json
{
  "should_extract": false,
  "memory_text": "",
  "memory_type": "context",
  "polarity": "neutral",
  "temporal_scope": "short_term"
}
```

**Actual**

```json
{
  "memory_text": "想试试新的跑步计划",
  "memory_text_raw": "明天想试试新的跑步计划",
  "memory_text_canonical": "想试试新的跑步计划",
  "memory_type": "preference",
  "polarity": "positive",
  "temporal_scope": "long_term",
  "confidence": 0.86,
  "extraction_source": "llm"
}
```

## viewer-yearly-024-extract-01

- Error Type: mismatch

**Content**

> 我做亚马逊跨境电商，最近一直在看广告数据

**Expected**

```json
{
  "should_extract": true,
  "memory_text": "做亚马逊跨境电商",
  "memory_type": "fact",
  "polarity": "neutral",
  "temporal_scope": "long_term"
}
```

**Actual**

```json
{}
```

## viewer-yearly-024-extract-02

- Error Type: mismatch

**Content**

> 我平时住在深圳，仓库也在这边

**Expected**

```json
{
  "should_extract": true,
  "memory_text": "平时住在深圳",
  "memory_type": "context",
  "polarity": "neutral",
  "temporal_scope": "long_term"
}
```

**Actual**

```json
{
  "memory_text": "住在深圳",
  "memory_text_raw": "我平时住在深圳，仓库也在这边",
  "memory_text_canonical": "住在深圳",
  "memory_type": "context",
  "polarity": "neutral",
  "temporal_scope": "long_term",
  "confidence": 0.78,
  "extraction_source": "llm"
}
```

## viewer-yearly-024-extract-03

- Error Type: mismatch

**Content**

> 我不喜欢一大早开会，脑子根本没开机

**Expected**

```json
{
  "should_extract": true,
  "memory_text": "不喜欢开早会",
  "memory_type": "preference",
  "polarity": "negative",
  "temporal_scope": "long_term"
}
```

**Actual**

```json
{
  "memory_text": "不喜欢开会",
  "memory_text_raw": "我不喜欢一大早开会，脑子根本没开机",
  "memory_text_canonical": "不喜欢开会",
  "memory_type": "preference",
  "polarity": "negative",
  "temporal_scope": "long_term",
  "confidence": 0.86,
  "extraction_source": "llm"
}
```

## viewer-yearly-024-extract-04

- Error Type: mismatch

**Content**

> 我一直都喜欢喝冰美式，特别是盯报表的时候

**Expected**

```json
{
  "should_extract": true,
  "memory_text": "一直都喜欢喝冰美式",
  "memory_type": "preference",
  "polarity": "positive",
  "temporal_scope": "long_term"
}
```

**Actual**

```json
{
  "memory_text": "喜欢冰美式",
  "memory_text_raw": "我一直都喜欢喝冰美式，特别是盯报表的时候",
  "memory_text_canonical": "喜欢冰美式",
  "memory_type": "preference",
  "polarity": "positive",
  "temporal_scope": "long_term",
  "confidence": 0.86,
  "extraction_source": "llm"
}
```

## viewer-yearly-024-extract-05

- Error Type: mismatch

**Content**

> 我经常熬夜看美国站数据，时差真难受

**Expected**

```json
{
  "should_extract": true,
  "memory_text": "经常熬夜看美国站数据",
  "memory_type": "fact",
  "polarity": "neutral",
  "temporal_scope": "long_term"
}
```

**Actual**

```json
{}
```

## viewer-yearly-024-extract-10

- Error Type: mismatch

**Content**

> 明天还得去仓库盘点库存

**Expected**

```json
{
  "should_extract": false,
  "memory_text": "",
  "memory_type": "context",
  "polarity": "neutral",
  "temporal_scope": "short_term"
}
```

**Actual**

```json
{
  "memory_text": "去仓库盘点库存",
  "memory_text_raw": "明天还得去仓库盘点库存",
  "memory_text_canonical": "去仓库盘点库存",
  "memory_type": "fact",
  "polarity": "neutral",
  "temporal_scope": "long_term",
  "confidence": 0.74,
  "extraction_source": "llm"
}
```
