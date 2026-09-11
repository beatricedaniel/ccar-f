# CCAR-F — Study Plan & 2-Week Schedule

**Prepared:** Friday 2026-08-28 · **Revised:** Mon 2026-08-31, **Wed 2026-09-02** · **Window:** **11 study days**, **Mon Aug 31 → Fri Sep 11** — weekend **Sep 12–13 kept free**, **end date held**.
**⚠️ Sep 2 re-plan (v2):** Day 1 (D4.3) done; **Day 2 on Tue Sep 1 was missed** (D4.4 + D4.6). To hold the Sep 11 end date and free weekend — and keep **Thu Sep 10 light (two meetings that day)** — the missed block is recovered from today (Sep 2), the **two D5 subtopic-days are merged into one (Mon Sep 7)** to buy back the lost day, **targeted repair gets its own full day (Wed Sep 9)**, and **Sep 10 carries only light, mock-independent D1/D3 maintenance**. Plan stays at 11 study days; D4 and D2 learning days are untouched (D5 is the lowest-priority of the three weak domains, so it absorbs the merge).
**Current standing:** merged mock score **≈ 648 / 1000** (need **720**) — see
`mock_exams/20260828_Merged_Results_Report.md`.
**Goal of these two weeks:** close a ~72-point gap, concentrated in **D4 → D2 → D5**.

---

## Part A — Study Plan (what to learn, in priority order)

The plan follows the score math: the fastest route to 720 is D4 first, then D2 and D5,
while keeping D1 and D3 warm. Primary source = the **Exam Guide** (`theory/…Exam Guide.pdf`);
secondary = the **connectry-architect MCP** for drilling (`get_section_details` →
`get_practice_question` → `start_assessment`) and full re-sims (`start_practice_exam`).

### Tier 1 — CRITICAL: Domain 4 (currently 40 %, worth 20 % of the exam)
This one domain, lifted to ~80 %, adds ~80 scaled points and nearly closes the gap alone.

