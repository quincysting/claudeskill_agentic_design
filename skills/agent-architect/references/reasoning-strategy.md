# Planning and reasoning strategy

Citation keys such as [ILLUSTRATED ch6] point to the book list under Sources in SKILL.md.

How each agent step decides: how it plans, how long it thinks, whether it tries several candidates, whether it reflects. The loop around these choices is control-loop.md; model choice per role is agent-model-selector's job.

## Three dials, each needs a signal

| Dial | Techniques | Pays only if | Costs |
|---|---|---|---|
| **Length**: think longer in one call | CoT prompting, reasoning model, higher effort or thinking budget | The step is decomposition- or constraint-heavy; value comes from training, no run-time check [ILLUSTRATED ch3] | Latency, output-priced tokens |
| **Breadth**: several candidates, keep one | Self-consistency, best-of-N, tree search | Something can tell a better candidate from a worse one. Generator-verifier works when verifying is easier than producing [DLLMA ch8] | Tokens (parallelisable) |
| **Depth**: more steps | ReAct, plan-execute-replan, Reflexion | Each step brings back information the model did not have (a tool result, a test, an evaluator score) | Wall time (serial) |

No signal → set the dial to its minimum. Extra compute without a signal mostly buys more text.

## Planning strategy per step

SYSTEMS's three strategies [SYSTEMS ch8]: **static** (steps fixed up front; simple, brittle when inputs vary), **dynamic** (agent picks each step; adaptive, harder to test and control), **hybrid** (fixed skeleton, a few dynamic steps; the usual production choice). In many practical systems "planning" means choosing the best next action and repeating, not writing a roadmap [SYSTEMS ch8].

Pick with two questions: does the next step depend on the last observation, and can code or a test tell a good output from a bad one?

| | Output verifiable (tests, schema, rules) | Output not verifiable |
|---|---|---|
| **Path fixed** | Plan, then check each step in code | One pass, low effort; a person or sampled review checks |
| **Path open** | ReAct with grounded reflection (tests or tool errors drive retries) | Bounded ReAct behind a human gate |

### Pattern table

| Pattern | Use when | Avoid when |
|---|---|---|
| One-call decomposition (least-to-most, plan-and-solve) | Subproblems follow from the question; no tools needed [ILLUSTRATED ch6] | Steps depend on tool results |
| ReAct with native tool calling | Next action depends on what the last one revealed | Path predictable; tight latency |
| Plan-and-execute | Plan reviewable; strong model plans, cheaper ones execute [BUILDAPPS ch5] | Most observations invalidate the plan |
| Plan, execute, replan | Long research-style tasks where steps become unnecessary or impossible [BUILDAGENTIC ch5] | Short tasks where a replan per step costs more than it saves |
| Query decomposition (self-ask) | Multi-hop factual questions answered by search [BUILDAPPS ch5] | Single-hop lookups |

**ReAct means the loop, not the text format.** Hand-written THOUGHT/ACTION/OBSERVATION prompts with regex parsing are brittle [DLLMA ch10]; with a model trained for native tool calling the ReAct class shrinks to a step cap [ILLUSTRATED ch6]. Use the provider's native tool calling. ReAct's failure modes (over-calling tools, looping without stop criteria, growing state [DEFGUIDE ch2]) are fixed in the loop, not the prompt.

**Plan-execute-replan, as built in [BUILDAGENTIC ch5]:** a large model plans (a solid plan is harder than any one step), a small model runs each step as a ReAct agent, a fast model replans after every step and may shorten or end the plan, a small model summarises. Step execution dominated latency, which argues for small executors. Copy: structured output from planner and replanner, a step cap, the role split. Fix: route cap-hit and error exits to a status, not to the same summariser as success.

**Write the plan down as data** when a person or evaluator must check intent before execution, or the task is long enough that progress must be tracked (coding agents keep plan files [ILLUSTRATED ch3]). Plan fields: step ID, tool, arguments, status, result, one-line justification [MESH ch4] [MESH ch5]. Replanning triggers: step failure, unexpected result, missing input.

## Length: reasoning effort

Evidence from the sources, all small or near ceiling:
- 30 HLE questions, two models, three effort levels: no detectable effect (differences of 1 to 3 questions) [BUILDAGENTIC ch7].
- MathQA: all settings above 90%; Claude Opus 4 best with reasoning off; median latency about 7.5 s off versus 12.5 to 15 s on [BUILDAGENTIC ch7].
- Computer use, 228 screens: reasoning lowered Sonnet 4 from 82.7% to 81.4%; for Opus 4.1 a 2.4% gain on coordinate tasks cost 96.5% more latency [BUILDAGENTIC ch7].
- A crossword with interlocking constraints: a non-reasoning model answered instantly with five errors; a reasoning model took two minutes and was nearly perfect (one run) [AGENTICAI ch6].
- External: longer reasoning can lower accuracy on distractor-heavy and constraint-tracking tasks (Gema et al., 2025); compute allocated per prompt by difficulty beat best-of-N by more than 4× in efficiency (Snell et al., 2024).

