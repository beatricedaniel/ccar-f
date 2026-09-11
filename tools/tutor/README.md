# CCAR-F Tutor

A tiny, single-file CLI that turns a **tutorial web page** into a guided,
self-graded **walkthrough** — so you actually understand the practice it
demonstrates instead of skimming it. Built for preparing the **CCAR-F**
(Claude Certified Architect – Foundations) exam; steps are tagged to the exam
domains **D1–D5** where they map.

## Requirements

- Python 3 (stdlib only — no `pip install`)
- `ANTHROPIC_API_KEY` in your environment (or a profile via `ant auth login`)
- `ANTHROPIC_WORKSPACE_ID` **only if** your key is identity-linked — the API then
  requires the workspace id (format `wrkspc_...`, found in the Console URL
  `platform.claude.com/workspaces/<id>/...`). If set, the tool sends it automatically.

## Run

```bash
export ANTHROPIC_API_KEY=sk-ant-...
python3 tools/tutor/tutor.py https://platform.claude.com/docs/en/agents-and-tools/tool-use/build-a-tool-using-agent
```

You can also pass a **local file** instead of a URL (`.html`/`.htm`/`.md`/`.txt`) —
useful when a page renders its content with JavaScript or blocks bots. Save the
page from your browser and point the tool at the file:

```bash
python3 tools/tutor/tutor.py ~/Downloads/build-a-tool-using-agent.html
```

Run with no argument and it will prompt you for the URL or path.

Then follow the prompts:

1. The tool fetches the page, extracts the readable text + code, and (on first
   run) asks Claude **once** to break it into a **6–10 step walkthrough**.
2. For each step you get a plain-language **explanation of what's happening and
   why**, the relevant **code**, a **`[Dn]` tag** when the concept maps to an
   exam domain, and one **comprehension question**.
3. Type your own answer (or just press **Enter**) to reveal the **model answer**,
   then self-mark **[c]orrect** or **[w]rong**.
4. After the pass you get a score and can **review the steps you marked wrong**.
   `q` at any prompt ends the session and writes the log.

## Model & cost

The model is chosen at startup from `TUTOR_MODEL`, defaulting to
`claude-opus-4-8`. Override it per run:

```bash
TUTOR_MODEL=claude-sonnet-5 python3 tools/tutor/tutor.py <url>
```

…or set a standing default (per tool — this is a **separate** variable from the
flashcards tool's `FLASHCARDS_MODEL`, so setting one does not affect the other):

```bash
echo 'export TUTOR_MODEL="claude-sonnet-5"' >> ~/.zshrc && source ~/.zshrc
```

**Which model?** Unlike flashcards (a shallow "facts → Q/A" task where Haiku is
usually plenty), building a walkthrough is a deeper job — it has to *structure*
the tutorial into teaching steps, explain the *why*, and map concepts to the
exam domains. Explanation quality is the whole point, so this is where the
stronger models earn their cost. Since you pay **once** per tutorial and then
re-study for free, that one-time cost is amortized across every later review —
prefer **`claude-opus-4-8`** (default) for tutorials you want to learn deeply,
**`claude-sonnet-5`** as the value sweet spot, and **`claude-haiku-4-5`** only
for a quick throwaway run to see the flow.

**You only pay when a walkthrough is *generated*** — the first time you load a
tutorial, or when you choose **regenerate**. Studying a cached walkthrough (or
re-drilling it) makes no API call and is free. A single generation is one call:
input is the extracted tutorial text (a typical docs page is ~7k tokens; capped
at ~120k chars ≈ ~40k tokens) plus ~2–3k output tokens. Approximate cost per
generation (no prompt caching, so each regenerate pays full input):

| Model | Price (in / out per 1M) | Typical page | Large tutorial |
|---|---|---|---|
| `claude-haiku-4-5` | $1 / $5 | ~$0.02 | ~$0.07 |
| `claude-sonnet-5` | $3 / $15 | ~$0.06 | ~$0.20 |
| `claude-opus-4-8` (default) | $5 / $25 | ~$0.10 | ~$0.33 |

Figures are estimates — token counts vary with page size and the tokenizer.

## Where things are stored

- `lessons/<slug>_<hash>.json` — the generated walkthrough for a tutorial
  (`<slug>` from the URL/file name, `<hash>` from the full source). Reused until
  you regenerate.
- `logs/<slug>/<YYYYMMDD_HHMMSS>.json` — one file per session, with the per-step
  marks (and their domain tags), the steps you missed, and your `pct_correct`.

## Notes

- HTML → text uses the stdlib `html.parser` only: it drops `script`/`style`/
  `nav`/`header`/`footer`/`aside`, keeps `<pre>`/`<code>` as fenced blocks, and
  (when present) restricts to the page's `<main>`/`<article>` to skip site chrome.
- If a page yields almost no text, the tool tells you it's likely JS-rendered and
  to pass a saved file instead — see **Run** above.
- The API call uses stdlib `urllib` with structured JSON output — no dependencies.
  If you later want retries/streaming, swap `call_claude()` for the official
  `anthropic` SDK (`pip install anthropic`); it's a small, localized change.
