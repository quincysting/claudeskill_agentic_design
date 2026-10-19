# Human oversight: tiers, approvals, escalation, earned autonomy

Autonomy is decided **per action, by code, every time the agent proposes something**, not as a label on the agent
("copilot", "autonomous"). A read-only search, a record update and a payment never share an approval path, and a
confident tool call does not erase that boundary [SYSTEMS ch10].

## 1. Action risk tiers

| Tier | Examples | Default handling | Hard limits (hold even after a human says yes) |
|---|---|---|---|
| Refuse | Tools not on the allowlist; amounts over cap; other tenant's data; anything policy forbids | Deny with a short reason; nobody is asked | n/a |
| Read-only | Search, lookup, list, fetch from allowlisted sources | Act and log | Tenant scoping, rate limits, size caps |
| Reversible write | Draft, create ticket, tag, update a field with history, notify the principal | Ask until the action class has earned autonomy, then act and notify with an undo | Per-action and per-day caps |
| Irreversible or high-value | Payments, refunds, deletions, external email or posts, permission or access changes, workflow transitions, deploys, contract or legal text | Ask every time, whatever the model's confidence [ENTERPRISE ch7] | Amount, volume, recipient and scope caps |

**Two axes: consequence class and permission tier.** The tiers above say what an action can break. A permission tier
says what the agent may do with it: read-only; draft-only (nothing sent or saved); execute with approval of the
specific payload; auto-execute, kept rare and limited to narrow, reversible actions with strong validation and a clear
rollback [PRODGUIDE ch12]. Set both per action, not per agent. The reversibility test picks between the last two: if a
mistake can't be undone quickly, the action needs approval, at least at first [PLAYBOOK ch4]. Enforcement of tiers:
[controls-catalog.md](controls-catalog.md) §2 Access rules.

The ladders in the books line up with this skill's rungs (§5):

| Rung (§5) | Permission tier [PRODGUIDE ch12] | Earned-autonomy stage [PLAYBOOK ch4] | Capability level [PLAYBOOK ch2] |
|---|---|---|---|
| Observe | Read-only | Read-only | None (a shadow run) |
| Suggest or draft | Draft-only | Draft only | L1 prompt assistance, L3 agent with tool access |
| Approve each | Execute with approval | Supervised execution, higher-risk cases | L3 |
| Act and notify with undo | Auto-execute, narrow and reversible | Supervised execution, routine cases | L4 supervised autonomy |
| Bounded autonomy | Auto-execute | Earned autonomy | L4 |

PLAYBOOK's L2 (a fixed workflow) and L5 (coordinated agents) are control-flow and architecture choices, not authority
rungs; they belong to agent-architect. Both PLAYBOOK scales rate the whole agent; keep the rung per action class, since
one level for the whole agent either holds back its safe actions or lets its riskiest one through.

**Where a new workflow starts: the five-factor score.** [PLAYBOOK ch2] scores volume, variability, risk, judgment
required and action scope from 1 to 3 each, where 1 argues for less autonomy. Totals of 5 to 7 suggest level 1 or 2,
8 to 10 level 3, 11 to 13 level 4, and 14 to 15 level 4 or 5 if processes and data are strong. Any single 1 is a
constraint the total can't override. Use the score to pick the starting rung and to answer a sponsor who wants full
autonomy on day one, then set rungs per action class: one refund inside a well-scoring support flow still starts at
approve each.

**Principal and recipients.** The principal is the authenticated person or account the agent acts for, identified
from the session, never from content the agent read. A message to the principal, with the recipient taken by code from
the session or a verified record, can only expose the principal's own data and can earn autonomy like a reversible
write. A message to anyone else is external communication: replies to inbound senders, new recipients, forwards,
calendar events with attendees (the provider emails them), file shares, and push, SMS or chat notifications.

- Email assistant: the mailbox owner is the principal. A reply to whoever wrote in goes to an outsider, so it is
  external communication.
- Support agent: the customer becomes the principal only once verified (a logged-in session, or the address on record
  for the order; never the From header, which can be forged).

