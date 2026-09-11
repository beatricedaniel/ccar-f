#!/usr/bin/env python3
"""Offline drilling over the CCAR-F certification question bank.

Pick a domain (or all five), a difficulty, and a session length, then work through
shuffled multiple-choice questions with the explanation shown after every answer.
Sessions are appended to history.jsonl so `--stats` can show progression over time.

The question bank is a vendored snapshot of the `connectry-architect` MCP server's
data (390 questions), refreshable with `--sync`. Unlike that server's interactive
assessment, this tool **shuffles the option letters**: in the source bank the correct
answer is hard-coded and B is correct 47.4 % of the time (59 % in D3), which trains a
"when unsure, pick B" reflex the real exam will punish. Shuffling is the point.

Like the sibling `labs.py` this tool is **fully offline**: no network calls, no
ANTHROPIC_API_KEY, no third-party packages.

Requirements: python3 (stdlib only — no third-party packages, no API key).
"""

import hashlib
import json
import os
import random
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

# --- config ---------------------------------------------------------------
HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent                      # tools/offline-assessment -> repo root
DATA = HERE / "data"
HISTORY = HERE / "history.jsonl"
SESSION = HERE / "session.json"
MOCK_EXAMS = REPO / "mock_exams"
CHEATS = REPO / "theory" / "cheat-sheet"

WEIGHTS = {1: 27, 2: 18, 3: 20, 4: 20, 5: 15}  # official exam domain weights
PASS_MARK = 720
SIZES = (20, 40, 60)
LETTERS = "ABCD"
DIFFICULTIES = ("easy", "medium", "hard")
SCHEMA = 1

# --sync reads the first of these that exists (override with OFFLINE_ASSESSMENT_SOURCE)
SOURCE_DIRS = [
    REPO / "tools" / "connectrylab-architect-cert-mcp" / "src" / "data",
    Path("/opt/homebrew/lib/node_modules/connectry-architect-mcp/dist/data"),
]
DATA_FILES = [f"domain-{d}.json" for d in sorted(WEIGHTS)] + ["curriculum.json"]

WIDTH = min(88, max(48, shutil.get_terminal_size((88, 24)).columns - 2))

USAGE = """offline-assessment.py — offline CCAR-F question drilling

  offline-assessment.py              start an interactive session
  offline-assessment.py --stats      progression across past sessions
  offline-assessment.py --sync       refresh the question snapshot in data/
  offline-assessment.py --selftest   validate the bank and the shuffle logic
  offline-assessment.py --seed N     replay a session's option ordering
  offline-assessment.py --export ID  write a markdown report (ID or "last")

Headless mode — one question per invocation, no prompts. Built for driving a
drill through a chat agent (e.g. a Claude Code cloud session, which has no tty):

  offline-assessment.py --start [--domain 1-5|all] [--difficulty easy|medium|hard|mix]
                                [--count N] [--seed N]
  offline-assessment.py --answer a|b|c|d   grade, explain, show the next question
  offline-assessment.py --skip             skip the current question
  offline-assessment.py --status           where the current session stands
  offline-assessment.py --finish           score and log the session now
  offline-assessment.py --discard          throw the unfinished session away
"""


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


def pick(prompt, options, disabled=()):
    """options: list of labels. Returns chosen index, or None on quit."""
    for i, label in enumerate(options, 1):
        print(f"  [{i}] {label}")
    while True:
        raw = ask(f"{prompt} (1-{len(options)}, q to quit): ").lower()
        if raw == "q":
            return None
        if raw.isdigit() and 1 <= int(raw) <= len(options):
            idx = int(raw) - 1
            if idx in disabled:
                print("  That option isn't available for this pool — pick another.")
                continue
            return idx
        print("  Please enter a valid number.")


def rule(char="=", width=60):
    print(char * width)


def wrap(text, indent="   ", width=WIDTH):
    """Lightweight word-wrap so long scenarios read cleanly in a terminal."""
    out, line = [], indent
    for word in text.split():
        if len(line) + len(word) + 1 > width and line.strip():
            out.append(line.rstrip())
            line = indent
        line += word + " "
    if line.strip():
        out.append(line.rstrip())
    return "\n".join(out)


def blocks(text, indent="   ", width=WIDTH):
    """Wrap prose but pass ``` fenced code through verbatim (12 scenarios have it)."""
    out, fenced = [], False
    for raw in text.split("\n"):
        if raw.lstrip().startswith("```"):
            fenced = not fenced
            out.append(indent + raw)
        elif fenced:
            out.append(indent + raw)
        elif raw.strip():
            out.append(wrap(raw, indent, width))
        else:
            out.append("")
    return "\n".join(out)


def bullet(label, text, width=WIDTH):
    """Option line with a hanging indent — the longest option is 452 chars."""
    head = f"   {label} "
    body = wrap(text, indent=" " * len(head), width=width)
    return head + body[len(head):]


COLOUR = sys.stdout.isatty() and not os.environ.get("NO_COLOR")


def paint(text, code):
    return f"\033[{code}m{text}\033[0m" if COLOUR else text


def ok(t):
    return paint(t, "32")


def bad(t):
    return paint(t, "31")


def bold(t):
    return paint(t, "1")


def pct(correct, total):
    return 100.0 * correct / total if total else 0.0


# --- data snapshot --------------------------------------------------------
def source_dir():
    env = os.environ.get("OFFLINE_ASSESSMENT_SOURCE")
    if env:
        return Path(env)
    for d in SOURCE_DIRS:
        if (d / "curriculum.json").exists():
            return d
    die("No connectry data source found. Set OFFLINE_ASSESSMENT_SOURCE to its src/data dir.")


