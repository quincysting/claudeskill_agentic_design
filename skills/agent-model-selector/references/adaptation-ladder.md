# The adaptation ladder

What to change when a role misses its target on the eval, in order of cost and reversibility. Leave at the first rung that meets the target. Weights change only for a behaviour failure that repeats and that you have verified data for.

## Contents
1. Three dials
2. Diagnose first: knowledge gap or behaviour gap
3. The ladder with entry and exit criteria
4. Methods primer: SFT, DPO, RLHF, GRPO and GSPO, continued pre-training, distillation, LoRA and QLoRA
5. How much data
6. Side effects: forgetting, lost generality, lock-in
7. Settled disagreements
8. Training-run checklist

## 1. Three dials

1. **Which model.** A configuration change, fully reversible, provided an eval tells you what the swap did.
2. **What the model sees.** Prompt, examples, retrieved documents, stored reflections and rules. Cheap to change and inspect, and it carries over to the next model. (One book calls this nonparametric learning.)
3. **What the model is.** SFT, preference tuning, RL, continued pre-training, distillation. Slow to set up, needs data and evaluation infrastructure, and must be redone or re-validated when the base model changes.

Agent traces improve every layer. With open weights they can drive post-training; with a closed model the same traces still improve prompts, tool descriptions, routing, eval sets and memory policies.

## 2. Diagnose first: knowledge gap or behaviour gap

Read 20 to 50 failing cases from the eval and label each:

