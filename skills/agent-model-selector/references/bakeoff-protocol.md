# Model bake-off protocol

A side-by-side run of candidate models and settings, per role, on the user's own tasks. It replaces leaderboard reading as the basis for a model choice. Building the eval set and calibrating judges belong to agent-eval-designer; this file says what a model decision needs from that eval and how to run and read the comparison.

## Contents
1. What the eval must provide
2. Pre-register the decision
3. Candidate grid
4. Fair prompting
5. Running it
6. Scoring
7. Analysis and the statistics you need
8. Decision rule
9. End-to-end confirmation and rollout
10. Re-run triggers
11. Report skeleton
12. Helper code

## 1. What the eval must provide

Per role:
- **Tasks from real traffic**, stratified: common cases, hard cases, edge cases (rare classes, long inputs, ambiguous requests), adversarial cases, and cases where the right action is to do nothing (no tool call, abstain, escalate).
- **Splits:** a dev split for prompt adaptation and a test split never used for tuning anything (details below for small labelled sets).
- **Size:** see the tables in section 7. Rough guide: 30 to 50 tasks can screen out clearly worse candidates; deciding between candidates within about 3 points needs about 300 or more paired tasks (table in section 7).
- **Labels or checks** a program can apply wherever possible (exact label, schema validity, expected tool and arguments, final state). A rubric judge only for open-ended text, calibrated against about 50 human-labelled cases.

End to end: a smaller set of full tasks scored on the final outcome, to confirm the assembled pipeline.

Plus a **general regression set** if any candidate is a tuned generative model.

**Splitting a small labelled set** (one set feeding both training and evaluation, such as 3,000 labelled items):
1. Carve out the test split first, stratified by class, and never touch it until the final comparison. Take about 20%, but aim for at least 30 test items per class: per-class recall on 24 items has a wide interval (20 of 24 correct is 64 to 93%; 27 of 30 is 74 to 97%). If rare classes cannot reach 30, oversample them into the test split and reweight overall metrics to production class frequencies, or merge them, or report them as "not measurable at this n".
2. Use the rest for development. Few-shot examples and prompt edits for prompted candidates come only from here.
3. For a trainable candidate (encoder or small classifier), run 5-fold stratified cross-validation on the development portion for hyperparameters and the learning curve. Then train once on all of it and score once on the test split, next to every other candidate.
4. Every candidate is scored on the same test items, so the comparison stays paired.

**When labels are expensive** (expert time): have experts review model-drafted labels instead of labelling from scratch, and size each role's set by the margin it must verify (section 7) rather than by habit. For a comparison between two candidates, only the items where they disagree change the difference, so label those first; add a random sample of agreed items to estimate absolute accuracy. Roles without labels stay provisional while roles with labels are measured; do not hold the whole plan back.

## 2. Pre-register the decision

Write these down before running anything, so the result cannot move the goalposts:
- Primary metric per role (accuracy, macro-F1, tool-call exact match, schema-valid rate, rubric pass rate, pass^k for side-effecting roles).
- Absolute target per role, and a hard floor if any (for example, no class below 80% recall).
- **Non-inferiority margin** versus the reference: how much worse a cheaper option may be on the primary metric. Set it to the larger of the business tolerance and the smallest margin the task count can verify (table in section 7). Never pre-register a margin the sample cannot detect; if the business needs a tighter one, label more tasks.
- Budgets: p95 latency per role call, cost per successful task.
- Secondary metrics that can veto: calibration error where thresholds matter, refusal or error rate, tool-call rate on no-tool cases.

## 3. Candidate grid

Per role, typically 3 to 6 configurations:
- **Reference:** the incumbent configuration if one runs in production; otherwise the provider's recommended general model at its recommended effort. Add the provider's top capability tier only as a probe for roles that miss their target with the reference.
- **Step-downs:** one tier down; the smallest class plausibly able (see `role-model-mapping.md`).
- **Effort sweep** for each reasoning-capable candidate: off or lowest, low, medium, high (and higher levels only for planning or long agentic work). Skip levels a model does not support.
- **Constraint-driven options:** an open-weight model if data residency or token probabilities are required; a fine-tuned encoder or small model if the role is fixed-label classification with labelled data.
- **Different family** from the judge, where a judge scores the role.

