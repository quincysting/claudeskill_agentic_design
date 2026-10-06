# Observability, online evals, alerts, releases and the improvement loop

Load this for steps 5 to 11 of the procedure. Offline eval design (datasets, scorers, judge calibration) belongs to **agent-eval-designer**; guardrail content and red-teaming to **agent-threat-modeler**. This file covers how those run in production and how failures flow back.

Two ideas run through this file:
- **Observability gives evidence, evaluation gives judgment.** A trace can show the agent retrieved three documents, called a tool, passed validation and answered, and still not say whether the answer was right. Join the two by trace ID: traces explain eval failures, evals say which traces matter.
- **Two speeds.** Guardrails are synchronous (block or modify before the user sees output, milliseconds, very low false-positive rate). Online evals are asynchronous (score a sample after delivery, feed aggregates and alerts). An LLM judge on the request path adds roughly 0.5 to 2 s per request.

## 1. Trace schema: what every run records

Work backwards from the questions an investigator asks: why did it answer this way, what context did it see, which tool did it call and what came back, did validation pass, how many steps, where did time and money go, why did it stop.

| Field | Span | OTel GenAI name (Development, 2026-10) or custom |
|---|---|---|
| Trace ID, propagated to every model, tool, MCP, retrieval and validation call, and to sub-agents | all | W3C trace context; MCP: `params._meta.traceparent` |
| Request ID also sent in provider request metadata and tool logs | root | custom `app.request_id` |
| Session or conversation | root, model | `gen_ai.conversation.id` |
| Agent name, version, environment, config or flag version | root | `gen_ai.agent.name`; custom `app.agent.version`, `app.config.version`, `deployment.environment.name` |
| Prompt name and version | model | `gen_ai.prompt.name`, `gen_ai.prompt.version` |
| Model and parameters | model | `gen_ai.provider.name`, `gen_ai.request.model`, `gen_ai.response.model`, `gen_ai.request.temperature`, `gen_ai.request.max_tokens` |
| Tokens incl. cache | model | `gen_ai.usage.input_tokens`, `gen_ai.usage.output_tokens`, `gen_ai.usage.cache_read.input_tokens`, `gen_ai.usage.cache_write.input_tokens` |
| Per-call finish reason | model | `gen_ai.response.finish_reasons` |
| Tool name, call ID, status, error class, latency | tool | `gen_ai.tool.name`, `gen_ai.tool.call.id`, `gen_ai.tool.type`, `error.type` |
| Tool arguments | tool | opt-in `gen_ai.tool.call.arguments`; in production prefer a hash or the IDs it touches (`app.tool.args_hash`) |
| Retrieved document or chunk IDs, scores; memory reads | retrieval, memory | operations `retrieval` (`gen_ai.data_source.id`), `search_memory`; custom `app.retrieval.doc_ids` |
| Validation and guardrail results (pass, fail, action taken) | validation | custom `app.validation.result`, `app.guardrail.action` |
| Decisions: selected tool, planner choice, fallback taken, approval requested and its outcome | model, root | custom `app.decision.*`, `app.fallback`, `app.approval.status` |
| **Agent stop reason** (final_answer, step_limit, cost_limit, validation_failed, approval_required, tool_error, timeout) | root | custom `app.stop_reason` (no agent-level attribute in the spec yet) |
| Loop iterations, retries, degraded or partial success | root | `gen_ai.invoke_agent.inference_calls`, `gen_ai.invoke_agent.tool_calls` (metrics); custom `app.loop.iterations`, `app.retries`, `app.degraded` |
| Cost in USD | root, model | custom `app.cost.usd` (compute from tokens × dated price table) |
| User feedback, online-eval verdicts | event on the evaluated span | `gen_ai.evaluation.result` with `gen_ai.evaluation.name`, `gen_ai.evaluation.score.value` / `.score.label`, `gen_ai.evaluation.explanation`; feedback as an event keyed by trace ID |

Not on the list: raw chain-of-thought. Record actions, observations, state and a short decision justification. Raw thinking text is model-specific, may hold sensitive content and is not what an auditor needs.

