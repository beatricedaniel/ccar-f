# CCAR-F — Merged Mock Exam Results & Report

**Date compiled:** 2026-08-28
**Sources merged:**
- `20260827_Initial Assessment | CCAR-F.pdf` — 15 items (3 per domain), connectry-architect platform
- `20260825_Practice Exam | Claude Certification Guide.pdf` — 60 items (exam-format), claudecertificationguide.com

The two sittings are combined below as if they were **one 75-item test**, then scored
using the real exam's methodology (domain %-correct × domain weight, scaled to 1,000).

---

## 1. Headline result

| Metric | Value |
|---|---|
| Total items | **75** (15 + 60) |
| Total correct | **48** |
| Raw accuracy | **64.0 %** |
| **Weighted scaled score (exam method)** | **≈ 648 / 1000** |
| Pass mark | 720 / 1000 (72 %) |
| **Verdict** | ❌ **NOT YET PASSING** — gap of ~72 points |

> The 60-item Practice Exam (weighted **609**) is the more realistic predictor because it
> matches the real format (60 items, scenario-based, multi-response). The Initial Assessment
> read 80 % only because it was a short, balanced 3-per-domain sampler. The merged **648** is
> the fairest current estimate of readiness: **close, but below the line, and the shortfall is
> concentrated in two or three domains.**

---

## 2. Domain breakdown (merged)

Weights: D1 27 % · D2 18 % · D3 20 % · D4 20 % · D5 15 %.

| Domain | Initial | Practice | **Merged** | **%** | Weighted contribution | Status |
|---|---|---|---|---|---|---|
| **D1** Agentic Architecture & Orchestration | 2/3 | 11/14 | **13/17** | **76.5 %** | 0.765 × 0.27 = **0.207** | 🟢 On track |
| **D2** Tool Design & MCP Integration | 3/3 | 5/11 | **8/14** | **57.1 %** | 0.571 × 0.18 = **0.103** | 🟠 Below line |
| **D3** Claude Code Config & Workflows | 2/3 | 11/12 | **13/15** | **86.7 %** | 0.867 × 0.20 = **0.173** | 🟢 Strongest |
| **D4** Prompt Engineering & Structured Output | 3/3 | 3/12 | **6/15** | **40.0 %** | 0.400 × 0.20 = **0.080** | 🔴 Critical gap |
| **D5** Context Management & Reliability | 2/3 | 6/11 | **8/14** | **57.1 %** | 0.571 × 0.15 = **0.086** | 🟠 Below line |
| **Total** | 12/15 | 36/60 | **48/75** | **64.0 %** | **≈ 0.648 → 648** | ❌ |

**Where the points are being lost:**
- **D4 alone** is dragging ~120 scaled points below its potential. Lifting D4 from 40 % → 80 %
  adds ~0.08 to the weighted score (**+80 points**) — that single domain almost closes the gap.
- **D2 and D5** each sit at 57 %; bringing both to ~75 % adds roughly **+30–35 points combined.**
- **D1 and D3 are already at/above passing** — maintain, don't over-invest.

---

## 3. Every missed question (merged), by domain

Legend: `IA` = Initial Assessment, `PE` = Practice Exam.

### D4 — Prompt Engineering & Structured Output — 9 misses (the priority)
| # | Task | Sub-topic | What was missed | Correct principle |
|---|---|---|---|---|
| PE-Q14 | 4.3 | enum-fields | Chose post-processing normalisation | Free-text → **enum with `other` + `strict:true`** constrains categorical output at the source |
| PE-Q27 | 4.3 | tool-choice-forcing | Chose prompt-based JSON | **`tool_choice:{type:tool,name:...}`** guarantees the tool is called every time |
| PE-Q40 | 4.3 | nullable-fields | Chose post-hoc validation | Make conditionally-absent fields **nullable** so the model can return `null` instead of fabricating |
| PE-Q52 | 4.3 | nullable-fields | Chose separate per-doc schemas | Same lesson — **one schema, make the 7 sometimes-absent fields optional/nullable** |
| PE-Q37 | 4.4 | detected-patterns | Framed it as "forcing patterns for accuracy" | `detected_patterns` externalises reasoning so **validation can detect inconsistency and feed back targeted errors for self-correction** |
| PE-Q56 | 4.4 | retry-boundary | Chose "remove the requirement" | **Retry fixable format errors; route absent-capability cases (unfamiliar language) to human review** |
| PE-Q42 | 4.2 | few-shot-ambiguity | Chose "one example per variant" | **2–4 targeted examples that show the reasoning** beat exhaustive coverage |
| PE-Q50 | 4.2 | few-shot-coded-content | Chose a static dictionary | **2–4 few-shot examples with reasoning chains** teach pattern recognition that generalises |
| PE-Q30 | 4.6 | self-review-bias | Chose "self-review is fine, 2 % = error rate" | Same-session self-review is **anchored to its own reasoning; use a fresh independent instance** |

