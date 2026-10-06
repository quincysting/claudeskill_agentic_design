---
name: agent-architect
description: Design or review an agentic AI system's architecture and return a design doc with decisions and rationale. Decides, per step, plain code vs model call vs workflow vs bounded agent loop, and its autonomy level; patterns (router, fan-out, orchestrator-workers, evaluator-optimizer, plan-and-execute, ReAct); the runtime and control loop (validation, budgets, stop conditions, exits, retries, checkpoints); planning and reasoning strategy; single vs multi-agent and coordination. Use for "design an agent for...", "should this be an agent or a workflow", "which agent pattern", "single agent or multi-agent", "review my agent architecture", "plan-and-execute vs ReAct", "orchestrator", "agent control loop". Not for tools/MCP/A2A (agent-tool-designer), RAG/memory/document ingestion (agent-context-designer), evals (agent-eval-designer), observability/cost (agent-ops-reviewer), security/oversight (agent-threat-modeler), model choice (agent-model-selector), ROI/governance/regulation (agentic-business-case).
---
# Agent Architect

Produces an architecture design doc for an agentic system. It covers which steps are code, model calls, workflows or bounded agent loops, how much authority each step carries, the orchestration pattern, the control loop with numbers, the planning strategy, and whether to use one agent or several, each decision with its rationale. The stance: use the least autonomy that handles the inputs, let the model propose while code decides, and put a number on every bound.

## When to use / when not to

Use when:
- Someone wants to build an "agent" or an "AI workflow" and the shape needs deciding before code is written.
- Someone asks whether a task needs an agent at all, which pattern fits, whether to use ReAct or plan-and-execute, or whether to split into several agents.
- Someone has an agent (code, framework config, diagram, traces) and wants its architecture reviewed: runaway loops, duplicated side effects, multi-agent sprawl, or cost and latency problems that come from structure.

Hand off by name; do not design these in depth here:

| Concern | Skill |
|---|---|
| Tool contracts and descriptions, MCP servers, A2A wire protocol | agent-tool-designer |
| Retrieval, RAG, long-term memory, context assembly and compaction; document ingestion (OCR, parsing, photo and form extraction pipelines) | agent-context-designer |
| Eval sets, judges, trajectory metrics | agent-eval-designer |
| Tracing, monitoring, production cost and latency tuning, serving | agent-ops-reviewer |
| Prompt injection, permissions, sandboxing, approval UX, human oversight | agent-threat-modeler |
| Which model per role, fine-tuning, distillation | agent-model-selector |
| Whether the use case is worth doing, ROI, governance, regulatory and compliance requirements (adverse-decision rules, fairness, model risk) | agentic-business-case |

This skill still marks where each of those attaches in the architecture (for example "approval gate here; threat-model it").

## Inputs to gather first

Read the user's material (code, docs, tickets) before asking anything. Ask only for facts that would change a decision. For everything else, state an assumption and keep going.

1. **Responsibility:** what comes in, what goes out, who or what consumes it. Write it as "Given X, produce Y that Z can use."
2. **Today's process:** the steps a person or system performs now, with rough time per step.
3. **Input variability:** how structured the input is, how many kinds there are, how often new kinds appear.
4. **Actions and side effects:** every read and write against an external system, whether it can be reversed, and what a wrong one costs (money, legal, customer, safety).
5. **Existing rules:** approval thresholds and what each is measured on (per payment or per case, gross or net, with or without earlier payments), compliance checks, SLAs, regulated or adverse decisions (denials, eligibility, pricing, fraud referral).
6. **Systems and data:** APIs, stores and documents; data sensitivity (PII, on-prem constraints).
7. **Load and limits:** volume per day, latency target (interactive or batch), cost ceiling per task.
8. **Evidence:** labelled examples, historical outcomes, an existing baseline, current metrics.
9. **Constraints:** a framework or platform already chosen, hosting, team size.
10. **Review mode:** the loop code, agent, crew or graph definitions, tool list, prompts, 3 to 5 real traces (one of them a failure), eval results, incident reports.

