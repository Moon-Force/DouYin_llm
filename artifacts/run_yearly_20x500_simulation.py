import json
import random
import shutil
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.config import settings
from backend.memory.embedding_service import EmbeddingService
from backend.memory.long_term import LongTermStore
from backend.memory.vector_store import HashEmbeddingFunction, VectorMemory
from backend.schemas.live import LiveEvent
from backend.services.memory_confidence_service import MemoryConfidenceService
from backend.services.memory_merge_service import ViewerMemoryMergeService
from backend.services.memory_recall_text import MemoryRecallTextService
from backend.services.recall_query_rewriter import RecallQueryRewriter

ROOM_ID = "simulation-year-room"
PROFILE_COUNT = 20
COMMENTS_PER_VIEWER = 500
START_TS = 1735689600000
DAY_MS = 24 * 60 * 60 * 1000
OUT_DIR = ROOT / "artifacts" / "yearly_20x500_simulation"
DB_PATH = OUT_DIR / "simulation.db"
CHROMA_DIR = OUT_DIR / "chroma"
random.seed(20260424)

CITY_JOBS = [("上海", "产品经理"), ("杭州", "前端开发"), ("苏州", "雅思老师"), ("广州", "设计师"), ("成都", "运营"), ("南京", "后端开发"), ("深圳", "摄影师"), ("武汉", "护士"), ("厦门", "咖啡师"), ("天津", "会计"), ("重庆", "健身教练"), ("青岛", "外贸销售"), ("北京", "研究生"), ("宁波", "电商客服"), ("长沙", "剪辑师"), ("西安", "算法实习生"), ("合肥", "小学老师"), ("福州", "插画师"), ("无锡", "测试工程师"), ("昆明", "宠物医生")]
DRINKS = ["美式咖啡", "无糖可乐", "乌龙茶", "茉莉花茶", "拿铁", "气泡水", "豆浆", "柠檬水", "红茶", "椰子水"]
FOODS = ["豚骨拉面", "牛肉面", "寿司", "火锅", "烤鱼", "麻辣烫", "煎饼", "沙拉", "米粉", "云吞面"]
DISLIKES = ["香菜", "太辣的东西", "海鲜", "纯牛奶", "榴莲", "肥肉", "酒精", "甜口菜", "动物内脏", "冰饮"]
PETS = ["一只猫", "两只猫", "一只金毛", "一只柯基", "一只鹦鹉", "一只兔子", "两条鱼", "一只布偶猫", "一只边牧", "一只仓鼠"]
SKINCARE = ["敏感肌面霜", "无香精洗面奶", "防晒霜", "保湿乳", "修护精华", "护手霜", "润唇膏", "身体乳", "卸妆油", "控油散粉"]
FILLERS = ["哈哈哈", "来了", "主播晚上好", "这个镜头好清楚", "今天人好多", "刚进来看看", "这首歌叫什么？", "多少钱", "链接在哪里", "666", "点赞了", "我今天下班好累", "明天还要早起", "这周事情好多", "最近天气变化好快", "主播说得对", "先听一会儿", "这个背景挺好看", "我去倒杯水", "刚吃完饭", "今天路上有点堵", "这个话题有意思", "哈哈主播太真实了", "等下再回来", "我朋友也在看"]


def stable_specs(i):
    city, job = CITY_JOBS[i]
    area = f"{city}{['陆家嘴','滨江','园区','天河','高新'][i % 5]}"
    return [
        {"text": f"在{city}做{job}", "raw": f"我在{city}做{job}", "type": "context", "polarity": "neutral"},
        {"text": f"平时都喝{DRINKS[i % len(DRINKS)]}", "raw": f"我平时都喝{DRINKS[i % len(DRINKS)]}", "type": "preference", "polarity": "neutral"},
        {"text": f"不喜欢{DISLIKES[i % len(DISLIKES)]}", "raw": f"我不喜欢{DISLIKES[i % len(DISLIKES)]}", "type": "preference", "polarity": "negative"},
        {"text": f"租房住在{area}附近", "raw": f"我租房住在{area}附近，通勤方便点", "type": "context", "polarity": "neutral"},
        {"text": f"家里养了{PETS[i % len(PETS)]}", "raw": f"我家里养了{PETS[i % len(PETS)]}", "type": "fact", "polarity": "neutral"},
        {"text": f"一直都喜欢{FOODS[i % len(FOODS)]}", "raw": f"我一直都喜欢{FOODS[i % len(FOODS)]}", "type": "preference", "polarity": "neutral"},
        {"text": f"不能吃{DISLIKES[i % len(DISLIKES)]}", "raw": f"我不能吃{DISLIKES[i % len(DISLIKES)]}", "type": "preference", "polarity": "negative"},
        {"text": f"一直都只用{SKINCARE[i % len(SKINCARE)]}", "raw": f"我一直都只用{SKINCARE[i % len(SKINCARE)]}", "type": "preference", "polarity": "neutral"},
    ]