def sync():
    src = source_dir()
    qdirs = {"curriculum.json": src, **{f: src / "questions" for f in DATA_FILES[:-1]}}
    old = {}
    manifest_path = DATA / "manifest.json"
    if manifest_path.exists():
        old = json.loads(manifest_path.read_text()).get("files", {})

    DATA.mkdir(parents=True, exist_ok=True)
    print(f"Syncing from {src}\n")
    files = {}
    for name in DATA_FILES:
        path = qdirs[name] / name
        if not path.exists():
            die(f"Missing source file: {path}")
        blob = path.read_bytes()
        json.loads(blob)                                  # validate before writing
        digest = hashlib.sha256(blob).hexdigest()
        n = len(json.loads(blob).get("questions", [])) if name.startswith("domain") else 0
        was = old.get(name, {}).get("sha256")
        state = "new" if was is None else ("unchanged" if was == digest else "UPDATED")
        print(f"  {name:<18} {state:<10} {len(blob):>7} B" + (f"  {n} questions" if n else ""))
        (DATA / name).write_bytes(blob)
        files[name] = {"sha256": digest, "bytes": len(blob), "questions": n}

    version = "unknown"
    pkg = src.parent.parent / "package.json"
    if pkg.exists():
        version = json.loads(pkg.read_text()).get("version", "unknown")
    manifest = {"source_version": version, "source_dir": str(src),
                "synced_at": datetime.now().isoformat(timespec="seconds"),
                "total_questions": sum(f["questions"] for f in files.values()),
                "files": files}
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"\n{manifest['total_questions']} questions from connectry-architect-mcp "
          f"v{version}.\nSnapshot written to {DATA.relative_to(REPO)}")


def load_bank():
    if not (DATA / "curriculum.json").exists():
        die(f"No snapshot in {DATA.relative_to(REPO)} — run: {Path(__file__).name} --sync")
    bank = []
    for name in DATA_FILES[:-1]:
        bank += json.loads((DATA / name).read_text())["questions"]
    bank.sort(key=lambda q: q["id"])

    cur = json.loads((DATA / "curriculum.json").read_text())
    meta = {}
    for d in cur["domains"]:
        meta[d["id"]] = {"title": d["title"], "weight": d["weight"],
                         "tasks": {t["id"]: t["title"] for t in d["taskStatements"]}}
    return bank, meta


def task_title(meta, task):
    return meta.get(int(task.split(".")[0]), {}).get("tasks", {}).get(task, "")


def cheatsheet(task):
    hits = sorted(CHEATS.glob(f"*/{task}-cheatsheet.md"))
    return hits[0].relative_to(REPO) if hits else None


# --- shuffle & remap ------------------------------------------------------
# Prose in `explanation` / `whyWrongMap` sometimes names an option by its letter
# ("Option B correctly sets ..."). Those letters are written against the source
# bank's ordering, so they must travel through the same bijection as everything
# else — otherwise the shuffle points the student at the wrong option, which is
# worse than not shuffling at all. 25 of the 390 questions contain one.
PROSE_LETTER = re.compile(r"\b(option|answer|choice)(s?)\s+([A-D])\b", re.I)


def remap_prose(text, new_of):
    """Rewrite 'Option B' style references through the shuffle's letter mapping."""
    return PROSE_LETTER.sub(
        lambda m: f"{m.group(1)}{m.group(2)} {new_of[m.group(3).upper()]}", text)


def present(q, seed):
    """Return a display copy of q with options shuffled and every letter remapped.

    Deterministic in (seed, q["id"]) alone — independent of question order, so a
    logged session replays exactly. correctAnswer, every whyWrongMap key, AND any
    letter named in the explanation prose move through the same bijection, so a
    rationale can never drift onto the wrong option (the one bug here that would
    actively mis-teach).
    """
    src = list(LETTERS)
    random.Random(f"{seed}:{q['id']}").shuffle(src)
    new_of = {old: LETTERS[i] for i, old in enumerate(src)}
    return {
        "id": q["id"], "domain": q["domainId"], "task": q["taskStatement"],
        "difficulty": q["difficulty"], "scenario": q["scenario"], "text": q["text"],
        "options": {new_of[old]: q["options"][old] for old in LETTERS},
        "correct": new_of[q["correctAnswer"]],
        "why_wrong": {new_of[old]: remap_prose(why, new_of)
                      for old, why in q["whyWrongMap"].items()},
        "explanation": remap_prose(q["explanation"], new_of),
        "references": q.get("references", []),
        "mapping": new_of,
    }


# --- selection ------------------------------------------------------------
def apportion(total, weights, caps):
    """Largest-remainder split of `total`, clamped to `caps` and redistributed."""
    keys = [k for k in weights if caps.get(k, 0) > 0]
    result = {k: 0 for k in weights}
    pool = total
    while pool > 0 and keys:
        wsum = sum(weights[k] for k in keys)
        if wsum <= 0:
            break
        raw = {k: pool * weights[k] / wsum for k in keys}
        base = {k: int(raw[k]) for k in keys}
        for k in sorted(keys, key=lambda k: -(raw[k] - int(raw[k])))[:pool - sum(base.values())]:
            base[k] += 1
        clamped = []
        for k in keys:
            take = min(base[k], caps[k] - result[k])
            result[k] += take
            pool -= take
            if result[k] >= caps[k]:
                clamped.append(k)
        for k in clamped:
            keys.remove(k)
        if not clamped and pool > 0:
            break                                          # safety net, unreachable
    return result


