---
name: agent-model-selector
description: Chooses a model and reasoning-effort setting for each role in an agent system (router, classifier, tool caller, planner, verifier, synthesiser) and decides how to adapt roles that fall short, climbing prompt, then examples and retrieval, then a stronger model, then fine-tuning (SFT, DPO, LoRA), then RL (GRPO) with entry criteria for each step. Produces a per-role model plan with justification and a bake-off protocol run on the user's own eval set. Covers small versus frontier, open versus closed weights, calibration, and reward design including reward hacking. Use for "which model should my agent use", "should I fine-tune", "fine-tune vs RAG", "what reasoning effort", "small language model for agents", "RL for agents", "model bake-off", or when one expensive model runs every step. Not for building the eval set (agent-eval-designer), serving cost or router infrastructure (agent-ops-reviewer), architecture (agent-architect), retrieval and memory (agent-context-designer) or tool schemas (agent-tool-designer).
---

# Agent Model Selector

This skill produces a model plan for an agent system: which model class and reasoning effort each role uses, what to do about roles that miss their targets, and a bake-off protocol that proves the choices on the user's own tasks. The stance: measure every role against a strong reference (the incumbent, or the provider's recommended general model), then step down only where a paired eval shows the target still holds. Treat reasoning effort as a per-role setting you measure. Change weights last, for behaviour and never for facts. Model names and prices go stale within months, so the plan names roles and classes first and dated examples second.

## When to use / when not to

Use when someone:
- is choosing models for a new agent or for one step of an existing agent;
- runs every step on one frontier model and wants lower cost or latency;
- asks whether to fine-tune, fine-tune or use RAG, use RL, or use a small model;
- asks what reasoning effort or thinking budget to use;
- is re-evaluating after a new model release, a price change or a deprecation notice;
- is planning a training run (SFT, DPO, GRPO) and needs the data, reward or evaluation design.

Hand off instead:
- **agent-eval-designer** builds the task set, judges and statistics machinery. This skill states what the bake-off needs from it.
- **agent-ops-reviewer** covers serving cost, caching, batching, quantisation, runtime routing infrastructure, shadow and canary rollout, and monitoring.
- **agent-architect** covers workflow versus agent, number of agents and orchestration shape.
- **agent-context-designer** covers retrieval, memory and context layout. Knowledge gaps go there.
- **agent-tool-designer** covers tool names, descriptions and schemas. Wrong-tool errors often start there, not in the model.
- **agent-threat-modeler** covers data leaving the boundary, poisoned training data and the safety of tuned models.
- **agentic-business-case** decides whether the project pays at all.

## Inputs to gather first

Ask for these, or find them in the code: model IDs in config, prompt files, eval folders, logs. If an input is missing, state an assumption and carry it into the plan's "Inputs and assumptions" table.

1. **Roles.** Every distinct model call: what it does, its input, its output form (label, JSON, tool call, prose), who consumes it, and whether it triggers side effects.
2. **Targets per role.** Quality metric and threshold, p95 latency budget, cost budget per task, calls per day, and the consequence of an error (reversible? user-facing? money, legal or safety?). If only an end-to-end latency target exists, split it across the calls on the critical path (sequential calls add up; parallel ones do not) and say so as an assumption.
3. **Current state.** Models and versions, effort or thinking settings, prompts, current scores, cost per task and p95 latency.
4. **Eval assets.** Labelled cases per role and end to end: how many, how the labels were made, whether a held-out split exists. Note which roles have labels and which do not.
5. **Failure evidence.** Which failures occur, how often, with examples.
6. **Adaptation data.** Logged traces, labelled examples with per-class counts, and success signals a program can check.
7. **Constraints.** Data residency and privacy, licences, approved vendors, ability to self-host (GPUs, ML operations staff), need for token probabilities.
8. **Change rate.** How often labels, policies and tools change.

## Procedure

### 1. Map the roles; remove the ones that need no model
Build the role table (template section 3). For each role, ask whether code, a rule, a regex, a lookup or a classifier would reach the target. If a model would be fenced in so tightly by rules that it hardly decides anything, use code. Classify each remaining role by kind: route or classify, extract, call tools, plan, verify or judge, synthesise for users, summarise. See `references/role-model-mapping.md` §1 and §2.

