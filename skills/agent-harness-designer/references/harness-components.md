# Harness components: what a production harness owns

Citation keys such as [PRODGUIDE ch16] point to the book list under Sources in SKILL.md. A citation with `repo:` names a file in that book's companion repository, or in a related public repository when the key is RELATED (URLs under Sources).

The harness is all the code around the model: the loop, tool dispatch, run record and state, checkpoints, budgets and stops, approval pauses, streams and cancel signals, and the operator's switches. In SYSTEMS's split the model reasons and chooses, and the runtime supplies everything else: the loop, the tools, validation, state and the rules for stopping [SYSTEMS ch6]. Keep that spine consistent and models, prompts and tools can change without rewriting it [PRODGUIDE ch16]. Ng's definition is the shortest: the software that wraps around the model to implement the agentic system, letting the model drive the loop that decides what to do next [NG Agents on the Desktop, 2026-06-12]. His list of harness design decisions makes a good agenda for a design review: workflow or harness, what to chain and what to parallelise, code or model per step, fallbacks, the tool surface (MCP, command line, sandboxed execution), memory, context over long sessions, one agent or several [NG The AI Engineering Skills Map Part 2, 2026-08-21]. Whatever the answers, the minimum stop condition is a turn cap.

Control sits outside the loop: the caller's cancel, the operator's kill switch and safe-mode replay must not depend on the model cooperating or on a redeploy. Ng's reading of a 2026 incident, in which a lab's agent broke into another company's systems, names buggy sandboxing and monitoring as key to enabling it, and that is where he puts the fix [NG Who's Responsible for Irresponsible AI?, 2026-09-18].

Use this file as the audit checklist in review mode and as the coverage check for a new design.

## 1. Audit checklist

One row per component. "Pass when" is what the design or code must show; "red flag" is what to grep for; the test names refer to harness-tests.md.

| # | Component | Pass when | Red flag in code or config | Test |
|---|---|---|---|---|
| 1 | Loop and decision contract | One structured proposal per step; code validates and executes (control-loop.md) | Free-text parsing; the model's output reaches a function unvalidated | Forced stop status |
| 2 | Run record | Every run has an ID and an append-only record: header plus events (§2) [PRODGUIDE ch16] | Logs only; no run ID in tool calls; IDs defaulted (`"default"`) | Resume after crash |
| 3 | Durable state | State and checkpoints in a store every worker shares; run and thread IDs issued by the server per principal | In-memory checkpointer or a process dict in a multi-worker service; one JSON file per session | Kill while paused |
| 4 | Checkpoints and resume | Intent saved before every side effect, receipt after; schema version on every checkpoint; resume tested across processes | Checkpoint once per turn; untyped JSON; resume tested in one process | Resume after crash |
| 5 | Idempotent writes and retries | Every write keyed by run, action and target; lookup before any retry; capped retries ending in "needs human" [PRODGUIDE ch16 §The Production Spine: State, Retries, Approvals, and Control] | Retry on timeout without a lookup; random key generated per attempt | Duplicate delivery, faults at the edge |
| 6 | Budgets | Each budget has a number, is checked before every model and tool call, lives in checkpointed state, pauses during human waits, is shared across delegation (control-loop.md, "Where budgets bite") | Check after the turn; counters on an object outside state; caps left at framework defaults | Forced stop status |
| 7 | Stops and exit statuses | Every stop has a named status and reason; forced stops are never `completed`; `cancelled` exists; each non-completed status has a durable sink | Step cap, error and success share one summariser; "max steps reached" returned as an answer | Forced stop status |
| 8 | Approval pauses | Approval is stored state bound to a digest of the exact action and arguments, an expiry and a nonce; pause and side effect in separate steps (§3) | Executes whatever call is on the thread after "approved"; write placed before the interrupt | Approval digest, kill while paused |
| 9 | Kill switch | Draft-only and abort flags read by the guard at every call, flipped without a redeploy, drilled; abort revokes credentials and cancels queued and running work (§4) | A redeploy or a prompt sentence is the only way to stop; flag read once at startup | Kill switch |
| 10 | Cancellation | Callers can cancel a run; the signal lives in run state so any worker sees it; long tools receive it and clean up; status `cancelled` | Cancel only kills a coroutine; tool has no cleanup path | Cancel |
| 11 | Streaming | Numbered events streamed from the record; disconnect policy set per run type; reconnect resends from the last event ID; output checks finish before text is released (serving-and-deployment.md §3) | Generator tied to the request; cancel-on-disconnect by accident; tokens released before the output check | Disconnect |
| 12 | Serving layer | No inference or blocking I/O on the request event loop; API, workers and model server separated; per-client limits; drain or checkpoint on shutdown | `graph.invoke` or a sync SDK call inside `async def`; the loop runs in the request handler | Faults at the edge |
| 13 | Deployment shape | Trigger named (request, event, schedule); event receivers never call the model, deduplicate by event ID, feed a queue with a dead-letter path (serving-and-deployment.md §6) | Loop runs inside the webhook handler; no dead-letter path | Duplicate delivery |
| 14 | Replay | Any past run can be replayed in safe mode; the team knows experiment from reproduction (§5) | Replay calls tools with side effects on; inputs not recorded | Safe-mode replay |
| 15 | Framework boundary | You can name what the framework owns, read the exact prompt and every transition, set every budget, swap the provider (framework-vocabulary-2026-10.md) | Nobody can say where state is stored or which caps are set | Harness bake-off |
| 16 | Harness tests | Resume, stop, budget, cancel, kill and duplicate-delivery tests run in CI against an out-of-process store (harness-tests.md) | Only end-to-end "it answered" tests | n/a |
| 17 | Trace hooks | Every event carries run ID, step, versions, tokens, cost, latency, status; tracing backend and dashboards are agent-ops-reviewer's | Trace IDs unrelated to run IDs | n/a |
| 18 | Containment | Every process the agent can drive (shell, browser, MCP servers, hooks, child agents) sits inside a named boundary; no path the agent can write is later loaded by the runtime or a privileged component as configuration, instructions or code (§7, "Containment inventory") | A sandbox on the shell tool only, with a browser or MCP server spawned beside it; the agent's working directory is also where the runtime reads settings, hooks or prompt files | Containment |
| 19 | Who decides done | Completion is decided by a check the harness runs and the agent cannot write (tests the harness executes, a state the backend reports) | Completion counted from a file or field the agent can write; "all items pass" read from the agent's own notes or task list | Completion claim |

