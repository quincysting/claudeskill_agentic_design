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
- Pin configuration per run: load the policy, hash it, write policy and schema hashes and run ID into state, so a config change cannot alter a run in flight [DEFGUIDE ch5].
- Human waits use the same mechanism: interrupt + checkpointer, resume when input arrives [BUILDAGENTIC ch2].

## Execution mode

| Choice | Pick |
|---|---|
| Sync request-response | Short, bounded work inside the UX latency budget |
| Async job | Long analysis, slow tools, approval waits. Needs job IDs, status, cancellation, correlation IDs, retries [SYSTEMS ch10] |
| Long-running across many context windows | Keep progress outside the model: a progress file, a structured task list with each item marked failing until verified, git commits per unit; each session picks one unfinished item, verifies it end to end, records it (Anthropic, "Effective harnesses for long-running agents", 2025-11) |

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

Left out on purpose, add per design: on resume, execute `pending` once approved instead of re-planning; time and cost budgets next to the step budget; schema validation of the final answer; per-step trace records; a circuit breaker.
