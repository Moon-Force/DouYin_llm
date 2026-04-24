import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.services.memory_reranker import GiteeRerankClient


OUT_DIR = ROOT / "artifacts" / "rerank_eval"
CASES_PATH = OUT_DIR / "live_memory_rerank_cases.json"
RESULTS_PATH = OUT_DIR / "gitee_qwen3_rerank_results.json"
REPORT_PATH = OUT_DIR / "gitee_qwen3_rerank_report.md"


def load_cases():
    return json.loads(CASES_PATH.read_text(encoding="utf-8"))


def evaluate_case(client, case):
    start = time.perf_counter()
    scores = client.rerank(case["query"], case["documents"], top_n=len(case["documents"]))
    elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
    ranked = sorted(
        [
            {
                "index": index,
                "score": float(scores.get(index, 0.0)),
                "document": document,
                "is_relevant": index in set(case.get("relevant_indexes", [])),
            }
            for index, document in enumerate(case["documents"])
        ],
        key=lambda item: item["score"],
        reverse=True,
    )
    relevant = set(case.get("relevant_indexes", []))
    top1 = ranked[0]["index"] if ranked else None
    top3 = [item["index"] for item in ranked[:3]]
    return {
        **case,
        "elapsed_ms": elapsed_ms,
        "ranked": ranked,
        "top1_index": top1,
        "top1_hit": bool(relevant and top1 in relevant),
        "top3_hit": bool(relevant and any(index in relevant for index in top3)),
        "no_relevant_case": not relevant,
        "no_relevant_max_score": ranked[0]["score"] if ranked and not relevant else None,
    }


def summarize(results):
    answerable = [item for item in results if not item["no_relevant_case"]]
    no_relevant = [item for item in results if item["no_relevant_case"]]
    top1_hits = sum(item["top1_hit"] for item in answerable)
    top3_hits = sum(item["top3_hit"] for item in answerable)
    return {
        "case_count": len(results),
        "answerable_case_count": len(answerable),
        "no_relevant_case_count": len(no_relevant),
        "top1_hits": top1_hits,
        "top3_hits": top3_hits,
        "top1_rate": top1_hits / len(answerable) if answerable else 0.0,
        "top3_rate": top3_hits / len(answerable) if answerable else 0.0,
        "avg_latency_ms": round(sum(item["elapsed_ms"] for item in results) / len(results), 2),
        "max_latency_ms": max(item["elapsed_ms"] for item in results),
        "no_relevant_max_scores": [item["no_relevant_max_score"] for item in no_relevant],
    }


def write_report(payload):
    summary = payload["summary"]
    lines = [
        "# Gitee Qwen3 Reranker 直播记忆话风测试报告",
        "",
        "## 测试目标",
        "",
        "验证在线 `Qwen3-Reranker-0.6B` 在直播弹幕 + 观众长期记忆候选上的排序能力，重点覆盖饮品、忌口、护肤、宠物、工作城市、住处、食物偏好和闲聊无召回场景。",
        "",
        "## 汇总指标",
        "",
        f"- 总 case 数：{summary['case_count']}",
        f"- 有明确相关记忆 case：{summary['answerable_case_count']}",
        f"- 无应召回记忆 case：{summary['no_relevant_case_count']}",
        f"- Top1 命中率：{summary['top1_rate']:.2%} ({summary['top1_hits']}/{summary['answerable_case_count']})",
        f"- Top3 命中率：{summary['top3_rate']:.2%} ({summary['top3_hits']}/{summary['answerable_case_count']})",
        f"- 平均延迟：{summary['avg_latency_ms']} ms",
        f"- 最大延迟：{summary['max_latency_ms']} ms",
        "",
        "## Case 明细",
        "",
    ]
    for item in payload["results"]:
        top = item["ranked"][0] if item["ranked"] else {}
        expected = item.get("relevant_indexes", [])
        status = "通过" if item["no_relevant_case"] or item["top1_hit"] else "未通过"
        lines.extend(
            [
                f"### {item['id']}（{item['category']}）",
                "",
                f"- 状态：{status}",
                f"- 延迟：{item['elapsed_ms']} ms",
                f"- 期望相关 index：{expected if expected else '无明确相关记忆'}",
                f"- Top1 index：{top.get('index')}，score：{top.get('score')}",
                f"- Top1 文档：{str(top.get('document', '')).splitlines()[0] if top else ''}",
                "",
            ]
        )
    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")


def main():
    api_key = os.getenv("MEMORY_RERANK_API_KEY", "").strip()
    if not api_key:
        raise SystemExit("Please set MEMORY_RERANK_API_KEY before running this eval.")
    client = GiteeRerankClient(
        base_url=os.getenv("MEMORY_RERANK_BASE_URL", "https://ai.gitee.com/v1"),
        api_key=api_key,
        model=os.getenv("MEMORY_RERANK_MODEL", "Qwen3-Reranker-0.6B"),
        timeout_seconds=float(os.getenv("MEMORY_RERANK_TIMEOUT_SECONDS", "20")),
    )
    results = [evaluate_case(client, case) for case in load_cases()]
    payload = {"summary": summarize(results), "results": results}
    RESULTS_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_report(payload)
    print(json.dumps(payload["summary"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
