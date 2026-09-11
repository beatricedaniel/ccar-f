#!/usr/bin/env python3
"""Guided walkthroughs of the CCAR-F §8 Preparation Exercises.

Pick one of the four exam-guide exercises and get coached through it step by step:
each step shows the verbatim task plus a teaching note, and you can pull progressive
hints, a self-check checkpoint, a model approach, and common pitfalls on demand.
Every session is logged under logs/.

Unlike the sibling tools (flashcards, tutor) this one is **fully offline**: it makes
no network calls and needs no ANTHROPIC_API_KEY. The coaching content lives in
guides/*.json, authored by a Claude Code session. To (re)author a guide, run
`labs.py --print-prompt <n>` and hand the printed prompt to Claude Code.

Requirements: python3 (stdlib only — no third-party packages, no API key).
"""

import json
import sys
from datetime import datetime
from pathlib import Path

# --- config ---------------------------------------------------------------
HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent                      # tools/labs -> repo root
GUIDES = HERE / "guides"
LOGS = HERE / "logs"

# The §8 exercises, verbatim from the exam guide. This is the source-of-truth
# spine: it drives the menu and the --print-prompt authoring prompt. The richer
# coaching layer (hints, model answers, ...) lives in guides/<n>-<slug>.json.
EXERCISES = [
    {
        "exercise": 1,
        "slug": "multi-tool-agent-escalation",
        "title": "Build a Multi-Tool Agent with Escalation Logic",
        "domains": ["D1", "D2", "D5"],
        "objective": (
            "Practice designing an agentic loop with tool integration, structured "
            "error handling, and escalation patterns."
        ),
        "steps": [
            "Define 3-4 MCP tools with detailed descriptions that clearly differentiate each "
            "tool's purpose, expected inputs, and boundary conditions. Include at least two tools "
            "with similar functionality that require careful description to avoid selection confusion.",
            "Implement an agentic loop that checks stop_reason to determine whether to continue "
            "tool execution or present the final response. Handle both \"tool_use\" and \"end_turn\" "
            "stop reasons correctly.",
            "Add structured error responses to your tools: include errorCategory "
            "(transient/validation/permission), isRetryable boolean, and human-readable "
            "descriptions. Test that the agent handles each error type appropriately (retrying "
            "transient errors, explaining business errors to the user).",
            "Implement a programmatic hook that intercepts tool calls to enforce a business rule "
            "(e.g., blocking operations above a threshold amount), redirecting to an escalation "
            "workflow when triggered.",
            "Test with multi-concern messages (e.g., requests involving multiple issues) and verify "
            "the agent decomposes the request, handles each concern, and synthesizes a unified response.",
        ],
    },
    {
        "exercise": 2,
        "slug": "claude-code-team-workflow",
        "title": "Configure Claude Code for a Team Development Workflow",
        "domains": ["D2", "D3"],
        "objective": (
            "Practice configuring CLAUDE.md hierarchies, custom slash commands, path-specific "
            "rules, and MCP server integration for a multi-developer project."
        ),
        "steps": [
            "Create a project-level CLAUDE.md with universal coding standards and testing "
            "conventions. Verify that instructions placed at the project level are consistently "
            "applied across all team members.",
            "Create .claude/rules/ files with YAML frontmatter glob patterns for different code "
            "areas (e.g., paths: [\"src/api/**/*\"] for API conventions, paths: [\"**/*.test.*\"] "
            "for testing conventions). Test that rules load only when editing matching files.",
            "Create a project-scoped skill in .claude/skills/ with context: fork and allowed-tools "
            "restrictions. Verify the skill runs in isolation without polluting the main "
            "conversation context.",
            "Configure an MCP server in .mcp.json with environment variable expansion for "
            "credentials. Add a personal experimental MCP server in ~/.claude.json and verify both "
            "are available simultaneously.",
            "Test plan mode versus direct execution on tasks of varying complexity: a single-file "
            "bug fix, a multi-file library migration, and a new feature with multiple valid "
            "implementation approaches. Observe when plan mode provides value.",
        ],
    },
    {
        "exercise": 3,
        "slug": "structured-extraction-pipeline",
        "title": "Build a Structured Data Extraction Pipeline",
        "domains": ["D4", "D5"],
        "objective": (
            "Practice designing JSON schemas, using tool_use for structured output, implementing "
            "validation-retry loops, and designing batch processing strategies."
        ),
        "steps": [
            "Define an extraction tool with a JSON schema containing required and optional fields, "
            "an enum with an \"other\" + detail string pattern, and nullable fields for information "
            "that may not exist in source documents. Process documents where some fields are absent "
            "and verify the model returns null rather than fabricating values.",
            "Implement a validation-retry loop: when Pydantic or JSON schema validation fails, send "
            "a follow-up request including the document, the failed extraction, and the specific "
            "validation error. Track which errors are resolvable via retry (format mismatches) "
            "versus which are not (information absent from source).",
            "Add few-shot examples demonstrating extraction from documents with varied formats "
            "(e.g., inline citations vs bibliographies, narrative descriptions vs structured tables) "
            "and verify improved handling of structural variety.",
            "Design a batch processing strategy: submit a batch of 100 documents using the Message "
            "Batches API, handle failures by custom_id, resubmit failed documents with modifications "
            "(e.g., chunking oversized documents), and calculate total processing time relative to "
            "SLA constraints.",
            "Implement a human review routing strategy: have the model output field-level "
            "confidence scores, route low-confidence extractions to human review, and analyze "
            "accuracy by document type and field to verify consistent performance.",
        ],
    },
    {
        "exercise": 4,
        "slug": "multi-agent-research-pipeline",
        "title": "Design and Debug a Multi-Agent Research Pipeline",
        "domains": ["D1", "D2", "D5"],
        "objective": (
            "Practice orchestrating subagents, managing context passing, implementing error "
            "propagation, and handling synthesis with provenance tracking."
        ),
        "steps": [
            "Build a coordinator agent that delegates to at least two subagents (e.g., web search "
            "and document analysis). Ensure the coordinator's allowedTools includes \"Task\" and "
            "that each subagent receives its research findings directly in its prompt rather than "
            "relying on automatic context inheritance.",
            "Implement parallel subagent execution by having the coordinator emit multiple Task "
            "tool calls in a single response. Measure the latency improvement compared to "
            "sequential execution.",
            "Design structured output for subagents that separates content from metadata: each "
            "finding should include a claim, evidence excerpt, source URL/document name, and "
            "publication date. Verify that the synthesis subagent preserves source attribution when "
            "combining findings.",
            "Implement error propagation: simulate a subagent timeout and verify the coordinator "
            "receives structured error context (failure type, attempted query, partial results). "
            "Test that the coordinator can proceed with partial results and annotate the final "
            "output with coverage gaps.",
            "Test with conflicting source data (e.g., two credible sources with different "
            "statistics) and verify the synthesis output preserves both values with source "
            "attribution rather than arbitrarily selecting one, and structures the report to "
            "distinguish well-established from contested findings.",
        ],
    },
]

