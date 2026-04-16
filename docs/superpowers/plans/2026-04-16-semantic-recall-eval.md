# Semantic Recall Eval Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把正式语义召回评测集接入现有 `verify_memory_pipeline` 命令，让它能通过切换 dataset 直接输出 `top1/top3` 指标。

**Architecture:** 保留现有 `pipeline` 与 `e2e` 验证入口，在 `tests.memory_pipeline_verifier.runner` 中增加 `task` 分发，并把语义召回评测实现成独立执行函数。评测数据使用 JSON fixture 存放，runner 负责读取、校验、建索引、统计指标和打印失败样例，从而保证后续切换测试集只改数据文件，不改评测主逻辑。

**Tech Stack:** Python `unittest`、现有 `tests.memory_pipeline_verifier` 工具、SQLite、Chroma、项目内 `EmbeddingService` / `VectorMemory`

---

## File Structure

- Create: `H:/DouYin_llm/tests/fixtures/semantic_recall/default.json`
  - 正式语义评测集，包含可替换的多样本中文改写问法。
- Modify: `H:/DouYin_llm/tests/memory_pipeline_verifier/datasets.py`
  - 增加语义评测 fixture 的加载与校验辅助函数，避免把数据格式逻辑塞进 runner。
- Modify: `H:/DouYin_llm/tests/memory_pipeline_verifier/runner.py`
  - 增加 `task` 参数、语义评测执行逻辑、top1/top3 汇总、失败样例打印。
- Modify: `H:/DouYin_llm/tests/test_verify_memory_pipeline.py`
  - 先写失败测试，再覆盖参数解析、数据校验、指标统计和默认兼容行为。

### Task 1: 固化语义评测集与数据校验

**Files:**
- Create: `H:/DouYin_llm/tests/fixtures/semantic_recall/default.json`
- Modify: `H:/DouYin_llm/tests/memory_pipeline_verifier/datasets.py`
- Test: `H:/DouYin_llm/tests/test_verify_memory_pipeline.py`

- [ ] **Step 1: 写失败测试，定义语义评测集加载与校验契约**

```python
def test_load_semantic_recall_fixture_returns_cases(self):
    fixture_path = Path("tests/fixtures/semantic_recall/default.json")

    cases = load_semantic_recall_fixture(fixture_path)

    self.assertGreaterEqual(len(cases), 5)
    self.assertIn("memory_texts", cases[0])
    self.assertIn("query", cases[0])
    self.assertIn("expected_memory_text", cases[0])


def test_validate_semantic_recall_cases_rejects_expected_text_outside_memory_texts(self):
    with self.assertRaises(ValueError):
        validate_semantic_recall_cases(
            [
                {
                    "label": "bad-case",
                    "memory_texts": ["我住在公司附近。"],
                    "query": "我家离公司很近",
                    "expected_memory_text": "我平时骑车上班。",
                }
            ]
        )
```

- [ ] **Step 2: 运行测试，确认它们先失败**

Run: `python -m unittest tests.test_verify_memory_pipeline.VerifyMemoryPipelineTests.test_load_semantic_recall_fixture_returns_cases tests.test_verify_memory_pipeline.VerifyMemoryPipelineTests.test_validate_semantic_recall_cases_rejects_expected_text_outside_memory_texts -v`

Expected: FAIL，报 `load_semantic_recall_fixture` / `validate_semantic_recall_cases` 未定义或行为不符合预期。

- [ ] **Step 3: 新增默认 fixture，并在 datasets.py 里实现最小加载/校验逻辑**

```json
[
  {
    "label": "工作熬夜",
    "room_id": "semantic-eval-room",
    "viewer_id": "id:semantic-eval-viewer-001",
    "memory_texts": [
      "我在杭州做前端开发，最近连续两周都在加班赶需求。",
      "我周末常去西湖边夜跑，一次差不多十公里。",
      "我皮肤偏干，换季的时候脸上很容易起皮。"
    ],
    "query": "最近写页面经常熬夜赶进度",
    "expected_memory_text": "我在杭州做前端开发，最近连续两周都在加班赶需求。"
  }
]
```

