# CCAR-F — Offline Assessment · D4 · hard · 23 items

**Date:** 2026-09-04 · **Seed:** 12345 · **Source bank:** connectry-architect-mcp snapshot

## 1. Headline result

| Metric | Value |
|---|---|
| Items | **23** |
| Correct | **21** |
| Raw accuracy | **91.3 %** |

## 2. Domain breakdown

| Domain | Correct | % | Weight |
|---|---|---|---|
| D4 Prompt Engineering & Structured Output | 21/23 | 91.3 % | 20 |

## 3. Task-statement breakdown

| Task | Title | Correct | % |
|---|---|---|---|
| 4.1 | Design prompts with explicit criteria to improve precision | 5/5 | 100.0 % |
| 4.2 | Apply few-shot prompting to improve output consistency | 3/4 | 75.0 % |
| 4.3 | Enforce structured output using tool use and JSON schemas | 4/4 | 100.0 % |
| 4.4 | Implement validation, retry, and feedback loops | 4/4 | 100.0 % |
| 4.5 | Design efficient batch processing strategies | 2/3 | 66.7 % |
| 4.6 | Design multi-instance and multi-pass review architectures | 3/3 | 100.0 % |

## 4. Every missed question

### q-4.2-hard-2 · 4.2 Apply few-shot prompting to improve output consistency · hard

```text
A team builds a multi-step reasoning prompt for legal contract analysis. They add five few-shot examples that each show the correct final answer but omit the intermediate reasoning steps. During evaluation, Claude produces correct answers on simple contracts but fails on complex multi-clause contracts with conflicting obligations.
```

**Question:** What is the MOST precise diagnosis of the failure mode, and what is the correct fix?

**You chose B:** Legal contract analysis requires tool calls; few-shot text examples cannot teach reasoning over structured documents.

> *Why it's wrong:* Few-shot text examples are entirely capable of teaching reasoning patterns over documents; tool calls are appropriate for retrieval or external actions, not for demonstrating analytical reasoning.

**Correct answer A:** The examples demonstrate conclusions without demonstrating the reasoning process; for complex tasks, few-shot examples should show complete chain-of-thought — including intermediate steps — so Claude learns to apply structured reasoning rather than pattern-matching on surface features.

> *Why:* When few-shot examples show only final answers, Claude learns to predict the output distribution but does not learn the intermediate reasoning structure needed for complex inputs. For multi-step or compositional reasoning tasks, examples must include chain-of-thought steps: 'Given clause 3.1 states X and clause 7.2 states Y, there is a conflict... therefore the governing rule is Z.' This teaches Claude the analytical process, not just the answer shape, enabling it to generalize to complex cases that require actual reasoning rather than shallow pattern matching.

**Cheat sheet:** `theory/cheat-sheet/4-prompt-engineering-structured-output/4.2-cheatsheet.md`

**References:** https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/use-examples · https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/chain-of-thought

### q-4.5-hard-1 · 4.5 Design efficient batch processing strategies · hard

```text
A financial services firm runs a nightly pipeline that generates personalized investment insights for 80,000 client accounts. Each insight requires one Claude API call. The pipeline must complete before market open at 9:30 AM EST, giving a 7-hour window starting at 2:30 AM. Regulatory requirements mandate an audit trail linking each response to the originating client account. The firm also wants to minimize API costs.
```

**Question:** Which architectural design best satisfies all constraints: volume, time window, auditability, and cost?

**You chose B:** Use the real-time API with 80 concurrent workers, each processing 1,000 accounts sequentially, and log request/response pairs to an audit database

> *Why it's wrong:* Using the real-time API for 80,000 sequential-within-worker calls incurs full per-token pricing (no 50% discount) and introduces complex concurrency management; it also risks rate limiting across 80 workers.

**Correct answer C:** Submit 8 concurrent batches of 10,000 requests each, using each client's account ID as the `custom_id`; poll with backoff and store result files with account mapping for audit

> *Why:* Splitting 80,000 accounts into 8 batches of 10,000 stays within the per-batch limit. Using the account ID as `custom_id` creates a built-in audit linkage between every response and its originating client. The 50% cost discount applies across all 8 batches. With 8 concurrent batches in a 7-hour window, completion before market open is feasible. Polling with exponential backoff avoids rate limit waste.

**Cheat sheet:** `theory/cheat-sheet/4-prompt-engineering-structured-output/4.5-cheatsheet.md`

**References:** https://docs.anthropic.com/en/api/creating-message-batches · https://docs.anthropic.com/en/api/retrieving-message-batch-results

## 5. Reproduce

`python3 tools/offline-assessment/offline-assessment.py --seed 12345`
