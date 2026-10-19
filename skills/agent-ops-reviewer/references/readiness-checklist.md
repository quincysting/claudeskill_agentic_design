# Production-readiness checklist (scored)

Score each item **0** (absent or only planned), **1** (partial, or present without evidence it works) or **2** (in place, with evidence: file and line, config, dashboard, runbook, test). Mark **N/A** with a reason when an item cannot apply (for example, no self-hosted models), and leave it out of the percentages. A framework default nobody chose (a default recursion limit, a default retry policy) scores at most 1. Score on evidence only; "we plan to" is 0, and a setting that exists but is never exercised (an untested fallback) is 1.

**Evidence tags.** Tag every score, and every fact a finding rests on, with one of five labels (the same five in every review skill):
- **seen**: read in code, config or a document supplied for this review; cite file:line or the section.
- **observed**: shown by logs, traces, metrics, a dashboard or a test run.
- **told**: stated by an owner or user and not checked. Scores at most 1.
- **inferred**: follows from seen code plus a library, platform or language behaviour not checked here (a client library's default timeout, a container runtime's default bind address). Name the behaviour and the version it depends on. An inferred fact can justify a 0, never a score above 1.
- **assumed**: no evidence (no access and no description). Scores 0.

An assumed 0 means "go and look"; a seen or observed 0 means "build it". Keep the two apart in the review. Severity follows the consequence if an inferred or assumed fact holds, and every inferred or assumed fact also goes under "Confirm first" with what would settle it. The "told: at most 1" cap is for claims that something exists. An owner's explicit statement that something is absent ("we don't trace tool calls", "stopping it needs a redeploy") scores 0 and counts like a seen 0: it makes "Not ready" firm. Numbers in the cost model keep their own input tags, measured or assumed.

**N/A.** J4 is N/A whenever every model runs on a managed API; that is the normal case, so leave it out of the denominator rather than scoring 0. For G1, list every tool and its side effect first, and ask when you cannot see the tool code. Search, fetch and query tools are reads; anything that sends, writes, books, pays, deletes or changes state outside the agent is a write. No write tools (common for research and Q&A agents) makes G1 and G7 N/A. Write tools but no shadow or replay path yet makes G1 N/A, with the recorder made a precondition of the fix that introduces shadow. Side effects unknown means G1 is assumed, not N/A.

**Stubs and missing components.** When a tool is a stub (it returns a fixed value, prints, or is a placeholder) or a component the code refers to is absent, say so in the review summary. Ask what each stub becomes; with no answer, take the intended wiring from docstrings or the README, state it as an assumption, and review under it. Score the write-dependent items (G1, G5, G7, Run gate rows 2, 3 and 5) under that assumption, and name the items and the verdict that change if the tools only read. A stub that reports a success it did not achieve (an order "placed" that went nowhere) is itself a finding. A feature with no real backend gets "remove it" among its fix options, not only a redesign.

**B** marks a blocker. Blockers are the failures that burn money without limit, leak data, make incidents undiagnosable, let a release act twice, or leave a running incident unstoppable short of a redeploy.

## Verdict rule

- **Not ready**: any blocker scores 0, or the total is below 50% of applicable points.
- **Ready with conditions**: every blocker scores at least 1 and the total is at least 50%. The conditions are every blocker at 1 plus all P0 fixes, each with an owner and a date before launch or scale-up.
- **Ready**: every blocker scores 2, the total is at least 75%, no area is below 50%, the Run gate passes (next section), and, when any tool writes, a written staged-rollout plan exists (shadow with stubbed writes, then a canary with rollback triggers; G1, G2).

Percent = points / (2 × applicable items). Report per area and overall.

