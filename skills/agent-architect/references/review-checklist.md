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
- Lifecycle position: which stage gates the system has passed, with evidence for each, and which sibling reviews it still needs (lifecycle-map.md).

## 4. Red flags

Severity: **Critical** = can cause irreversible harm or data loss; **High** = bug or major cost/reliability problem; **Medium** = maintainability or efficiency; **Low** = style.

| Red flag | Severity | Fix |
|---|---|---|
| Model output reaches a write or high-impact tool without code validation | Critical | Validation gate: allowlist, schema, scope, risk tier [SYSTEMS ch10] |
| Irreversible action (payment, refund, delete, external send) with no approval policy in code | Critical | Approval gate above a threshold; agent proposes, person decides; threat-model with agent-threat-modeler |
| Side-effecting step retried or resumed without an idempotency key | Critical | Idempotency key per run + step + action [SYSTEMS ch17] |
| Loop runs inside a webhook or trigger handler that the sender retries on timeout, with no event dedupe | Critical if the run writes, else High | Acknowledge, deduplicate by event ID, enqueue, process async (agent-harness-designer: references/control-loop.md) |
| Model writes free-form queries or commands (SQL, shell, HTTP) against real data stores | Critical | Scoped, parameterised tools; hand to agent-tool-designer and agent-threat-modeler |
| Memory shared across users, tickets or tenants | High | Per-run execution state; long-term memory design with agent-context-designer |
| Adverse or regulated decision (denial, referral, eligibility) made or worded by the model with no decision record | Critical | A person decides; decision record with reason codes from a fixed list, evidence links, versions; regulatory requirements to agentic-business-case |
| Client approval threshold computed from a model-extracted amount, or splittable across payments | Critical | Compute the measure in code from the system of record; aggregate per case |
| Run held open for days waiting on a decision made in another system | Medium | End with `handed_off`; start a new run on the decision event (agent-harness-designer: references/control-loop.md) |
| Regenerated drafts overwrite each other with no version | Medium | Versioned outputs with a current pointer; reject decisions on superseded versions |
| Critical constraint exists only in the prompt | High (Critical if destructive) | Enforce in orchestrator, tool layer or policy engine [ENTERPRISE ch7] |
| No step, time or cost cap, or caps left at framework defaults nobody chose | High | Budgets with numbers, sized from eval worst case (agent-harness-designer: references/control-loop.md) |
| No no-progress detection | High | Stop on repeated (tool, args) or N steps without new facts [SYSTEMS ch8] |
| Cap-hit, error and success exits produce the same output, or a step's flag reads the same for "not needed" and "failed" | High | Exit statuses carried to the output; partial results say what is missing; per-step status `called` / `not_needed` / `failed: <reason>` |
| Off-list or unparseable model output (a label, yes/no, a timeout) defaults to a real answer | Critical if it defaults to an adverse decision, else High | Treat it as `invalid`: re-ask once, then escalate (agent-harness-designer: references/control-loop.md, failure table) |
| A non-`completed` exit only writes a log line, or a dead-letter or failure sink has never been seen to fire | High | Durable sink per exit with run ID and checkpoint reference; a test that forces each exit (agent-harness-designer: references/control-loop.md, "Exit statuses") |
| Run state or checkpoints written with an unconditional overwrite where more than one writer can exist (retry plus resume, replicas, redelivered events) | High | Conditional create/update on a version, or one consumer per case (agent-harness-designer: references/control-loop.md, "One writer per run") |
| Checkpoints stored as untyped JSON with no schema version, or resume tested only inside one process | High | Serialise through the typed state schema, version it, test write-kill-reload across processes (agent-harness-designer: references/control-loop.md) |
| Ordered-stream trigger with unbounded retries, or a poison event that blocks its partition | High | Bounded retries by count and age, batch splitting, report the first failure, a tested failure sink (agent-harness-designer: references/control-loop.md, "Ordered streams") |
| Required check failure lets the run continue | High | Stop or escalate; degrade only for optional steps [SYSTEMS ch10] |
| Model calls for deterministic work (fetching the obvious next thing, formatting, arithmetic) | Medium (High at volume) | Prefetch and compute in code [SYSTEMS ch16] |
| Several agents with the same context, tools and output schema (role theatre) | High | Merge; apply the split test [SYSTEMS ch13] |
| LLM manager/coordinator routing every step, accumulating summarising and judging | High | Coordinator in code; LLM routing as enum + FINISH |
| Every agent receives the full conversation history | Medium | Task + named context slice; filter handoffs [DEFGUIDE ch2] |
| Agents can message each other without a hop cap or repetition detection | High | Hop and round caps, tailspin detection [ENTERPRISE ch6] |
| A split justified by data or permissions, but every agent's identity can reach every store, or nobody has tested a denial | High | Per-agent credentials scoped to its own stores; a negative test per other agent (multi-agent.md, "If you split") |
| Undocumented direct call between agents, with no budget, fallback, audit record or status | Medium | Document it as an exception, or route it through the orchestrator (multi-agent.md) |
| Message types hand-copied into each agent, or receivers that reject unknown fields | Medium | One schema source, additive changes, contract tests, readers deployed first (multi-agent.md) |
| Peer address compiled into another agent's package | Medium | Address in the registry entry or deploy-time configuration |
| Critique or reflection loop with no round cap, or reflection on every step without a signal | Medium | 1 to 2 rounds; trigger on evidence [DLLMA ch10] |
| Reasoning effort high everywhere, never measured | Medium | Sweep per task family; default low or adaptive [BUILDAGENTIC ch7] |
| Hand-parsed THOUGHT/ACTION text format | Medium | Native tool calling or structured output |
| No checkpoints on runs that wait for people or last minutes | High | Checkpoint per step with config versions; durable execution if long |
| Checkpoints hold only messages | Medium | Add tool results, pending routing, config versions [DEFGUIDE ch5] |
| Policy or prompt can change mid-run | Medium | Pin and hash config per run [DEFGUIDE ch5] |
| A peer agent's deploy changes the code a running case talks to | Medium | Call peers at versions or aliases fixed at run start (agent-harness-designer: references/control-loop.md) |
| No trace that answers "why did it do that?" | High | Per-step trace; hand to agent-ops-reviewer |
| Raw chain-of-thought shown to users or used as the audit record | Medium | Log structured decisions and reasons [SYSTEMS ch3] |
| Agent with no remaining autonomy (every step forced by rules) | Low | Replace with code [ENTERPRISE ch1] |
| An agent where a workflow was never measured against it | Medium | Build-both comparison (autonomy-and-shape.md) |
| Graph with branches and cycles no test case requires | Medium | Collapse to a chain; add branches when a test needs one [BUILDAPPS ch5] |
| Single process runs every step at high volume | Medium | Orchestrator service, external state, queues [SYSTEMS ch10] |
| Drafting and executing share one state or one call, so draft-only mode cannot be enforced | High | Separate states with enforcement in code; only code moves a draft into the world [PRODGUIDE ch16] (pattern-catalog.md) |
| The loop follows next actions advertised in tool results without checking the allowlist and risk tiers | High | Treat advertised actions as hints; intersect with the allowlist and tiers (pattern-catalog.md); contract with agent-tool-designer, threat with agent-threat-modeler |
| A voice-in, voice-out model speaks commitments (refunds, bookings) with no text checkpoint | High | Cascaded pipeline, or a background agent that checks policy and confirms the call ran before anything is spoken (pattern-catalog.md, "Voice agents") |
| A model-written plan where the steps could be listed, or a fixed reflect-N loop described as planning | Medium | Fixed steps in code; a model-written plan only where the decomposition depends on the input [NG Agentic Design Patterns Part 4, Planning, 2024-04-10] |
| Authority raised for the whole agent on one period's approval rate, with no case count, no written rules for the new actions and no recovery plan | High | Promote per step on the move-up conditions (autonomy-and-shape.md, "Raising authority over time") |
| A stage gate skipped: tools or harness built before a threat model and permission tiers exist, or launch on the 30-case smoke suite | High | Close the gate first (lifecycle-map.md); threat model at Design, held-out release gate at Prove |

