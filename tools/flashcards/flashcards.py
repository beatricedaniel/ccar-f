#!/usr/bin/env python3
"""Anki-style flashcard CLI for CCAR-F exam prep.

Pick a domain (D1-D5) and a task; the tool reads that task's theory PDFs, asks
Claude to write 10 flashcards, and drills you until you score 100 %. Each session
is logged under logs/.

Requirements: python3, `pdftotext` (Poppler) on PATH, and an ANTHROPIC_API_KEY.
No third-party packages. Override the model with FLASHCARDS_MODEL.
"""

import glob
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

# --- config ---------------------------------------------------------------
HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent                      # tools/flashcards -> repo root
THEORY = REPO / "theory"
DECKS = HERE / "decks"
LOGS = HERE / "logs"

MODEL = os.environ.get("FLASHCARDS_MODEL", "claude-opus-4-8")
API_URL = "https://api.anthropic.com/v1/messages"
MAX_CHARS = 120_000                            # cap combined PDF text
NUM_CARDS = 10

TASK_RE = re.compile(r"^(\d+)\.(\d+)-")

CARD_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["cards"],
    "properties": {
        "cards": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["front", "back"],
                "properties": {
                    "front": {"type": "string"},
                    "back": {"type": "string"},
                },
            },
        }
    },
}


# --- small helpers --------------------------------------------------------
def die(msg):
    print(f"\n⛔  {msg}", file=sys.stderr)
    sys.exit(1)


def humanise(slug):
    return slug.replace("-", " ").strip().capitalize()


def ask(prompt):
    try:
        return input(prompt).strip()
    except (EOFError, KeyboardInterrupt):
        print()
        sys.exit(0)


def pick(prompt, options):
    """options: list of (label,). Returns chosen index, or None on quit."""
    for i, label in enumerate(options, 1):
        print(f"  [{i}] {label}")
    while True:
        raw = ask(f"{prompt} (1-{len(options)}, q to quit): ").lower()
        if raw == "q":
            return None
        if raw.isdigit() and 1 <= int(raw) <= len(options):
            return int(raw) - 1
        print("  Please enter a valid number.")


# --- discovery ------------------------------------------------------------
def discover_domains():
    """Return sorted list of (num, folder_path, title)."""
    domains = []
    for p in THEORY.iterdir() if THEORY.is_dir() else []:
        m = re.match(r"^(\d+)-(.+)$", p.name)
        if p.is_dir() and m:
            domains.append((int(m.group(1)), p, humanise(m.group(2))))
    return sorted(domains, key=lambda d: d[0])


def discover_tasks(domain_folder):
    """Return sorted list of (dnum, tnum, label, [pdf paths])."""
    tasks = {}
    for pdf in sorted(domain_folder.glob("*.pdf")):
        m = TASK_RE.match(pdf.name)
        if not m:
            continue
        key = (int(m.group(1)), int(m.group(2)))
        tasks.setdefault(key, []).append(pdf)
    out = []
    for (dnum, tnum), pdfs in sorted(tasks.items()):
        # exam-objective PDF = the one with the longest slug
        def slug(p):
            return TASK_RE.sub("", p.stem)
        objective = max(pdfs, key=lambda p: len(slug(p)))
        label = humanise(slug(objective)) or f"{dnum}.{tnum}"
        out.append((dnum, tnum, label, pdfs))
    return out


# --- pdf extraction -------------------------------------------------------
def extract_task_text(pdfs):
    if not shutil.which("pdftotext"):
        die("`pdftotext` not found on PATH. Install Poppler (e.g. `brew install poppler`).")
    chunks = []
    for pdf in pdfs:
        try:
            res = subprocess.run(
                ["pdftotext", "-layout", str(pdf), "-"],
                capture_output=True, text=True, check=True,
            )
            chunks.append(f"===== {pdf.name} =====\n{res.stdout}")
        except subprocess.CalledProcessError as e:
            print(f"  (warning: could not read {pdf.name}: {e})")
    text = "\n\n".join(chunks)
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
        "output_config": {"format": {"type": "json_schema", "schema": CARD_SCHEMA}},
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


def generate_cards(dnum, tnum, label, pdfs):
    print(f"\nReading {len(pdfs)} PDF(s) and generating {NUM_CARDS} flashcards with {MODEL} ...")
    text = extract_task_text(pdfs)
    if not text.strip():
        die("No text could be extracted from this task's PDFs.")
    prompt = (
        f"You are creating exactly {NUM_CARDS} Anki-style flashcards to test knowledge of the "
        f"CCAR-F (Claude Certified Architect – Foundations) exam.\n"
        f"Domain: D{dnum}. Task {dnum}.{tnum} — {label}.\n\n"
        f"Use ONLY the handout text below. Each card has a focused question (front) and a concise, "
        f"self-contained answer (back). Together the {NUM_CARDS} cards should cover the key concepts, "
        f"patterns, and exam traps a student must know for this task. Return exactly {NUM_CARDS} cards.\n\n"
        f"----- HANDOUT TEXT -----\n{text}"
    )
    result = call_claude(prompt)
    cards = result.get("cards", [])
    if len(cards) != NUM_CARDS:
        print(f"  (model returned {len(cards)} cards; retrying once)")
        result = call_claude(prompt)
        cards = result.get("cards", [])
    if not cards:
        die("Could not generate any flashcards.")
    return cards[:NUM_CARDS]


