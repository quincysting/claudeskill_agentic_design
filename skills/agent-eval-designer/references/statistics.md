# Eval statistics

None of the source books gives a statistical treatment of evals. The nearest are a rule that a difference should amount to at least three flipped cases [EVALS ch6], a warning that pass@k needs far more trials than k [ILLUSTRATED ch7], and a call for confidence intervals [MESH ch6]. This file applies standard binomial statistics and Miller's "Adding Error Bars to Evals" (external, 2024-11). Every number below was computed with the code at the end.

## A pass rate is an estimate

With n independent tasks and observed rate p, the standard error is √(p(1−p)/n). Report a Wilson interval; it behaves well near 0% and 100%.

Observed 80%:

| Tasks | 95% interval |
|---|---|
| 10 | 49–94% |
| 30 | 63–90% |
| 100 | 71–87% |
| 250 | 75–84% |
| 1,000 | 77–82% |

Tasks needed for a given half-width:

| True rate | ±10 points | ±5 points | ±3 points |
|---|---|---|---|
| 80% | 62 | 246 | 683 |
| 50% | 97 | 385 | 1,068 |

A 30-task suite cannot tell 75% from 85%. 29 of 30 passing is 97% with an interval of about 83 to 99%. Report counts ("29 of 30") with the interval, not "97%". One book's case study reports 99% on 30 to 34 tasks after tuning prompts against those same tasks [EVALS ch14]. The gain from its 20-of-30 baseline is real, but the final level is uncertain by about 16 points and has no held-out confirmation.

## Zero failures is not zero risk

If all n independent tasks pass, the 95% upper bound on the failure rate is about 3/n (rule of three). Repeated trials of one task are not independent, so count distinct tasks, not trials. Variants of one scenario are not fully independent either; see "Correlated tasks" below.
- 30 clean runs are compatible with a 10% failure rate.
- To claim a critical-failure rate below 1%, you need about 300 independent tasks with zero failures (exactly 299).
- 3 of 3 attacks blocked has a 95% lower bound of about 44% on the block rate.

For a safety or "never do X" claim, size the suite from the rate you need to rule out. If the suite can't reach that size before launch, state the bound it does support ("zero failures in 40 tasks: below about 7.5%") and keep a human approval on that action until it can.

## Compare versions paired, on the same tasks

Analyse per-task differences between two versions rather than two separate rates. Shared difficulty cancels, which Miller calls free variance reduction.

With pass/fail outcomes, only tasks where the versions disagree (discordant tasks) carry information. Use an exact sign test on them:
- 3 tasks flipped fail→pass and none back: two-sided p = 0.25. Not evidence.
- 5 one-way flips: two-sided p ≈ 0.06; one-sided p ≈ 0.03.
- 6 one-way flips: two-sided p ≈ 0.03.

"At least three flipped cases" [EVALS ch6] is a floor for a second look, not a significance test. A ten-task model comparison with 9 of 10 against 4 of 10 gives p ≈ 0.06 [DEFGUIDE ch9].

Unpaired (two different task sets, or a reported rate against a published one), at 80% power and α = 0.05:
- 80% → 85% needs about 900 tasks per version;
- 80% → 90% needs about 200.

With repeated trials, compare per-task pass@1 differences with a bootstrap that resamples tasks (code below). If the interval includes zero, the change has not been shown to help. Put that interval in the pull request.

**State the minimum detectable difference.** The best case is a change that flips tasks only one way. Even then, the sign test needs 6 flips (two-sided), so the smallest gain a suite of n tasks can confirm is 6/n: 60 points at n = 10, 20 at n = 30, 6 at n = 100, 1.5 at n = 400. Real changes flip some tasks back, so the practical floor is higher. Put this number in the plan, so nobody reads a 3-point move on 50 tasks as progress.

**Practical estimate.** Measure the discordance rate d: the share of tasks whose pass/fail differs between two runs of the *unchanged* system (from the three baseline runs used to set the tolerance). A paired test then detects a net change of about

  MDE ≈ 2.8 × √(d / n)   (80% power, two-sided α = 0.05; never below 6/n)

| n tasks | d = 0.05 | d = 0.10 |
|---|---|---|
| 75 | 7.2 points | 10.2 points |
| 100 | 6.3 points | 8.9 points |
| 300 | 3.6 points | 5.1 points |
| 1,000 | 2.0 points | 2.8 points |

A simulation at n = 300, d = 0.10 and a true 5-point gain detected it 83% of the time. With clustered tasks (below), use n_eff instead of n. Lowering d also helps: more trials per task, steadier judges, fewer borderline tasks.

## Which split the numbers come from

