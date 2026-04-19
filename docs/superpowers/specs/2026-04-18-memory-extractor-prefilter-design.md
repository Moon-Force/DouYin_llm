# Memory Extractor Prefilter Design

## Goal

Add a conservative prefilter ahead of viewer-memory extraction so obvious low-value comments do not consume LLM calls or produce noisy auto memories.

## Problem

The current pipeline sends nearly every valid comment through the LLM-backed memory extractor when memory extraction is enabled. This increases token cost and latency even for comments that are clearly not reusable long-term memories, such as greetings, short spam, and simple shopping questions.

## Design

### Scope

This change only targets comments that are clearly not useful as long-term viewer memory:

- low-signal greetings or acknowledgements
- short repetitive spam-like comments
- short transactional shopping questions

It does not attempt to rank all comments or replace the existing LLM decision boundary.

### Placement

The prefilter will live in the composite extraction layer in [backend/services/memory_extractor.py](/H:/DouYin_llm/backend/services/memory_extractor.py), before the LLM extractor is invoked.

This keeps the behavior centralized:

- obvious garbage comments return `[]` immediately
- all other comments keep the current flow: `LLM -> empty/error fallback to rules`

### Filtering Rules

The first version will remain intentionally conservative:

- skip exact low-signal comments such as `来了`, `好的`, `哈哈`, `支持主播`
- skip short comments dominated by repeated filler characters such as repeated `哈/啊/嗯/哦/6`
- skip short transactional comments containing phrases like `多少钱`, `链接`, `怎么买`, `有货吗`

Potential memory-bearing comments like `我在杭州上班`, `我最近一直自己做饭`, or `我家里养了两只猫` must continue through the existing extraction flow.

### Behavioral Impact

- obvious noise no longer calls the LLM extractor
- obvious noise no longer falls through to the rule extractor
- non-obvious comments remain unchanged

### Testing

Add unit tests that prove:

- obvious noise comments do not call either extractor
- pass-through comments still call the LLM extractor
- existing fallback behavior still works for comments that are not prefiltered

## Risks

- If the rules are too broad, valid memory-bearing comments may be dropped before extraction.
- If the rules are too narrow, token savings will be limited.

The initial version therefore prefers precision over recall on the skip path.