# --- deck persistence -----------------------------------------------------
def deck_path(dnum, tnum):
    return DECKS / f"D{dnum}" / f"{dnum}.{tnum}.json"


def load_or_build_deck(dnum, tnum, label, pdfs):
    path = deck_path(dnum, tnum)
    if path.exists():
        choice = pick("You've studied this task before",
                      ["Study the existing cards", "Reset (generate 10 new cards)"])
        if choice is None:
            return None
        if choice == 0:
            return json.loads(path.read_text())
    cards = generate_cards(dnum, tnum, label, pdfs)
    deck = {
        "domain": dnum,
        "task": f"{dnum}.{tnum}",
        "label": label,
        "model": MODEL,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "source_pdfs": [p.name for p in pdfs],
        "cards": cards,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(deck, indent=2, ensure_ascii=False))
    print(f"Saved deck to {path.relative_to(REPO)}")
    return deck


# --- study loop -----------------------------------------------------------
def study(deck):
    all_cards = deck["cards"]
    attempts = []          # {attempt, scope, pct_correct, missed:[fronts]}
    queue = list(all_cards)
    scope = "all"
    attempts_to_100 = None
    n = 0
    while queue:
        n += 1
        print(f"\n===== Attempt {n} ({scope}: {len(queue)} card(s)) =====")
        missed = []
        for i, card in enumerate(queue, 1):
            print(f"\nCard {i}/{len(queue)}")
            print(f"Q: {card['front']}")
            resp = ask("   [Enter] to reveal, q to quit: ").lower()
            if resp == "q":
                _finalise(deck, attempts, attempts_to_100)
                return
            print(f"A: {card['back']}")
            while True:
                mark = ask("   [c]orrect / [w]rong / q: ").lower()
                if mark in ("c", "w", "q"):
                    break
            if mark == "q":
                _finalise(deck, attempts, attempts_to_100)
                return
            if mark == "w":
                missed.append(card)
        correct = len(queue) - len(missed)
        pct = round(100 * correct / len(queue), 1)
        attempts.append({
            "attempt": n, "scope": scope, "pct_correct": pct,
            "missed": [c["front"] for c in missed],
        })
        print(f"\n--- Report: {correct}/{len(queue)} correct ({pct} %) ---")

        if not missed:
            print("\U0001f389  100 % — all cards correct!")
            attempts_to_100 = n
            break

        choice = pick("What next?",
                      ["Redo all cards", "Redo only the missed cards"])
        if choice is None:
            break
        if choice == 0:
            queue, scope = list(all_cards), "all"
        else:
            queue, scope = missed, "missed"

    _finalise(deck, attempts, attempts_to_100)


def _finalise(deck, attempts, attempts_to_100):
    if not attempts:
        print("No attempts recorded; nothing to log.")
        return
    dnum = deck["domain"]
    task = deck["task"]
    ts = datetime.now()
    log = {
        "domain": dnum,
        "task": task,
        "label": deck.get("label"),
        "started_at": ts.isoformat(timespec="seconds"),
        "model": deck.get("model"),
        "deck_generated_at": deck.get("generated_at"),
        "cards": deck["cards"],
        "attempts": attempts,
        "attempts_to_100": attempts_to_100,
    }
    log_dir = LOGS / f"D{dnum}" / task
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"{ts:%Y%m%d_%H%M%S}.json"
    log_file.write_text(json.dumps(log, indent=2, ensure_ascii=False))
    print(f"\nSession log saved to {log_file.relative_to(REPO)}")
    if attempts_to_100:
        print(f"Reached 100 % in {attempts_to_100} attempt(s). Nice work!")


# --- main -----------------------------------------------------------------
def main():
    print("=" * 60)
    print("  CCAR-F Flashcards  —  study a domain/task, drill to 100 %")
    print(f"  model: {MODEL}   (override with FLASHCARDS_MODEL)")
    print("=" * 60)

    domains = discover_domains()
    if not domains:
        die(f"No domain folders found under {THEORY}.")

    print("\nDomains:")
    di = pick("Choose a domain", [f"D{n} — {title}" for n, _, title in domains])
    if di is None:
        return
    dnum, folder, _ = domains[di]

    tasks = discover_tasks(folder)
    if not tasks:
        die(f"No task PDFs found in {folder}.")

    print(f"\nTasks in D{dnum}:")
    ti = pick("Choose a task",
              [f"{d}.{t} — {label}" for d, t, label, _ in tasks])
    if ti is None:
        return
    dnum, tnum, label, pdfs = tasks[ti]

    deck = load_or_build_deck(dnum, tnum, label, pdfs)
    if deck is None:
        return
    study(deck)


if __name__ == "__main__":
    main()
