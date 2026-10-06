# Regression gates in CI

Load this for step 9 of the procedure. The offline suite itself (cases, scorers, judge calibration, sample sizes) comes from **agent-eval-designer**; this file covers how it gates changes.

## 1. What triggers the gate

Run it on every PR that touches prompts, model IDs or parameters, tool definitions or tool code, agent configs, retrieval settings or the eval dataset. Use a path filter so documentation-only PRs skip it. Model migrations and provider switches go through the **same** gate, never a looser one.

## 2. Tiers

| Tier | When | What runs | Budget | Rule |
|---|---|---|---|---|
| Pre-merge fast | Every PR in scope | Deterministic scorers: schema validity, forbidden tools, required steps, step and cost budgets, exact-match fields | Free, under about 30 s (slower pre-merge checks get bypassed) | Any newly failing case fails the build |
| Pre-merge judge | PRs in scope, after the fast job | Full suite with the LLM judge | A few dollars per PR (mid-2026 figures: $1 to $5) | Confirmed regressions and paired test (section 4) |
| Nightly | Main branch | Full suite, all scorers, repeated trials | Moderate | Same rule; opens an issue instead of blocking |
| Release | Before promotion to canary | Full suite plus held-out split, consensus judging | Larger | Tolerance 2 to 3%, zero confirmed new failures on hard checks, and a person reads the five lowest-scoring passing cases |

**Judge on every PR or nightly?** With a few prompt or model PRs a week, run the judge on every PR in scope so the author sees the effect before merging. With dozens of PRs a day, keep pre-merge deterministic and catch semantic regressions nightly, accepting a day's delay.

## 3. Setting the tolerance

1. Run the unchanged system three times on the suite.
2. Measure the spread of the pass rate and the per-case flip rate between runs.
3. Set the tolerance just above that spread. A starting point of 5% for PRs and 2 to 3% for release is common; 0% raises constant false alarms because judge scores vary, and 15% lets real drops through.
4. Re-measure whenever the judge model, rubric or dataset changes.

A real 2-point change on a 100-case suite is invisible to any gate. If the decision needs that resolution, grow the suite (sizing in **agent-eval-designer**).

## 4. Why "fail on any flipped case" is wrong for judged cases

If each of 100 passing judge-scored cases flips by chance with probability 2% per run, at least one flips in 87% of runs (63% at 1%). A gate that fails on any single flip is red most of the time and engineers learn to ignore it.

- **Deterministic checks**: zero tolerance. Any newly failing case fails the gate.
- **Judge-scored cases**: rerun each flipped case (3 reruns, majority vote) and count it only if it fails again. With a 2% flip rate this cuts the chance of a false confirmed regression on 100 cases to about 0.2%. Then test the net change with a one-sided paired sign test on the confirmed flips, and fail if the net drop exceeds the tolerance.
- Key cases by a stable case ID, never by input text (shared preambles collide).
- Pin the judge model and rubric version, and include both in any verdict-cache key. A cache keyed only on scorer name, output and expected answer silently reuses old verdicts after a judge upgrade.

