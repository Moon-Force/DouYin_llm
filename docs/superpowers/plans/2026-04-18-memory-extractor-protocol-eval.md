# Memory Extractor Protocol And Offline Eval Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the LLM memory extractor fail loudly on protocol-level response issues, add general/high-coverage few-shot examples to the prompt, and add a real labeled offline evaluation path for memory extraction quality.

**Architecture:** Keep the transport client responsible for protocol validation and response-shape classification, keep the LLM extractor responsible for prompt construction and schema normalization, and extend the existing verifier so memory-extraction evaluation lives beside semantic-recall evaluation instead of becoming a separate script. Use TDD for each behavior change so protocol regressions and eval-metric regressions are caught close to the edited code.

**Tech Stack:** Python, unittest, existing verifier CLI, JSON fixtures, OpenAI-compatible chat completions over `urllib`

---

### Task 1: Classify protocol failures in the transport client

**Files:**
- Modify: `H:\DouYin_llm\backend\services\memory_extractor_client.py`
- Modify: `H:\DouYin_llm\tests\test_llm_memory_extractor.py`

- [ ] **Step 1: Write failing client tests for protocol classification**

```python
class MemoryExtractorClientProtocolTests(unittest.TestCase):
    def test_infer_json_rejects_reasoning_only_response(self):
        payload = {
            "choices": [
                {
                    "message": {
                        "content": "",
                        "reasoning": "I think the answer is...",
                    },
                    "finish_reason": "stop",
                }
            ]
        }
        client = build_client_with_raw_response(payload)

        with self.assertRaisesRegex(ValueError, "reasoning_only"):
            client.infer_json("system", "user")

    def test_infer_json_rejects_truncated_response(self):
        payload = {
            "choices": [
                {
                    "message": {
                        "content": "",
                    },
                    "finish_reason": "length",
                }
            ]
        }
        client = build_client_with_raw_response(payload)

        with self.assertRaisesRegex(ValueError, "response_truncated"):
            client.infer_json("system", "user")
```

- [ ] **Step 2: Run the targeted tests to verify they fail for the right reason**

Run: `python -m unittest tests.test_llm_memory_extractor.MemoryExtractorClientProtocolTests -v`

Expected: FAIL because the current client only looks at `choices[0].message.content` and does not emit stable protocol classifications.

- [ ] **Step 3: Implement minimal response-shape classification in the client**

```python
choice = response_payload["choices"][0]
message = choice["message"]
finish_reason = str(choice.get("finish_reason", "")).strip().lower()
content = message.get("content")
reasoning = message.get("reasoning")

if finish_reason == "length":
    raise ValueError(f"memory extractor response_truncated for {endpoint}; ...")
if not isinstance(content, str):
    raise ValueError(f"memory extractor invalid_response_shape for {endpoint}; ...")
if not content.strip() and isinstance(reasoning, str) and reasoning.strip():
    raise ValueError(f"memory extractor reasoning_only for {endpoint}; ...")
if not content.strip():
    raise ValueError(f"memory extractor empty_content for {endpoint}; ...")
```

- [ ] **Step 4: Re-run the targeted tests and the full extractor test module**

Run: `python -m unittest tests.test_llm_memory_extractor -v`

Expected: PASS, with the client tests proving `reasoning_only`, `response_truncated`, `empty_content`, and invalid response shape are surfaced explicitly.

- [ ] **Step 5: Commit**

```bash
git add H:\DouYin_llm\backend\services\memory_extractor_client.py H:\DouYin_llm\tests\test_llm_memory_extractor.py
git commit -m "fix: classify memory extractor protocol failures"
```

### Task 2: Add general high-coverage few-shot prompting

**Files:**
- Modify: `H:\DouYin_llm\backend\services\llm_memory_extractor.py`
- Modify: `H:\DouYin_llm\tests\test_llm_memory_extractor.py`

- [ ] **Step 1: Write failing prompt-shape tests for few-shot coverage**

