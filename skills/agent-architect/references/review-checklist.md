# Reviewing an existing agent architecture

Citation keys such as [SYSTEMS ch10] point to the book list under Sources in SKILL.md.

Also run section 4 against your own draft design before returning it.

Base the review on code and traces rather than slides. Map what actually runs, then compare it with what the design needs.

## 1. Collect

- Entry point and the loop: whoever calls the model repeatedly.
- Agent, crew, graph or workflow definitions; the tool list with each tool's side effects.
- System prompts (look for rules that should be code: "never", "always confirm", "do not exceed").
- Configuration: step limits, timeouts, retries, model and effort settings.
- 3 to 5 real traces, including one failure. Eval results and incident reports if any.

## 2. Where to look in code

Search for the loop and its bounds. Framework knob names, as of 2026-10 (verify against current docs; defaults change):

| Framework | Bounds and control to find |
|---|---|
| Hand-rolled | `while True`, `for step in range`, recursion; where `max_steps` is checked; what happens on exit |
| LangGraph | `recursion_limit`, checkpointer, `interrupt`, conditional edges back to the model node |
| CrewAI | `max_iter`, `max_rpm`, `allow_delegation`, `Process.hierarchical` with `manager_llm` |
| OpenAI Agents SDK | `max_turns`, handoffs, guardrails |
| AutoGen / AG2 | termination conditions, max rounds or messages |
| Claude Agent SDK | `max_turns`, allowed tools, permission mode, hooks |

Also grep for: retry decorators around side-effecting calls (idempotency?), `temperature`, effort or thinking settings, places where tool output is concatenated into the next prompt unvalidated, and any code path where model output is passed straight to `exec`, SQL, HTTP or a payment API.

## 3. Rebuild the as-is picture

- Step map: each step, its shape (code, call, workflow, agent), its authority.
- Ownership table: who decides, validates, authorises, executes, stores, records, stops. Write "nobody" where nobody does.
- Agent count and the split-test answers for each agent (multi-agent.md).

## 4. Red flags

Severity: **Critical** = can cause irreversible harm or data loss; **High** = bug or major cost/reliability problem; **Medium** = maintainability or efficiency; **Low** = style.

| Red flag | Severity | Fix |
|---|---|---|
| Model output reaches a write or high-impact tool without code validation | Critical | Validation gate: allowlist, schema, scope, risk tier [SYSTEMS ch10] |
| Irreversible action (payment, refund, delete, external send) with no approval policy in code | Critical | Approval gate above a threshold; agent proposes, person decides; threat-model with agent-threat-modeler |
| Side-effecting step retried or resumed without an idempotency key | Critical | Idempotency key per run + step + action [SYSTEMS ch17] |
| Loop runs inside a webhook or trigger handler that the sender retries on timeout, with no event dedupe | Critical if the run writes, else High | Acknowledge, deduplicate by event ID, enqueue, process async (control-loop.md) |
| Model writes free-form queries or commands (SQL, shell, HTTP) against real data stores | Critical | Scoped, parameterised tools; hand to agent-tool-designer and agent-threat-modeler |
| Memory shared across users, tickets or tenants | High | Per-run execution state; long-term memory design with agent-context-designer |
| Adverse or regulated decision (denial, referral, eligibility) made or worded by the model with no decision record | Critical | A person decides; decision record with reason codes from a fixed list, evidence links, versions; regulatory requirements to agentic-business-case |
| Client approval threshold computed from a model-extracted amount, or splittable across payments | Critical | Compute the measure in code from the system of record; aggregate per case |
| Run held open for days waiting on a decision made in another system | Medium | End with `handed_off`; start a new run on the decision event (control-loop.md) |
| Regenerated drafts overwrite each other with no version | Medium | Versioned outputs with a current pointer; reject decisions on superseded versions |
| Critical constraint exists only in the prompt | High (Critical if destructive) | Enforce in orchestrator, tool layer or policy engine [ENTERPRISE ch7] |
| No step, time or cost cap, or caps left at framework defaults nobody chose | High | Budgets with numbers, sized from eval worst case (control-loop.md) |
| No no-progress detection | High | Stop on repeated (tool, args) or N steps without new facts [SYSTEMS ch8] |
| Cap-hit, error and success exits produce the same output | High | Exit statuses carried to the output; partial results say what is missing |
| Required check failure lets the run continue | High | Stop or escalate; degrade only for optional steps [SYSTEMS ch10] |
| Model calls for deterministic work (fetching the obvious next thing, formatting, arithmetic) | Medium (High at volume) | Prefetch and compute in code [SYSTEMS ch16] |
| Several agents with the same context, tools and output schema (role theatre) | High | Merge; apply the split test [SYSTEMS ch13] |
| LLM manager/coordinator routing every step, accumulating summarising and judging | High | Coordinator in code; LLM routing as enum + FINISH |
| Every agent receives the full conversation history | Medium | Task + named context slice; filter handoffs [DEFGUIDE ch2] |
| Agents can message each other without a hop cap or repetition detection | High | Hop and round caps, tailspin detection [ENTERPRISE ch6] |
| Critique or reflection loop with no round cap, or reflection on every step without a signal | Medium | 1 to 2 rounds; trigger on evidence [DLLMA ch10] |
| Reasoning effort high everywhere, never measured | Medium | Sweep per task family; default low or adaptive [BUILDAGENTIC ch7] |
| Hand-parsed THOUGHT/ACTION text format | Medium | Native tool calling or structured output |
| No checkpoints on runs that wait for people or last minutes | High | Checkpoint per step with config versions; durable execution if long |
| Checkpoints hold only messages | Medium | Add tool results, pending routing, config versions [DEFGUIDE ch5] |
| Policy or prompt can change mid-run | Medium | Pin and hash config per run [DEFGUIDE ch5] |
| No trace that answers "why did it do that?" | High | Per-step trace; hand to agent-ops-reviewer |
| Raw chain-of-thought shown to users or used as the audit record | Medium | Log structured decisions and reasons [SYSTEMS ch3] |
| Agent with no remaining autonomy (every step forced by rules) | Low | Replace with code [ENTERPRISE ch1] |
| An agent where a workflow was never measured against it | Medium | Build-both comparison (autonomy-and-shape.md) |
| Graph with branches and cycles no test case requires | Medium | Collapse to a chain; add branches when a test needs one [BUILDAPPS ch5] |
| Single process runs every step at high volume | Medium | Orchestrator service, external state, queues [SYSTEMS ch10] |

