# Eval plan: <agent name>

*Version <n> · <date> · owner: <name/role> · decision served: <launch go/no-go | version comparison | regression protection | migration>*

## Summary

- **Pin check (SKILL.md step 0, done first):** <each model the agent and judge use: active / deprecated (retirement date) / retired / unchecked (assumed); page; date checked>. Retired: the existing suite is not the system under test; re-baseline on <replacement, to be confirmed> first. Unchecked: a blocking week-1 item
- **Decision:** <what this suite decides, and by when>
- **Suite:** <N tasks (dev N / held-out N) in S scenarios, n_eff ≈ …>, <k> trials on side-effecting tasks; release rates within ±<Y> on the held-out split; detects ≥ <X> points between versions (MDE ≈ 2.8 × √(d / n), d = <measured or assumed>)
- **Hard gates:** <three to five checks that block any release>
- **Top risks addressed:** <1>, <2>, <3>
- **Build first:** <what exists by end of week 1>
- **Gate items supplied** (lifecycle map: agent-architect): Decide: <decision served; eval budget, cost and wall time per tier>. Build: <first smoke suite, golden run and baseline, ready by …>. Prove: <held-out hard checks pass; harness slice passes>

## 1. System under test

| Item | Value (pinned) |
|---|---|
| Agent version / prompt version | |
| Model and version (agent and judge, defaults included), lifecycle status from the pin check (page, date checked), temperature, max steps. A retired or unchecked pin is written "to be confirmed", never as the system under test | |
| Served interface (direct call / server API with persistent threads); settings a caller or console can override | |
| Tools (R = read, W = write, W! = irreversible) | |
| Read tools with live data (prices, inventory, balances) | |
| Retrieval sources / memory; index snapshot ID; per-user access mechanism (yes / no) | |
| Single- or multi-turn; user population | |

## 2. Assumptions

| # | Assumption | Why it matters | How to confirm |
|---|---|---|---|

## 3. Policy decisions

Rules the agent must follow. Only signed-off rules become hard checks; open ones are scored report-only.

| Rule (e.g. what counts as consent to charge) | Owner | Status (signed / open) | Date | Encoded as (hard / report-only) |
|---|---|---|---|---|

## 4. Quality dimensions

| Dimension | Failure looks like | Severity | Hard / soft | Scorer (code / judge / human) | Target |
|---|---|---|---|---|---|
| Outcome correctness (final state) | | | Hard | Code predicate | |
| Path and tool use | | | Hard rules + soft efficiency | Code | |
| Safety and policy | | | Hard | Code + judge | |
| Communication | | | Soft | Judge | |
| Cost and latency | | | Budget hard, rest soft | Counters | |

## 5. Task set

**Sources and share:** incidents/bad traces <x%>, production or pilot logs <x%>, expert-written <x%>, reviewed synthetic <x%>. Expected outcomes confirmed by <who>.
*Pre-launch:* existing prompts as seeds <n>, real inputs borrowed from the current manual process <n>, dogfood/beta harvest <n> (dates), threat-model seeds <n>, reviewed synthetic <n>. The real-input slice is reported separately. Gates resting mostly on synthetic tasks: <list>. Date by which real inputs make up most of each slice: <date>.

**First suite (smoke, run on every change):** 10 normal / 10 edge / 10 adversarial, plus failure cases (a tool fails, data is missing). Binary SLA predicates. Golden run <ID>, checked on its hard properties. Baseline <ID>, saved before the first change. One change per iteration. It catches large regressions only (27 of 30 is 74 to 97%; changes under about 20 points are ties), so it is not the release gate.

**Composition:**

| Slice | Scenarios | Tasks | Notes |
|---|---|---|---|
| Per tool (<tool>) | | | |
| Multi-tool chains | | | |
| No tool needed | | | assert zero calls |
| Must ask / must refuse / must escalate | | | no write while info missing (hard) |
| Stress variants (ambiguity, missing info, partial tool failure, intent switch, injected instruction) | | | |
| Lost acknowledgement on writes (timeout after commit, duplicate message, restart) | | | exactly one write |
| Multi-turn (simulated persona) | ≥ 20 | | N/A for single-turn agents |
| Safety: misuse / manipulation through data / benign-task harm | | | attack design: agent-threat-modeler |
| Access (retrieval): two or more callers with different scopes, a restricted gold document, a caller who sets their own filter or k | | | critical hard check on retrieved document IDs; a capability suite expected to fail if no access mechanism exists |
| Harness slice: resume after crash, stop rules, budget exhaustion, cancel, kill switch, kill while paused, edge faults | n/a | | scripted model, hard checks; harness side: agent-harness-designer |
| **Total (dev / held-out)** | | | |