def draw(pool, k, rng, seen):
    """Round-robin across task statements, freshest questions first."""
    groups = {}
    for q in pool:
        groups.setdefault(q["taskStatement"], []).append(q)
    for g in groups.values():
        g.sort(key=lambda q: (seen.get(q["id"], 0), rng.random()))
    order = sorted(groups)
    rng.shuffle(order)
    out = []
    while len(out) < k:
        progressed = False
        for t in order:
            if groups[t] and len(out) < k:
                out.append(groups[t].pop(0))
                progressed = True
        if not progressed:
            break
    return out


def select(bank, domain, difficulty, n, seed, seen):
    rng = random.Random(f"{seed}:select")
    pool = [q for q in bank
            if (domain is None or q["domainId"] == domain)
            and (difficulty is None or q["difficulty"] == difficulty)]
    if n >= len(pool):                                     # "All N" — no weighting
        picked = list(pool)
    elif domain is None:
        caps = {d: sum(1 for q in pool if q["domainId"] == d) for d in WEIGHTS}
        picked = []
        for d, k in apportion(n, WEIGHTS, caps).items():
            picked += draw([q for q in pool if q["domainId"] == d], k, rng, seen)
    else:
        picked = draw(pool, n, rng, seen)
    rng.shuffle(picked)
    assert len({q["id"] for q in picked}) == len(picked), "duplicate question selected"
    return picked


# --- history --------------------------------------------------------------
def read_history():
    if not HISTORY.exists():
        return []
    out = []
    for line in HISTORY.read_text().splitlines():
        if line.strip():
            out.append(json.loads(line))
    return out


def seen_counts(hist):
    seen = {}
    for s in hist:
        for q in s.get("questions", []):
            seen[q["id"]] = seen.get(q["id"], 0) + 1
    return seen


# --- session --------------------------------------------------------------
def choose(bank, meta):
    """Three menus -> (domain, difficulty, n, pool). None domain/difficulty = all."""
    rule()
    print("  CCAR-F · Offline Assessment")
    rule()
    print("\nWhich domain?")
    doms = sorted(WEIGHTS)
    labels = [f"D{d}  {meta[d]['title']}  ({meta[d]['weight']} %)" for d in doms]
    labels.append("All domains  (weighted like the real exam)")
    i = pick("Domain", labels)
    if i is None:
        sys.exit(0)
    domain = None if i == len(doms) else doms[i]

    print("\nWhich difficulty?")
    i = pick("Difficulty", ["easy", "medium", "hard", "mix  (all three)"])
    if i is None:
        sys.exit(0)
    difficulty = None if i == 3 else DIFFICULTIES[i]

    pool = sum(1 for q in bank
               if (domain is None or q["domainId"] == domain)
               and (difficulty is None or q["difficulty"] == difficulty))
    scope = "All domains" if domain is None else f"D{domain}"
    print(f"\nHow many questions?   (pool: {pool} for {scope} · {difficulty or 'mix'})")
    labels, values, disabled = [], [], set()
    for s in SIZES:
        values.append(s if s <= pool else None)
        if s <= pool:
            labels.append(f"{s} questions")
        else:
            labels.append(f"{s} questions  — unavailable (only {pool} in this pool)")
            disabled.add(len(labels) - 1)
    if pool not in SIZES:
        labels.append(f"All {pool}")
        values.append(pool)
    i = pick("Length", labels, disabled)
    if i is None:
        sys.exit(0)
    return domain, difficulty, values[i], pool


def show_question(p, idx, total, meta, correct_so_far, answered_so_far):
    print()
    rule()
    head = (f"  Q {idx}/{total} · D{p['domain']} {meta[p['domain']]['title']} · "
            f"{p['task']} · {p['difficulty']}")
    print(head[:WIDTH])
    if answered_so_far:
        print(f"  Score so far: {correct_so_far}/{answered_so_far} "
              f"({pct(correct_so_far, answered_so_far):.0f} %)")
    rule()
    print("\nScenario")
    print(blocks(p["scenario"]))
    print("\nQuestion")
    print(blocks(p["text"]))
    print()
    for L in LETTERS:
        print(bullet(f"{L})", p["options"][L]))


def print_verdict(p, choice):
    """Verdict banner, the chosen/correct options, and the explanation."""
    print()
    rule("-")
    if choice == p["correct"]:
        print(ok(f"✅  Correct — {p['correct']}"))
    else:
        print(bad(f"❌  Incorrect — you chose {choice}, the answer is {p['correct']}"))
    rule("-")

    if choice != p["correct"]:
        print("\nYour answer")
        print(bullet(f"{choice})", p["options"][choice]))
        print(wrap(p["why_wrong"][choice], indent="      "))
        print("\nCorrect answer")
        print(bullet(f"{p['correct']})", p["options"][p["correct"]]))

    print("\nWhy")
    print(blocks(p["explanation"]))


def print_others(p, choice):
    """Rationales for the options the student neither picked nor should have."""
    for L in LETTERS:
        if L != p["correct"] and L != choice:
            print()
            print(bullet(f"{L})", p["options"][L]))
            print(wrap(p["why_wrong"][L], indent="      "))


def print_refs(p):
    for url in p["references"]:
        print(f"   {url}")
    sheet = cheatsheet(p["task"])
    if sheet:
        print(f"   Cheat sheet: {sheet}")