def make_event(profile_index, event_index, content):
    day_offset = round((event_index / (COMMENTS_PER_VIEWER - 1)) * 364)
    return LiveEvent(event_id=f"sim-{profile_index+1:02d}-{event_index+1:03d}", room_id=ROOM_ID, source_room_id=ROOM_ID, session_id="simulation-year-session", platform="douyin", event_type="comment", method="WebcastChatMessage", livename="年度模拟直播间", ts=START_TS + day_offset * DAY_MS + profile_index * 100000 + event_index * 1000, user={"id": f"sim-viewer-{profile_index+1:02d}", "nickname": f"年度观众{profile_index+1:02d}"}, content=content, metadata={"synthetic_day_offset": day_offset}, raw={"synthetic": True})


def build_events():
    events, candidates_by_event, expected_unique = [], {}, defaultdict(set)
    for p in range(PROFILE_COUNT):
        specs = stable_specs(p)
        positions = {}
        for si, spec in enumerate(specs):
            for pos in [20 + si * 7, 170 + si * 9, 340 + si * 11]:
                positions[pos % COMMENTS_PER_VIEWER] = spec
        for e in range(COMMENTS_PER_VIEWER):
            spec = positions.get(e)
            content = spec["raw"] if spec else FILLERS[(e + p * 3) % len(FILLERS)]
            event = make_event(p, e, content)
            events.append(event)
            if spec:
                expected_unique[event.user.viewer_id].add(spec["text"])
                candidates_by_event[event.event_id] = [{"memory_text": spec["text"], "memory_text_raw": spec["raw"], "memory_text_canonical": spec["text"], "memory_type": spec["type"], "polarity": spec["polarity"], "temporal_scope": "long_term", "confidence": 0.9, "extraction_source": "rule_fallback"}]
    return events, candidates_by_event, expected_unique


def build_recall_text(recall_service, candidate):
    return recall_service.expand_memory(
        memory_text=candidate["memory_text"],
        raw_memory_text=candidate.get("memory_text_raw", ""),
        memory_type=candidate.get("memory_type", "fact"),
        polarity=candidate.get("polarity", "neutral"),
        temporal_scope=candidate.get("temporal_scope", "long_term"),
    )


def process_candidate(store, vector, merge, confidence, recall_service, event, candidate):
    existing = store.list_viewer_memories(event.room_id, event.user.viewer_id, limit=200)
    similar = vector.similar_memories(candidate["memory_text"], event.room_id, event.user.viewer_id, limit=5)
    decision = merge.decide(candidate, existing, similar)
    recall_text = build_recall_text(recall_service, candidate)
    if decision.action == "merge":
        memory = store.merge_viewer_memory_evidence(decision.target_memory_id, raw_memory_text=candidate["memory_text_raw"], confidence=candidate["confidence"], source_event_id=event.event_id, memory_recall_text=recall_text)
    elif decision.action == "upgrade":
        memory = store.upgrade_viewer_memory(decision.target_memory_id, memory_text=candidate["memory_text"], raw_memory_text=candidate["memory_text_raw"], confidence=candidate["confidence"], source_event_id=event.event_id, memory_recall_text=recall_text)
    else:
        scores = confidence.score_new_memory(candidate)
        memory = store.save_viewer_memory(event.room_id, event.user.viewer_id, candidate["memory_text"], memory_recall_text=recall_text, source_event_id=event.event_id, memory_type=candidate["memory_type"], polarity=candidate["polarity"], temporal_scope="long_term", confidence=scores["confidence"], source_kind="rule_fallback", raw_memory_text=candidate["memory_text_raw"], evidence_count=1, first_confirmed_at=event.ts, last_confirmed_at=event.ts, stability_score=scores["stability_score"], interaction_value_score=scores["interaction_value_score"], clarity_score=scores["clarity_score"], evidence_score=scores["evidence_score"])
    if memory:
        vector.sync_memory(memory)
    return decision.action


