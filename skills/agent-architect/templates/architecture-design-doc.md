# <System name>: agent architecture

> Status: draft | Mode: design / review | Date: <YYYY-MM-DD>

## 0. Summary

<4 to 6 sentences: what the system does, its overall shape (e.g. "a workflow with one bounded agent step"), agent count, the main bounds, where people approve, and the top open question.>

**Confirm first:** <the 3 to 5 assumptions that would change the design most if wrong, each with the decision it drives>

## 1. Responsibility and scope

- **Responsibility:** Given <input>, produce <output> that <consumer> can <use>.
- **Success criteria:** <measurable: accuracy or acceptance rate, p95 latency, cost per task, % escalated>
- **Non-goals:** <what it will not do in v1>
- **Assumptions:** <each one, marked so it can be confirmed>

## 2. Step map

| # | Step | Shape | Authority | Owner component | Why (run-time discovery, if agent) |
|---|---|---|---|---|---|
| 1 | | code / call / workflow / agent | act / act+notify / approve / suggest | | |

Steps marked "build both": <list, with the comparison in §9>.

## 3. Architecture

<Mermaid or text diagram: request → orchestrator → model → gate → tools → backends; state store; trace store; approval queue.>

**Ownership**

| Responsibility | Owner |
|---|---|
| Decide next action | |
| Validate proposal | |
| Authorise (risk tier) | |
| Execute tools | |
| Store state | |
| Record trace | |
| Stop | |

**Pattern(s):** <skeleton pattern + pattern inside each agent step, with one line of why>

**Where the loop lives:** embedded / orchestrator service / durable engine, because <...>

## 4. Control loop

**Decision contract:** <schema of the planner's output>

**Validation gate:** <checks in order>

**Tools and risk tiers** (contracts designed with agent-tool-designer)

| Tool | Tier | Gate |
|---|---|---|

**Budgets** (mark values provisional until the eval's worst case is known; unknown cost ceiling: state it as an assumption and bound tokens instead)

| Budget | Value | Basis |
|---|---|---|
| Loop steps | | |
| Model calls | | |
| Tool calls | | |
| Tokens / cost per run | | |
| Wall clock | | |
| Breadth (docs, chunks, findings) | | |
| Re-asks / review rounds | | |

**Stop conditions:** <goal met, enough info, no progress rule, resource limits>

**Exits:** completed / partial / awaiting_approval / handed_off / escalated / failed: <what each returns and who sees it; which downstream decisions end the run with handed_off and which event starts the follow-up run>

**Failure handling**

| Failure class | Response |
|---|---|

**Idempotency and versions:** <key scheme for each write; run-trigger dedupe; current-state checks before money moves; version scheme for regenerated outputs>

**State and checkpoints:** <state schema fields; checkpoint points; run ID; pinned config>

**Execution mode:** sync / async / triggered / continuous, because <latency, waits>

## 5. Planning and reasoning

| Agent step | Strategy | Effort | Breadth (N, verifier) | Reflection trigger and cap | Model role size |
|---|---|---|---|---|---|

## 6. Agent topology

- **Decision:** single / multi, because <split-test answers>
- If multi: topology, coordinator (code), message schema, context slice per agent, conflict rule, caps, transport.
- Single-agent baseline for comparison: <which>

## 7. Human oversight points

| Point | Trigger | What the person sees | Default if no response |
|---|---|---|---|

Client thresholds: <measure, where computed, aggregation rule, band plan below and above>

Definitions used: reversible = <...>; cheap = <...>

**Decision records** (regulated or adverse decisions): <fields: decision, reason codes from fixed list, evidence refs, rule/policy version, model/prompt versions, recommender, decider, override reason>

(Approval UX, permissions and threat model: agent-threat-modeler. Regulatory requirements: agentic-business-case.)

## 8. Estimates

| Path | Share of volume | Model calls (typical / worst) | Latency p50 / p95 | Cost per task | Volume/day → daily cost |
|---|---|---|---|---|---|

(No prices known: give calls and tokens per path, the weighted average, and the ratio to the current system; the metered eval replay gives the real cost.)

**At volume:** tokens per case (typical / worst) <...>; peak arrivals/min <...>; concurrency <...>; required RPM / TPM vs provider limits <...>; queue wait at peak <...>; cacheable prefix <...>

**Against the incumbent:** <today's minutes and cost per case vs model + infra cost + remaining human review minutes; error and rework rates>

Reliability note: <chain length, gates, direction of the arithmetic>

## 9. Validation plan

- Baseline vs proposed per "build both" step: <cases, scorer, primary metric, guardrails, minimum gain and how it was derived, label adjudication for noisy ground truth>
- Reasoning-effort sweep: <task families, settings>
- Eval set design: agent-eval-designer.

## 10. Decision log

| # | Decision | Alternatives considered | Rationale | Revisit when |
|---|---|---|---|---|

## 11. Handoffs to sibling skills

| Concern | Skill | What to bring |
|---|---|---|
| Tool contracts, MCP/A2A | agent-tool-designer | |
| Retrieval, memory, context; document ingestion (OCR, parsing, photo extraction) | agent-context-designer | |
| Evals | agent-eval-designer | |
| Tracing, cost, serving | agent-ops-reviewer | |
| Threats, guardrails, oversight UX | agent-threat-modeler | |
| Model per role | agent-model-selector | |
| Business case, governance, regulatory and compliance requirements | agentic-business-case | |

## 12. Risks and open questions

| Risk or question | Impact | Mitigation or who answers |
|---|---|---|

## 13. Rollout and authority graduation

| Step | Start stage (shadow / suggest / approve / act+notify / act) | Promotion criteria (metric, target, N cases, M weeks) | Rollback trigger | Ceiling (never beyond) | Sign-off |
|---|---|---|---|---|---|

- Shadow period: <duration, traffic share, what is compared with the human decision>
- Model or prompt change: re-validate at the current stage; no automatic promotion.
- Promotion and rollback metrics designed with agent-eval-designer; approval UX with agent-threat-modeler.
