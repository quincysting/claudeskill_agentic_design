# Eval plan: <agent name>

*Version <n> · <date> · owner: <name/role> · decision served: <launch go/no-go | version comparison | regression protection | migration>*

## Summary

- **Decision:** <what this suite decides, and by when>
- **Suite:** <N tasks (dev N / held-out N) in S scenarios, n_eff ≈ …>, <k> trials on side-effecting tasks; release rates within ±<Y> on the held-out split; detects ≥ <X> points between versions (MDE ≈ 2.8 × √(d / n), d = <measured or assumed>)
- **Hard gates:** <three to five checks that block any release>
- **Top risks addressed:** <1>, <2>, <3>
- **Build first:** <what exists by end of week 1>

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

**Composition:**

| Slice | Scenarios | Tasks | Notes |
|---|---|---|---|
| Per tool (<tool>) | | | |
| Multi-tool chains | | | |
| No tool needed | | | assert zero calls |
| Must ask / must refuse / must escalate | | | no write while info missing (hard) |
| Stress variants (ambiguity, missing info, partial tool failure, intent switch, injected instruction) | | | |
| Lost acknowledgement on writes (timeout after commit, duplicate message, restart) | | | exactly one write |
| Multi-turn (simulated persona) | ≥ 20 | | |
| Safety: misuse / manipulation through data / benign-task harm | | | attack design: agent-threat-modeler |
| **Total (dev / held-out)** | | | |

**Schema:** id, scenario_id, version, clock, prompt or turns, initial_state, success predicates, hard_rules, expected_tools / expect_no_tool, reference (optional), tags (type, tool, difficulty, source, risk, split).

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

## 7. Scorers

| Scorer | Dimension | Type | Hard / soft | Inputs | Pass rule |
|---|---|---|---|---|---|

**Judge rubrics** (one per judge): criteria as practical questions, level definitions, weights or gate criteria, JSON output with reasoning first, judge model and family, rubric version.

**Calibration plan:** <50–100> human-labelled cases per gating criterion and task type, labelled by <who>, 20% double-labelled; report κ, false-pass rate, confusion matrix, bias; readiness threshold <κ ≥ 0.6 and false-pass ≤ x%>; recalibrate on judge or rubric change and <quarterly>. Until ready, the judge ranks outputs for human review only.
**Schedule:** labels needed <criteria × task types × cases> ÷ capacity <hours/month × measured labels/hour> = <months> until the judge can gate.

## 8. Metrics and reporting

- Hard-check pass rate (all must pass), with Wilson 95% interval and task count
- pass@1 and pass^<k> (per task, averaged) for side-effecting tasks
- Per-dimension soft scores; breakdown by tag (type, tool, risk, source, language)
- Error rate, harness fault rate; cost and latency per task (median and p95)
- Capability suite and regression suite reported separately

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
| Pre-merge | PR touching prompts/tools/models/data | Critical subset, deterministic scorers, 1 trial (cached transcripts when only scorers or data changed) | Any hard regression |
| PR judge run (few PRs/week) or nightly (many) | <choose one> | Dev split, judges, k trials | Confirmed (rerun) regressions with sign test p < 0.05, or net Δ < −tolerance |
| Release | | Hard checks on dev + held-out; rates from held-out; consensus judging | As above, tolerance <2–3%>; critical hard checks 100% on every trial; non-critical floors <x%> with listed limitations; human reads lowest-scoring passes |

Tolerance source: <spread of three unchanged runs>. Baseline policy: saved only after review, with dataset and judge versions. Model migrations use the same gate.

## 11. Operations and budget

| Item | Value |
|---|---|
| Suite owner / steward | |
| Labelling budget (annotations/month, who) | |
| Cost per run by tier (agent inference from measured cost per trial + judge + simulator) | |
| Monthly eval spend vs production inference | |
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