If item 1, 4 or 7 is unknown and cannot be inferred, ask at most three questions in one message. Otherwise proceed and list the assumptions in the doc.

## Procedure

Design mode runs steps 1 to 10. Review mode runs step R first, then steps 1 to 10 to produce the target architecture.

**R. Review the as-is system.** Map what actually runs from the code and traces, not from the docs: the step map, the ownership table, the agent count. Run `references/review-checklist.md` and record each finding with its severity, evidence (file:line, config key, trace ID) and fix. For each reported incident (duplicate actions, runaway loops), name the structural cause and say how the user can confirm it from logs. If a framework is in use, apply the framework test in `references/pattern-catalog.md`. Keep what works; the target design marks each section keep, change or add.

1. **Frame.** Write the responsibility sentence, measurable success criteria, non-goals and assumptions.

2. **Decompose.** List the task's steps from the as-is process. For each step give its input, output, side effect and consumer. Split any step that mixes a read with a consequential write. Treat document ingestion (OCR, parsing, document-type classification, photo or form extraction) as its own step: record its shape, output schema and failure exit here, and hand the pipeline design to agent-context-designer. A per-document call is one step fanned out over N documents; estimates multiply by documents per case.

3. **Choose each step's shape.** Climb the ladder per step and stop at the first rung that holds: plain code, then a single model call or RAG, then a workflow with model steps, then a bounded agent loop. For every agent step, write down the deciding fact: *what will this step discover at run time that decides its next action?* If there is no answer, the step is not an agent. If you are unsure between workflow and agent, mark the step "build both" and settle it in step 9. Flow, catalogue and worked example: `references/autonomy-and-shape.md`.

4. **Set each step's authority, separately from its shape.** Options are act, act and notify, approve, or suggest. Choose from input variability crossed with the cost of a wrong action (table below). Irreversible or high-value actions get limits enforced in code plus a person, however confident the model is. Prefer not to give the agent such tools at all: the agent puts a proposal in its final output, and a code action path recomputes, checks and executes it. Mark these as approval gates for agent-threat-modeler.
   - **Client approval rules are a floor on oversight, not an automation target.** Above the client's threshold a person always approves, enforced in code. Below it, still run the matrix: the band may start at suggest and graduate later. First pin what the threshold is measured on, and compute it in code from the system of record, aggregated so a payout cannot be split under it.
   - **Define "reversible" and "cheap" for the domain** before using the matrix. Reversible means the system can undo the action fully, at negligible cost, before harm lands (a draft, a hold, an internal note). Money sent, external messages, communicated denials and deletions count as irreversible. Cheap means the expected loss of one wrong action is below what the organisation already accepts without review today; if no such tolerance exists, treat it as costly.
   - **Regulated or adverse decisions** (denial, reduction, eligibility, pricing, fraud referral): a person decides in v1 unless policy and regulation explicitly allow automation. Every case gets a decision record: decision, reason codes from a fixed list, evidence references, rule and policy version, model and prompt versions, recommender and decider. Hand the regulatory requirements to agentic-business-case.
   Detail and examples: `references/autonomy-and-shape.md`.

5. **Pick patterns.** Choose the skeleton pattern, then the pattern inside each agent step. The default for an agent step is deterministic prefetch plus a bounded planner: code fetches what is always needed, and the model picks one next action from an allowlist or says it is done. Pick another pattern only when its "use when" condition holds: `references/pattern-catalog.md`. Place a router where its inputs exist (after prefetch or extraction if it needs them), and route on rules over structured fields before calling a model for unstructured signals.

6. **Choose the planning and reasoning strategy per agent step.** Use ReAct with native tool calling when the next action depends on the last observation. Use plan-and-execute when the plan should be reviewed and its steps map to registered tools. Add replanning when observations often invalidate the plan. Spend extra compute (effort, sampling, reflection) only where a signal makes it pay, and write the dial values as numbers. See `references/reasoning-strategy.md`.