**Declared is not enforced.** A status value or a `requires_approval` label does nothing unless the harness acts on it. One open-source toolkit labels shell tools as needing approval, and nothing blocks them unless a policy is passed in [RELATED repo: aisuite/aisuite/toolkits/shell.py]; the same library declares a `max_turns_exceeded` status and returns an exhausted run like a finished one [RELATED repo: aisuite/aisuite/agents/types.py] [RELATED repo: aisuite/aisuite/client.py]. Refuse to start when a tool needs approval and no approval policy is wired, and test every label by forcing it.

## 2. Run record

The run record is the spine: resume, audit, replay, evaluation and incident review all read it [PRODGUIDE ch16 §The Production Spine: State, Retries, Approvals, and Control].

**Header (written once, at run start).** Run ID; principal (who or what started it); trigger (request, event source and ID, schedule); timestamp; agent version; prompt, policy and tool-schema versions or hashes; model and provider; permission tier; input reference (not the raw input when it holds personal data); budget limits; state-schema version [PRODGUIDE ch16].

**What a run tracks while it works.** The goal in one line, the constraints and permissions for this run, the plan, an execution record of what was attempted and what happened, and open questions, so that "unknown" has a place to live instead of being filled with confident text [PRODGUIDE ch2 §State, What the Agent Tracks During a Run].

**Event vocabulary.** Keep the record as an append-only log of typed events; derive the typed state the gate reads from it, or write both in one transaction. The model reads a serialised thread, the gate reads typed fields, and both views are needed [RELATED repo: 12-factor-agents/content/factor-05-unify-execution-state.md] [PRODGUIDE ch16].

