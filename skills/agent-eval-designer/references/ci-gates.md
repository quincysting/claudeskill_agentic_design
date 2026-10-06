# Offline regression gates

How the offline suite gates changes. Online evals, production sampling, alerting, shadow and canary releases are out of scope; they belong to agent-ops-reviewer, which consumes the suite and baseline defined here.

## What triggers a run

Every PR that touches prompts, tool definitions, model configuration, agent code, retrieval configuration or the dataset. Use a path filter so documentation-only PRs skip it [EVALS ch6]. Model migrations and judge upgrades trigger a full run too.

## Baseline

A baseline is a saved report: dataset version, agent version (prompt, model, tools), judge model and rubric version, and per-task results keyed by stable task ID [EVALS ch6].
- Save one before the first change. Without it there is nothing to compare against [EVALS ch6].
- Save a new baseline only by decision, after a person has reviewed the diff, never automatically after a green run [EVALS ch13].
- A baseline is valid only for its judge and dataset versions. When either changes, rerun the unchanged agent first and save that as the new baseline, so the next comparison isolates the agent change [EVALS ch5].

## Gate rules

| Check type | Rule | Why |
|---|---|---|
| Deterministic hard checks (state predicates, forbidden tools, preconditions, schema, budgets) | Any task that passed in the baseline and fails now blocks the merge | Deterministic checks don't flicker; a new failure is real |
| Judge-scored or stochastic tasks | A flip counts only if a majority of 3 reruns reproduce it; then block if the net change is below −tolerance or the one-sided sign test on confirmed flips gives p < 0.05 | Single flips are mostly noise |
| Overall pass rate | Block if below a floor agreed for the release (e.g. "regression suite ≥ 98%"); see "Floors versus zero tolerance" | Catches slow erosion across PRs |
| Error rate | Block if above about 5% | Systematic breakage [EVALS ch2] |
| Cost and latency per task | Warn (or block) above a stated budget | A "better" version at twice the cost is a trade-off someone must accept explicitly [SYSTEMS ch14] |

**Tolerance.** Run the unchanged system three times and set the tolerance just above the spread you observe [EVALS ch6]. A tolerance of 0% raises constant false alarms because judge scores vary; 15% lets real drops through. 5% is a common starting point, 2 to 3% at release [EVALS ch6].

**Why not "any new failure blocks".** The EVALS book's regression detector flags a regression if any previously passing case now fails, and its release gate demands zero new failures [EVALS ch6]. On judge-scored cases this mostly measures noise. If each of 100 passing cases flips by chance with probability 2%, at least one flips in 87% of runs. CI turns red most of the time and engineers learn to ignore it, which the same book describes [EVALS ch6]. Keep zero tolerance for deterministic checks only.

**Floors versus zero tolerance.** Two different rules, often confused:
- *Zero tolerance* applies to **regressions**: a task that passed its hard checks in the baseline and fails now.
- A *floor* is an **absolute level** for the release: the share of tasks that pass all hard checks.

Whether a floor may sit below 100% depends on the check:

| Hard check | Floor at release (dev + held-out) | What to do with a failure |
|---|---|---|
| Critical: irreversible or money action without consent, duplicate charge, wrong account, cross-customer data access, forbidden tool executed | 100%, every trial. One confirmed failure in any trial blocks | Fix, add variants of the failing task, rerun |
| Non-critical hard checks: step or cost budget exceeded, schema slip that the system recovers from | Below 100% allowed, set per check (e.g. ≥ 98%) | Each failing task reviewed and listed as a known limitation with an owner |
| Capability-suite tasks (new features) | No floor; tracked as a rate | Moved to the regression suite once they pass |

For stochastic agents a critical check can fail in 1 of 5 trials. That trial failed, and the floor counts trials, not tasks: users get that failure rate. Report pass^k for the critical slice and block on any failure. A per-trial floor below 100% on a critical check is a decision for the product owner to sign, with a human approval on the action until the rate is bounded (statistics.md, "Zero failures is not zero risk").