```python
def load_semantic_recall_fixture(input_path: str | Path) -> list[dict]:
    cases = json.loads(Path(input_path).read_text(encoding="utf-8"))
    validate_semantic_recall_cases(cases)
    return cases


def validate_semantic_recall_cases(cases: list[dict]) -> None:
    if not cases:
        raise ValueError("semantic recall dataset is empty")
    for index, case in enumerate(cases, start=1):
        memory_texts = [str(item or "").strip() for item in case.get("memory_texts", [])]
        expected = str(case.get("expected_memory_text", "")).strip()
        query = str(case.get("query", "")).strip()
        if len(memory_texts) < 2:
            raise ValueError(f"case {index} must contain at least 2 memory_texts")
        if not query:
            raise ValueError(f"case {index} query is required")
        if expected not in memory_texts:
            raise ValueError(f"case {index} expected_memory_text must exist in memory_texts")
```

- [ ] **Step 4: 运行测试，确认加载与校验通过**

Run: `python -m unittest tests.test_verify_memory_pipeline.VerifyMemoryPipelineTests.test_load_semantic_recall_fixture_returns_cases tests.test_verify_memory_pipeline.VerifyMemoryPipelineTests.test_validate_semantic_recall_cases_rejects_expected_text_outside_memory_texts -v`

Expected: PASS

- [ ] **Step 5: 提交这一小步**

```bash
git add tests/fixtures/semantic_recall/default.json tests/memory_pipeline_verifier/datasets.py tests/test_verify_memory_pipeline.py
git commit -m "test: add semantic recall fixture coverage"
```

### Task 2: 给 verify_memory_pipeline 增加 task 分发

**Files:**
- Modify: `H:/DouYin_llm/tests/memory_pipeline_verifier/runner.py`
- Test: `H:/DouYin_llm/tests/test_verify_memory_pipeline.py`

- [ ] **Step 1: 写失败测试，锁定新的命令参数和兼容行为**

```python
def test_normalize_task_accepts_pipeline_and_semantic_recall(self):
    self.assertEqual(normalize_task("pipeline"), "pipeline")
    self.assertEqual(normalize_task("semantic-recall"), "semantic-recall")
    with self.assertRaises(ValueError):
        normalize_task("unknown")


def test_parse_args_accepts_task_dataset_and_count(self):
    args = parse_args(
        [
            "--mode",
            "internal",
            "--task",
            "semantic-recall",
            "--dataset",
            "tests/fixtures/semantic_recall/default.json",
            "--count",
            "50",
        ]
    )

    self.assertEqual(args.mode, "internal")
    self.assertEqual(args.task, "semantic-recall")
    self.assertEqual(args.dataset, "tests/fixtures/semantic_recall/default.json")
    self.assertEqual(args.count, 50)
```

- [ ] **Step 2: 运行测试，确认 task 相关断言先失败**

Run: `python -m unittest tests.test_verify_memory_pipeline.VerifyMemoryPipelineTests.test_normalize_task_accepts_pipeline_and_semantic_recall tests.test_verify_memory_pipeline.VerifyMemoryPipelineTests.test_parse_args_accepts_task_dataset_and_count -v`

Expected: FAIL，因为 `normalize_task` 尚不存在，`parse_args` 尚不接受 `--task`。

- [ ] **Step 3: 在 runner.py 实现最小 task 分发与参数校验**

```python
def normalize_task(task):
    normalized = str(task or "").strip().lower()
    if normalized not in {"pipeline", "semantic-recall"}:
        raise ValueError(f"unsupported task: {task}")
    return normalized


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Verify the viewer memory extraction pipeline.")
    parser.add_argument("--mode", default="internal", choices=["internal", "e2e"])
    parser.add_argument("--task", default="pipeline", choices=["pipeline", "semantic-recall"])
    parser.add_argument("--count", default=1, type=int)
    parser.add_argument("--dataset", default="")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    mode = normalize_mode(args.mode)
    task = normalize_task(args.task)
    repo_root = Path(__file__).resolve().parents[2]

    if task == "semantic-recall":
        if mode != "internal":
            raise ValueError("semantic-recall only supports internal mode")
        if not args.dataset:
            raise ValueError("--dataset is required for semantic-recall")
        results = run_semantic_recall_verification(args.dataset)
    elif mode == "internal":
        dataset = load_dataset_fixture(args.dataset) if args.dataset else None
        results, _ = run_internal_verification(dataset=dataset, count=args.count)
    else:
        results = run_e2e_verification(repo_root)
```

- [ ] **Step 4: 运行测试，确认参数分发通过且默认行为未破坏**

Run: `python -m unittest tests.test_verify_memory_pipeline.VerifyMemoryPipelineTests.test_normalize_task_accepts_pipeline_and_semantic_recall tests.test_verify_memory_pipeline.VerifyMemoryPipelineTests.test_parse_args_accepts_task_dataset_and_count tests.test_verify_memory_pipeline.VerifyMemoryPipelineTests.test_parse_args_accepts_dataset_and_count -v`