REQUIRED_STEP_KEYS = {"n", "title", "domains", "task", "explain", "hints",
                      "checkpoint", "model_answer", "pitfalls"}


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


def wrap(text, indent="   ", width=88):
    """Lightweight word-wrap so long teaching notes read cleanly in a terminal."""
    out, line = [], indent
    for word in text.split():
        if len(line) + len(word) + 1 > width and line.strip():
            out.append(line.rstrip())
            line = indent
        line += word + " "
    if line.strip():
        out.append(line.rstrip())
    return "\n".join(out)


def domains_str(domains):
    return " · ".join(domains)


# --- guide loading & validation -------------------------------------------
def guide_path(ex):
    return GUIDES / f"{ex['exercise']}-{ex['slug']}.json"


def load_guide(ex):
    path = guide_path(ex)
    if not path.exists():
        die(f"No guide found at {path.relative_to(REPO)}.\n"
            f"   Regenerate it: run `python3 tools/labs/labs.py --print-prompt {ex['exercise']}`\n"
            f"   and hand the printed prompt to a Claude Code session.")
    try:
        guide = json.loads(path.read_text())
    except json.JSONDecodeError as e:
        die(f"Guide {path.name} is not valid JSON: {e}")
    steps = guide.get("steps")
    if not isinstance(steps, list) or not steps:
        die(f"Guide {path.name} has no steps.")
    for i, step in enumerate(steps, 1):
        missing = REQUIRED_STEP_KEYS - set(step)
        if missing:
            die(f"Guide {path.name} step {i} is missing fields: {', '.join(sorted(missing))}.")
    return guide


