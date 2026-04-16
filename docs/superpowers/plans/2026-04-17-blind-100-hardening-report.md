# Blind 100 Hardening Report Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 直接升级 `blind_100.json` 为每条 10 条高相似记忆的更难评测集，并让现有 `semantic-recall` 命令在运行后自动生成一份包含全量 case 明细的 Markdown 报告。

**Architecture:** 保留现有 `semantic-recall` 命令入口和数据 schema，不新增必填参数。runner 内部新增结构化 case 结果与 Markdown 渲染逻辑，先基于结构化结果统计 `top1/top3`，再把同一份结果写成固定路径报告；数据集则继续沿用 `blind_100.json`，但把每条 case 的 `memory_texts` 从 4 条扩到 10 条，并显式加入高相似干扰项。

**Tech Stack:** Python `unittest`、JSON fixture、现有 `tests.memory_pipeline_verifier.runner`、SQLite、Chroma、项目内 `EmbeddingService` / `VectorMemory`

---

## File Structure

- Modify: `H:/DouYin_llm/tests/fixtures/semantic_recall/blind_100.json`
  - 把 100 条 case 升级为每条 10 条记忆，保持 5 类标签各 20 条，并提高同一 viewer 内部的语义干扰强度。
- Modify: `H:/DouYin_llm/tests/memory_pipeline_verifier/runner.py`
  - 增加结构化语义评测结果、报告输出路径派生、Markdown 报告生成与写文件逻辑。
- Modify: `H:/DouYin_llm/tests/test_verify_memory_pipeline.py`
  - 先写失败测试，收紧 blind_100 数据约束，并验证报告文件生成与内容。

本次不修改：

- `H:/DouYin_llm/tests/memory_pipeline_verifier/datasets.py`
  - 保持通用 fixture 加载逻辑不动，本轮约束由 blind_100 专项测试承接。

### Task 1: 先写失败测试，锁定 blind_100 新约束与报告产物

**Files:**
- Modify: `H:/DouYin_llm/tests/test_verify_memory_pipeline.py`
- Test: `H:/DouYin_llm/tests/test_verify_memory_pipeline.py`

- [ ] **Step 1: 写失败测试，收紧 blind_100 到 10 条记忆**

```python
def test_blind_semantic_recall_fixture_cases_have_ten_memory_choices(self):
    fixture_path = Path("tests/fixtures/semantic_recall/blind_100.json")

    cases = load_semantic_recall_fixture(fixture_path)

    self.assertTrue(all(len(case["memory_texts"]) >= 10 for case in cases))
    self.assertTrue(all(case["expected_memory_text"] in case["memory_texts"] for case in cases))


def test_blind_semantic_recall_fixture_keeps_category_balance_and_non_copy_queries(self):
    fixture_path = Path("tests/fixtures/semantic_recall/blind_100.json")

    cases = load_semantic_recall_fixture(fixture_path)
    category_counts = Counter(tuple(case["tags"]) for case in cases)

    self.assertEqual(category_counts[("typo",)], 20)
    self.assertEqual(category_counts[("spoken",)], 20)
    self.assertEqual(category_counts[("fragment",)], 20)
    self.assertEqual(category_counts[("typo", "spoken", "fragment", "mixed_noise")], 20)
    self.assertEqual(category_counts[("distractor",)], 20)
    self.assertTrue(all(case["query"].strip() != case["expected_memory_text"].strip() for case in cases))
```

- [ ] **Step 2: 写失败测试，锁定 Markdown 报告生成**

