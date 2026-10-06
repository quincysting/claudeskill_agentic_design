# Production-readiness checklist (scored)

Score each item **0** (absent or only planned), **1** (partial, or present without evidence it works) or **2** (in place, with evidence: file and line, config, dashboard, runbook, test). Mark **N/A** with a reason when an item cannot apply (for example, no self-hosted models), and leave it out of the percentages. A framework default nobody chose (a default recursion limit, a default retry policy) scores at most 1. Score on evidence only; "we plan to" is 0, and a setting that exists but is never exercised (an untested fallback) is 1.

**Evidence tags.** Tag every score with where it came from: **seen** (you inspected the file, config, trace or dashboard), **told** (an owner described it but you have not seen it; scores at most 1) or **U, unverified** (no access and no description; scores 0). A U-tagged 0 means "go and look"; a seen 0 means "build it". Keep the two apart in the review.

**N/A.** J4 is N/A whenever every model runs on a managed API; that is the normal case, so leave it out of the denominator rather than scoring 0. For G1, list every tool and its side effect first, and ask when you cannot see the tool code. Search, fetch and query tools are reads; anything that sends, writes, books, pays, deletes or changes state outside the agent is a write. No write tools (common for research and Q&A agents) makes G1 N/A. Write tools but no shadow or replay path yet is also N/A, with the recorder made a precondition of the fix that introduces shadow. Side effects unknown means G1 is U, not N/A.

**B** marks a blocker. Blockers are the failures that burn money without limit, leak data, make incidents undiagnosable, or let a release act twice.

## Verdict rule

- **Not ready**: any blocker scores 0, or the total is below 50% of applicable points.
- **Ready with conditions**: every blocker scores at least 1 and the total is at least 50%. The conditions are every blocker at 1 plus all P0 fixes, each with an owner and a date before launch or scale-up.
- **Ready**: every blocker scores 2, the total is at least 75%, and no area is below 50%.

Percent = points / (2 × applicable items). Report per area and overall.

**Missing evidence.**
- **Provisional**: put "Provisional" in front of the verdict when any blocker is U or more than a quarter of applicable items are U. Report a floor (U items at 0) and a ceiling (U items at 2) and the verdict each one gives; the gap shows how far the verdict rests on evidence nobody has seen. A blocker *seen* at 0 makes "Not ready" firm, whatever else is unverified.
- **Too speculative to score**: when the run map is assumed (you have not seen the loop, caps and tool code or config), or more than half of the blockers or half of the applicable items are U, do not hand back item-by-item scores as findings. Deliver a discovery plan (the evidence per blocker: one production trace followed end to end, loop and retry config, exporter and masking config, prompt and tool registry, tool router per mode; who holds each and how long it takes) plus the provisional verdict from what you know. Rescore when the evidence arrives.

**Lite mode** (internal pilot, under about 100 requests a day, no write tools): score only the blockers plus B2, C2, F2, I1 and I2, and say so in the review.

## A. Bounded execution and resilience

| ID | Item | Evidence to look for |
|---|---|---|
| A1 **B** | Hard caps on loop iterations, tool calls and tokens per task type, enforced by the runtime; the stop reason is recorded | `max_iterations`, `max_turns`, `recursion_limit` and similar set deliberately (framework defaults are not a decision); stop reason on the trace |
| A2 **B** | Per-session cost and turn fuse that halts and hands off, independent of the provider's account-level cap | Session object carrying running cost and turns, checked every iteration; handoff path |
| A3 | Timeouts on every model call, tool, retrieval and job, and the timeout cancels the work | Client timeouts, cancellation of in-flight tool or generation; no orphaned work after timeout |
| A4 | Retries only on transient errors (timeouts, 429, 5xx) with jittered backoff and a max; client errors fail fast; write tools retried only with an idempotency key; retries counted on the trace | Retry decorator config; error-class handling; idempotency keys on write calls. A blanket retry on a write tool can act twice: treat it as P0 |
| A5 | Circuit breaker per dependency with a defined degraded path | Breaker config; degraded responses flagged |
| A6 | Fallback model tested end to end with the same schema, enum normalisation and decision-consistency checks | CI job running the suite on the fallback |
| A7 | Structured output validated: strict schema mode where available, local validation, bounded re-ask with the error | Validator code; re-ask limit |
| A8 | Long runs are async with job ID, status, cancel and streamed progress; checkpoints allow resume | Job queue, SSE or WebSocket endpoint, checkpoint store |
| A9 | Rate limits per user or tenant, bounded queues, backpressure, explicit rejection or degradation | Limiter config, queue max size, depth alert |