Prune the grid with a quick screen on 30 to 50 dev tasks; run the survivors on the full test split.

## 4. Fair prompting

The incumbent prompt was tuned for the incumbent model, which biases the comparison in its favour.
- Give every candidate the same small adaptation budget on the dev split (for example, up to three prompt edits or one hour), then freeze.
- Use each provider's native tool-calling and structured-output features rather than a lowest-common-denominator format.
- Keep the information content identical: same context, same tools, same examples.
- Record the exact prompt version per candidate.

## 5. Running it

- **Same tasks, every candidate** (paired design). Randomise run order to spread time-of-day load effects.
- **Production settings.** Same context length, tools, timeouts and retry policy as production. Do not lower temperature to reduce variance on the system under test (several current APIs no longer accept sampling parameters anyway). Fix the judge's settings for reproducibility.
- **Repeated trials.** Outputs vary even at temperature 0 (serving-stack batch effects). Use at least 3 trials per task for side-effecting or customer-facing roles and report pass^k; 1 or 2 suffice for screening deterministic-looking classification.
- **Record per call:** raw output, input, output and reasoning tokens, cached tokens, wall-clock latency, retries, errors and refusals, model ID with version and date.
- **Count errors and timeouts as failures.** Dropping them inflates the rate.
- **Cache state:** note whether prompt caching was warm; compare candidates under the same cache conditions.

## 6. Scoring

- Program checks first; judges only for what code cannot decide.
- For tool-calling roles: tool choice (exact), argument accuracy (normalised), schema validity, calls made on no-tool cases, calls per task.
- For classifiers: accuracy, per-class recall, macro-F1, confusion matrix, ECE if thresholds are used (log-probabilities or classifier head, never stated confidence).
- For synthesis: faithfulness to provided evidence, completeness against a checklist, then style.
- Cost per successful task = total spend (including retries, reasoning tokens, judge calls if they are part of the production loop) divided by successes.

## 7. Analysis and the statistics you need

A pass rate is an estimate. At an observed 80%:

| Tasks | 95% interval (Wilson) |
|---|---|
| 10 | 49 to 94% |
| 30 | 63 to 90% |
| 100 | 71 to 87% |
| 250 | 75 to 84% |
| 1,000 | 77 to 82% |

For a half-width of ±10, ±5 or ±3 points at 80% you need about 61, 246 and 683 tasks. A 30-task suite cannot tell 75% from 85%.

**Compare paired, on the same tasks.** Only tasks where the two configurations disagree carry information. Count discordant tasks: b = reference passes and candidate fails, c = candidate passes and reference fails.
- An exact sign test on (c, b): three one-way flips give p = 0.25; about six one-way flips are needed for p < 0.05.
- For a non-inferiority decision use the interval on the mean paired difference (bootstrap over tasks). With a fraction q of tasks discordant and no true difference, the 95% half-width is about 1.96 × √(q/n). That half-width is the smallest margin you can verify:

| Tasks n | q = 0.05 | q = 0.10 | q = 0.20 |
|---|---|---|---|
| 50 | 6.2 | 8.8 | 12.4 |
| 100 | 4.4 | 6.2 | 8.8 |
| 150 | 3.6 | 5.1 | 7.2 |
| 300 | 2.5 | 3.6 | 5.1 |
| 500 | 2.0 | 2.8 | 3.9 |
| 1,000 | 1.4 | 2.0 | 2.8 |

  Assume q = 0.10 until a pilot run on 30 to 50 dev tasks measures it.
- Unpaired designs need far more: detecting 80% versus 85% at 80% power takes about 900 tasks per arm.

**Trials are not tasks.** 50 tasks × 5 trials is not 250 independent observations; hard tasks fail together. Average trials within a task first, then bootstrap over tasks. Tasks generated from the same document or tool are correlated the same way.

