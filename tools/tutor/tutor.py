#!/usr/bin/env python3
"""Turn a web tutorial into a guided, self-graded walkthrough for CCAR-F prep.

Give it the URL of a tutorial page (e.g. a Claude docs guide) or a local
.html/.md file. The tool reads the page, asks Claude once to break it into a
6-10 step walkthrough (explanation + relevant code + a comprehension question +
a model answer per step, tagged to exam domains D1-D5 where relevant), caches
it, then drills you offline: answer each question, reveal the model answer, and
self-mark until you've understood every step.

Requirements: python3 and an ANTHROPIC_API_KEY. No third-party packages.
Override the model with TUTOR_MODEL.
"""

import hashlib
import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

# --- config ---------------------------------------------------------------
HERE = Path(__file__).resolve().parent
LESSONS = HERE / "lessons"
LOGS = HERE / "logs"

MODEL = os.environ.get("TUTOR_MODEL", "claude-opus-4-8")
API_URL = "https://api.anthropic.com/v1/messages"
MAX_CHARS = 120_000                            # cap tutorial text sent to Claude
MIN_CHARS = 400                                # below this, assume a JS-rendered/empty page
USER_AGENT = "Mozilla/5.0 (compatible; CCAR-F-tutor/1.0)"

DOMAINS = {
    "D1": "Agentic Architecture & Orchestration",
    "D2": "Tool Design & MCP Integration",
    "D3": "Claude Code Configuration & Workflows",
    "D4": "Prompt Engineering & Structured Output",
    "D5": "Context Management & Reliability",
}

LESSON_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["title", "summary", "steps"],
    "properties": {
        "title": {"type": "string"},
        "summary": {"type": "string"},
        "steps": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["title", "explanation", "code", "question", "answer", "domain"],
                "properties": {
                    "title": {"type": "string"},
                    "explanation": {"type": "string"},
                    "code": {"type": "string"},
                    "question": {"type": "string"},
                    "answer": {"type": "string"},
                    "domain": {"anyOf": [{"type": "string", "enum": list(DOMAINS)},
                                         {"type": "null"}]},
                },
            },
        },
    },
}


# --- small helpers --------------------------------------------------------
def die(msg):
    print(f"\n⛔  {msg}", file=sys.stderr)
    sys.exit(1)


def ask(prompt):
    try:
        return input(prompt).strip()
    except (EOFError, KeyboardInterrupt):
        print()
        sys.exit(0)


def pick(prompt, options):
    """options: list of labels. Returns chosen index, or None on quit."""
    for i, label in enumerate(options, 1):
        print(f"  [{i}] {label}")
    while True:
        raw = ask(f"{prompt} (1-{len(options)}, q to quit): ").lower()
        if raw == "q":
            return None
        if raw.isdigit() and 1 <= int(raw) <= len(options):
            return int(raw) - 1
        print("  Please enter a valid number.")


def rule(char="=", width=60):
    print(char * width)


# --- input + fetch --------------------------------------------------------
def is_url(s):
    return s.startswith("http://") or s.startswith("https://")


def slug_for(source):
    """A short, human-readable, filesystem-safe stem for the cache/log files."""
    if is_url(source):
        parts = [p for p in urlparse(source).path.split("/") if p]
        base = parts[-1] if parts else (urlparse(source).netloc or "tutorial")
    else:
        base = Path(source).stem
    base = re.sub(r"[^a-z0-9]+", "-", base.lower()).strip("-")
    return base or "tutorial"