def reveal(p, choice, meta):
    """Show the verdict + explanation; returns nothing. Loops on [w]/[r]."""
    print_verdict(p, choice)

    while True:
        nxt = ask("\n   [Enter] next · [w] why the others are wrong · "
                  "[r] references · [q] quit: ").lower()
        if nxt == "w":
            print_others(p, choice)
        elif nxt == "r":
            print()
            print_refs(p)
        elif nxt == "q":
            return "quit"
        else:
            return None


def save_session(state):
    SESSION.write_text(json.dumps(state, indent=2, ensure_ascii=False))


def run(bank, meta, seed, resume=None):
    if resume:
        state = resume
        by_id = {q["id"]: q for q in bank}
        questions = [by_id[i] for i in state["ids"]]
        seed = state["seed"]
    else:
        domain, difficulty, n, _ = choose(bank, meta)
        questions = select(bank, domain, difficulty, n, seed, seen_counts(read_history()))
        state = {"seed": seed, "domain": domain, "difficulty": difficulty,
                 "planned": len(questions), "ids": [q["id"] for q in questions],
                 "answers": [], "started_at": datetime.now().isoformat(timespec="seconds")}
        scope = "All domains" if domain is None else f"D{domain} {meta[domain]['title']}"
        print(f"\n{len(questions)} questions · {scope} · {difficulty or 'mix'}")
        if domain is None:
            split = {}
            for q in questions:
                split[q["domainId"]] = split.get(q["domainId"], 0) + 1
            print("  " + " · ".join(f"D{d} {split.get(d, 0)}" for d in sorted(WEIGHTS)))
        save_session(state)

    answers = state["answers"]
    total = len(questions)
    for idx in range(len(answers), total):
        p = present(questions[idx], seed)
        correct = sum(1 for a in answers if a["ok"])
        attempted = sum(1 for a in answers if not a["skipped"])
        show_question(p, idx + 1, total, meta, correct, attempted)

        while True:
            raw = ask("\n   Your answer — [a/b/c/d] · [s]kip · [q]uit and save: ").upper()
            if raw in ("A", "B", "C", "D", "S", "Q"):
                break
            print("   Enter a, b, c, d, s or q.")

        if raw == "Q":
            break
        if raw == "S":
            answers.append({"id": p["id"], "d": p["domain"], "t": p["task"],
                            "diff": p["difficulty"], "shown": p["correct"],
                            "picked": None, "ok": False, "skipped": True})
            save_session(state)
            continue

        answers.append({"id": p["id"], "d": p["domain"], "t": p["task"],
                        "diff": p["difficulty"], "shown": p["correct"],
                        "picked": raw, "ok": raw == p["correct"], "skipped": False})
        save_session(state)
        if reveal(p, raw, meta) == "quit":
            break

    finalise(state, meta, bank)


# --- headless mode --------------------------------------------------------
# One question per process invocation, state carried in session.json, no prompts
# anywhere. This is what makes the tool usable from an agent that can only run
# non-interactive shell commands (a Claude Code cloud session has no tty).

def load_state():
    if not SESSION.exists():
        die("No session in progress. Start one with --start.")
    return json.loads(SESSION.read_text())


def headless_present(state, bank, idx):
    """Build the display copy of the question at `idx` in the saved session."""
    by_id = {q["id"]: q for q in bank}
    return present(by_id[state["ids"][idx]], state["seed"])


def headless_show_next(state, bank, meta):
    """Print the next unanswered question, or None if the session is complete."""
    idx = len(state["answers"])
    if idx >= len(state["ids"]):
        return None
    p = headless_present(state, bank, idx)
    correct = sum(1 for a in state["answers"] if a["ok"])
    attempted = sum(1 for a in state["answers"] if not a["skipped"])
    show_question(p, idx + 1, len(state["ids"]), meta, correct, attempted)
    print("\n   Reply with:  --answer a|b|c|d   ·   --skip")
    return p


def headless_start(bank, meta, seed, domain, difficulty, count):
    if SESSION.exists():
        s = json.loads(SESSION.read_text())
        die(f"A session is already in progress "
            f"({len(s['answers'])}/{s['planned']} answered). "
            f"Continue it with --answer, or clear it with --finish / --discard.")

    pool = sum(1 for q in bank
               if (domain is None or q["domainId"] == domain)
               and (difficulty is None or q["difficulty"] == difficulty))
    scope = "All domains" if domain is None else f"D{domain}"
    if pool == 0:
        die(f"No questions for {scope} · {difficulty or 'mix'}.")
    if count > pool:
        die(f"Only {pool} questions available for {scope} · {difficulty or 'mix'} "
            f"(asked for {count}). Use --count {pool} or fewer, or --difficulty mix.")

    questions = select(bank, domain, difficulty, count, seed, seen_counts(read_history()))
    state = {"seed": seed, "domain": domain, "difficulty": difficulty,
             "planned": len(questions), "ids": [q["id"] for q in questions],
             "answers": [], "started_at": datetime.now().isoformat(timespec="seconds")}
    save_session(state)

    print(f"\n{len(questions)} questions · {scope} · {difficulty or 'mix'} · seed {seed}")
    if domain is None:
        split = {}
        for q in questions:
            split[q["domainId"]] = split.get(q["domainId"], 0) + 1
        print("  " + " · ".join(f"D{d} {split.get(d, 0)}" for d in sorted(WEIGHTS)))
    headless_show_next(state, bank, meta)
    return 0