External communication defaults to draft-first or delayed send (§3). It can earn autonomy per recipient class
(existing thread participants, the internal domain), never for new external recipients while the run is tainted.
Every reply run is tainted by the message it answers, so one rule has to win: a reply to the existing participants of
the thread whose content tainted the run, carrying only that thread's content (no links, attachments or data from
elsewhere), follows this rule and can earn autonomy per recipient class. Any other destination after taint (new
recipients, forwards, shares, invites) is egress after taint: ask or deny, never promoted.

Upgrade an action to "ask" dynamically when:
- untrusted content has entered the run and the action can send data out (taint);
- this pattern is seen for the first time [ENTERPRISE ch7], or the input looks out of distribution;
- the value crosses a threshold (procurement example: auto-approve under $1,000, several sign-offs above [BUILDAPPS ch13]);
- validation failed, evidence is weak, or policy is ambiguous [SYSTEMS ch11].

Scope matters: a personal agent may send its owner's email alone; a department-wide finance agent may route every action
through approval [BUILDAPPS ch13].

## 2. Routing order (encode exactly this)

1. **Hard limits first.** Allowlist, caps, scoped credentials, budget. Out of bounds → refuse; no approval request is
   created, so neither a persuasive agent nor a hurried reviewer can authorise it [DEFGUIDE ch6], [DEFGUIDE ch12].
2. **Consequence sets the default.** Irreversible or high-value → ask.
3. **Earned trust plus instance routineness decide the middle.** A reversible write runs with notification only if its
   action class is promoted *and* this instance looks routine. Otherwise ask.
4. **Outcomes move the policy.** Approvals, rejections, edits and undos update the trust record per action class.

## 3. Approval gate specification

States: `pending → approved | rejected | expired | escalated`, and `edited`, which goes back through the hard limits
[SYSTEMS ch18]. In this skill an edit closes the approval as `edited` and opens a new one for the edited arguments
(agent-harness-designer uses the same rule).