**Missing evidence.**
- **Provisional**: put "Provisional" in front of the verdict when any blocker is assumed or more than a quarter of applicable items are assumed. Report a floor (assumed items at 0) and a ceiling (assumed items at 2) and the verdict each one gives; the gap shows how far the verdict rests on evidence nobody has seen. A blocker *seen* at 0, or stated absent by its owner, makes "Not ready" firm, whatever else is unverified.
- **Code-only review** (a repository with no logs, traces, dashboards or owners to ask): say so in the review header. Runtime facts (whether an endpoint is reachable, which defaults are in effect, whether a trace arrives) are inferred and go under "Confirm first". Items code cannot show are marked **not assessable from code**: D (unless alert rules are in the repo), E (unless scorer or sampler code is), F2 to F7 (unless CI config is), G2, G3, G6, H, I1, I6 to I9, J1, J3 and J5 (unless the repo holds the config or document that shows them). Leave them out of the denominator, compute the floor and ceiling over the assessable items only, and list the rest in the discovery plan instead of scoring them assumed at 0. A blocker seen at 0 keeps "Not ready" firm. "Ready" is never given from code alone. When the folder holds several variants of one system (a demo and a production build, single- and multi-agent versions, alternative backends), name the one you review as the shipping candidate, score only that one, and list the other variants' defects separately.
- **Too speculative to score**: when the run map is assumed (you have not seen the loop, caps and tool code or config), or more than half of the blockers or half of the applicable items are assumed, do not hand back item-by-item scores as findings. Deliver a discovery plan (the evidence per blocker: one production trace followed end to end, loop and retry config, exporter and masking config, prompt and tool registry, tool router per mode; who holds each and how long it takes) plus the provisional verdict from what you know. Rescore when the evidence arrives.

**Lite mode** (internal pilot, under about 100 requests a day, no write tools): score only the blockers plus B2, C2, F2, I1 and I2, report Run gate rows 1, 4 and 6 only, and say so in the review.

**No-loop, no-tool profile** (one model call per request and no tools, such as a chat or Q&A endpoint whose retrieval runs in code). Score it in full, with three items read for this shape:
- A1 becomes caps on input (messages and characters or tokens of the forwarded history, size of the retrieved context) and on output, plus handling of the stop reason: a length stop reaches the user as a truncated answer, never as a server error or a silent cut.
- A2 becomes a per-client fuse (requests and tokens per client or session per window), since there is no loop to stop.
- G5 becomes an off switch that takes the model call out and shows a fallback (a human channel or a static message) without a redeploy.

G1, G7, G8, Run gate rows 2 and 5, A4's idempotency part (its retry part still applies) and A8 are N/A; so are B5's tool fields, and K6 and K7 when the team runs no tool server. J6's problem-details format and K4's signing and disclosure contact are scored but ranked P2 unless the review finds a concrete exposure through them.

## Run gate

This is the Run stage gate in agent-architect's lifecycle map (lifecycle-map.md), which lays out the stages, the perspectives with their owners and the gate at the end of each stage. Run it before each rollout stage (internal, limited beta, monitored scale) and report it next to the verdict, each row marked pass or fail. It has three parts: PRODGUIDE's six-item readiness gate, kept short because short gates get used [PRODGUIDE ch16 §The Production Spine: State, Retries, Approvals, and Control]; monitoring that is live; and written conditions for widening autonomy. A row passes when every item it maps to scores 2, seen or observed. The runtime rows are designed and tested in **agent-harness-designer**; this review checks that they exist and work.

| Gate row | Passes when | Items | Designed in |
|---|---|---|---|
| 1. Run record | Every run has an ID and an append-only record of prompt and policy versions, plan, source references, payload previews, approvals, receipts, errors and exit status | B8 | agent-harness-designer |
| 2. Idempotent side effects | Every side-effecting call carries an idempotency key, and a timeout triggers a lookup before any retry, so reruns create no duplicates | A4 | agent-harness-designer (retries); agent-tool-designer (keys, receipts) |
| 3. Tiers, approval, kill switch | Permission tiers are enforced per tool action, irreversible actions need an approval bound to the exact action, and a kill switch forces draft-only at once | G5, G7 | agent-threat-modeler (tiers, approvals); agent-harness-designer (switch) |
| 4. Redaction and retention | State and logs hold sensitive fields redacted or as references; retention is set per record and deletion runs | C1, C4 | this skill (observability.md §3) |
| 5. Safe-mode replay | A past run replays from its record with side effects off and reproduces the plan and payload previews | G1, G8 | agent-harness-designer |
| 6. KPIs and reruns | A small KPI set tied to the SLA is on a dashboard, and the suite reruns after every meaningful change | I9, F3 | this skill; the suite: agent-eval-designer |
| Monitoring live | Windowed alerts with sample floors route to a named owner, and one trace has been followed end to end in the backend | B1, D3, D7 | this skill |
| Autonomy expansion | Each move to more autonomy has written conditions: a sustained approval rate, written rules for the new actions and a rollback plan. PLAYBOOK's figures differ by chapter: 80% over 30 to 60 days [PLAYBOOK ch2], 85% over 30 days and 90% over 60 days [PLAYBOOK ch4] | not scored | agent-threat-modeler (human oversight) |