A stop reason matters because a loop that finished and one that hit its cap both return a response; only one is healthy. A degraded run (soft retrieval timeout, fallback model, skipped optional step) produces an answer that looks fine; flag it.

**Instrument three boundaries**: request movement (entry, each iteration, retries, fallbacks, response), AI behaviour (prompt assembly, model call, retrieval, tool selection, validation, memory), and production impact (latency, tokens, cost, timeouts, degraded runs). Logging only entry and exit is the black-box trap: the diagnosis becomes "the model gave a bad answer". In graph frameworks, one span per node with tool name, status, error code, prompt ID and token counts.

**Multi-agent**: the task ID and trace context survive every delegation, so agent A's trace includes its messages to B and C and what they did. Propagate in HTTP headers or message metadata; for MCP, inside each request's `params._meta` (HTTP headers only cover the outer transport).

## 2. OpenTelemetry GenAI semantic conventions (status as of 2026-10-06)

- **Where**: moved out of the main semantic-conventions repo into `open-telemetry/semantic-conventions-genai` (created May 2026). No tagged release yet. **Every document is Development status**, not stable. Pin your instrumentation library versions and expect attribute renames.
- **Span operations** (`gen_ai.operation.name`): inference (`chat`, `generate_content`, `text_completion`), `embeddings`, `retrieval`, memory (`search_memory`, `create_memory` and others), `create_agent`, `invoke_agent` (span name `invoke_agent {gen_ai.agent.name}`), `invoke_workflow`, `plan`, `execute_tool` (span name `execute_tool {gen_ai.tool.name}`), plus agent-skill spans (`load_skill`, `read_skill_resource`) and command execution.
- **Metrics**: `gen_ai.client.operation.duration`, `gen_ai.client.operation.time_to_first_chunk`, `gen_ai.client.operation.time_per_output_chunk`, server-side `gen_ai.server.request.duration`, `gen_ai.server.time_to_first_token`, `gen_ai.server.time_per_output_token`; agent-level `gen_ai.invoke_agent.duration`, `gen_ai.invoke_agent.inference_calls`, `gen_ai.invoke_agent.tool_calls`, `gen_ai.execute_tool.duration`, `gen_ai.invoke_workflow.duration`. Token counters live in a separate token-metrics document: `gen_ai.client.inference.usage.input_tokens`, `.output_tokens`, `.cache_read.input_tokens`, `.cache_write.input_tokens`. Older instrumentation emits `gen_ai.client.token.usage` with a `gen_ai.token.type` attribute; check which your library emits before building dashboards.
- **Events**: `gen_ai.evaluation.result` (parent it to the evaluated span, or set `gen_ai.response.id` when the span is gone); `gen_ai.client.inference.operation.details` for request details at debug severity.
- **MCP**: span name `{mcp.method.name} {target}`, attributes `mcp.method.name`, `mcp.session.id`, `mcp.protocol.version`, `jsonrpc.request.id`, `gen_ai.tool.name`; trace context written unprefixed in `params._meta` (`traceparent`, `tracestate`, `baggage`).
- **Content**: `gen_ai.system_instructions`, `gen_ai.input.messages`, `gen_ai.output.messages`, `gen_ai.tool.definitions`, `gen_ai.tool.call.arguments`, `gen_ai.tool.call.result` are **opt-in**. The spec's three patterns: (1, default) record none; (2) record on attributes, for pre-production or when storage is compliant; (3) upload content to external storage with separate access control and record references on the span, recommended for production. Instrumentations commonly gate capture behind an env var such as `OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT`; check your library's docs.
- **Gaps you fill yourself**: agent-level stop reason, cost, degraded flag, decision records, prompt version where your framework does not set it. Use one custom namespace (`app.*`) so a later spec addition is a rename, not a redesign.

Minimal manual instrumentation with the OpenTelemetry Python API (auto-instrumentation for your SDK or framework covers model spans; add the root and the custom attributes yourself):