# --- study session --------------------------------------------------------
STEP_MENU = ("[h]int  [c]heckpoint  [s]olution  [p]itfalls  "
             "[l]ist  [b]ack  [Enter] next  [q]uit")


def print_overview(guide):
    rule("=")
    print(f"  Exercise {guide['exercise']} — {guide['title']}")
    print(f"  Domains: {domains_str(guide['domains'])}")
    rule("=")
    print("\nObjective")
    print(wrap(guide["objective"]))
    if guide.get("overview"):
        print("\nOverview")
        print(wrap(guide["overview"]))
    print(f"\nSteps ({len(guide['steps'])}):")
    for st in guide["steps"]:
        print(f"  {st['n']}. [{domains_str(st['domains'])}] {st['title']}")


def show_step(step, idx, total):
    rule("-")
    print(f"Step {idx + 1}/{total} · {domains_str(step['domains'])} — {step['title']}")
    rule("-")
    print("Task")
    print(wrap(step["task"]))
    print("\n💡 Coach")
    print(wrap(step["explain"]))


def run_step(step):
    """Interactive command loop for one step. Returns 'next' | 'back' | 'list' | 'quit'."""
    hints_shown = 0
    while True:
        cmd = ask(f"\n   {STEP_MENU}\n   > ").lower()
        if cmd in ("", "n"):
            return "next"
        if cmd == "b":
            return "back"
        if cmd == "l":
            return "list"
        if cmd == "q":
            return "quit"
        if cmd == "h":
            hints = step["hints"]
            if hints_shown >= len(hints):
                print("   (no more hints — try the checkpoint with [c] or reveal [s]olution)")
            else:
                print(f"\n   Hint {hints_shown + 1}/{len(hints)}:")
                print(wrap(hints[hints_shown]))
                hints_shown += 1
        elif cmd == "c":
            print("\n❓ Checkpoint")
            print(wrap(step["checkpoint"]))
            follow = ask("\n   [Enter] to reveal the model answer, s to skip: ").lower()
            if follow != "s":
                print("\n✅ Model answer")
                print(wrap(step["model_answer"]))
        elif cmd == "s":
            print("\n✅ Model answer")
            print(wrap(step["model_answer"]))
        elif cmd == "p":
            print("\n⚠️  Common pitfalls")
            for pit in step["pitfalls"]:
                print(wrap(f"- {pit}"))
        else:
            print("   Unknown command. Use h / c / s / p / l / b / Enter / q.")


def study(guide):
    print_overview(guide)
    steps = guide["steps"]
    marks = {}                      # step index -> "got_it" | "revisit" | "skipped"
    idx = 0
    while 0 <= idx < len(steps):
        show_step(steps[idx], idx, len(steps))
        action = run_step(steps[idx])
        if action == "quit":
            break
        if action == "list":
            print_overview(guide)
            continue
        if action == "back":
            idx = max(0, idx - 1)
            continue
        # action == "next": self-assess before advancing
        while True:
            mark = ask("   Mark this step — [g]ot it / [r]evisit / [s]kip: ").lower()
            if mark in ("g", "r", "s"):
                break
        marks[idx] = {"g": "got_it", "r": "revisit", "s": "skipped"}[mark]
        idx += 1

    _finalise(guide, marks)


def _finalise(guide, marks):
    steps = guide["steps"]
    if not marks:
        print("\nNo steps completed; nothing to log.")
        return

    if guide.get("wrap_up"):
        print("\n🎉 Wrap-up")
        print(wrap(guide["wrap_up"]))

    got = sum(1 for m in marks.values() if m == "got_it")
    revisit_steps = [steps[i]["title"] for i, m in marks.items() if m == "revisit"]
    pct = round(100 * got / len(steps), 1)

    rule("-")
    print(f"Completed {len(marks)}/{len(steps)} step(s) · "
          f"{got} got it ({pct} %) · {len(revisit_steps)} to revisit")
    if revisit_steps:
        print("To revisit:")
        for title in revisit_steps:
            print(f"  - {title}")

    ts = datetime.now()
    log = {
        "exercise": guide["exercise"],
        "slug": guide["slug"],
        "title": guide["title"],
        "domains": guide["domains"],
        "started_at": ts.isoformat(timespec="seconds"),
        "finished_at": datetime.now().isoformat(timespec="seconds"),
        "guide_generated_at": guide.get("generated_at"),
        "steps": [
            {"n": steps[i]["n"], "title": steps[i]["title"],
             "domains": steps[i]["domains"], "marked": marks[i]}
            for i in sorted(marks)
        ],
        "revisit": revisit_steps,
        "pct_understood": pct,
    }
    log_dir = LOGS / guide["slug"]
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"{ts:%Y%m%d_%H%M%S}.json"
    log_file.write_text(json.dumps(log, indent=2, ensure_ascii=False))
    print(f"\nSession log saved to {log_file.relative_to(REPO)}")