The task set has a dev split (iterate freely) and a held-out split (scored only for release decisions). They answer different questions, so quote each number from the right one:

| Number | Computed on | Why |
|---|---|---|
| PR and nightly comparisons (paired, sign test) | Dev split | Running held-out on every PR leaks it: people see which tasks fail and tune toward them |
| Hard-check regressions at release | Dev + held-out | Every task must pass anyway; more tasks, more chances to catch a failure |
| Release claims: pass@1, pass^k, judge-scored quality, with intervals | Held-out only | Dev numbers are inflated by tuning; label them "tuned on" if shown |
| Zero-failure bounds for critical behaviour | Dev + held-out, counted as effective independent tasks | The bound comes from the number of clean independent tasks, whichever split they sit in |

**Size the held-out split for the release claim**, not as a fixed percentage. A 300-task suite with 25% held out has 75 release tasks, which gives about ±9 points at 80% and ±7 at 90%. If the release needs ±5, the held-out split alone needs about 250 to 400 tasks. Three ways to get there:
- grow the suite;
- hold out a larger share for release;
- rotate: before each release, write a fresh held-out batch from recent traffic, decide, then fold the old held-out into dev. Rotation also keeps the held-out set current.

## Correlated tasks: count effective tasks

Variants of one base scenario (same task with different phrasing, persona, stress dimension or fixture) tend to pass or fail together. They count for less than their number. With m variants per base scenario and an intra-cluster correlation ρ of pass/fail outcomes:

  n_eff = n / (1 + (m − 1) × ρ)

300 tasks built as 50 scenarios × 6 variants give n_eff ≈ 150 at ρ = 0.2, about 86 at ρ = 0.5, and 50 at ρ = 1.

Rules:
- Give every task a `scenario_id`. Variants share it; genuinely different tasks get their own.
- **Zero-failure bounds:** if ρ is unknown, count scenarios, not variants. 50 clean scenarios bound the rate at about 3/50 = 6%, whatever the variant count. Once you have results, estimate ρ (code below) and use n_eff.
- **Intervals and comparisons:** bootstrap over `scenario_id`, not over task IDs.
- **To raise n_eff, add scenarios, not variants.** Variants are for coverage of stress dimensions; scenarios are for statistical power.

## Trials are not tasks

50 tasks run 5 times are 250 trials, but nowhere near the precision of 250 tasks: a hard task fails repeatedly. Tasks generated from one document, one template or one tool are correlated the same way. Miller found clustered standard errors up to about three times the naive ones on real evals. So:
- compute intervals by resampling tasks, not trials;
- treat near-duplicate tasks as a cluster;
- use repeats to estimate per-task reliability (pass^k) and to reduce noise within each task.

Evaluate the agent at production temperature. Lowering it to cut variance measures a system users never see. The judge is different: make it as reproducible as the provider allows, with temperature 0 [EVALS ch5] where accepted, or a pinned prompt and a majority of three samples on models that reject non-default sampling.

## pass@1, pass@k, pass^k

The same trials give three numbers [ILLUSTRATED ch7]:
- **pass@1**: share of trials that succeed.
- **pass@k**: probability that at least one of k trials succeeds. It measures capability and rises with k.
- **pass^k**: probability that all k trials succeed. It measures reliability and falls with k.

Under independent trials with per-trial success p, pass^k = p^k. At p = 0.9, pass^3 = 0.73 and pass^8 = 0.43. At p = 0.7, pass^8 = 0.06. At p = 0.99, pass^8 = 0.92. Models can tie on pass@1 and differ on both: on one public benchmark two frontier models tied at a pass@1 of 40, while one had the higher pass^3 (28 against 23) and the other the higher pass@3 (60) [ILLUSTRATED ch7].

Use pass^k when a user gets one attempt or actions have side effects. Use pass@k when a verifier allows retrying until success, or when choosing training checkpoints [ILLUSTRATED ch7].

Estimators, with n trials per task and c successes:
- pass@k (unbiased, from the Codex paper) = 1 − C(n−c, k) / C(n, k)
- pass^k (from τ-bench) = C(c, k) / C(n, k)

Both are trustworthy only when n is well above k [ILLUSTRATED ch7]. Compute per task, then average across tasks. A single global p overstates pass^k when some tasks always pass and others always fail.

## Agreement needs a chance baseline

Within-one agreement on a 1 to 5 scale is 52% for two random raters, and about 78% when both use only 3 to 5. Report Cohen's κ (pass/fail), weighted κ or Krippendorff's α (ordinal), and the judge's false-pass rate. With 50 calibration cases, 90% observed agreement has a 95% interval of about 79 to 96%. See llm-judges.md.