```python
def test_run_semantic_recall_verification_writes_markdown_report(self):
    dataset = [
        {
            "label": "blind-001",
            "tags": ["typo"],
            "room_id": "room-1",
            "viewer_id": "id:viewer-1",
            "memory_texts": [
                "我在杭州做前端开发，最近连续两周都在加班赶需求。",
                "我最近在赶一个移动端重构项目，这两周经常改到半夜。",
                "我们组这个月一直在冲版本，晚上开会和改页面都特别频繁。",
                "我白天写后台联调，晚上还得补前端交互细节。",
                "我最近在做页面性能优化，连着几天都改到很晚。",
                "最近版本联调问题很多，下班后还得继续跟。",
                "这段时间需求变更多，前端排期一直很紧。",
                "我最近总在补交互细节，晚上经常不能准点走。",
                "最近项目节奏特别赶，白天晚上都在盯页面。",
                "我这两周一直在赶上线，所以经常熬夜处理问题。",
            ],
            "query": "最近写页面经常熬页赶进度",
            "expected_memory_text": "我在杭州做前端开发，最近连续两周都在加班赶需求。",
        }
    ]

    with tempfile.TemporaryDirectory(prefix="semantic-report-") as tempdir, patch(
        "tests.memory_pipeline_verifier.runner.load_semantic_recall_fixture",
        return_value=dataset,
    ), patch("tests.memory_pipeline_verifier.runner.EmbeddingService", return_value=MagicMock()), patch(
        "tests.memory_pipeline_verifier.runner.VectorMemory"
    ) as vector_cls:
        fake_vector = MagicMock()
        fake_vector.similar_memories.return_value = [
            {"memory_text": "我在杭州做前端开发，最近连续两周都在加班赶需求。"},
            {"memory_text": "我最近在赶一个移动端重构项目，这两周经常改到半夜。"},
            {"memory_text": "我们组这个月一直在冲版本，晚上开会和改页面都特别频繁。"},
        ]
        vector_cls.return_value = fake_vector

        results, report_path = run_semantic_recall_verification(
            "tests/fixtures/semantic_recall/blind_100.json",
            report_dir=Path(tempdir),
        )

    report_text = Path(report_path).read_text(encoding="utf-8")
    self.assertTrue(Path(report_path).exists())
    self.assertEqual(results[3].name, "report")
    self.assertIn("# Semantic Recall Report", report_text)
    self.assertIn("## blind-001", report_text)
    self.assertIn("Top1 Hit", report_text)
    self.assertIn("Top3 Hit", report_text)
```

- [ ] **Step 3: 运行测试，确认它们先失败**

Run: `python -m unittest tests.test_verify_memory_pipeline.VerifyMemoryPipelineTests.test_blind_semantic_recall_fixture_cases_have_ten_memory_choices tests.test_verify_memory_pipeline.VerifyMemoryPipelineTests.test_run_semantic_recall_verification_writes_markdown_report -v`

Expected: FAIL，前者因为 blind_100 目前只有 4 条记忆，后者因为 `run_semantic_recall_verification` 还不支持 `report_dir` / `report` 步骤 / Markdown 报告。

- [ ] **Step 4: 提交测试骨架**

```bash
git add tests/test_verify_memory_pipeline.py
git commit -m "test: add blind recall hardening guards"
```

### Task 2: 升级 blind_100 数据集到 10 条高相似记忆

**Files:**
- Modify: `H:/DouYin_llm/tests/fixtures/semantic_recall/blind_100.json`
- Test: `H:/DouYin_llm/tests/test_verify_memory_pipeline.py`

- [ ] **Step 1: 扩展每条 case 的 memory_texts 到 10 条，并保持 5 类 x 20 条**

```json
{
  "label": "blind-001",
  "tags": ["typo"],
  "room_id": "semantic-blind-room",
  "viewer_id": "id:semantic-blind-viewer-001",
  "memory_texts": [
    "我在杭州做前端开发，最近连续两周都在加班赶需求。",
    "我最近在赶一个移动端重构项目，这两周经常改到半夜。",
    "我们组这个月一直在冲版本，晚上开会和改页面都特别频繁。",
    "我白天写后台联调，晚上还得补前端交互细节。",
    "我最近在做页面性能优化，连着几天都改到很晚。",
    "最近版本联调问题很多，下班后还得继续跟。",
    "这段时间需求变更多，前端排期一直很紧。",
    "我最近总在补交互细节，晚上经常不能准点走。",
    "最近项目节奏特别赶，白天晚上都在盯页面。",
    "我这两周一直在赶上线，所以经常熬夜处理问题。"
  ],
  "query": "最近写页面经常熬页赶进度",
  "expected_memory_text": "我在杭州做前端开发，最近连续两周都在加班赶需求。"
}
```

生成原则直接落实到文件内容：