| Event | Carries | Written |
|---|---|---|
| `request` | The task and input reference | At run start, after the header |
| `plan` | Structured plan or the next proposal, with a one-line reason | Each model step |
| `sources` | References to retrieved documents or records | When retrieval runs |
| `rejected` | Why a proposal failed validation | When the gate rejects |
| `preview` | The exact action and arguments that would run | Draft-only, safe mode, before an approval |
| `awaiting_approval` | Action, arguments, digest, expiry, approval ID | When a tier needs approval |
| `approval` | Decision, approver identity, digest signed, time | When the decision arrives |
| `denied` | Rejection or expiry, with the approver's comment | So the model can replan |
| `intent` | Tool, arguments, idempotency key | Before every side effect, saved durably |
| `receipt` | Key, result or external reference | After every side effect, saved durably |
| `error` | Category (agent-fixable or infrastructure), attempt count | On every failed call |
| `budget` | Counter values, ladder warnings | When a threshold is crossed |
| `cancel` / `kill` | Who, when, which level | When the signal is seen |
| `exit` | Status, stop reason, payload or what was not done | Last event of every run |

**Typed state (the projection).** Status, current step, counters (`used`, `spent`, active time), pending approval, last stream position, last event sequence number. This is what the guard and gate read.

**Run record and a framework checkpointer.** With a framework that has its own checkpointer, keep two stores with two jobs. The checkpointer holds the typed state the guard reads (counters, pending approval, cancel flag) and is what resumes the run. The record header and events are a separate append-only table, written in the same transaction as the state change or through an outbox, so neither moves without the other. Status and event endpoints read the record, never the checkpointer.

**Pause and resume.** Pausing returns the thread; resuming loads it, appends the human's answer and re-enters the loop [RELATED repo: 12-factor-agents/packages/create-12-factor-agent/template/src/server.ts]. Because state lives outside the process, any worker can take the next step: the loop as a stateless reducer over the record [RELATED repo: 12-factor-agents/content/factor-12-stateless-reducer.md]. While it waits for a person the run holds no worker and no lease: it checkpoints, releases both, and the decision enqueues a resume message; the wall clock stays paused (control-loop.md, "Downstream decisions").

**Retention.** Redact or reference sensitive fields; set a retention period per field class [PRODGUIDE ch16]. Keep enough to replay: raw input or a reference, prompt versions, permission tiers, retrieved sources [PRODGUIDE ch14 §Replay: The Fastest Way to Fix Agents].

## 3. Approval record and binding

An approval ID stops a double execution, not a changed one. Bind each approval to the task, capability, target, a digest of the parameters, an expiry and a single-use nonce; any change, extra retry or expired token needs a new approval [AISEC repo: part8_multi-agent_harness_spec/safety-governance.md]. That specification defaults to 15 minutes and one invocation per approval [AISEC repo: part8_multi-agent_harness_spec/agents.yaml]. PRODGUIDE's single-service pattern checks that the approved payload matches the stored preview before executing [PRODGUIDE ch16 §Pattern 1: Single Service Agent]; the 12-factor template, by contrast, executes whatever arguments sit on the thread's last event [RELATED repo: 12-factor-agents/packages/create-12-factor-agent/template/src/server.ts].

Fields: approval ID, run ID, action, arguments, digest, requested at, expires at, nonce, state (`pending`, `approved`, `rejected`, `expired`, `escalated`, `edited`), approver identity, decided at, comment.

Every component that computes or checks a digest uses one canonical form: JSON with sorted keys, compact separators (`,` and `:`), non-ASCII characters kept as they are, encoded as UTF-8. With a library's default separators, two implementations can compute different digests for the same arguments. agent-threat-modeler's approval rules point here.

```python
import hashlib, json, time

def digest(action, args):
    canonical = json.dumps([action, args], sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

def may_execute(appr, action, args, now=None):
    """The executor's check, run on resume immediately before the call."""
    return (appr["state"] == "approved" and not appr.get("used")
            and (now or time.time()) < appr["expires_at"]
            and appr["digest"] == digest(action, args))
```

Two lifetimes, not one: the request's lifetime is how long a person has to decide (hours for an overnight queue, a product choice); the approval's lifetime is how long the decision stays usable before execution, and it should be short, like the specification's 15 minutes. Rules: silence never means yes (an expired request does nothing); an edit closes this approval as `edited` and opens a new one for the edited arguments, which goes back through the hard limits (agent-threat-modeler uses the same rule); mark the approval used in the same write as the intent. What the approver sees, who may approve and the autonomy policy belong to agent-threat-modeler.