Expected: PASS

- [ ] **Step 5: 提交这一小步**

```bash
git add tests/memory_pipeline_verifier/runner.py tests/test_verify_memory_pipeline.py
git commit -m "feat: add semantic recall task dispatch"
```

### Task 3: 实现 top1/top3 语义召回评测

**Files:**
- Modify: `H:/DouYin_llm/tests/memory_pipeline_verifier/runner.py`
- Modify: `H:/DouYin_llm/tests/test_verify_memory_pipeline.py`

- [ ] **Step 1: 写失败测试，锁定 top1/top3 指标输出**

```python
def test_run_semantic_recall_verification_reports_top1_and_top3(self):
    dataset = [
        {
            "label": "job-overtime",
            "room_id": "room-1",
            "viewer_id": "id:viewer-1",
            "memory_texts": [
                "我在杭州做前端开发，最近连续两周都在加班赶需求。",
                "我周末常去西湖边夜跑，一次差不多十公里。",
                "我皮肤偏干，换季的时候脸上很容易起皮。",
            ],
            "query": "最近写页面经常熬夜赶进度",
            "expected_memory_text": "我在杭州做前端开发，最近连续两周都在加班赶需求。",
        }
    ]

    with patch("tests.memory_pipeline_verifier.runner.load_semantic_recall_fixture", return_value=dataset), patch(
        "tests.memory_pipeline_verifier.runner.EmbeddingService", return_value=MagicMock()
    ), patch("tests.memory_pipeline_verifier.runner.VectorMemory") as vector_cls:
        fake_vector = MagicMock()
        fake_vector.similar_memories.return_value = [
            {"memory_text": "我在杭州做前端开发，最近连续两周都在加班赶需求。"},
            {"memory_text": "我皮肤偏干，换季的时候脸上很容易起皮。"},
        ]
        vector_cls.return_value = fake_vector

        results = run_semantic_recall_verification("tests/fixtures/semantic_recall/default.json")

    self.assertEqual(results[0].name, "dataset")
    self.assertEqual(results[1].name, "index_memories")
    self.assertEqual(results[2].name, "semantic_recall")
    self.assertEqual(
        results[2].details,
        "cases=1 top1=1/1 top3=1/1 top1_rate=1.0000 top3_rate=1.0000",
    )
```

- [ ] **Step 2: 运行测试，确认统计逻辑先失败**

Run: `python -m unittest tests.test_verify_memory_pipeline.VerifyMemoryPipelineTests.test_run_semantic_recall_verification_reports_top1_and_top3 -v`

Expected: FAIL，因为 `run_semantic_recall_verification` 尚不存在或返回格式不对。

- [ ] **Step 3: 在 runner.py 实现最小语义评测执行函数**

```python
def run_semantic_recall_verification(dataset_path):
    print_header("Memory Pipeline Verify: semantic recall")
    results = []
    settings.ensure_dirs()
    cases = load_semantic_recall_fixture(dataset_path)

    record_step(results, "dataset", True, f"path={dataset_path} cases={len(cases)}")

    with tempfile.TemporaryDirectory(prefix="semantic-recall-") as tempdir:
        temp_root = Path(tempdir)
        database_path = temp_root / "live_prompter.db"
        chroma_dir = temp_root / "chroma"
        chroma_dir.mkdir(parents=True, exist_ok=True)

        store = LongTermStore(database_path)
        vector = VectorMemory(chroma_dir, settings=settings, embedding_service=EmbeddingService(settings))

        total_memories = 0
        for index, case in enumerate(cases, start=1):
            room_id = str(case.get("room_id") or DEFAULT_ROOM_ID)
            viewer_id = str(case.get("viewer_id") or f"id:semantic-eval-viewer-{index:03d}")
            for memory_text in case["memory_texts"]:
                store.save_viewer_memory(room_id, viewer_id, memory_text, source_event_id=f"semantic-{index:03d}")
                total_memories += 1

        vector.prime_memory_index(store.list_all_viewer_memories(limit=10000), batch_size=64, force_rebuild=True)
        record_step(results, "index_memories", True, f"cases={len(cases)} memories={total_memories}")

        top1_hits = 0
        top3_hits = 0
        for index, case in enumerate(cases, start=1):
            room_id = str(case.get("room_id") or DEFAULT_ROOM_ID)
            viewer_id = str(case.get("viewer_id") or f"id:semantic-eval-viewer-{index:03d}")
            recalled = vector.similar_memories(case["query"], room_id, viewer_id, limit=3)
            top_texts = [item.get("memory_text", "") for item in recalled]
            expected = case["expected_memory_text"]
            if top_texts[:1] and top_texts[0] == expected:
                top1_hits += 1
            if expected in top_texts:
                top3_hits += 1

        total_cases = len(cases)
        record_step(
            results,
            "semantic_recall",
            top3_hits == total_cases,
            (
                f"cases={total_cases} "
                f"top1={top1_hits}/{total_cases} "
                f"top3={top3_hits}/{total_cases} "
                f"top1_rate={top1_hits / total_cases:.4f} "
                f"top3_rate={top3_hits / total_cases:.4f}"
            ),
        )
        return results
```

