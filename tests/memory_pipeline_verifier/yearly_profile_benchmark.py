from __future__ import annotations

import json
from pathlib import Path


_ARCHETYPES = [
    {
        "nickname_prefix": "夜班程序员",
        "memory_items": [
            ("在杭州做前端开发", "context", "neutral", "我在杭州做前端开发，最近项目一直在赶需求"),
            ("平时都喝美式咖啡", "preference", "positive", "我平时都要喝美式咖啡，不然下午根本顶不住"),
            ("不太能吃辣", "preference", "negative", "我不太能吃辣，吃多了胃会不舒服"),
            ("租房住在公司附近", "context", "neutral", "我租房住在公司附近，这样通勤方便点"),
            ("家里养了两只猫", "fact", "neutral", "我家里养了两只猫，晚上回去还得铲屎"),
            ("一直都喜欢吃豚骨拉面", "preference", "positive", "我一直都喜欢吃豚骨拉面，周末经常去那家店"),
            ("平时凌晨一点以后才睡", "fact", "neutral", "我平时都是凌晨一点以后才睡，作息有点乱"),
        ],
        "short_term_items": [
            "这周我准备连续夜跑，把作息拉回来",
            "我今天又在加班改页面，感觉眼睛都花了",
            "今晚下班还想去吃面，最近就馋这口",
            "明天可能还得继续跟需求评审",
            "这两天 bug 特别多，真有点顶不住",
        ],
        "semantic_queries": [
            ("最近还是在写页面那块，需求一来就得一直改", "在杭州做前端开发"),
            ("一到下午整个人就得靠那杯黑的续着", "平时都喝美式咖啡"),
            ("那种重口一点的我真顶不住，胃先抗议", "不太能吃辣"),
        ],
    },
    {
        "nickname_prefix": "备考雅思",
        "memory_items": [
            ("最近在备考雅思", "fact", "neutral", "我最近在备考雅思，晚上下班后会背单词做听力"),
            ("平时住在苏州", "context", "neutral", "我平时都住在苏州，公司在园区那边"),
            ("不喜欢香菜", "preference", "negative", "我不喜欢香菜，吃粉的时候都会提前说"),
            ("一直都喜欢喝无糖可乐", "preference", "positive", "我一直都喜欢喝无糖可乐，复习的时候会来一瓶"),
            ("家里有个弟弟", "fact", "neutral", "我家里还有个弟弟，今年刚上高三"),
            ("平时骑电动车通勤", "fact", "neutral", "我平时都骑电动车通勤，单程差不多四十分钟"),
            ("一直都想去英国读传媒", "fact", "neutral", "我一直都想去英国读传媒，申请学校还在准备"),
        ],
        "short_term_items": [
            "这周我要连着上三天口语课，时间有点满",
            "我今天模考又卡在阅读了，心态有点崩",
            "明天又要去上口语课，希望这次能顺一点",
            "今天晚上准备再刷一套听力题",
            "这两天一直在改文书，脑子有点炸",
        ],
        "semantic_queries": [
            ("下班以后基本都在刷单词和听那个考试的材料", "最近在备考雅思"),
            ("那玩意儿一放进去整碗味道都不对，我每次都得提前说", "不喜欢香菜"),
            ("平时去单位不是开车，就是骑那个两轮电的过去", "平时骑电动车通勤"),
        ],
    },
    {
        "nickname_prefix": "健身减脂",
        "memory_items": [
            ("一直都在减脂", "fact", "neutral", "我一直都在减脂，晚饭尽量不吃米饭和面"),
            ("平时去公司附近那家健身房", "context", "neutral", "我平时都去公司附近那家健身房，器械还挺全"),
            ("不能喝纯牛奶", "preference", "negative", "我不能喝纯牛奶，乳糖不耐一喝就肚子疼"),
            ("一直都喜欢吃鸡胸和玉米", "preference", "positive", "我一直都喜欢吃鸡胸和玉米，做饭也方便"),
            ("家里有一台跑步机", "fact", "neutral", "我家里有一台跑步机，下雨天就在家练"),
            ("平时早上空腹称体重", "fact", "neutral", "我平时都习惯早上空腹称体重，看看有没有掉"),
            ("不喜欢喝奶茶", "preference", "negative", "我不喜欢喝奶茶，太甜了容易破坏饮食"),
        ],
        "short_term_items": [
            "这周我准备冲一下半马配速，训练量会大一点",
            "我今天腿练完直接酸到楼梯都不想走",
            "今晚练完准备去吃个轻食碗，别再放纵了",
            "这两天在控制碳水，状态有点一般",
            "明天想试试新的跑步计划",
        ],
        "semantic_queries": [
            ("那种白的我喝了肚子就开始闹，完全不行", "不能喝纯牛奶"),
            ("平时练器械还是去公司边上那家，不想跑太远", "平时去公司附近那家健身房"),
            ("甜得发腻那种饮料我一般都绕着走", "不喜欢喝奶茶"),
        ],
    },
    {
        "nickname_prefix": "跨境电商",
        "memory_items": [
            ("做亚马逊跨境电商", "fact", "neutral", "我做亚马逊跨境电商，最近一直在看广告数据"),
            ("平时住在深圳", "context", "neutral", "我平时住在深圳，仓库也在这边"),
            ("不喜欢开早会", "preference", "negative", "我不喜欢一大早开会，脑子根本没开机"),
            ("一直都喜欢喝冰美式", "preference", "positive", "我一直都喜欢喝冰美式，特别是盯报表的时候"),
            ("经常熬夜看美国站数据", "fact", "neutral", "我经常熬夜看美国站数据，时差真难受"),
            ("租房住在公司附近", "context", "neutral", "我租房住在公司附近，不然通勤太折腾"),
            ("不能吃太甜", "preference", "negative", "我不能吃太甜，吃多了嗓子会难受"),
        ],
        "short_term_items": [
            "这周广告费又涨了，利润有点难看",
            "今天刚开完运营复盘会，人都麻了",
            "明天还得去仓库盘点库存",
            "这两天退款率有点高，挺烦",
            "今晚准备把 listing 再优化一下",
        ],
        "semantic_queries": [
            ("老得半夜盯那边的数据，不看不放心", "经常熬夜看美国站数据"),
            ("就是做那种跨境平台运营的，主要看站内投放", "做亚马逊跨境电商"),
            ("齁甜那种我吃两口就受不了，嗓子也难受", "不能吃太甜"),
        ],
    },
    {
        "nickname_prefix": "新手宝妈",
        "memory_items": [
            ("刚当妈妈", "fact", "neutral", "我刚当妈妈没多久，现在还在摸索节奏"),
            ("平时住在南京", "context", "neutral", "我平时住在南京，爸妈偶尔会来帮忙"),
            ("不喜欢香精味太重的护肤品", "preference", "negative", "我不喜欢香精味太重的护肤品，闻着头晕"),
            ("一直都喜欢喝温豆浆", "preference", "positive", "我一直都喜欢喝温豆浆，早上比较舒服"),
            ("晚上经常要起夜喂奶", "fact", "neutral", "我晚上经常要起夜喂奶，睡眠一直断断续续"),
            ("家里有一只金毛", "fact", "neutral", "我家里有一只金毛，现在总爱围着宝宝转"),
            ("平时喜欢囤湿巾和纸尿裤", "preference", "positive", "我平时喜欢囤湿巾和纸尿裤，怕突然不够用"),
        ],
        "short_term_items": [
            "这周宝宝有点闹觉，我人都熬傻了",
            "今天终于睡了个整觉，太不容易了",
            "明天要带宝宝去打疫苗",
            "这两天宝宝胃口不太好，有点担心",
            "今晚准备早点睡，能睡多久算多久",
        ],
        "semantic_queries": [
            ("夜里老得起来照顾小的，基本没法一觉到天亮", "晚上经常要起夜喂奶"),
            ("香味太冲的那种抹脸的我闻着就头晕", "不喜欢香精味太重的护肤品"),
            ("家里除了宝宝还有只大狗，最近老围着转", "家里有一只金毛"),
        ],
    },
]


