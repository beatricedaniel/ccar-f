# CCAR-F Labs

A tiny, single-file CLI that coaches you step by step through the four **Preparation
Exercises** in §8 of the exam guide. Pick an exercise and work each step with a teaching
note, progressive hints, a self-check checkpoint, a model approach, and common pitfalls.
Built for preparing the **CCAR-F** (Claude Certified Architect – Foundations) exam.

Unlike its sibling tools (`flashcards`, `tutor`), Labs is **fully offline**: it makes
**no network calls and needs no `ANTHROPIC_API_KEY`**. The coaching content ships as
`guides/*.json`, authored ahead of time by a Claude Code session.

## Requirements

- Python 3 (stdlib only — no `pip install`)
- **No API key, no network** — everything runs locally.

## Run

```bash
python3 tools/labs/labs.py
```

Then follow the prompts:

1. Pick one of the four **exercises** (each label shows its exam **domains**, e.g.
   `Exercise 1 · D1 · D2 · D5 — Build a Multi-Tool Agent with Escalation Logic`).
2. Read the **objective**, **overview**, and step list.
3. Work each **step**: you see the verbatim task and a coach note, then use on-demand
   commands —
   - `h` — next **hint** (progressive; keep pressing for more)
   - `c` — **checkpoint** question, then Enter to reveal the model answer
   - `s` — reveal the **model answer** (solution) directly
   - `p` — common **pitfalls**
   - `l` — reprint the step **list** · `b` — go **back** a step
   - `Enter` (or `n`) — **next** step, after self-marking `[g]ot it / [r]evisit / [s]kip`
   - `q` — **quit** and save the session
4. At the end you get a **wrap-up**, a summary (got-it vs revisit, % understood), and a
   saved session log.

## Model & cost

**Free.** Labs makes no API calls while you study — the guides are pre-authored and
replayed offline, so there is nothing to pay and no key to set.

The only time Claude is involved is if you want to **(re)author or customize a guide**.
Print a ready-to-paste authoring prompt and hand it to your Claude Code session:

```bash
python3 tools/labs/labs.py --print-prompt 3   # prompt for Exercise 3
```

That prompt embeds the verbatim §8 exercise text and the guide schema, and asks Claude
Code to write `guides/3-structured-extraction-pipeline.json`. This runs inside your
Claude Code session (not billed as an API call from this tool), so the study loop itself
stays $0.

## Where things are stored

- `guides/<n>-<slug>.json` — the coaching content for each exercise (objective, per-step
  teaching note, hints, checkpoint, model answer, pitfalls, wrap-up). Edit or regenerate
  these to tune the coaching.
- `logs/<slug>/<YYYYMMDD_HHMMSS>.json` — one file per study session, recording which
  steps you marked *got it* / *revisit* / *skipped*, the list to revisit, and your
  percent-understood.

## Notes

- The four exercises and their verbatim steps live in the `EXERCISES` constant in
  `labs.py` (the source of truth for the menu and `--print-prompt`). The richer coaching
  layer lives in `guides/`.
- On startup the selected guide is validated (required step fields present); a missing or
  malformed guide fails with a friendly message pointing at `--print-prompt`.
- Fully stdlib, no dependencies — there is no API client to swap in and nothing to
  install.