```python
def test_system_prompt_contains_general_high_coverage_examples(self):
    from backend.services.llm_memory_extractor import LLMBackedViewerMemoryExtractor

    prompt = LLMBackedViewerMemoryExtractor._system_prompt()

    self.assertIn("长期偏好", prompt)
    self.assertIn("负向偏好", prompt)
    self.assertIn("短期计划", prompt)
    self.assertIn("低信号", prompt)
    self.assertIn("交易问句", prompt)
```

- [ ] **Step 2: Run the targeted prompt test and verify it fails**

Run: `python -m unittest tests.test_llm_memory_extractor.LLMBackedViewerMemoryExtractorTests.test_system_prompt_contains_general_high_coverage_examples -v`

Expected: FAIL because the current prompt only defines schema and does not include explicit examples.

- [ ] **Step 3: Implement a compact few-shot block in `_system_prompt()`**

```python
examples = [
    {
        "input": "我一直都喝无糖可乐",
        "output": {"should_extract": True, "memory_type": "preference", ...},
    },
    {
        "input": "我一点都不喜欢香菜",
        "output": {"should_extract": True, "polarity": "negative", ...},
    },
    {
        "input": "我在杭州做前端开发",
        "output": {"should_extract": True, "memory_type": "context", ...},
    },
    {
        "input": "今晚下班准备去吃火锅",
        "output": {"should_extract": False, "temporal_scope": "short_term", ...},
    },
    {
        "input": "来了哈哈哈",
        "output": {"should_extract": False, ...},
    },
    {
        "input": "这个多少钱，链接在哪",
        "output": {"should_extract": False, ...},
    },
]
```

- [ ] **Step 4: Re-run prompt/extractor tests**

Run: `python -m unittest tests.test_llm_memory_extractor.LLMBackedViewerMemoryExtractorTests -v`

Expected: PASS, and existing normalization behavior still holds.

- [ ] **Step 5: Commit**

```bash
git add H:\DouYin_llm\backend\services\llm_memory_extractor.py H:\DouYin_llm\tests\test_llm_memory_extractor.py
git commit -m "feat: add few-shot memory extraction prompt"
```

### Task 3: Add a labeled offline evaluation dataset and verifier task

**Files:**
- Create: `H:\DouYin_llm\tests\fixtures\memory_extraction\default.json`
- Create: `H:\DouYin_llm\tests\fixtures\memory_extraction\hard.json`
- Modify: `H:\DouYin_llm\tests\memory_pipeline_verifier\datasets.py`
- Modify: `H:\DouYin_llm\tests\memory_pipeline_verifier\runner.py`
- Modify: `H:\DouYin_llm\tests\test_llm_memory_extractor.py`

- [ ] **Step 1: Write failing verifier tests for the new task and metrics**

```python
def test_normalize_task_accepts_memory_extraction(self):
    from tests.memory_pipeline_verifier.runner import normalize_task

    self.assertEqual(normalize_task("memory-extraction"), "memory-extraction")

def test_load_memory_extraction_fixture_validates_required_fields(self):
    from tests.memory_pipeline_verifier.datasets import validate_memory_extraction_cases

    cases = [
        {
            "label": "negative_preference",
            "content": "我一点都不喜欢香菜",
            "expected": {
                "should_extract": True,
                "memory_text": "不喜欢香菜",
                "memory_type": "preference",
                "polarity": "negative",
                "temporal_scope": "long_term",
            },
        }
    ]

    validate_memory_extraction_cases(cases)
```

- [ ] **Step 2: Run the targeted verifier tests and verify they fail**

Run: `python -m unittest tests.test_llm_memory_extractor.MemoryExtractionVerifierTests -v`

Expected: FAIL because the dataset validator and `memory-extraction` task do not exist yet.

- [ ] **Step 3: Implement fixture validation, task dispatch, and metric reporting**

