# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repository is

This is **not a conventional software project** — it is a personal study repository for preparing the
**CCAR-F** exam: *Claude Certified Architect – Foundations* (the free, fully-open tier of the
Claude certification tracks). There is no build, lint, or test toolchain, and no dependency
manifest at the root. Most content is PDFs, markdown notes, and JSON data; the interactive part is
the `connectry-architect` MCP server plus four small local CLI study tools under `tools/`
(all Python 3 **stdlib-only** — nothing to `pip install`).

Directory layout:

- `theory/` — source material, one directory per domain (`1-agentic-architecture-orchestration` …
  `5-context-management-reliability`), holding the downloaded docs/lesson PDFs named
  `<d>.<t>-<slug>.pdf`. Also at this level:
  - `theory/cheat-sheet/<domain-dir>/<d>.<t>-cheatsheet.md` — condensed notes, one per task statement
    (all 30 written).
  - `theory/…Exam Guide.pdf` — the official exam guide (the primary source; §8 holds the four
    Preparation Exercises that `tools/labs` coaches).
  - `theory/references.csv` — `reference,subject,url` index of every source, keyed `<d>-<t>`.
- `practice/` — still empty; hands-on work currently lives in the tools' own `logs/` dirs.
- `mock_exams/` — saved exam/assessment results (PDF exports and markdown reports).
- `tools/` — the study tooling (see below).
- `20260828_Study_Plan_and_Schedule.md` (repo root) — the day-by-day study plan and schedule,
  revised in place. **Treat it as the source of truth for what to study next, current standing,
  and the go/no-go rule for booking the real exam** rather than re-deriving a plan.
- `README.md` — one-paragraph overview.

## The exam (target for all work here)

Pass mark is **720/1000 (72%)**. Scoring: each domain's percent-correct is multiplied by its
weight, scaled to 1000; if a domain has no questions in a given exam its weight is redistributed.
The five domains, their weights and task-statement counts (30 task statements total, ids `<d>.<t>`):

| Domain | Weight | Tasks | Sample themes |
|---|---|---|---|
| **D1 — Agentic Architecture & Orchestration** | 27% | 7 | agentic loops & stop reasons, sequential pipelines vs. dynamic decomposition, coordinator/subagent patterns, handoff & enforcement, SDK hooks |
| **D2 — Tool Design & MCP Integration** | 18% | 5 | tool descriptions/boundaries, structured error responses (transient / validation / permission / business), `tool_choice` distribution, MCP servers & resources, built-in tools |
| **D3 — Claude Code Configuration & Workflows** | 20% | 6 | plan mode vs. direct execution, settings & permissions, CLAUDE.md, subagents/skills, team workflows |
| **D4 — Prompt Engineering & Structured Output** | 20% | 6 | few-shot design, JSON-schema/structured output, validation & retry loops, batch processing, multi-pass self-review |
| **D5 — Context Management & Reliability** | 15% | 6 | context windows & compaction, memory/storage, caching, failure modes & recovery |

When helping the user study, tie explanations back to these domains and to the specific task
statement the question bank cites (e.g. "Lesson 2.2: Structured Error Responses"), and point at the
matching `theory/cheat-sheet/…/<d>.<t>-cheatsheet.md`.

## Tooling

### `connectry-architect` MCP server (the online study platform)

Prefer its tools over ad-hoc web research when the user wants to learn, practice, or track progress.
Tool groups (`mcp__connectry-architect__*`):

- **Learn**: `get_curriculum`, `get_section_details`, `get_study_plan`
- **Practice**: `get_practice_question`, `start_assessment` / `submit_answer`
- **Exams**: `start_practice_exam` / `submit_exam_answer`, `get_exam_history`
- **Progress**: `get_dashboard`, `get_progress`, `get_weak_areas`, `reset_progress`
- **Capstone**: `scaffold_project`, `start_capstone_build`, `capstone_build_step`, `capstone_build_status`
- **Misc**: `follow_up`

These tools are deferred — load their schemas with `ToolSearch` (e.g.
`select:mcp__connectry-architect__get_curriculum,...`) before calling. Typical study loop:
`get_weak_areas` / `get_dashboard` to find gaps → `get_section_details` to study → `get_practice_question`
or `start_assessment` to drill → `start_practice_exam` to simulate.

Managed via `claude mcp` (pre-approved in `.claude/settings.local.json`). The server's own source is
checked out at `tools/connectrylab-architect-cert-mcp/` — a **separate clone of the upstream repo**
(`github.com/Connectry-io/connectrylab-architect-cert-mcp`), not this repo's code: don't commit into it
or treat its files as study material.

### Local CLI study tools (`tools/`)

Each is a single Python file with a `README.md` and a `PLAN.md` next to it; read the tool's README
before changing it. All are stdlib-only and write per-session JSON logs under their own `logs/`.

| Tool | Run | Network / cost |
|---|---|---|
| `tools/offline-assessment/offline-assessment.py` | `python3 tools/offline-assessment/offline-assessment.py` | **Offline, free.** Drills the pinned 390-question bank in `data/` with **shuffled options** (the upstream bank is 47% "B"). Flags: `--stats`, `--sync` (refresh snapshot from the MCP server), `--selftest` (run after `--sync`), `--seed`, `--export`. History in `history.jsonl`. |
| `tools/labs/labs.py` | `python3 tools/labs/labs.py` | **Offline, free.** Coaches the four Exam Guide §8 Preparation Exercises from pre-authored `guides/*.json`. `--print-prompt <n>` prints an authoring prompt to (re)generate a guide inside a Claude Code session. |
| `tools/flashcards/flashcards.py` | `python3 tools/flashcards/flashcards.py` | **Claude API** — needs `ANTHROPIC_API_KEY`, `pdftotext` (Poppler). Generates 10 cards per task from that task's theory PDFs; you only pay on generate/reset. Model via `FLASHCARDS_MODEL`. Decks in `decks/D<d>/<d>.<t>.json`. |
| `tools/tutor/tutor.py` | `python3 tools/tutor/tutor.py <url-or-file>` | **Claude API** — needs `ANTHROPIC_API_KEY`. Turns a tutorial page into a 6–10 step self-graded walkthrough tagged by domain. Model via `TUTOR_MODEL`. Walkthroughs cached in `lessons/`. |

Both API tools also honour `ANTHROPIC_WORKSPACE_ID` for identity-linked keys.

## Working in this repo

- **Match the existing naming conventions.** Theory PDFs and cheat sheets are `<d>.<t>-<slug>`;
  mock-exam and assessment exports are `mock_exams/YYYYMMDD_<Name>.md|pdf`
  (`offline-assessment.py` writes full 60-question runs there automatically).
- Study notes go under the matching directory, organized by domain/task statement so material maps
  cleanly onto how the exam is scored. New sources should also be added to `theory/references.csv`.
- When editing a CLI tool, keep the house style: single file, Python 3 stdlib only, no third-party
  dependencies, session logs as JSON, and update the tool's `README.md` alongside the change.
- This **is** a git repository (branch `main`), but commits are not part of the study loop — only
  commit when the user asks.
