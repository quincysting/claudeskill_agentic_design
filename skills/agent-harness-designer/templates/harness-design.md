# Harness design: <agent name>

<!-- Design mode: fill every section and delete the Status lines. Review mode: Summary and Confirm first, then the findings table, then the sections, each with its Status line filled. Delete these comments. -->

## 0. Summary

<4 to 6 sentences: what the agent does, how it is triggered and served, where state lives, the framework decision, the controls an operator has, and the riskiest open point.>

**Confirm first**
1. <assumption that most changes the design, e.g. "the AP system's webhook retries on timeout for 24 hours">
2. <...>
3. <...>

## Findings (review mode only)

| # | Severity | Finding | Evidence: stated / inferred / confirmed (file:line, config key, run ID) | Fix | Test that catches it |
|---|---|---|---|---|---|

## 1. Runtime frame

Status (review mode): keep / change / add

- Responsibility: <Given X, produce Y that Z can use> (from the architecture doc, if any)
- Trigger and caller: <request / event / schedule; who waits, for how long>
- Run class: <interactive seconds / job minutes / long-running with human waits of up to N>
- Constraints: <host, time limits, framework already in use, data rules>

**Side-effect inventory**

| Action | Tool | Reversible? | Target (key source) | Backend dedupes or offers lookup? | Tier (read / write / high-impact) |
|---|---|---|---|---|---|

## 2. Framework or own loop

Status (review mode): keep / change / add

- Decision: <framework / vendor SDK / own loop / durable engine>, because <...>
- What it owns / what we build:

| harness-components row | Framework does it | Framework helps | We build it |
|---|---|---|---|

- Defaults we set explicitly: <caps, checkpointer, recursion or turn limits>
- Exit test answers (5 questions): <...>
- Provider swap: <how, what is logged>

## 3. Loop contract

Status (review mode): keep / change / add

<Reference the architecture doc's contract, or write it: decision contract, gate order, risk tiers, stop conditions, failure classes. Note any runtime additions.>

## 4. Run record and state

Status (review mode): keep / change / add

- Run ID: <issued by / derived from>, scoped to <principal>
- Header fields: <...>
- Event vocabulary: <list, or "as harness-components.md §2" plus additions>
- Typed state: <fields the guard and gate read>
- Store: <which, shared by all workers>; writer rule: <conditional writes on version / one consumer per run>
- Checkpoint schema version and migration rule: <...>
- Retention and redaction: <...>

## 5. Checkpoints, idempotency, approvals

Status (review mode): keep / change / add

- Intent / receipt placement: <...>
- Key per write: <run + action + target, or business key>; lookup before retry: <how>
- Resume rule for an intent without a receipt: <...>
- Approval: fields, lifetime <N min>, digest of <...>, nonce, executor check, pause and execute in separate steps
- Compensation: <reversible steps and reverts; irreversible steps last>

## 6. Budgets and stops

Status (review mode): keep / change / add

| Budget | Number | Basis | Checked | Stored | Warn at | On hit (status, reason) |
|---|---|---|---|---|---|---|
| Steps (framework super-steps or loop iterations) | | | before every step | run state | | `partial`, `max_steps` |
| Model calls | | | before every call | run state | | `partial`, `budget:model_calls` |
| Tool calls | | | before every call | run state | | `partial`, `budget:tool_calls` |
| Tokens or cost | | | before every call | run state | | `partial`, `budget:tokens` or `budget:cost` |
| Wall time (paused during human waits) | | | before every call | run state | | `partial`, `wall_time` |
| Retries per call | | | per failure class | run state | | `escalated`, `retries_exhausted` |

The framework's recursion or turn limit (LangGraph's `recursion_limit`, an SDK's `max_turns`) is a backstop set above the pre-call step guard, not the step budget. Its error maps to `partial` with `max_steps`, never to `failed` or `completed`.

Exit statuses and their sinks (stop reasons from the fixed list in harness-tests.md §4):

| Status | Stop reasons | Sink |
|---|---|---|

## 7. Operator controls

Status (review mode): keep / change / add

- Cancel: <endpoint, where the signal lives, safe points, long-tool cleanup>
- Draft-only: <flag store, read where, propagation time, who flips it>
- Abort: <what is revoked, what is cancelled, snapshot, restart approval>
- Triggers for each level: <...>
- Drill: <schedule, environment>
- Replay: <safe-mode mechanism; experiment vs reproduction; what is recorded to make it possible>

## 8. Service endpoint and deployment shape

Status (review mode): keep / change / add

- Shape: <single service / receiver + queue + workers / scheduled / foreground + background>, because <...>
- Layers: <API / workers / model server>
- Endpoint:

| Call | Request | Response | Errors (problem details types) |
|---|---|---|---|

- Streaming: <SSE / WebSocket / none>; disconnect policy per run type: <...>; output check before release: <...>
- Limits per client: <rate, concurrent streams>
- Shutdown and drain: <...>

## 9. Harness tests and run-record contract

Status (review mode): keep / change / add

| Test | How | Passes when | In CI? |
|---|---|---|---|

- Run-record fields handed to agent-eval-designer: <list or "as harness-tests.md §4">
- Harness bake-off (if choosing between harnesses): <tasks, trials, model held fixed, metrics>

## 10. Decision log

| Decision | Alternatives | Rationale | Revisit when |
|---|---|---|---|

## 11. Handoffs

| To | What |
|---|---|
| agent-architect | <shape questions this design raised> |
| agent-tool-designer | <tool contracts: keys, lookups, receipts, reversibility> |
| agent-threat-modeler | <approval UX and approvers, permission tiers, guardrail content, sandboxing> |
| agent-eval-designer | <harness test slice, run-record contract> |
| agent-ops-reviewer | <tracing backend, alarms, readiness gate, rollout> |

## 12. Risks and open questions

- <...>