Row 2 is N/A when no tool writes. Otherwise a row whose mapped item is N/A is judged on its remaining applicable items, and a row with every item N/A is N/A: with no write tools, row 3 comes down to G5 and row 5 to G8. With stub tools, judge rows 2, 3 and 5 under the stated wiring assumption ("Stubs and missing components", above). The autonomy row passes when the conditions are written and owned; whether they are met at a given moment is agent-threat-modeler's call, not this review's.

## A. Bounded execution and resilience

| ID | Item | Evidence to look for |
|---|---|---|
| A1 **B** | Per-run caps on tokens, model calls, tool calls, retries and plan steps per task type, enforced by the runtime before every call; a forced stop returns a partial result (what was done, what was not, the receipts, the smallest question that unblocks the next step) with status `partial`, never `completed`, and records the stop reason [PRODGUIDE ch17 §Budget Guardrails and Context Discipline] | `max_iterations`, `max_turns`, `recursion_limit` and similar set deliberately (framework defaults are not a decision); counters in checkpointed state (design: agent-harness-designer); a forced stop's status and output on a trace |
| A2 **B** | Per-session cost and turn fuse that halts and hands off, independent of the provider's account-level cap | Session object carrying running cost and turns, checked every iteration; handoff path |
| A3 | Timeouts on every model call, tool, retrieval and job, and the timeout cancels the work | Client timeouts, cancellation of in-flight tool or generation; no orphaned work after timeout |
| A4 | Retries only on transient errors (timeouts, 429, 5xx) with jittered backoff and a max; client errors fail fast; every side-effecting call carries an idempotency key (run ID, action and target), and a timeout triggers a lookup by key or target before any retry; retries counted on the trace | Retry decorator config; error-class handling; idempotency keys on write calls; the lookup before a write is retried. A blanket retry on a write tool can act twice: treat it as P0 |
| A5 | Circuit breaker per dependency with a defined degraded path | Breaker config; degraded responses flagged |
| A6 | Fallback model tested end to end with the same schema, enum normalisation and decision-consistency checks | CI job running the suite on the fallback |
| A7 | Structured output validated: strict schema mode where available, local validation, bounded re-ask with the error | Validator code; re-ask limit |
| A8 | Long runs are async with job ID, status, cancel and streamed progress; checkpoints allow resume | Job queue, SSE or WebSocket endpoint, checkpoint store |
| A9 | Rate limits per user or tenant, streams throttled and open streams capped per client, concurrency capped when tools slow down, bounded queues, backpressure, explicit rejection or degradation | Limiter config, open-stream cap, queue max size, depth alert [FASTGENAI ch9 §API Rate Limiting and Throttling] |

## B. Tracing and correlation

| ID | Item | Evidence |
|---|---|---|
| B1 **B** | One trace ID per request reaches model calls, tool calls, MCP calls, retrieval, validation and logs; sub-agents inherit it; the request ID also goes into provider metadata | Pick one production trace and follow it end to end; a log line from each component carries the same trace ID as the trace; parallel branches stay in the request's trace. Best: a test with a fake tracer asserts one trace per request (concurrent branches included) and the trace ID on every log line |
| B2 | One span per step (model, tool, retrieval, validation, guardrail, handoff) with status and error class | Trace view shows the steps, not only entry and exit |
| B3 | Root and model spans carry agent version, prompt name and version, model ID and parameters, config version, environment | Attributes on a sample trace |
| B4 | Root records stop reason, iterations, retries, fallbacks, degraded flag, tokens including cache-read, and cost | Attributes on a sample trace; token counts mapped to the spec's meaning per provider (input includes cached tokens); a test checks the cost arithmetic |
| B5 | Decisions recorded: selected tool and arguments (or a hash in production), planner choice, validation result, approvals | Attributes or events |
| B6 | OpenTelemetry-based or OTLP-exportable; GenAI convention names where they exist; instrumentation versions pinned (the conventions are Development status) | Dependency pins; exporter config |
| B7 | User feedback and online-eval verdicts join the trace by ID | Feedback event or table keyed by trace ID |
| B8 | Run record keyed by run ID: a header (agent, prompt, policy and model versions, permission tier, input reference, limits) and events for plan, source references, payload previews, approvals, receipts, errors and exit status; the run ID is on every trace and audit entry | One run's record read end to end and matched to its traces by run ID (observability.md §1, "The run record is the join"); design in agent-harness-designer. Traces alone don't count: a run that waits for a person spans several traces |

