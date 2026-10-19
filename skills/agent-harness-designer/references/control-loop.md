# Control loop: the runtime contract

Citation keys such as [SYSTEMS ch10] point to the book list under Sources in SKILL.md.

This file moved here from agent-architect (2026-10). The architect keeps the shape decision and a one-paragraph summary of this contract; the loop's runtime detail lives here. The parts of the harness around the loop (run record, kill switch, replay, serving, deployment shapes, harness tests) are in harness-components.md, serving-and-deployment.md and harness-tests.md.

The model proposes; code decides; tools act. Every failure then has an address: weak context is a context fix, an unsafe call is a validation fix, a runaway loop is a stop-rule fix [SYSTEMS ch10]. "The model decided" is never a root cause, only evidence that no component was given the job [SYSTEMS ch10].

## Runtime anatomy

```
request
  -> ORCHESTRATOR (code): load run state by run ID, prefetch fixed inputs, assemble context
  -> GUARD (code): cancel signal, kill flags, budgets; runs before EVERY model call and EVERY tool call
  -> MODEL: returns ONE structured proposal {final} | {tool, args, reason}
  -> VALIDATION + POLICY GATE (code): schema, allowlist, scope, permission, risk tier, repeat check
       reject -> one-line reason back to the model (costs a step)
       draft-only or safe mode -> record a preview, execute nothing
       needs approval -> approval request bound to a digest of (tool, args), expiry, nonce;
                         checkpoint; status awaiting_approval
       allowed -> GUARD again -> save intent -> TOOL REGISTRY (code): timeout, idempotency key,
                  lookup before any retry -> backend -> save receipt
  -> ORCHESTRATOR: append events, update state, check stop conditions
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
| Record evidence | The run record (harness-components.md §2), exported to the trace store | — |
| Stop | Orchestrator's stop rules; the caller's cancel | "the model stopped calling tools" as the only exit |
| Stop everything | An operator, through kill flags the guard reads at every call (harness-components.md §4) | a redeploy, or a sentence in the system prompt |

ENTERPRISE frames the orchestrator as the accountable control plane: it sees every request and tool call, enforces autonomy rules, keeps the audit trail [ENTERPRISE ch7]. Vendors call this the harness. The 12-factor guide states the same split as owning your control flow: the model picks the next step, your code decides what runs, when to pause and when to stop [RELATED repo: 12-factor-agents/content/factor-08-own-your-control-flow.md].

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
5. Permission and risk tier (below). Where the tier needs an approval, it must be bound to a digest of exactly this tool and these arguments, unexpired and unused; the executor recomputes the digest and treats a mismatch as a new request (harness-components.md §3).
6. Guard passes again just before the tool call: no cancel, no kill flag, budget left (Budgets, below). The guard ran before the model call too.
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

SYSTEMS says its numbers are only examples; what it requires is that some budget exists before production, because more machines alone do not make an agent system scale, while bounded work does [SYSTEMS ch10].

### Where budgets bite

A budget that exists but is checked in the wrong place does not hold. Five rules:
- **Check before every model call and every tool call**, not once per turn. A breaker checked after the whole turn lets that turn's tool rounds run unchecked; the hardened teaching loop allows up to five per turn [DEFGUIDE repo: ch07/ch07_hardening_backbone.ipynb].
- **Keep the counters in the run's checkpointed state.** A tracker object outside state resets when the worker restarts [DEFGUIDE repo: ch06/ch06_A2A_MCP_Governed.ipynb].
- **Pause the clock during human waits.** Subtract the time spent waiting for a reviewer from the run's time budget, so a slow approver does not trip the agent's timeout [DEFGUIDE ch6].
- **Use a ladder and share it.** Warn at about 80% of any ceiling (stop creating new tasks, alert the operator) and stop at 100% (end the task, revoke its capabilities). The budget is shared across delegated work: a handoff to another agent cannot reset it. Detect repeats of the same worker, capability and input digest [AISEC repo: part8_multi-agent_harness_spec/safety-governance.md]. That specification's defaults (20 agent turns, 30 tool calls, one retry per task, 30 minutes) are one team's numbers [AISEC repo: part8_multi-agent_harness_spec/agents.yaml]; the ladder and the shared budget are what transfer.
- **One ledger for delegated work.** Sharing means one budget ledger per run in checkpointed state, not a number copied to each child: three parallel children each handed "what remains" can spend three times that. A child reserves a slice by conditional decrement before it spawns and before each of its calls, and returns what it did not use when it exits; cap the number of children and the depth. A reservation that fails ends the child with a budget reason. (This mechanism is this skill's; the specification above states only that the budget is shared.)
- **Leave headroom for the call you cannot price.** A pre-call check cannot know the call's cost, and accounting after each response overshoots by up to one response plus whatever running subagents spend before they stop (one vendor SDK documents this, as of 2026-10; framework-vocabulary-2026-10.md). Set the hard cap one maximum call below the real limit.
- **Under a vendor agent loop, split the budgets.** The SDK runs the loop, so the harness guards only what the SDK lets it intercept. A pre-tool hook can refuse a tool call before it runs, so tool-call budgets, kill flags and cancel can be checked before each tool call. Model calls, tokens and cost are usually counted only after each response, against the SDK's own turn and budget caps. Write down which budgets fall in which group. For the after-response group, set the SDK cap as a backstop one maximum call below the real limit. When the job runs several sessions from an outer loop of your own, guard the session count and the job's total spend there, before each session starts (`budget:sessions`, `budget:cost`). Confirm what the installed SDK version can intercept (framework-vocabulary-2026-10.md, "Where the guard runs").

When a budget is hit, PRODGUIDE's safe fallback applies: downgrade to draft-only, return the minimum useful output, and ask only the questions needed to continue [PRODGUIDE ch17 §Budget Guardrails and Context Discipline]. The status is `partial` with the budget named as the reason.

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
| `completed` | Goal met, output validated. A run whose deliverable is a draft or a pack ends `completed` once it is delivered to the person's queue or the receiving system, even though a person acts on it next |
| `partial` | Stopped early; states what was not done and why (budget, no progress, optional dependency down) |
| `awaiting_approval` | Paused at a short in-run gate; state checkpointed; this run resumes on the decision |
| `handed_off` | The run leaves a pending action (a proposal, a decision-record stub) that a person or another system decides on its own timeline, and a new run executes the decision; external reference stored; this run is over. Draft-only and safe mode also end here, with reason `draft_only` |
| `escalated` | Handed to a person with evidence, sources and the reason, because the run could not proceed |
| `failed` | Required check or dependency failed; nothing irreversible done after the failure |
| `cancelled` | Stopped by the caller's cancel or by the kill switch (abort); neither a task failure nor a success. The record says who stopped it and when; no call starts after the signal |

Partial output beats fake completeness [SYSTEMS ch16]. A common bug: the step cap or an error routes to the same summariser as success, and a truncated run produces a confident report. Carry the status through. Next to the status, record a stop reason from the fixed list in harness-tests.md §4, which ties each reason to its status and is the list agent-eval-designer's scorers read. Never write a reason as free text.

- Each optional step reports what it did: `called`, `not_needed` or `failed: <reason>`. A single flag that reads the same for "skipped" and "broke" makes a failure look like success.
- Every non-`completed` exit lands somewhere durable that a person or system works from: the approval queue, the receiving system for `handed_off`, a review queue for `escalated` and `partial`, a dead-letter queue for `failed` once retries are exhausted, the incident record for a `cancelled` run stopped by the kill switch. Each item carries the run ID, status, reason and a checkpoint reference. A log line alone is not a sink. Prove each sink with a test that forces that exit and checks the item arrives.

### Downstream decisions: hand off, don't hold the run

Use `awaiting_approval` only when the run itself holds the pending action and the decision comes back to it quickly, through the agent's own UI or queue, within minutes to hours. The channel does not decide the status: a chat button or an email link that leads to the harness's own approval endpoint within the request lifetime is `awaiting_approval` (the link itself only opens a read-only view; harness-components.md §3). `handed_off` is for a decision taken in another system of record, on that system's timeline, that comes back as a new event.

A paused run holds no worker. On `awaiting_approval` it checkpoints, releases its worker and its lease, and the decision enqueues a resume message that any worker can pick up. The wall clock stays paused for the whole wait.

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
| One tool keeps failing | Trip a breaker on that tool after N consecutive errors (about 3 is the 12-factor default) and stop retrying until a cooldown passes; hitting the threshold is a good point to escalate [RELATED repo: 12-factor-agents/content/factor-09-compact-errors.md]. A breaker covers one component; the kill switch covers the whole agent (harness-components.md §4) |
| A write timed out (outcome unknown) | Default sequence: look the idempotency key up, or read the target's state; if nothing is found, retry at most once with the same key; if the outcome is still unknown, end `escalated` with reason `outcome_unknown`. Never ask the model again, which may choose a different action [PRODGUIDE ch16 §The Production Spine: State, Retries, Approvals, and Control]. A backend with neither a key nor a lookup gets no automatic retry for that write: on a timeout the run ends `escalated`, or the write goes through a path that is safe to repeat (a person executes it, or the backend deduplicates). List that backend as a blocking assumption under "Confirm first" |
| Cancel signal or kill flag | Stop at the next safe point (the guard); end `cancelled`; a long tool receives the cancellation and cleans up (serving-and-deployment.md §4). A cancelled run never resumes, so settle any write in flight first: let the call return within its timeout or look the key up, record the receipt, and list any intent still without one on the exit event, so the item in the `cancelled` sink asks a person to reconcile it |
| Low confidence or blocked | Escalate to a person with sources and confidence attached [AGENTICAI ch8] |

Two correction loops, kept separate [DEFGUIDE ch5]: the **inner loop** re-asks the model to satisfy the same schema (fast, for model-shaped failures); the **outer loop** is the graph or orchestrator, with gates, retry routing and checkpoints (for timeouts, infrastructure failure, policy violations and side effects). Count retries in state so they stay bounded and visible.

**Idempotency.** A retried, resumed or replayed step must not repeat side effects. Every write carries an idempotency key derived from durable run state: run ID + action + target, or the business object (ticket + charge + action) when the same action could come from more than one run [SYSTEMS ch10] [SYSTEMS ch17] [PRODGUIDE ch16]. Not a step counter, which shifts when a resumed run re-plans, and not a hash of all arguments, which a rephrased field defeats; add the plan step only when a plan legitimately repeats an action on one target. Key semantics at the tool (lookup, receipts, backend behaviour on a reused key) are agent-tool-designer's. Two more places duplicates come from:
- **Triggers.** Webhooks and queues redeliver, especially when the handler is slow. Derive the run ID from the event (source ID + event ID) and deduplicate before starting, or the whole run, writes included, repeats. Do not run the loop inside a webhook handler; acknowledge, enqueue, process.
- **Different keys, same effect.** A key only catches repeats of itself. For money and other high-impact writes, also check the target's current state before acting (has this charge already been refunded?).

**Versioned outputs.** When a run regenerates an artifact (a new draft or recommendation after new documents arrive), write it as (case ID, artifact type, version), move a "current" pointer by upsert, and keep superseded versions for audit. Consumers act only on the current version; a decision made on an older version is rejected or re-confirmed.

## State and checkpoints

- **Execution state** (this run: fetched inputs, tried actions, findings, retry counts, status) is different from **memory** that outlives runs. Memory design is agent-context-designer's job.
- Keep the minimum the workflow needs, in a database, not process memory: runtime status (busy, waiting, error), task status, task state detailed enough to restart and diagnose [MESH ch5].
- Most systems are stateless per request with task state in an external store [SYSTEMS ch10].
- Checkpoint at step boundaries, keyed by run ID (thread ID per conversation branch), and around every side effect: **save the intent before it and the receipt after it**, and key the effect so whatever falls between the two writes is safe to repeat. A checkpoint per turn is too coarse when a turn holds several tool rounds: a crash mid-turn repeats calls that already happened [DEFGUIDE repo: ch07/ch07_hardening_backbone.ipynb]. A checkpoint holds intermediate tool results, the node where execution paused, pending routing, and the configuration to resume with the same model, prompt, tools and policy, so a late failure does not repay earlier expensive reasoning [DEFGUIDE ch5].
- **On resume, a final intent without a receipt** means "look the key up, then record the receipt or execute", never "ask the model again": the model may pick a different action with a different key.
- Pin configuration per run: load the policy, hash it, write policy and schema hashes and run ID into state, so a config change cannot alter a run in flight [DEFGUIDE ch5]. Peer agents are configuration too: a multi-step run calls versioned endpoints or aliases fixed at run start, or a deploy mid-run means later steps talk to different code.
- Human waits use the same mechanism: interrupt + checkpointer, resume when input arrives [BUILDAGENTIC ch2]. Pause in one step and execute in the next: on resume a framework node reruns from its start, so a write placed before the pause happens twice [DEFGUIDE ch2 §Designing Human-in-the-Loop Workflows].
- When new input arrives for a stored case, restart from the first phase whose inputs changed and reuse the checkpoints before it.

### When the state is a working tree

A coding agent keeps much of its state in files and version control rather than in a store the harness writes. Treat the repository as part of the checkpoint:
- Record a session-start and a session-end event with the commit hash at each point, so the run record says which tree each session saw and which it left.
- On resume, if the tree is dirty (changes left uncommitted when the last session died), snapshot it to a branch named after the run and session, then reset to the last recorded commit. Nothing is lost, and the next session starts from a known tree.
- Put the run ID and the step key in commit trailers (lines such as `Run-Id:` and `Step-Key:` at the end of the message), so "was this step already done?" is a lookup in the history, not a question for the model.
- Progress files and task lists in the tree are agent-writable. The harness decides completion with its own check (harness-components.md §1, row 19).

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

### Leases for long runs on a queue

Before designing the lease, write down four facts about the queue or task broker in use, from its documentation for the installed version:
1. When a message is acknowledged: on delivery (before the work) or after the work.
2. What a killed worker does to an in-flight message: lost, redelivered, or acknowledged as failed.
3. The redelivery timeout (a visibility timeout, an acknowledgement deadline) and what happens to a message still unacknowledged when it passes.
4. Where results are visible: to any reader, or only to the process that published the task.

Celery, a Python task queue, shows the common traps (documentation read 2026-10-20; confirm against your version):
- Early acknowledgement is its default, so a worker killed mid-task loses the task.
- Late acknowledgement alone does not redeliver everything. A task that fails or times out is still acknowledged by default, and so is the message of a task whose child process was killed, unless the worker-lost rejection setting is on (which can loop a poison task). Late acknowledgement also lets a task run more than once, so idempotency comes first.
- Its soft time limit raises an exception the task can catch, so a broad exception handler can swallow the limit and carry on; only the hard limit kills the process.
- On its Redis and SQS transports, a task not acknowledged within the visibility timeout (one hour by default on Redis) goes to another worker while the first may still be running it.
- Its RPC result backend hands a result over once, and only to the client that published the task, and keeps it in transient messages by default; a status endpoint in another process cannot read it.

Whatever the broker, a run that can outlast its redelivery timeout or lose its worker needs a lease and a sweeper, as below. A visibility-timeout queue hides a message for that timeout and then delivers it again. A run that lasts longer than that timeout is redelivered while its first worker is still busy. Dropping that redelivery is right only if something recovers the run when the busy worker dies; otherwise the run stays `running` for ever. Give each run a lease:
- The worker that starts or resumes a run takes the lease with a conditional write (owner, expiry), and renews it on a heartbeat. The same heartbeat extends the message's visibility.
- A redelivery for a run whose lease is live is acknowledged and dropped. A redelivery for a run whose lease has expired takes the lease and resumes from the last checkpoint.
- A sweeper runs on a schedule and re-enqueues every non-terminal run whose lease expired, so a run whose worker died after a redelivery was dropped still resumes, once. A run in `awaiting_approval` holds no lease and is not swept; its decision event resumes it.
- Set the lease expiry to a few heartbeat intervals, and the heartbeat well inside the redelivery timeout.

Tests: harness-tests.md, "Lease, redelivery" and "Lease, dead holder".

### Typed, versioned checkpoints

- Serialise through the state schema (a typed model), not ad hoc JSON. Enums, nested records and optional fields must round-trip; a string compared with an enum is silently false.
- Store a state-schema version with every checkpoint. On load, migrate known older versions and refuse unknown ones: end the run `failed` with the reason, or restart it deliberately from a recorded position. Never resume from state the code can't read.
- Test resume across processes: write in one process, kill it, load in a fresh one, compare field by field. A same-process test passes even with an in-memory store.
- When a run consumes a stream, record the last position it committed. On a restart without usable state, start from that position or the earliest retained one, never "latest" by default, which skips the backlog.

### Resume is not replay

Resume continues a run from its last checkpoint; retry repeats one call (idempotent, or verified first); rerun starts the job again; fork branches a new run from a past checkpoint. Replay re-runs a past run from its record, and it comes in two kinds [PRODGUIDE ch14 §Replay: The Fastest Way to Fix Agents]:
- **Experiment:** call the model again with the recorded input, change one component, compare plans, sources and previews. Framework replay from a checkpoint is this kind: nodes after the checkpoint run again, model and tool calls included, and may differ (LangGraph documentation, as of 2026-10).
- **Reproduction:** feed back the recorded model outputs and tool results from the event log instead of calling anything, to see exactly what happened.

Either way, side effects stay off: safe mode is the same mechanism as draft-only, and replays run under a credential with no write scope (harness-components.md §5). A home-made replay that re-runs the recorded tool calls is an experiment with side effects on, which is a defect to fix.

## Execution mode

| Choice | Pick |
|---|---|
| Sync request-response | Short, bounded work inside the UX latency budget |
| Async job | Long analysis, slow tools, approval waits. Needs job IDs, status, cancellation, correlation IDs, retries [SYSTEMS ch10]; the endpoint, streaming and disconnect policy are in serving-and-deployment.md |
| Long-running across many context windows | Keep progress outside the model: a progress file, a structured task list with each item marked failing until verified, git commits per unit; each session picks one unfinished item, verifies it end to end, records it (Anthropic, "Effective harnesses for long-running agents", 2025-11) |
| Triggered from an ordered stream | Events for one key must be handled in order (a partitioned log, change events per case). Needs bounded retries and a tested failure sink (below) |

### Ordered streams: poison events and failure sinks

In an ordered stream one failing event stops everything behind it in its partition, and the trigger retries it until the event expires while the backlog grows.
- Bound retries by count and by event age, and split a failing batch to isolate the bad event.
- Report the first failed event and stop processing the rest of the batch, so later events aren't handled before it; the source redelivers from there.
- Send the isolated event to a failure sink with enough to replay it. If the sink stores only pointers (partition and offset), keep the source's retention longer than your triage time.
- Attach the sink to the trigger that reads the stream. A sink configured for another invocation path never sees these failures, and a sink that never fires looks exactly like a healthy one. Prove the path with a test that injects a malformed event and checks it lands in the sink.
- Partition by the case or session whose events must stay in order (multi-agent.md, "Partitioning").

## Estimating at volume and reliability arithmetic

Both moved to the agent-architect skill's references/sizing.md. Tokens per path, peak load, concurrency, rate limits, caching, cost against the incumbent and chain reliability arithmetic decide how many steps and agents a design can afford, so they belong to the Design stage. Runtime capacity (workers, streams, per-client limits) is in serving-and-deployment.md; production tuning belongs to agent-ops-reviewer.

## Trace per step (minimum)

Assembled context reference, proposal, validation result, tool call and result, latency, tokens, model, prompt and policy versions, status. Persist structured plans, decisions with one-line reasons and stop reasons; raw reasoning text is optional and model-specific [SYSTEMS ch8]. These are events in the run record (harness-components.md §2). Trace design and dashboards: agent-ops-reviewer.

## Loop skeleton

A minimal shape to adapt. Planner, tool table (`args`, `writes`, `approval`, `target`, `call`, `lookup`), store, flags, cancel check and approval decision are injected; the run state was loaded by run ID from a store every worker shares. It checks cancel, the kill switch and the budget before every model and tool call, saves an intent before every write and a receipt after, looks the key up before (re)trying, records a preview instead of executing in draft-only or safe mode, and ends every path with a status.

```python
import hashlib, json