## B. Tracing and correlation

| ID | Item | Evidence |
|---|---|---|
| B1 **B** | One trace ID per request reaches model calls, tool calls, MCP calls, retrieval, validation and logs; sub-agents inherit it; the request ID also goes into provider metadata | Pick one production trace and follow it end to end |
| B2 | One span per step (model, tool, retrieval, validation, guardrail, handoff) with status and error class | Trace view shows the steps, not only entry and exit |
| B3 | Root and model spans carry agent version, prompt name and version, model ID and parameters, config version, environment | Attributes on a sample trace |
| B4 | Root records stop reason, iterations, retries, fallbacks, degraded flag, tokens including cache-read, and cost | Attributes on a sample trace |
| B5 | Decisions recorded: selected tool and arguments (or a hash in production), planner choice, validation result, approvals | Attributes or events |
| B6 | OpenTelemetry-based or OTLP-exportable; GenAI convention names where they exist; instrumentation versions pinned (the conventions are Development status) | Dependency pins; exporter config |
| B7 | User feedback and online-eval verdicts join the trace by ID | Feedback event or table keyed by trace ID |

## C. Logging, redaction and retention

| ID | Item | Evidence |
|---|---|---|
| C1 **B** | No raw PII, credentials or secrets in telemetry: masked or dropped before export | Masking code before attributes are set; collector redaction config; a spot check of real traces |
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
| D3 | Alerts use windows with a minimum sample count, are layered (digest, warning, page) and are tuned towards at most one false page a week, with outcomes logged | Alert rules; alert log |
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

## F. CI gates and versioning

| ID | Item | Evidence |
|---|---|---|
| F1 **B** | Prompts, tool definitions, agent configs and model IDs are versioned; rollback is a version change, not a code edit | Registry or versioned files; version on traces |
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
| G2 | Canary at 1 to 5% for at least 24 hours with version-tagged telemetry and automatic rollback | Deploy config; rollback rule |
| G3 | Rollback has been rehearsed and its time is known | Drill record |
| G4 | In-flight sessions survive deploys (sticky versions, rainbow deploys, checkpoints) | Deploy strategy |
| G5 | Kill switch to disable the agent, or one tool, quickly | Feature flag |

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
| I2 | Expected, likely high (about p95) and capped ceiling cost per request known; monthly projection at expected volume and at peak (busiest day × 30) | Cost model with dated prices |
| I3 | Cost attributed per workflow, tenant, feature and step from traces, not read off the invoice | Cost dashboard |
| I4 | Cache-read token share on a dashboard, with an alert when a deploy breaks the cache | Panel; rule |
| I5 | Deterministic work done in code; tool results trimmed; token ceiling per prompt section | Code; token budgets |
| I6 | Any routing or cascade is judged on cost per successful task including repairs | Comparison report |
| I7 | Batch or flex tiers used for evals, enrichment and backfills | Job config |
| I8 | p95 latency SLO defined; time to first token tracked; streaming for long answers | SLO doc; panels |

## J. Deployment and capacity

| ID | Item | Evidence |
|---|---|---|
| J1 | Each agent's serving tier is justified by its data sensitivity and load shape | Deployment doc |
| J2 | A gateway or abstraction makes provider and model a config value; a second provider or model has passed the gate | Gateway config; CI run |
| J3 | Provider rate limits (requests and tokens per minute) checked against peak load with headroom | Limits vs projected peak |
| J4 | If self-hosting: weights on persistent storage, measured cold start, prefix caching on, KV cache sized for target concurrency at real context lengths, quantized checkpoint evaluated on own tasks | Infra config; load-test results. N/A when every model is a managed API |

## Fix priorities

- **P0**: any blocker below 2; anything that can spend without bound, leak data or act twice; peak load above provider limits. Fix before launch or scale-up.
- **P1**: gaps that stop you detecting or diagnosing a regression (B2 to B4, D1 to D3, E1 to E2, F2 to F5, G2 to G3, H1).
- **P2**: cost and latency optimisations, hygiene, tooling.

Within a tier, order by risk removed or money saved per unit of effort. Each fix names what to change, where (file, config, service), how to verify it (the metric or test that proves it), effort (S, M, L), an owner and when it is due: a date when the review targets one, otherwise "week N" counted from the review date (P0 fixes in the first weeks, before any scale-up).
