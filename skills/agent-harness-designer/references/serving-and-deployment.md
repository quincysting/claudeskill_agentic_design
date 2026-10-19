# Serving and deployment: the agent as a service

Citation keys such as [FASTGENAI ch5] point to the book list under Sources in SKILL.md.

This file covers the agent's own endpoint (designed under the API-contracts perspective, whose owner is agent-tool-designer), streaming, cancellation, long work behind HTTP and the three deployment shapes. Tool contracts the agent calls are agent-tool-designer's; hosting cost, autoscaling and dashboards are agent-ops-reviewer's.

## 1. Three layers

An async server trusts its handlers to do only non-blocking work: one blocking call inside an `async def` handler, a database query or model inference, stalls every other request [FASTGENAI ch5 §Blocking the Main Server]. Self-hosted inference is memory-bound and belongs in a separate model server that can batch [FASTGENAI ch5 §Externalizing Model Serving]; a single web framework process has a limited thread pool, the interpreter lock and no micro-batching [FASTGENAI ch2 §FastAPI Limitations]. So an agent service has three layers.

| Layer | Owns | Never |
|---|---|---|
| API | Authentication, request validation, run creation, status, the event stream, cancel and approval endpoints, per-client limits | Runs the loop or calls the model inside the request |
| Workers | The loop (control-loop.md), reading and writing the run record, tool calls | Hold a client request open |
| Model server or provider API | Inference, batching | Holds run state |

In-process background tasks share the event loop, give concurrency rather than parallelism and handle retries and exceptions poorly; a queue with a broker is the dependable version [FASTGENAI ch5 §Managing Long-Running AI Inference Tasks].

## 2. The agent's own endpoint

Treat the endpoint as a product with a contract, like any tool. A minimal resource design:

| Call | Does | Contract notes |
|---|---|---|
| `POST /runs` | Creates a run; returns its ID, status URL and events URL | Validate the body against a declared schema, and responses too [FASTGENAI ch4]; take an `Idempotency-Key` header (or a client-chosen run ID with PUT-create) so a retried create finds the same run [RESTCOOK ch5 §5.15]; return 202 Accepted for anything longer than a few seconds |
| `GET /runs/{id}` | Status resource: status, stop reason, progress, a refresh interval, links to the result or failure | Status values pending, working, completed, failed, plus the agent's own exits (`partial`, `awaiting_approval`, `handed_off`, `escalated`, `cancelled`) [RESTCOOK ch7 §7.15 Synchronous Reply for Incomplete Work with 202 Accepted] |
| `GET /runs/{id}/events` | Server-sent events streamed from the run record | Each event has a sequence number as its `id`; a client resumes with `Last-Event-ID` |
| `POST /runs/{id}/cancel` | Sets the cancel signal in run state; returns 202 | Idempotent; cancelling a finished run is a no-op that returns the final status |
| `POST /runs/{id}/approvals/{approval_id}` | Records a decision | Authenticated session with CSRF protection, by an approver entitled to approve this action; the body carries the decision and the digest the approver saw; the executor still recomputes it. A link sent to an approver opens a read-only `GET` view and never decides (harness-components.md §3) |