```python
from opentelemetry import trace
tracer = trace.get_tracer("support-agent", AGENT_VERSION)

def handle(req):
    with tracer.start_as_current_span("invoke_agent support-agent") as root:
        root.set_attribute("gen_ai.operation.name", "invoke_agent")
        root.set_attribute("gen_ai.agent.name", "support-agent")
        root.set_attribute("gen_ai.conversation.id", req.session_id)
        root.set_attribute("app.agent.version", AGENT_VERSION)
        run = agent_loop(req)                      # model and tool spans nest here
        root.set_attribute("app.stop_reason", run.stop_reason)
        root.set_attribute("app.loop.iterations", run.iterations)
        root.set_attribute("app.cost.usd", round(run.cost_usd, 6))
        root.set_attribute("app.degraded", run.degraded)
        return run.answer

def call_tool(name, args, call_id):
    with tracer.start_as_current_span(f"execute_tool {name}") as span:
        span.set_attribute("gen_ai.operation.name", "execute_tool")
        span.set_attribute("gen_ai.tool.name", name)
        span.set_attribute("gen_ai.tool.call.id", call_id)
        span.set_attribute("app.tool.args_hash", stable_hash(args))   # not the raw args in prod
        tool = TOOLS[name]
        return tool(**args)                                          # exceptions mark the span as error
```

Export over OTLP (default ports 4317 gRPC, 4318 HTTP) and confirm a span arrives end to end before relying on any dashboard. Extend the stack the company already runs; add an LLM-native backend (Langfuse, Phoenix and similar) only for features you will use, such as built-in eval and annotation. Several tools are fine if they correlate by trace ID.

## 3. What to log, what to redact, how long to keep it

Observability storage turns into a shadow database of private prompts, documents, credentials and tool results unless you stop it at the edge. Protect data **before** it lands in the observability platform.

| Class | Examples | Production default |
|---|---|---|
| Always (metadata) | IDs, versions, model, token counts, latency, cost, tool names and status, document and chunk IDs with scores, validation results, stop reason, prompt hash | Log on every run |
| Sampled payloads | Full prompts, outputs, tool arguments and results | Only for: a sampled share, failed validations, escalations, high-risk workflows, incidents; masked first; external store with references on the span |
| Never | Credentials, tokens, secrets, full payment data, raw health or government IDs | Masked or dropped in-process before `set_attribute`; Collector redaction or transform processors as a second line |

- **Two records, two policies.** An **audit log** of actions, decisions, approvals and outcomes (metadata, actor identity and task lineage, long retention, tamper-evident, compliance access) and a **debug payload store** (sampled, masked, short retention, restricted access). Most "log everything" versus "log nothing" arguments dissolve once these are separated.
- **Retention**: delete debug payloads and eval samples on a schedule (7 to 90 days is common); keep failures and expensive outliers longer than successes. Verify that deletion runs.
- **Hosted tracers**: a one-line integration that records every input and output is a privacy decision. Check data residency, processing terms and whether a self-hosted option exists before turning it on in production. For workflows with credentials or highly sensitive data, trace metadata only.
- **Volume**: raw completions for every request become an expensive, unsearchable store. Metadata plus sampled payloads answers most investigations; the cost is that the payload for a rare failure may not exist, which is why failures are always captured.

## 4. Metrics and dashboards

| Layer | Track |
|---|---|
| Infrastructure | p50/p95/p99 latency, error rate, timeouts, queue depth, saturation |
| Model | calls per request, input/output/cache-read tokens, context-window use, structured-output failure rate, provider 429s |
| Agent loop | task success, loop iterations, tool calls per request, tool failure rate per tool, repeated identical tool calls, retries, fallbacks, escalations, **stop-reason distribution** |
| Quality | sampled online-eval pass rate by stratum, groundedness, guardrail block rate |
| Economics | cost per request by task type, tenant and feature; cost per successful task; retry and fallback cost; eval spend vs inference spend |
| User | rephrasing, abandonment, retries, explicit ratings, bypass to a manual channel |

Reading aid: repeated tool calls point to unstable tool selection; step-limit stops to failure to converge; schema violations to unstable generation; frequent fallbacks to an unmet reliability threshold; correct but incomplete answers to a usefulness problem. Users rarely click ratings, so retries, rephrasing, abandonment and bypass are often the only failure signal you get.