## C. Logging, redaction and retention

| ID | Item | Evidence |
|---|---|---|
| C1 **B** | No raw PII, credentials or secrets in telemetry: masked or dropped before export | Masking code before attributes are set; collector redaction config; a spot check of real traces. On a running system that scores 0, the data is already stored: the P0 fix also finds and purges or re-masks every stored copy (observability.md §3, "When sensitive data is already stored") and escalates to the privacy or legal owner. In a code-only review, write the stored-copy part as "if any real data has passed through, purge or re-mask it; ask the privacy owner" |
| C2 | Content capture off by default in production; full payloads only for a sampled share, failures, escalations and incidents, in a store with references on the span | Capture flags per environment |
| C3 | Audit log (actions, approvals, outcomes; long retention; tamper-evident) separate from the debug payload store (short retention; restricted access) | Two sinks with different policies |
| C4 | Retention schedules automated and verified | Deletion jobs and their last run |
| C5 | Audit relies on decisions and short justifications, not raw chain-of-thought | Audit schema |
| C6 | Third-party tracing vendor checked for residency, processing terms and access control, or self-hosted | DPA or self-host config |

## D. Monitoring and alerting

| ID | Item | Evidence |
|---|---|---|
| D1 | Dashboard by layer (infrastructure, model, agent loop, quality, economics, user) with p50, p95, p99 | Dashboard link |
| D2 | Stop-reason and loop-iteration distributions tracked, with alerts on shifts | Panels and rules |
| D3 | Alerts use windows with a minimum sample count, are layered (digest, warning, page) and are tuned towards at most one false page a week, with outcomes logged | Alert rules; alert log; rate alerts guarded by a denominator floor; each alert validated on a regression window (fires) and a benign window (stays quiet) |
| D4 | Alert text names component and version and links example traces; relative triggers after deploys | Alert templates |
| D5 | Runbook for quality alerts exists and was used | Runbook; last incident notes |
| D6 | Drift statistics calibrated on own history and used to explain, not to page | Drift job config |
| D7 | Named owner per metric and a standing triage review | RACI or on-call doc; meeting notes |

## E. Online evals and feedback

| ID | Item | Evidence |
|---|---|---|
| E1 | Online scoring runs asynchronously, off the request path; inline guardrails stay within about 100 ms | Worker code; latency of guardrail spans |
| E2 | Hash-based, stratified sampling at a rate that fits volume; failures, escalations and guardrail hits always captured | Sampler code |
| E3 | Samples scrubbed before they are written and deleted on a schedule | Sampler write path |
| E4 | Eval spend tracked per scorer against a budget (5 to 15% of inference spend) | Cost report |
| E5 | Implicit signals tracked: rephrase, abandonment, retries, bypass to a manual channel | Metrics |
| E6 | Online scorers can catch confident wrong answers: groundedness against the trace's own tool results, claim-versus-action checks or code policy rules, plus a periodic labelled sample for reference-based correctness | Scorer list; not only helpfulness or tone judges |

## F. CI gates and versioning