| Rule | Why |
|---|---|
| Side effect never in the same step as the interrupt; propose, pause, execute in separate steps | On resume the interrupted step reruns from its start, so anything before the pause runs twice [DEFGUIDE ch2] |
| Execution keyed by the write's idempotency key, derived from durable run state as agent-harness-designer sets it (run, action and target, or a business key); the approval ID is stored with the intent and marked used in the same write | Double clicks, retried webhooks, resumed runs and a re-approval after a timeout execute at most once: a new approval gets a new ID, but the write keeps its key |
| The approval binds a digest of the exact action and arguments (one canonical form: agent-harness-designer's harness-components.md §3), an expiry and a single-use nonce; the executor recomputes the digest and refuses a changed, expired or reused approval | An ID stops a double execution, not a changed one. Any change, extra retry or expiry needs a new approval [AISEC repo: part8_multi-agent_harness_spec/safety-governance.md]. Its example default is one invocation within 15 minutes [AISEC repo: part8_multi-agent_harness_spec/agents.yaml]; a template that runs whatever call is on the thread once "approved" shows the gap [RELATED repo: 12-factor-agents/packages/create-12-factor-agent/template/src/server.ts] |
| Irreversible actions use a payload preview, then a confirm question that names the action, the target and the details that matter (for an email: this draft, this recipient, this subject) and asks for a yes or no, never "should I send it?" | Specificity forces a conscious yes [PRODGUIDE ch12] |
| Before asking, the agent lists its assumptions and unknowns; if it isn't sure of the target (which customer, which campaign), it asks a question instead of offering to act | Uncertainty is a stop condition, not something an approval resolves [PRODGUIDE ch12] |
| The request restates the action's permission tier | No silent upgrade goes unnoticed [PRODGUIDE ch12] |
| Edited arguments re-run the hard limits | Otherwise "edit" is a way around the caps |
| Deadline on every request; silence = no; on timeout escalate to the next approver, then expire with nothing executed. The deadline's length is a product choice: write it down as an assumption | No request blocks forever or defaults to yes [SYSTEMS ch18] |
| Checkpoint state durably before pausing | The pause must survive restarts; human wait time is excluded from the agent's time budget [DEFGUIDE ch6] |
| Record approver identity, decision, time, and any override reason | Audit and accountability |
| Separation of duties for the highest tier: requester ≠ approver; two people for the most sensitive actions | One compromised or careless person is not enough |
| Approval request revalidated at execution time | State may have changed while it waited (balance, stock, permissions) |
| The agent can only request; a separate executor identity runs the approved action | A policy engine in front of tools can't see approval state, so the agent's own permit must stop at the request tool ([controls-catalog.md](controls-catalog.md) §2) |

**What the reviewer sees, in this order:** (1) the exact action and arguments: recipient list, amount, SQL, diff;
(2) the evidence the agent used; (3) the gate's reason for asking, written by code; (4) the agent's own explanation,
labelled as written by the agent. Never lead with the agent's narrative: a hijacked agent writes convincing
justifications [DEFGUIDE ch12]. Show plans, steps and status; keep raw reasoning traces out of the approval view.
[AISEC ch10] adds diffs, risks and source provenance on the screen, a clear line between what the agent knows and what
it inferred, and a second channel to confirm critical actions.

**Who sees it:** route to someone qualified to judge that action. Per-command approval protects only people who can
read the command [ILLUSTRATED ch10]; for non-expert users, rely on least privilege and design-time scope instead.

**Approvals sent as links.** A link in an email or a chat message is a pointer, not a credential.
- The approver signs in, and the gate checks that this identity may approve this action class at this value. The
  requester never approves its own request.
- Opening the link shows the review view (below) and decides nothing. Mail scanners, link previews and prefetch open
  links with nobody reading them, so a link that approves when opened approves on its own, and a forwarded link would
  let whoever received it approve. Either is a defect.
- The decision is an explicit action in the signed-in session, bound to the digest of what was shown. The recorded
  approver is the authenticated identity, never whoever held the link.
- If links that approve or execute are already in people's mailboxes, retire them: first disable the action behind the
  old links, then expire the approvals they point at, then review the actions approved without a signed-in approver.
- Mechanics (a read-only GET, an authenticated POST with CSRF protection, the retirement steps, tests):
  agent-harness-designer, harness-components.md §3.

**When the platform already binds the approval.** A forge that ties a review to a commit SHA and dismisses it on a new
push, or a document system that ties a sign-off to a version, already supplies the digest: the SHA or version is it.
Record what it lacks, usually a single-use nonce and an expiry, and add them where you can, for example by closing
approvals older than a set time and asking for a fresh review before the merge runs.

**Delegates as reviewers.** An assistant who approves for the principal (the normal case for executives) is a separate
identity with its own entitlements and approval rights, and is recorded as the approver. The requester never approves
its own request. The capacity check (§4) counts the delegate's review time, not the principal's.

**Mechanisms:** graph interrupt and resume with a checkpointer (LangGraph `interrupt` / `Command(resume=...)`),
draft-then-send, pull-request review, maker-checker, ticket approval. Reuse the approval workflow your organisation
already trusts [ENTERPRISE ch7]. For a tool that needs a human answer mid-call, MCP elicitation keeps the answer out of
the model's hands; form mode must not collect secrets; URL mode sends the user to a consent, payment or password page
whose contents never pass through the model [MCP ch6]. Handle decline and cancel as real outcomes. Asking a person
can also be a tool the model calls for clarification [RELATED repo: 12-factor-agents/content/factor-07-contact-humans-with-tools.md];
a mandatory approval is never that tool, because code raises it from the tier table and the model can't skip it.
Consent screens decay like approvals; keep them rare ([mcp-hardening.md](mcp-hardening.md) §5).

### Sends that can't be undone: draft-first or delayed send

- **Draft-first.** The agent writes to drafts or an outbox and the principal sends. Strongest option; costs one action
  per send, which batching reduces.
- **Delayed send with a cancel window.** The gate queues the send, notifies the principal with the exact recipients and
  content, and sends unless cancelled. The send becomes reversible for the length of the window. A window of seconds,
  like a mail client's undo-send, only catches a human sender's slip; for an agent it must match how quickly someone
  looks at the queue in practice, or it protects nothing. Measure cancel latency in the pilot instead of guessing.
  Until it is measured, the window is unset and sends start draft-first.
- Either way: hard limits re-run at send time, each queued item executes at most once (idempotency key), and a cancel
  that arrives after sending reports the real status.
- Not for payments, deletions or permission changes; those use the approval gate.

## 4. Escalation design

Approval gates are planned (this action class always asks). Escalations are triggered (this case is unusual).
Escalation needs both policy and infrastructure: thresholds per decision type, a destination per trigger, and a payload
telling the receiver what the agent attempted, why it escalated and what is needed to proceed [BUILDAPPS ch13].

Signal order:
1. **Deterministic triggers first:** high-impact action, value threshold, weak evidence, policy ambiguity, risky tool call,
   failed validation, first occurrence of a pattern [SYSTEMS ch11], [ENTERPRISE ch7]. Vague triggers make escalation
   inconsistent and erode trust in the workflow.
2. **Uncertainty second, only once calibrated** and only for the reversible middle tier. Options: agreement across 3-5
   samples of the same input (about five is usually enough, at N times the cost [ENTERPRISE ch6]; one example escalates above roughly 20%
   divergence [BUILDAPPS ch11]), a trained classifier, conformal prediction, out-of-distribution detection.
3. **Do not route on stated confidence** ("I'm 90% sure") until it is calibrated against your labelled outcomes; models
   asked for confidence tend to be overconfident (Xiong et al., ICLR 2024, external), and confidence is not accuracy
   when facts changed after training [ENTERPRISE ch6].

Uncertainty times consequence: score both, escalate above a threshold tuned offline on historical cases
[BUILDAPPS ch11]. The book's example aim is fewer than about 10% of cases reaching a person; treat that as a starting
point, not a measured threshold.

**Capacity check: approvals per day (always do the arithmetic).**
1. For each action class that can reach a person: volume per day × share expected to ask (from the tiers, taint rules
   and expected escalations). The sum is approvals per day. Count each class at its current rung on the autonomy ladder
   (§5), not its target: a class at "approve each" during a pilot asks for every instance. Run the check once per
   rollout stage, since the asks fall only as classes are promoted.
2. Minutes per review: time about 20 real or mock reviews. If you can't, state an assumption and label it. Approvals
   that are reviews of work (code, contracts, long drafts) take minutes, not seconds.
3. Review budget: reviewers × minutes per day each can spend on review.
4. Require approvals × minutes per review ≤ about half the budget. The half is this skill's convention for headroom
   (peaks, incidents), not a measured figure. For a personal assistant the reviewer is the principal: ask how many
   approvals a day they will really read and design to that number.
5. If it doesn't fit, reduce asks with the patterns in controls-catalog §4, cap intake at admission (how many requests
   the agent accepts per day, sized to the review budget), narrow the scope, or delay launch. Don't
   auto-approve to make the numbers work. A time-boxed pilot may run over the budget only with the reviewer's written
   acceptance and an end date. After launch, watch approval latency (§8).