def headless_respond(bank, meta, letter):
    """Record an answer (letter) or a skip (letter=None), then show what's next."""
    state = load_state()
    idx = len(state["answers"])
    if idx >= len(state["ids"]):
        die("Every question is already answered. Run --finish to score it.")
    p = headless_present(state, bank, idx)

    if letter is None:
        state["answers"].append({"id": p["id"], "d": p["domain"], "t": p["task"],
                                 "diff": p["difficulty"], "shown": p["correct"],
                                 "picked": None, "ok": False, "skipped": True})
        save_session(state)
        print(f"\n   Skipped Q{idx + 1} — not counted either way.")
    else:
        state["answers"].append({"id": p["id"], "d": p["domain"], "t": p["task"],
                                 "diff": p["difficulty"], "shown": p["correct"],
                                 "picked": letter, "ok": letter == p["correct"],
                                 "skipped": False})
        save_session(state)
        # No follow-up prompt is possible here, so print everything up front:
        # the verdict, the other options' rationales, and the references.
        print_verdict(p, letter)
        print("\nThe other options")
        print_others(p, letter)
        print("\nReferences")
        print_refs(p)

    if headless_show_next(state, bank, meta) is None:
        print("\n   Last question answered — scoring the session.")
        finalise(state, meta, bank)
    return 0


def headless_status(bank, meta):
    state = load_state()
    answers = state["answers"]
    correct = sum(1 for a in answers if a["ok"])
    attempted = sum(1 for a in answers if not a["skipped"])
    scope = "All domains" if state["domain"] is None else f"D{state['domain']}"
    print(f"\nSession · {scope} · {state['difficulty'] or 'mix'} · seed {state['seed']}")
    print(f"  started  {state['started_at'][:16].replace('T', ' ')}")
    print(f"  answered {len(answers)}/{state['planned']}"
          f"  ({len(answers) - attempted} skipped)")
    if attempted:
        print(f"  correct  {correct}/{attempted} ({pct(correct, attempted):.0f} %)")
    if len(answers) < state["planned"]:
        headless_show_next(state, bank, meta)
    else:
        print("\n  All questions answered — run --finish to score and log it.")
    return 0


def headless_finish(bank, meta):
    state = load_state()
    if not state["answers"]:
        SESSION.unlink()
        print("Nothing answered; session discarded.")
        return 0
    finalise(state, meta, bank)
    return 0


def headless_discard():
    if not SESSION.exists():
        print("No session in progress.")
        return 0
    s = json.loads(SESSION.read_text())
    SESSION.unlink()
    print(f"Discarded an unfinished session ({len(s['answers'])}/{s['planned']} answered).")
    return 0


# --- results & logging ----------------------------------------------------
def tally(answers):
    doms, tasks = {}, {}
    for a in answers:
        if a["skipped"]:
            continue
        for store, key in ((doms, a["d"]), (tasks, a["t"])):
            e = store.setdefault(key, {"n": 0, "correct": 0})
            e["n"] += 1
            e["correct"] += 1 if a["ok"] else 0
    return doms, tasks


def scaled_score(doms):
    """Weighted score out of 1000; absent domains have their weight redistributed."""
    present_w = sum(WEIGHTS[d] for d in doms if doms[d]["n"])
    if not present_w:
        return 0
    got = sum(WEIGHTS[d] * doms[d]["correct"] / doms[d]["n"] for d in doms if doms[d]["n"])
    return round(1000 * got / present_w)


def finalise(state, meta, bank):
    answers = state["answers"]
    if not answers:
        print("\nNothing answered; nothing logged.")
        SESSION.unlink(missing_ok=True)
        return

    attempted = [a for a in answers if not a["skipped"]]
    skipped = len(answers) - len(attempted)
    correct = sum(1 for a in attempted if a["ok"])
    doms, tasks = tally(answers)
    completed = len(answers) == state["planned"]
    scope = "All domains" if state["domain"] is None else f"D{state['domain']}"

    print()
    rule()
    title = "Session complete" if completed else \
        f"Session ended early — {len(answers)}/{state['planned']} answered"
    print(f"  {title} — {scope} · {state['difficulty'] or 'mix'}")
    rule()
    print(f"\n  Correct   {correct}/{len(attempted)}   "
          f"({pct(correct, len(attempted)):.1f} %)")
    if skipped:
        print(f"  Skipped   {skipped}")

    score = None
    if state["domain"] is None:
        score = scaled_score(doms)
        verdict = ok("PASS") if score >= PASS_MARK else bad("below pass mark")
        print(f"\n  {bold('Weighted scaled score')}   {bold(str(score))} / 1000    "
              f"{verdict}  (mark {PASS_MARK})")
        print(f"\n  {'Domain':<26}{'Correct':>9}{'%':>8}{'Weight':>8}")
        print("  " + "-" * 51)
        for d in sorted(doms):
            e = doms[d]
            print(f"  D{d} {meta[d]['title'][:22]:<23}{e['correct']:>4}/{e['n']:<4}"
                  f"{pct(e['correct'], e['n']):>7.1f}{WEIGHTS[d]:>8}")

    weak = sorted(((t, e) for t, e in tasks.items() if e["n"] >= 2),
                  key=lambda kv: pct(kv[1]["correct"], kv[1]["n"]))[:5]
    if weak:
        print("\n  Weakest task statements (2+ attempted)")
        for t, e in weak:
            print(f"    {t}  {task_title(meta, t)[:44]:<46}{e['correct']}/{e['n']}"
                  f"{pct(e['correct'], e['n']):>6.0f} %")

    hist_line = {
        "schema": SCHEMA, "session_id": datetime.now().strftime("%Y%m%d_%H%M%S"),
        "started_at": state["started_at"],
        "finished_at": datetime.now().isoformat(timespec="seconds"),
        "seed": state["seed"], "mode": "all" if state["domain"] is None else "domain",
        "domain": state["domain"], "difficulty": state["difficulty"],
        "planned": state["planned"], "answered": len(answers), "skipped": skipped,
        "completed": completed, "correct": correct,
        "pct": round(pct(correct, len(attempted)), 1),
        "scaled_score": score, "passed": (score >= PASS_MARK) if score else None,
        "domains": {str(d): doms[d] for d in sorted(doms)}, "tasks": tasks,
        "questions": answers,
    }
    with open(HISTORY, "a") as f:
        f.write(json.dumps(hist_line, ensure_ascii=False) + "\n")
    SESSION.unlink(missing_ok=True)
    print(f"\n  Session logged to {HISTORY.relative_to(REPO)}")

    full = completed and state["domain"] is None and state["planned"] >= 60
    if full:
        path = export(hist_line, meta, bank)
        print(f"  Report saved to {path.relative_to(REPO)}")
    print(f"  Replay this ordering:  {Path(__file__).name} --seed {state['seed']}")