7. **Decide on one agent or several.** Default to one. Split only on a real boundary (data access, permissions, tool set, evaluation criteria, independent release), or for breadth-first parallel work that returns answers and has the token budget for it. Before splitting because of tool count or context size, try fixing it inside one agent. If you split, specify the topology, an orchestrator in code, typed messages, context slices, a conflict rule and caps. See `references/multi-agent.md`.

8. **Specify the runtime and control loop.** Fill the ownership table: decide, validate, authorise, execute, store, record and stop each get one named component, and "the model" may own only *decide*. Then write the decision contract, the validation gate, tool risk tiers, budgets with numbers, stop conditions, exit statuses, retries per failure class, idempotency for writes and for run triggers (a redelivered webhook or event must map to the same run), versioning for outputs that get regenerated, the state schema and checkpoints, the execution mode, and where the loop lives. When a person or another system decides downstream on its own timeline, end the run with `handed_off` and start a new run on the decision event; keep `awaiting_approval` for short gates the run itself resumes. See `references/control-loop.md`.

9. **Estimate and plan validation.**
   - **Per path:** typical and worst-case model calls and tokens (per document where documents fan out), p50 and p95 latency against the target, cost per task against the ceiling.
   - **At volume:** peak arrivals, concurrency, provider rate limits (requests and tokens per minute), queue wait, and what prompt caching saves on stable prefixes.
   - **Against the incumbent:** if it is human labour, compare handling minutes and cost per case, counting the review minutes your design still needs, not model calls against people.
   - **Unknowns:** never invent prices. If prices, shares or the cost ceiling are unknown, give tokens and calls, state the missing figure as an assumption or open question, and say that a metered eval replay gives the real number.
   - **Reliability:** apply the chain arithmetic for direction only.
   - **Build both:** for each such step, fix these before the run: one case set and scorer for both designs, a primary metric tied to the error the consumer pays for, guardrail limits on the other metrics, and a minimum gain derived from error cost and larger than the measurement's noise. Score against adjudicated labels when the ground truth is past human decisions. Without that evidence keep the less autonomous design. Method: `references/autonomy-and-shape.md`; statistics and eval-set design: agent-eval-designer.
   Sizing method: `references/control-loop.md`.

10. **Write and check.** Fill `templates/architecture-design-doc.md`, including the rollout and authority-graduation section. Put the 3 to 5 assumptions that most change the design in a "Confirm first" block right after the Summary. Run the red-flag table in `references/review-checklist.md` against your own draft, then the Quality bar below; fix any failures and re-run before returning.

## Decision guide

### Shape per step

| Situation | Shape | Why | Watch out for |
|---|---|---|---|
| Rules can be written down; ms latency; certification | Plain code | Cheaper, testable, auditable | Forcing a model in because "it's an AI project" |
| One transformation of unstructured input | Single call, output validated in code | Output is data; code routes it | Letting its output silently drive actions |
| Questions over a corpus, no actions | RAG pipeline | Fixed path, cheap to maintain | Scope creep into acting |
| Steps and branches can be listed | Workflow with model steps | Branch-level audit trail, predictable cost | Branch count growing every week, which means the inputs are variable |
| Most steps fixed, one needs judgment | Workflow skeleton + one agent step | The most common production answer | Defining where the agent's input comes from and how its output is checked |
| Next step depends on what was found; inputs novel | Bounded agent loop | Adapts per case | Missing bounds, which are part of the definition |
| Variable and costly or irreversible | Agent proposes, code checks limits, a person decides | Variability needs judgment; cost needs a person | Reviewers who rubber-stamp |
| Unsure between workflow and agent | Build both and compare | The one head-to-head measurement found a workflow matching agent accuracy at about a third of the cost and half the latency | Comparing with different scorers |

### Authority per step

| | Reversible or cheap | Irreversible or costly |
|---|---|---|
| **Predictable inputs** | Act (automate) | Deterministic and audited; approval above a threshold, in code |
| **Variable inputs** | Act; people sample results | Agent proposes; code checks limits; a person decides |