## 5. Earned autonomy (per action class, not per agent)

Ladder: **observe (shadow) → suggest or draft → approve each → act and notify with undo → bounded autonomy.**

- **Observe:** the agent shows what it would have done; nothing executes. This produces the comparison data for the
  first promotion [AGENTICAI ch10]. A shadow can't run flows that ask users for approval without exposing them; use
  replayed or synthetic responses there [BUILDAPPS ch11].
- **Promotion gates:** measured rates over a minimum number of cases, fixed before the pilot: shadow agreement with
  human decisions, draft edit rate, approval rejection rate, undo rate, incidents. Real example: a Copilot rollout
  expanded from 50 to more than 400 engineers only after a 33% suggestion-acceptance rate and 72% developer
  satisfaction met preset thresholds [BUILDAPPS ch13]. Calendar-based promotion ("trusted after three months") is an
  anecdote, not a gate.
- **Move-up conditions in the books, as a spread.** [PLAYBOOK ch2] asks for about 80% of outputs approved without
  changes, sustained 30 to 60 days (its summary says at least 30), plus written rules covering what the agent may now
  do on its own and a plan for recovering when those actions fail. [PLAYBOOK ch4]'s stages use 85% over 30 or more days to leave
  draft-only and 90% over 60 or more days to leave supervised execution. The spread from 80 to 90% shows the numbers
  are judgment, not measurement, so don't quote one as the book's rule. Keep the two preconditions (written rules,
  rehearsed recovery plan) and add the case count the books leave out: 30 days at five cases a week is about 20 cases,
  too few to tell 80% from 65%. The defaults below supply it.
