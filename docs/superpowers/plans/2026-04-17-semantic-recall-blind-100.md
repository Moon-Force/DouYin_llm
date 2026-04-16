# Blind 100 Semantic Recall Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 新增一份 100 条混合式盲测脏数据集，并把最小合法性校验接到现有 `verify_memory_pipeline` 测试体系里，保证后续可以直接跑出该数据集的 `top1/top3`。

**Architecture:** 保持现有 `semantic-recall` runner 不变，本次只补充新的 JSON fixture 与最小测试断言。数据文件继续沿用现有 case schema，只额外使用可选 `tags` 字段做人工分析；测试负责约束总量、唯一性、标签完整性和目标记忆归属，命令行验证继续通过既有 `tests.memory_pipeline_verifier.runner` 完成。

**Tech Stack:** Python `unittest`、JSON fixture、现有 `tests.memory_pipeline_verifier.datasets` / `tests.memory_pipeline_verifier.runner`、SQLite、Chroma、项目内 `VectorMemory`

---

## File Structure

- Create: `H:/DouYin_llm/tests/fixtures/semantic_recall/blind_100.json`
  - 100 条盲测脏数据集，保持与现有 `semantic-recall` schema 兼容，并为每条样本补齐 `tags`。
- Modify: `H:/DouYin_llm/tests/test_verify_memory_pipeline.py`
  - 新增盲测集合法性测试，只校验数据规模、唯一性和字段约束，不改 runner 行为。
- Create: `H:/DouYin_llm/docs/superpowers/plans/2026-04-17-semantic-recall-blind-100.md`
  - 本计划文档。

本次实现明确不修改：

- `H:/DouYin_llm/tests/memory_pipeline_verifier/runner.py`
- `H:/DouYin_llm/tests/memory_pipeline_verifier/datasets.py`

本次提交也不要混入当前工作区已有的独立脏改动：

- `H:/DouYin_llm/tests/fixtures/semantic_recall/hard.json`
- `H:/DouYin_llm/tests/test_verify_memory_pipeline.py` 中与 `hard.json` 相关但不属于 blind_100 的既有未提交部分需要先阅读，再在其基础上追加，不要回退。

### Task 1: 先写盲测集约束测试

**Files:**
- Modify: `H:/DouYin_llm/tests/test_verify_memory_pipeline.py`
- Test: `H:/DouYin_llm/tests/test_verify_memory_pipeline.py`

- [ ] **Step 1: 写失败测试，锁定 blind_100 的数据契约**

```python
def test_load_semantic_recall_blind_fixture_has_hundred_tagged_cases(self):
    fixture_path = Path("tests/fixtures/semantic_recall/blind_100.json")

    cases = load_semantic_recall_fixture(fixture_path)

    self.assertGreaterEqual(len(cases), 100)
    self.assertEqual(len({case["label"] for case in cases}), len(cases))
    self.assertTrue(
        all(
            isinstance(case.get("tags"), list)
            and case["tags"]
            and all(str(tag).strip() for tag in case["tags"])
            for case in cases
        )
    )


def test_blind_semantic_recall_fixture_cases_have_dense_memory_choices(self):
    fixture_path = Path("tests/fixtures/semantic_recall/blind_100.json")

    cases = load_semantic_recall_fixture(fixture_path)

    self.assertTrue(all(len(case["memory_texts"]) >= 4 for case in cases))
    self.assertTrue(
        all(case["expected_memory_text"] in case["memory_texts"] for case in cases)
    )
```

- [ ] **Step 2: 运行测试，确认它们先失败**

Run: `python -m unittest tests.test_verify_memory_pipeline.VerifyMemoryPipelineTests.test_load_semantic_recall_blind_fixture_has_hundred_tagged_cases tests.test_verify_memory_pipeline.VerifyMemoryPipelineTests.test_blind_semantic_recall_fixture_cases_have_dense_memory_choices -v`

Expected: FAIL，报 `blind_100.json` 不存在，或样本规模 / 标签字段不满足断言。

- [ ] **Step 3: 提交这一步的测试骨架**

```bash
git add tests/test_verify_memory_pipeline.py
git commit -m "test: add blind recall dataset guards"
```

### Task 2: 新增 100 条混合盲测脏数据集

**Files:**
- Create: `H:/DouYin_llm/tests/fixtures/semantic_recall/blind_100.json`
- Test: `H:/DouYin_llm/tests/test_verify_memory_pipeline.py`

- [ ] **Step 1: 创建 blind_100.json，并按 5 类 x 20 条组织样本**