Gate script (standard library; plug in your harness's `run_case`):

```python
"""regression_gate.py BASELINE.json CANDIDATE.json  -> exit 1 blocks the merge.
Each file maps case_id -> {"hard_pass": bool, "soft_pass": bool}."""
import json, sys
from math import comb

def p_worse(worse, better):
    """One-sided exact sign test on discordant cases: P(>= worse of n | no real change)."""
    n = worse + better
    return sum(comb(n, k) for k in range(worse, n + 1)) / 2 ** n if n else 1.0

def confirmed(run_case, cid, want, reruns=3):
    return sum(run_case(cid)["soft_pass"] == want for _ in range(reruns)) > reruns // 2

def gate(baseline, candidate, run_case, tolerance=0.03, alpha=0.05):
    hard, worse, better = [], [], []
    for cid, base in baseline.items():
        cand = candidate.get(cid, {"hard_pass": False, "soft_pass": False})  # missing counts as failed
        if base["hard_pass"] and not cand["hard_pass"]:
            hard.append(cid)
        elif base["soft_pass"] != cand["soft_pass"] and confirmed(run_case, cid, cand["soft_pass"]):
            (better if cand["soft_pass"] else worse).append(cid)
    delta = (len(better) - len(worse)) / max(len(baseline), 1)
    p = p_worse(len(worse), len(better))
    print(json.dumps({"hard_regressions": hard, "confirmed_worse": worse, "confirmed_better": better,
                      "net_delta": round(delta, 3), "p_worse": round(p, 3)}, indent=2))
    return 1 if hard or delta < -tolerance or p < alpha else 0

if __name__ == "__main__":
    from harness import run_case            # yours: runs one case on the candidate, returns its scores
    base, cand = (json.load(open(f)) for f in sys.argv[1:3])
    sys.exit(gate(base, cand, run_case))
```

How to read it: five confirmed regressions and no improvements give p ≈ 0.03 and fail; four give p ≈ 0.06 and pass the sign test, but on a 100-case suite a net −4% already exceeds a 3% tolerance.

## 5. Wiring and reporting

```yaml
# .github/workflows/agent-evals.yml (shape only; adapt runner, secrets, paths)
on:
  pull_request:
    paths: ["prompts/**", "agent/**", "tools/**", "evals/**", "config/models.*"]
jobs:
  fast:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: python evals/run.py --scorers deterministic --out cand_fast.json
      - run: python evals/regression_gate.py evals/baseline_fast.json cand_fast.json
  judge:
    needs: fast
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: python evals/run.py --scorers all --out cand.json
      - run: python evals/regression_gate.py evals/baseline.json cand.json > gate_report.json
```

- Post the three lists to the PR (hard regressions, confirmed worse, confirmed better) as well as the verdict, because reviewers act on named cases. For non-engineers, translate the red build into user impact: "three billing queries now produce incorrect refund amounts".
- Include in every report: dataset version, agent version, model ID, judge model and rubric version, run cost and wall-clock time.
- Also run the **fallback model** through the suite on a schedule: a fallback that has never passed the gate is not a fallback.

## 6. Baselines and flaky cases

- A baseline exists from before the first change. Save a new one only by decision, after reviewing the diff; never automatically on green.
- Never promote "the best of N experiments" straight to baseline: after many runs on a small set the maximum is inflated by luck. Confirm the winner on the held-out split.
- Report counts with intervals ("29 of 30, 95% CI 83 to 99%"), not bare percentages from small sets.
- Triage flaky cases weekly: tighten the rubric, widen that scorer's tolerance, or move a chronically borderline case out of the automated suite into periodic human review.

## 7. What evaluation costs (mid-2026 figures from the eval literature; recheck)

| Scorer | Cost per verdict | Latency |
|---|---|---|
| Deterministic check | free | under 1 ms |
| Embedding comparison | about $0.0001 | fast |
| Small-model judge | $0.001 to $0.005 | 0.5 to 1.5 s |
| Mid-size judge | $0.005 to $0.02 | 1 to 3 s |
| Claim-level faithfulness | $0.02 to $0.10 | 3 to 10 s |
| Human annotation | $0.50 to $5.00 | minutes to hours |

| Stage | Frequency | Typical cost |
|---|---|---|
| Full suite with judge during development | each prompt change | $0.50 to $2 per run |
| CI deterministic | every commit | $0 |
| CI full suite with judge | every PR | $1 to $5 per PR |
| Production sampled LLM eval | continuous, about 5% | scales with volume |
| Weekly comprehensive eval and calibration | weekly | $5 to $20 |
| Human annotation round | monthly | $50 to $500 |

Cost falls by ordering (deterministic first so clear failures skip the judge), caching verdicts for unchanged outputs (key includes judge model and rubric version), concurrency, the cheapest adequate judge per scorer, and batch pricing for scheduled runs (about half price). Tiering plus caching typically cut eval spend by more than half. A cheaper judge is not free: a small model agreed with a mid-size one on faithfulness only about 82% of the time in one comparison, so calibrate before switching. A 20-minute pre-merge eval is a cost too; developers route around it.