## 5. Full checklist by area

**Shape and authority**
- [ ] Each step has a shape chosen per step, with the run-time discovery named for every agent step.
- [ ] Steps needing full accuracy, certification or millisecond latency are code.
- [ ] Each step's authority is set separately from its shape; "reversible" and "cheap" are defined for the domain.
- [ ] Client thresholds have a pinned measure and act as a floor on oversight.
- [ ] Regulated or adverse decisions have a human decider and a decision record with reason codes.
- [ ] A rollout plan gives each step's starting stage, promotion criteria and rollback trigger.
- [ ] A cheaper baseline was compared for any agent step whose path is in doubt, with a primary metric, guardrails and a minimum gain written in advance.

**Runtime**
- [ ] One named owner each for decide, validate, authorise, execute, store, record, stop.
- [ ] Structured proposals validated against schema and allowlist; capped re-asks with a one-line reason.
- [ ] Tools have risk tiers; writes gated in code; approvals where the tier requires.
- [ ] Budgets with numbers: steps, calls, tokens or cost, wall time, breadth.
- [ ] No-progress detection.
- [ ] Every exit designed: completed, partial, awaiting_approval, handed_off, escalated, failed; downstream decisions start a new run.
- [ ] Retries split by failure class; idempotency on writes; required-check failure stops the run.
- [ ] State schema; checkpoint per step with versions; run ID; config pinned per run.
- [ ] Execution mode fits the latency target; long runs async and resumable.

**Reasoning**
- [ ] Each model step names its dials with numbers and the signal each depends on.
- [ ] ReAct uses native tool calling and has a step cap.
- [ ] Plans are data with replanning triggers; the replanner can end early.
- [ ] Reflection fires on evidence and is capped.

**Multi-agent (if any)**
- [ ] A single-agent baseline exists with scores, latency and cost.
- [ ] Each agent passes the split test.
- [ ] Orchestrator in code; typed messages validated at each hop; context slices written down.
- [ ] Caps on calls, hops, rounds; repetition detection; written conflict rule.
- [ ] Run ID propagated; nested trajectories traceable.

## 6. Report shape

Findings first, sorted by severity: finding, evidence (file:line, config key, or trace ID), impact, fix. Then the target architecture using the design-doc template, marking each section **keep**, **change** or **add**, and a migration order that fixes Critical items first without a rewrite.