## Errors count

If 5% of trials crash and are dropped, a 95% pass rate is an unknown quality level [EVALS ch2]. Score errored trials as failures and report the error rate beside the pass rate.

## Gate noise

If each of 100 passing judge-scored tasks flips by chance with probability 2%, at least one flips in 87% of runs (63% at 1%). A "no new failures" rule on judge-scored tasks therefore mostly measures noise. Rerun flipped tasks three times and count a flip only if the majority agree. At a 2% flip rate the chance of a false confirmed regression across 100 tasks drops to about 0.2%. See ci-gates.md.

## Code (standard library)

```python
import random
from math import comb, sqrt, ceil
from statistics import mean

def wilson(passed, n, z=1.96):
    """95% Wilson interval for passed/n."""
    if n == 0:
        return (0.0, 1.0)
    p, d = passed / n, 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))

def tasks_for_halfwidth(p, half, z=1.96):
    """Tasks needed for a +/- `half` interval around rate p."""
    return ceil(z * z * p * (1 - p) / half ** 2)

def sign_test(worse, better):
    """One-sided exact sign test on discordant tasks: P(>= `worse` of n | no real change).
    Double it (cap at 1) for a two-sided test."""
    n = worse + better
    return sum(comb(n, k) for k in range(worse, n + 1)) / 2 ** n if n else 1.0

def pass_at_k(c, n, k):
    """P(at least one of k trials passes), from c passes in n trials."""
    return 1.0 if n - c < k else 1 - comb(n - c, k) / comb(n, k)

def pass_hat_k(c, n, k):
    """P(all k trials pass), from c passes in n trials."""
    return comb(c, k) / comb(n, k) if c >= k else 0.0

def icc(clusters):
    """Intra-cluster correlation of pass/fail (ANOVA estimator).
    clusters: list of lists of 0/1, one list per scenario_id (pool trials of a task by majority first)."""
    N, k = sum(len(c) for c in clusters), len(clusters)
    p = sum(map(sum, clusters)) / N
    msb = sum(len(c) * (sum(c) / len(c) - p) ** 2 for c in clusters) / (k - 1)
    msw = sum((y - sum(c) / len(c)) ** 2 for c in clusters for y in c) / (N - k)
    m0 = (N - sum(len(c) ** 2 for c in clusters) / N) / (k - 1)
    den = msb + (m0 - 1) * msw
    return max(0.0, (msb - msw) / den) if den else 0.0

def n_eff(n, m, rho):
    """Effective independent tasks: n tasks in clusters of about m variants, correlation rho."""
    return n / (1 + (m - 1) * rho)

def mde(d, n):
    """Approximate minimum detectable paired difference (80% power, two-sided 0.05)."""
    return max(2.8 * sqrt(d / n), 6 / n)

def paired_bootstrap(old, new, boot=2000, seed=0):
    """old/new: {task_id: [bool, ...]} on the same tasks. Mean per-task pass@1 gain, 95% CI.
    Resamples tasks, not trials."""
    ids, rng = sorted(old), random.Random(seed)
    d = {i: mean(new[i]) - mean(old[i]) for i in ids}
    draws = sorted(mean(d[i] for i in rng.choices(ids, k=len(ids))) for _ in range(boot))
    return mean(d.values()), draws[int(0.025 * boot)], draws[int(0.975 * boot)]

if __name__ == "__main__":
    assert [round(x, 2) for x in wilson(24, 30)] == [0.63, 0.9]
    assert tasks_for_halfwidth(0.8, 0.05) == 246
    assert sign_test(5, 0) == 1 / 32 and sign_test(0, 0) == 1.0
    assert pass_hat_k(5, 5, 3) == 1.0 and pass_hat_k(4, 5, 3) == 0.4
    assert abs(pass_at_k(1, 5, 1) - 0.2) < 1e-9
    old = {i: [i % 2 == 0] * 3 for i in range(40)}
    new = {i: [True] * 3 for i in range(40)}
    gain, lo, hi = paired_bootstrap(old, new)
    assert gain == 0.5 and lo > 0
    assert icc([[1] * 6] * 25 + [[0] * 6] * 25) == 1.0 and round(n_eff(300, 6, 0.5)) == 86
    assert round(mde(0.10, 300), 3) == 0.051 and mde(0.0, 100) == 0.06
    print("ok")
```

Usage: `wilson(sum(per_task_pass), n_tasks)` for a headline rate; `mean(pass_hat_k(sum(r), len(r), 3) for r in results.values())` for pass^3; `sign_test(len(newly_failing), len(newly_passing))` for a gate.