```json
[
  {
    "label": "blind-001",
    "tags": ["typo"],
    "room_id": "semantic-blind-room",
    "viewer_id": "id:semantic-blind-viewer-001",
    "memory_texts": [
      "我乳糖不耐，喝牛奶就容易肚子不舒服。",
      "我早饭一般只喝美式咖啡，不怎么吃甜的。",
      "我最近在减脂，晚饭尽量不吃米饭和面。",
      "我喜欢吃重辣火锅，但是一点都不吃香菜。"
    ],
    "query": "喝牛乃就容易胃不苏服",
    "expected_memory_text": "我乳糖不耐，喝牛奶就容易肚子不舒服。"
  },
  {
    "label": "blind-021",
    "tags": ["spoken"],
    "room_id": "semantic-blind-room",
    "viewer_id": "id:semantic-blind-viewer-021",
    "memory_texts": [
      "我平时直播都戴隐形眼镜，时间一长眼睛会特别干。",
      "我最近晚上十一点以后基本不喝咖啡，不然睡不着。",
      "我上周刚把工位从浦东搬到张江那边。",
      "我其实特别怕冷，办公室空调一低就得披外套。"
    ],
    "query": "就是那个隐形戴久了眼会干得不行",
    "expected_memory_text": "我平时直播都戴隐形眼镜，时间一长眼睛会特别干。"
  }
]
```

每 20 条的分组要求直接落实到文件内容里：

- `blind-001` 到 `blind-020` 使用 `["typo"]`
- `blind-021` 到 `blind-040` 使用 `["spoken"]`
- `blind-041` 到 `blind-060` 使用 `["fragment"]`
- `blind-061` 到 `blind-080` 使用 `["typo", "spoken", "fragment", "mixed_noise"]`
- `blind-081` 到 `blind-100` 使用 `["distractor"]`

并对每条 case 同时满足下面约束：

- `memory_texts` 至少 4 条
- 至少 2 条干扰记忆与目标记忆语义接近
- `query` 不直接复读 `expected_memory_text`
- `expected_memory_text` 在 `memory_texts` 中唯一成立

- [ ] **Step 2: 运行刚才的两个测试，确认盲测集被测试识别为合法**

Run: `python -m unittest tests.test_verify_memory_pipeline.VerifyMemoryPipelineTests.test_load_semantic_recall_blind_fixture_has_hundred_tagged_cases tests.test_verify_memory_pipeline.VerifyMemoryPipelineTests.test_blind_semantic_recall_fixture_cases_have_dense_memory_choices -v`

Expected: PASS

- [ ] **Step 3: 提交数据集文件**

```bash
git add tests/fixtures/semantic_recall/blind_100.json tests/test_verify_memory_pipeline.py
git commit -m "test: add blind semantic recall dataset"
```

### Task 3: 跑完整验证，确保盲测集直接接入现有评测命令

**Files:**
- Create: `H:/DouYin_llm/tests/fixtures/semantic_recall/blind_100.json`
- Modify: `H:/DouYin_llm/tests/test_verify_memory_pipeline.py`

- [ ] **Step 1: 跑 verify_memory_pipeline 全量单测**

Run: `python -m unittest tests.test_verify_memory_pipeline -v`

Expected: PASS，包括默认数据集、`hard.json` 相关测试和本次新增 blind_100 测试。

- [ ] **Step 2: 用正式命令跑 blind_100 语义召回验证**

Run: `python -u -m tests.memory_pipeline_verifier.runner --mode internal --task semantic-recall --dataset tests/fixtures/semantic_recall/blind_100.json`

Expected: 输出 `dataset`、`index_memories`、`semantic_recall` 三个步骤，并显示 blind_100 的 `top1/top3` 结果。

- [ ] **Step 3: 检查工作区，确认没有把无关脏改动混入本次提交**

Run: `git status --short`

Expected: 只剩与 blind_100 相关的改动；`.qoder/`、旧计划文档和其他既有脏文件不处理，`hard.json` 若仍未纳入本次范围则继续保持独立。

- [ ] **Step 4: 提交最终验证收口**

```bash
git add tests/fixtures/semantic_recall/blind_100.json tests/test_verify_memory_pipeline.py
git commit -m "test: verify blind semantic recall dataset"
```

## Self-Review

- 规格覆盖检查：100 条、混合式、保留现有 schema、补充 `tags`、最小合法性测试、通过现有命令输出 `top1/top3`，都已映射到 Task 1-3。
- 占位符检查：没有使用 `TODO` / `TBD` / “后续再补” 这类占位描述。
- 一致性检查：全程统一使用 `blind_100.json`、`tags`、`semantic-recall`、`top1/top3` 这些现有命名。
