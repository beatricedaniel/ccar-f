# Plan: guided-walkthrough CLI (`tutor`) for CCAR-F prep

## Context

This repo is a study workspace for the **CCAR-F** exam. Alongside the flashcards tool (which drills
PDF theory), the user wanted a way to *understand a web tutorial* — e.g.
`https://platform.claude.com/docs/en/agents-and-tools/tool-use/build-a-tool-using-agent` — rather
than skim it. `tutor.py` takes a tutorial URL (or a local file), turns it into an interactive
**guided walkthrough**, and drills the learner offline.

It deliberately mirrors `tools/flashcards/flashcards.py`: single-file, **Python 3 stdlib only**, one
structured Claude API call to build a cached study asset, then a free offline session with logging.

Confirmed decisions:
- **Session style:** guided walkthrough + comprehension checks (read-and-understand, not hands-on
  rebuild). Code is shown, never run.
- **Depth:** pre-generate once, **self-grade** offline (reveal model answer → mark `[c]/[w]`). One
  API call per tutorial, cached; re-runs are free.
- **Exam binding:** CCAR-F-flavored — each step carries an optional `domain` tag (`D1`–`D5`/null) and
  the explanation names the connection.
- **Runtime:** Python 3, stdlib only. No build step, no third-party deps.

## Deliverables

```
tools/tutor/
  tutor.py     # the CLI (single file, stdlib only)
  README.md    # one-screen usage + env vars + cost note
  lessons/     # generated walkthroughs, reused until regenerated:  lessons/<slug>_<hash>.json
  logs/        # per-session logs:  logs/<slug>/YYYYMMDD_HHMMSS.json
```
`lessons/` and `logs/` are created on demand and are data, not code.

## How it works

### 1. Input + fetch
- Arg 1 = a **URL** (`http…`) or a **local file** (`.html`/`.htm`/`.md`/`.txt`); no arg → prompt.
- URLs fetched via `urllib.request` with a browser-ish `User-Agent`; `HTTPError`/`URLError` →
  friendly `die()`. Local files read directly; `.md`/`.txt` skip HTML extraction.

### 2. HTML → readable text (stdlib `html.parser`)
- `_Extractor(HTMLParser)`: drops `script`/`style`/`noscript`/`nav`/`header`/`footer`/`aside`/`svg`;
  keeps `<pre>`/`<code>` as ```` ``` ````-fenced blocks; if a `<main>`/`<article>` exists, keeps only
  fragments inside it (each fragment is tagged in/out of `main`, filtered in `render()`); collapses
  whitespace; caps at `MAX_CHARS` (120k).
- If HTML yields `< MIN_CHARS` (400) of text → `die()` telling the user the page is likely
  JS-rendered and to pass a saved file instead.

### 3. Generate the walkthrough (one Claude call, structured output)
- `LESSON_SCHEMA`: `{title, summary, steps:[{title, explanation, code, question, answer, domain}]}`
  with `additionalProperties:false` and `domain` an enum of `D1..D5` + `null`.
- Prompt: act as a tutor; produce **6–10 steps** that build understanding end to end; each step =
  what/why explanation + relevant code (verbatim where useful, else concise, else empty) + one
  comprehension question + a model answer; set `domain` when the concept maps to an exam domain and
  name it in the explanation; **use only the provided text**. `max_tokens: 8000`.
- Reuses the flashcards `call_claude()` almost verbatim (`urllib`, `x-api-key`,
  `anthropic-version: 2023-06-01`, optional `ANTHROPIC_WORKSPACE_ID`, structured-output body,
  friendly auth/workspace error hints). Empty `steps` → retry once, else `die()`.
- Cached to `lessons/<slug>_<hash>.json` (`slug` = kebab of URL last segment / file stem; `hash` =
  `sha1(source)[:8]`) with metadata (`source`, `host`, `model`, `generated_at`).

### 4. Walkthrough session (offline, free)
- Print `title` + `summary` once. For each step: header `Step i/N — title` (+ `[Dn — name]` when
  tagged), explanation, fenced code (if any), the question; take the learner's answer or Enter →
  reveal model answer → mark `[c]/[w]/q`.
- After a pass: `correct/N (pct %)` report; if any missed, offer **review the steps you marked
  wrong** (requeues only those) vs **finish**. `q` finalises early.
- `_finalise()` writes `logs/<slug>/YYYYMMDD_HHMMSS.json`: per-step `{title, domain, marked}`,
  `missed` titles, `pct_correct`, `reviewed` flag, and source/model metadata.

## Key implementation notes / reuse
- **No third-party deps:** `urllib`, `json`, `html.parser`, `hashlib`, `re`, `pathlib`, `os`,
  `datetime` only. (Retries/streaming later → swap in the `anthropic` SDK; small, localized change.)
- **Reused from flashcards verbatim/near-verbatim:** `die`/`ask`/`pick` helpers, `call_claude`, the
  cache-or-regenerate flow, and the study/report/redo-missed loop + logging shape.
- **Model override:** `MODEL = os.environ.get("TUTOR_MODEL", "claude-opus-4-8")`.
- File kept ~370 lines; small named helpers only.

## Verification (end-to-end)
1. `python3 tools/tutor/tutor.py <docs-url>` with `ANTHROPIC_API_KEY` set
   (`TUTOR_MODEL=claude-haiku-4-5` for a cheap run) → fetch, extract, one API call, cached lesson
   with `title`/`summary`/6–10 tagged steps.
2. Walk the session: explanation + fenced code + question per step; Enter reveals model answer; end
   report shows `pct %`; review-missed re-drills only wrong steps; a log lands in `logs/<slug>/`.
3. Re-run same source → **study existing vs regenerate** prompt (cache hit = no API call).
4. Failure paths (all covered by offline smoke tests): unset key → clear auth error; JS-rendered/empty
   page → "save the page and pass the file" message; local `.md` → skips HTML extraction.