## 5. Full checklist by area

**Lifecycle gates** (lifecycle-map.md; the owner skill supplies each item)
- [ ] Decide: the responsibility sentence passes the concreteness test; the data readiness audit passed and a five-factor starting level is recorded, with any factor at 1 named as a constraint (agentic-business-case); a usable API exists for every system touched (agent-tool-designer).
- [ ] Design: this architecture, with the loop contract and sizing; a threat model with Rule of Two triage and a permission tier per action (agent-threat-modeler); tool boundaries (agent-tool-designer); a model per role (agent-model-selector).
- [ ] Build: tool contracts reviewed (agent-tool-designer); the harness has a run record, checkpoints, cancellation and a kill switch (agent-harness-designer); retrieval and memory designed (agent-context-designer); a smoke suite and baseline (agent-eval-designer).
- [ ] Prove: hard checks pass on held-out tasks; harness tests pass; the red-team pass is done; contract tests run in CI.
- [ ] Run: the readiness gate passes before each rollout stage and monitoring is live (agent-ops-reviewer); each widening of autonomy meets written move-up conditions, judged per action class (agent-threat-modeler).

**Shape and authority**
- [ ] Each step has a shape chosen per step, with the run-time discovery named for every agent step.
- [ ] Steps needing full accuracy, certification or millisecond latency are code.
- [ ] Each step's authority is set separately from its shape; "reversible" and "cheap" are defined for the domain.
- [ ] Client thresholds have a pinned measure and act as a floor on oversight.
- [ ] Regulated or adverse decisions have a human decider and a decision record with reason codes.
- [ ] A rollout plan gives each step's starting stage, promotion criteria and rollback trigger.
- [ ] A cheaper baseline was compared for any agent step whose path is in doubt, with a primary metric, guardrails and a minimum gain written in advance.