### 2. Confirm the measuring instrument
Do not choose models without an eval. Per role you need tasks from real traffic with checkable labels, a dev split and a test split, and enough tasks for the decision (`references/bakeoff-protocol.md` §1, §7). If they are missing, write down what the eval must contain, hand off to agent-eval-designer, and mark the plan "provisional: unmeasured". You can still give starting choices from the decision guide.

Give each role its own status (measured, measurable now, or provisional) and measure the roles you can now instead of holding everything back. When labels are expensive (expert time), have experts review model-drafted labels rather than label from scratch. For a comparison between two candidates, label first the cases where they disagree, because only those change the difference; add a random sample of agreed cases to estimate absolute accuracy. Splitting a small labelled set and per-class minimums: `references/bakeoff-protocol.md` §1.

### 3. Set the reference
The reference is the configuration every step down must stay close to. Choose it this way:
- If a configuration runs in production, the incumbent is the reference.
- If nothing runs yet, the reference is the provider's recommended general-purpose model (the "start here" model on its model page) at its recommended effort, not the most expensive tier.
- Use the top capability tier only as a probe, on roles that miss their target with the reference, to learn whether capability is the limit. If the probe also misses, no model swap will fix that role; it goes to step 7.

Record per role: quality, p50 and p95 latency, cost per successful task and a labelled failure list; record end-to-end success too. If reference numbers are not available yet, the summary states the expected direction (cheaper, faster) and what will be measured, without invented percentages.

### 4. Shortlist candidates per role
Pick 2 to 4 candidates per role using decision guide table A: one tier below the reference, the smallest class that could plausibly cope, and an open-weight option when the constraints call for one. For a fixed-label classification role whose labels meet table E1, a fine-tuned encoder or small classifier is a candidate from the start: training one is cheap and the result is a measurement, so it enters the bake-off instead of waiting for a later rung. If the current vendor's cheapest tier is only a small step down, add another vendor's small tier or a self-hosted open-weight model where the constraints allow (`references/model-landscape-2026-10.md`). Use public leaderboards only to shortlist. Take model names from `references/model-landscape-2026-10.md` after refreshing them as that file describes, and date every name and price you write down.

### 5. Run the bake-off
Follow `references/bakeoff-protocol.md`. Pre-register the metric, target, non-inferiority margin and budgets. Use the same tasks for every candidate, with an equal prompt-adaptation budget for each. Run at production settings, with repeated trials, an effort sweep for reasoning-capable models, and cost per successful task. Compare paired results with intervals. Set each non-inferiority margin no smaller than what the task count can detect (table F); if the business needs a tighter margin, label more tasks or mark the choice provisional.

### 6. Choose per role and set effort
For each role, take the cheapest configuration by cost per successful task that meets the target, is non-inferior to the reference within the margin, fits the latency budget, and passes the veto metrics. Within the chosen model, use the lowest effort level that is non-inferior to its best level. Defaults before measurement are in table B. Then run the assembled mixed-model pipeline end to end against the all-reference pipeline, because a weaker router's errors cascade downstream. Give each stepped-down role a fallback, such as a retry on the stronger model when validation fails or calibrated confidence is low.

### 7. Adapt the roles that still miss
Label 20 to 50 failures per role as a knowledge gap or a behaviour gap (`references/adaptation-ladder.md` §2). Knowledge gaps go to retrieval or a lookup tool (agent-context-designer), never to fine-tuning. Behaviour gaps climb the ladder in table C and stop at the first rung that meets the target. Check table E2 before recommending any rung that changes a generative model's weights (fixed-label classifiers were handled in step 4 under E1). "Not yet, because…" is a valid and common answer.

### 8. If weights will change, design the run
Choose the method from table D. Specify the base model (chosen for knowledge and licence), LoRA by default, verified data with splits, a general-capability regression set, and a comparison on the same held-out tasks against what the tuned model would replace: the untrained base for generative tuning, the best prompted candidate for an encoder classifier. For RL, design the reward with `references/rl-and-reward-design.md`: gate before partial credit, adversarial reward tests before training, an independent held-out scorer, and filtering to tasks the model solves sometimes but not always. Name a fallback in case vendor-hosted tuning is withdrawn.

