# Model plan: <system name>

Prepared <YYYY-MM-DD>. Model names and prices checked on <date> from <provider pages>; re-check before acting.
Status per role is in section 3 (measured, measurable now, provisional).

## 1. Summary

<3 to 5 lines: what changes, expected effect on cost per successful task and p95 latency (direction only if reference numbers are unknown), what must be measured before switching, and the single biggest risk.>

## 2. Inputs and assumptions

| Input | Value | Source (user, code, assumed) |
|---|---|---|
| Volume | <calls or tasks per day> | |
| Current setup | <model@version, effort, per role> | |
| Current cost and p95 | <$/task, s> | |
| Eval assets | <tasks per role, labels, splits> | |
| Labelled data | <counts, per class> | |
| Constraints | <residency, licence, self-hosting, logprobs> | |

Missing inputs and how the plan handles them: <list>

## 3. Roles and recommended models

| # | Role | Risk if wrong | Target (pre-registered) | p95 budget | Recommended class (current example, dated) | Fallback | Why | Status |
|---|---|---|---|---|---|---|---|---|
| 1 | <role and output form> | <low/med/high; reversible?> | <metric ≥ x> | <s> | <class (model@date)> | <stronger model on validation failure> | <one line> | <measured / measurable now / provisional> |

Reference for each role: <incumbent, or the provider's recommended general model>. Top-tier probe: <roles, if any>. Effort settings are in section 4.

Steps replaced by code: <list, with the rule or function that replaces each>

## 4. Reasoning effort

| Role | Starting level | Sweep levels | Expected effect | Decision rule |
|---|---|---|---|---|

## 5. Adaptation decisions

| Failure observed | Knowledge or behaviour | Rung chosen | Entry criteria met? (data, repetition, stability, hosting) | If it fails, next rung |
|---|---|---|---|---|

Fine-tuning verdict: <not now / yes for role X> because <criteria>.

## 6. Training plan (only if a rung at or above fine-tuning is chosen)

- Method and base model: <SFT with LoRA on <open model>, or encoder classifier, or DPO, or GRPO>
- Data: <source, size, verification, splits, per-class counts, no-tool and failure cases>
- Reward (RL only): <gate, partial credit, adversarial tests, independent held-out scorer>
- Comparison: <what the tuned model replaces, on the same held-out tasks: untrained base for generative tuning; best prompted candidate for an encoder classifier>
- Regression set: <general capabilities checked>
- Lifecycle: <versioning, registry, rollback, re-run on next base model, fallback if hosted tuning is withdrawn>

## 7. Bake-off protocol

- Tasks per role and strata: <…>; splits: <dev/test>
- Pre-registered metric, target, non-inferiority margin (not below the smallest detectable at this n), budgets: <…>
- Candidate grid: <models × effort levels × prompt version>
- Fair prompting budget: <…>
- Trials per task: <k>; production settings: <…>
- Scoring: <program checks; judge (family, calibration)>
- Analysis: <paired differences, bootstrap over tasks, sign test on discordant tasks, Wilson intervals>
- Decision rule: <cheapest config passing target, margin, latency, vetoes>
- End-to-end confirmation: <…>
- Rollout hand-off: <shadow, canary, fallback; owner>

## 8. Re-evaluation triggers

<new model or deprecation (with known retirement dates), price change, drift, task change, schedule>

## 9. Hand-offs

<agent-eval-designer: …; agent-ops-reviewer: …; agent-context-designer: …; agent-tool-designer: …>
