# <System name>: agent architecture

> Status: draft | Mode: design / review | Date: <YYYY-MM-DD>

## 0. Summary

<4 to 6 sentences: what the system does, its overall shape (e.g. "a workflow with one bounded agent step"), agent count, the main bounds, where people approve, and the top open question.>

**First actions:** <the three things to do first, in order>

**Confirm first:** <the 3 to 5 assumptions that would change the design most if wrong, each with the decision it drives>

**Lifecycle:** <stage this doc closes (usually Design); Decide gate items already passed or still open; starting level from the five-factor score, with any factor at 1 named>.

## Stage plan (whole-path requests only; delete otherwise)

| Stage | Calendar weeks | Skills in call order | Runs in parallel | Gate items to pass |
|---|---|---|---|---|

- People outside the team to book on day 1, with lead times: <model risk, security, compliance, labellers, data owners>
- Perspectives and owners: API contracts (agent-tool-designer), tool access, guardrails and security hardening (agent-threat-modeler), harness (agent-harness-designer), evals (agent-eval-designer), context and knowledge (agent-context-designer), cost and operations (agent-ops-reviewer)
- A fixed deadline narrows the scope or the starting autonomy, never the gates.

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

## 4. Loop contract

The numbers and choices the runtime must enforce. The runtime itself (run record and state, checkpoints and resume, cancellation, kill switch and draft-only mode, streaming, serving, deployment shape) is designed with agent-harness-designer from this section.

**Decision contract:** <schema of the planner's output>

**Validation gate:** <checks in order>

**Tools and risk tiers** (contracts designed with agent-tool-designer)

| Tool | Tier | Gate |
|---|---|---|

**Budgets** (mark values provisional until the eval's worst case is known; unknown cost ceiling: state it as an assumption and bound tokens instead; no agent step: the contract applies per workflow run and loop steps = 0)

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

**Exits:** completed / partial / awaiting_approval / handed_off / escalated / failed / cancelled, with the meanings and stop reasons in agent-harness-designer's harness-tests.md §4 (skipped items, such as suppressed or ineligible ones, are recorded outcomes, not statuses): <what each returns and who sees it; the durable sink each non-completed exit lands in. A delivered draft or pack is completed; handed_off is for a pending action someone else decides on their own timeline: which ones, and which event starts the follow-up run>

**Failure handling**

| Failure class | Response |
|---|---|

**Idempotency and versions:** <key for each write from run, action and target, or a business key when more than one run can reach the same target, never a step counter; run-trigger dedupe; current-state checks before money moves; version scheme for regenerated outputs>

**State the runtime must keep:** <what must survive a crash or a human wait (pending approvals, receipts, retry counts); pinned config and peer versions per run; where more than one writer could exist. Store, checkpoint layout and resume: agent-harness-designer>

**Execution mode:** sync / async / triggered / continuous, because <latency, waits; for ordered-stream triggers: retry bounds and failure sink>

## 5. Planning and reasoning

(No agent step: replace this section with one line saying why it is skipped.)

| Agent step | Strategy | Effort | Breadth (N, verifier) | Reflection trigger and cap | Model role size |
|---|---|---|---|---|---|

## 6. Agent topology

- **Decision:** single / multi, because <split-test answers>
- If multi: topology, coordinator (code), message schema and how it evolves, discovery and addresses, context slice per agent, credentials per agent with the denial test, conflict rule, caps, transport and partition key, any direct peer call as a documented exception.
- Single-agent baseline for comparison: <which>

## 7. Human oversight points

| Point | Trigger | What the person sees | Default if no response |
|---|---|---|---|

Client thresholds: <measure, where computed, aggregation rule, band plan below and above>

Definitions used: reversible = <...>; cheap = <...> (per batch for actions repeated at volume)

Batch controls for high-volume actions: <daily cap and ramp; outcome breakers with minimum samples; sampled review with a weekly minimum; kill switch>

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
- Against the non-AI incumbent: <business outcome, randomised arms where possible, minimum gain set in advance; a tie goes to the simpler option>
- Reasoning-effort sweep: <task families, settings>
- Eval set design: agent-eval-designer.

## 10. Decision log

| # | Decision | Alternatives considered | Rationale | Revisit when |
|---|---|---|---|---|

## 11. Handoffs to sibling skills

In lifecycle order (references/lifecycle-map.md, "Order of calls"); each row names the gate item the skill supplies.

| Concern | Skill | Gate item it supplies | What to bring |
|---|---|---|---|
| Business case, data readiness, governance, regulatory and compliance requirements | agentic-business-case | Decide: concreteness, data readiness audit, starting level, business case | |
| Threats, access, guardrails, oversight UX | agent-threat-modeler | Design: threat model, permission tier per action; Prove: red-team pass; Run: judges each widening of autonomy | |
| Model per role | agent-model-selector | Design: model per role | |
| Evals | agent-eval-designer | Decide: eval budget; Build: smoke suite; Prove: held-out gate | |
| Tool contracts, MCP/A2A | agent-tool-designer | Decide: usable APIs; Design: tool boundaries; Build: contracts reviewed; Prove: contract tests in CI | |
| Retrieval, memory, context; document ingestion (OCR, parsing, photo extraction) | agent-context-designer | Build: retrieval and memory designed | |
| Runtime: loop, state, checkpoints, cancellation, kill switch, serving, deployment shape | agent-harness-designer | Build: harness components; Prove: harness tests | |
| Tracing, cost per successful run, readiness, rollout | agent-ops-reviewer | Run: readiness gate, monitoring, written autonomy conditions | |

## 12. Risks and open questions

| Risk or question | Impact | Mitigation or who answers |
|---|---|---|

## 13. Rollout and authority graduation

| Step | Start stage (shadow / suggest / approve / act+notify / act) | Promotion criteria (metric, target, N cases, M weeks) | Rollback trigger | Ceiling (never beyond) | Sign-off |
|---|---|---|---|---|---|

- Shadow period: <duration, traffic share, what is compared with the human decision>
- Model or prompt change: re-validate at the current stage; no automatic promotion.
- Promotion and rollback metrics designed with agent-eval-designer; approval UX with agent-threat-modeler.
