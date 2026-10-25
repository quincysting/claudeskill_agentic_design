# Orchestration pattern catalog

Citation keys such as [MESH ch3] point to the book list under Sources in SKILL.md.

Pick the skeleton pattern first, then the pattern inside each agent step. Each entry gives when to use it, when not to, its characteristic failure, and the guard you must put in code. Names follow Anthropic's "Building effective agents" (2024-12): prompt chaining, routing, parallelization, orchestrator-workers, evaluator-optimizer.

## Quick selector

| Situation | Pattern |
|---|---|
| Known steps, each output checkable | Prompt chain |
| Distinct input classes need different handling | Router (or cascade if the classes are "easy" and "hard") |
| Independent subtasks, or several samples should vote | Parallel fan-out and merge |
| Subtasks only knowable after reading the input | Orchestrator-workers |
| Clear acceptance criteria, latency tolerant | Evaluator-optimizer |
| Next step depends on what was just found | Tool-calling loop (ReAct) |
| Plan reviewable, steps map to registered tools | Plan, then deterministic execution |
| Most steps fixed, a few need judgment | Deterministic prefetch + bounded planner (the production default) |
| Several modes share the same policies | Hierarchical state machine |
| Runs last minutes to days, wait on people, must survive crashes | Durable workflow engine |
| Tools, controls and use cases multiplying | Orchestrator service instead of an embedded loop |
| Actions change systems of record, or approvals arrive later | Draft and execute as separate states |
| Valid next actions depend on server state the model cannot see | Next actions in tool results (affordance-driven tools) |
| Users talk to the agent by voice | Cascaded voice pipeline, or foreground and background agents |

## Ng's four patterns and how reliable each is

Andrew Ng's four agentic design patterns cut the same space more coarsely [NG Agentic Design Patterns Part 1, 2024-03-20]: reflection is the evaluator-optimizer below, tool use is the tool-calling loop, planning is the plan-then-execute pattern, and multi-agent collaboration is multi-agent.md. He orders them by maturity. Reflection and tool use he can make work reliably; planning and multi-agent collaboration are powerful but harder to predict [NG Agentic Design Patterns Part 4, Planning, 2024-04-10] [NG Agentic Design Patterns Part 5, Multi-Agent Collaboration, 2024-04-17].

Use the order as the default for what to try first, with two qualifiers. It is 2024 practitioner judgment from his own applications, not a measurement. And reflection is reliable only when it reflects on evidence such as a test, a tool error or a rubric; unprompted self-critique can make answers worse (reasoning-strategy.md, "Depth: reflection").

## Workflow patterns (code decides the path)

### Prompt chain (explicit pipeline)
- **Use:** steps known; each output can be checked. DLLMA recommends this paradigm for strict reliability needs and advises against autonomous agents for mission-critical work [DLLMA ch10].
- **Avoid:** input variety keeps breaking the fixed path.
- **Failure:** cascade. An early misreading of intent spoils every later step [MESH ch3].
- **Guard:** validate between steps; cap chain length. A model never "performs" a transaction; that is a tool call checked by code.

### Router
- **Use:** inputs fall into distinct classes.
- **Avoid:** a misroute is costly and there is no fallback lane.
- **Failure:** misclassification sends a request down a path that cannot handle it [MESH ch3] [DLLMA ch13].
- **Guard:** a fallback lane for ambiguous inputs; unit-test the router like any classifier [BUILDAPPS ch5]; the router's output is an enum, not prose.
- **Placement:** put the router where its inputs exist. If routing needs fetched records or fields extracted from documents, it sits after prefetch and extraction, mid-chain. Route on rules over structured fields first (amount bands, product type, flags already in the system of record); call a model only for signals that live in unstructured text, and let rules override it.

### Cascade (sequential router)
- **Use:** most inputs are easy and you have a usable confidence signal. Try a cheap model or rule; escalate below a threshold.
- **Avoid:** confidence is uncalibrated or self-reported. Asking the model to state its own confidence has not been shown to work [DLLMA ch13].
- **Usable signals:** classifier output probabilities, agreement across samples (self-consistency), margin between the top two first-token probabilities [DLLMA ch13]. The same thresholding can choose between LLM, coded rule and human [ENTERPRISE ch1].

### Parallel fan-out and merge
- **Use:** independent subtasks, or several samples to vote.
- **Avoid:** outputs can conflict and there is no merge rule.
- **Failure:** contradictory outputs with no reconciliation [MESH ch3].
- **Guard:** a deterministic merge rule written before launch; per-branch timeouts; partial results labelled as such.
- **Provenance through the merge:** when the output must be sourced, each branch returns its tool-produced source records (citation annotations, result IDs, retrieved document IDs), not just text. Code gives each record an ID and the merge keeps the IDs with the content they support. The writer cites IDs, and the citation check compares them with the tool-produced set. Do not have the model write source URLs or titles: checking a citation against a list the model wrote proves nothing.

