# Role-to-model mapping

How to staff each role in an agent with a model class and a reasoning-effort setting before the bake-off confirms it. Model names live in `model-landscape-2026-10.md`; this file uses classes so it stays valid when names change.

## Contents
1. Role catalogue with starting choices
2. Does the step need a model at all?
3. Small versus frontier
4. Reasoning effort per role
5. Calibration and confidence-based routing
6. Open versus closed weights
7. Cost per successful task, not per call
8. Encoders and long inputs

## 1. Role catalogue

| Role | What matters most | Starting class | Starting effort | Step down when | Keep strong when |
|---|---|---|---|---|---|
| Intent router, triage, filter | Throughput, cost, calibrated scores | Code or rules first; else a small prompted model, plus a fine-tuned encoder when labels meet the per-class floor | Off or lowest | Label set is fixed and labelled data exists | Labels are open-ended or change weekly |
| Fixed-label classifier (clause type, ticket category, sentiment) | Accuracy per class, calibration, consistency | Prompted reference model and a smaller prompted model; a fine-tuned encoder or small classifier as a candidate from the start when labels meet the per-class floor (about 50 per class in train) | Off | Labels meet the floor, classes are stable, and the tuned candidate is non-inferior on the test split | Classes need reading long documents with cross-references |
| Field extraction to a schema | Schema-valid rate, field accuracy | Small or mid model with structured output | Off or low | Fields are explicit in the text | Fields need inference across sections, or units and dates are ambiguous |
| Tool caller or executor | Valid arguments, right tool, latency, many calls | Mid model with native tool calling | Off or low | Tool set is small and well described | Many similar tools, long multi-step chains, costly side effects |
| Planner, decomposer | Handles ambiguity and long horizons | Strong general tier (the reference); top tier only as a probe | Sweep; start at the provider default | Plans are short and templated | Open-ended goals, many constraints that must hold together |
| Verifier, critic | Catches real errors, low false-pass rate | Strong model, ideally a different family from the generator; or code | Sweep, often medium or higher | The check can be written in code | Errors are semantic (legal, medical, policy) |
| Final synthesis for users | Accuracy, clarity, faithfulness to evidence | Strong model | Low or medium; raise only on evidence | Output is templated or short | High-stakes advice, long reports, nuanced tone |
| Judge or grader in evals | Agreement with human labels | Different family from the models it grades; calibrated before use | Medium | Never step down below what calibration supports | Always calibrate first |
| Summariser, compressor of history | Faithful, short | Small or mid model | Off or low | Summaries are checked downstream | The summary is the only record a later step sees |

The "starting class" column lists what to put into the bake-off first. The bake-off makes the choice.

The reference for every role is the incumbent configuration if one runs in production, otherwise the provider's recommended general model at its recommended effort. Use the provider's top capability tier only as a probe for roles that miss their target.

Two allocation rules underlie the table. Pay for a stronger model only where stronger reasoning changes the result; sending every step to the strongest model is, in one book's words, lazy architecture disguised as quality. And user-facing, high-risk or state-changing steps deserve more caution than internal, read-only ones.

## 2. Does the step need a model at all?

Replace the model with code when any of these is true:
- The output is a deterministic function of the input (format conversion, arithmetic, date parsing, lookups, routing on a field value).
- A regex or keyword rule gets the target accuracy on the eval.
- The model would be confined so tightly by rules and validation that it hardly decides anything.

Code is free to run, deterministic, and testable. Keep the model for judgement.

## 3. Small versus frontier

A small model (or a fine-tuned encoder) is likely enough when most of these hold:
- The output space is narrow: a fixed label set, a short extraction, one tool choice from a small set, a format rewrite.
- Inputs look like each other and like the training or prompt examples.
- Errors are caught downstream (schema validation, a verifier, human review) or are cheap to retry.
- Volume is high enough that per-call savings multiplied by calls exceed the cost of building and maintaining the eval and any tuning pipeline.
- Latency matters (interactive turns, many calls per task).

Keep a frontier model when the step must handle ambiguity, long-horizon planning, rare long-tail inputs, long documents with cross-references, or final user-facing answers where a mistake is costly.

Watch the hidden cost: a cheap model that emits invalid tool arguments or weak classifications can spend more in retries, repairs and escalations than it saves on the first call. Always compare cost per successful task (section 7).

Small-model conversion loop for an existing agent (after the NVIDIA small-language-model paper and the log-label-tune-distil lifecycle in *The Agentic Enterprise*):
1. Log every model call with role, input, output and outcome.
2. Strip sensitive data.
3. Cluster calls into recurring tasks; rank clusters by volume times cost.
4. For the top clusters, bake off small candidates (prompted first).
5. If prompted small models miss the target, fine-tune on verified examples from the logs (often teacher outputs from the frontier model, checked by a person or a program).
6. Route the cluster to the small model behind a fallback to the strong one; keep logging; retrain periodically.

## 4. Reasoning effort per role

Treat effort (or thinking on/off, or a thinking budget on self-hosted models) as a per-role setting chosen by a sweep, never a global default.