| ID | Item | Evidence |
|---|---|---|
| F1 **B** | Prompts, tool definitions, agent configs and model IDs are versioned; rollback is a version change, not a code edit | Registry or versioned files; version on traces. A prompt or config read at runtime is pinned to a version, the version is on every trace, and changing it is a release (gate, then canary), not an edit |
| F2 | An offline suite with a reviewed baseline exists | Dataset version; baseline file and its review |
| F3 | The CI gate runs on PRs touching prompts, models, tools, configs or datasets | Workflow with path filter |
| F4 | Deterministic regressions have zero tolerance; judged flips are rerun and tested as paired differences; tolerance came from repeated runs | Gate code; tolerance note |
| F5 | The gate posts newly failing and newly passing cases to the PR; baselines change only after review | PR comments; baseline history |
| F6 | Judge model and rubric version pinned; verdict cache keyed on both | Config; cache key |
| F7 | Model migrations go through the same gate | Migration PRs |

## G. Release and rollback

| ID | Item | Evidence |
|---|---|---|
| G1 **B** | Shadow runs and offline replay cannot execute write tools: they hit a recorder or dry-run stub | Tool router config per mode; a test proving it. N/A if the agent has no write tools, or if no shadow or replay path exists yet; in that case make the recorder a precondition of the fix that introduces shadow |
| G2 | Canary at 1 to 5% for at least 24 hours [EVALS ch10] with version-tagged telemetry and automatic rollback on written triggers: success under the SLA, p95 latency, duplicate side effects and review minutes [PRODGUIDE ch17 §Performance Tuning Without Breaking Reliability], plus cost per successful run (this skill's addition). When any tool writes, an all-at-once cutover with no shadow and no canary is P0 | Deploy config; a rollback rule naming each trigger; on a trigger the canary flips to draft-only or rolls back [PRODGUIDE ch17 §Performance Tuning Without Breaking Reliability] |
| G3 | Rollback has been rehearsed and its time is known | Drill record |
| G4 | In-flight sessions survive deploys (sticky versions, rainbow deploys, checkpoints) | Deploy strategy |
| G5 **B** | Kill switch in two levels: draft-only (execution off, planning and previews on) and abort (every call off, credentials revoked, restart only with a person's approval); flags the gate reads at every call, flipped without a redeploy, drilled, and able to stop one tool as well as the whole agent | The flag store the gate reads; the last drill and how long a flip took to reach running workers. A switch that needs a redeploy scores 0. A blocker only when a tool writes; otherwise scored as a normal item. For a customer-facing agent, an off switch that falls back to a human channel is a P0 fix even when no tool writes |
| G6 | After every deploy or config change, a smoke set runs: one canary question per tool or data source whose answer identifies the backend, plus one memory write-and-read in a new session if the agent has memory | Smoke job and its last run; health checks alone don't count |
| G7 | Permission tier per tool action (read, draft, execute with approval, rarely auto) held in run state and enforced by the gate; an irreversible action needs an approval bound to a digest of the exact action and arguments, with an expiry and a nonce, and the executor refuses a changed digest or an expired approval | Tier table; approval records; a test that edits an argument after approval and is refused. Tier design and who approves: agent-threat-modeler |
| G8 | Safe-mode replay: any past run loads from its record and replays with tool calls simulated or execution disabled, still producing the plan and payload previews; the team knows whether a replay reproduces (recorded outputs fed back) or experiments (fresh model calls) | One replay of a failed run compared with the original; design in agent-harness-designer. G1 checks that a replay cannot write; G8 checks that replay exists |
| G9 | Escalation and human handoff work end to end, and the customer-facing failure path is tested: a handoff request reaches a person or a queue, and a model or server error shows the user a clear message and a way to continue | Two cases in the post-deploy smoke set (G6), one that triggers a handoff and one that forces a server error; the listener or queue that receives the handoff. A handoff event that nothing receives scores 0, seen |

## H. Improvement loop

| ID | Item | Evidence |
|---|---|---|
| H1 | Every incident or confirmed bad output becomes a reviewed test case within a day; golden paths kept | Dataset commits linked to incidents |
| H2 | Regular triage groups failures by root cause; backlog prioritised by frequency, severity, feasibility, recurrence | Triage notes |
| H3 | One change per round, measured on the full suite, recorded as problem, change, measurement | Change log |
| H4 | Optimiser output and any self-adaptation pass the same gate; no unreviewed self-modification in production | Process; code paths that write prompts |
| H5 | Post-incident reviews fix instrumentation gaps as well as the bug | Postmortem actions |

## I. Cost and latency

| ID | Item | Evidence |
|---|---|---|
| I1 | Written performance budget per task type (latency, calls, tokens, tool calls, steps, retries, cost) with an action at each limit (stop, degrade, go async) | Budget doc or config |
| I2 | Expected, likely high (every step at its p95; above a true p95) and capped ceiling cost per request known; monthly projection at expected volume and at peak (busiest day × 30) | Cost model with dated prices |
| I3 | Cost attributed per workflow, tenant, feature and step from traces, not read off the invoice | Cost dashboard; a per-call ledger that reconciles with the invoice within a few percent; cost metric dimensions low-cardinality (no session or user IDs) |
| I4 | Cache-read token share and cache write-to-read ratio on a dashboard, with an alert when a deploy breaks the cache | Panel; rule |
| I5 | Deterministic work done in code; tool results trimmed; token ceiling per prompt section | Code; token budgets |
| I6 | Any routing or cascade is judged on cost per successful run including repairs | Comparison report |
| I7 | Batch or flex tiers used for evals, enrichment and backfills | Job config |
| I8 | p95 latency SLO defined; time to first token tracked; streaming for long answers | SLO doc; panels |
| I9 | A small KPI set tied to the SLA on one dashboard: success under the SLA, cost per successful run with review minutes priced in, p50 and p95 per phase with jitter, duplicate side-effect rate, review and cleanup minutes per run | Dashboard; the cost per successful run arithmetic (cost-latency.md §2) [PRODGUIDE ch17 §The Economics of an Agent Run] |

## J. Deployment and capacity

| ID | Item | Evidence |
|---|---|---|
| J1 | Each agent's serving tier is justified by its data sensitivity and load shape | Deployment doc |
| J2 | A gateway or abstraction makes provider and model a config value; a second provider or model has passed the gate | Gateway config; CI run |
| J3 | Provider rate limits (requests and tokens per minute) checked against peak load with headroom | Limits vs projected peak |
| J4 | If self-hosting: weights on persistent storage, measured cold start, prefix caching on, KV cache sized for target concurrency at real context lengths, quantized checkpoint evaluated on own tasks | Infra config; load-test results; base model pinned to an immutable revision and mirrored to own storage when serving adapters. N/A when every model is a managed API |
| J5 | Each host's maximum execution time exceeds the agent's capped latency ceiling plus the async-job path; for an SLA, health checks replace unhealthy instances, autoscaling follows an agent signal, and instances span at least two zones | Host timeout vs `cost_model.py` latency ceiling; health check and scaling config |
| J6 | Service boundary: requests and responses validated against declared schemas; errors in one documented format (problem details, RFC 9457) | Schema models on every endpoint; a malformed request refused with a clear error [FASTGENAI ch4 §Pydantic Models] |
| J7 | No inference or other blocking work on the request event loop (async clients, a worker pool or a separate model server); workers hold no request open; in-flight runs drain or checkpoint on shutdown | Handler code; a load test where one slow call does not stall other requests [FASTGENAI ch5 §Blocking the Main Server]. Serving design: agent-harness-designer |

## K. Servers and supply chain

These rows cover the agent service, every tool or MCP server your team runs and the trace collector: operational defaults that nobody chose but that decide the blast radius [HARDMCP ch10]. Score what you can see; for a third-party server, score what you can verify (signature, pinned version, inventory entry) and hand the rest to **agent-threat-modeler**, which also owns the attacker-style tests, the authentication design and the host-side controls (definition pinning, `server::name`). K1 is N/A when nothing listens locally. K8 is N/A only when every server is reached over stdio or loopback and traces never leave the host. K9 is N/A when no request field names a server-side resource.

| ID | Item | Evidence |
|---|---|---|
| K1 | Local servers bind to loopback (stdio preferred for local use), with a remote endpoint only where one is needed; the Host and Origin headers are checked against an allowlist, because a web page can reach a localhost server through DNS rebinding | Bind address in config; a request with a foreign Host header refused. A container port published with no host address binds every interface (the container runtime's default): K1 scores 0, seen, and reachability beyond the host stays inferred until checked |
| K2 | Servers run with a read-only filesystem and no ambient capabilities (container settings, or the managed runtime's equivalent) | Container or runtime spec |
| K3 | Encryption on every hop, client to server and server to server | TLS settings per hop |
| K4 | Releases are signed and the signature verified before launch; every server is inventoried with owner, version and where it runs; a disclosure contact is published (`security.txt`) | The verification step in the launch path; the inventory; the contact file |
| K5 | The full resolved dependency tree is pinned to versions and hashes; a vulnerability audit is a build gate, on a tighter clock for auth and crypto libraries; installs use verified wheels from a vetted index | Lock file with hashes; audit job; index config [HARDMCP ch3]. A library the code imports that arrives only through another package (transitive or peer dependency) is an undeclared direct dependency: declare and pin it, but don't report it as missing |
| K6 | Every call is answerable: a structured log line per call with actor, tool, arguments (or their hash) and request ID, redacted inside the logging path | Log schema; redaction in the logger, not after storage |
| K7 | Runtime abuse is resisted: idempotency keys reject replays, per-identity rate limits stop floods, and delegated tasks carry signed provenance | A replayed request refused; limiter config; the provenance check on delegated calls |
| K8 **B** | Every server reachable beyond stdio or loopback authenticates every request, `tools/list` included (OAuth as the MCP specification describes, or mutual TLS): MCP and tool servers, the agent's own API, and the trace collector. Anonymous callers are never acceptable on internal servers. A public endpoint built for anonymous end users (a website chat widget) is acceptable only behind bot protection, per-client rate limits (A9) and server-side allowlists for every resource the request names (K9), and the hops behind it still authenticate. The OTLP collector is not internet-exposed and requires authentication plus TLS, because traces carry prompts and tool arguments. A blocker when the server can reach private data or a write tool; a collector that receives prompts or tool arguments counts as private data. No authentication plus such reach scores 0; when only the bind address or published port is seen, tag reachability beyond the host inferred | An unauthenticated request (and one with another client's token) refused, on each endpoint; collector bind address and auth config; for a public endpoint, the bot check and the per-client limiter |
| K9 **B** | Resource identifiers the client supplies (knowledge base or index, tenant, model, file path, bucket) are checked server-side against an allowlist or the caller's ownership before use; better, the server takes them from its own config. A blocker when the resource can hold private data or a write tool reaches it | Each request field traced into the server-side call it feeds, with the check before it; a request naming another tenant's or an unlisted resource refused. A model ID chosen by the client and passed through unchecked counts too (cost and policy) |

## Fix priorities

- **P0**: any blocker below 2; any Run gate row that fails; anything that can spend without bound, leak data or act twice; peak load above provider limits; K items on a server that can reach private data or a write tool; an all-at-once cutover with no shadow or canary when any tool writes (G2); no off switch with a human fallback on a customer-facing agent (G5). For C1 at 0 on a running system, the P0 covers the stored copies as well as future export: purge or re-mask them, keep a deletion log, and hand the notification question to the privacy or legal owner (observability.md §3); in a code-only review, "if any real data has passed through". Fix before launch or scale-up.
- **P1**: gaps that stop you detecting or diagnosing a regression (B2 to B4, B8, D1 to D3, E1 to E2, E6, F2 to F5, G2 to G3, G6, H1); a handoff or failure path that does not reach the user or a person (G9); K items on other servers.
- **P2**: cost and latency optimisations, hygiene, tooling.

**A fix that relies on a framework control.** When a P0 fix is built on a control the framework provides (middleware authentication, session handling, CSRF protection), check the pinned framework version for published bypasses of that control, and schedule the upgrade with the fix or before it, never after. For example, CVE-2025-29927 (March 2025) let requests skip Next.js middleware on self-hosted 14.x before 14.2.25 and 15.x before 15.2.3 (older lines had their own fixes), so an authorization check placed in middleware on an older pin did not run (as of 2026-10). When you cannot check advisories (no web access), say so, put the framework version under "Confirm first", and still schedule the upgrade with the fix.

Within a tier, order by risk removed or money saved per unit of effort. Each fix names what to change, where (file, config, service), how to verify it (the metric or test that proves it), effort (S, M, L), an owner and when it is due: a date when the review targets one, otherwise "week N" counted from the review date (P0 fixes in the first weeks, before any scale-up).
