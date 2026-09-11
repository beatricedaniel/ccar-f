# Plan: offline assessment CLI for CCAR-F prep

## Context

The `connectry-architect` MCP server's interactive assessment paces one question at a
time through tool round-trips. It is slow for what it delivers: the whole question bank
is static JSON on disk and the server does no generation at runtime (verified — zero
`fetch`/API calls in its `dist/index.js`). 390 questions with scenarios, options,
explanations, per-distractor rebuttals and doc references are simply sitting there.

The second, sharper motivation is a **bias in the source data**. The correct letter is
hard-coded and never randomised — the server's only two `Math.random` calls shuffle
*which questions* are picked (`dist/index.js:1123-1142`, `:2361`), never option order,
and options are always emitted A→D in file order (`:866-870`). B is correct **185/390 =
47.4 %**, and 59 % / 58 % / 54 % in D3 / D4 / D5. Blind-B scores ~465/1000 — not a pass,
but more than enough to inflate practice scores and train a "when unsure, pick B" reflex
the real exam will punish.

So: drill the same bank offline, fast, with the letters shuffled.

## Confirmed decisions

- **Python 3, stdlib only**, single file — matches `flashcards.py` / `tutor.py` / `labs.py`.
- **Vendored snapshot** in `data/` with a sha256 `manifest.json`, refreshed by `--sync`,
  rather than reading the MCP server's copy live. See `data/SOURCE.md` for why.
- **Session length is offered against the real pool**; infeasible sizes are shown as
  unavailable with the pool size rather than hidden, so the numbering stays stable.
- **All-domain sessions apportioned by exam weight** (27/18/20/20/15), so the scaled
  score compares to the 720 pass mark.
- **Logging is a single append-only `history.jsonl`**, one line per session — a
  deliberate deviation from the siblings' `logs/<key>/*.json`, justified below.
- **Minimal colour** (verdict + score), auto-disabled off-TTY or under `NO_COLOR`.
- **Auto-export to `mock_exams/` only for full-length runs** (60q, all domains);
  `--export` forces one otherwise. That directory holds curated artifacts and shouldn't
  silently become a log.

## Deliverables

```
tools/offline-assessment/
  offline-assessment.py   ~880 lines, chmod 755, stdlib only
  README.md               Requirements / Run / Where things are stored / Notes
  PLAN.md                 this file
  data/
    domain-1..5.json      390 questions, 904 KB, verbatim v0.1.13 snapshot
    curriculum.json       domain titles, weights, 30 task-statement titles
    manifest.json         sha256 + byte count + question count per file
    SOURCE.md             provenance, licence, why we snapshot
  history.jsonl           created on first finished session
  session.json            transient, only while a session is in progress
```

## How it works

### 1. Data snapshot (`--sync`)

Reads the first available source — the in-repo MCP checkout, then the global npm install
(override with `OFFLINE_ASSESSMENT_SOURCE`) — validates each file parses, hashes it,
prints `new` / `unchanged` / `UPDATED` per file, and writes `manifest.json`. It is the
only code path that writes into `data/`.

### 2. Three menus

Domain (D1-D5 with weights, or all) → difficulty (easy/medium/hard/mix) → length. The
length menu is computed from the actual pool. This matters because **no single-domain +
single-difficulty pool reaches 40**:

| Pool | easy | medium | hard | mix |
|---|---|---|---|---|
| D1 | 28 | 35 | 28 | 91 |
| D2 | 20 | 25 | 20 | 65 |
| D3 / D4 / D5 | 24 | 30 | 24 | 78 |
| All | 120 | 150 | 120 | 390 |

An `All N` row is appended only when `N` isn't already one of 20/40/60, so D2-easy
(exactly 20) doesn't show a duplicate.

### 3. Shuffle and remap — the correctness-critical part

`present(q, seed)` is keyed on `(seed, question id)`, not on position, so it is
independent of question order and a logged session replays exactly.

`new_of` is a bijection on `{A,B,C,D}` by construction, options are rebuilt by iterating
the fixed `LETTERS` string (a malformed source key raises rather than silently yielding a
3-option question), and `correctAnswer` plus all three `whyWrongMap` keys go through the
**same** mapping. Remapping one without the other would attach a rationale to the wrong
option — the single bug here that would actively mis-teach, so `--selftest` asserts the
correct answer's *text* is invariant and that every rationale still describes the option
it is attached to.

Selection uses a separate stream (`f"{seed}:select"`) so changing selection logic later
never perturbs historical shuffles.

### 4. Selection