- 每条 `memory_texts` 都达到 `10` 条
- 原有目标记忆保留
- 新增 `6` 条优先写同主题、同时间段、同生活域的高相似干扰项
- 继续保持 `query` 不直接复读 `expected_memory_text`
- 继续保持 `label` 唯一、`viewer_id` 唯一、`tags` 分布不变

- [ ] **Step 2: 运行 blind_100 数据约束测试，确认通过**

Run: `python -m unittest tests.test_verify_memory_pipeline.VerifyMemoryPipelineTests.test_load_semantic_recall_blind_fixture_has_hundred_tagged_cases tests.test_verify_memory_pipeline.VerifyMemoryPipelineTests.test_blind_semantic_recall_fixture_cases_have_ten_memory_choices tests.test_verify_memory_pipeline.VerifyMemoryPipelineTests.test_blind_semantic_recall_fixture_keeps_category_balance_and_non_copy_queries -v`

Expected: PASS

- [ ] **Step 3: 提交数据集升级**

```bash
git add tests/fixtures/semantic_recall/blind_100.json tests/test_verify_memory_pipeline.py
git commit -m "test: deepen blind semantic recall dataset"
```

### Task 3: 给 semantic recall runner 增加结构化结果和 Markdown 报告

**Files:**
- Modify: `H:/DouYin_llm/tests/memory_pipeline_verifier/runner.py`
- Modify: `H:/DouYin_llm/tests/test_verify_memory_pipeline.py`

- [ ] **Step 1: 写失败测试，锁定报告路径派生和返回值**

```python
def test_semantic_recall_report_path_uses_dataset_name(self):
    report_path = build_semantic_recall_report_path(
        "tests/fixtures/semantic_recall/blind_100.json"
    )

    self.assertEqual(
        report_path.as_posix(),
        "artifacts/semantic_recall_reports/blind_100.md",
    )
```

- [ ] **Step 2: 运行测试，确认 helper 尚不存在**

Run: `python -m unittest tests.test_verify_memory_pipeline.VerifyMemoryPipelineTests.test_semantic_recall_report_path_uses_dataset_name -v`

Expected: FAIL，报 `build_semantic_recall_report_path` 未定义。

- [ ] **Step 3: 在 runner.py 里实现结构化 case 结果、报告路径和 Markdown 渲染**

```python
def build_semantic_recall_report_path(dataset_path, report_dir=None):
    dataset_name = Path(dataset_path).stem
    base_dir = Path(report_dir) if report_dir else Path("artifacts") / "semantic_recall_reports"
    return base_dir / f"{dataset_name}.md"


def render_semantic_recall_report(dataset_path, total_memories, case_results):
    total_cases = len(case_results)
    top1_hits = sum(1 for item in case_results if item["top1_hit"])
    top3_hits = sum(1 for item in case_results if item["top3_hit"])
    lines = [
        "# Semantic Recall Report",
        "",
        "## Summary",
        f"- Dataset: {dataset_path}",
        f"- Cases: {total_cases}",
        f"- Memories: {total_memories}",
        f"- Top1: {top1_hits}/{total_cases}",
        f"- Top3: {top3_hits}/{total_cases}",
    ]
    for item in case_results:
        lines.extend(
            [
                "",
                f"## {item['label']}",
                "",
                f"- Tags: {', '.join(item['tags'])}",
                f"- Query: {item['query']}",
                f"- Expected: {item['expected_memory_text']}",
                f"- Top1 Hit: {'yes' if item['top1_hit'] else 'no'}",
                f"- Top3 Hit: {'yes' if item['top3_hit'] else 'no'}",
                "",
                "Top 3:",
                *[
                    f"{index}. {text}"
                    for index, text in enumerate(item['top_texts'], start=1)
                ],
            ]
        )
    return "\n".join(lines) + "\n"
```

- [ ] **Step 4: 改造 run_semantic_recall_verification，生成 report 步骤并返回路径**

