# PLAN — `labs`

## Context

The CCAR-F study repo has two single-file study CLIs under `tools/`: `flashcards` (drill
cards from theory PDFs to 100 %) and `tutor` (walk a lesson from a URL/PDF). Section **8.
Preparation Exercises** of the exam guide lists four hands-on exercises (each with an
Objective, a Steps list, and a "Domains reinforced" line) that nothing in the repo helped
the user work through. `labs` fills that gap: pick an exercise, get coached step by step.

## Confirmed decisions

- **Fully offline, no API.** Unlike `flashcards`/`tutor`, `labs` makes no network call and
  needs no `ANTHROPIC_API_KEY`. Coaching content is authored **once by a Claude Code
  session** and shipped as `guides/*.json`; the CLI is a pure offline replay engine. This
  makes it the leanest of the three tools (no `urllib`, no `call_claude`).
- **Scope: study / explain only.** The coach teaches, hints, quizzes, and reveals a model
  approach. It does **not** scaffold or write project files (the MCP capstone builder
  covers hands-on builds).
- **Domain numbers in every exercise name**, per request.

## Deliverables

```
tools/labs/
  labs.py                                   # single-file offline CLI (stdlib only; NO urllib/API)
  guides/
    1-multi-tool-agent-escalation.json
    2-claude-code-team-workflow.json
    3-structured-extraction-pipeline.json
    4-multi-agent-research-pipeline.json
  logs/                                      # created on demand, one file per session
  README.md
  PLAN.md
```

## How it works

1. **`EXERCISES` constant** in `labs.py` holds the four §8 exercises verbatim (number,
   slug, title, domains, objective, steps). It is the source of truth for the menu and the
   `--print-prompt` authoring prompt.
2. **Menu** — `pick` one of four labels, each showing the exercise's domains
   (e.g. `Exercise 1 · D1 · D2 · D5 — …`).
3. **Load & validate** `guides/<n>-<slug>.json` (checks each step has the required fields);
   friendly `die` if missing/malformed, pointing at `--print-prompt`.
4. **Overview** — print objective, overview, numbered step list.
5. **Step loop** — for each step show `Step k/N · <domains> — <title>`, the verbatim task,
   and the coach note. On-demand commands: `h` (progressive hint), `c` (checkpoint →
   reveal), `s` (model answer), `p` (pitfalls), `l` (list), `b` (back), `Enter`/`n`
   (self-mark `[g]/[r]/[s]` then advance), `q` (quit).
6. **Wrap-up + log** — print the guide's wrap-up and a summary, then write a timestamped
   session log.

## Key implementation notes / reuse

- Mirrors `flashcards.py` conventions: `die()` / `ask()` / `pick()` copied verbatim, the
  `=`*60 banner, `# --- section ---` banners, emoji accents (`⛔ 💡 ❓ ✅ ⚠️ 🎉`), and the
  `_finalise()` timestamped-log shape.
- Adds a small `wrap()` word-wrapper so long teaching notes read cleanly in a terminal.
- **No API layer at all** — no `urllib`, no `ANTHROPIC_API_KEY`, no cost. Regeneration is
  delegated to a Claude Code session via `labs.py --print-prompt <n>`, which emits an
  authoring prompt (verbatim exercise text + guide schema) — the tool itself never calls
  the API.
- **Guide JSON schema** (per exercise): `exercise, slug, title, domains, objective,
  overview, steps[], wrap_up, authored_by, generated_at`; each step:
  `n, title, domains, task, explain, hints[], checkpoint, model_answer, pitfalls[]`.
- **Log schema**: `exercise, slug, title, domains, started_at, finished_at,
  guide_generated_at, steps[{n,title,domains,marked}], revisit[], pct_understood`.

## Verification

1. `python3 tools/labs/labs.py` → banner + 4 exercises with domain codes; `q` quits
   cleanly at every prompt.
2. Pick each exercise → guide loads/validates; objective/overview/steps print; task text
   matches §8.
3. Exercise every step command (`h/c/s/p/l/b/n`, self-mark) — behaves as specified;
   hints exhaust gracefully.
4. Finish a run → wrap-up + summary print; a log appears under `logs/<slug>/` and parses
   with `python3 -m json.tool`.
5. `python3 tools/labs/labs.py --print-prompt 3` prints a complete authoring prompt with
   the verbatim Exercise 3 text and the schema.
6. `grep -n "urllib\|ANTHROPIC_API_KEY\|api.anthropic" tools/labs/labs.py` returns nothing.
7. Every `guides/*.json` parses with `python3 -m json.tool`.
