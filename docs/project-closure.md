# Project Closure Note

## Status

This project has reached a reasonable stopping point as a research and validation build.

Its core technical direction has already been answered:

- Long-term viewer memory extraction is feasible.
- Semantic recall over viewer memories is feasible.
- Prompt assembly that combines current comment memory and recalled historical memory is feasible.
- Viewer-level recall isolation works and does not leak across `room_id + viewer_id`.

At the same time, the main remaining problem is also clear:

- The memory extraction layer is still the dominant bottleneck.
- The retrieval layer is comparatively stable.

That means the project is no longer blocked by uncertainty. It is now blocked by optimization cost.

## What Was Proved

The current codebase and reports support these conclusions:

1. A new incoming viewer message can be persisted, memory-extracted, semantically recalled, and turned into a suggestion.
2. Recalled memory and current-comment memory can both be inserted into the LLM prompt.
3. Memory merge decisions such as `merge / upgrade / supersede / create` are covered by tests.
4. Viewer memory recall is filtered by both room and viewer identity, so cross-user leakage is prevented.
5. Under larger synthetic benchmarks, semantic recall remains strong while extraction quality degrades first.

## Main Remaining Bottleneck

The highest-value remaining work would all be in extraction quality, not in system architecture:

- Short-term comments are still too likely to be written into long-term memory.
- `memory_text_canonical` is not consistently compact enough.
- Type and polarity boundaries remain noisy under more ambiguous language.
- Extraction quality degrades faster than retrieval quality when benchmark difficulty increases.

This is important because it changes the nature of the project:

- Earlier work was about validating whether the direction works.
- Remaining work would be about repeated prompt tuning, post-processing, dataset iteration, and metric tightening.

That is a new phase of work, not a small extension of the current one.

## Why Closure Is Reasonable

Closing the project now is reasonable for three practical reasons:

1. The core research question has already been answered.
2. The next improvements are incremental and tuning-heavy, not structurally new.
3. The current repository has already accumulated enough tests, reports, and benchmark artifacts to preserve the learning.

In other words, this is a good place to stop a `v0 research prototype`.

## Recommended Final Artifacts To Keep

Keep these as the minimum useful archive:

- `tests/` additions around memory extraction, merge flow, vector recall isolation, and old-viewer message flow
- `scripts/run_yearly_profile_benchmark.py`
- `artifacts/yearly_profile_benchmark/`
- `artifacts/yearly_profile_benchmark_stress/`
- `artifacts/semantic_recall_reports/default.md`

If you want only one summary set to preserve, prioritize:

- `artifacts/yearly_profile_benchmark_stress/final_report_cn.md`
- `artifacts/yearly_profile_benchmark_stress/pressure_curve_cn.md`
- `artifacts/yearly_profile_benchmark_stress/semantic_recall_report.md`
- `artifacts/yearly_profile_benchmark_stress/memory_extraction_report.md`

## Suggested Project Label

The cleanest way to frame this project at closure is:

`Live viewer memory + semantic recall exploration prototype (v0 research build)`

That label is honest about both what worked and what was not finished.

## If The Project Is Ever Restarted

If this project is resumed later, the next phase should start with a narrow goal:

`Improve extraction precision without sacrificing recall`

The most likely first tasks would be:

- tighten short-term filtering
- improve canonicalization
- harden negative preference detection
- expand ambiguous benchmark datasets
- re-run the same benchmark suite before and after each change

If those are not worth funding or time, the project should remain closed.

## Final Recommendation

Treat this repository as complete enough to archive.

Do not continue adding new product features to this branch of work.
If work resumes, treat it as a new phase with a new success metric centered on extraction quality, not general feature growth.