**Flaky tasks.** Triage weekly. Tighten the rubric, widen that scorer's tolerance, or move a chronically borderline task out of the automated suite into periodic human review. EVALS calls the last option underused [EVALS ch6].

## Tiers

| Tier | Runs | Content | Budget |
|---|---|---|---|
| Pre-merge (every relevant PR) | Minutes at most | Deterministic scorers on a tagged critical subset (about 30 to 50 tasks, mostly incident cases [EVALS ch2]), 1 trial, run concurrently, dev split | Scoring is free, but running the agent is not (see "Agent inference cost"). EVALS targets under about 30 s because slower pre-merge checks get bypassed [EVALS ch6]; with an agent in the loop, that is reachable only with a small concurrent subset. When only scorers or the dataset changed, re-score cached transcripts instead of rerunning the agent |
| PR judge run (a few relevant PRs a week) | Minutes | Full dev split with judges, 3 trials per task where outputs vary | Judge $1–5 per run at mid-2026 prices [EVALS ch11], plus agent inference |
| Nightly (dozens of PRs a day) | Up to an hour | Same as the PR judge run, on the day's main branch | Same |
| Release | Before shipping | Hard checks on dev + held-out; release rates and intervals from held-out only (statistics.md, "Which split"); consensus judging; 5+ trials on side-effecting tasks; tolerance 2–3%; a person reads the five lowest-scoring passing cases [EVALS ch6] | Higher; accepted |

Judge on every PR or nightly? With a few prompt PRs a week, run the judge on every PR that touches prompts, models, tools or datasets so the author sees the effect before merging. With dozens of PRs a day, keep pre-merge deterministic and catch semantic regressions nightly, accepting a day's delay [EVALS ch6][EVALS ch15].

## Report format on the PR

Lead with named tasks, not the verdict. Reviewers act on named tasks [EVALS ch6]:

```
EVAL GATE: BLOCKED   dataset v2026-10-01.3 · judge model-X@2026-09 rubric v4 · 312 tasks × 3 trials
Hard regressions (2):   book-intl-044 (charged twice), cancel-hold-009 (no confirmation before cancel)
Confirmed worse (3):    faq-baggage-012, change-date-031, refund-tax-007
Confirmed better (1):   search-multi-city-002
Net pass@1: 0.871 → 0.861 (paired Δ −0.010, 95% CI −0.024 to +0.004) · sign test p = 0.31
pass^3 (side-effecting tasks): 0.74 → 0.71 · error rate 0.6% · cost/task $0.041 → $0.047 (+15%)
```

For non-engineers, translate a red build into user impact: "three billing queries now produce incorrect refund amounts" [EVALS ch6].

## Gate code (standard library)

```python
import json
from math import comb

def p_worse(worse, better):
    """One-sided exact sign test: P(at least `worse` of n confirmed flips | no real change)."""
    n = worse + better
    return sum(comb(n, k) for k in range(worse, n + 1)) / 2 ** n if n else 1.0

def confirmed(rerun, task_id, want, reruns=3):
    """A soft flip counts only if a majority of reruns reproduce it."""
    return sum(rerun(task_id)["soft_pass"] == want for _ in range(reruns)) > reruns // 2

def gate(baseline, candidate, rerun, tolerance=0.03):
    """baseline/candidate: {task_id: {"hard_pass": bool, "soft_pass": bool}}. Returns exit code."""
    hard, worse, better = [], [], []
    for tid, base in baseline.items():
        cand = candidate.get(tid, {"hard_pass": False, "soft_pass": False})   # missing = failed
        if base["hard_pass"] and not cand["hard_pass"]:
            hard.append(tid)
        elif base["soft_pass"] != cand["soft_pass"] and confirmed(rerun, tid, cand["soft_pass"]):
            (better if cand["soft_pass"] else worse).append(tid)
    delta = (len(better) - len(worse)) / len(baseline)
    p = p_worse(len(worse), len(better))
    print(json.dumps({"hard_regressions": hard, "confirmed_worse": worse,
                      "confirmed_better": better, "net_delta": round(delta, 3), "p_worse": round(p, 3)}))
    return 1 if hard or delta < -tolerance or p < 0.05 else 0
```

