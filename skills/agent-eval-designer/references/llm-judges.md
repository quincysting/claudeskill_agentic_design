# LLM judges: design, calibration, human labels

A judge is a measuring instrument and needs testing like one. Everyone agrees on deterministic checks first and human calibration [EVALS ch1][DEFGUIDE ch9][SYSTEMS ch14][ILLUSTRATED ch7]. The disagreement is about how far to trust a judge by default. One book says a well-built judge reaches 80 to 90% agreement with people, citing no source [EVALS ch5]. The likely origin is the MT-Bench study, which measured pairwise preferences between chat answers, not agent outcomes, and documented position, verbosity and self-enhancement bias in the same paper (Zheng et al., external, 2023-06). Others warn that a judge can "make bad judgment scalable" [SYSTEMS ch14] and say not to trust evaluations whose criteria you cannot see [DLLMA ch5]. **Rule:** quote no agreement figure for a judge until you have measured one on your own task with a chance-corrected statistic. Until then, use judge scores to rank outputs for human review [DEFGUIDE ch8].

Ng makes the same point from practice: a rubric judge on free-form output beats nothing, but can be too noisy to show whether a tweak helped [NG We Need Better Evals for LLM Applications, 2024-05-29]. Even a calibrated judge's verdict on one change needs paired reruns before anyone acts on it (ci-gates.md, "Gate rules"), and whatever can be checked against a label belongs in code (scorers.md).

## Rubric design

The judge receives the task input, the agent's output (or transcript), the rubric and optionally a reference. It returns a score and a reason per criterion as JSON [EVALS ch5].

1. **Ask the workflow's practical questions**, not "rate the quality". For a code-review agent: is the finding real, is it grounded in the changed lines, is the severity justified, should this comment be shown [SYSTEMS ch14]. For a support agent: is every stated fact supported by a tool result, does the reply match what was executed, should a human have been involved. Generic quality prompts reward fluency.
2. **Three to five criteria**, each tied to the task. More than about seven dilutes focus [EVALS ch5].
3. **Define every score level**, e.g. 1 = factual errors, 3 = correct but incomplete, 5 = correct and complete [EVALS ch5]. Binary criteria (true/false) are easier to calibrate than 1 to 5 scales; prefer them where the decision is binary anyway. Write the levels for this dimension. A scale copied from a template for another dimension (a faithfulness scale on a tone judge), or one whose top level asks only for a polite, on-topic reply, has no level a fluent wrong answer would land in. Test it before use: a known fluent-but-wrong output must score below the top level.
4. **Make correctness a gate, not just a weight.** In EVALS's example the weights are correctness 0.4, completeness 0.3, clarity 0.2 and conciseness 0.1; a fluent wrong answer scoring 1, 2, 5 and 5 averages 2.5 and fails a 3.0 threshold [EVALS ch5]. It fails only because completeness is low too. With three criteria (correctness 0.4, clarity 0.3, conciseness 0.3), the same wrong answer scores 0.4 + 1.5 + 1.5 = 3.4 and passes. A weight alone cannot stop fluent wrong answers, so fail the case if correctness is below 3, whatever the rest.
5. **Reason before score.** Ask for the reasoning field first; the reason is what makes a failure actionable [EVALS ch5].
6. **Lowest-variance settings** for the judge, within what the provider and API version accept. Use temperature 0 [EVALS ch5] where the provider accepts it, and check each provider's own parameter support. For Claude judges, omit `temperature`, `top_p` and `top_k`: as of 2026-10, API version 2026-10-21 returns a 400 error for any value on every model, even the default, and on 2023-06-01 a non-default value fails on Claude 4.7 and later (Anthropic's deprecations page and the 2026-10-21 migration guide, checked 2026-10-25). Get repeatability instead from a pinned model version, pinned prompt and rubric versions, fixed inputs, structured output, the majority (or median) of three judge samples, and calibration against human labels. The agent runs at production settings.
7. **Version the rubric like code.** Store its calibration results with it [SYSTEMS ch14][EVALS ch5].

Example output contract:

```json
{
  "reasoning": "Reply says the refund is $49.00; refund_item result shows 49.00. Mentions 3-5 days, which policy doc supports.",
  "criteria": {
    "claims_supported_by_tool_results": true,
    "reply_matches_executed_actions": true,
    "policy_followed": true,
    "should_have_escalated": false,
    "tone_ok": 4
  },
  "pass": true
}
```

Compute `pass` in code from the criteria (gate criteria all true, soft criteria above threshold). Do not trust a `pass` or aggregate score the judge reports about itself.