Put accuracy, cost and latency on the same screen so nobody optimises one at the others' expense. Assign an owner per metric (product: task success and user signals; ML/eval: quality and drift; SRE: latency, errors, capacity; finance or platform: cost) and hold a standing triage over the shared dashboard. Unread dashboards give the illusion of monitoring.

## 5. Online evals on a sample

- Score in a background worker, never in the request handler. Keep guardrails (synchronous, platform or safety owner, strict latency) and online evals (asynchronous, eval owner) separate in code and ownership, so nobody adds an expensive scorer to the request path by accident.
- **Sample by hashing the request ID**, so a replayed request gets the same decision:

```python
import hashlib
def sampled(request_id: str, rate: float) -> bool:
    return int(hashlib.sha256(request_id.encode()).hexdigest()[:8], 16) / 0xFFFFFFFF < rate
```

- **Rate**: score everything below about 100 requests a day; start at 5% above that; **stratify** by task type and risk (a 5% sample of traffic that is 90% simple may contain no complex queries) and always include failures, escalations and guardrail hits.
- **Size the window, not just the rate.** Half-width of a 95% interval on a pass rate p from n samples ≈ 1.96 × √(p(1−p)/n). At p = 85%: ±12.8 points with 30 samples, ±7.7 with 83, ±3.1 with 500, ±2.2 with 1,000. To resolve a drop of d points you need a half-width well under d; n ≈ 3.84 × p(1−p) / h². Short windows only catch large drops.
- **Cost**: order scorers cheapest first (deterministic, then embedding, then small judge, then larger judge, then human). Budget eval spend at 5 to 15% of inference spend, with a floor of tens of dollars a month for small systems. Example from the eval literature (mid-2026): 10,000 requests a day at 5% is 500 scored runs, about $30 a month with a small-model judge.
- **Privacy**: scrub at the point of sampling, before the write; delete samples on a schedule.
- Attach each verdict to its trace as a `gen_ai.evaluation.result` event so a low score leads straight to the run.

## 6. Alerts that people act on

Never alert on a single request. Alert on windows with a minimum sample count, in layers:

| Layer | Rule (starting point; tune on your data) | Route |
|---|---|---|
| Digest | Daily summary of pass rates, cost, latency, stop reasons, top failing clusters | Email or chat |
| Warning | 4-hour window dips below baseline − 2 × tolerance while the 24-hour average holds; or a relative jump after a deploy (validation failures or tool errors doubling, loop iterations leaving their usual range, cache-read share collapsing) | Team chat |
| Page | 24-hour average below baseline − tolerance across two consecutive windows, with at least the minimum sample count in each; hard SLO breaches (p95 latency, error rate) over two windows; spend rate projecting above the monthly budget | On-call |

- An alert says where to look: "tool-call failures up for customer-profile tool after deployment v42", not "AI system unhealthy". Include version, component and links to example traces.
- Start generous, log each alert's outcome (real, noise), tune monthly towards at most one false page a week; if you cannot get there, get more samples or steadier scorers rather than tighter thresholds.
- Cost alerts: any session hitting the cost fuse (count, not page), hourly spend versus the same hour last week, cost per successful task by version.

**Runbook when a quality alert fires**: check the sample count and which scorer moved; read the lowest-scoring samples to see whether outputs are bad or the scorer misfires; then check, in order, a recent deploy (prompt, model, tool, config), a shift in inputs, and degraded upstream dependencies (retrieval, tool APIs, provider); act (rollback, guardrail change, upstream escalation); rerun suspect inputs 3 to 5 times (a failure rate above about 80% means a systematic bug); add the failing inputs to the eval set; and fix the blindness that hid the problem, not only the bug.

**Drift statistics explain; outcomes page.** Population stability index on categorical features such as tool mix (below 0.1 stable, 0.1 to 0.25 minor, above 0.25 major, as a starting point), effect sizes rather than p-values for continuous features (at production volume every KS test is significant), embedding-centroid distance for query topics. Calibrate any threshold by computing the statistic between consecutive normal weeks and alerting well above that range. Page on the sampled pass rate, task success or abandonment; use drift to explain why it moved.

## 7. Releases: shadow, canary, A/B

