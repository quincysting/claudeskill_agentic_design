# Runtime and control loop

Citation keys such as [SYSTEMS ch10] point to the book list under Sources in SKILL.md.

The model proposes; code decides; tools act. Every failure then has an address: weak context is a context fix, an unsafe call is a validation fix, a runaway loop is a stop-rule fix [SYSTEMS ch10]. "The model decided" is never a root cause, only evidence that no component was given the job [SYSTEMS ch10].

## Runtime anatomy

```
request
  -> ORCHESTRATOR (code): load run state, prefetch fixed inputs, assemble context
  -> MODEL: returns ONE structured proposal {final} | {tool, args, reason}
  -> VALIDATION + POLICY GATE (code): schema, allowlist, scope, permission, risk tier, budget
       reject -> one-line reason back to the model (costs a step)
       needs approval -> pause, checkpoint, status awaiting_approval
       approve -> TOOL REGISTRY (code): timeout, retry, idempotency key -> backend
  -> ORCHESTRATOR: record trace, update state, checkpoint, check stop conditions
  -> loop, or exit with a status
```

## Ownership table (fill one per design)

| Responsibility | Owner | Never |
|---|---|---|
| Decide next action | Model (planner role), or code for fixed steps | — |
| Validate proposal | Gate in the orchestrator | the model |
| Authorise by risk tier | Policy in code or an external policy engine | the prompt |
| Execute | Tool registry | model output reaching a function unvalidated [SYSTEMS ch10] |
| Store state | Orchestrator, external store | conversation history as the only state |
| Record evidence | Trace store | — |
| Stop | Orchestrator's stop rules | "the model stopped calling tools" as the only exit |

ENTERPRISE frames the orchestrator as the accountable control plane: it sees every request and tool call, enforces autonomy rules, keeps the audit trail [ENTERPRISE ch7]. Vendors call this the harness.

## Decision contract

The planner returns exactly one of:

```json
{"final": {...result schema...}}
{"tool": "<name from allowlist>", "args": {...}, "reason": "<one line>"}
```

A done flag, one tool, arguments and a reason is the planner contract in [SYSTEMS ch16]. Anything else is rejected. Use the provider's native tool calling or structured output, not regex-parsed text.

## Validation gate checks, in order

1. Parses against the schema.
2. Tool name is in the allowlist for this agent and this step.
3. Arguments match the tool's input schema.
4. Scope: arguments refer to objects this run may touch (the file is in this merge request; the claim ID is this claim).
5. Permission and risk tier (below).
6. Budget remains.
7. Not a repeat of an executed (tool, args) pair.

On rejection, feed one clear sentence of what was wrong and what is allowed, not a stack trace, and count the re-ask against the budget [DEFGUIDE ch5].

## Tool risk tiers

| Tier | Examples | Rule [SYSTEMS ch10] |
|---|---|---|
| read | fetch, search, list | may run automatically |
| write | create draft, post comment, update record | validation + authorisation in code |
| high-impact | payments, deletions, external messages, permission changes | approval + audit; idempotency key; often a person |

For high-impact actions, prefer a **proposal, not a tool**: the agent's final output carries `{action, target, amount, reason}`, and a code action path recomputes eligibility and limits from its own data, checks current state, applies the approval threshold and executes. The model never holds the credential.

Critical constraints live outside the context window. An agent told to confirm before deleting emails deleted more than two hundred, most likely because context compression dropped the instruction [ENTERPRISE ch7]. Prompts shape behaviour; validation decides what the system accepts [SYSTEMS ch17]. Tool contracts themselves (names, schemas, descriptions) are agent-tool-designer's job.

## Budgets

Write every one down with a number before launch. Without one, agents drift toward more calls, more context and more output [SYSTEMS ch16].

| Budget | How to set it | Reference points |
|---|---|---|
| Loop steps | Worst-case steps observed in eval + headroom | `max_steps` 10 in ILLUSTRATED's loop [ILLUSTRATED ch6]; 12 loop steps in SYSTEMS's review agent [SYSTEMS ch16]; 5 plan steps in BUILDAGENTIC's deep-research agent [BUILDAGENTIC ch5] |
| Model calls | Count per path | 5 for SYSTEMS's review agent [SYSTEMS ch16] |
| Tool calls | Per tool and total | Research subagents: 3 to 10 calls for simple fact-finding, 10 to 15 each for comparisons (Anthropic, 2025-06) |
| Tokens or cost per run | From the cost ceiling per task | — |
| Wall clock | From the UX: interactive → seconds; longer → async job | 30 s for SYSTEMS's review agent [SYSTEMS ch16] |
| Breadth | Files, chunks, findings, candidates | 10 files, 5 chunks, 5 findings [SYSTEMS ch16] |
| Re-asks after a rejected proposal | Small; each costs a step | 2 is this skill's default |
| Review or critique rounds | 1 to 2, then accept, reject or escalate [SYSTEMS ch13] | — |
| Retries per transient failure | With backoff | — |