TERMINAL = {"completed", "partial", "handed_off", "escalated", "failed", "cancelled"}

class Stop(Exception):
    def __init__(self, status, reason):                # reason from harness-tests.md §4
        super().__init__(status)
        self.status, self.reason = status, reason

def guard(st, flags, cancelled, kind=None):
    """Before every model call and every tool call: kill switch, cancel, then the budget."""
    if flags.get("abort"):
        raise Stop("cancelled", "kill_switch")
    if cancelled():
        raise Stop("cancelled", "caller_cancel")
    if kind:
        st["used"][kind] += 1
        if st["used"][kind] > st["limits"][kind]:
            raise Stop("partial", f"budget:{kind}")
        if st["spent"] >= st["limits"]["usd"]:
            raise Stop("partial", "budget:cost")

def run(st, plan, tools, store, flags, cancelled, decision):
    """st was loaded by run ID from a store every worker shares. Returns the run's status."""
    if st.get("status") in TERMINAL:
        return st["status"]
    try:
        while True:
            last = st["events"][-1] if st["events"] else {}
            if last.get("type") == "intent":                  # crashed after the intent, before the receipt
                d = last
            elif last.get("type") == "awaiting_approval":
                verdict = decision(st["id"], last)             # checks digest of tool + args, expiry, nonce
                if verdict == "pending":
                    return "awaiting_approval"
                if verdict != "approved":
                    st["events"].append({"type": "denied", "key": last["key"], "verdict": verdict})
                    continue                                   # the model replans with the denial in view
                d = last
            else:
                guard(st, flags, cancelled, "model_calls")
                d = plan(st["events"])                        # {"final": x} or {"tool", "args", "reason"}
                st["spent"] += d.get("cost", 0.0)
                if "final" in d:
                    return end(st, store, "completed", d["final"])
                spec = tools.get(d.get("tool"))
                if not spec or set(d.get("args", {})) != spec["args"]:
                    st["events"].append({"type": "rejected", "allowed": sorted(tools)})
                    continue                                   # the re-ask costs a model call
                if any(e["type"] == "intent" and (e["tool"], e["args"]) == (d["tool"], d["args"])
                       for e in st["events"]):
                    return end(st, store, "partial", "repeated call", "no_progress")
                target = d["args"].get(spec.get("target"))     # the business object the tool acts on
                key = hashlib.sha256(json.dumps([st["id"], d["tool"], target]).encode()).hexdigest()
                d = {"type": "proposal", "tool": d["tool"], "args": d["args"], "key": key}
            guard(st, flags, cancelled)                        # abort wins over everything below
            spec = tools[d["tool"]]
            if spec["writes"] and (flags.get("draft_only") or st.get("safe_mode")):
                return end(st, store, "handed_off", {"preview": d}, "draft_only")  # execute nothing
            if d["type"] == "proposal" and spec["writes"] and spec["approval"]:
                record(st, store, "awaiting_approval", d)
                return "awaiting_approval"
            guard(st, flags, cancelled, "tool_calls")
            if d["type"] != "intent":
                d = record(st, store, "intent", d)             # intent is durable before the effect
            lookup = spec.get("lookup")                    # writes only: verify before (re)trying
            prior = lookup(d["key"]) if spec["writes"] else None
            result = prior if prior is not None else spec["call"](d["args"], d["key"])
            st["events"].append({"type": "receipt", "key": d["key"], "result": result})
            store.save(st)                                     # receipt is durable after it
    except Stop as s:
        return end(st, store, s.status, {"used": st["used"], "spent": st["spent"]}, s.reason)

def record(st, store, kind, d):
    ev = {"type": kind, "tool": d["tool"], "args": d["args"], "key": d["key"]}
    st["events"].append(ev)
    st["status"] = "awaiting_approval" if kind == "awaiting_approval" else "running"
    store.save(st)
    return ev

def end(st, store, status, payload, reason=None):
    st["events"].append({"type": "exit", "status": status, "stop_reason": reason, "payload": payload})
    st["status"], st["stop_reason"] = status, reason
    store.save(st)
    return status
```

Left out on purpose, add per design: schema validation of the final answer and of tool arguments beyond their names; the wall-clock budget (paused during approval waits); retries per failure class; the budget ladder's 80% warning; per-step trace fields; a per-tool circuit breaker; the approval record itself (`decision` must check the digest, expiry and nonce); conditional, versioned `store.save` when more than one process can hold a run (see "One writer per run"). harness-tests.md has the tests this skeleton was checked against.