```python
if normalized not in {"pipeline", "semantic-recall", "memory-extraction"}:
    raise ValueError(f"unsupported task: {task}")

metrics = {
    "case_count": len(cases),
    "json_parse_rate": parsed_count / len(cases),
    "schema_valid_rate": schema_valid_count / len(cases),
    "should_extract_precision": precision,
    "should_extract_recall": recall,
    "should_extract_f1": f1,
    "memory_type_accuracy": memory_type_accuracy,
    "polarity_accuracy": polarity_accuracy,
    "temporal_scope_accuracy": temporal_scope_accuracy,
}
```

- [ ] **Step 4: Add real labeled fixtures with broad coverage**

```json
[
  {
    "label": "long_term_positive_preference",
    "content": "我一直都喝无糖可乐",
    "expected": {
      "should_extract": true,
      "memory_text": "喜欢喝无糖可乐",
      "memory_type": "preference",
      "polarity": "positive",
      "temporal_scope": "long_term"
    }
  }
]
```

Include both `default.json` and `hard.json`, with explicit negative preference, stable background, short-term plan, low-signal, transactional, temporal-boundary, and polarity-confusion samples.

- [ ] **Step 5: Run offline evaluation on both fixtures**

Run: `python -m tests.memory_pipeline_verifier.runner --mode internal --task memory-extraction --dataset tests/fixtures/memory_extraction/default.json`

Run: `python -m tests.memory_pipeline_verifier.runner --mode internal --task memory-extraction --dataset tests/fixtures/memory_extraction/hard.json`

Expected: Both commands complete and print metrics plus a bounded set of failure samples.

- [ ] **Step 6: Commit**

```bash
git add H:\DouYin_llm\tests\fixtures\memory_extraction\default.json H:\DouYin_llm\tests\fixtures\memory_extraction\hard.json H:\DouYin_llm\tests\memory_pipeline_verifier\datasets.py H:\DouYin_llm\tests\memory_pipeline_verifier\runner.py H:\DouYin_llm\tests\test_llm_memory_extractor.py
git commit -m "feat: add offline memory extraction evaluation"
```

### Task 4: Final verification and baseline capture

**Files:**
- Review: `H:\DouYin_llm\backend\services\memory_extractor_client.py`
- Review: `H:\DouYin_llm\backend\services\llm_memory_extractor.py`
- Review: `H:\DouYin_llm\tests\memory_pipeline_verifier\runner.py`
- Review: `H:\DouYin_llm\tests\fixtures\memory_extraction\default.json`
- Review: `H:\DouYin_llm\tests\fixtures\memory_extraction\hard.json`

- [ ] **Step 1: Run the full targeted unit test module**

Run: `python -m unittest tests.test_llm_memory_extractor -v`

Expected: PASS

- [ ] **Step 2: Run the existing semantic recall regression commands**

Run: `python -m tests.memory_pipeline_verifier.runner --mode internal --task semantic-recall --dataset tests/fixtures/semantic_recall/default.json`

Run: `python -m tests.memory_pipeline_verifier.runner --mode internal --task semantic-recall --dataset tests/fixtures/semantic_recall/hard.json`

Expected: PASS, showing the new verifier work did not regress semantic-recall mode.

- [ ] **Step 3: Run the new memory extraction evaluation commands**

Run: `python -m tests.memory_pipeline_verifier.runner --mode internal --task memory-extraction --dataset tests/fixtures/memory_extraction/default.json`

Run: `python -m tests.memory_pipeline_verifier.runner --mode internal --task memory-extraction --dataset tests/fixtures/memory_extraction/hard.json`

Expected: PASS, with printed metrics and visible failure samples for error analysis.

- [ ] **Step 4: Record residual risks in the handoff or final summary**

```text
- Small Ollama models may still hit truncation when prompt length grows.
- The offline dataset measures extraction structure and labels, not retrieval quality.
- If reasoning-only persists for the selected model, switching model or adjusting generation settings remains a follow-up decision.
```