Slices are tags and may overlap. Give each task one primary slice so the primary-slice counts sum to the total, and list tag counts separately (they may add up to more than the total).

**Schema:** id, scenario_id, version, clock, prompt or turns, initial_state, success predicates, hard_rules, expected_tools / expect_no_tool, expected_exit, reference (optional), tags (type, tool, difficulty, source, risk, split). Retrieval tasks add gold_docs (stable source IDs, never content-derived or store-assigned IDs) and index_version.

**Real user data:** de-identified by <method and who checks it>; eval use and the judge's provider and region allowed by <data owner, terms>; access <who>; retention <period>; deletion requests reach the sets by <process>.

**Versioning and maintenance:** immutable versions with changelog, including fixtures and recordings; validation before each run; expected tools checked against the live registry; quarterly review; incident → task within <1 day>.

## 6. Harness

- Fresh environment per trial: <fixture / sandbox / mock API>
- Served interface: evals run through <the interface production uses, e.g. the server API with threads>; effective configuration and dependency versions logged per trial
- Search index: frozen snapshot <ID> with distractor documents; chunking and embedding configuration part of the dataset version; ingestion check (index twice: same count; edited document replaces the old one)
- Clock fixed per task; live read data from <synthetic fixtures / versioned recordings> per read tool; live vendor sandbox only as a non-gating smoke run
- Write tools: <sandbox or recorder per tool>, test credentials only, CI on `pull_request` with no production secrets; attempted and executed calls recorded; idempotency key or status lookup available: <yes/no per tool>
- Fault injection: <which tasks, which faults, incl. ack lost after commit>
- User simulator: <model, persona prompts version>; validated against <n> real or dogfood conversations on turns, clarifications, volunteered information
- Recorded per trial: transcript (calls, args, results, errors, latency), tokens, cost, stop reason, final state
- Errored trials = failed; error rate reported. Harness faults (simulator, recorder, unmatched recording) rerun and reported separately
- Production settings; oracle visible to scorers only; suite shown to fail against a deliberately broken agent
- Prompt and config version recorded per trial; runs with mixed versions rejected; runtime-read prompts pinned to <version>
- Trials read from telemetry: <no / yes: export checked live before traffic, per-trial readiness wait with deadline, eval sessions sampled at 100%, missing trace = harness fault (rerun, then counted as failed)>
- Run-record contract: fields the scorers read <list>, each with the harness code that writes it; status and stop reason from the fixed lists; a missing field = unscorable, counted against the suite; exit status checked against expected_exit
- Suite read-only to the agent (tests, data, fixtures, scorers, judge prompts); hashes checked before scoring

## 7. Scorers

| Scorer | Dimension | Type | Hard / soft | Inputs | Pass rule |
|---|---|---|---|---|---|

**Judge rubrics** (one per judge): criteria as practical questions, level definitions, weights or gate criteria, JSON output with reasoning first, judge model and family, rubric version.

**Calibration plan:** <50–100> human-labelled cases per gating criterion and task type, labelled by <who>, 20% double-labelled; report κ, false-pass rate, confusion matrix, bias; readiness threshold <starting defaults, confirmed by owner and date: κ ≥ 0.6; false-pass ≤ x%, set by the criterion's severity (e.g. ≤ 5% for a gating grounding criterion)>; recalibrate on judge or rubric change and <quarterly>. Until ready, the judge ranks outputs for human review only. Held-out evaluator for release (not tuned against): <hidden-rubric judge / fresh human-labelled sample / none needed because prompts aren't tuned on judge scores>.
**Schedule:** labels needed <criteria × task types × cases> ÷ capacity <hours/month × measured labels/hour> = <months> until the judge can gate. Measure labels per hour in the first labelling session; do not assume a rate.
**Authoring:** scenarios <n> × minutes per scenario <m> = <hours> of expert time to write expected outcomes (gold documents, required facts), against <expert hours/month> and the launch date; if it doesn't fit, start with the held-out split and a smaller dev split.
**Total expert time:** authoring <h> + labelling <h, double-labelled share included> + calibration rounds <h> = <h> ÷ <expert hours/month> = <months>. The "Before launch" items can finish in <month>. If that is after the launch date: <start with the held-out split, and say so>.

## 8. Metrics and reporting

- Hard-check pass rate (all must pass), with Wilson 95% interval and task count
- pass@1 and pass^<k> (per task, averaged) for side-effecting tasks
- Per-dimension soft scores; breakdown by tag (type, tool, risk, source, language)
- Error rate, harness fault rate, sessions sent / scored / errored; cost and latency per task (median and p95)
- Capability suite and regression suite reported separately
- One production signal beside the offline headline: <complaint or escalation rate, from agent-ops-reviewer>; a rising offline score with a rising production signal means the instrument is broken until explained