- **Default thresholds** (this skill's convention, not a measured standard; replace with the owner's risk appetite):
  - Minimum cases from the rule of three: with zero failures in n cases, the 95% upper bound on the true failure rate
    is about 3/n. Pick n = 3 ÷ the failure rate you can tolerate: 100 clean cases bound it near 3%, 300 near 1%. Start
    with 100 for reversible classes and 300 for low-value sub-classes of irreversible actions, over at least two weeks
    of real traffic.
  - Set the ceiling v of a low-value sub-class from a loss budget: v is the highest amount for which (daily volume of
    actions at or under v) × v × (3 ÷ n) stays within the loss the owner accepts per day, where n is the clean-case
    count above. The owner signs v; actions above it stay at "ask every
    time".
  - Zero severe failures in the window (wrong recipient, over a limit, data exposed, unauthorised action), and a
    substantive edit or rejection rate no worse than the owner accepts from a person doing the same work.
  - Demote on any severe failure, or when the rejection or undo rate over the last n cases exceeds twice the rate at
    promotion.
- **Demotion is automatic and skips levels:** an error-budget breach drops the action class straight back to "approve
  each" or pauses it [MESH ch13]. Keep sampling audits after promotion; one-off certification is dangerous [ENTERPRISE ch6].
- **Re-certify on change:** new model, prompt, tool version or data source resets the evidence for affected classes.
- **Trust repair:** after a visible mistake, provide a way to restrict, reset or retrain, and say so to users
  [BUILDAPPS ch13].

Human roles shift as policy matures: executor (checks every output) → reviewer (spot-checks exceptions) →
collaborator → governor (sets policy, audits) [BUILDAPPS ch13]. Each needs its own interface.

## 6. Calibrated trust and the user's controls

- Calibrated trust matches reliance to actual reliability on a task type; miscalibration either way harms performance
  [ENTERPRISE ch7]. Shared dashboards of agent and human accuracy help teams calibrate [AGENTICAI ch10].
- Tell users what the agent can do, what it is doing now, which stage a long task is at and when to expect an update.
  Fail with an explanation and a next step, and keep the user's progress [BUILDAPPS ch3].
- Show a confidence number to users only after it is calibrated.
- **Autonomy slider** (Manual / Ask / Agent) moves inside a ceiling set by policy: users may always lower autonomy;
  raising it above an action's tier is not their call; automatic demotion overrides both [BUILDAPPS ch3], [MESH ch13].
  A user-controlled dial is an adoption tool, not a safety control.
- Let users set notification frequency, channel and thresholds; interrupt for high stakes only.

## 7. Stop controls and operator surfaces

- **Disengage button:** stops all autonomous operation and falls back to a defined manual or deterministic mode
  [ENTERPRISE ch6]. Server-side (revoke credentials, halt the queue), reachable from a phone, logged, tested in drills.
  In the inbox-deletion incident remote stop attempts failed until the owner reached the machine [ENTERPRISE ch7].
- **Agent-side stop:** the agent can say it cannot proceed safely and hand control back.
- **Operator workbench:** fleet health, error rates, alerts; start, stop, pause, schedule. Operators control execution
  without default access to content; elevated access is granted, time-boxed and logged [MESH ch8].

## 8. Oversight metrics (watch for rubber-stamping and fatigue)

| Metric | Warning sign |
|---|---|
| Approval latency | Decisions in one or two seconds are rubber stamps |
| Rejection and edit rate | Near zero for months: either the tier can be promoted or nobody is reading |
| Escalation rate vs reviewer capacity | Queue growth, expiries |
| Undo rate after act-and-notify | Rising: demote the class |
| Override rate (humans reversing completed actions) | Leading indicator of drift [MESH ch13] |

Field reference (external, Anthropic 2026-02): experienced users auto-approved more and also interrupted more;
effective oversight means being able to intervene when it matters, not approving every action.

## 9. Regulation pointer (as of 2026-10; hand details to agentic-business-case)

EU AI Act Article 14 expects high-risk systems to let overseers understand capabilities and limits, stay aware of
automation bias, decline or override outputs, and stop the system into a safe state; some biometric uses need two
qualified people to verify. The Annex III obligations' application date has moved before; check the current timeline.