# --- guide authoring prompt (--print-prompt) ------------------------------
GUIDE_SCHEMA_HINT = """{
  "exercise": <int>, "slug": "<kebab-slug>", "title": "<title>",
  "domains": ["D1", ...],
  "objective": "<verbatim objective, copied below>",
  "overview": "<2-4 sentence framing of the whole exercise>",
  "steps": [
    {
      "n": <int>, "title": "<short step title>", "domains": ["D2", ...],
      "task": "<verbatim step bullet, copied below>",
      "explain": "<teaching note: the concept + why it matters, tied to the domain/lesson>",
      "hints": ["<progressive hint 1>", "<hint 2>", "<hint 3>"],
      "checkpoint": "<a self-check question the learner answers before revealing>",
      "model_answer": "<the model approach / what a strong answer covers>",
      "pitfalls": ["<common mistake / exam trap>", "..."]
    }
  ],
  "wrap_up": "<synthesis: how the exercise maps to the exam + what to review next>",
  "authored_by": "claude-code", "generated_at": "<YYYY-MM-DD>"
}"""


def print_prompt(ex):
    steps_block = "\n".join(f"  Step {i}: {s}" for i, s in enumerate(ex["steps"], 1))
    print(f"""You are an expert CCAR-F (Claude Certified Architect – Foundations) instructor.
Author a step-by-step coaching guide for the following §8 Preparation Exercise, as a
single JSON object matching this schema exactly (no prose, no markdown fences):

{GUIDE_SCHEMA_HINT}

Rules:
- Copy `objective` and each step's `task` VERBATIM from the source below.
- One steps[] entry per source step, in order, with n starting at 1.
- `domains` per step = the domain(s) that step exercises, drawn from the exercise's
  domains ({domains_str(ex['domains'])}). Exam weights: D1 27%, D2 18%, D3 20%, D4 20%, D5 15%.
- `explain` teaches the concept and why it matters; `hints` go from gentle nudge to
  near-solution; `model_answer` is what a strong answer covers; `pitfalls` are real
  exam traps. Keep it study/explain only — no scaffolding of project files.

Write the JSON to tools/labs/guides/{ex['exercise']}-{ex['slug']}.json.

----- SOURCE EXERCISE (verbatim) -----
Exercise {ex['exercise']}: {ex['title']}
Domains reinforced: {domains_str(ex['domains'])}
Objective: {ex['objective']}
Steps:
{steps_block}
""")


# --- main -----------------------------------------------------------------
def main():
    argv = sys.argv[1:]
    if argv and argv[0] == "--print-prompt":
        if len(argv) < 2 or not argv[1].isdigit():
            die("Usage: labs.py --print-prompt <exercise number 1-4>")
        n = int(argv[1])
        ex = next((e for e in EXERCISES if e["exercise"] == n), None)
        if not ex:
            die(f"No exercise numbered {n}. Choose 1-{len(EXERCISES)}.")
        print_prompt(ex)
        return

    rule("=")
    print("  CCAR-F Labs  —  guided walkthroughs of the §8 Preparation Exercises")
    print("  offline · no API key needed · free")
    rule("=")

    print("\nExercises:")
    labels = [f"Exercise {e['exercise']} · {domains_str(e['domains'])} — {e['title']}"
              for e in EXERCISES]
    i = pick("Choose an exercise", labels)
    if i is None:
        return
    guide = load_guide(EXERCISES[i])
    study(guide)


if __name__ == "__main__":
    main()