**Zero failures is not zero risk.** If n trials all pass, the 95% upper bound on the failure rate is about 3/n.

## 8. Decision rule

For each role, choose the cheapest configuration (by cost per successful task) that:
1. meets the absolute target and any hard floor;
2. is non-inferior to the reference: the lower end of the 95% interval on the paired difference is above minus the margin;
3. meets the p95 latency budget;
4. passes the veto metrics (calibration, refusal rate, no-tool restraint).

Ties: lower p95 latency, then fewer vendors in the system, then the more portable option (open weights, standard API features). If nothing but the reference passes, keep the reference and send the role to the adaptation ladder only if cost or latency is the problem.

Effort: within the chosen model, take the lowest effort level that is non-inferior to its best level.

If the evidence cannot separate two candidates at the available task count, say so and pick on cost and portability, flagged as "not distinguishable at n = …".

## 9. End-to-end confirmation and rollout

Per-role wins interact: a weaker router's misroutes cascade into downstream steps. Run the assembled mixed-model pipeline on the end-to-end set and compare with the all-reference pipeline (paired). Then hand off rollout to agent-ops-reviewer: shadow traffic, canary, per-role fallback to the stronger model on validation failure or low calibrated confidence, and production monitoring of the same metrics.

## 10. Re-run triggers

Re-run the bake-off (at least the affected roles) when:
- a provider releases a new model or deprecates one in use (record retirement dates);
- prices change enough to reorder the cost ranking;
- production metrics drift from the bake-off numbers;
- the task, tools or label set change;
- a provider changes a model behind an unpinned alias (pin versions where possible);
- otherwise on a fixed schedule (quarterly is common).

Keep the harness, splits and candidate configs versioned so a re-run is a command, not a project.

## 11. Report skeleton

```
Bake-off: <system>, <role>, run <date>
Tasks: n=<…> (test split), strata: <…>; trials per task: <k>
Pre-registered: metric=<…>, target=<…>, margin=<…>, p95 budget=<…>, cost budget=<…>
| Config (model@version, effort, prompt v) | Primary (95% CI) | Paired diff vs reference (95% CI) | b / c | p95 s | Cost/success | Veto metrics |
Decision: <config> because <rule 1–4>. Not distinguishable: <…>.
Caveats: <judge agreement, cache state, small strata>
```

## 12. Helper code (standard library)

```python
import math, random, statistics

def wilson(successes, n, z=1.96):
    """95% interval for a pass rate."""
    if n == 0:
        return (0.0, 1.0)
    p = successes / n
    d = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / d
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (centre - half, centre + half)

def sign_test(c, b):
    """Exact two-sided p-value on discordant tasks: c = only candidate passed, b = only reference passed."""
    n, k = c + b, min(c, b)
    if n == 0:
        return 1.0
    return min(1.0, 2 * sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n)

def paired_diff(base, cand, iters=4000, seed=0):
    """Mean per-task difference (cand - base), 95% bootstrap interval over tasks.
    base, cand: {task_id: score in [0, 1], averaged over that task's trials}."""
    d = [cand[t] - base[t] for t in sorted(base)]
    rng = random.Random(seed)
    boots = sorted(statistics.fmean(rng.choices(d, k=len(d))) for _ in range(iters))
    return statistics.fmean(d), boots[int(0.025 * iters)], boots[int(0.975 * iters) - 1]

def non_inferior(base, cand, margin):
    """True if the lower 95% bound of (cand - base) is above -margin."""
    return paired_diff(base, cand)[1] > -margin

def cost_per_success(total_cost, successes):
    return total_cost / successes if successes else float("inf")

lo, hi = wilson(24, 30)
assert 0.62 < lo < 0.64 and 0.89 < hi < 0.91
assert abs(sign_test(3, 0) - 0.25) < 1e-9 and sign_test(6, 0) < 0.05
base = {i: 1.0 for i in range(100)}
assert non_inferior(base, dict(base), margin=0.02)
worse = {i: (0.0 if i < 10 else 1.0) for i in range(100)}
assert not non_inferior(base, worse, margin=0.02)
```