| Role | Default | Raise when | Evidence |
|---|---|---|---|
| Routing, classification, extraction | Off or lowest | Almost never; chain-of-thought adds noise to labels and breaks short machine-readable output | Books agree CoT hurts simple classification and format conversion |
| Single-step tool selection and arguments | Off or low | The eval shows a gain at a higher level | Across five model families, higher reasoning never improved tool choice by more than a point and always added latency; two models were worst at high effort (mid-2025, about 10,000 scored choices) |
| Planning, decomposition, constraint-heavy steps | Provider default, then sweep | Constraint-heavy or multi-tool plans show gains | A reasoning model solved an interlocking-constraint puzzle a standard model rushed (one anecdote); providers recommend higher effort for long agentic coding |
| Verification, critique | Medium, then sweep | False-pass rate drops at higher effort | Verification is where extra thinking most often pays, but measure it |
| Final synthesis | Low or medium | Faithfulness or completeness gains on the eval | Longer reasoning can hurt on distractor-heavy context; agent contexts are distractor-heavy |
| Long autonomous coding or research runs | Provider recommendation (often high) | Sweep including lower levels | On SWE-bench, more overthinking correlated with fewer resolved issues; high effort cost about 3.5 times more for an 8-point gain in one run |

Mechanics that change the answer:
- Reasoning tokens are billed (at output-token prices) and add latency even when hidden. They count against the output cap, so raise `max_tokens` when raising effort.
- On current hosted models effort also changes tool behaviour: lower effort makes fewer, terser tool calls. A sweep therefore has to score the whole step, including whether needed tool calls were made.
- Some models cannot turn thinking off; use their lowest effort as "off".
- Effort levels are recalibrated between model generations. Re-sweep after every model change instead of carrying the setting over.
- Changing effort mid-conversation can invalidate the prompt cache; set it per conversation or per role call, or use a provider's cache-preserving per-message control.
- A router or adaptive thinking is worth it when one endpoint mixes easy and hard requests; "always high" should be an eval result, never a default.

## 5. Calibration and confidence-based routing

If any role routes, escalates or auto-approves on a confidence threshold, the threshold is only meaningful if the model is calibrated: of answers given at 80% confidence, about 80% should be right.

- Measure expected calibration error (ECE): bucket predictions by confidence, compare each bucket's mean confidence with its accuracy, average the gaps weighted by bucket size.
- Use token log-probabilities or a classifier head for confidence. Never use confidence the model states in text: models gave wrong answers with stated confidence of 70% or more while their token probabilities were spread almost evenly, the signature of a guess.
- Few-shot prompting improved both accuracy and calibration over zero-shot in the one measured study, and fine-tuning improved calibration further for every model tested; a fine-tuned encoder was the best calibrated.
- Some closed APIs return log-probabilities only for the top 20 tokens, and some return none. If calibrated scores are a hard requirement, that favours an open model or an encoder for the routing role.
- RLHF-style alignment tends to reduce calibration; do not assume a chat model's probabilities are calibrated without measuring on your labels.

## 6. Open versus closed weights

| Choose | When | Cost of the choice |
|---|---|---|
| Managed closed model | Starting out; workflows still changing; no ML operations staff; top capability needed | Vendor lock-in; tuning (if offered) lives only in the vendor's environment; menus change (one major provider closed its fine-tuning platform to new users in 2026) |
| Managed open-weight model (hosted by a third party) | Want portability and lower price while avoiding GPUs | Check host's data handling; capability gap varies by task |
| Self-hosted open-weight model | Data must not leave your boundary; need token probabilities, LoRA adapters, RL; volume makes GPUs cheaper than tokens | GPUs, serving stack, upgrades and on-call are yours |

Open models' main advantage is transparency and control (weights, logits, any training method), not automatic cost savings; self-hosting has overhead. A common path: managed models while the system takes shape, then in-house open models for the roles where control, customisation or data isolation justify the operations work. Check licences: "open" usually means open weights only, and some licences that allow commercial use still exclude named use cases. Some providers' terms forbid using their outputs to train competing models, which matters for distillation.

## 7. Cost per successful task, not per call
8. Encoders and long inputs

Compare candidates on:

```
cost_per_success = (total spend on the eval run, including retries, reasoning tokens and judge calls) / (tasks that met the role's success definition)
```

and on p95 latency including retries. Add a rough cost for each failure that escapes (human repair, escalation, refund) when that dominates. A model at one fifth of the token price that needs two retries and causes extra escalations may cost more per success than the expensive model.

## 8. Encoders and long inputs

Encoders have a hard maximum input length. Classic BERT-family models stop at 512 tokens; ModernBERT raised this to 8,192 and NeoBERT supports 4,096 (figures from the books, 2025). Legal clauses, emails with threads and tickets with logs can exceed the limit.

1. Measure the token-length distribution of real inputs with the candidate's tokenizer: median, p95, maximum, and the share above the limit.
2. Pick a strategy for inputs over the limit:
   - **Truncate** (keep the head, or head plus tail) when the label signal is local, such as a clause heading or the first lines of a ticket.
   - **Chunk and aggregate**: split into overlapping windows, classify each, and combine. Use the maximum chunk probability for "contains X" labels (a risky clause anywhere) and a length-weighted mean for whole-document labels.
   - **Route by length**: send inputs over the limit to the prompted LLM candidate and keep the encoder for the rest.
3. Score the long-input stratum separately in the bake-off. An encoder can win overall and still fail on the long tail.