Reading it: 5 confirmed regressions and no improvements give p ≈ 0.03 and block. 4 give p ≈ 0.06 and pass the sign test, but on a 100-task suite the net −4% already exceeds a 3% tolerance. A real 2-point change on 100 tasks is invisible to any gate; the suite has to grow (statistics.md).

## Model migrations, optimisers, best-of-many

- **Same gate for model migrations.** A migration validator that calls a model change safe whenever the pass rate falls by no more than the tolerance, however many cases regress, is looser than the gate on a one-line prompt edit. One book's companion code does exactly that. Run the migration through the full gate and read every regressed task before deciding.
- **Recalibrate the judge** if the migration also changes the judge model.
- **Best of many experiments.** After twenty experiments on 30 tasks, the best pass rate is inflated by luck. Confirm the winner on the held-out split before saving it as the baseline [EVALS ch13].
- **Automated prompt optimisers** (DSPy and similar) are proposal generators. Their output goes through the same gate, with a held-out set the optimiser never saw.

## Cost

Mid-2026 figures from [EVALS ch11]; check current prices. The table covers scoring. Its "$0" for deterministic CI means the scorers cost nothing; running the agent to produce the transcripts is extra, and for multi-step agents it is usually the larger cost.

| Stage | Eval | Frequency | Typical cost |
|---|---|---|---|
| Development | Full suite with judge | Every prompt change | $0.50–2.00 per run |
| CI | Deterministic only | Every commit | $0 |
| CI | Full suite with judge | Every PR | $1–5 per PR |
| Weekly | Full eval plus judge calibration check | Weekly | $5–20 |
| Monthly | Human annotation round | Monthly | $50–500 |

- A 200-case run with a judge and faithfulness checks costs about $12. Ten iterations in an afternoon cost about $120, or about $15 when cases that fail cheap checks skip the judge and verdicts on unchanged outputs are cached [EVALS ch11].
- Budget heuristic: eval spend at 5 to 15% of production inference spend, with a floor of about $10 to 20 a month for small systems [EVALS ch11].
- Batch APIs roughly halve judge cost for scheduled runs [EVALS ch11].
- Trials multiply cost: 300 tasks × 3 trials × a $0.01 judge call is $9 per run before agent inference. Agent inference for multi-step tasks often costs more than judging; measure it per task.
- Wall-clock time is a cost too: a 20-minute eval blocks developers [EVALS ch11]. Run trials concurrently.

### Agent inference cost per run

Estimate it before promising a cadence:

  cost per run ≈ Σ over task slices of (tasks × trials × cost per trial) + judge verdicts × judge price + simulator calls (multi-turn)

- **Measure cost per trial; don't guess it.** Run 10 to 20 trials per task type in week 1. The harness records tokens and cost per trial (datasets-and-harness.md, requirement 4). Take the median and the p95 per slice.
- **Why it's larger than it looks.** A multi-step agent re-sends its growing context on every model call, so input tokens grow roughly with steps × average context length. Prompt caching cuts the repeated prefix. Retries and recovery paths in stress tasks cost more than happy paths.
- **Illustrative arithmetic** (hypothetical prices; substitute your own): 300 tasks × 3 trials × 8 model calls × 6,000 input tokens is about 43M input tokens per run. At $1 per million input tokens that is about $43 before output tokens, judges and simulator calls.
- **Fit trials to budget by risk.** Use pass^k trials (3, or 5 at release) on side-effecting and customer-facing slices. Read-only, low-risk slices get 1 trial in nightly runs and 3 at release. The pre-merge subset gets 1 trial. Write the per-tier cost into the plan next to the cadence, and check it against the 5 to 15% of production inference heuristic above.

## Tooling

Keep scorers and datasets in your own code behind thin adapters (about 20 lines each) to whatever platform you use. One author's teams switched observability platforms twice in 18 months. Before adopting a platform, confirm that datasets, annotations with provenance, per-case results and scorer configs export in bulk [EVALS ch12]. Tool names and features change fast (as of 2026-10); choose on these principles, not feature grids.