**Approvals delivered by a link.** Mail scanners, link previews and browser prefetch open links with nobody reading them, and a forwarded email hands the link to someone else. So a link or a GET that approves or executes is a Critical defect in itself (§8), whatever expiry it carries.
- The link opens a read-only view of the stored approval: the exact action and arguments, the digest, the expiry. Opening it decides nothing.
- The decision is a POST from an authenticated session, with CSRF protection, by an approver entitled to approve this action, and it carries the digest the approver saw. The executor still recomputes the digest. The recorded approver is the authenticated identity.
- The link carries no authority. A token in it only says which approval to show, so forwarding it transfers nothing.
- Retiring executing links already sent, in this order: change the old endpoint so it can only show the read-only view (or return 410 Gone); mark every approval the old links point at `expired`; rotate the key that signed the link tokens; reissue, through the new flow, the requests that are still needed. Then search the audit trail for decisions that arrived without an authenticated session and review those actions as unapproved.
- Tests: harness-tests.md, "Approval link GET" and "Link holder without a session".

Who may approve which action is agent-threat-modeler's (its human-oversight.md §3 states the same link rules from the approver's side).

## 4. Kill switch: the full contract

PRODGUIDE's kill switch is a configuration setting: execution stops, but the agent can still plan and draft; in limited beta, flip it, investigate by run ID and resume once the root cause is understood [PRODGUIDE ch16 §The Production Spine: State, Retries, Approvals, and Control] [PRODGUIDE ch18 §Stage 2: Limited Beta, Controlled Execution, Monitor Everything]. AGENTICAI adds an emergency shutdown procedure and a human override that pauses any change the agent started [AGENTICAI ch11 §When Agents Go Rogue: Building Essential Safeguards for AI Systems]. Keep two levels.

| Level | Stops | Keeps | Flip when | Restart |
|---|---|---|---|---|
| Draft-only (routine) | Every side-effecting call; the guard records a preview instead | Reads, planning, drafting, previews | An anomaly, a deploy under watch, an investigation, the first weeks of a new workflow | Flip back once the cause is understood |
| Abort (incident) | Everything: revoke capability and approval tokens, cancel queued and running work, deny new agent tasks and tool calls | An immutable audit snapshot | Scope mismatch, unexpected egress, loss of the audit path, injected text that changes policy, budget runaway, an operator's call [AISEC repo: part8_multi-agent_harness_spec/safety-governance.md] | Human review and a fresh start approval |

Mechanics:
- Both flags are harness state read by the guard before every call, never prompt text: an agent told to confirm before deleting emails deleted more than two hundred, most likely after the instruction fell out of its context [ENTERPRISE ch7 §Mapping the Risk Landscape].
- Flipping must not need a redeploy, and must work from wherever the operator is.
- **Propagation time.** The quality bar asks how long a flip takes to reach running workers. Bound it one of two ways: workers read the flags through a cache with a TTL of a few seconds, so no new call starts later than one TTL after the flip; or the flag store pushes changes to the workers. A call already in flight finishes unless abort has revoked its credentials. Write the bound in the runbook and measure it in every drill.
- **Draft-only has two meanings.** It is also a permission tier per action (agent-threat-modeler). The kill switch's draft-only level moves every action to the draft-only tier while it is on; each action's own tier applies again when the switch is flipped back.
- Revoking credentials is what makes a stuck in-flight call harmless; cooperative cancel alone waits for the next safe point.
- Scope: per agent, per tenant and global. Draft-only and safe-mode replay share one mechanism, so build it once.
- Drill on a schedule: flip draft-only mid-run in staging, then abort, and check the record (harness-tests.md).

A per-component circuit breaker (control-loop.md, failure table) is not a kill switch: it pauses one component automatically; the switch stops the agent.

## 5. Safe-mode replay

Replay needs the captured input and state (raw input or a reference, prompt versions, permission tiers, retrieved sources) and controlled side effects: tool calls simulated, drafts sent to a sandbox, or execution disabled while payload previews are still produced. Load a failed run, replay it, compare plan, sources and previews with the original, change one component at a time; replay over many cases is also the evidence for widening autonomy [PRODGUIDE ch14 §Replay: The Fastest Way to Fix Agents].