### Orchestrator-workers
- **Use:** subtasks depend on the input and cannot be listed up front.
- **Avoid:** you cannot cap plan size or depth.
- **Failure:** circular dependencies and infinite loops from unexpected worker responses [MESH ch3].
- **Guard:** caps on plan size, depth and total worker calls, enforced in code. When workers become agents with their own loops, see multi-agent.md.

### Evaluator-optimizer (reflection)
- **Use:** clear criteria; accuracy matters more than latency [MESH ch3].
- **Avoid:** weak critic, latency-bound path. Reflection invoked too often makes the model second-guess correct answers [DLLMA ch10].
- **Guard:** prefer a coded check or explicit rubric as the evaluator; cap iterations (1 to 2 rounds); then accept, reject or escalate.

## Agent patterns (the model picks some next steps)

### Tool-calling loop (ReAct with native tool calling)
- **Use:** the next action depends on what the last one revealed.
- **Avoid:** the path is predictable.
- **Failure:** over-calling tools, looping without stopping criteria, growing state [DEFGUIDE ch2].
- **Guard:** step cap (even the minimal teaching loop has `max_steps` of 10 [ILLUSTRATED ch6]), no-progress detection, validation gate, explicit exits. These live in the loop, not the prompt. See the agent-harness-designer skill, references/control-loop.md.

### Plan, then deterministic execution
- **Use:** plans are reviewable, steps map to registered tools, and the decomposition depends on the input.
- **Avoid:** most observations would invalidate the plan; or the steps could be listed in advance, in which case they belong in code. Planning is worth its unpredictability only when the steps cannot be specified ahead of time [NG Agentic Design Patterns Part 4, Planning, 2024-04-10].
- **Shape:** the model writes a plan as data (ID, steps with step ID, tool or collaborator, parameters, status, result; a DAG when steps depend on each other); code binds each step to a registered tool, fills parameters, and a deterministic engine runs it. MESH prefers the engine over model-driven execution for repeatability and explainability, and persists plan, bindings, substitutions and execution log for comparison afterwards [MESH ch5] [MESH ch6].
- **Payoff:** an inspectable plan, a clear failure location, cheaper models during execution [BUILDAPPS ch5].
- **Cost:** adaptability. Add explicit replanning triggers (see reasoning-strategy.md).

### Deterministic prefetch + bounded planner (default)
- **Use:** most steps fixed, a few need judgment. This is the reference design in [SYSTEMS ch16] and [SYSTEMS ch17].
- **Shape:** code fetches what is always needed (e.g. merge-request metadata and changed files). The planner returns one next action from an allowlist, or "done", as structured data. The service validates tool name, argument schema, scope (the file belongs to this request) and step budget before anything runs [SYSTEMS ch17]. Separate model roles behind separate interfaces: a reasoner that picks the next bounded action, and an analyzer that turns one unit of input into evidenced findings and returns nothing when evidence is weak [SYSTEMS ch17].
- **Rule:** the planner should be "boring in the best possible way" [SYSTEMS ch16]. Every step that code can decide is removed from the model.

### Draft and execute as separate states
- **Use:** actions change systems of record, or approvals arrive later than the run that proposed them.
- **Avoid:** read-only answers with no side effects.
- **Shape:** the run moves through phases: a planner returns the classification, entities, unknowns and a plan mapped to tools; retrieval fetches the governing procedure; a verifier checks the plan against the rules and that unknowns were surfaced rather than guessed; an executor drafts artifacts and payload previews; the run stops at the approval boundary when execution is not allowed [PRODGUIDE ch16]. A run-level state machine (received, planned, drafted, awaiting approval, executed, completed, failed safely) shows operators what is stuck [PRODGUIDE ch16].
- **Rule:** draft and execute are different states with different enforcement in code, not different prompts. The same agent can then run draft-only for weeks and have its permissions widened per action on evidence (autonomy-and-shape.md, "Raising authority over time"). `suggest` is draft-only; only code moves a draft into the world.
- **Runtime:** the draft-only switch, the kill switch that forces it, and approvals bound to the exact action are agent-harness-designer's.

### Next actions in tool results (affordance-driven tools)
- **Use:** tools act on objects with a lifecycle (an order, a claim, a ticket), and which actions are valid depends on server state and on the user, which the model cannot see.
- **Avoid:** stateless lookups.
- **Shape:** each result lists the actions possible now, with their inputs and rules, instead of the prompt hard-coding a workflow [RESTCOOK ch3]. The object's lifecycle is a small state machine whose transitions are typed safe, unsafe or idempotent. A three-step flow can then become two without breaking the agent that follows the controls. State-dependent next actions go in tool results, not in the tool list, which says what a caller may ever do.
- **Guard:** an advertised action is a hint, never a permission. The harness intersects it with the allowlist and the risk tiers before anything runs; following tool output blindly makes it an injection channel. Contract fields and the result shape: agent-tool-designer; the threat side: agent-threat-modeler.