### 9. Plan the lifecycle
Pin model versions. Record retirement dates. Keep the bake-off harness, splits and configs versioned so a re-run is one command. List the re-run triggers (`references/bakeoff-protocol.md` §10). Keep all labelled data and tuning scripts so tuning can be repeated on the next base model.

### 10. Write the output
Use `templates/model-plan.md`. Check it against the quality bar before returning it.

## Decision guide

**A. Starting model class per role** (the bake-off decides; details in `references/role-model-mapping.md`)

| Role | Start with | Why | Watch out for |
|---|---|---|---|
| Router, triage, filter | Code or rules; otherwise a small prompted model, plus a fine-tuned encoder when labels meet E1 | Volume and latency dominate; label set is fixed | Routing on stated confidence; use calibrated scores |
| Fixed-label classifier | The prompted reference model and a smaller prompted model; a fine-tuned encoder or small classifier from the start when labels meet E1 | In one study, tuned small models matched a tuned large one (about 73%) at a fraction of the cost, and the encoder was best calibrated | Rare classes stay weakest; report per-class recall; long inputs may exceed the encoder's length limit |
| Extraction to schema | Small or mid model with structured output | Narrow output; schema validation catches errors | Inference across sections needs a stronger model |
| Tool caller | Mid model with native tool calling, effort off or low | Valid arguments and latency matter most | Many overlapping tools: fix the tool design first |
| Planner | The reference model (strong general tier); sweep effort; probe the top tier only if it misses | Ambiguity and long horizons | Paying for high effort without a measured gain |
| Verifier or critic | Code if the check is codable; else a strong model from another family | False passes are the costly error | A same-family verifier shares the generator's blind spots |
| User-facing synthesis | Strong model, effort low or medium | Accuracy and clarity are visible | Long noisy context hurts more than a smaller model does |
| Eval judge | Different family from the graded models, calibrated on human labels | Self-preference and position bias | Using it before measuring agreement |

**B. Reasoning effort before measurement**

| Step type | Default | Raise only if |
|---|---|---|
| Routing, labels, extraction, format conversion | Off or lowest | Never by default; reasoning adds noise and breaks short outputs |
| Single-step tool selection and arguments | Off or low | The eval shows a gain. Across five model families, more reasoning never improved tool choice by more than a point and always added latency |
| Planning, decomposition, constraint-heavy steps | Provider default, then sweep | The sweep shows a gain worth the latency |
| Verification | Medium, then sweep | The false-pass rate drops |
| Long autonomous coding or research | Provider recommendation | Sweep lower levels too; overthinking can lower success |

On current hosted models, effort also changes how many tool calls the model makes. Re-sweep after every model change, because levels are recalibrated between generations. Changing effort mid-conversation can break the prompt cache.

**C. Failure to adaptation rung** (entry criteria in `references/adaptation-ladder.md` §3)