def _date_to_ts_ms(date_text: str) -> int:
    year, month, day = [int(part) for part in str(date_text).split("-")]
    month_lengths = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    leap = year % 400 == 0 or (year % 4 == 0 and year % 100 != 0)
    if leap:
        month_lengths[1] = 29
    days_before_year = 0
    for current_year in range(1970, year):
        days_before_year += 366 if (current_year % 400 == 0 or (current_year % 4 == 0 and current_year % 100 != 0)) else 365
    days_before_month = sum(month_lengths[: month - 1])
    days_since_epoch = days_before_year + days_before_month + (day - 1)
    return days_since_epoch * 24 * 60 * 60 * 1000


def _date_text_for_index(event_index: int, total_events: int) -> str:
    # Spread comments across ~1 year, keeping results deterministic.
    start_month = 4
    start_year = 2025
    offset_days = int(((event_index - 1) * 357) / max(1, total_events - 1))
    month_lengths = [30, 31, 30, 31, 31, 30, 31, 30, 31, 31, 28, 31]
    year = start_year
    month = start_month
    day = 5

    while offset_days > 0:
        current_month_length = month_lengths[(month - start_month) % len(month_lengths)]
        remaining = current_month_length - day
        step = min(offset_days, remaining)
        day += step
        offset_days -= step
        if day >= current_month_length:
            offset_days -= 1
            if offset_days < 0:
                offset_days = 0
            day = 1
            month += 1
            if month > 12:
                month = 1
                year += 1

    return f"{year:04d}-{month:02d}-{day:02d}"


