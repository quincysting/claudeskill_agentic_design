# Operations and cost plan: <agent name>

Date: <YYYY-MM-DD> · Prices as of <date>, source <URL> · Status: <draft | agreed>

## 1. Targets

| Task type | Volume/day (now, peak) | p95 latency target | Cost ceiling per request | Quality bar (eval metric) |
|---|---|---|---|---|

## 2. Run map and budgets

```
<text flow of the request path with model, p, calls, cap per step>
```

| Task type | Max steps | Max tool calls | Max input tokens | Max retries | Timeout | Cost fuse/session | At the limit |
|---|---|---|---|---|---|---|---|

## 3. Cost model

- Tiers: <small = model, mid = model, …>, prices as of <date>
- Per request: expected <$>, likely high (~p95) <$>, capped ceiling <$> (<ratio>x; a bound, not a forecast). With no caps: "UNBOUNDED now; <$> with proposed caps <list>".
- Per month: <$> at expected volume; <$> at peak (expected × busiest day's volume × 30)
- Per-step share: <steps, including non-model cost>
- Inputs table: <each value marked measured or assumed>
- Quality baseline: <eval set and version, pass rate with interval, cost per successful task>, or "none yet: build it first (agent-eval-designer); no lever below ships until it exists"

### Levers, in order

| # | Lever | Step | Expected effect | Proof metric | Risk and guard |
|---|---|---|---|---|---|

## 4. Latency plan

<p95 decomposition (model, retrieval, tool, orchestration, loop) and the chosen levers>

## 5. Tracing

- Spans: <list, with OTel GenAI operation names>
- Attributes: <standard ones used> + custom `app.*`: <stop_reason, cost, degraded, versions…>
- Propagation: <HTTP headers, message metadata, MCP params._meta>
- Library versions pinned: <…> (GenAI conventions are Development status as of <date>)

## 6. Logging, redaction and retention

| Record | Content | Masking | Store | Retention | Access |
|---|---|---|---|---|---|
| Audit log | | | | | |
| Debug payloads | | | | | |
| Eval samples | | | | | |

## 7. Metrics and dashboards

<panels by layer and owner per metric>

## 8. Online evals

Sampling: <rate, strata, always-captured classes> · Scorers: <cheapest first> · Budget: <$/month, % of inference> · Verdicts on trace as `gen_ai.evaluation.result`.

## 9. Alerts

| Alert | Signal | Window | Min samples | Trigger | Severity | Route | Runbook |
|---|---|---|---|---|---|---|---|

## 10. CI gates

| Tier | Trigger | Scorers | Rule | Budget |
|---|---|---|---|---|

## 11. Release and rollback

<shadow (write tools stubbed), canary %, duration, rollback rule, session stickiness, kill switch>

## 12. Improvement loop

<cadence, owners, failure-to-test-case SLA, change log format, optimiser policy>

## 13. Deployment per agent

| Agent or step | Data sensitivity | Load shape | Tier | Reason |
|---|---|---|---|---|

Peak load per model (busiest day ÷ 1,440 × peak-hour factor <x>; default 3 = 24 h ÷ 8 busy hours, assumed until measured):

| Model | Calls/min | Uncached input tok/min | Output tok/min | Provider limits (RPM, ITPM, OTPM) | Headroom |
|---|---|---|---|---|---|

## 14. Rollout sequence

| Week (date, or N from the plan date) | Deliverable | Owner | Done when |
|---|---|---|---|

## 15. Assumptions and open questions