| Failure | First rung | Escalate to | Do not |
|---|---|---|---|
| Wrong, outdated or missing facts | Retrieval or lookup tool | Better retrieval (agent-context-designer) | Fine-tune to add facts: learned slowly, can raise hallucination, stale tomorrow |
| Ignores instructions, wrong format | Prompt and spec fix | Few-shot or dynamic exemplars, then stronger model, then SFT | Jump to SFT before measuring cheaper fixes |
| Wrong label from a fixed set | Sharpen label definitions; add contrastive examples | Fine-tuned encoder or small classifier (in the bake-off once labels meet E1) | Rely on stated confidence for thresholds |
| Inconsistent: same input gives different outputs, or labellers disagree | Find the source: rerun each case 3 to 5 times for run-to-run agreement, and measure human agreement (Cohen's kappa) on the confusable classes. If people disagree, fix the definitions. If runs disagree, use enum-constrained output, lowest effort, and no free-text reasoning before a label | Majority vote of 3 to 5 samples for high-stakes calls; a fine-tuned classifier (deterministic argmax) | Count label noise as model error, or train on labels people disagree on |
| Rules from a playbook or policy misapplied | Rule text in context (retrieve the relevant sections when the playbook is long) plus worked examples | Stronger model or higher effort; then SFT on correctly applied cases | Fine-tune the rule text into weights; rules change |
| Wrong tool or needless calls | Tool names, descriptions, overlap (agent-tool-designer) | Examples, then SFT including "don't call" cases, then RL | Train around a confusing tool set |
| Wrong exact values in arguments (amounts, IDs, dates) | Compute or fetch the value in code; the model passes a reference such as an order line ID (agent-tool-designer), plus a validator | Nothing: this is a design fix | Fine-tune or RL a model to copy numbers more carefully |
| Acceptable but wrong tone or priorities | Prompt with examples | DPO on chosen versus rejected pairs | Use SFT to express a preference between two good answers |
| Fails multi-step reasoning | Stronger model or higher effort | RL only with a program-checkable outcome | RL against an uncalibrated judge alone |
| Too expensive at volume, task stable | Step down plus fallback | Distil or tune a small specialist from verified logs | Distil before the task and labels stabilise |
| Distinctive domain language (legal, biomedical, new language) | Retrieval plus glossary in context | Continued pre-training with replay | Use it to keep facts current |

**D. Training method by available signal**

| You have | Use | Not |
|---|---|---|
| Inputs with correct outputs or labels, per role call | SFT (LoRA), or an encoder classifier for fixed labels | RL, which is overkill when demonstrations exist and the task is imitation |
| Only conversation outcomes (resolved, escalated, thumbs) | Nothing yet: label the individual role calls first | Training a role on outcomes that other roles also caused |
| Pairs of better and worse outputs | DPO | PPO with a learned reward model, unless you already run that stack |
| A program that verifies success, and tasks solved sometimes | GRPO-style RL, after SFT if the format is not yet reliable | A flat-sum reward without a gate |
| Only an LLM judge | Judge as ranker behind a program gate; otherwise stay with SFT or DPO | A judge alone as the reward |
| Only the model's own majority votes | Nothing for production | Label-free self-training on live traffic |

**E1. Train a fixed-label classifier (encoder or small model)?** A heuristic by training labels per class, counted after the test split is held out:

| Labels per class in train | Verdict |
|---|---|
| Under about 50 for most classes | Do not train. Use the labels as the test set and the few-shot pool |
| About 50 to 200 (often 1,000 to 5,000 in total) | Grey zone. Train it as a bake-off candidate. Adopt it only if it is non-inferior to the best prompted candidate on the fixed test split and meets the per-class floors. Draw a learning curve (25%, 50%, 100% of train): still rising means label more, starting with the weakest classes; flat and behind means drop it |
| Over about 200 for most classes | Strong default candidate; still confirm on the test split |

Classes below the floor: merge them, or route them to the prompted model. Inputs longer than the encoder's maximum length need truncation, chunking or routing (`references/role-model-mapping.md` §8).

**E2. Fine-tune a generative model (SFT, DPO, RL) now?** Say yes only if all of these hold: the gap is behavioural; cheaper rungs were tried and measured; the same failure repeats across many logged cases; there are enough verified examples (hundreds to thousands of curated examples for SFT of a large model; about 10,000 to 100,000 per task as a rule of thumb when a small generative model replaces a large one's calls); the task and labels will stay stable until the next base-model upgrade; volume justifies a pipeline; you can host the tuned model and re-run the tuning; and the vendor still offers tuning for that model, or you use open weights. Otherwise answer "not now" and name the cheaper rung plus the evidence that would change the answer.

**F. Smallest non-inferiority margin a paired comparison can verify** (95%, in points; q is the share of tasks where the two configurations disagree; assume q = 0.10 until a pilot measures it)

| Tasks n | q = 0.05 | q = 0.10 | q = 0.20 |
|---|---|---|---|
| 50 | 6.2 | 8.8 | 12.4 |
| 100 | 4.4 | 6.2 | 8.8 |
| 150 | 3.6 | 5.1 | 7.2 |
| 300 | 2.5 | 3.6 | 5.1 |
| 500 | 2.0 | 2.8 | 3.9 |
| 1,000 | 1.4 | 2.0 | 2.8 |

Margin = the larger of the business tolerance and the table value. Never pre-register a margin smaller than the table allows at your n.

## Output

Return a filled `templates/model-plan.md` with these sections:
1. **Summary**: what changes, expected effect on cost per success and p95 (direction only if reference numbers are unknown), what must be measured first, biggest risk.
2. **Inputs and assumptions**: each with its source (user, code, assumed).
3. **Role table**: role, risk, pre-registered target, latency budget, recommended class with a dated example model, fallback, a one-line reason, and status per role (measured, measurable now, provisional).
4. **Effort plan**: starting level, sweep levels and decision rule per role.
5. **Adaptation decisions**: failure, gap type, rung, entry criteria met or not, next rung. Include a clear fine-tuning verdict.
6. **Training plan**: only if a weight-changing rung is chosen.
7. **Bake-off protocol**: tasks and strata, splits, pre-registered metric, margin and budgets, candidate grid, trials, scoring, analysis, decision rule, end-to-end check, rollout hand-off.
8. **Re-evaluation triggers**, including known retirement dates.
9. **Hand-offs** to sibling skills, each with a specific question.

Keep it to what a team can act on this week. Put long rationale in one-line "why" cells, not essays.

## Quality bar

Before returning, check that:
- [ ] Every role has a numeric target and a latency budget, or an explicit assumption.
- [ ] Every recommended model is a class plus a dated example, and the plan says the names and prices must be re-checked.
- [ ] No role's choice rests on leaderboards alone; each is marked measured or to measure.
- [ ] The reference is the incumbent or the provider's recommended general model, the top tier appears only as a probe, and every step down has a fallback and a margin no smaller than table F allows at its n.
- [ ] Reasoning effort is set per role, with tool calling and classification defaulting to off or low unless measured otherwise.
- [ ] Costs are compared per successful task, including retries and reasoning tokens.
- [ ] Every failure is labelled knowledge or behaviour, and knowledge gaps never go to fine-tuning.
- [ ] The fine-tuning verdict lists which entry criteria (E1 or E2) are met and which are not, and every tuned model is compared with what it would replace.
- [ ] Any RL plan has a gated reward, adversarial reward tests, an independent held-out scorer, a base-model comparison and a regression set.
- [ ] The bake-off states task counts and the smallest difference it can detect at that count.
- [ ] Confidence-based routing uses calibrated scores (log-probabilities or a classifier head), never stated confidence.
- [ ] Licence, data residency and tuning availability are checked for every candidate.
- [ ] Hand-offs name the sibling skill and the question it should answer.

## Common mistakes

| Mistake | Fix |
|---|---|
| Naming models and prices from memory as if current | Use classes plus dated examples; refresh from provider pages; date every number |
| Pre-registering a 2-point margin on 150 tasks | Read table F; label more tasks or widen the margin, and say which |
| Assuming one vendor's tiers deliver the savings | In the 2026-10 Anthropic lineup, Haiku 4.5 is the only small tier (active, but with no successor listed); without it the cheapest tier (Sonnet 5.5) is half the list price of Opus 5.5; add effort cuts, batch pricing, another vendor's small tier or an open-weight model where constraints allow |
| Choosing by leaderboard or by brand | Shortlist from leaderboards, decide on the user's tasks; gaps between top models on public benchmarks are usually marginal |
| Declaring a winner from 20 to 30 cases | Show intervals; count discordant tasks; say "not distinguishable at n = …" when that is the truth |
| Comparing the incumbent's tuned prompt against untuned candidates | Equal adaptation budget per candidate on the dev split, scored on the test split |
| Turning reasoning up everywhere, or assuming it helps tool selection | Sweep per role; default off or low for tools, labels and extraction |
| Recommending fine-tuning to teach facts or policies | Retrieval or a lookup tool; tune only how the model uses them |
| Recommending fine-tuning before trying prompt, exemplars and a stronger model | Climb the ladder; record what each rung scored |
| Comparing price per token or per call | Cost per successful task, including retries, repairs and escalations |
| Routing or escalating on the model's stated confidence | Token probabilities or a classifier head; measure ECE on the user's labels |
| An RL reward with substring matching or credit before a gate | Exact or normalised matching, gate first, adversarial tests before training |
| Reporting a trained model without the untrained base on the same tasks | Always include the base; report how many groups actually trained |
| Forgetting general capabilities after tuning | Regression set after every tuning step |
| Treating a tuned closed model as a durable asset | It lives in the vendor's environment and dies with its base; keep data and scripts, name an open-weight fallback |
| Drifting into serving infrastructure, eval design or retrieval design | Hand off to the sibling skill with a specific question |

## Sources

Distilled from a cross-book study guide on agent design (chapters on model selection and adaptation, reasoning and planning, and LLM fundamentals). Book chapters used:
- *Building Applications with AI Agents*: ch1 and ch2 (model selection), ch7 (learning without weights, when to fine-tune, SFT for function calling, DPO, RLVR), ch11 (continuous learning), and its companion fine-tuning and reflexion code.
- *Designing Large Language Model Applications*: ch5 (choosing an LLM, open versus proprietary, model flavours), ch6 (the need for fine-tuning, recipe, datasets), ch7 (continual pre-training, PEFT, merging), ch8 (RLHF, hallucination after fine-tuning, reasoning data), ch11 (fine-tuning embedding models).
- *AI Agents: The Definitive Guide*: ch3 (GRPO, GSPO, RULER, ART), ch4 (models as team members, thinking modes and budgets, open versus closed, LoRA), and its companion notebooks.
- *Building Agentic AI*: ch3 (model bake-off for SQL generation), ch5 and companion repo (tool selection with reasoning on and off), ch7 (reasoning-effort experiments), ch8 (calibration, classifier versus multiple choice, domain adaptation).
- *An Illustrated Guide to AI Agents*: ch2 and ch3 (post-training, reasoning models), ch5 (SFT versus RL for tool learning, ToolRL, Search-R1), ch6 (self-improvement), ch7 (benchmarks, pass^k).
- *Systems Thinking for Agentic AI*: ch3 (chain-of-thought as a tool), ch12 (task-based model routing, cost versus quality).
- *The Agentic Enterprise*: ch5 (log, label, fine-tune, distil), ch8 (portability).
- *Agentic Mesh*: ch15 (model registry and versioned tuning pipelines).
- *AI Evals in Practice*: ch6 (minimum flips for a real difference).

External (checked 2026-10):
- Anthropic, Models overview and Effort documentation (fetched 2026-10-06): https://platform.claude.com/docs/en/about-claude/models/overview and https://platform.claude.com/docs/en/build-with-claude/effort
- OpenAI, API pricing page, including the fine-tuning wind-down notice (fetched 2026-10-06): https://developers.openai.com/api/docs/pricing
- L. Weng, "Reward Hacking in Reinforcement Learning" (2024-11): https://lilianweng.github.io/posts/2024-11-28-reward-hacking/
- Anthropic, research post on natural emergent misalignment from reward hacking (2025-11): https://www.anthropic.com/research/emergent-misalignment-reward-hacking
- Thinking Machines, "LoRA Without Regret" (2025-09): https://thinkingmachines.ai/blog/lora/
- NVIDIA Research, "Small Language Models are the Future of Agentic AI" (2025-06, revised 2026-09): https://arxiv.org/abs/2506.02153
- Cuadron et al., "The Danger of Overthinking" (2025-02): https://arxiv.org/abs/2502.08235
- Ovadia et al., "Fine-Tuning or Retrieval?" (2024-01): https://arxiv.org/abs/2312.05934
- OpenAI, "A practical guide to building agents" (2025-04): https://cdn.openai.com/business-guides-and-resources/a-practical-guide-to-building-agents.pdf
- E. Miller, "Adding Error Bars to Evals" (2024-11): https://arxiv.org/abs/2411.00640