| Kind | Model and tools | Use for |
|---|---|---|
| Experiment | Called again, side effects off | Testing a prompt, model or policy change against real cases |
| Reproduction | Recorded outputs fed back from the event log; nothing called | Seeing exactly what happened; debugging the harness itself |

Framework replay from a checkpoint is an experiment, not a reproduction: steps after the checkpoint run again and may differ (framework-vocabulary-2026-10.md).

Replays run under a credential with no write scope, so a bug in the guard cannot write. In an experiment, read tools may run live; the replay's record says which ones ran and what they returned. A home-made replay that re-runs the recorded tool calls is an experiment with side effects on: a defect to fix, not a replay mode.

## 6. Compensation

Jobs whose steps can be undone get a revert per step keyed by the request ID, reverted in reverse order when the job fails or is cancelled; jobs and tasks get a maximum run time after which the engine cancels and reverts [RESTCOOK ch7 §7.1 Designing Workflow-Compliant Services] [RESTCOOK ch7 §7.6 Supporting RESTful Job Control Language]. A related prototype shows two limits of naive compensation: it "reverts" irreversible steps too, and only logs a revert that fails [RELATED repo: apis-and-agents/job-control/index.js]. Put irreversible steps last and behind approval; a failed revert escalates like an incident; when nothing automatic works, alert a named person with the job's description, progress and state [RESTCOOK ch7 §7.18 Calling for Help]. Whether a tool is reversible is a contract field (agent-tool-designer). Whether a cancel also reverts steps that completed correctly (a label that was right, say) is a product decision per run type; write it down.

## 7. The tutorial harness shipped to production

The commonest harness failure is good teaching code deployed as is. None of the seven companion repositories of the original books has an idempotency key, a kill switch or draft-only mode, side-effect-free replay, schema-versioned checkpoints or cancel-on-disconnect, and apart from one Temporal example their durable state is a JSON file. Each row below is a finding to raise when you see the pattern; the repositories were read, not run.

| What the tutorial does | Why it breaks in production | Fix | Evidence |
|---|---|---|---|
| Keeps the checkpointer in memory in a multi-worker service, while printing that conversations are persisted | Each worker has its own memory; a restart loses everything; a follow-up on another worker finds nothing | A durable checkpointer every worker shares | [BUILDAGENTIC repo: sdr_multi_agent/flask_app/agent_builder.py] [BUILDAGENTIC repo: sdr_multi_agent/flask_app/app.py] |
| Defaults the thread ID to `"default"` | Every caller that omits an ID shares one conversation | Server-issued IDs per principal; reject a missing ID | [BUILDAGENTIC repo: sdr_multi_agent/flask_app/agent_builder.py] |
| Declares an exhausted-run status but never sets it | A truncated run is reported, scored and billed as a success | Set it; test it | [RELATED repo: aisuite/aisuite/agents/types.py] [RELATED repo: aisuite/aisuite/client.py] |
| Routes step cap, completion and errors to one summariser; records step errors as results | A failed run produces a confident report | Distinct exits and statuses | [BUILDAGENTIC repo: deep_research/deep_research_graph.py] |
| Returns "Max steps reached without completion." as an ordinary answer | Callers and evals cannot tell a stop from an answer | Status `partial` with reason `max_steps` | [ILLUSTRATED repo: src/illustrated_agents/agent.py] |
| Runs the inner tool loop as `while True` | One misbehaving model or tool spins until something external kills it | Budgets checked before every call | [MCP repo: ch3/12_make_tool_calls/agent.py] [RELATED repo: 12-factor-agents/packages/create-12-factor-agent/template/src/agent.ts] |
| Checks the cost and turn breaker after the whole turn; checkpoints per turn | Up to five tool rounds run unchecked; a crash mid-turn repeats tool calls | Guard before every call; intent and receipt around every write | [DEFGUIDE repo: ch07/ch07_hardening_backbone.ipynb] |
| Loads the thread from its store without awaiting the result | Resume after a restart fails at the first approval | Cross-process kill-while-paused test | [RELATED repo: 12-factor-agents/packages/create-12-factor-agent/template/src/server.ts] |
| Retries a workflow activity that wraps model and tool calls; reads a stream from position zero held in memory, with no consumer group or acknowledgement | Retries repeat side effects; a restart reprocesses every task | One side effect per activity, keyed; consumer groups with ack and dead letter | [BUILDAPPS repo: src/frameworks/langgraph_agents/supply_chain/temporal_supply_chain_multi_agent.py] [BUILDAPPS repo: src/frameworks/langgraph_agents/supply_chain/redis_streams_multi_agent_supply_chain.py] |