- [ ] **Step 4: 增补失败样例覆盖，再跑通过测试**

```python
def test_run_semantic_recall_verification_marks_failure_when_expected_text_misses_top3(self):
    dataset = [
        {
            "label": "missed-case",
            "memory_texts": ["我住在公司附近。", "我早饭只喝美式咖啡。"],
            "query": "家离单位很近",
            "expected_memory_text": "我住在公司附近。",
        }
    ]

    with patch("tests.memory_pipeline_verifier.runner.load_semantic_recall_fixture", return_value=dataset), patch(
        "tests.memory_pipeline_verifier.runner.EmbeddingService", return_value=MagicMock()
    ), patch("tests.memory_pipeline_verifier.runner.VectorMemory") as vector_cls:
        fake_vector = MagicMock()
        fake_vector.similar_memories.return_value = [{"memory_text": "我早饭只喝美式咖啡。"}]
        vector_cls.return_value = fake_vector

        results = run_semantic_recall_verification("tests/fixtures/semantic_recall/default.json")

    self.assertFalse(results[2].ok)
    self.assertEqual(
        results[2].details,
        "cases=1 top1=0/1 top3=0/1 top1_rate=0.0000 top3_rate=0.0000",
    )
```

Run: `python -m unittest tests.test_verify_memory_pipeline.VerifyMemoryPipelineTests.test_run_semantic_recall_verification_reports_top1_and_top3 tests.test_verify_memory_pipeline.VerifyMemoryPipelineTests.test_run_semantic_recall_verification_marks_failure_when_expected_text_misses_top3 -v`

Expected: PASS

- [ ] **Step 5: 提交这一小步**

```bash
git add tests/memory_pipeline_verifier/runner.py tests/test_verify_memory_pipeline.py
git commit -m "feat: add semantic recall evaluation metrics"
```

### Task 4: 完整回归验证并收口

**Files:**
- Modify: `H:/DouYin_llm/tests/memory_pipeline_verifier/runner.py`
- Modify: `H:/DouYin_llm/tests/memory_pipeline_verifier/datasets.py`
- Modify: `H:/DouYin_llm/tests/test_verify_memory_pipeline.py`
- Create: `H:/DouYin_llm/tests/fixtures/semantic_recall/default.json`

- [ ] **Step 1: 跑语义评测相关测试**

Run: `python -m unittest tests.test_verify_memory_pipeline -v`

Expected: PASS，且新增语义评测相关测试全部通过。

- [ ] **Step 2: 跑现有 memory pipeline 关键回归测试**

Run: `python -m unittest tests.test_vector_store tests.test_comment_processing_status tests.test_verify_memory_pipeline tests.test_empty_room_bootstrap -v`

Expected: PASS，无回归失败。

- [ ] **Step 3: 用真实命令跑默认语义评测集**

Run: `python -m tests.memory_pipeline_verifier.runner --mode internal --task semantic-recall --dataset tests/fixtures/semantic_recall/default.json`

Expected: 输出 `dataset`、`index_memories`、`semantic_recall` 三个步骤，并包含 `top1/top3` 指标。

- [ ] **Step 4: 查看工作区，只保留本次改动**

Run: `git status --short`

Expected: 仅出现 `tests/fixtures/semantic_recall/default.json`、`tests/memory_pipeline_verifier/datasets.py`、`tests/memory_pipeline_verifier/runner.py`、`tests/test_verify_memory_pipeline.py` 等本次改动文件；`.qoder/` 与其他既有脏文件不处理。

- [ ] **Step 5: 最终提交**

```bash
git add tests/fixtures/semantic_recall/default.json tests/memory_pipeline_verifier/datasets.py tests/memory_pipeline_verifier/runner.py tests/test_verify_memory_pipeline.py
git commit -m "feat: add semantic recall evaluation dataset"
```
