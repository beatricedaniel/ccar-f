# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repository is

This is **not a software project** — it is a personal study repository for preparing the
**CCAR-F** exam: *Claude Certified Architect – Foundations* (the free, fully-open tier of the
Claude certification tracks). There is no build, lint, or test toolchain. The content is prose,
PDFs, and notes; the primary interactive tooling is an MCP server (see below).

Directory layout (from `README.md`; most dirs are placeholders to be filled in over time):

- `theory/` — theoretical content / lesson notes
- `practice/` — concrete applications of theoretical concepts
- `mock_exams/` — saved results of practice exams (e.g. exported PDFs)
- `tools/` — tooling used to prepare for the exam
- `README.md` — one-paragraph overview

## The exam (target for all work here)

Pass mark is **720/1000 (72%)**. Scoring: each domain's percent-correct is multiplied by its
weight, scaled to 1000; if a domain has no questions in a given exam its weight is redistributed.
The five domains (D1–D5), from the mock exam breakdown:

- **D1 — Agentic Architecture & Orchestration** (highest weight, ~27%): task decomposition,
  sequential pipelines vs. dynamic adaptive decomposition, multi-agent coordinator/subagent patterns.
- **D2 — Tool Design & MCP Integration**: structured error responses (four error categories:
  transient / validation / permission / business), MCP tool specification, error context returned to coordinators.
- **D3 — Claude Code Configuration & Workflows**: plan mode vs. direct execution, when to map
  dependencies before committing to an approach.
- **D4 — Prompt Engineering & Structured Output**.
- **D5 — Context Management & Reliability**.

When helping the user study, tie explanations back to these domains and the specific lessons the
question bank cites (e.g. "Lesson 2.2: Structured Error Responses").

## Primary tooling: the `connectry-architect` MCP server

This connected MCP server *is* the study platform. Prefer its tools over ad-hoc web research when
the user wants to learn, practice, or track progress. Tool groups (`mcp__connectry-architect__*`):

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

Managed via `claude mcp` (the only pre-approved Bash command in `.claude/settings.local.json`).

## Working in this repo

- When adding study notes, place them under the matching directory (`theory/`, `practice/`) and
  organize by exam domain (D1–D5) so material maps cleanly onto how the exam is scored.
- Save new mock-exam exports into `mock_exams/` using the existing `YYYYMMDD_...` naming convention.
- This is not a git repository; there is no commit/PR workflow.