| Failure looks like | Gap | Goes to |
|---|---|---|
| Wrong or outdated fact, missing policy, unknown entity, needs a citation | Knowledge | Retrieval or a lookup tool (agent-context-designer). Never fine-tuning. |
| Right facts in context, ignored or misused | Behaviour (instruction following) | Prompt and context rungs |
| Wrong format, schema violations, wrong label from a fixed set | Behaviour (mapping) | Prompt, examples, then SFT or a classifier |
| Wrong tool, or a call where none was needed | Often tool design, then behaviour | agent-tool-designer first (names, descriptions, overlap), then examples, then SFT/RL |
| Wrong exact value in an argument (amount, ID, date) | Design | Compute or fetch the value in code and let the model pass a reference to it; validate arguments against the system of record. Not a training problem |
| Correct but wrong tone, verbosity, priorities among acceptable answers | Behaviour (preference) | Prompt, examples, then DPO |
| Fails on multi-step reasoning or planning | Capability | Stronger model or higher effort; RL only with a verifiable outcome |
| A playbook or policy rule is misapplied | Knowledge plus behaviour | The rule text is knowledge: keep it in context and retrieve the relevant sections when the playbook is long. Applying it is behaviour: worked examples, a stronger model, then SFT on correctly applied cases. Never tune the rule text itself into weights |
| Humans disagree on the right label for the same case | Label definition | Measure agreement (Cohen's κ) on 50 to 100 cases of the confusable classes; fix definitions before blaming or training the model |
| Inconsistent across runs on the same input | Variance | Lower-variance setup (structured output, fewer free choices), sample-and-vote, or a fine-tuned classifier |

Facts belong in context; behaviour belongs in weights. Fine-tuning on new facts learns them slowly, can raise hallucination even on unrelated questions, and goes stale the next day.

## 3. The ladder

| Rung | Change | Entry criteria | Exit (stop climbing) when | Watch out |
|---|---|---|---|---|
| 0 | Measure | Eval exists for the role; baseline score recorded; failures labelled by gap type | Always do this first | Without a baseline you cannot tell whether later rungs helped |
| 1 | Prompt and spec | Any behaviour gap | Target met on the held-out split | Prompts tuned on the eval set overfit it; keep a test split you never tune on |
| 2a | Static few-shot examples | Format or edge cases the prompt cannot describe | Target met | Examples anchor length and tone; use 2 or 3 varied ones |
| 2b | Dynamic exemplars (retrieve similar past successes per input) | Logged successful runs exist and inputs vary | Target met | Needs a trustworthy success label, or it retrieves lucky failures |
| 2c | Reflections or an insight list (rules learned from success versus failure) | Tasks repeat and failures are detectable | Target met | The model is rewriting its own memory: cap length, review rules, prune stale ones |
| 2d | Retrieval or a lookup tool | Knowledge gap | Grounded answers correct | Moves the bottleneck to retrieval quality |
| 3 | Stronger model or higher effort for this role | Rungs 1 and 2 tried and measured | Target met at acceptable cost | This is the usual exit; it is reversible and needs no data |
| 4 | Supervised fine-tuning of a generative model | Behaviour gap persists after rungs 1 to 3, or rung 3 meets target but costs too much; the same failure repeats across many logged cases; enough verified examples (section 5); task and labels stable until the next base-model upgrade; you can host and re-run the tuning | Tuned model meets target on held-out data and passes the general regression set | Forgetting; lock-in to a base model; tuning data that teaches the eval's quirks |
| 5 | Preference tuning (DPO) | Outputs are acceptable but the wrong one is chosen among acceptable options (tone, priorities, summary focus); chosen versus rejected pairs exist | Win rate against the SFT model on held-out pairs, plus no regression | Pairs labelled by one person encode one person's taste |
| 6 | Reinforcement learning (GRPO-style) | A program can verify the outcome (or a judge ranks only outputs that passed a program gate); the model succeeds on some but not all attempts for many tasks; rewards pass adversarial tests; compute for sampling many rollouts | Beats the untrained model on held-out tasks scored by an independent checker, with no regression | Reward hacking (see `rl-and-reward-design.md`); zero-variance groups that teach nothing |
| 7 | Distil to a small specialist | Task is stable and narrow, traffic is heavy, teacher outputs are verified, and the teacher's terms allow training on its outputs | Small model meets target at lower cost per success | Keeps the teacher's errors; needs retraining when the task changes |
| side | Continued pre-training | Large corpus in a distinctive domain language (legal, biomedical, a new natural language) | Domain perplexity and downstream task improve | Not for current facts; do domain-adaptive before task-adaptive, both before SFT |

A fine-tuned encoder or small classifier for a fixed label set is not gated by this ladder: when its labels meet the per-class floor (section 5) it enters the bake-off as a candidate from the start, because training it is cheap and the bake-off measures it. Rungs 4 to 7 govern changing a generative model's weights.

When fine-tuning pays: classification, format, tool-call syntax and when-not-to-call, and cost reduction on a narrow, high-volume task. When it does not: adding knowledge, tasks still changing, low volume, or no capacity to repeat the work when a better base model arrives ("when in doubt, don't fine-tune").

Hosted tuning availability is a real constraint: as of 2026-10 one major provider had closed its fine-tuning platform to new users. If a plan relies on tuning a closed model, name the fallback (an open-weight model with LoRA) up front.

## 4. Methods primer

| Method | Training signal | Changes well | Notes |
|---|---|---|---|
| SFT (instruction tuning) | (prompt, ideal response) pairs; loss on the response tokens only | Format, structure, tool-call syntax, classification, following a task without a long prompt | Imitates exact wording, so it generalises less well to new phrasings than RL |
| Fine-tuned encoder classifier | (text, label) pairs; a classification head on an encoder | Fixed-label classification with calibrated probabilities, at very low cost and latency | Cannot generate; label set fixed at training time |
| DPO | (prompt, chosen, rejected) triples; no reward model, no critic | Tone, style, which of two acceptable answers to prefer | Needs a reasonable starting policy (usually an SFT or instruct model) |
| RLHF with PPO | Human rankings train a reward model; PPO optimises against it with a KL penalty to a reference | General helpfulness; the classic chat recipe | Needs a reward model and a critic; heavy; tends to reduce calibration |
| RL with verifiable rewards, usually GRPO | A program scores sampled outputs (format, correctness) | Reasoning and tool use where correctness is checkable | No critic; see below |
| GSPO | As GRPO, with ratio and clipping per whole sequence instead of per token | Stability on long outputs | A refinement of GRPO |
| Continued pre-training | Raw domain text, next-token loss | Domain vocabulary and style | Replay recipe below |
| Distillation | A larger model's outputs become a smaller model's training data | Cost and latency on a narrow task | Check output-use terms |

**GRPO in four lines.** Sample a group of responses for the same prompt; score each; normalise within the group (subtract the group mean, divide by the standard deviation) to get each response's advantage; raise the probability of above-average responses with a clipped update and a KL penalty that keeps the policy near a reference model. Two consequences: rewards only need to be consistent within a group, so a judge that ranks candidates side by side can serve as a reward; and a group where every attempt scores the same has zero variance and teaches nothing, so training tasks must sit at the edge of the model's ability.

**SFT and RL for tool use: use both, in order.** SFT is the cheaper way to teach a schema and the "don't call" cases, and gives RL a sensible starting policy (the same idea as a cold-start SFT before RL in reasoning-model recipes). RL then hardens behaviour against varied phrasings, provided the reward is strict. Before either, try built-in function calling with runtime schema validation, and keep validating every call at runtime after tuning.

**SFT data problems specific to tools.** Many requests have several valid calls (two tools that both return the same file); data usually assumes tools never fail. Include alternative valid calls in the scorer, include failure and retry examples, and include requests that must be answered without any tool.

**LoRA, QLoRA and adapters.** LoRA trains a pair of small low-rank matrices per adapted weight and freezes the base. It matches full fine-tuning for small and medium SFT datasets and for policy-gradient RL (even at rank 1), falls behind when the dataset exceeds the adapter's capacity (large-corpus continued pre-training), prefers all layers (especially MLP) over attention-only, and wants a learning rate roughly 10 times the full-tuning one (2025 results). QLoRA puts LoRA adapters on a 4-bit quantised frozen base to cut memory. Adapters can be merged into the base or loaded per request, so one base can serve many specialisations. Full fine-tuning costs roughly four times the memory per trainable parameter because of optimiser state. Default to LoRA.

**Continued pre-training recipe (replay against forgetting).** Start with new-domain data at about 25% of the mix and raise it gradually to a ceiling such as 80%; re-warm the learning rate, then decay it. Other countermeasures: distillation against an older checkpoint, regularisation, parameter expansion.

**Merging and ensembling.** Weight averaging and adapter merging sometimes work and are poorly understood; merged models tend to keep shared capabilities and lose unshared ones. Treat as an experiment, not a plan.

## 5. How much data

Orders of magnitude from the books and papers they cite, not rules:

| Use | Volume |
|---|---|
| Dynamic exemplars | A store of dozens to thousands of verified successes; a few retrieved per call (two or three varied examples usually beat six similar ones) |
| SFT of a large model | Hundreds to thousands of curated examples |
| Instruction tuning | A few thousand high-quality examples can suffice (LIMA) |
| Reasoning behaviour via SFT | About 1,000 question-and-trace pairs gave a 32B model stable reasoning (s1) |
| RL cold start before GRPO | About 5,000 long traces in one reasoning-model recipe |
| RL for tool use | About 4,000 traces in ToolRL |
| Small-model replacement of an agent's calls | 10,000 to 100,000 examples per task as a rule of thumb (NVIDIA, 2025) |
| Encoder or small classifier | The measured study had about 173,000 training examples; with a few thousand, expect less. Heuristic by training labels per class (after holding out the test split): under about 50, do not train; about 50 to 200, a grey zone where the tuned model is a bake-off candidate decided by the test split and a learning curve; over about 200, a strong default candidate. Confusable classes need more |

Labels must belong to the role being trained. A conversation outcome (resolved, escalated, a thumbs-down) mixes the effects of every role and every tool, so it is not a training label for any single one; sample role calls from those conversations and label each call (right intent? right tool and arguments?).

With limited labels, draw a learning curve: train on 25%, 50% and 100% of the labels and score the held-out split. If the curve is still rising, more labels will pay; if flat, look elsewhere. Rare classes are where tuned classifiers stay worst, so report per-class accuracy.

Data quality beats quantity. Verify synthetic answers with a program or a reviewer before training: a public reasoning dataset used as a textbook example contained a worked answer that was simply wrong (three dice summing to 11: 27 ways, probability 1/8, not the 1/12 its trace concluded). Draw examples from real traffic, have a person check them, and keep every labelled example so the tuning can be repeated on the next base model.

## 6. Side effects

- **Catastrophic forgetting and lost generality.** Tuning on narrow data degrades tool use, formatting or reasoning the base had; a reasoning-only intermediate model did poorly on writing and translation until general data was mixed back in. Mix in general or conversational data, use small learning rates and LoRA, and run a general-capability regression set after every tuning step, next to the task eval.
- **Specialisation versus the upstream release cycle.** A new base model can beat months of tuning on the old one. Make tuning a repeatable pipeline (data, scripts, hyperparameters, eval) registered with versions and rollback, not a one-off.
- **Vendor lock-in.** A tuned closed model lives only in the vendor's environment and dies with its base model's deprecation.

## 7. Settled disagreements

- **Fine-tune or retrieve for knowledge?** Retrieve. The pro-fine-tuning evidence in the books is strong for classification, format and cost, and weak for knowledge: one domain-adaptation run's top-grade rate rose from 6.5% to 22%, about equal to a small model with a lookup tool (23%) and far below a larger model with retrieval (71%). External work (Ovadia et al., 2024) found retrieval beat unsupervised fine-tuning for both familiar and new facts.
- **Does fine-tuning add capability?** Mostly it exposes and reshapes behaviour the base already has. Choose the base model for what it knows; tune it for how it behaves.
- **Who supplies the learning signal?** A program wherever correctness is checkable; a judge only as a relative ranker behind a correctness gate; people to label the data that calibrates both. Label-free self-improvement (majority vote over the model's own samples) is research, not something to point at production traffic: a wrong majority becomes training signal.

## 8. Training-run checklist

1. Failure is a behaviour gap, repeated across many logged cases, and cheaper rungs were tried and measured.
2. Train, validation and held-out test splits fixed before any tuning; the test split was never used for prompt work.
3. Examples verified by a person or a program; per-class counts known; "no tool" and tool-failure cases included.
4. Base model chosen for knowledge and licence; LoRA unless there is a reason not to.
5. General-capability regression set prepared.
6. For RL: reward passes adversarial tests; tasks filtered to those solved sometimes but not always; independent held-out scorer (see `rl-and-reward-design.md`).
7. Every comparison includes what the tuned model would replace, on the same held-out data: the untrained base for generative tuning, the best prompted candidate for an encoder classifier (an untrained classification head is meaningless).
8. Calibration measured if thresholds depend on confidence.
9. Data, scripts, hyperparameters, eval results and the resulting model versioned and registered with a rollback path.
10. A re-run plan for the next base model and a fallback if hosted tuning is withdrawn.