### Hierarchical state machine
- **Use:** behaviour alternates among a few stable modes (plan, act, reflect, await approval) and recovery matters.
- **Avoid:** a three-node flow.
- **Shape:** a superstate (e.g. WORKING) carries rate limits, safety filters and circuit breakers once; substates inherit them; a history marker resumes the last active substate; parallel regions handle fan-out; checkpoint at each state boundary [DEFGUIDE ch1]. A router is a one-edge state machine; a tool-calling agent is a loop inside WORKING.
- **Failure of the flat version:** duplicated edges once planning, reflection, approvals and retries are added.

### Durable workflow engine
- **Use:** runs last minutes to days, wait on people or slow systems, call unreliable services, must survive crashes.
- **Shape:** each agent step is an activity with retries; progress persists; a later failure does not rerun earlier steps [BUILDAPPS ch8].
- **Constraint (as of 2026-10, Temporal docs):** workflow code is replayed against its history and must make the same calls in the same order, so every LLM call, API call and DB query goes in an activity. The orchestration logic must be deterministic code. That is the model/code boundary, enforced by the engine.
- **Alternative:** explicit database state with your own resume logic: more control, more code [BUILDAPPS ch8].

### Orchestrator service versus embedded loop
- Embedded (the app runs the loop) is fine for a narrow early system.
- A dedicated orchestrator service becomes the better design as tools, memory and controls accumulate, because guardrails and observability get one home [SYSTEMS ch10]. A single process funnelling every step hits throughput limits and one crash takes the pipeline down [MESH ch6].

## Voice agents

The loop is the same; what changes is where you can check the output before it reaches the user.

| Shape | Use when | Avoid when |
|---|---|---|
| Cascaded pipeline: speech-to-text, a text agent, text-to-speech | The agent makes commitments (refunds, bookings) that must be checked against policy, and confirmed as executed, before anything is spoken; you need transcripts and swappable parts | Every 100 ms of delay matters more than control |
| Speech-to-speech session | Quick prototypes and low-stakes conversation where an occasional mistake is acceptable | You must inspect or filter each turn before it is spoken |
| Foreground and background agents | You need both: a foreground agent talks in real time while a background agent reasons, applies guardrails and calls tools | A cascade already meets the latency target |

Ng builds the cascade when he needs control: in text there are guardrails and agentic workflows to check, for example, that a promised refund is within policy and that the refund call is actually made, while the tools for checking voice-in, voice-out output are much less mature [NG What I've Learned Building Voice Applications, 2025-02-26]. The cascade costs latency, and people expect conversational replies within roughly 0.3 to 1 second; his 2025 workaround was a quick pre-response while the full answer was computed [NG What I've Learned Building Voice Applications, 2025-02-26]. His 2026 letter describes the foreground and background split instead, which keeps the guardrails in the background agent [NG Building Voice-Enabled Apps is Easier Than You May Think, 2026-04-03]. A benchmarked cascade (a phone bot that claims sub-second response) is in [BUILDAGENTIC ch9]; interruptions and when voice is the wrong channel are in [BUILDAPPS ch3]. Serving and streaming: agent-harness-designer; the latency budget: agent-ops-reviewer.

## Topology discipline

Climb only when a test case requires it: single tool → parallel tools → chain → graph [BUILDAPPS ch5].
- Chains need a length cap because errors compound along them.
- Graphs cost more model calls and add cycles, unreachable nodes and conflicting state merges as failure classes. Cap depth and branching.

## Composing a system

Most designs combine one skeleton with one or two agent steps:
1. Skeleton: chain or router in code, steps from autonomy-and-shape.md.
2. Agent steps: prefetch + bounded planner, or plan-then-execute when the plan should be reviewed.
3. Wrappers where needed: evaluator-optimizer around a drafting step with a rubric; durable engine around the whole run if it waits on people.
4. Control plane: one deterministic orchestrator owns budgets, policy and the audit trail for all of it.

Execution style, per workflow [ENTERPRISE ch5]: turn-taking (answers and sleeps), continuous (loops on a job and revises its plan), triggered (woken by an event such as a review comment). Control passes from coded programs to agents and back as each part of the workflow needs.

## Framework choice

The books disagree (prototype in a framework and own the loop in production [DLLMA ch10]; build on LangGraph [DEFGUIDE ch5]; pick by weighted scorecard [AGENTICAI ch8]). Judge the framework on four abilities instead of its brand. It passes if you can:
1. read the exact prompt sent each step,
2. see every state transition,
3. set every budget and stop rule,
4. replace any component (model, tool, store).

Fail any one and the framework becomes the thing you debug. Framework APIs change fast; check current docs before quoting parameters.
