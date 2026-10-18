# Eval plan: <agent name>

*Version <n> · <date> · owner: <name/role> · decision served: <launch go/no-go | version comparison | regression protection | migration>*

## Summary

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
| Model and version, temperature, max steps | |
| Tools (R = read, W = write, W! = irreversible) | |
| Read tools with live data (prices, inventory, balances) | |
| Retrieval sources / memory | |
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
| Harness slice: resume after crash, stop rules, budget exhaustion, cancel, kill switch, kill while paused, edge faults | n/a | | scripted model, hard checks; harness side: agent-harness-designer |
| **Total (dev / held-out)** | | | slice counts must sum to this total |

**Schema:** id, scenario_id, version, clock, prompt or turns, initial_state, success predicates, hard_rules, expected_tools / expect_no_tool, expected_exit, reference (optional), tags (type, tool, difficulty, source, risk, split).

**Versioning and maintenance:** immutable versions with changelog, including fixtures and recordings; validation before each run; expected tools checked against the live registry; quarterly review; incident → task within <1 day>.

## 6. Harness

- Fresh environment per trial: <fixture / sandbox / mock API>
- Clock fixed per task; live read data from <synthetic fixtures / versioned recordings> per read tool; live vendor sandbox only as a non-gating smoke run
- Write tools: <sandbox or recorder per tool>; attempted and executed calls recorded; idempotency key or status lookup available: <yes/no per tool>
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

**Calibration plan:** <50–100> human-labelled cases per gating criterion and task type, labelled by <who>, 20% double-labelled; report κ, false-pass rate, confusion matrix, bias; readiness threshold <κ ≥ 0.6 and false-pass ≤ x%>; recalibrate on judge or rubric change and <quarterly>. Until ready, the judge ranks outputs for human review only. Held-out evaluator for release (not tuned against): <hidden-rubric judge / fresh human-labelled sample / none needed because prompts aren't tuned on judge scores>.
**Schedule:** labels needed <criteria × task types × cases> ÷ capacity <hours/month × measured labels/hour> = <months> until the judge can gate. Measure labels per hour in the first labelling session; do not assume a rate.

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
| Critical zero-failure bound | Dev + held-out | <scenarios or n_eff> | < 3/n_eff = <z%> |

- d (share of tasks flipping between unchanged runs): <measured / assumed>; ρ for variants: <estimated / unknown, so counted by scenario>
- Comparison method: paired on the same tasks; sign test on flipped tasks; bootstrap over scenarios for pass@1 deltas
- If a needed bound can't be reached before launch: the bound supported is <…>; human approval stays on <action> until <n> clean scenarios

## 10. Gates

| Tier | Trigger | Runs | Blocks when |
|---|---|---|---|
| Pre-merge | PR touching prompts/tools/models/data | Critical subset, deterministic scorers, 1 trial (cached transcripts when only scorers or data changed); harness slice when harness code changed | Any hard regression or harness-slice failure |
| PR judge run (few PRs/week) or nightly (many) | <choose one> | Dev split, judges, k trials | Confirmed (rerun) regressions with sign test p < 0.05, or net Δ < −tolerance |
| Release | | Hard checks on dev + held-out; rates from held-out; consensus judging | As above, tolerance <2–3%>; critical hard checks 100% on every trial; non-critical floors <x%> with listed limitations; human reads lowest-scoring passes; full harness slice passes |

Tolerance source: <spread of three unchanged runs>. Baseline policy: saved only after review, with dataset and judge versions. Model migrations use the same gate.

## 11. Operations and budget

| Item | Value |
|---|---|
| Suite owner / steward | |
| Labelling budget (annotations/month, who) | |
| Cost per run by tier (agent inference from measured cost per trial + judge + simulator) | |
| Monthly eval spend vs production inference | |
| Eval budget line by tier: cost per day (ideas × tasks × trials × cost per trial) and wall time per run (tasks × trials × median trial time ÷ concurrency) | |
| Error analysis: cadence, who reads failing traces, attribution table (step × share of failing cases) | |
| Flaky-case triage cadence | |
| Hand-off to online monitoring | agent-ops-reviewer: <what it receives: suite, baseline, scorers, tags> |

## 12. Rollout

| When | Deliverable |
|---|---|
| Week 1 | |
| Before launch | |
| After launch (first month) | |

## 13. Known gaps and open questions

- Not covered by the offline suite: load, concurrency, rate limits, behaviour at production scale → <load testing / production monitoring owner>
- Open policy decisions (section 3)
- Security tests beyond refusal (implementation, infrastructure, runtime agentic behaviour) → agent-threat-modeler