Rules:
- Default low or adaptive effort. Raise it for planning, decomposition, multi-tool orchestration and constraint-heavy steps; leave it off for classification, extraction, short structured outputs and high-throughput endpoints [DEFGUIDE ch4].
- Treat effort as an experimental variable per task family: sweep off/low/medium/high, measure accuracy, p50/p95 latency and cost, with enough cases to see a real difference [BUILDAGENTIC ch7]. Include long, noisy contexts in the sweep.
- A router or the model's adaptive thinking is worth it when one endpoint mixes easy and hard requests.
- Do not add "think step by step" for a reasoning model; the thinking switch replaces it [ILLUSTRATED ch3]. CoT on a non-reasoning model helps for math, comparing alternatives, debugging, planning; it hurts classification and machine-readable outputs [SYSTEMS ch3].
- A reasoning step between tool calls (analyse the tool output before the next call) helps in policy-heavy, sequential domains: Anthropic's "think" tool raised τ-bench airline pass^1 from 0.370 to 0.570 with domain examples in the prompt (2025-03). Current models provide this natively as interleaved thinking.
- Reasoning models are stochastic like any LLM; evaluate with repeated runs, not single samples.

## Breadth: sampling and search

| Technique | Use when | Avoid when |
|---|---|---|
| Self-consistency (majority vote) | Short comparable answers (number, label, option) and the model is usually right | Free text; tasks the model rarely gets right (the majority is wrong) [ILLUSTRATED ch3] |
| Best-of-N with a verifier | A cheap reliable check exists: tests, schema, rules [ILLUSTRATED ch3] | Only an uncalibrated judge |
| Verifier-guided refinement | The check returns a specific failure reason (iterative backprompting [DLLMA ch8]) | Only the model's own opinion is available |
| Tree search (beam, MCTS, AB-MCTS) | Partial solutions can be scored and pruned [DEFGUIDE ch3] | Scoring slow or noisy; latency-bound step |

Search optimises whatever the scorer rewards. A taste score ("quality 0 to 1") climbs polish and length; a neutral fallback score on judge errors hides failures [DEFGUIDE ch3]. Score correctness with code where possible; calibrate any LLM judge first (agent-eval-designer).

Put the strongest model on the pruning or selection step: a wrong choice there discards the best branch early [DEFGUIDE ch2].

Rule of thumb [DLLMA ch8]: refine when a candidate is close; sample fresh ones when every candidate is poor.

```python
def solve(task, generate, refine, verify, budget=8, explore_below=0.5):
    """verify(text) -> (score 0..1, reason). The verifier, never the model, decides best and stop."""
    pool = []
    for spent in range(budget):
        best = max(pool, key=lambda c: c[1], default=None)
        if best and best[1] == 1.0:
            return best, spent, "verified"
        text = (generate(task) if best is None or best[1] < explore_below      # breadth
                else refine(task, best[0], best[2]))                           # depth, with the reason
        pool.append((text, *verify(text)))
    best = max(pool, key=lambda c: c[1])
    return best, budget, "verified" if best[1] == 1.0 else "budget_exhausted"
```

Tune `explore_below` on the eval set; it encodes problem difficulty.

## Depth: reflection

The dividing line is the source of the feedback. Reflect on evidence; do not run unprompted "are you sure?" passes on correctness questions. Models struggle to correct their own reasoning without external feedback and sometimes get worse (Huang et al., ICLR 2024). DLLMA calls reflection's effectiveness overstated and harmful when invoked too often [DLLMA ch10].

| Variant | Use when | Mechanism |
|---|---|---|
| Verifier/tool-grounded critique (CRITIC, backprompting) | A test, tool error, search result or evaluator gives a concrete reason | Feed the failing case, not "try again" |
| Self-Refine | Drafts judged against quality criteria (completeness, style, format) [ILLUSTRATED ch6] | Draft, critique, revise; capped |
| Reflexion (across attempts) | Tasks are retried and success or failure is known [ILLUSTRATED ch6] | After a failure, write a short strategy lesson; prepend to the next attempt |

Triggers: a failed check, a tool error, a low evaluator score, the same action repeated more than three times [DLLMA ch10]. Each reflection must produce a concrete changed plan. Cap rounds (1 to 2). For Reflexion, the reflection prompt sees the full action/observation transcript ending in the failure status, asks for strategy rather than a summary, and memory keeps only the last three reflections [BUILDAPPS ch7]; date them and prune when they stop helping.

## Multi-model roles inside one step

Planner large, executor small, replanner fast, summariser small [BUILDAGENTIC ch5]; strongest model on selection or pruning [DEFGUIDE ch2]. Size each role by its error cost. The model picks themselves: agent-model-selector.

## What to log

Structured plans, decisions with one-line justifications, verifier results, stop reasons. Not raw chain-of-thought: it leaks into user text, breaks JSON parsers, and a rationalisation is not an explanation [SYSTEMS ch3]. Persist the action/observation trace, not exposed reasoning [SYSTEMS ch8].

## Fast-aging facts (as of 2026-10; verify against current provider docs)

- Anthropic: fixed `budget_tokens` for extended thinking is deprecated on Claude 4.6 models and rejected from 4.7 on, replaced by adaptive thinking steered by an effort setting; at low effort the model may skip thinking on easy inputs. Budget forcing still applies to self-hosted open-weight models [DEFGUIDE ch4].
- Interleaved thinking between tool calls is native. Thinking blocks must be passed back complete and unmodified with tool results. Changing the thinking configuration between requests invalidates prompt-cache breakpoints, so fix it per conversation.
- Current Anthropic models do not return raw reasoning; returned thinking, if any, is a summary, and full thinking tokens are billed. Audit designs must rest on structured plans, decisions and tool traces, not raw CoT.
- Reasoning tokens are billed at output price and count against the output cap even when hidden [BUILDAGENTIC ch7] [DEFGUIDE ch4].