## Judge strength and family

- With a reference answer and a narrow rubric, a mid-tier judge often works. One book trusts a mid-tier judge from another family after spot-checking about 5% of verdicts [BUILDAGENTIC ch4].
- For reference-free judgments (faithfulness, helpfulness, policy), use a strong judge. A small model agreed with a mid-size one on faithfulness verdicts only about 82% of the time, mostly missing implicit support [EVALS ch11]. A judge weaker than the system under test is a common mistake [EVALS ch5].
- Use a different model family than the agent, to avoid self-preference [ILLUSTRATED ch7][EVALS ch7].
- Measure agreement either way; the choice is empirical.

## Known biases and mitigations

| Bias | Mitigation |
|---|---|
| Verbosity: longer answers score higher | Criterion for conciseness, length-normalised scoring, calibration cases with long wrong answers [EVALS ch5] |
| Position: first (or second) option favoured in pairwise | Run both orders; count a win only if it holds in both [ILLUSTRATED ch7] |
| Self-preference: favours its own family's style | Judge from another family [ILLUSTRATED ch7] |
| Identity: told which model, prompt or version wrote the output | Strip model names, version tags and provider-specific formatting; randomise order; run both orders. On a past unblinded run, re-score a sample blind once to estimate the bias |
| Authority: confident tone or citations sway it | Require claims to be checked against provided evidence |
| Leniency: everything gets 4s and 5s | Tighten upper score levels; positive bias versus humans signals this [EVALS ch5] |

Ensembles help on high-stakes runs. Take the median of three judges from different families, and send cases where they differ by 0.4 or more on a 0 to 1 scale to a person. This triples cost, so keep it for model migrations and release gates [EVALS ch5].

## Calibration protocol

1. **Sample 50 to 100 cases per task type** from real outputs [EVALS ch5]. Include passes, failures, borderline cases and outputs that sound right but are wrong. If failures are rare, oversample them; a judge that says "pass" to everything looks accurate on a set of passes. The quickest source of sound-right-but-wrong cases is the divergence list: trials a reference-free judge scored high while a reference-based or state check failed (scorers.md, "Divergence check").
2. **A person labels them blind** with the same rubric. Two people label at least 20% of them, to measure human agreement too [EVALS ch9].
3. **Run the judge** on the same cases at its production settings.
4. **Report:**

| Statistic | Target | Why |
|---|---|---|
| Confusion matrix on the pass/fail decision | — | Shows where it errs |
| **False-pass rate**: judge pass among human fails | As low as the risk demands; state it | Lets bad outputs through; this is what matters for gates |
| False-fail rate | Low enough not to bury reviewers | Creates noise and reruns |
| Cohen's κ on pass/fail | Report it; κ below about 0.6 means the judge is not ready to gate | Corrects for chance agreement |
| Weighted κ or Krippendorff's α for 1–5 scores | Report | Same, for ordinal scales |
| Within-one agreement (1–5 scale) | Above 80% [EVALS ch5] | Only meaningful next to the chance baseline below |
| Correlation with human scores | Above 0.7 [EVALS ch5] | |
| Bias (judge mean minus human mean) | Within ±0.3 [EVALS ch5] | Positive means lenient: tighten upper levels |
| Mean absolute error | Below 0.8 [EVALS ch5] | |
| Interval on agreement | Report it | With 50 cases, 90% observed agreement has a 95% interval of about 79–96% |

The κ ≥ 0.6 cut-off is a common rule of thumb for "substantial" agreement, not a book figure. Set the false-pass ceiling from the cost of a bad output reaching a user.