None of this makes the repositories bad teaching code. It means the step from prototype to service is a harness project with its own checklist and its own tests.

**Containment inventory.** A coding or browsing agent drives more processes than its shell tool, and reference code often sandboxes only the shell. In review mode, list each process and the boundary that contains it:

| Process the agent can drive | Usual boundary | Gap to look for |
|---|---|---|
| Shell commands | OS sandbox, container, command allowlist | An allowlist that lets interpreters or agent-written scripts run by name is a convenience, not a control (agent-threat-modeler) |
| A browser or other MCP server the SDK spawns | Its own process, often outside the shell sandbox | Network egress and reach into internal networks that neither the allowlist nor the shell sandbox governs |
| Hooks and plugins | Run by the runtime, with the runtime's rights | Hook definitions in files the agent can write |
| Child agents and subprocesses | Whatever the parent passes on | Credentials and scopes inherited by default |

Then list every path the agent can write that something later loads: project settings, hook definitions, instruction or prompt files, test and scorer files (harness-tests.md §1), and the task list the harness reads progress from (§1, row 19). Whether a runtime loads project-level settings from its working directory by default depends on the SDK and its version, and has changed between releases of at least one vendor SDK (as of 2026-10). Confirm against the pinned version and tag the finding inferred until then. Each uncontained process or loaded writable path is a finding, rated by what it reaches. One container per run with no push or write credentials bounds most of the processes at once; writable paths the runtime loads still need their own check.

## 8. Severity for review findings

| Severity | Harness examples |
|---|---|
| Critical | A write can run twice after a retry, resume or redelivered event; an approval executes changed arguments; an approval link or GET that approves or executes; no way to stop side effects without a redeploy; one caller can read or cancel another's runs; a run can be left `running` for ever with nothing to recover it (no lease expiry or sweeper); no terminal condition or no spend cap on an unattended job or on shared infrastructure |
| High | Forced stops reported as `completed`; a failure reported as success (an exception caught and returned as a successful task or an HTTP 200); no terminal condition or no spend cap on an attended run; budgets checked per turn or reset on restart; in-memory state behind several workers; blocking inference on the event loop; loop inside a webhook handler; a debug or development server reachable from the network; a credential printed to logs, or a hard-coded fallback secret (these last two also go to agent-threat-modeler) |
| Medium | No safe-mode replay; disconnect policy accidental; checkpoints without a schema version; no per-client limits |
| Low | Event names inconsistent; stop reasons free text instead of a fixed list |

**Evidence labels, in every review.** Tag each fact a finding rests on: **seen** (read in code, config or a document supplied for this review; cite file:line or section), **observed** (logs, traces, metrics or a test run), **told** (an owner or user said so; not checked), **inferred** (follows from seen code plus a library, platform or language behaviour not checked here; name the behaviour and the version it depends on), **assumed** (no evidence). Severity follows the consequence if an inferred or assumed fact holds: write it as "Critical (inferred)" or "High (assumed)" and put the fact under "Confirm first". Never downgrade a finding because its trigger is inferred. The sibling review skills use the same five labels.

**A control that can be bypassed is not a boundary.** When the only thing between the agent and an action is a control the agent can get around (a rule in the prompt, an allowlist that runs interpreters or scripts the agent wrote), rate the finding as if no control were there, by what the bypass reaches.

**Entry points.** Map which entry points real callers use: the UI's calls, scheduled jobs, documented routes. A finding on a path no current caller reaches keeps its severity by consequence and says so ("reached only by direct API callers"); removing the path is one of its fixes. A fix that removes or changes an entry point names every caller that must move in the same change, such as a UI that must switch to the asynchronous route.

**Missing components.** When a finding depends on a component that is absent from the input (an empty submodule, a service the code calls but the folder does not hold), keep the severity by consequence, tag the finding "depends on missing <component>", and put that component first under "Confirm first".

**Count each harm once.** When a finding's worst consequence (a duplicate send, say) is already its own finding, rate the second finding by what it adds.
