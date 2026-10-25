# Model plan: <system name>

Prepared <YYYY-MM-DD>. Model names and prices checked on <date> from <provider pages> (or "not refreshed, unpriced", with the refresh as the first action); re-check before acting.
Status per role is in section 3 (measured, measurable now, provisional).

## 1. Summary

<3 to 5 lines: what changes, expected effect on cost per solved task and p95 latency (direction only if reference numbers are unknown; with no prices, a savings ranking by calls and tokens per run, labelled as a ranking), what must be measured before switching, and the single biggest risk.>

## 2. Inputs and assumptions

| Input | Value | Source (user, code, assumed) |
|---|---|---|
| Volume | <calls or tasks per day> | |
| Current setup | <model@version, effort, per role> | |
| Harness and provider layer | <framework or own loop @version; swap layer @version> | |
| Current cost and p95 | <$/task, s> | |
| Eval assets | <tasks per role, labels, splits> | |
| Labelled data | <counts, per class> | |
| Constraints | <residency, licence, self-hosting, logprobs> | |

Effective request settings per role, as the framework or swap layer sends them (not the role's own config line):

| Role | Model (explicit / framework default / env override) | Effort | Verbosity | Output cap | Hosted-tool settings | Traced to (file:line), or "unverified" |
|---|---|---|---|---|---|---|

A value marked "unverified" stays marked in sections 3, 4 and 7, and tracing it is a first action.

Missing inputs and how the plan handles them: <list>

## 3. Roles and recommended models

| # | Role | Risk if wrong | Target (pre-registered) | p95 budget | Recommended class (current example, dated) | Fallback | Why | Status |
|---|---|---|---|---|---|---|---|---|
| 1 | <role and output form> | <low/med/high; reversible?> | <metric ≥ x; "(assumed)" in this cell if no owner set it> | <s> | <class (model@date)> | <stronger model on validation failure> | <one line> | <measured / measurable now / provisional> |

Reference for each role: <incumbent, or the provider's recommended general model>. Top-tier probe: <roles, if any>. Effort settings are in section 4.

Steps and sub-checks replaced by code: <list, with the rule or function that replaces each; include checks taken out of a role's prompt (exact match, set membership, counts, length limits)>

## 4. Reasoning effort

| Role | Starting level | Sweep levels | Expected effect | Decision rule |
|---|---|---|---|---|

Verbosity or output-length sweep: <roles whose required output is longer than the default they get implicitly, and the levels swept; levels a model does not accept are marked "not supported">

## 5. Adaptation decisions

| Failure observed | Knowledge or behaviour | Rung chosen | Entry criteria met? (data, repetition, stability, hosting) | If it fails, next rung |
|---|---|---|---|---|

If no failures are logged yet, list the first hypotheses, mark each row "(assumed)", and make labelling real failures the first bake-off output.

Fine-tuning verdict: <not now / yes for role X> because <criteria>.

## 6. Training plan (only if a rung at or above fine-tuning is chosen)

- Method and base model: <SFT with LoRA on <open model>, or encoder classifier, or DPO, or GRPO>
- Data: <source, size, verification, splits, per-class counts, no-tool and failure cases>
- Privacy and rights: <personal data and secrets removed or pseudonymised by …; training use and the tuning provider and region allowed by <data owner, terms>; retention; deletion requests and retrain trigger; extraction test before release>
- Reward (RL only): <gate, partial credit, adversarial tests, independent held-out scorer>
- Comparison: <what the tuned model replaces, on the same held-out tasks: untrained base for generative tuning; best prompted candidate for an encoder classifier>
- Regression set: <general capabilities checked>
- Checkpoint and serving: <checkpoint chosen by validation metric; base pinned to a revision and mirrored; training-serving parity test>
- Lifecycle: <versioning, registry, rollback, re-run on next base model, fallback if hosted tuning is withdrawn>

## 7. Bake-off protocol

- Tasks per role and strata: <…>; splits: <dev/test>
- Pre-registered metric, target, non-inferiority margin (not below the smallest detectable at this n), budgets: <…>
- Candidate grid: <models × effort levels × loop (one shot, or k check-and-revise rounds) × prompt version>; effort, verbosity and output cap set explicitly for every candidate, the incumbent included, where its API accepts them ("not supported" otherwise)
- Held fixed across candidates: <harness, tools, budgets, provider layer @version>; effective request parameters and native stop reasons logged
- Cross-vendor roles: <route (framework adapter, gateway or custom provider @version) used by every candidate, or "routes differ: parameters and stop reasons logged on both, route reported as a variable"; features the role relies on (structured output, hosted tools, reasoning carried across turns) checked on the route>
- Live or time-dependent upstream inputs: <recorded once per task as of <date> and replayed; upstream stages baked off on their own; live confirmation run>
- Hosted tools: <tool, settings, fee per call; a swap of a provider-hosted tool runs as a harness comparison with the model fixed>
- Fair prompting budget: <…>
- Trials per task: <k>; production settings: <…>; side-effecting tools: <sandbox / recorder / dry-run stub>, non-production credentials
- Task data: <de-identified; providers and regions allowed to receive it; where the framework's trace or telemetry exporter sends data>
- Failures counted: <errors, timeouts, refusals, and errors a wrapper turns into empty or null results, per candidate>
- Scoring: <program checks; judge (family, calibration); independent of any verifier or judge being chosen; for verifier roles, a planted-defect set with recall per type and false-reject rate on clean items, sized per type>
- Analysis: <paired differences, bootstrap over tasks, sign test on discordant tasks, Wilson intervals>
- Decision rule: <cheapest config passing target, margin, latency, vetoes>
- End-to-end confirmation: <…>
- Rollout hand-off: <shadow, canary, fallback; owner>

## 8. Re-evaluation triggers

<new model or deprecation (with known retirement dates), price change, drift, task change, schedule>

## 9. Hand-offs

<agent-eval-designer: …; agent-ops-reviewer: …; agent-context-designer: …; agent-tool-designer: …>