```python
def run_semantic_recall_verification(dataset_path, report_dir=None):
    ...
    case_results = []
    for index, case in enumerate(cases, start=1):
        ...
        top1_hit = bool(top_texts[:1]) and top_texts[0] == expected
        top3_hit = expected in top_texts
        case_results.append(
            {
                "label": str(case.get("label") or f"case-{index}"),
                "tags": [str(tag).strip() for tag in case.get("tags", []) if str(tag).strip()],
                "query": str(case.get("query") or "").strip(),
                "expected_memory_text": expected,
                "top_texts": top_texts,
                "top1_hit": top1_hit,
                "top3_hit": top3_hit,
            }
        )
        if top1_hit:
            top1_hits += 1
        if top3_hit:
            top3_hits += 1

    ...
    report_path = build_semantic_recall_report_path(dataset_path, report_dir=report_dir)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        render_semantic_recall_report(dataset_path, total_memories, case_results),
        encoding="utf-8",
    )
    record_step(results, "report", True, f"path={report_path}")
    return results, report_path
```

- [ ] **Step 5: 跑报告相关测试，确认通过**

Run: `python -m unittest tests.test_verify_memory_pipeline.VerifyMemoryPipelineTests.test_semantic_recall_report_path_uses_dataset_name tests.test_verify_memory_pipeline.VerifyMemoryPipelineTests.test_run_semantic_recall_verification_writes_markdown_report tests.test_verify_memory_pipeline.VerifyMemoryPipelineTests.test_run_semantic_recall_verification_reports_top1_and_top3 tests.test_verify_memory_pipeline.VerifyMemoryPipelineTests.test_run_semantic_recall_verification_marks_failure_when_expected_text_misses_top3 -v`

Expected: PASS，且原有 top1/top3 测试更新后仍成立。

- [ ] **Step 6: 提交 runner 和报告能力**

```bash
git add tests/memory_pipeline_verifier/runner.py tests/test_verify_memory_pipeline.py
git commit -m "feat: add semantic recall markdown report"
```

### Task 4: 完整验证并用正式命令生成 blind_100 报告

**Files:**
- Modify: `H:/DouYin_llm/tests/fixtures/semantic_recall/blind_100.json`
- Modify: `H:/DouYin_llm/tests/memory_pipeline_verifier/runner.py`
- Modify: `H:/DouYin_llm/tests/test_verify_memory_pipeline.py`

- [ ] **Step 1: 跑 verify_memory_pipeline 全量单测**

Run: `python -m unittest tests.test_verify_memory_pipeline -v`

Expected: PASS，包括 blind_100 10 条记忆约束和 Markdown 报告测试。

- [ ] **Step 2: 用正式命令跑 blind_100，并确认报告文件生成**

Run: `python -u -m tests.memory_pipeline_verifier.runner --mode internal --task semantic-recall --dataset tests/fixtures/semantic_recall/blind_100.json`

Expected: 输出 `dataset`、`index_memories`、`semantic_recall`、`report` 四个步骤，并在 `artifacts/semantic_recall_reports/blind_100.md` 生成全量报告。

- [ ] **Step 3: 检查报告文件内容**

Run: `Get-Content -Path artifacts/semantic_recall_reports/blind_100.md -Encoding utf8 | Select-Object -First 60`

Expected: 能看到 `# Semantic Recall Report`、`## Summary` 和 `## blind-001` 这类 case 明细标题。

- [ ] **Step 4: 检查工作区，只保留本次改动**

Run: `git status --short`

Expected: 仅出现 `tests/fixtures/semantic_recall/blind_100.json`、`tests/memory_pipeline_verifier/runner.py`、`tests/test_verify_memory_pipeline.py` 和生成的 `artifacts/semantic_recall_reports/blind_100.md`；无关文件不处理。

- [ ] **Step 5: 提交最终收口**

```bash
git add tests/fixtures/semantic_recall/blind_100.json tests/memory_pipeline_verifier/runner.py tests/test_verify_memory_pipeline.py artifacts/semantic_recall_reports/blind_100.md
git commit -m "feat: harden blind semantic recall evaluation"
```

## Self-Review

- 规格覆盖检查：升级现有 blind_100、每条 10 条记忆、高相似干扰项、Markdown 报告、全量 case 明细、固定路径产物，都已映射到 Task 1-4。
- 占位符检查：没有使用 `TODO`、`TBD` 或“后续再补”这类占位语句。
- 一致性检查：全程统一使用 `blind_100.json`、`artifacts/semantic_recall_reports/blind_100.md`、`build_semantic_recall_report_path`、`render_semantic_recall_report`、`run_semantic_recall_verification(..., report_dir=None)` 这些命名。