## 9. Statistics

| Number | Split | Tasks (n_eff) | Precision |
|---|---|---|---|
| PR / nightly comparisons | Dev | | MDE ≈ <x> points |
| Release rates (pass@1, pass^k, judged quality) | Held-out | | ±<y> points |
| Critical zero-failure bound: <check 1> (one row per critical check) | Dev + held-out | Exercising scenarios only: <n> | < 3/n = <z%> (0 of 15 → about 18 to 20%, whatever the suite size) |
| Critical zero-failure bound: <check 2> | Dev + held-out | Exercising scenarios only: <n> | < 3/n = <z%> |

Every critical-bound row also has a dimension (§4), a scorer (§7), a gate (§10) and a place in the stage preconditions (§12). A code-scored critical check whose scenarios can be generated (access: each restricted document × each caller who must not see it) is sized for the claim, not left at a small n (scorers.md, "Access checks for retrieval").

- d (share of tasks flipping between unchanged runs): <measured / assumed>; ρ for variants: <estimated / unknown, so counted by scenario>
- Comparison method: paired on the same tasks; sign test on flipped tasks; bootstrap over scenarios for pass@1 deltas
- If a needed bound can't be reached before launch: the bound supported is <…>; human approval stays on <action> until <n> clean exercising scenarios, or, with no consequential action, the cohort stage that bound supports (§12)

## 10. Gates

| Tier | Trigger | Runs | Blocks when |
|---|---|---|---|
| Pre-merge | PR touching prompts/tools/models/data | Critical subset, deterministic scorers, 1 trial (cached transcripts only when expectations, labels or scorer code changed); harness slice when harness code changed | Any hard regression or harness-slice failure |
| PR judge run (few PRs/week) or nightly (many) | <choose one> | Dev split, judges, k trials (1 on read-only slices) | Confirmed (rerun) regressions with sign test p < 0.05, or net Δ < −tolerance, on code-scored metrics and calibrated judges only |
| Release | | Hard checks on dev + held-out; rates from held-out; consensus judging | As above, tolerance <2–3%>; critical hard checks 100% on every trial; non-critical floors <x%> with listed limitations; human reads lowest-scoring passes; full harness slice passes |

Tolerance source: <spread of three unchanged runs>. Baseline policy: saved only after review, with dataset and judge versions. Model migrations use the same gate.

## 11. Operations and budget

| Item | Value |
|---|---|
| Suite owner / steward | |
| Labelling budget (annotations/month, who) | |
| Expert time vs launch date: total from §7 (authoring + labelling + calibration) ÷ hours/month, and the month the "Before launch" items finish | |
| Cost per run by tier (agent inference from measured cost per trial + judge + simulator) | |
| Monthly eval spend vs production inference | |
| Eval budget line by tier: cost per day (ideas × tasks × trials × cost per trial) and wall time per run (tasks × trials × median trial time ÷ concurrency) | |
| Error analysis: cadence, who reads failing traces, attribution table (step × share of failing cases) | |
| Flaky-case triage cadence | |
| Hand-off to online monitoring | agent-ops-reviewer: <what it receives: suite, baseline, scorers, tags> |

## 12. Rollout

| When | Deliverable |
|---|---|
| Week 1 | Pin check resolved first (retired: replacement chosen and re-baselined; unchecked: looked up); then the Critical fixes |
| Before launch | |
| After launch (first month) | |

**User-facing stages** (dogfood on real data, pilot, beta, general availability). Before the first one, every critical hard check passes on its exercising slice. A smaller cohort is a size stage, not a substitute for a critical check. If a critical check cannot pass because its control does not exist (for example no per-user access filter while restricted content is in scope), every user-facing stage is blocked: <name the missing control>.

| Stage | Cohort size | Critical checks passed / controls in place | Bound the suite supports | Visible sources, in-product feedback | Human approval on (consequential actions only) |
|---|---|---|---|---|---|
| *Example: 1. Staff dogfood, no logs yet* | *15* | *Access filter in place; boundary test passes* | *Access 0 of 300 generated pairs: < 1%. Injection 0 of 30: < 10%. Held-out hard checks 54 of 60: 80 to 95%* | *Sources shown; thumbs and free text* | *None: no consequential action* |

With no logs yet, a stage's bound comes from the suite alone; later stages add their logs to the real-input slice and re-bound.

## 13. Known gaps and open questions

- Not covered by the offline suite: load, concurrency, rate limits, behaviour at production scale → <load testing / production monitoring owner>
- Open policy decisions (section 3)
- Security tests beyond refusal (implementation, infrastructure, runtime agentic behaviour) → agent-threat-modeler