# --- markdown export ------------------------------------------------------
def export(s, meta, bank):
    by_id = {q["id"]: q for q in bank}
    scope = "All" if s["domain"] is None else f"D{s['domain']}"
    stamp = s["session_id"][:8]
    base = f"{stamp}_Offline_Assessment_{scope}_{s['difficulty'] or 'mix'}_{s['answered']}q"
    path = MOCK_EXAMS / f"{base}.md"
    n = 2
    while path.exists():
        path = MOCK_EXAMS / f"{base}_{n}.md"
        n += 1

    attempted = [a for a in s["questions"] if not a["skipped"]]
    L = [f"# CCAR-F — Offline Assessment · {scope} · {s['difficulty'] or 'mix'} · "
         f"{s['answered']} items", "",
         f"**Date:** {s['finished_at'][:10]} · **Seed:** {s['seed']} · "
         f"**Source bank:** connectry-architect-mcp snapshot", "",
         "## 1. Headline result", "",
         "| Metric | Value |", "|---|---|",
         f"| Items | **{len(attempted)}** |",
         f"| Correct | **{s['correct']}** |",
         f"| Raw accuracy | **{s['pct']} %** |"]
    if s["scaled_score"] is not None:
        verdict = "✅ **PASSING**" if s["passed"] else "❌ **below pass mark**"
        L += [f"| **Weighted scaled score** | **{s['scaled_score']} / 1000** |",
              f"| Pass mark | {PASS_MARK} / 1000 |", f"| Verdict | {verdict} |"]
    L += ["", "## 2. Domain breakdown", "",
          "| Domain | Correct | % | Weight |", "|---|---|---|---|"]
    for d, e in s["domains"].items():
        L.append(f"| D{d} {meta[int(d)]['title']} | {e['correct']}/{e['n']} | "
                 f"{pct(e['correct'], e['n']):.1f} % | {WEIGHTS[int(d)]} |")

    L += ["", "## 3. Task-statement breakdown", "",
          "| Task | Title | Correct | % |", "|---|---|---|---|"]
    for t in sorted(s["tasks"]):
        e = s["tasks"][t]
        L.append(f"| {t} | {task_title(meta, t)} | {e['correct']}/{e['n']} | "
                 f"{pct(e['correct'], e['n']):.1f} % |")

    L += ["", "## 4. Every missed question", ""]
    missed = [a for a in attempted if not a["ok"]]
    if not missed:
        L.append("None — every attempted question was answered correctly.")
    for a in missed:
        q = by_id[a["id"]]
        p = present(q, s["seed"])
        L += [f"### {a['id']} · {a['t']} {task_title(meta, a['t'])} · {a['diff']}", ""]
        # A scenario containing ``` needs a 4-backtick outer fence.
        fence = "````" if "```" in q["scenario"] else "```"
        L += [f"{fence}text", q["scenario"], fence, "",
              f"**Question:** {q['text']}", "",
              f"**You chose {a['picked']}:** {p['options'][a['picked']]}", "",
              f"> *Why it's wrong:* {p['why_wrong'][a['picked']]}", "",
              f"**Correct answer {p['correct']}:** {p['options'][p['correct']]}", "",
              f"> *Why:* {q['explanation']}", ""]
        sheet = cheatsheet(a["t"])
        if sheet:
            L += [f"**Cheat sheet:** `{sheet}`", ""]
        if q.get("references"):
            L += ["**References:** " + " · ".join(q["references"]), ""]

    skipped = [a for a in s["questions"] if a["skipped"]]
    if skipped:
        L += ["## 4b. Skipped", ""] + [f"- {a['id']} · {a['t']}" for a in skipped] + [""]
    L += ["## 5. Reproduce", "",
          f"`python3 tools/offline-assessment/offline-assessment.py --seed {s['seed']}`", ""]

    MOCK_EXAMS.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(L))
    return path