SYSTEMS says its numbers are only examples; what it requires is that some budget exists before production. "Agent systems do not scale only by adding machines. They scale by bounding work." [SYSTEMS ch10]

## Stop conditions

Four legitimate reasons to stop [SYSTEMS ch8]:
1. Goal completed.
2. Enough information to answer well.
3. No progress: the same (tool, args) twice, or N steps with no new facts.
4. Resource limit: steps, calls, tokens, cost, time.

The easiest mistake is to keep going because the model can always suggest another step. Agents retry with reworded arguments, refetch unchanged data, or produce another plan instead of noticing they are blocked [SYSTEMS ch8]. The orchestrator decides whether another step is justified.

## Exit statuses

Every path ends in one of these, carried to the final output:

| Status | Meaning |
|---|---|
| `completed` | Goal met, output validated |
| `partial` | Stopped early; states what was not done and why (budget, no progress, optional dependency down) |
| `awaiting_approval` | Paused at a short in-run gate; state checkpointed; this run resumes on the decision |
| `handed_off` | Package delivered (draft, proposal, evidence, decision-record stub) to a person or another system that decides on its own timeline; external reference stored; this run is over |
| `escalated` | Handed to a person with evidence, sources and the reason, because the run could not proceed |
| `failed` | Required check or dependency failed; nothing irreversible done after the failure |

Partial output beats fake completeness [SYSTEMS ch16]. A common bug: the step cap or an error routes to the same summariser as success, and a truncated run produces a confident report. Carry the status through.

- Each optional step reports what it did: `called`, `not_needed` or `failed: <reason>`. A single flag that reads the same for "skipped" and "broke" makes a failure look like success.
- Every non-`completed` exit lands somewhere durable that a person or system works from: the approval queue, the receiving system for `handed_off`, a review queue for `escalated` and `partial`, a dead-letter queue for `failed` once retries are exhausted. Each item carries the run ID, status, reason and a checkpoint reference. A log line alone is not a sink. Prove each sink with a test that forces that exit and checks the item arrives.

### Downstream decisions: hand off, don't hold the run

Use `awaiting_approval` only when the run itself holds the pending action and the decision comes back to it quickly, through the agent's own UI or queue, within minutes to hours.

When the decision is made by a person in another system (a claims queue, a ticketing tool) on that system's SLA:
1. End the run with `handed_off`. Store the package, the case ID, the external reference and the config versions used.
2. Let the decision arrive as a new event (webhook, poll, queue message) keyed by case ID.
3. Start a new run on that event. It loads the stored package, re-reads current state (documents, amounts, status may have changed), re-validates, then executes the approved action through the action path or closes the case.
4. Reject a decision made on a superseded package version (see versioned outputs below).

Holding a run open for days pins old configuration, ties up resources and acts on stale state.

## Failure handling by class