**Runtime** (the loop contract is set here; the runtime that enforces it is designed with agent-harness-designer)
- [ ] One named owner each for decide, validate, authorise, execute, store, record, stop.
- [ ] Structured proposals validated against schema and allowlist; capped re-asks with a one-line reason.
- [ ] Tools have risk tiers; writes gated in code; approvals where the tier requires.
- [ ] Budgets with numbers: steps, calls, tokens or cost, wall time, breadth.
- [ ] No-progress detection.
- [ ] Every exit designed: completed, partial, awaiting_approval, handed_off, escalated, failed, cancelled; downstream decisions start a new run; every non-completed exit lands in a durable sink that a test has seen fire.
- [ ] Retries split by failure class; idempotency on writes; required-check failure stops the run; off-list model output is `invalid`, never a real answer.
- [ ] Typed state schema with a version; checkpoint per step; run ID; config and peer versions pinned per run; resume tested across processes.
- [ ] One writer per run: conditional state writes or a single consumer per case.
- [ ] Execution mode fits the latency target; long runs async and resumable; ordered-stream triggers have bounded retries and a failure sink.

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
- [ ] Each agent's credentials reach only its own stores, proven by a denial test.
- [ ] Inter-agent schemas come from one source and change additively; discovery by capability and minimum version where agents release independently; addresses in configuration.
- [ ] Any direct agent-to-agent call is a documented exception with budget, fallback, audit record and status.
- [ ] Event-driven: partitioned by case or session; log retention covers replay and audit.

## 6. Report shape

Findings first, sorted by severity: finding, evidence (file:line, config key, or trace ID), impact, fix. Then the target architecture using the design-doc template, marking each section **keep**, **change** or **add**, and a migration order that fixes Critical items first without a rewrite.
