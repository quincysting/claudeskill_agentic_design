# Model bake-off protocol

A side-by-side run of candidate models and settings, per role, on the user's own tasks. It replaces leaderboard reading as the basis for a model choice. Building the eval set and calibrating judges belong to agent-eval-designer; this file says what a model decision needs from that eval and how to run and read the comparison.

## Contents
1. What the eval must provide
2. Pre-register the decision
3. Candidate grid
4. Fair comparison: prompts, harness, provider layer
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
- **Tasks from real traffic**, stratified: common cases, hard cases, edge cases (rare classes, long inputs, ambiguous requests), adversarial cases, and cases where the right action is to do nothing (no tool call, abstain, escalate). Real traffic is de-identified before it becomes a task (personal data and secrets removed or pseudonymised), and it goes to a candidate's provider only where the data owner and the customer terms allow that provider and region; a candidate nobody has vetted for the data runs on synthetic or already-public tasks. Access control, retention and deletion follow agent-eval-designer's "Real user data" rules.
- **Splits:** a dev split for prompt adaptation and a test split never used for tuning anything (details below for small labelled sets).
- **Size:** see the tables in section 7. Rough guide: 30 to 50 tasks can screen out clearly worse candidates; deciding between candidates within about 3 points needs about 200 to 430 paired tasks, depending on how often they disagree (section 7).
- **Labels or checks** a program can apply wherever possible (exact label, schema validity, expected tool and arguments, final state). A rubric judge only for open-ended text, calibrated against about 50 human-labelled cases.
- **Fixed upstream inputs.** Web search results, today's date and live APIs make the same task differ from run to run, which breaks the paired design. For a role whose upstream input is live or time-dependent:
  - record the upstream outputs once per task with a fixed "as of" date (and pass that date wherever the pipeline would inject today's), then replay them into every downstream candidate;
  - bake off the upstream stages on their own, on the same queries, scored on what they return;
  - confirm the assembled pipeline afterwards on live runs (section 9).

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
- **Non-inferiority margin** versus the reference: how much worse a cheaper option may be on the primary metric. Set it to the larger of the business tolerance and the smallest margin the task count can verify (table in section 7), read at the size of the test split the decision is scored on, after dev and few-shot items are carved out. Never pre-register a margin the sample cannot detect; if the business needs a tighter one, label more tasks.
- Budgets: p95 latency per role call, cost per solved task.
- Secondary metrics that can veto: calibration error where thresholds matter, refusal or error rate, tool-call rate on no-tool cases.

## 3. Candidate grid

A candidate is a configuration, not a bare model: model and version, effort, loop (one shot, or a fixed number of check-and-revise rounds) and prompt version, all run under the same harness. Per role, typically 3 to 6 configurations:
- **Reference:** the incumbent configuration if one runs in production; otherwise the provider's recommended general model at its recommended effort. Add the provider's top capability tier only as a probe for roles that miss their target with the reference.
- **Step-downs:** one tier down; the smallest class plausibly able (see `role-model-mapping.md`).
- **Effort sweep** for each reasoning-capable candidate: off or lowest, low, medium, high (and higher levels only for planning or long agentic work). Skip levels a model, or a hosted tool it uses, does not support, and record them as "not supported" (section 4). A role that sends no effort today runs at the provider's default, so setting it explicitly is a saving with no model change: put it first in that role's sweep.
- **Verbosity or output-length sweep** for a role that must write long user-facing output while the default it gets implicitly is terse (low against medium, say). Before building the grid, compare each role's required output length, taken from its prompt or spec, with that default.
- **Constraint-driven options:** an open-weight model if data residency or token probabilities are required; a fine-tuned encoder or small model if the role is fixed-label classification with labelled data.
- **Different family** from the judge, where a judge scores the role.
- **A smaller model in a loop**, where a program can check the role's output (tests, a validator, a schema): the smaller candidate with a fixed number of check-and-revise rounds, next to the larger candidate in one shot. Try this before stepping up to a bigger model. Ng's 2024 compilation of HumanEval results is the illustration: GPT-3.5 zero-shot solved 48.1%, GPT-4 zero-shot 67.0%, and GPT-3.5 inside an iterative agent loop up to 95.1% [NG Agentic Design Patterns Part 1, 2024-03-20]. The figures come from 2024 models on one coding benchmark, are the best of several research methods and report no cost, so carry only the direction into a plan. The loop multiplies calls and tokens, so it wins only if cost and p95 latency per solved task still fit (sections 6 and 8).

Prune the grid with a quick screen on 30 to 50 dev tasks; run the survivors on the full test split.

## 4. Fair comparison: prompts, harness, provider layer

**Prompts.** The incumbent prompt was tuned for the incumbent model, which biases the comparison in its favour.
- Give every candidate the same small adaptation budget on the dev split (for example, up to three prompt edits or one hour), then freeze.
- Use each provider's native tool-calling and structured-output features rather than a lowest-common-denominator format.
- Keep the information content identical: same context, same tools, same examples.
- Record the exact prompt version per candidate.

**Hold one thing fixed.** To compare models, keep the harness, tools, budgets, stop rules and provider layer identical. To compare harnesses (a framework against your own loop, a vendor harness against a neutral one), keep the model fixed. A model win measured under two different harnesses is not a model result. Public leaderboards rank a model and a harness as one entry, and rows also differ in prompts, budgets and versions, so the gaps between rows are observational. One single-author preprint (Arjmandi, 2026-09, https://arxiv.org/abs/2609.11987; 80 tasks, two frontier models) found no reliable average gap with the model held fixed, gaps that varied by task family (a split chosen after seeing the data), and a 1.2 to 1.6 times difference in observed cost per solved task. Treat it as one data point. So the harness can matter as much as a model upgrade on some tasks, or not at all, and it reliably moves cost. Never carry a fixed points gap for "harness versus model" into a plan; report pass rate by task family and cost per solved task. This file owns the bake-off protocol for both comparisons, including which side to hold fixed. For a harness bake-off, the agent-harness-designer skill supplies the harness variants and the harness tests each variant must pass first (its harness-tests.md, section 5).

**A candidate from another vendor.** Some rules ask for a different family: a verifier unlike the generator, a judge unlike the models it grades. If the incumbent runs through a vendor-native client, "provider layer held fixed" and "another family" cannot both hold for that role until you plan the route. Name it: the framework's built-in adapter for other providers, a gateway, or a custom provider class. Run every candidate for that role, the incumbent included, through that one route where possible. Where that is not possible, log the effective request parameters and native stop reasons on both routes and report the route as a variable next to the model. Never claim the provider layer is fixed for that role. An adapter brings its own defaults and stop-reason mapping (the swap-layer example below), so check those on the chosen route before the first run. A route can change features as well as defaults: native structured output, hosted tools, and how reasoning state carries across turns. Check that every feature the role relies on works on the chosen route, or record the difference next to the route variable.

**Resolve effective request settings from source.** What a role sends can differ from its own config line. Read the framework or swap-layer code that builds the request and record, per role:
- the model: the explicit name, or the framework default, including any environment variable or run-level setting that overrides it;
- effort, verbosity and the output cap;
- hosted-tool settings (search context size, maximum uses, extra result fields requested).

Follow the precedence rules in that code, and watch two of them. An explicit settings object passed for any reason (to request one extra response field, say) can suppress the framework's per-model defaults, so the role sends no effort or verbosity at all. And defaults keyed by model name apply only to names in the framework's table, so a name outside it gets none. Then trace a third layer, the run: a run or runner config can replace the agent's model or overlay its settings. A copy of an agent made with a new model name can also re-resolve the defaults for that name, so resolve a copy's settings from the copy, not from the original. Record the result per role in the plan's section 2 with the file and line each value came from. Mark a value you could not trace "unverified" in every table where it appears, and list tracing it as a first action.

In the bake-off, set effort, verbosity and the output cap explicitly for every candidate, the incumbent included, wherever the candidate's API accepts the parameter. Swapping only the model name can silently add or drop framework defaults, and the comparison then measures those defaults along with the model. Some effort levels and output-style controls are unavailable on older models or with some hosted tools. Record "not supported" in that cell instead of sending the parameter: a rejected parameter fails the first call, and an ignored one would make the grid claim a setting that never applied.

**Keep provider swaps cheap, and know what the layer changes.** Route every model call through one thin interface, so trying another provider's model for accuracy, latency or cost is a configuration change [NG Build an Autonomous Agent Using This Simple Recipe!, 2025-12-10]. Switching model providers then costs a few lines of code, while switching orchestration frameworks after an agent is built on one is a lot of work [NG The Falling Cost of Building AI Applications, 2024-12-04], so keep a second provider (an open-weight option included) working from the first prototype [NG What Comes After Tokenmaxxing?, 2026-08-07]. The layer stays cheap only while your code avoids one provider's request features. A swap layer is not neutral either. In aisuite 0.2.0 (released 2026-09-18, read 2026-10-18), the library Ng started for exactly this, the Anthropic adapter:
- sets `max_tokens` to 4,096 when the caller gives none;
- maps any stop reason it does not recognise, a refusal among them, to an ordinary `stop`;
- lifts only a leading system message into the system field [RELATED repo: aisuite/aisuite/providers/anthropic_provider.py].

A bake-off run through such a layer can be measuring the adapter's defaults: one provider looks terse because its output was capped, or compliant because its refusals read as normal stops. Set output limits explicitly per candidate, log what the layer actually sent and the provider's own stop reason (section 5), and rerun the full suite after any change to the layer or its version.

## 5. Running it

- **Same tasks, every candidate** (paired design). Where an upstream input is live or time-dependent, every candidate gets the recorded version (section 1). Randomise run order to spread time-of-day load effects.
- **Production settings, sandboxed effects.** Same context length, tool schemas, timeouts and retry policy as production. Every write, send or spend tool routes to a sandbox, a recorder or a dry-run stub that uses non-production credentials, and production credentials are absent from the bake-off environment. Score the intended call (tool and arguments) or the sandbox's final state. Repeated trials against real tools would issue real refunds, messages or bookings several times per task. Do not lower temperature to reduce variance on the system under test (several current APIs no longer accept sampling parameters anyway). Fix the judge's settings for reproducibility.
- **Repeated trials.** Outputs vary even at temperature 0 (serving-stack batch effects). Use at least 3 trials per task for side-effecting or customer-facing roles and report pass^k; 1 or 2 suffice for screening deterministic-looking classification.
- **Record per call:** raw output, input, output and reasoning tokens, cached tokens, wall-clock latency, retries, errors and refusals, model ID with version and date. Also record the effective request parameters as sent (model, output cap, effort, verbosity, hosted-tool settings, system prompt), hosted-tool calls made, the provider's native stop reason, the route for a cross-vendor candidate (section 4), and the harness and provider-layer versions.
- **Count errors and timeouts as failures.** Dropping them inflates the rate. Where the harness wraps a call and turns errors into empty or null results, count those per candidate as failures too; otherwise a candidate that errors more can look cheaper.
- **Traces are a data destination.** The framework's default trace or telemetry exporter can send prompts and outputs to a third party. Include it in the data-terms check (section 1), especially when a cross-vendor candidate runs, and point it at your own store or turn it off for the bake-off when the terms do not cover it.
- **Cache state:** note whether prompt caching was warm; compare candidates under the same cache conditions.

## 6. Scoring

- Program checks first; judges only for what code cannot decide.
- **An independent success signal.** When a verifier, critic or judge is among the roles being chosen, no role's success is read from that component's verdict, because the signal would move with the candidate under test. Score every role with a scorer that is not a candidate: program checks, or a judge calibrated on human labels.
- **Verifier roles on planted defects.** Build clean items plus items with one planted defect each, grouped by defect type (an unsupported claim, a wrong number, a missing source, say). Report recall per defect type and the false-reject rate on clean items. Size each type with the Wilson table in section 7: about 30 items per type gives 27 of 30 caught as 74 to 97%. For a type that must almost never slip through, use the 3/n rule: 30 planted items with no misses bound the miss rate at about 10%, and 100 at about 3%.
- For tool-calling roles: tool choice (exact), argument accuracy (normalised), schema validity, calls made on no-tool cases, calls per task.
- For classifiers: accuracy, per-class recall, macro-F1, confusion matrix, ECE if thresholds are used (log-probabilities or classifier head, never stated confidence).
- For synthesis: faithfulness to provided evidence, completeness against a checklist, then style.
- Cost per solved task, as defined in `role-model-mapping.md` §7: configuration-level spend, retries, repairs, escalations and hosted-tool fees included, divided by successes, without human review minutes (use agent-ops-reviewer's cost per successful run when variants differ in review time).
- For loop configurations, count every call in the loop, check runs included, and report tokens and p95 latency per solved task. In agentic runs the token volume per task, not the price per call, drives cost (`role-model-mapping.md` §7).

## 7. Analysis and the statistics you need

A pass rate is an estimate. At an observed 80%:

| Tasks | 95% interval (Wilson) |
|---|---|
| 10 | 49 to 94% |
| 30 | 63 to 90% |
| 100 | 71 to 87% |
| 250 | 75 to 84% |
| 1,000 | 77 to 82% |

For a half-width of ±10, ±5 or ±3 points at 80% you need about 62, 246 and 683 tasks. A 30-task suite cannot tell 75% from 85%.

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

  Assume q = 0.10 until a pilot run on 30 to 50 dev tasks measures it. Read the table at the test-split n, not the total labelled count: carving 150 dev and few-shot items out of 300 leaves n = 150.

  The inverse, for planning: to verify a margin m (as a fraction) at discordance q, the test split needs about 1.96² × q / m² tasks. Three points at q = 0.10 needs about 430 tasks (300 verify only 3.6 points); at q = 0.05 it needs about 215 (`tasks_for_margin` in section 12).
- Unpaired designs need far more: detecting 80% versus 85% at 80% power takes about 900 tasks per arm.

**Trials are not tasks.** 50 tasks × 5 trials is not 250 independent observations; hard tasks fail together. Average trials within a task first, then bootstrap over tasks. Tasks generated from the same document or tool are correlated the same way.

**Zero failures is not zero risk.** If n trials all pass, the 95% upper bound on the failure rate is about 3/n.

## 8. Decision rule

For each role, choose the cheapest configuration (by cost per solved task) that:
1. meets the absolute target and any hard floor;
2. is non-inferior to the reference: the lower end of the 95% interval on the paired difference is above minus the margin;
3. meets the p95 latency budget;
4. passes the veto metrics (calibration, refusal rate, no-tool restraint).

Ties: lower p95 latency, then fewer vendors in the system, then the more portable option (open weights, standard API features). If nothing but the reference passes, keep the reference and send the role to the adaptation ladder only if cost or latency is the problem.

Effort: within the chosen model, take the lowest effort level that is non-inferior to its best level.

If the evidence cannot separate two candidates at the available task count, say so and pick on cost and portability, flagged as "not distinguishable at n = …".

## 9. End-to-end confirmation and rollout

Per-role wins interact: a weaker router's misroutes cascade into downstream steps. Run the assembled mixed-model pipeline on the end-to-end set and compare with the all-reference pipeline (paired). Where section 1 replayed recorded upstream inputs, finish with live runs of both pipelines, scored by the same independent scorer. The paired per-task results go to agent-eval-designer's comparison and gates, so the switch passes the same gate as any other change. Then hand off rollout to agent-ops-reviewer: shadow traffic, canary, per-role fallback to the stronger model on validation failure or low calibrated confidence, and production monitoring of the same metrics.

## 10. Re-run triggers

Re-run the bake-off (at least the affected roles) when:
- a provider releases a new model or deprecates one in use (record retirement dates);
- prices change enough to reorder the cost ranking;
- production metrics drift from the bake-off numbers;
- the task, tools or label set change;
- the harness, framework or provider layer changes version (re-run with the model held fixed, so a score change is pinned on the right component);
- a provider changes a model behind an unpinned alias (pin versions where possible);
- otherwise on a fixed schedule (quarterly is common).

Keep the harness, splits and candidate configs versioned so a re-run is a command, not a project.

## 11. Report skeleton

```
Bake-off: <system>, <role>, run <date>
Tasks: n=<…> (test split), strata: <…>; trials per task: <k>
Pre-registered: metric=<…>, target=<…>, margin=<…>, p95 budget=<…>, cost budget=<…>
Held fixed: harness=<name@version>, provider layer=<name@version>, tools, budgets
Set per candidate: effort, verbosity, output cap; route for cross-vendor roles=<adapter/gateway/custom@version, or "differs: logged on both">
Upstream inputs: <live, or recorded as of <date> and replayed>
| Config (model@version, effort, loop rounds, prompt v) | Primary (95% CI) | Paired diff vs reference (95% CI) | b / c | p95 s | Cost/success | Veto metrics |
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

def cost_per_solved_task(total_cost, successes):
    return total_cost / successes if successes else float("inf")

def tasks_for_margin(margin, q, z=1.96):
    """Test-split size needed to verify a non-inferiority margin (fraction) at discordance q."""
    return math.ceil(z * z * q / margin ** 2)

lo, hi = wilson(24, 30)
assert 0.62 < lo < 0.64 and 0.89 < hi < 0.91
assert abs(sign_test(3, 0) - 0.25) < 1e-9 and sign_test(6, 0) < 0.05
base = {i: 1.0 for i in range(100)}
assert non_inferior(base, dict(base), margin=0.02)
worse = {i: (0.0 if i < 10 else 1.0) for i in range(100)}
assert not non_inferior(base, worse, margin=0.02)
assert 420 < tasks_for_margin(0.03, 0.10) < 435 and tasks_for_margin(0.036, 0.10) <= 300
```