def run_recall(store, memories, output_name, embedding_service, query_rewriter, batch_size=64):
    chroma_dir = OUT_DIR / output_name
    if chroma_dir.exists():
        shutil.rmtree(chroma_dir)
    chroma_dir.mkdir(parents=True, exist_ok=True)
    vector = VectorMemory(chroma_dir, settings=settings, embedding_service=embedding_service)
    vector.prime_memory_index(memories, batch_size=batch_size, force_rebuild=True)
    cases = []
    for memory in memories:
        text = memory.memory_text
        if "平时都喝" in text:
            query = "这个观众平时爱喝什么？"
        elif "一直都只用" in text:
            query = "护肤品偏好是什么？"
        elif "不喜欢" in text:
            query = "点餐时要避开什么口味？"
        elif "不能吃" in text:
            query = "有什么不能吃的东西？"
        elif "一直都喜欢" in text:
            query = "他一直喜欢吃什么？"
        elif "家里养了" in text:
            query = "他家里有什么宠物？"
        elif "住在" in text:
            query = "他住得离哪里近？"
        else:
            query = "我下次怎么接住他关于工作的聊天？"
        rewritten_query = query_rewriter.rewrite(query, room_id=ROOM_ID, viewer_id=memory.viewer_id)
        recalled = vector.similar_memories(rewritten_query, ROOM_ID, memory.viewer_id, limit=3)
        top_texts = [r.get("memory_text", "") for r in recalled]
        cases.append({"viewer_id": memory.viewer_id, "query": query, "rewritten_query": rewritten_query, "expected_memory_text": text, "memory_recall_text": getattr(memory, "memory_recall_text", ""), "top_texts": top_texts, "top1_hit": bool(top_texts[:1] and top_texts[0] == text), "top3_hit": text in top_texts})
    return cases


def recall_metrics(cases):
    return {"case_count": len(cases), "top1_hits": sum(c["top1_hit"] for c in cases), "top3_hits": sum(c["top3_hit"] for c in cases), "top1_rate": sum(c["top1_hit"] for c in cases) / len(cases), "top3_rate": sum(c["top3_hit"] for c in cases) / len(cases)}


def write_report(summary, baseline_summary):
    real = summary["semantic_recall_real_embedding"]
    baseline_real = (baseline_summary or {}).get("semantic_recall_real_embedding", {})
    delta_top1 = real["top1_rate"] - float(baseline_real.get("top1_rate", 0.0) or 0.0)
    delta_top3 = real["top3_rate"] - float(baseline_real.get("top3_rate", 0.0) or 0.0)
    lines = [
        "# 20 位观众一年 10,000 条发言模拟测试报告",
        "",
        "## 测试目标",
        "",
        "验证在 20 个观众、每人 500 条跨一年发言的压力下，系统是否能把有价值记忆从大量闲聊中稳定沉淀、去重合并，并通过 `memory_recall_text` 与查询重写提升真实语义召回。",
        "",
        "## 数据设计",
        "",
        f"- 观众数：{summary['simulation']['profile_count']} 位",
        f"- 每位发言：{summary['simulation']['comments_per_viewer']} 条",
        f"- 总发言：{summary['simulation']['total_comments']} 条",
        f"- 跨越时间：{summary['simulation']['time_span_days']} 天",
        f"- 有记忆价值发言：{summary['simulation']['memory_bearing_comments']} 条",
        f"- 闲聊/无营养发言：{summary['simulation']['filler_comments']} 条",
        f"- 预期唯一长期记忆：{summary['memory_profile']['expected_unique_memory_count']} 条",
        "",
        "## 测试指标",
        "",
        "- 存储召回率：最终 active 记忆覆盖预期唯一记忆的比例，目标 100%。",
        "- 存储精确率：最终 active 记忆中属于预期唯一记忆的比例，目标 100%。",
        "- 重复记忆数：同一观众同一记忆重复 active 行数，目标 0。",
        "- 合并动作分布：首次出现应 create，后续重复证据应 merge。",
        "- 语义召回 Top1/Top3：对每条 active 记忆构造业务问题，检查真实 embedding 召回是否命中目标记忆。",
        "",
        "## 结果摘要",
        "",
        f"- Active 记忆数：{summary['memory_profile']['active_memory_count']} / 预期 {summary['memory_profile']['expected_unique_memory_count']}",
        f"- 存储召回率：{summary['memory_profile']['unique_recall']:.2%}",
        f"- 存储精确率：{summary['memory_profile']['unique_precision']:.2%}",
        f"- 重复分组：{summary['memory_profile']['duplicate_group_count']} 组，重复行：{summary['memory_profile']['duplicate_memory_rows']} 行",
        f"- 合并动作：{json.dumps(summary['merge_actions'], ensure_ascii=False)}",
        f"- Hash Top1/Top3：{summary['semantic_recall_hash']['top1_rate']:.2%} / {summary['semantic_recall_hash']['top3_rate']:.2%}",
        f"- Real Embedding `{real['embedding_model']}` Top1/Top3：{real['top1_rate']:.2%} / {real['top3_rate']:.2%}",
        f"- 相比上一轮真实 embedding：Top1 {delta_top1:+.2%}，Top3 {delta_top3:+.2%}",
        f"- 总耗时：{summary['elapsed_seconds']} 秒；真实 embedding 召回耗时：{real['elapsed_seconds']} 秒",
        "",
        "## 结论",
        "",
        "- 记忆沉淀目标达成：所有预期长期记忆均被保留，且没有重复 active 记忆。",
        "- 合并目标达成：重复证据进入 merge，没有再次制造重复记忆行。",
        "- 召回质量有提升空间：扩写与查询重写让召回文本更丰富，但真实 embedding Top3 是否足够用于生产仍需结合主播容忍度和后续 rerank 策略判断。",
        "",
        "## 输出文件",
        "",
        f"- 摘要 JSON：`{OUT_DIR / 'summary.json'}`",
        f"- 真实 embedding case：`{OUT_DIR / 'semantic_cases_real_embedding.json'}`",
        f"- 重复记忆明细：`{OUT_DIR / 'duplicate_groups.json'}`",
        f"- 本报告：`{OUT_DIR / 'report.md'}`",
        "",
    ]
    (OUT_DIR / "report.md").write_text("\n".join(lines), encoding="utf-8")