| Failure | Response |
|---|---|
| Model output breaks schema | Inner loop: re-ask with the validation error, bounded [DEFGUIDE ch5] |
| Closed-vocabulary output (a label, yes/no, met/not met) that is not exactly one allowed value, or no answer (timeout) | Its own `invalid` class: re-ask once, then escalate. Never map it onto a real label, and never onto the adverse one: a garbled reply must not become a denial. Adverse decisions stay with a person (autonomy-and-shape.md) |
| Transient tool or network error | Retry with backoff, bounded |
| Tool unavailable | Alternative tool or path if one exists; else partial or failed |
| Optional enrichment fails | Degrade: continue, mark output partial [SYSTEMS ch10] |
| Required compliance, approval or validation check fails | Stop. Never proceed as if it passed [SYSTEMS ch10] |
| Repeated garbage from one component | Circuit breaker pauses it (AGENTICAI's summariser was paused after three gibberish outputs in a minute) and routes to fallback or a person [AGENTICAI ch8] |
| Low confidence or blocked | Escalate to a person with sources and confidence attached [AGENTICAI ch8] |

Two correction loops, kept separate [DEFGUIDE ch5]: the **inner loop** re-asks the model to satisfy the same schema (fast, for model-shaped failures); the **outer loop** is the graph or orchestrator, with gates, retry routing and checkpoints (for timeouts, infrastructure failure, policy violations and side effects). Count retries in state so they stay bounded and visible.

**Idempotency.** A retried, resumed or replayed step must not repeat side effects. Every write carries an idempotency key derived from run ID + step ID + action, or from the business object (ticket + charge + action) when the same action could come from more than one run [SYSTEMS ch10] [SYSTEMS ch17]. Two more places duplicates come from:
- **Triggers.** Webhooks and queues redeliver, especially when the handler is slow. Derive the run ID from the event (source ID + event ID) and deduplicate before starting, or the whole run, writes included, repeats. Do not run the loop inside a webhook handler; acknowledge, enqueue, process.
- **Different keys, same effect.** A key only catches repeats of itself. For money and other high-impact writes, also check the target's current state before acting (has this charge already been refunded?).

**Versioned outputs.** When a run regenerates an artifact (a new draft or recommendation after new documents arrive), write it as (case ID, artifact type, version), move a "current" pointer by upsert, and keep superseded versions for audit. Consumers act only on the current version; a decision made on an older version is rejected or re-confirmed.

## State and checkpoints

- **Execution state** (this run: fetched inputs, tried actions, findings, retry counts, status) is different from **memory** that outlives runs. Memory design is agent-context-designer's job.
- Keep the minimum the workflow needs, in a database, not process memory: runtime status (busy, waiting, error), task status, task state detailed enough to restart and diagnose [MESH ch5].
- Most systems are stateless per request with task state in an external store [SYSTEMS ch10].
- Checkpoint at every step boundary, keyed by run ID (thread ID per conversation branch). A checkpoint holds intermediate tool results, the node where execution paused, pending routing, and the configuration to resume with the same model, prompt, tools and policy, so a late failure does not repay earlier expensive reasoning [DEFGUIDE ch5].
- Pin configuration per run: load the policy, hash it, write policy and schema hashes and run ID into state, so a config change cannot alter a run in flight [DEFGUIDE ch5]. Peer agents are configuration too: a multi-step run calls versioned endpoints or aliases fixed at run start, or a deploy mid-run means later steps talk to different code.
- Human waits use the same mechanism: interrupt + checkpointer, resume when input arrives [BUILDAGENTIC ch2].
- When new input arrives for a stored case, restart from the first phase whose inputs changed and reuse the checkpoints before it.

### One writer per run

Two writers can hold the same run: a retry and a resume, two replicas, a redelivered event. With unconditional writes the last writer wins and the other write is lost without an error. Either:
- make state writes conditional: create only if the key does not exist; update only if the stored version equals the version you read, and increment it. On a failed condition, reload and decide again; never blind-overwrite. IDs for append-only records (ledger entries, step logs) come from a conditional create or a time-ordered unique ID, never "read the last ID and add one"; or
- route every event for one run or case through a single consumer (multi-agent.md, "Partitioning"), so there is one writer by construction.

```python
def save(store, run_id, state, read_version):     # read_version is 0 for a new run
    ok = store.put_if(run_id, {**state, "version": read_version + 1}, expect_version=read_version)
    if not ok:
        raise StaleState(run_id)                    # reload and re-decide; never overwrite
```

### Typed, versioned checkpoints

- Serialise through the state schema (a typed model), not ad hoc JSON. Enums, nested records and optional fields must round-trip; a string compared with an enum is silently false.
- Store a state-schema version with every checkpoint. On load, migrate known older versions and refuse unknown ones: end the run `failed` with the reason, or restart it deliberately from a recorded position. Never resume from state the code can't read.
- Test resume across processes: write in one process, kill it, load in a fresh one, compare field by field. A same-process test passes even with an in-memory store.
- When a run consumes a stream, record the last position it committed. On a restart without usable state, start from that position or the earliest retained one, never "latest" by default, which skips the backlog.

## Execution mode

| Choice | Pick |
|---|---|
| Sync request-response | Short, bounded work inside the UX latency budget |
| Async job | Long analysis, slow tools, approval waits. Needs job IDs, status, cancellation, correlation IDs, retries [SYSTEMS ch10] |
| Long-running across many context windows | Keep progress outside the model: a progress file, a structured task list with each item marked failing until verified, git commits per unit; each session picks one unfinished item, verifies it end to end, records it (Anthropic, "Effective harnesses for long-running agents", 2025-11) |
| Triggered from an ordered stream | Events for one key must be handled in order (a partitioned log, change events per case). Needs bounded retries and a tested failure sink (below) |

### Ordered streams: poison events and failure sinks

In an ordered stream one failing event stops everything behind it in its partition, and the trigger retries it until the event expires while the backlog grows.
- Bound retries by count and by event age, and split a failing batch to isolate the bad event.
- Report the first failed event and stop processing the rest of the batch, so later events aren't handled before it; the source redelivers from there.
- Send the isolated event to a failure sink with enough to replay it. If the sink stores only pointers (partition and offset), keep the source's retention longer than your triage time.
- Attach the sink to the trigger that reads the stream. A sink configured for another invocation path never sees these failures, and a sink that never fires looks exactly like a healthy one. Prove the path with a test that injects a malformed event and checks it lands in the sink.
- Partition by the case or session whose events must stay in order (multi-agent.md, "Partitioning").

## Estimating at volume

Design-level sizing; production tuning and serving belong to agent-ops-reviewer. Put assumptions next to every figure.

1. **Tokens per path.** For each model call: input (system prompt + tool definitions + assembled context + documents) and output (including reasoning tokens, billed as output). Multiply per-document calls by documents per case. Report typical and worst case.
2. **Peak load.** Daily volume → peak arrivals per minute. Measure the peak hour from history; if unknown, assume arrivals within business hours with a 2× peak-hour factor and label it (this skill's convention).
3. **Concurrency.** Runs in flight ≈ arrival rate × average run duration (Little's law). Size workers and connection pools from it.
4. **Rate limits.** Required requests per minute = peak arrivals × calls per case; required tokens per minute = peak arrivals × tokens per case. Compare with the provider tier's limits (check current values). A queue absorbs bursts; expected wait ≈ backlog ÷ throughput, which must fit the SLA.
5. **Caching.** Put stable content (system prompt, tool definitions, policy text) first so the provider's prompt cache can reuse it; cached input is cheaper and faster (check current pricing). Changing tools or thinking settings between calls invalidates the cache.
6. **Cost.** Tokens × current prices per model role. If prices are unknown, stop at tokens and calls and say so.
7. **Against the incumbent.** For human labour, compare per case: today's handling minutes × loaded hourly rate, against model and infrastructure cost plus the review and approval minutes the design still needs. Compare error and rework rates too. The business case itself goes to agentic-business-case.

## Reliability arithmetic (direction, not prediction)

Chain of n steps, each succeeding independently with probability p: success = p^n. At p = 0.98, ten steps ≈ 0.82 [DEFGUIDE ch5].

A gate catching fraction v of failures and allowing recovery raises effective per-step success to p + (1 − p)·v. At p = 0.98, v = 0.9: 0.998 per step, ≈ 0.98 over ten steps [DEFGUIDE ch5].

Real errors are not independent (they cluster on hard decisions), so use the numbers for direction. What survives: adding steps without checks makes things worse; the gain comes from catching errors at boundaries; a step moved into code does not compound.

## Trace per step (minimum)

Assembled context reference, proposal, validation result, tool call and result, latency, tokens, model, prompt and policy versions, status. Persist structured plans, decisions with one-line reasons and stop reasons; raw reasoning text is optional and model-specific [SYSTEMS ch8]. Trace design and dashboards: agent-ops-reviewer.

## Loop skeleton

A minimal shape to adapt; the planner, executor, approval check and store are injected.

```python
import json

TOOLS = {"get_record": ({"id"}, "read"), "post_note": ({"id", "text"}, "write")}

def run(task, plan, execute, approve, store, run_id, max_steps=10):
    st = store.load(run_id) or {"facts": {"input": execute("prefetch", {"task": task})},
                                "seen": [], "steps": 0}
    while st["steps"] < max_steps:
        st["steps"] += 1
        d = plan(task, st["facts"])                         # model: {"final"} or {"tool","args","reason"}
        if "final" in d:
            return done(store, run_id, st, "completed", d["final"])
        spec = TOOLS.get(d.get("tool"))
        if not spec or set(d.get("args", {})) != spec[0]:
            st["facts"]["error"] = f"invalid call; allowed: {sorted(TOOLS)}"
            continue                                        # re-ask costs a step
        key = d["tool"] + json.dumps(d["args"], sort_keys=True)
        if key in st["seen"]:
            return done(store, run_id, st, "partial", "no progress")
        if spec[1] != "read" and not approve(d):
            store.save(run_id, {**st, "pending": d})        # resume from here after the decision
            return {"status": "awaiting_approval", "proposal": d}
        st["seen"].append(key)
        st["facts"].pop("error", None)
        st["facts"][d["tool"] + str(d["args"])] = execute(d["tool"], d["args"],
                                                          idem_key=f"{run_id}:{st['steps']}")
        store.save(run_id, st)                              # checkpoint every step
    return done(store, run_id, st, "partial", "step budget")

def done(store, run_id, st, status, payload):
    store.save(run_id, {**st, "status": status})
    return {"status": status, "result": payload, "steps": st["steps"]}
```

Left out on purpose, add per design: on resume, execute `pending` once approved instead of re-planning; time and cost budgets next to the step budget; schema validation of the final answer; per-step trace records; a circuit breaker; conditional, versioned `store.save` when more than one process can hold a run (see "One writer per run").