Rules for the contract:
- **Identity and access.** Run IDs are issued by the server and scoped to the principal; every read, cancel and approval checks that this caller may act on this run. Broken object-level authorization (another user's record by a changed ID) is one of the commonest API failures [APIARCH ch7].
- **One streaming entry point.** Expose one stream per run and route in the backend, so the client does not juggle state across endpoints [FASTGENAI ch6 §Designing APIs for Streaming].
- **Errors as problem details.** Use RFC 9457 problem details (it obsoletes RFC 7807; as of 2026-10), one `type` per failure category, never a stack trace.
- **Change without breaking.** Take nothing away, redefine nothing, make additions optional [RESTCOOK ch2] [RESTCOOK ch3 §3.11]. Because new status values will appear, clients treat an unknown status as "not finished, check again". The full versioning discipline is agent-tool-designer's.
- **Limits per client.** Rate limits stop abuse and share capacity; throttling slows a stream to what the client can consume or caps open WebSocket connections [FASTGENAI ch9 §API Rate Limiting and Throttling] [FASTGENAI ch9 §Throttling Real-Time Streams].

## 3. Streaming

| Run type | Transport | On client disconnect |
|---|---|---|
| Interactive turn, nobody else waits for it | SSE | Cancel the run and record `cancelled` with reason `caller_cancel`; saves cost |
| Interactive, client talks back mid-stream (voice, steering) | WebSocket | Cancel or pause, per product decision; record it |
| Background job or long run with a watcher | SSE from the record | Keep running; a reconnect with the last event ID resends the gap |
| Batch, nobody watching | None; status resource only | Not applicable |

SSE is plain HTTP, server to client, with automatic reconnection and event IDs for resuming; WebSocket is full duplex and more complex [FASTGENAI ch6 §Comparing Communication Mechanisms] [FASTGENAI ch6 §Server-Sent Events]. A client that disconnects mid-stream risks data loss or state drift [FASTGENAI ch6]. The book's WebSocket endpoint catches the disconnect, leaves the generation loop and releases the connection in a `finally` block [FASTGENAI repo: examples/ch06/6-15.py], and its database chapter stores a streamed answer only after the response [FASTGENAI ch7 §Storing Data When Working with Real Time Streams]. For agents, go one step further:

- **Stream a view of the record.** Workers append numbered events as they happen; the API forwards them. A disconnect loses nothing. The API also needs to learn that new events exist: a database notification, a pub/sub channel, or short polling of the record at a stated interval. Pick one and write down the delay it adds.
- **Make cancel-on-disconnect a policy per run type** (table above), never an accident of which coroutine died. The book does not state a rule; the choice is cost (interactive) against finished work (background).
- **Check before you release.** A whole-answer output check cannot run after tokens have left. One listing runs the input guardrail and generation concurrently and cancels generation when the guardrail fails [FASTGENAI repo: examples/ch09/9-3.py]; a variant returns the answer if generation wins the race and skips the verdict [FASTGENAI repo: examples/ch09/9-5.py]. Where an output check is required, buffer, or check each window before releasing it, and test with a slow guardrail and a fast model. Guardrail content is agent-threat-modeler's.

## 4. Cancellation

- The cancel signal lives in run state (or a store every worker reads), not only in the process that took the request, so whichever worker holds the run sees it.
- The guard checks it at safe points: before every model and tool call, and between stream chunks.
- A long tool receives cancellation as an exception. Ignore cancellations of unknown or finished requests, stop the operation, free its resources and clean up in a `finally` block [MCP ch6 §Request Cancellation]. The MCP mechanism changed with the 2026-07-28 revision (framework-vocabulary-2026-10.md); catch cancellation in the tool itself.
- A cancel during a write leaves the outcome unknown, and a cancelled run is never resumed, so nothing would look the key up later. Before recording `cancelled`, let the call in flight return within its timeout or look the key up, record the receipt, and list any intent still without one on the exit event; the item in the `cancelled` sink then asks a person to reconcile it (control-loop.md, failure table).
- Cooperative cancel keeps the record consistent but waits for the next safe point; killing the process is immediate and can leave a side effect half done. Cancel runs cooperatively; in an incident the abort level of the kill switch revokes credentials so a stuck call is harmless when it returns.

## 5. Long work behind HTTP

- A synchronous call is simpler until work outlasts the timeout: 30 seconds is common for HTTP, and streaming beats a long POST [DEFGUIDE ch7 §Hardening the Backbone]. A job costs a queue and a status endpoint and takes the timeout out of the design.
- Serverless functions have a hard per-invocation limit; FASTGENAI rules them out for serving a model, citing a 10-minute limit [FASTGENAI ch12 §Deploying to Serverless Functions]. Check your platform's current limit against the run's capped worst case.
- Give jobs and tasks a maximum run time after which the harness cancels them [RESTCOOK ch7 §7.6 Supporting RESTful Job Control Language].
- Shutdown: on a deploy or scale-in, stop taking new work, let in-flight steps finish or checkpoint them, then release the lease and make the message visible again (or re-enqueue the run) so another worker resumes it. If the worker dies instead, the lease expiry and the sweeper do the same (control-loop.md, "Leases for long runs on a queue").

## 6. Deployment shapes, chosen by trigger

On-demand calls map to a single service, external events to webhooks plus a queue, recurring cadence to scheduled runs; start with the shape the first use case needs and reuse the same spine everywhere [PRODGUIDE ch16].

| Shape | Use when | Must have | Fails when |
|---|---|---|---|
| Single service [PRODGUIDE ch16 §Pattern 1: Single Service Agent] | A caller waits; bounded work; moderate volume | Run ID and header at entry; draft and execute as different states with different enforcement, so the service can run draft-only for weeks; on approval, load state by run ID, check the approved payload against the stored preview, execute, record the receipt | Work regularly outlasts the request timeout |
| Event receiver + queue + workers [PRODGUIDE ch16 §Pattern 2: Event-Driven Agents with Webhooks and Queues] | Webhooks or business events | Receiver verifies the webhook, validates its shape, maps the event type to an allowed workflow, writes the header, enqueues and acknowledges; it never calls the model. Any model work the handler used to do (classifying the event, say) becomes the worker's first step. If the enqueue fails after the header is written, return 5xx so the sender retries and the conditional create re-enqueues a run that is still queued; or write the header and the message through an outbox in one transaction. Run ID derived from the event's source and ID, so a redelivered event finds its run. Workers with controlled concurrency, and a lease per run when runs outlast the queue's visibility timeout (control-loop.md, "Leases for long runs on a queue"); the queue as retry and backoff engine; a dead-letter path for manual review; at-least-once assumed | The loop runs inside the handler: the sender times out, redelivers, and the work runs twice |
| Scheduled run [PRODGUIDE ch16 §Pattern 3: Scheduled Agents for Operational Cadence] | Recurring work: triage, hygiene, report drafts | A run packet per run (inputs, rules applied, drafts, approvals needed, a short check against the SLA) as the review surface; incremental by default with a periodic full reconciliation | Silent drift nobody reviews |
| Foreground + background agents | Long work while a user waits for updates or wants to steer | A background worker on the run record; a foreground agent that keeps the user informed and routes asynchronous feedback to it [NG Agents Running in Parallel Get There Faster, 2025-08-27] | Both write the same state; give the run one writer |

Message brokers and event buses carry the events between these parts [BUILDAPPS ch8 §Message Brokers and Event Buses]; consume with groups and acknowledgements, never from a position kept in memory.

## 7. Durable workflow engines

An engine persists progress, so a crashed run resumes at its last completed activity without redoing earlier steps [BUILDAPPS ch8 §Orchestration and Workflow Engines]. Two rules decide whether it works for an agent:
- **Determinism.** Workflow code is replayed from history on recovery, so model and tool calls go in activities (steps), never in workflow code.
- **Grain.** One side effect per activity, keyed. In one book example a single activity wraps a model call, the tool calls and a second model call with three attempts, so a retry repeats every tool call inside it [BUILDAPPS repo: src/frameworks/langgraph_agents/supply_chain/temporal_supply_chain_multi_agent.py]. Engine steps are typically at-least-once: key the write inside them.

AWS options (Step Functions, Lambda durable functions) are in aws-implementation-notes.md.
