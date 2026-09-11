# CCAR-F Preparation Toolkit

## Purpose

Content and tools the author found useful when preparing for the **CCAR-F** exam —
*Claude Certified Architect – Foundations*, the free, fully-open tier of the Claude
certification tracks.

The exam is scored out of 1000 with a **720 pass mark**; each domain's percent-correct is
weighted and scaled:

| Domain | Weight |
|---|---|
| D1 — Agentic Architecture & Orchestration | 27% |
| D2 — Tool Design & MCP Integration | 18% |
| D3 — Claude Code Configuration & Workflows | 20% |
| D4 — Prompt Engineering & Structured Output | 20% |
| D5 — Context Management & Reliability | 15% |

Everything here is organised by those five domains and their 30 task statements (`<d>.<t>`).

## Structure

```
|- 20260828_Study_Plan_and_Schedule.md  <- day-by-day plan, current standing, go/no-go rule
|- mock_exams                           <- results of mock exams and assessments
|- practice                             <- concrete usage of theoretical concepts
|- README.md
|- theory                               <- source PDFs, one directory per domain
|  |- cheat-sheet                       <- condensed notes, one per task statement
|  |- ...Exam Guide.pdf                 <- the official exam guide
|  |- references.csv                    <- index of every source (reference, subject, url)
|- tools                                <- tools used to prepare for the exam
   |- connectrylab-architect-cert-mcp   <- clone of the connectry-architect MCP server
   |- flashcards                        <- generate & drill flashcards per task statement
   |- labs                              <- coached walkthrough of the Exam Guide exercises
   |- offline-assessment                <- drill the question bank offline, shuffled options
   |- tutor                             <- turn a tutorial page into a guided walkthrough
```

## Tools

Four small CLIs, each a single Python 3 file using **the standard library only** — no
`pip install`. Every tool has its own `README.md` with full options and costs.

| Tool | Run | Needs |
|---|---|---|
| [offline-assessment](tools/offline-assessment/README.md) — drill the pinned 390-question bank with shuffled answer options (`--stats`, `--sync`, `--export`) | `python3 tools/offline-assessment/offline-assessment.py` | nothing — offline & free |
| [labs](tools/labs/README.md) — step-by-step coaching through the four Preparation Exercises in §8 of the exam guide | `python3 tools/labs/labs.py` | nothing — offline & free |
| [flashcards](tools/flashcards/README.md) — turn a task statement's theory PDFs into 10 cards and drill to 100% | `python3 tools/flashcards/flashcards.py` | `ANTHROPIC_API_KEY`, `pdftotext` |
| [tutor](tools/tutor/README.md) — turn a tutorial page into a 6–10 step self-graded walkthrough | `python3 tools/tutor/tutor.py <url-or-file>` | `ANTHROPIC_API_KEY` |

The API-backed tools only spend on *generation* (a new deck or walkthrough); re-studying
what is already cached is free. Model choice is per tool via `FLASHCARDS_MODEL` / `TUTOR_MODEL`.

### The `connectry-architect` MCP server

The online study platform — curriculum, practice questions, timed practice exams, progress
tracking and scaffolded projects — used from Claude Code as `mcp__connectry-architect__*`
tools. `tools/connectrylab-architect-cert-mcp/` is a checkout of its
[upstream repository](https://github.com/Connectry-io/connectrylab-architect-cert-mcp),
kept here for reference; `offline-assessment.py --sync` pulls its question bank down for
offline drilling.
