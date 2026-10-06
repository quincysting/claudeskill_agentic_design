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
- **Guard:** step cap (even the minimal teaching loop has `max_steps` of 10 [ILLUSTRATED ch6]), no-progress detection, validation gate, explicit exits. These live in the loop, not the prompt. See control-loop.md.

### Plan, then deterministic execution
- **Use:** plans are reviewable and steps map to registered tools.
- **Avoid:** most observations would invalidate the plan.
- **Shape:** the model writes a plan as data (ID, steps with step ID, tool or collaborator, parameters, status, result; a DAG when steps depend on each other); code binds each step to a registered tool, fills parameters, and a deterministic engine runs it. MESH prefers the engine over model-driven execution for repeatability and explainability, and persists plan, bindings, substitutions and execution log for comparison afterwards [MESH ch5] [MESH ch6].
- **Payoff:** an inspectable plan, a clear failure location, cheaper models during execution [BUILDAPPS ch5].
- **Cost:** adaptability. Add explicit replanning triggers (see reasoning-strategy.md).

### Deterministic prefetch + bounded planner (default)
- **Use:** most steps fixed, a few need judgment. This is the reference design in [SYSTEMS ch16] and [SYSTEMS ch17].
- **Shape:** code fetches what is always needed (e.g. merge-request metadata and changed files). The planner returns one next action from an allowlist, or "done", as structured data. The service validates tool name, argument schema, scope (the file belongs to this request) and step budget before anything runs [SYSTEMS ch17]. Separate model roles behind separate interfaces: a reasoner that picks the next bounded action, and an analyzer that turns one unit of input into evidenced findings and returns nothing when evidence is weak [SYSTEMS ch17].
- **Rule:** the planner should be "boring in the best possible way" [SYSTEMS ch16]. Every step that code can decide is removed from the model.

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