`apportion()` is Hare quota + largest remainders, then a clamp-and-redistribute loop for
any domain whose quota exceeds its pool. The clamp is load-bearing for `All 390`
(weight-proportional would ask D1 for 105 of its 91). For 20/40/60 the splits are
5/4/4/4/3, 11/7/8/8/6 and 16/11/12/12/9.

Within a domain, questions are grouped by task statement, sorted by how often history
shows you've seen them (freshest first), then drawn **round-robin** across task
statements so a 20-question D1 session touches all 7 rather than clustering.

Reproducibility note: seed-deterministic *selection* is incompatible with history-aware
freshness, so the seed governs option shuffling only and the question ids are logged
verbatim. Replay uses the logged ids. Don't "fix" this later.

### 5. Session loop

Scenario and question wrap at terminal width (capped at 88), with ``` fenced blocks
passed through verbatim — 12 scenarios contain them. Options use a hanging indent; the
longest in the bank is 452 chars.

The explanation is shown whether the answer was right or wrong. When wrong, the rebuttal
for **the letter actually chosen** is shown inline, then the correct option; the other
two rationales sit behind `w` so the screen stays under a terminal height, and `r` shows
reference URLs plus the matching `theory/cheat-sheet/*/<task>-cheatsheet.md`.

`s` skips (excluded from the denominator, no reveal — skipping shouldn't be a free
answer). `q` finalises whatever was answered, logged with `"completed": false`.
`session.json` is rewritten after every answer, so an abrupt kill loses at most one and
relaunching offers to resume.

### 6. Logging and stats

One JSON object per session appended to `history.jsonl`, carrying per-domain and
per-task tallies plus a compact per-question record (`shown` letter, `picked`, `ok`).
With `seed` + `id` the option texts are reconstructible, so they are never stored.

**Why not the siblings' `logs/<key>/*.json`:** the progression view needs one sequential
read rather than a recursive glob plus N loads; the per-session detail here is ids and
letters rather than human-readable content nobody would open (unlike a flashcards log,
which contains the cards); and the human-readable artifact already exists in
`mock_exams/`. A `logs/` copy would be a third representation of the same session. Every
line carries `"schema": 1` so a future migration is cheap.

`--stats` shows the scaled-score trend with ASCII bars, per-domain first/last/trend,
weakest task statements, and coverage (how much of the 390 you've seen, which task
statements you've never touched).

### 7. Markdown export

Modelled on `20260828_Merged_Results_Report.md` so the two read as one family: headline
result, domain breakdown, task-statement breakdown, then every missed question with the
scenario, your choice, why it was wrong, the correct answer and its explanation.

One hazard worth remembering: a scenario containing ``` inside a fenced block needs a
**4-backtick** outer fence, or the report silently corrupts. Two of the 12 fenced
scenarios hit this.

## Key implementation notes / reuse

- `die()`, `ask()`, `pick()`, `rule()` and `wrap()` are lifted from `labs.py:153-196`;
  `pick()` gained a `disabled` set for the unavailable-size rows.
- `blocks()` (fence-aware wrapping) and `bullet()` (hanging indent) are new and are what
  make long options and code scenarios readable.
- No `argparse` — flags are parsed in a `while argv:` loop like `labs.py --print-prompt`.
- No overlap with `flashcards.py`, which generates recall cards through the Claude API;
  this only ever reads the fixed bank.

## Verification (end-to-end)

`--selftest` is the standing guard and covers, over all 390 questions:

1. **Structure** — 4 non-empty options, `correctAnswer` in ABCD, `whyWrongMap` keyed by
   exactly the three wrong letters, difficulty valid, task statement matching its domain.
2. **Shuffle losslessness** across 8 seeds (3 120 round-trips) — option texts preserved
   as a multiset, the correct answer's text invariant, rationales still attached to the
   options they describe, mapping bijective, output deterministic.
3. **Bias** — the shuffled correct-letter distribution near 25 % per letter, printed
   next to the source's 49/185/106/50.
4. **Selection** — 66 (scope × difficulty × size) combinations return the exact size with
   no repeats.
5. **Integrity** — every `data/*.json` sha256 matches `manifest.json`.

Manual checks performed: greyed-out length rows for D2-easy with no duplicate `All 20`;
a wrong answer showing the rebuttal for the chosen letter; a fenced scenario rendering
with indentation intact; early quit logging `"completed": false` and removing
`session.json`; an interrupted session resuming at the right question with the score
carried; a 60-question all-domain run apportioning 16/11/12/12/9 and exporting a report
whose nested fences escape correctly; `--stats`; `--export last` with filename collision
handling.