### D2 — Tool Design & MCP Integration — 6 misses
| # | Task | Sub-topic | What was missed | Correct principle |
|---|---|---|---|---|
| PE-Q07 | 2.1 | descriptions (Select 3) | Incomplete multi-select | Rename overlapping tools **+** rewrite descriptions (purpose/inputs/outputs/when) **+** audit system prompt for keyword bias |
| PE-Q12 | 2.1 | boundary-descriptions | Chose few-shot examples | Add **boundary descriptions by intent** (execute-a-cancellation vs learn-about-cancellation) |
| PE-Q09 | 2.2 | error-categories | Mixed up the mapping | 503 → **transient/retryable**; restricted journal → **business/not-retryable**; malformed DOI → **validation/retryable-after-fix** |
| PE-Q22 | 2.2 | access-vs-empty | Chose "escalate, never retry" | A `success` + empty array is a **valid empty result** — inform the user, don't retry or escalate |
| PE-Q35 | 2.4 | resources | Chose a `describe_schema` tool | Expose the catalogue as **MCP resources** to remove per-task discovery calls entirely |
| PE-Q38 | 2.4 | config-scope | Chose env-vars for server defs | Team servers → **project `.mcp.json`**; personal → **user `~/.claude.json`**; env vars are for **credentials only** |

### D5 — Context Management & Reliability — 6 misses
| # | Task | Sub-topic | What was missed | Correct principle |
|---|---|---|---|---|
| PE-Q06 | 5.6 | conflict-handling | Chose "flag & escalate to human" | **Annotate both values with source + publication date** and let the consumer interpret |
| PE-Q19 | 5.6 | claim-source-mapping | Chose a database of outputs | Require subagents to emit **structured claim-source mappings** the synthesis agent preserves |
| PE-Q25 | 5.4 | scratchpad | Chose pre-loading whole codebase | **Scratchpad files** persist key findings across context boundaries |
| PE-Q36 | 5.3 | silent-suppression | Chose "validate all non-empty" | **Silent suppression (empty-as-success) is the worst anti-pattern** — return structured error context |
| PE-Q59 | 5.2 | explicit-escalation | Chose "resolve it, it's simple" | An **explicit request for a human is honoured immediately**, regardless of issue simplicity |
| IA-Q13 | 5.1 | lost-in-the-middle | Chose "auto-deletes old turns" | It's an **attention** effect (start/end favoured), not storage; re-pin critical info near the end |

### D1 — Agentic Architecture & Orchestration — 4 misses (otherwise strong)
| # | Task | Sub-topic | What was missed | Correct principle |
|---|---|---|---|---|
| PE-Q10 | 1.5 | posttooluse-normalisation | Chose a validation subagent | **PostToolUse hook** gives 100 % deterministic normalisation at file-write time |
| PE-Q54 | 1.3 | parallel-spawning | Chose a new combined subagent | **Decompose the multi-concern request and route to existing specialists in parallel** |
| PE-Q57 | 1.4 | confidence-routing | Chose "escalate every borderline" | **Tiered confidence routing**: auto-action high-confidence, human-review only the uncertain |
| IA-Q1 | 1.1 | agentic-loop signal | Chose `content[0].type` | **`stop_reason`** (`tool_use` vs `end_turn`) is the canonical loop-control signal |

### D3 — Claude Code Config & Workflows — 2 misses (strongest domain)
| # | Task | Sub-topic | What was missed | Correct principle |
|---|---|---|---|---|
| PE-Q20 | 3.4 | mode-selection | Missed one task's mode | Plan mode for architectural / multi-file-pattern tasks; **direct execution only for clear single-fix scope** |
| IA-Q8 | 3.1 | hierarchy precedence | Chose "project wins" | Resolution is user → project → **directory**; **most-specific (closest) scope wins**, not team-authority |

---

## 4. The pattern behind the misses (most useful takeaway)

Across D4/D2/D5, the wrong answers share a signature. When offered a **deterministic,
structural, source-level fix** versus a **probabilistic downstream patch**, the downstream
patch was chosen. The exam almost always rewards the structural fix:

| When you reach for… | The exam wants… | Seen in |
|---|---|---|
| Post-hoc validation / rejecting bad values | **Schema constraint** (nullable, enum, `strict:true`) | Q14, Q40, Q52 |
| Prompt instruction ("always use the tool") | **API-level guarantee** (`tool_choice` forcing) | Q27, and D4 broadly |
| A validation subagent (still probabilistic) | **A hook** (deterministic interception) | Q10 |
| An exploratory discovery tool | **MCP resources** (catalogue upfront) | Q35 |
| "Flag it and escalate to a human" | **Annotate with provenance** and proceed | Q06, Q19 |
| "Add more examples / more retries" | **2–4 targeted examples** / **respect the retry boundary** | Q42, Q50, Q56 |

**One nuance to hold alongside it — escalation direction:** you *over-escalate* on data
conflicts (Q06: annotate, don't pause for a human) but *under-escalate* on explicit human
requests (Q59: escalate immediately). The rule: escalate on **explicit customer request,
policy gap/silence, or inability to progress** — not on issue difficulty, sentiment, or
self-reported confidence.

Internalising this single heuristic — *prefer the deterministic/structural fix; escalate on
trigger not on difficulty* — would flip the majority of the 24 missed items.