**Starting defaults** (this skill's suggestion; the owner confirms or changes them, and the plan records who and when): κ ≥ 0.6 on pass/fail, and a false-pass ceiling set by the criterion's severity, for example ≤ 5% for a gating grounding criterion and looser for a soft tone criterion. Measure the false-pass rate on enough human-failed cases to bound it: 3 judge passes among 40 human fails is 7.5% with a Wilson interval of about 3 to 20%, so the calibration set needs failures, oversampled if they are rare.

**Chance baseline.** Two raters scoring 1 to 5 at random agree within one point 52% of the time. If both use only 3, 4 and 5, random agreement within one point is about 78%. So the 80% target can be met by raters who barely agree [EVALS ch5][EVALS ch9]. One worked example reports exact agreement of 0.40 beside within-one agreement of 0.87 and calls it healthy [EVALS ch9]. The book's companion agreement and calibration code reports within-one rate, mean difference, correlation and bias, with no chance correction. Add κ yourself.

5. **Fix and repeat.** Rewrite ambiguous levels, add worked examples to the rubric, split criteria that mix two things, then rerun calibration on fresh cases. Do not tune the rubric on the same cases you report agreement on.
6. **Calibrate per task type.** A judge calibrated on refunds is not calibrated on bookings.
7. **Recalibrate when the judge model, its version or the rubric changes**, and on a schedule (quarterly). In one example a judge upgrade moved a baseline from 91% to 84% with no change to the system [EVALS ch5]. A quarterly human round found a tone scorer had drifted 0.3 points on a 5-point scale over six months [EVALS ch9]. Pin the judge model version and put it, with the rubric version, in every verdict cache key.

```python
def kappa(a, b):
    """Cohen's kappa for two lists of categorical labels (e.g. human vs judge pass/fail)."""
    n = len(a)
    po = sum(x == y for x, y in zip(a, b)) / n
    pe = sum((a.count(c) / n) * (b.count(c) / n) for c in set(a) | set(b))
    return 1.0 if pe == 1 else (po - pe) / (1 - pe)

def false_pass_rate(human, judge):
    """Share of human-failed cases the judge passed. Inputs: lists of booleans (True = pass)."""
    fails = [j for h, j in zip(human, judge) if not h]
    return sum(fails) / len(fails) if fails else float("nan")   # nan: no failures to test on
```

## Held-out evaluator

When people iterate prompts against judge scores, the prompt learns the rubric's wording, just as it learns the dev split. Keep at least one release-time evaluator nobody tunes against: a judge whose rubric the prompt authors don't see, or a fresh human-labelled sample. Calibrate it like any other judge; being hidden doesn't make it right. Report its score next to the visible judges. A growing gap between them means the prompt is learning the rubric rather than the task. A hidden judge guards the rubric, not the data, so it doesn't replace the held-out split (statistics.md, "Which split the numbers come from").

## Labelling schedule

Calibration needs more labels than a busy expert gives in a month, so do the arithmetic before promising a date.

- **Labels needed** = gating criteria × task types × 50 to 100 cases. Add second-rater time for the 20% double-labelled; that second rater can be an engineer.
- **Monthly capacity** = expert hours × labels per hour. Measure the rate: time the expert's first 20 labels. Binary criteria on short transcripts go much faster than 1 to 5 scales on long multi-step traces.
- **Months to calibrate** = labels needed / monthly capacity.

- **Authoring time.** Expected outcomes cost expert time too: gold documents, required facts, success predicates. Authoring hours = scenarios × minutes per scenario. 200 scenarios at an assumed 10 minutes each is about 33 hours, or about five and a half months of an expert who gives 6 hours a month. Check the sum (labels plus authoring) against the launch date before promising a suite size; if it does not fit, write the held-out split first and grow dev after launch.

Illustrative arithmetic (the labelling rate is an assumption; measure yours): 2 gating criteria × 1 task type × 60 cases is 120 labels. At 2 expert hours a month and 25 labels an hour that is 50 labels a month, so about 2.5 months.

If that is too slow:
- move criteria into code checks;
- make criteria binary;
- calibrate one criterion per round, highest risk first;
- show the labeller only the span that matters (the tool calls and the reply, not the whole trace);
- have an engineer pre-label, and spend the expert's time on blind labels of a sample plus adjudicating disagreements.

Until a criterion is calibrated, code checks gate and the judge only ranks outputs for review.

## Human annotation as an operation

People calibrate judges, break ties and judge subjective qualities [EVALS ch9]. Annotators and judge providers see real user data only after de-identification, and only where the data terms allow it (datasets-and-harness.md, "Real user data").
- **Budget.** About 50 annotations a month (roughly two expert hours) is a workable minimum [EVALS ch9].
- **What to annotate.** Cases where scorers disagree (a spread of 0.3 or more): if annotators also disagree, the rubric is ambiguous; if they side with one scorer, the other is off. Sample about 70% failures and 30% passes to catch false passes [EVALS ch9].
- **Quality controls.** Hide known-answer gold questions in 10 to 20% of each batch and double-annotate at least 20%. Keep batches under 50 and guidelines to one page with three examples [EVALS ch9].
- **Labels that become tests.** Ask reviewers to classify failures ("false positive: guarded upstream", "wrong amount", "should have escalated"), not just reject them. The label becomes the next task [SYSTEMS ch14].
- **Tools.** A spreadsheet or terminal below about 200 annotations a month; an open-source tool (Label Studio, Argilla) from 200 to 2,000; custom above that [EVALS ch9]. As of 2026-10; check current options.