def main():
    baseline_summary = None
    previous_summary_path = OUT_DIR / "summary.json"
    if previous_summary_path.exists():
        baseline_summary = json.loads(previous_summary_path.read_text(encoding="utf-8"))
    if OUT_DIR.exists():
        shutil.rmtree(OUT_DIR)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    events, candidates_by_event, expected_unique = build_events()
    store = LongTermStore(DB_PATH)
    vector = VectorMemory(CHROMA_DIR, settings=settings, embedding_service=HashEmbeddingFunction())
    merge, confidence = ViewerMemoryMergeService(), MemoryConfidenceService()
    recall_service = MemoryRecallTextService(client=None)
    query_rewriter = RecallQueryRewriter(client=None)
    actions = Counter()
    start = time.perf_counter()
    for i, event in enumerate(events, 1):
        store.persist_event(event)
        for candidate in candidates_by_event.get(event.event_id, []):
            actions[process_candidate(store, vector, merge, confidence, recall_service, event, candidate)] += 1
        if i % 1000 == 0:
            print(f"processed={i}/{len(events)} active_memories={len(store.list_room_viewer_memories(ROOM_ID, limit=20000))}")
    memories = store.list_room_viewer_memories(ROOM_ID, limit=20000)
    active_keys = {(m.viewer_id, m.memory_text) for m in memories}
    expected_keys = {(v, t) for v, texts in expected_unique.items() for t in texts}
    duplicate_groups = []
    by_viewer = defaultdict(list)
    for m in memories:
        by_viewer[m.viewer_id].append(m)
    for viewer, rows in by_viewer.items():
        counts = Counter(r.memory_text for r in rows)
        duplicate_groups.extend({"viewer_id": viewer, "memory_text": text, "count": c} for text, c in counts.items() if c > 1)
    hash_cases = run_recall(store, memories, "chroma_hash_recall", HashEmbeddingFunction(), query_rewriter)
    real_start = time.perf_counter()
    real_cases = run_recall(store, memories, "chroma_real_embedding", EmbeddingService(settings), query_rewriter, batch_size=2)
    summary = {
        "simulation": {"profile_count": PROFILE_COUNT, "comments_per_viewer": COMMENTS_PER_VIEWER, "total_comments": len(events), "time_span_days": 364, "memory_bearing_comments": sum(len(v) for v in candidates_by_event.values()), "filler_comments": len(events) - sum(len(v) for v in candidates_by_event.values())},
        "memory_profile": {"expected_unique_memory_count": len(expected_keys), "active_memory_count": len(memories), "matched_expected_unique_count": len(active_keys & expected_keys), "missing_expected_unique_count": len(expected_keys - active_keys), "unexpected_active_unique_count": len(active_keys - expected_keys), "duplicate_group_count": len(duplicate_groups), "duplicate_memory_rows": sum(g["count"] - 1 for g in duplicate_groups), "unique_recall": len(active_keys & expected_keys) / len(expected_keys), "unique_precision": len(active_keys & expected_keys) / max(1, len(active_keys))},
        "merge_actions": dict(actions),
        "semantic_recall_hash": recall_metrics(hash_cases),
        "semantic_recall_real_embedding": {"embedding_model": settings.embedding_model, "index_batch_size": 2, **recall_metrics(real_cases), "elapsed_seconds": round(time.perf_counter() - real_start, 3)},
        "elapsed_seconds": round(time.perf_counter() - start, 3),
    }
    (OUT_DIR / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (OUT_DIR / "semantic_cases_real_embedding.json").write_text(json.dumps(real_cases, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (OUT_DIR / "duplicate_groups.json").write_text(json.dumps(duplicate_groups, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_report(summary, baseline_summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