### Pattern

| Situation | Pattern | Watch out for |
|---|---|---|
| Known steps, each checkable | Prompt chain | Cascading misreads; validate between steps |
| Distinct input classes | Router (enum output) + fallback lane | Misroutes; unit-test the router |
| Mostly easy inputs, calibrated confidence available | Cascade | Self-reported confidence does not work |
| Independent subtasks | Parallel fan-out + merge rule | Conflicting outputs with no rule |
| Subtasks known only after reading the input | Orchestrator-workers | Uncapped plan size or depth |
| Clear criteria, latency tolerant | Evaluator-optimizer | Weak critic; more than 2 rounds |
| Most steps fixed, a few need judgment | Deterministic prefetch + bounded planner | Planner asked to decide things code can decide |
| Reviewable plan over registered tools | Plan, then deterministic execution | Stale plans; add replanning triggers |
| Several modes share policies | Hierarchical state machine | Over-engineering a three-node flow |
| Long runs, human waits, must survive crashes | Durable workflow engine | Model calls inside replayed code; they belong in activities |

### Planning and reasoning

| Step type | Strategy | Effort | Extra compute |
|---|---|---|---|
| Classification, extraction, short structured output | Single pass | Off or low | None |
| Next action depends on the last observation | ReAct, native tool calling, step cap | Low or adaptive; raise if the eval shows a gain | Reflection only on a failed check or repeated action |
| Long research-style task | Plan, execute, replan; large planner, small executors | Higher for the planner | Replanner may end early |
| Output checkable by tests, schema or rules | Generate then verify; best-of-N or refine on the verifier's reason | Low | N and rounds bounded; stop when verified |
| Short comparable answers, model usually right | Self-consistency vote | Low | 5 to 10 samples |
| Constraint-heavy reasoning | Reasoning model or higher effort | High, but measure it | Verify in code where possible |

### One agent or several

| Situation | Decision |
|---|---|
| Sequential, tightly coupled work (coding, one document) | One agent |
| Interactive and latency-bound | One agent |
| Wrong tool chosen among many tools | One agent with tool search or coarser tools |
| Needs a clean context for sub-questions | One agent with subagents called as tools |
| Roles differ in data sensitivity, permissions, tools or eval criteria | Split along that boundary; orchestrator in code |
| Breadth-first research, subtasks return answers, budget allows several times the tokens | Orchestrator-workers in parallel |
| Parallel workers would write parts of one artifact | Do not parallelise; use one writer or a sequential pipeline with a decisions record |
| One role must be released or certified independently | Split that role only |

### Budget starting points