- **4.3 Structured output & schema design** *(4 of 9 D4 misses)* — the biggest single lever:
  - Make conditionally-absent fields **optional / nullable** → the model returns `null`
    instead of fabricating (Q40, Q52). Never "fix" fabrication with post-hoc validation.
  - **Enum fields** (+ an `"other"` value) with **`strict: true`** to constrain categorical
    output at the schema level, not with prompt instructions (Q14).
  - **`tool_choice`**: `auto` (may return text) vs `any` (must call some tool) vs
    **forced `{type:"tool", name:"…"}`** (must call *that* tool) — force it when you need a
    guaranteed extraction every time (Q27).
  - Remember: strict schemas kill **syntax** errors but not **semantic** ones (values that
    don't sum, wrong field placement).
- **4.4 Validation, retry & feedback loops** — know the **retry boundary**: retry
  format/structural errors with error-feedback; **route absent-info / absent-capability
  cases to human review** — retries can't conjure missing data or a language the model
  can't read (Q56). `detected_patterns` externalises reasoning so validation can catch
  inconsistencies and feed targeted corrections back (Q37).
- **4.2 Few-shot prompting** — **2–4 targeted examples that show the reasoning** beat both
  longer prose and exhaustive per-variant coverage (Q42, Q50). Reasoning chains generalise.
- **4.6 Multi-pass / self-review** — same-session self-review is anchored to its own
  reasoning; use a **fresh independent instance** for genuine QA (Q30). Split large reviews
  into per-file passes + a cross-file pass.
- **4.5 Batch processing** — already fine, but confirm: Message Batches API = 50 % cheaper,
  ≤24 h, no SLA → good for overnight, **not** for blocking pre-merge checks; correlate with
  `custom_id`.
- **Hands-on:** Exam Guide **Exercise 3** (structured-data-extraction pipeline).

### Tier 2 — HIGH: Domain 2 (57 %) and Domain 5 (57 %)

**Domain 2 — Tool Design & MCP Integration**
- **2.2 Structured error responses** — the four categories cold:
  **transient** (retryable), **validation** (fix input then retry), **business/policy**
  (not retryable — escalate/alternative), **permission** (not retryable). Always return
  `errorCategory` + `isRetryable` + human-readable message (Q09). Distinguish an **access
  failure** from a **valid empty result** (`success` + `[]` = inform, don't retry) (Q22).
- **2.4 MCP integration** — expose catalogues (schemas, docs, issue lists) as **MCP
  resources** to eliminate exploratory discovery calls (Q35). Scope: team = project
  **`.mcp.json`** (version-controlled), personal = user **`~/.claude.json`**; env-var
  expansion (`${TOKEN}`) is for **credentials**, not server definitions (Q38).
- **2.1 Tool descriptions** — descriptions are the primary selection signal; fix misrouting
  by renaming overlapping tools, rewriting descriptions (purpose/inputs/outputs/**boundaries**),
  and auditing the system prompt for keyword bias (Q07, Q12). *(2.1 was 100 % on the short
  assessment but slipped on the harder items — review the boundary/multi-select nuance.)*
- **2.3 / 2.5** — skim: too-many-tools (18 vs 4-5) degrades selection; scoped tool access;
  Grep/Glob/Read/Write/Edit selection.
- **Hands-on:** Exam Guide **Exercise 1** (multi-tool agent with escalation logic).

**Domain 5 — Context Management & Reliability**
- **5.6 Information provenance** — **annotate conflicting values with source + date**;
  don't average, don't silently pick the newest, don't pause for a human (Q06). Require
  subagents to emit **structured claim-source mappings** that survive synthesis (Q19).
- **5.3 Error propagation** — **silent suppression (empty-as-success) is the worst
  anti-pattern**; propagate structured error context (failure type, attempted query,
  partial results, alternatives) (Q36). Don't terminate the whole workflow on one failure.
- **5.2 Escalation** — escalate on **explicit human request / policy gap / inability to
  progress** — *not* on issue difficulty, sentiment, or confidence scores. Honour an explicit
  "get me a human" **immediately** (Q59).
- **5.4 / 5.1** — **scratchpad files** persist findings across context boundaries (Q25);
  "lost in the middle" is an **attention** effect — re-pin critical constraints near the end
  (IA-Q13).

### Tier 3 — MAINTAIN: Domain 1 (76.5 %) and Domain 3 (86.7 %)
Already passing — light touch to patch specific gaps and prevent regression.
- **D1:** PostToolUse **hooks** for deterministic normalisation (Q10); decompose
  multi-concern requests to **parallel existing specialists**, don't spawn a combined agent
  (Q54); **tiered confidence routing** not blanket escalation (Q57); `stop_reason`
  (`tool_use`/`end_turn`) is the loop signal (IA-Q1).
- **D3:** plan vs direct **per task** (Q20); CLAUDE.md precedence = **most-specific/closest
  scope wins** (IA-Q8).
- **Hands-on (spans D1+D2+D5):** Exam Guide **Exercise 4** (multi-agent research pipeline)
  and **Exercise 2** (team Claude Code config) if time permits.

---

## Part B — Schedule (Mon Aug 31 → Fri Sep 11, 11 days; weekend Sep 12–13 free)

Assumes **~2.5–3 h/day** (holiday pace — adjust up/down freely; weekends kept lighter).
Daily loop with the MCP: `get_section_details <task>` → read → `get_practice_question`
(≥5) → `start_assessment` to score → log misses. Re-read the merged report's §4 heuristic
every few days until it's automatic.

> **Re-plan note (Sep 2, v2):** Day 1 ✅ done. **Tue Sep 1 was missed** — its D4.4 + D4.6 block is
> recovered as the new Day 2 (Wed Sep 2). Because **Thu Sep 10 must stay light (two meetings)**,
> the lost day is bought back by **merging the two D5 days into Mon Sep 7 (Day 7)** — D5 is the
> lowest-priority of the three weak domains. Full mock #1 moves to **Tue Sep 8**, **targeted repair
> gets its own full day Wed Sep 9**, and **Sep 10 holds only light, mock-independent D1/D3
> maintenance**. End date (Fri Sep 11) and the free weekend are unchanged.

### Week 1 — Attack the weak domains

| Day | Date | Focus | Concrete actions |
|---|---|---|---|
| **1** | Mon Aug 31 | ✅ **DONE** — Orientation + full D4.3 | Re-read Exam Guide §6 D4 + Appendix. **nullable/optional fields**, **enum + strict**, **`tool_choice`** auto/any/forced. Drill 4.3; re-do PE-Q14, Q27, Q40, Q52 and explain each. |
| **—** | ~~Tue Sep 1~~ | ❌ **MISSED** — D4.4 + D4.6 | Recovered as **Day 2** below. |
| **2** | Wed Sep 2 | D4.4 + D4.6 *(recovered)* | Retry **boundary**, `detected_patterns`, self-review vs independent instance. Drill 4.4 & 4.6. |
| **3** | Thu Sep 3 | D4.2 + **Exercise 3** + project `d4-prompts` | Few-shot (2–4 targeted, reasoning chains). Build the structured-extraction pipeline hands-on. Run MCP mini project **`d4-prompts`**. |
| **4** | Fri Sep 4 | D4 consolidation | `start_assessment` on **all of D4**. Target **≥ 80 %**. Re-drill anything still shaky. |
| **5** | Sat Sep 5 | D2.2 + D2.1 + project `d2-tools` | Four error categories + `isRetryable`; access-vs-empty; tool descriptions/boundaries. Drill D2. Run MCP mini project **`d2-tools`**. |
| **6** | Sun Sep 6 | D2.4 + **Exercise 1** (lighter) | MCP resources vs tools; project vs user scoping. Build the multi-tool escalation agent. |

*(The separate end-of-week-1 checkpoint mock is dropped in the v2 re-plan — Full mock #1 now lands
just two days later, on Tue Sep 8, and serves as the first full gauge.)*

### Week 2 — Reliability, reinforcement, and full simulations

| Day | Date | Focus | Concrete actions |
|---|---|---|---|
| **7** | Mon Sep 7 | **All of D5** (5.6 + 5.3 + 5.2 + 5.4/5.1) + project `d5-context` *(merged — heavier)* | Provenance (annotate with source+date), claim-source mappings, silent-suppression anti-pattern, escalation triggers, scratchpad files, lost-in-the-middle. Drill D5; `start_assessment` on D5 → **≥ 75 %**. Project **`d5-context`** is *do-if-time*. |
| **8** | Tue Sep 8 | **Full mock #1** | `start_practice_exam` under timed conditions (120 min, 60 items). Score by domain, list every miss. |
| **9** | Wed Sep 9 | **Targeted repair** *(full day)* | Rework *only* the domains/subtopics still under 75 % from mock #1. Re-drill those question sets. A dedicated day — this is the main lever between the two mocks. |
| **10** | Thu Sep 10 | **D1/D3 maintenance — LIGHT** *(2 meetings today)* | Low-effort and mock-independent so it fits around the meetings: patch the known D1/D3 gaps — hooks, multi-concern decomposition, confidence routing, `stop_reason`, plan-vs-direct, CLAUDE.md precedence. Projects **`d1-agentic`**/**`d3-config`** + **Exercise 4** are **optional weekend stretch — not for today**. |
| **11** | Fri Sep 11 | **Full mock #2** + review + logistics | Morning: second timed `start_practice_exam` — **target ≥ 720 weighted**; compare domain deltas vs the Day 8 mock. Afternoon: skim §4 heuristic, four error categories, schema/tool_choice rules; **register with Pearson VUE** (confirm ID name matches); prep the testing environment. |
| **—** | **Sat–Sun Sep 12–13** | **FREE — no study** *(optional: any slipped `d1-agentic`/`d3-config`)* | Rest weekend before sitting the exam. |

### Go / no-go rule for booking the real exam
Book only once **two consecutive full mocks score ≥ 740 weighted** (a safety margin above
720) **and no single domain is below 65 %**. If mock #1 (Day 8) and mock #2 (Day 11) aren't both
there, **don't book yet** — use the free weekend + extra days the following week for targeted
repair and push the sitting. A retake after a fail costs $125 and a 14-day wait, so it's cheaper
to be sure. Plan to sit the exam the week of **Sep 15** once the two-mock bar is cleared.
**Repair runway:** the v2 re-plan gives repair its own full day (Day 9, Wed Sep 9) between the two
mocks. If mock #1 exposes a broad D4/D2/D5 gap, you can borrow the lighter Day 10 and the free
weekend for extra repair — but keep the D1/D3 mini-projects optional so they never crowd it out.
The one trade-off: all of D5 is compressed into Day 7, so give that day a solid block.

### Daily habit checklist
- [ ] Re-state the §4 heuristic out loud: *prefer the deterministic/structural fix; escalate on trigger, not difficulty.*
- [ ] For every missed practice item, write the **correct principle** in one line (not just the letter).
- [ ] Keep a running "misses log" so Day 10 repair is targeted.
- [ ] Track task-statement mastery via `get_curriculum` — push every assessed task to STRONG.

---

## Part C — Hands-on MCP reference projects

Distinct from the Exam Guide **Exercises 1–4** above, the `connectry-architect` MCP scaffolds
its own hands-on builds (`scaffold_project projectId="…"`). Five single-domain "mini" projects
map onto the schedule; the all-domain capstone is a stretch/post-exam option.

| Project ID | Title | Domain(s) | Scheduled |
|---|---|---|---|
| `d4-prompts` | D4 Mini — Prompt Engineering | 4 | Day 3 (Thu Sep 3) |
| `d2-tools` | D2 Mini — Tool Design | 2 | Day 5 (Sat Sep 5) |
| `d5-context` | D5 Mini — Context Management | 5 | Day 7 (Mon Sep 7) — *do-if-time* |
| `d1-agentic` | D1 Mini — Agentic Loop | 1 | Weekend Sep 12 — *optional stretch* |
| `d3-config` | D3 Mini — Claude Code Config | 3 | Weekend Sep 12 — *optional stretch* |
| `capstone` | Capstone — Multi-Agent Research System | 1–5 | *unscheduled — post-exam* |

To launch one: `scaffold_project projectId="<id>"` for instructions, or `start_capstone_build`
for the guided all-30-task-statements capstone. These are mirrored as cards on the **CCAR-F**
Trello board (Zero2One workspace), each due on its paired study day.