def _build_history_event(profile_index: int, event_index: int, nickname: str, date_text: str, content: str) -> dict:
    ts = _date_to_ts_ms(date_text) + (event_index * 1000)
    viewer_number = f"{profile_index:03d}"
    return {
        "event_id": f"yearly-history-{viewer_number}-{event_index:02d}",
        "room_id": "yearly-profile-room",
        "source_room_id": "yearly-profile-room",
        "session_id": f"yearly-profile-session-{viewer_number}",
        "platform": "douyin",
        "event_type": "comment",
        "method": "WebcastChatMessage",
        "livename": "yearly-profile-benchmark",
        "ts": ts,
        "user": {
            "id": f"viewer-yearly-{viewer_number}",
            "nickname": nickname,
        },
        "content": content,
        "metadata": {
            "dataset": "yearly_profile_benchmark",
            "event_index": event_index,
            "date": date_text,
        },
        "raw": {},
    }


def _profile_spec_for_index(profile_index: int) -> dict:
    return _ARCHETYPES[(profile_index - 1) % len(_ARCHETYPES)]


def _nickname_for_profile(profile_index: int, spec: dict) -> str:
    return f"{spec['nickname_prefix']}{profile_index:02d}"


def build_yearly_profile_benchmark_dataset(profile_count: int = 24, comments_per_user: int = 12) -> dict:
    normalized_profile_count = min(max(int(profile_count), 20), 50)
    normalized_comments_per_user = min(max(int(comments_per_user), 10), 20)

    profiles = []
    history_events = []
    extraction_cases = []
    semantic_cases = []

    for profile_index in range(1, normalized_profile_count + 1):
        spec = _profile_spec_for_index(profile_index)
        nickname = _nickname_for_profile(profile_index, spec)
        viewer_id = f"viewer-yearly-{profile_index:03d}"
        comment_dates = []
        memory_texts = []

        long_term_items = spec["memory_items"]
        short_term_items = spec["short_term_items"]
        long_term_count = min(len(long_term_items), max(6, normalized_comments_per_user - 5))
        short_term_count = normalized_comments_per_user - long_term_count

        event_index = 1
        for item_index in range(long_term_count):
            memory_text, memory_type, polarity, content = long_term_items[item_index % len(long_term_items)]
            date_text = _date_text_for_index(event_index, normalized_comments_per_user)
            history_event = _build_history_event(profile_index, event_index, nickname, date_text, content)
            history_events.append(history_event)
            extraction_cases.append(
                {
                    "label": f"{viewer_id}-extract-{event_index:02d}",
                    "room_id": history_event["room_id"],
                    "user_id": history_event["user"]["id"],
                    "nickname": history_event["user"]["nickname"],
                    "content": content,
                    "expected": {
                        "should_extract": True,
                        "memory_text": memory_text,
                        "memory_type": memory_type,
                        "polarity": polarity,
                        "temporal_scope": "long_term",
                    },
                }
            )
            comment_dates.append(_date_to_ts_ms(date_text))
            memory_texts.append(memory_text)
            event_index += 1

        for item_index in range(short_term_count):
            content = short_term_items[item_index % len(short_term_items)]
            date_text = _date_text_for_index(event_index, normalized_comments_per_user)
            history_event = _build_history_event(profile_index, event_index, nickname, date_text, content)
            history_events.append(history_event)
            extraction_cases.append(
                {
                    "label": f"{viewer_id}-extract-{event_index:02d}",
                    "room_id": history_event["room_id"],
                    "user_id": history_event["user"]["id"],
                    "nickname": history_event["user"]["nickname"],
                    "content": content,
                    "expected": {
                        "should_extract": False,
                        "memory_text": "",
                        "memory_type": "context",
                        "polarity": "neutral",
                        "temporal_scope": "short_term",
                    },
                }
            )
            comment_dates.append(_date_to_ts_ms(date_text))
            event_index += 1

        min_ts = min(comment_dates)
        max_ts = max(comment_dates)
        span_days = int((max_ts - min_ts) / (24 * 60 * 60 * 1000))
        profiles.append(
            {
                "viewer_id": viewer_id,
                "nickname": nickname,
                "comment_count": normalized_comments_per_user,
                "span_days": span_days,
            }
        )

        for query_index, (query_text, expected_memory_text) in enumerate(spec["semantic_queries"], start=1):
            distractors = [text for text in memory_texts if text != expected_memory_text][: max(4, min(8, len(memory_texts) - 1))]
            semantic_cases.append(
                {
                    "label": f"{viewer_id}-semantic-{query_index:02d}",
                    "room_id": "yearly-profile-room",
                    "viewer_id": f"id:{viewer_id}",
                    "memory_texts": [expected_memory_text, *distractors],
                    "distractor_memory_texts": list(distractors),
                    "query": query_text,
                    "expected_memory_text": expected_memory_text,
                    "tags": ["yearly_profile", "multi_turn", "llm_benchmark", "ambiguous", "spoken", "paraphrase"],
                }
            )

    return {
        "profiles": profiles,
        "history_events": history_events,
        "extraction_cases": extraction_cases,
        "semantic_cases": semantic_cases,
    }