def fetch_source(source):
    """Return (raw_text, is_html). URLs are fetched; local files are read."""
    if is_url(source):
        req = urllib.request.Request(
            source, headers={"User-Agent": USER_AGENT, "Accept": "text/html"}
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                charset = resp.headers.get_content_charset() or "utf-8"
                raw = resp.read().decode(charset, "replace")
        except urllib.error.HTTPError as e:
            die(f"Could not fetch the page (HTTP {e.code}). "
                f"If it needs a login or blocks bots, save it locally and pass the file path.")
        except urllib.error.URLError as e:
            die(f"Network error fetching the page: {e.reason}")
        return raw, True

    path = Path(source).expanduser()
    if not path.is_file():
        die(f"Not a URL and not a readable file: {source}")
    raw = path.read_text(encoding="utf-8", errors="replace")
    is_html = path.suffix.lower() in (".html", ".htm")
    return raw, is_html


# --- html -> readable text (stdlib only) ----------------------------------
class _Extractor(HTMLParser):
    """Pull readable prose + fenced code from an HTML page.

    Drops non-content subtrees (script/style/nav/...). If the page has a <main>
    or <article>, only text inside it is kept — that trims docs chrome. <pre>/
    <code> content is preserved and emitted fenced so Claude sees code vs prose.
    """

    _SKIP = {"script", "style", "noscript", "nav", "header", "footer", "aside", "svg"}
    _BLOCK = {"p", "div", "section", "li", "tr", "h1", "h2", "h3", "h4", "h5", "h6", "br"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []          # (fragment_or_None, in_main); None marks a block break
        self.skip_depth = 0
        self.pre_depth = 0
        self.main_depth = 0
        self.saw_main = False
        self._pre_started = False

    def _emit(self, frag):
        self.parts.append((frag, self.main_depth > 0))

    def handle_starttag(self, tag, attrs):
        if tag in self._SKIP:
            self.skip_depth += 1
        elif tag in ("main", "article"):
            self.main_depth += 1
            self.saw_main = True
        elif tag == "pre":
            self.pre_depth += 1
            self._pre_started = False
        elif tag in self._BLOCK:
            self._emit(None)

    def handle_endtag(self, tag):
        if tag in self._SKIP and self.skip_depth:
            self.skip_depth -= 1
        elif tag in ("main", "article") and self.main_depth:
            self.main_depth -= 1
        elif tag == "pre" and self.pre_depth:
            self.pre_depth -= 1
            if self._pre_started:
                self._emit("\n```\n")
        elif tag in self._BLOCK:
            self._emit(None)

    def handle_data(self, data):
        if self.skip_depth:
            return
        if self.pre_depth:
            if not self._pre_started:
                self._emit("\n```\n")
                self._pre_started = True
            self._emit(data)
            return
        text = data.strip()
        if text:
            self._emit(text + " ")

    def render(self):
        # If the page had a <main>/<article>, keep only fragments inside it
        # (drops nav/sidebar chrome); otherwise fall back to the whole document.
        frags = [(f, in_main) for f, in_main in self.parts]
        if self.saw_main:
            frags = [(f, in_main) for f, in_main in frags if in_main]
        out, blank = [], 0
        for f, _ in frags:
            if f is None:
                blank += 1
                if blank <= 2:
                    out.append("\n")
            else:
                blank = 0
                out.append(f)
        text = "".join(out)
        text = re.sub(r"[ \t]+\n", "\n", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()


def extract_text(raw, is_html):
    if not is_html:
        return raw[:MAX_CHARS]
    parser = _Extractor()
    parser.feed(raw)
    text = parser.render()
    return text[:MAX_CHARS]


# --- claude api -----------------------------------------------------------
def call_claude(prompt):
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        die("ANTHROPIC_API_KEY is not set.\n"
            "   Export it (`export ANTHROPIC_API_KEY=sk-...`) or run `ant auth login`.")
    body = {
        "model": MODEL,
        "max_tokens": 8000,
        "output_config": {"format": {"type": "json_schema", "schema": LESSON_SCHEMA}},
        "messages": [{"role": "user", "content": prompt}],
    }
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    # Identity-linked API keys must declare which workspace the request acts in.
    workspace_id = os.environ.get("ANTHROPIC_WORKSPACE_ID")
    if workspace_id:
        headers["anthropic-workspace-id"] = workspace_id
    req = urllib.request.Request(
        API_URL,
        data=json.dumps(body).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")
        hint = ""
        if "workspace" in detail.lower():
            hint = ("\n   Your API key is identity-linked. Set your workspace id:\n"
                    "   export ANTHROPIC_WORKSPACE_ID=wrkspc_...  (find it in the Console URL)")
        die(f"Claude API error {e.code}: {detail}{hint}")
    except urllib.error.URLError as e:
        die(f"Network error calling Claude API: {e.reason}")
    text = next((b.get("text", "") for b in data.get("content", [])
                 if b.get("type") == "text"), "")
    return json.loads(text)


def generate_lesson(source, text):
    print(f"\nReading the tutorial and building a walkthrough with {MODEL} ...")
    if not text.strip():
        die("No readable text could be extracted from this page.")
    domain_lines = "\n".join(f"   {k} {v}" for k, v in DOMAINS.items())
    prompt = (
        "You are a patient tutor. Turn the tutorial below into a guided walkthrough of "
        "6-10 steps that build understanding of the practice it demonstrates, end to end.\n\n"
        "Each step must have:\n"
        "- title: a short label for the step.\n"
        "- explanation: what is happening and WHY, in plain language. This is the teaching.\n"
        "- code: the relevant code excerpt (verbatim from the tutorial where it helps, else a "
        "concise version). Use an empty string for purely conceptual steps.\n"
        "- question: one focused comprehension question that checks the learner understood the step.\n"
        "- answer: a concise, self-contained model answer to that question.\n"
        "- domain: if the step's concept maps to a CCAR-F exam domain, set this to that code and "
        "name the connection inside the explanation; otherwise null. The domains are:\n"
        f"{domain_lines}\n\n"
        "Also provide an overall title and a one-paragraph summary of what the tutorial teaches "
        "and the end goal. Use ONLY the tutorial text provided below.\n\n"
        f"----- TUTORIAL SOURCE: {source} -----\n{text}"
    )
    lesson = call_claude(prompt)
    steps = lesson.get("steps", [])
    if not steps:
        print("  (model returned no steps; retrying once)")
        lesson = call_claude(prompt)
        steps = lesson.get("steps", [])
    if not steps:
        die("Could not build a walkthrough from this page.")
    return lesson


# --- lesson persistence ---------------------------------------------------
def lesson_path(source):
    h = hashlib.sha1(source.encode("utf-8")).hexdigest()[:8]
    return LESSONS / f"{slug_for(source)}_{h}.json"


def load_or_build_lesson(source):
    path = lesson_path(source)
    if path.exists():
        choice = pick("You've loaded this tutorial before",
                      ["Study the existing walkthrough", "Regenerate (fresh API call)"])
        if choice is None:
            return None
        if choice == 0:
            return json.loads(path.read_text())
    raw, is_html = fetch_source(source)
    text = extract_text(raw, is_html)
    if is_html and len(text) < MIN_CHARS:
        die("Very little readable text was found — this page probably renders its content with "
            "JavaScript, or blocked the request.\n"
            "   Open it in a browser, save it as HTML (or copy the article into a .md file), "
            "and pass that file path instead of the URL.")
    lesson = generate_lesson(source, text)
    lesson.update({
        "source": source,
        "host": urlparse(source).netloc if is_url(source) else "local file",
        "model": MODEL,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
    })
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(lesson, indent=2, ensure_ascii=False))
    print(f"Saved walkthrough to {path.relative_to(HERE)}")
    return lesson


# --- walkthrough session --------------------------------------------------
def _show_step(step, idx, total):
    tag = ""
    dom = step.get("domain")
    if dom in DOMAINS:
        tag = f"   [{dom} — {DOMAINS[dom]}]"
    print()
    rule("-")
    print(f"Step {idx}/{total} — {step['title']}{tag}")
    rule("-")
    print(f"\n{step['explanation']}")
    code = (step.get("code") or "").strip()
    if code:
        print("\n```")
        print(code)
        print("```")
    print(f"\n❓ {step['question']}")


def walkthrough(lesson):
    steps = lesson["steps"]
    print()
    rule()
    print(f"  {lesson.get('title', 'Tutorial walkthrough')}")
    rule()
    summary = (lesson.get("summary") or "").strip()
    if summary:
        print(f"\n{summary}")

    queue = list(steps)
    scope = "all"
    marks = []             # {title, domain, marked} across the final pass
    reviewed = False
    while queue:
        pass_marks = []
        missed = []
        for i, step in enumerate(queue, 1):
            _show_step(step, i, len(queue))
            ans = ask("\n   Your answer (or [Enter] to reveal, q to quit): ").lower()
            if ans == "q":
                return _finalise(lesson, pass_marks or marks, reviewed)
            print(f"\n💡 Model answer: {step['answer']}")
            while True:
                mark = ask("   [c]orrect / [w]rong / q: ").lower()
                if mark in ("c", "w", "q"):
                    break
            if mark == "q":
                return _finalise(lesson, pass_marks or marks, reviewed)
            pass_marks.append({"title": step["title"], "domain": step.get("domain"),
                               "marked": "correct" if mark == "c" else "wrong"})
            if mark == "w":
                missed.append(step)
        marks = pass_marks
        correct = len(queue) - len(missed)
        pct = round(100 * correct / len(queue), 1)
        print()
        rule("-")
        print(f"Report ({scope}): {correct}/{len(queue)} understood ({pct} %)")
        rule("-")

        if not missed:
            print("🎉  You've worked through every step. Nice.")
            break
        choice = pick("What next?",
                      ["Review the steps you marked wrong", "Finish"])
        if choice != 0:
            break
        queue, scope, reviewed = missed, "review", True

    _finalise(lesson, marks, reviewed)


def _finalise(lesson, marks, reviewed):
    if not marks:
        print("No steps marked; nothing to log.")
        return
    correct = sum(1 for m in marks if m["marked"] == "correct")
    pct = round(100 * correct / len(marks), 1)
    ts = datetime.now()
    log = {
        "title": lesson.get("title"),
        "source": lesson.get("source"),
        "model": lesson.get("model"),
        "generated_at": lesson.get("generated_at"),
        "finished_at": ts.isoformat(timespec="seconds"),
        "steps": marks,
        "missed": [m["title"] for m in marks if m["marked"] == "wrong"],
        "pct_correct": pct,
        "reviewed": reviewed,
    }
    slug = slug_for(lesson.get("source", "tutorial"))
    log_dir = LOGS / slug
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"{ts:%Y%m%d_%H%M%S}.json"
    log_file.write_text(json.dumps(log, indent=2, ensure_ascii=False))
    print(f"\nSession log saved to {log_file.relative_to(HERE)}")


# --- main -----------------------------------------------------------------
def main():
    rule()
    print("  CCAR-F Tutor  —  turn a web tutorial into a guided walkthrough")
    print(f"  model: {MODEL}   (override with TUTOR_MODEL)")
    rule()

    source = sys.argv[1].strip() if len(sys.argv) > 1 else ask(
        "\nTutorial URL (or local .html/.md file): ")
    if not source:
        return

    lesson = load_or_build_lesson(source)
    if lesson is None:
        return
    walkthrough(lesson)


if __name__ == "__main__":
    main()
