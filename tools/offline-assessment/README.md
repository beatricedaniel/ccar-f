# CCAR-F Offline Assessment

Drill the certification question bank from the terminal, with the answer options
**shuffled** so the source data's letter bias can't teach you the wrong reflex.

Pick a domain (or all five, weighted like the real exam), a difficulty, and a session
length. Every answer is explained whether you got it right or wrong, and every session
is logged so `--stats` can show progression.

## Requirements

`python3` — stdlib only. No `pip install`, no API key, no network access. Same
constraint as the sibling tools; `labs.py` is the closest relative.

## Run

```sh
python3 tools/offline-assessment/offline-assessment.py
```

| Command | What it does |
|---|---|
| *(no args)* | Start an interactive session (resumes an interrupted one if found) |
| `--stats` | Progression across past sessions: score trend, per-domain, weak task statements, coverage |
| `--sync` | Refresh the question snapshot in `data/` from the MCP server, with a per-file diff |
| `--selftest` | Validate the bank and prove the shuffle is lossless — run this after `--sync` |
| `--seed N` | Fix the seed, reproducing a past session's exact option ordering |
| `--export ID` | Write a markdown report for a logged session (`ID` or `last`) |
| `--help` | Usage |

During a question: `a`/`b`/`c`/`d` to answer, `s` to skip, `q` to quit and save.
After answering: `Enter` for the next one, `w` for the other options' rationales,
`r` for reference links and the matching local cheat sheet.

## Why the shuffle matters

In the upstream bank the correct letter is hard-coded, and the MCP server never
randomises option order — its only shuffles pick *which questions* you get. **B is
correct 185/390 times (47.4 %)**, rising to 59 % in D3 and 11-of-13 for task statement
1.5. Answering B blindly scores ~465/1000. That won't pass (720), but it is more than
enough to inflate practice scores and train a "when unsure, pick B" habit the real exam
will punish.

This tool remaps every question onto freshly shuffled letters, moving `correctAnswer`
and all three `whyWrongMap` rationales through the same bijection. Measured over 78 000
draws (all 390 questions × 200 seeds): **A 25.0 % / B 25.1 % / C 24.8 % / D 25.1 %** —
chance, as it should be. Any single session is a 20-60 item sample, so its own letter
spread will wobble; that is noise, not bias.

## Where things are stored

```
tools/offline-assessment/
  offline-assessment.py   the tool
  data/                   pinned snapshot of the 390-question bank (see data/SOURCE.md)
    manifest.json         sha256 per file, checked by --selftest
  history.jsonl           one line per finished session — drives --stats
  session.json            only while a session is in progress; deleted when it ends
```

Full-length runs (60 questions, all domains) also write a markdown report to
`mock_exams/YYYYMMDD_Offline_Assessment_All_<difficulty>_60q.md`. Shorter drills do
not — use `--export` if you want one.

## Notes

- **Session length is capped by the pool.** No single domain + single difficulty has 40
  questions (largest is D1-medium at 35, smallest D2-easy at 20), so those sizes are
  shown as unavailable with the real pool size. Pick `mix` for longer single-domain runs.
- **All-domain sessions are apportioned by exam weight** (D1 27 / D2 18 / D3 20 / D4 20 /
  D5 15), so 60 questions split 16/11/12/12/9 and the scaled score is directly comparable
  to the 720 pass mark. A domain absent from a session has its weight redistributed.
- **Questions never repeat within a session**, and selection prefers ones you have seen
  least often, spread round-robin across task statements so a session covers the domain
  evenly rather than clustering.
- **Skipping does not reveal the answer** — a skip means "don't teach me this one", and
  it is excluded from the accuracy denominator rather than counted wrong.
- **Interrupted sessions survive.** `session.json` is rewritten after every answer, so a
  Ctrl-C or a closed terminal loses at most one answer; relaunching offers to resume.
- **Colour is minimal** (the verdict and the score only) and switches off automatically
  when output is not a terminal or `NO_COLOR` is set, so piping to a file stays clean.
- Unlike `flashcards.py`, which generates recall cards via the Claude API, this tool only
  ever reads the fixed certification bank — it is completely offline.