| Strategy | Use for | Rules |
|---|---|---|
| Shadow | Model, prompt or planner changes, seen on real traffic before any user | Same inputs under the same request ID, output logged never shown; compare tool choice, latency, tokens, quality; promote after it matches production over about 200 to 500 sampled requests. **Route write tools to a recorder** that returns the recorded production result or a dry-run response, and score the intended call; a shadow that can call `issue_refund` acts twice. Approvals: replayed or synthetic. Costs extra inference for the shadowed share. |
| Canary | Promoting a candidate that passed shadow | 1 to 5% of traffic for at least 24 hours; every metric filterable by version tag; automatic rollback if its score falls more than the tolerance below production |
| A/B | Questions about user behaviour (completion, satisfaction) | Enough samples, sticky assignment, no switching mid-session, per-variant state for agents with memory; read transcripts before declaring a loser (a lower completion rate can mean deeper engagement) |
| Bandit | Many variants, a reward you trust, spare traffic | Only with a validated reward; oversight against chasing short-term trends |

Default for agent changes: shadow on a sample, then canary with rollback. Keep in-flight sessions on the version they started with (sticky versions or rainbow deploys, plus checkpoints to resume), so a release does not break running agents. Rollback is a version lookup only if prompts, tool definitions, agent configs and model IDs are versioned and the version is on every trace.

## 8. The improvement loop

```
production run (traced) -> hashed sample scored async -> windowed alert
   -> triage worst traces -> group by root cause -> change ONE thing
   -> CI gate vs reviewed baseline -> shadow -> canary -> production
   (triage and the gate add new cases to the versioned eval suite)
```

- **Order of maturity**: no evals; ad hoc checks; offline suite gating CI; production sampling, monitoring and guardrails; quality criteria written before implementation. Production alerts without an offline suite cannot be reproduced, so build the CI gate first.
- **Every production failure becomes a reviewed test case within 24 hours**, with a correct expectation; notable successes become "golden paths" new versions must keep. If a case disappears after the immediate fix, the team has learned something and the system has not.
- **Triage** weekly or faster: deduplicate, tag, link each issue to its traces, prioritise by frequency, severity, feasibility and recurrence. Group failures by root cause, not symptom, and fix the largest group first. Root causes are often an ambiguous task definition or a metric that rewards the wrong behaviour.
- **One change per round**, measured on the full suite, recorded as problem, change and measurement. When a round does not help, ask whether the instruction is ignored or followed badly, whether the expected output is well defined, and whether the limit is architectural (a loop that handles one tool call per turn cannot be prompted into multi-task requests; hand that to **agent-architect**).
- **Escalation to people**: route the cases with the highest uncertainty times consequence, tuned so a manageable share escalates (under about 10% is a common target). Validate any confidence signal against labelled outcomes; self-reported confidence numbers are not evidence.
- **Automated prompt optimisers** (DSPy and similar) are proposal generators: their output goes through the same gate and shadow as a human edit. As of 2026-10, DSPy's guidance is about 10 examples for few-shot bootstrapping, 50 or more for random search and around 200 for long MIPROv2 runs; reflective optimisers such as GEPA can use judge explanations and reviewer notes as feedback.
- **No unreviewed self-modification in production.** Bounded runtime fallbacks (skip an optional step, use a fallback model, defer to a person) are fine because they are predictable and logged. An agent that rewrites its own behaviour without a regression gate cannot notice that it fixed one case and broke ten. Promote in-context wins into versioned prompts through the gate.

## 9. Choosing tooling

Choose on principles, not feature grids (which date within months): OTLP ingest, correlation by trace ID across tools, bulk export of traces, datasets, annotations with provenance, per-case results and scorer configs, and a self-host option if data rules require it. Keep scorers in your own code behind small adapters so a platform switch is a configuration change; teams do switch platforms. Build-versus-buy estimate from the eval literature (mid-2026, five engineers): own toolkit about eight engineering hours a month; a platform $200 to $500 a month plus about two hours; if more than half your scoring is custom, building tends to win; multiply migration estimates by three to five. Langfuse, as one example, is open source and self-hostable (MIT core, as of 2026-10).