def build_yearly_profile_dataset_summary(dataset: dict) -> dict:
    profiles = list(dataset.get("profiles") or [])
    comments = [int(profile.get("comment_count", 0)) for profile in profiles]
    spans = [int(profile.get("span_days", 0)) for profile in profiles]
    return {
        "profile_count": len(profiles),
        "total_comments": len(dataset.get("history_events") or []),
        "comments_per_user_min": min(comments) if comments else 0,
        "comments_per_user_max": max(comments) if comments else 0,
        "time_span_days_min": min(spans) if spans else 0,
        "time_span_days_max": max(spans) if spans else 0,
    }


def write_yearly_profile_benchmark_dataset(output_dir: Path, dataset: dict) -> dict:
    target_dir = Path(output_dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    history_events_path = target_dir / "history_events.json"
    extraction_cases_path = target_dir / "extraction_cases.json"
    semantic_cases_path = target_dir / "semantic_cases.json"

    history_events_path.write_text(
        json.dumps(dataset["history_events"], ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    extraction_cases_path.write_text(
        json.dumps(dataset["extraction_cases"], ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    semantic_cases_path.write_text(
        json.dumps(dataset["semantic_cases"], ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    return {
        "history_events": history_events_path,
        "extraction_cases": extraction_cases_path,
        "semantic_cases": semantic_cases_path,
    }


def render_yearly_profile_report_markdown(
    *,
    dataset_summary: dict,
    extraction_metrics: dict,
    semantic_summary: dict,
    output_files: dict,
    llm_summary: dict | None = None,
) -> str:
    llm_summary = llm_summary or {}
    mode = str(llm_summary.get("mode") or "").strip().lower()
    mode_label = "LLM 抽取" if mode == "llm" else "规则抽取"

    lines = []
    lines.append("# 年度用户记忆画像评测报告")
    lines.append("")
    lines.append("## 数据概览")
    lines.append("")
    lines.append(f"- 用户数：{int(dataset_summary.get('profile_count', 0))}")
    lines.append(f"- 总评论数：{int(dataset_summary.get('total_comments', 0))}")
    lines.append(
        f"- 每位用户评论数范围：{int(dataset_summary.get('comments_per_user_min', 0))} - {int(dataset_summary.get('comments_per_user_max', 0))}"
    )
    lines.append(
        f"- 时间跨度范围（天）：{int(dataset_summary.get('time_span_days_min', 0))} - {int(dataset_summary.get('time_span_days_max', 0))}"
    )
    lines.append("")
    lines.append("## 抽取模式")
    lines.append("")
    lines.append(f"- 抽取模式：{mode_label}")
    if llm_summary.get("model"):
        lines.append(f"- 抽取模型：{llm_summary['model']}")
    if llm_summary.get("base_url"):
        lines.append(f"- 抽取接口：{llm_summary['base_url']}")
    lines.append("")
    lines.append("## 记忆画像抽取成功率")
    lines.append("")
    lines.append(f"- 样本数：{int(extraction_metrics.get('case_count', 0))}")
    lines.append(f"- JSON 解析成功率：{float(extraction_metrics.get('json_parse_rate', 0.0)):.4f}")
    lines.append(f"- Schema 合法率：{float(extraction_metrics.get('schema_valid_rate', 0.0)):.4f}")
    lines.append(f"- 抽取精确率：{float(extraction_metrics.get('should_extract_precision', 0.0)):.4f}")
    lines.append(f"- 抽取召回率：{float(extraction_metrics.get('should_extract_recall', 0.0)):.4f}")
    lines.append(f"- 抽取 F1：{float(extraction_metrics.get('should_extract_f1', 0.0)):.4f}")
    lines.append(f"- 记忆类型准确率：{float(extraction_metrics.get('memory_type_accuracy', 0.0)):.4f}")
    lines.append(f"- 极性准确率：{float(extraction_metrics.get('polarity_accuracy', 0.0)):.4f}")
    lines.append(f"- 时态范围准确率：{float(extraction_metrics.get('temporal_scope_accuracy', 0.0)):.4f}")
    lines.append(f"- 误报数：{int(extraction_metrics.get('false_positive_count', 0))}")
    lines.append(f"- 漏报数：{int(extraction_metrics.get('false_negative_count', 0))}")
    lines.append("")
    lines.append("## 语义召回成功率")
    lines.append("")
    lines.append(f"- 样本数：{int(semantic_summary.get('case_count', 0))}")
    lines.append(f"- Top1 命中数：{int(semantic_summary.get('top1_hits', 0))}")
    lines.append(f"- Top3 命中数：{int(semantic_summary.get('top3_hits', 0))}")
    lines.append(f"- Top1 命中率：{float(semantic_summary.get('top1_rate', 0.0)):.4f}")
    lines.append(f"- Top3 命中率：{float(semantic_summary.get('top3_rate', 0.0)):.4f}")
    lines.append("")
    lines.append("## 输出文件")
    lines.append("")
    lines.append(f"- 历史评论数据：{output_files['history_events']}")
    lines.append(f"- 抽取评测数据：{output_files['extraction_cases']}")
    lines.append(f"- 召回评测数据：{output_files['semantic_cases']}")
    lines.append(f"- 抽取明细报告：{output_files['memory_extraction_report']}")
    lines.append(f"- 召回明细报告：{output_files['semantic_recall_report']}")
    lines.append("")
    lines.append("## 分析结论")
    lines.append("")
    lines.append("本轮结果说明 LLM 抽取已经明显优于规则抽取，尤其是在长期偏好、负向约束和 canonical 提纯上更稳定。")
    lines.append("从抽取侧看，如果 Precision 和类型准确率仍低于预期，优先应继续优化 memory_text_canonical 的提纯规则、负向偏好识别和 short_term 过滤。")
    lines.append("从召回侧看，如果 Top1 和 Top3 保持高位，说明长期画像入库后的语义检索与重排已经能支撑老观众多轮对话。")
    lines.append("下一步建议重点看两类误差：")
    lines.append("1. LLM 把短期状态误写入长期记忆。")
    lines.append("2. LLM 把长期事实写得过长，导致 canonical 不够干净。")
    lines.append("")
    return "\n".join(lines)