# --- stats ----------------------------------------------------------------
def stats(meta):
    hist = read_history()
    if not hist:
        die("No sessions logged yet — run a session first.")
    rule()
    print(f"  CCAR-F Offline Assessment — progression")
    total_q = sum(len(s["questions"]) for s in hist)
    print(f"  {len(hist)} sessions · {total_q} questions · since {hist[0]['started_at'][:10]}")
    rule()

    full = [s for s in hist if s.get("scaled_score") and s["completed"]]
    if full:
        print("\nScaled score (all-domain sessions)")
        for s in full[-8:]:
            score = s["scaled_score"]
            bar = "#" * round(score / 50)
            flag = " ✅" if score >= PASS_MARK else ""
            print(f"  {s['started_at'][:10]}  {s['answered']:>3}q  {score:>4}  "
                  f"[{bar:<20}]{flag}")
        print(f"{'':>26}^ pass mark {PASS_MARK}")

    print(f"\n{'Accuracy by domain':<30}{'first':>7}{'last':>7}{'trend':>8}{'seen':>7}")
    for d in sorted(WEIGHTS):
        runs = [s["domains"][str(d)] for s in hist if str(d) in s.get("domains", {})]
        runs = [r for r in runs if r["n"]]
        if not runs:
            continue
        first, last = pct(runs[0]["correct"], runs[0]["n"]), pct(runs[-1]["correct"], runs[-1]["n"])
        seen = sum(r["n"] for r in runs)
        delta = last - first
        trend = f"{delta:+.0f}" if len(runs) > 1 else "—"
        print(f"  D{d} {meta[d]['title'][:25]:<26}{first:>6.0f}%{last:>6.0f}%"
              f"{trend:>8}{seen:>7}")

    agg = {}
    for s in hist:
        for t, e in s.get("tasks", {}).items():
            a = agg.setdefault(t, {"n": 0, "correct": 0})
            a["n"] += e["n"]
            a["correct"] += e["correct"]
    weak = sorted(((t, e) for t, e in agg.items() if e["n"] >= 3),
                  key=lambda kv: pct(kv[1]["correct"], kv[1]["n"]))[:6]
    if weak:
        print("\nWeakest task statements (3+ attempts)")
        for t, e in weak:
            print(f"  {t}  {task_title(meta, t)[:44]:<46}{e['correct']}/{e['n']}"
                  f"{pct(e['correct'], e['n']):>6.0f} %")

    seen = seen_counts(hist)
    all_tasks = {t for d in meta.values() for t in d["tasks"]}
    touched = set(agg)
    print(f"\nCoverage: {len(seen)}/390 questions seen · "
          f"{len(touched)}/{len(all_tasks)} task statements touched")
    never = sorted(all_tasks - touched)
    if never:
        print("  Never seen: " + ", ".join(never))


# --- selftest -------------------------------------------------------------
def selftest():
    bank, meta = load_bank()
    fails = []

    def check(cond, msg):
        if not cond:
            fails.append(msg)

    check(len(bank) == 390, f"expected 390 questions, got {len(bank)}")
    check(len({q['id'] for q in bank}) == len(bank), "duplicate question ids")
    for q in bank:
        i = q["id"]
        check(set(q["options"]) == set(LETTERS), f"{i}: options != ABCD")
        check(all(str(v).strip() for v in q["options"].values()), f"{i}: empty option")
        check(q["correctAnswer"] in LETTERS, f"{i}: bad correctAnswer")
        check(set(q["whyWrongMap"]) == set(LETTERS) - {q["correctAnswer"]},
              f"{i}: whyWrongMap keys wrong")
        check(q["difficulty"] in DIFFICULTIES, f"{i}: bad difficulty")
        check(q["taskStatement"].startswith(str(q["domainId"])), f"{i}: task/domain mismatch")
    print(f"  structure ......... {len(bank)} questions checked")

    # shuffle losslessness, over many seeds
    n = 0
    for seed in range(8):
        for q in bank:
            p = present(q, seed)
            i = q["id"]
            check(sorted(p["options"].values()) == sorted(q["options"].values()),
                  f"{i}: option texts changed")
            check(p["options"][p["correct"]] == q["options"][q["correctAnswer"]],
                  f"{i}: correct answer text moved")
            check(set(p["why_wrong"]) == set(LETTERS) - {p["correct"]},
                  f"{i}: why_wrong keys wrong after shuffle")
            for L, why in p["why_wrong"].items():
                orig = [k for k in LETTERS if q["options"][k] == p["options"][L]][0]
                check(remap_prose(q["whyWrongMap"][orig], p["mapping"]) == why,
                      f"{i}: rationale detached from option")
            check(len(set(p["mapping"].values())) == 4, f"{i}: mapping not a bijection")
            check(present(q, seed) == p, f"{i}: not deterministic")
            n += 1
    print(f"  shuffle ........... {n} round-trips, lossless")

    # A letter named in prose ("Option B ...") must land on the same option text
    # after shuffling, or the explanation teaches the wrong answer.
    prose_qs = checked = 0
    for q in bank:
        fields = [q["explanation"], *q["whyWrongMap"].values()]
        if not any(PROSE_LETTER.search(s) for s in fields):
            continue
        prose_qs += 1
        for seed in range(8):
            p = present(q, seed)
            for src_text, out_text in zip(fields,
                                          [p["explanation"], *[
                                              p["why_wrong"][p["mapping"][k]]
                                              for k in q["whyWrongMap"]]]):
                src_letters = [m.group(3).upper()
                               for m in PROSE_LETTER.finditer(src_text)]
                out_letters = [m.group(3).upper()
                               for m in PROSE_LETTER.finditer(out_text)]
                check(out_letters == [p["mapping"][L] for L in src_letters],
                      f"{q['id']}: prose letter not remapped (seed {seed})")
                for sl, ol in zip(src_letters, out_letters):
                    check(q["options"][sl] == p["options"][ol],
                          f"{q['id']}: prose points at the wrong option (seed {seed})")
                    checked += 1
    print(f"  prose letters ..... {prose_qs} questions, {checked} references remapped")

    dist = {L: 0 for L in LETTERS}
    for q in bank:
        dist[present(q, 7)["correct"]] += 1
    src = {L: sum(1 for q in bank if q["correctAnswer"] == L) for L in LETTERS}
    check(all(abs(v - 97.5) <= 25 for v in dist.values()), f"bias not removed: {dist}")
    print(f"  bias .............. source {src} -> shuffled {dist}")

    combos = 0
    for domain in [None] + sorted(WEIGHTS):
        for diff in [None] + list(DIFFICULTIES):
            pool = [q for q in bank if (domain is None or q["domainId"] == domain)
                    and (diff is None or q["difficulty"] == diff)]
            for size in list(SIZES) + [len(pool)]:
                if size > len(pool):
                    continue
                got = select(bank, domain, diff, size, 5, {})
                check(len(got) == size, f"{domain}/{diff}/{size}: got {len(got)}")
                check(len({q['id'] for q in got}) == size, f"{domain}/{diff}/{size}: dupes")
                combos += 1
    print(f"  selection ......... {combos} combinations, exact size, no repeats")

    manifest_path = DATA / "manifest.json"
    if manifest_path.exists():
        man = json.loads(manifest_path.read_text())
        for name, e in man["files"].items():
            digest = hashlib.sha256((DATA / name).read_bytes()).hexdigest()
            check(digest == e["sha256"], f"{name}: sha256 mismatch — data/ was modified")
        print(f"  integrity ......... {len(man['files'])} files match manifest")

    print()
    if fails:
        for f in fails[:20]:
            print(bad(f"  FAIL  {f}"))
        print(bad(f"\n{len(fails)} check(s) failed"))
        return 1
    print(ok("  All checks passed."))
    return 0