At design time no eval exists. Set each budget provisionally from the path a correct run needs (count its calls, add 50 to 100% headroom; this skill's convention), mark it provisional, and resize from the eval's worst case.

| Bound | Start | Basis |
|---|---|---|
| Agent loop steps | 8 to 12 | Calls a correct run needs plus headroom; for scale, a teaching loop caps at 10 and a production review agent at 12 |
| Re-asks after an invalid proposal | 2 | Each re-ask costs a step |
| Critique or review rounds | 1 to 2 | Beyond that the loop "performs confidence" |
| Reflection trigger | Failed check, tool error, or the same action more than 3 times | Reflection without a signal makes the model second-guess correct answers |
| Plan steps (research agent) | about 5 | The replanner may end early |
| Wall clock, interactive | The UX budget, in seconds | Anything longer becomes an async job |

## Output

Return one markdown document following `templates/architecture-design-doc.md`, in this order:

0. Summary (4 to 6 sentences), then a "Confirm first" block with the 3 to 5 assumptions that most change the design.
1. Responsibility, success criteria, non-goals, assumptions.
2. Step map table: step, shape, authority, owner component, and the run-time discovery for each agent step.
3. Architecture: a diagram (mermaid or text), the ownership table, the chosen patterns, where the loop lives.
4. Control loop: decision contract, validation gate, tool risk tiers, budgets table with numbers, stop conditions, exits, failure handling, idempotency, state and checkpoints, execution mode.
5. Planning and reasoning per agent step.
6. Agent topology, with the split-test answers.
7. Human oversight points, and decision records for regulated or adverse decisions.
8. Estimates: calls and tokens per path, latency, cost per task and per day, peak throughput and rate limits, comparison with the incumbent.
9. Validation plan.
10. Decision log: decision, alternatives, rationale, revisit-when.
11. Handoffs to sibling skills.
12. Risks and open questions.
13. Rollout and authority graduation: shadow, suggest, approve, act and notify, with entry criteria and a rollback trigger per step.

In review mode, put a findings table first (severity, finding, evidence, fix, sorted by severity), then the target architecture with each section marked keep, change or add, then a migration order that fixes Critical items first.

Keep it to what someone can build from. If the user asked a narrow question ("ReAct or plan-and-execute for this step?"), answer it directly with the relevant decision-log rows and skip the full template.

## Quality bar

Check every item before returning; fix and re-check any that fail. An item that depends on an input the user has not given (a cost ceiling, a latency target) passes if the doc states it as an assumption or open question and expresses the bound in the units that are known (tokens, calls, seconds).

- [ ] Every step has a shape chosen per step, and every agent step names the fact it discovers at run time.
- [ ] Authority is set per step and separately from shape; every irreversible or high-value action has a code-enforced limit and a named human gate; any client threshold has a pinned definition and is enforced as a floor.
- [ ] Every regulated or adverse decision has a human decider (or documented permission to automate) and a decision record with reason codes from a fixed list.
- [ ] The ownership table names a component for decide, validate, authorise, execute, store, record and stop, and the model owns only decide.
- [ ] Every budget has a number and a basis; there is a no-progress rule.
- [ ] Every exit status is defined, downstream decisions use `handed_off` plus a new run, and no failure or cap-hit path can be presented as success.
- [ ] Every write has an idempotency scheme, run triggers are deduplicated, and high-impact writes check current state first; retries are split by failure class; a failed required check stops the run.
- [ ] Each reasoning dial (effort, samples, reflection) names the signal that justifies it, or is set to its minimum.
- [ ] A multi-agent design names its single-agent baseline and the boundary that justifies each split.
- [ ] Each "build both" step has a comparison with a primary metric, guardrails and a minimum gain set in advance.
- [ ] The rollout section gives each step's starting authority, entry criteria for the next stage and a rollback trigger.
- [ ] Latency and cost estimates are checked against the stated targets.
- [ ] The decision log gives an alternative and a rationale for each major decision.
- [ ] Sibling concerns are handed off by name rather than designed here.
- [ ] Assumptions and open questions are explicit; fast-aging facts (framework knobs, model features) are hedged.

## Common mistakes

| Mistake | Fix |
|---|---|
| Making the whole system "an agent" | Decide per step; most steps are code or single calls |
| Role theatre: planner, researcher, analyst and critic agents that share the same context and tools | Apply the split test; merge roles that fail it |
| An LLM manager or coordinator that routes, summarises and judges | Put the coordinator in code; if a model routes, it returns an enum plus FINISH |
| "The model decides when to stop" | Code owns the stop: budgets, no-progress detection, exit statuses |
| Safety rules written only in the system prompt | Enforce them in the gate, the tool layer or a policy engine; context compression can drop prompts |
| Budgets described in words ("reasonable limits") | Give numbers with a basis, sized from eval worst case |
| Reasoning effort high everywhere; an "are you sure?" pass on every step | Set effort per task family from a sweep; reflect only on evidence |
| Model calls for deterministic steps (fetch, format, compute) | Prefetch and compute in code |
| Giving the agent the payment, refund or delete tool | The agent outputs a proposal; a code action path recomputes, checks and executes it |
| Retrying refunds, payments or posts with no idempotency key | Key every write by run, step and action; deduplicate triggers; check current state before money moves |
| Treating 0.98^n reliability arithmetic as a prediction | Use it for direction; the gain comes from validation at boundaries |
| Designing a fleet with an event bus for a request/response feature | Use the transport the load needs; in-process calls are fine at small scale |
| Quoting framework parameters or model features from memory as current | Mark them "verify against current docs" |
| Reading a client's "approve above $X" as licence to automate everything below $X | Treat it as a floor; run the matrix for the band below it and graduate on evidence |
| An adverse decision (denial, referral) justified only by the model's free text | A person decides; reason codes from a fixed list and evidence links in a decision record |
| Holding a run open for days while someone decides in another system | End with `handed_off`; the decision event starts a new run that re-reads current state |
| Asking a dozen questions before producing anything | Ask at most three blocking questions; otherwise assume, label and proceed |
| Designing tool schemas, RAG or eval suites in depth | Mark the attachment point and hand off to the sibling skill |

## Sources

Distilled from the following books. In `references/`, a citation such as [SYSTEMS ch8] names one of these books and a chapter; each reference file restates the point it relies on, so the books are not needed to use the skill.
- SYSTEMS: *Systems Thinking for Agentic AI*, ch3, 6, 8, 10, 13, 16, 17, 18.
- DEFGUIDE: *AI Agents: The Definitive Guide*, ch1, 2, 3, 4, 5, 10, 11.
- BUILDAPPS: *Building Applications with AI Agents*, ch1, 5, 7, 8, 12.
- BUILDAGENTIC: *Building Agentic AI*, ch1, 2, 4, 5, 7.
- ILLUSTRATED: *An Illustrated Guide to AI Agents*, ch1, 3, 6, 8.
- MESH: *Agentic Mesh*, ch1, 3, 4, 5, 6, 7, 10, 14.
- DLLMA: *Designing Large Language Model Applications*, ch8, 10, 13.
- ENTERPRISE: *The Agentic Enterprise*, ch1, 5, 6, 7.
- AGENTICAI: *Agentic Artificial Intelligence*, ch2, 3, 6, 8.

External (checked 2026-10):
- Anthropic, Building effective agents (2024-12): https://www.anthropic.com/engineering/building-effective-agents
- Anthropic, How we built our multi-agent research system (2025-06): https://www.anthropic.com/engineering/multi-agent-research-system
- Anthropic, Effective harnesses for long-running agents (2025-11): https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents
- Anthropic, The "think" tool (2025-03): https://www.anthropic.com/engineering/claude-think-tool
- Anthropic extended thinking docs: https://platform.claude.com/docs/en/build-with-claude/extended-thinking
- OpenAI, A practical guide to building agents (2025-04): https://cdn.openai.com/business-guides-and-resources/a-practical-guide-to-building-agents.pdf
- Cognition, Don't Build Multi-Agents (2025-06): https://cognition.com/blog/dont-build-multi-agents
- Kim et al., Towards a Science of Scaling Agent Systems (v3 2026-04): https://arxiv.org/abs/2512.08296
- Cemri et al., Why Do Multi-Agent LLM Systems Fail? (MAST): https://arxiv.org/abs/2503.13657
- Snell et al., Scaling LLM Test-Time Compute Optimally (2024-08): https://arxiv.org/abs/2408.03314
- Huang et al., Large Language Models Cannot Self-Correct Reasoning Yet (2023-10): https://arxiv.org/abs/2310.01798
- Gema et al., Inverse Scaling in Test-Time Compute (2025-07): https://arxiv.org/abs/2507.14417
- Feng et al., Levels of Autonomy for AI Agents (2025-07): https://arxiv.org/abs/2506.12469
- METR, time horizons (2025-03) and their limits (2026-01): https://metr.org/blog/2025-03-19-measuring-ai-ability-to-complete-long-tasks/ , https://metr.org/notes/2026-01-22-time-horizon-limitations/
- Temporal workflow definition: https://docs.temporal.io/workflow-definition