# --- main -----------------------------------------------------------------
def main():
    argv = sys.argv[1:]
    seed = random.randrange(2 ** 31)
    action = None
    export_id = None
    answer_letter = None
    h_domain, h_difficulty, h_count = None, None, 20

    while argv:
        arg = argv.pop(0)
        if arg in ("-h", "--help"):
            print(USAGE)
            return 0
        elif arg == "--sync":
            action = "sync"
        elif arg == "--stats":
            action = "stats"
        elif arg == "--selftest":
            action = "selftest"
        elif arg == "--seed":
            if not argv:
                die("--seed needs a number")
            seed = int(argv.pop(0))
        elif arg == "--export":
            if not argv:
                die("--export needs a session id or 'last'")
            action, export_id = "export", argv.pop(0)
        elif arg == "--start":
            action = "start"
        elif arg == "--answer":
            if not argv:
                die("--answer needs a letter (a, b, c or d)")
            raw = argv.pop(0).strip().upper()
            if raw not in LETTERS:
                die(f"--answer takes a, b, c or d — got {raw!r}")
            action, answer_letter = "answer", raw
        elif arg == "--skip":
            action = "skip"
        elif arg == "--status":
            action = "status"
        elif arg == "--finish":
            action = "finish"
        elif arg == "--discard":
            action = "discard"
        elif arg == "--domain":
            if not argv:
                die("--domain needs 1-5 or 'all'")
            raw = argv.pop(0).strip().lower().lstrip("d")
            if raw == "all":
                h_domain = None
            elif raw.isdigit() and int(raw) in WEIGHTS:
                h_domain = int(raw)
            else:
                die(f"--domain takes 1-5 or 'all' — got {raw!r}")
        elif arg == "--difficulty":
            if not argv:
                die(f"--difficulty needs one of {', '.join(DIFFICULTIES)} or 'mix'")
            raw = argv.pop(0).strip().lower()
            if raw == "mix":
                h_difficulty = None
            elif raw in DIFFICULTIES:
                h_difficulty = raw
            else:
                die(f"--difficulty takes {', '.join(DIFFICULTIES)} or 'mix' — got {raw!r}")
        elif arg == "--count":
            if not argv:
                die("--count needs a number")
            raw = argv.pop(0)
            if not raw.isdigit() or int(raw) < 1:
                die(f"--count needs a positive number — got {raw!r}")
            h_count = int(raw)
        else:
            print(USAGE)
            die(f"Unknown option: {arg}")

    if action == "sync":
        return sync()
    if action == "selftest":
        return selftest()
    if action == "discard":
        return headless_discard()

    bank, meta = load_bank()

    if action == "stats":
        return stats(meta)
    if action == "start":
        return headless_start(bank, meta, seed, h_domain, h_difficulty, h_count)
    if action == "answer":
        return headless_respond(bank, meta, answer_letter)
    if action == "skip":
        return headless_respond(bank, meta, None)
    if action == "status":
        return headless_status(bank, meta)
    if action == "finish":
        return headless_finish(bank, meta)
    if action == "export":
        hist = read_history()
        if not hist:
            die("No sessions to export.")
        match = hist[-1] if export_id == "last" else \
            next((s for s in hist if s["session_id"] == export_id), None)
        if not match:
            die(f"No session with id {export_id}")
        path = export(match, meta, bank)
        print(f"Report saved to {path.relative_to(REPO)}")
        return 0

    resume = None
    if SESSION.exists():
        state = json.loads(SESSION.read_text())
        scope = "All domains" if state["domain"] is None else f"D{state['domain']}"
        print(f"\nUnfinished session: {scope} · {state['difficulty'] or 'mix'} · "
              f"{len(state['answers'])}/{state['planned']} answered "
              f"(started {state['started_at'][:16].replace('T', ' ')})")
        i = pick("Choose", ["Resume it", "Discard it and start fresh"])
        if i is None:
            return 0
        if i == 0:
            resume = state
        else:
            SESSION.unlink()

    run(bank, meta, seed, resume)
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
