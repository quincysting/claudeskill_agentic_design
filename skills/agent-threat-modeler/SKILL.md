---
name: agent-threat-modeler
description: Threat-model an AI agent and design its defences, or review an existing agent's security and oversight with prioritised fixes; also the red-team pass at the Prove stage. Owns tool access, guardrails and security hardening. Covers Rule of Two triage, STRIDE per element, prompt injection, permission tiers and scope-entitlement checks per action, policy gate, credentials and token exchange, MCP hardening (definition pinning, supply chain, OAuth, consent), guardrail layers, sandboxing, OWASP Agentic Top 10 and MAESTRO mapping, and oversight (approvals bound to the exact action, escalation, earned autonomy). Use for "threat model my agent", "prompt injection", "is it safe to give my agent access to X", "guardrails", "sandbox code execution", "approval flow", "harden my MCP server", "red-team plan", "agent security review". Not for exploits or payloads, tool interface design (agent-tool-designer), harness runtime (agent-harness-designer), eval datasets (agent-eval-designer) or governance (agentic-business-case).
---

# Agent Threat Modeler

This skill produces a threat model plus controls plan for an agent design, or a security-and-oversight review of an
existing agent with prioritised fixes. The stance: **the model proposes, code disposes.** Assume any text that reaches the model can
steer it, bound what a steered model can do with deterministic controls outside the model, then layer detection,
human oversight and recovery on top. Defensive only: name attack classes and the property a test checks; never write
working payloads.

**Perspectives owned:** tool access, guardrails and security hardening. Each perspective has one owning skill; the
end-to-end lifecycle map (stages, perspectives, stage gates) is lifecycle-map.md in the agent-architect skill's
references. **Stage:** this skill starts at Design, where the threat model, access rules and guardrail design are
decided before tool contracts and the harness are built, and returns at Prove as the red-team pass against the built
system ([red-team-test-plan.md](references/red-team-test-plan.md)). Gate items it supplies:
- *Design:* a threat model with the Rule of Two triage and a permission tier for every action (Steps 1 to 10);
- *Prove:* the red-team pass is done and its Critical findings are fixed (Step 11);
- *Run:* each widening of autonomy is judged per action class (Step 10, earned autonomy).

## When to use / when not to

Use when:
- designing an agent that calls tools, reads untrusted content, runs code, browses, keeps memory or talks to other agents;
- someone asks whether it is safe to connect the agent to a mailbox, database, repo, payment API, browser or shell;
- reviewing agent code or config for security or approval flows before launch, after an incident, or after a model,
  tool or data-source change;
- choosing a sandbox tier, guardrail stack, approval flow or autonomy policy;
- mapping an agent to OWASP for an audit.

Don't use, or hand off:
- Chat feature with no tools, retrieval or memory: do a light pass with the LLM Top 10 table in
  [owasp-mapping.md](references/owasp-mapping.md) only.
- Requests for jailbreaks, injection strings or exploit code: decline that part; offer technique classes and the
  harness tools in [red-team-test-plan.md](references/red-team-test-plan.md).
- Tool schemas, contracts and catalogue governance → agent-tool-designer (this skill still decides which tools need
  gates and which permission tier each action gets).
- The agent's runtime (loop, state, checkpoints, budgets, streaming, kill-switch mechanics, safe-mode replay) →
  agent-harness-designer. This skill says which stops and gates must exist and tests them.
- Context, retrieval and memory architecture → agent-context-designer.
- Red-team datasets, graders and eval harness → agent-eval-designer (hand over the test plan from Step 11).
- Live-fleet monitoring, incidents, cost → agent-ops-reviewer.
- Choosing models → agent-model-selector. Overall pattern or topology → agent-architect.
- Regulation, governance boards, ROI → agentic-business-case.

## Inputs to gather first

Ask for what you can't find. If the user gives nothing, ask at most five questions (1, 2, 4, 5, 9 below) and proceed
on stated, conservative assumptions: unknown sources are untrusted, unknown tools have side effects, unknown
credentials are broad.

When you can't ask, put every assumption in the template's Assumptions row and tag findings that depend on one
`(assumed)`. "Unknown means riskier" applies to the properties of components that exist (a tool's scope, a source's
trust). A component nobody mentioned (memory, other agents) becomes an open question marked N/A pending confirmation;
don't model it into existence.

| # | Question | Where to look in code |
|---|---|---|
| 1 | What does the agent do, for whom? Public, internal, multi-tenant? Who approves actions and can they judge them? | README, system prompt, auth middleware |
| 2 | Every tool or action and its side effect; which MCP servers, first- or third-party, pinned? Do you also run or publish an MCP server? | Tool registries, `@tool` decorators, function schemas, `.mcp.json` / client MCP config, server deployment manifest |
| 3 | What private data can it read, and whose? | DB accounts, API scopes, retrieval filters |
| 4 | Every source of text that reaches the context (user, web, email, files, RAG, tool results, tool descriptions, memory, other agents, screen) | Loaders, fetch tools, RAG pipeline, memory read path |
| 5 | Every way data can leave (HTTP, email, chat, PRs/comments, webhooks, rendered markdown images/links, file shares, third-party APIs, log shipping) | Outbound clients, UI renderer, logging config |
| 6 | How tools authenticate; whose identity; token scope and lifetime; every live entry point to the agent (endpoints, aliases, deployed versions) and the authenticator on each | `os.environ`, `api_key`, `token`, env passed to subprocesses or stdio servers, secrets in prompts; the live endpoint and version list and its authorizer config |
| 7 | Does it write or run code, use a shell, or drive a browser? Where does that run? | `exec(`, `eval(`, `subprocess`, `shell=True`, Docker/E2B config, browser profile setup |
| 8 | What persists across sessions, who can write it, is it shared across users? | Memory store, vector DB namespaces, "lessons learned" files |
| 9 | What runs without a human today; how approvals work; how to stop it | Interrupt/approval code, Slack/Teams buttons, kill switch, feature flags |
| 10 | Existing controls: gates, guardrails (and whether each fails open or closed), budgets, rate limits, audit logs; who can change or switch them off | Middleware, gateways, policy files; the live gate mode and attached rules; roles allowed to update them |
| 11 | Constraints: latency budget, data residency, regulation, worst outcome the owner cannot accept | Ask |

If the system runs on AWS, map each decision with
[references/aws-implementation-notes.md](references/aws-implementation-notes.md).

## Procedure

**1. Pick mode and scope.** New design → fill [templates/threat-model.md](templates/threat-model.md), whose section
numbers match the steps below. Existing code you can read → fill
[templates/security-review.md](templates/security-review.md). If it is unclear whether code exists, or the system is
partly built, use the threat-model template and mark every control *existing* or *planned*. For "is it safe to give my
agent access to X", use the short form in Output. Model one agent or flow at a time; for multi-agent systems, model
each agent, then the links between them.

**Rule of Two triage**, before the inventories: does the job need private data, untrusted content and the ability to
act externally at the same time? If no run ever holds all three, name the leg that is absent by design and keep it
absent in code. If the job needs all three, every such flow needs a leg cut per request, or human oversight backed by
controls that hold without the reviewer ([controls-catalog.md](references/controls-catalog.md) §4). Record the answer
in the scope table; Step 5 repeats the check per flow.

**2. Write the worst outcomes.** Three to seven concrete "must never happen" statements tied to assets: "customer PII
reaches a third party", "refund over the cap without a person", "production rows deleted", "agent acts as another
tenant", "secrets leave the sandbox". These set impact for every later step.

**3. Build the inventories.** Capability inventory: one row per tool with side-effect class (read / reversible write /
irreversible or high-value / egress / code execution / permission change), data reached, credential and scope, whether
its output brings untrusted content, and the gate today. Input inventory: source → who controls it → trust (trusted:
your code and config; semi: authenticated users; untrusted: everything else, including tool results, tool descriptions,
retrieved documents, memory written by runs that read untrusted content, and other agents). Unknown → riskier class.
Entry-point inventory: every endpoint, alias and deployed version that can invoke the agent, its authenticator, and who
holds invoke rights. Authentication can be set per version, so an old version may have none.

**Challenge the premise when it is the risk.** If the stated architecture is itself a finding (the agent runs on the
user's own broad OAuth token, an admin key, a personal browser session, a shared service account, or an "act as user
X" API where the user is a string the caller asserts), say so in the
summary, propose the alternative (a separate agent identity with narrowly scoped delegated tokens, or a proxy that holds
the token and exposes only intent-level operations when the provider's scopes are too coarse; see
[controls-catalog.md](references/controls-catalog.md) §3), and still model the system as specified so the owner sees
the consequence.

**4. Draw trust boundaries.** A mermaid or text flow: inputs → context → model (untrusted side) → proposal →
enforcement point → tools, sandbox, memory or human → results back as data. Mark where enforcement lives in code today.
Draw it as a data-flow diagram and apply STRIDE to every process and flow
([threat-catalog.md](references/threat-catalog.md) §STRIDE per element).
No single enforcement point between proposals and side effects is automatically finding #1, and so is a tool backend
that can be called without passing through it ([controls-catalog.md](references/controls-catalog.md) §2).

**5. Run the lethal trifecta check per flow.** For each flow ask: private data? untrusted content? external channel
(including URLs, rendered images, created artefacts)? All three in one run means one injected instruction can exfiltrate.
Choose which leg to cut for that flow and how, in code. See [threat-catalog.md](references/threat-catalog.md) §The
lethal trifecta and [controls-catalog.md](references/controls-catalog.md) §4. When the product's purpose needs all three
legs (an inbox or browser assistant), keep the cut and use the prompt-reduction patterns in the same section; count the
approvals per day it would cause.

**6. Trace propagation paths.** For each untrusted source, starting with trifecta flows, walk source → plan → tool call
→ effect → persistence → recovery, and at each hop ask the four questions: Reach, Gate, Persistence, Recovery
([threat-catalog.md](references/threat-catalog.md)). Trace at least one path with no attacker (destructive shortcut,
double execution, safety instruction lost to compression, cost runaway). Record each gap.

**7. Fill the threat register and map to OWASP.** Use the T1-T21 entries in
[threat-catalog.md](references/threat-catalog.md). Map each threat to ASI and LLM IDs with
[owasp-mapping.md](references/owasp-mapping.md). Every ASI01-ASI10 item ends as covered (built), covered (planned), gap,
or N/A with a reason; a design-mode register never reads as built coverage.
Then cross-check coverage against the MAESTRO layers and the CoSAI risk map in the same file.

**8. Prioritise.** Apply the first rule that matches:

| Priority | Rule |
|---|---|
| P0 (block launch / fix now) | A path from untrusted input to an irreversible, egress, code-execution or cross-tenant effect with no deterministic control; secrets reachable by the model; model code on the host; no way to stop the agent; a network-reachable bind (0.0.0.0 or a public interface) whose authentication is unknown, written `P0 (assumed)` |
| P1 (before launch) | Control exists only in the prompt, or only as human approval without hard limits; shared or broad credentials; unvalidated persistent memory; no audit of tool calls; controls that the role running the agent can switch off; an audit log or kill switch that is missing or unverified (with no way at all to stop the agent, P0) |
| P2 (next iteration) | Defence-in-depth gaps: no scanner on tool output, missing budgets on low-impact tools, no red-team regression, weak monitoring |
| P3 (hygiene) | Documentation, naming, log retention, minor hardening |

Within a level, rank by worst outcome (Step 2), then exposure (public > authenticated > internal). Don't invent numeric
risk scores; if the organisation has a scoring scheme (DREAD, for example), use it to order findings within a level,
never to move one across levels. Findings often share a root cause (usually: no single
enforcement point). Keep them as separate findings so each can be tested, but group the fixes: one gate can close
several. A P0 that depends on an unverified assumption is written `P0 (assumed)` and still blocks until the assumption
is checked or the control exists. If the check shows the assumption is false, re-rank or close the finding; if true,
it becomes a plain P0 and blocks until its control exists. Verdict, in both modes: any open P0 → Block (design mode: don't build or launch until
the P0 controls are in the plan); only P1s, each with an owner and date → Ship with conditions; P2/P3 only → Ship.

**9. Choose controls, architecture before detection.** Work down this list and stop when the residual risk for each
P0/P1 path is bounded by something the model cannot bypass ([controls-catalog.md](references/controls-catalog.md)):
1. Remove or narrow the capability (intent-level tools, read-only accounts, scoped resources). Ask whether a step
   needs the model at all: a fixed report or lookup is safer as plain code.
2. One deterministic policy gate on every side effect: default-deny allowlist, schema and semantic argument checks,
   hard limits, budgets, taint and resource-scope rules, risk-tier routing, audit. Backends accept calls only from
   the gate; state checks stay in the handlers; rules ship log-only, then enforced (controls-catalog §2).
3. Access rules per action, enforced by the gate: a permission tier per action (read-only, draft-only, execute with
   approval, auto-execute), every call authorised as granted scope ∩ user entitlements per object and function,
   separate identities to recommend, prepare and execute, and a scope gate with a circuit breaker on outbound and
   state-changing steps (controls-catalog §2 Access rules).
4. Credentials and identity: broker injects secrets; per-agent identity; user identity from a verified token, never
   an asserted ID; short-lived scoped tokens, exchanged per hop; no pass-through (controls-catalog §3).
5. MCP hosts and servers, when in scope: tools resolved as `server::name`, definitions pinned per session, supply
   chain, the server's front door, token acceptance and exchange, consent, sampling, elicitation and roots, runtime
   defaults ([mcp-hardening.md](references/mcp-hardening.md)).
6. Isolation for code and computer use, and for parsers of untrusted files (attachments) and third-party MCP
   servers: pick the tier from the quick-pick table in [sandboxing.md](references/sandboxing.md); call it a sandbox only
   if it bounds files, network, time and memory.
7. Injection containment where no leg can be cut: plan-then-execute, dual LLM, map-reduce, action selector.
8. Memory hygiene: validated writes, provenance, tenant isolation, purge path; notes agents leave for other agents
   count as memory.
9. Guardrails in three layers (prompt, screening, hard limits), the prompt never the control: input, tool-output and
   output checks; provenance gate and egress allowlist; nothing released before its verdicts; fail open or fail
   closed declared per check ([guardrails.md](references/guardrails.md)).
10. Human oversight (Step 10).
11. Detection and recovery: audit log (credential issuance included), behavioural baselines, per-agent kill switch,
    rotation, restore, and protection of the controls themselves, tests and policy files included (controls-catalog
    §10). The kill switch's runtime mechanics are designed in agent-harness-designer.

For each control write what it stops, where it lives, whether the model can bypass it, who can switch it off, and its
cost. A prompt
instruction never counts as the control for a P0 or P1 path. Give every control an ID (C-01, C-02...). Oversight
mechanisms (approval gates, hard limits, the kill switch, the autonomy ladder) are controls too and get IDs here; the
register, oversight table and tests refer to controls only by IDs defined in this plan.

**10. Design oversight** ([human-oversight.md](references/human-oversight.md)):
- Give every action a tier: refuse / act and log / act and notify with undo / ask. Irreversible, financial,
  external-communication and permission-changing actions always ask, behind hard limits that hold after a yes. Pair
  each with its permission tier, and pick the workflow's starting rung from the five-factor score
  ([human-oversight.md](references/human-oversight.md) §1).
- Identify the principal (the authenticated person the agent acts for). Messages to anyone else, including calendar
  invites with attendees, shares and notifications, are external communication. For sends that can't be undone, say
  whether you use draft-first, a delayed-send window with cancel, or approval
  ([human-oversight.md](references/human-oversight.md) §3).
- Specify the approval gate: states, deadline, silence means no, edits re-run the limits, side effect in a separate
  step, execution keyed by the write's idempotency key from durable run state (the approval ID is stored with the
  intent and marked used in the same write), reviewer view that leads with the exact action. The approval binds a digest of
  the exact action and arguments, an expiry and a nonce, and the executor refuses a changed, expired or reused one.
  Irreversible actions get a payload preview and a confirm question naming action and target; an agent unsure of the
  target asks instead of offering to act.
- Escalation triggers: deterministic first; uncertainty only once calibrated. Route to a qualified reviewer and
  compute approvals per day against reviewer time (method in §4 of the same file).
- Earned autonomy per action class: current rung, promotion metric and threshold, automatic demotion, re-certification
  on change. Use the default thresholds in §5 unless the owner sets their own. The books' move-up figures are a spread
  (80 to 90% approval over 30 to 60 days), not one rule; keep their preconditions: written rules for the new actions and
  a rehearsed recovery plan.
- A stop control that is server-side, remote and drilled, with a defined safe mode.

**11. Plan verification.** Write one test per P0/P1 path plus ASI coverage using the schema in
[red-team-test-plan.md](references/red-team-test-plan.md): technique class, injection point, expected trace property.
Include the ASI seed suite, the authorization tests (the same call under two identities), the harness-level abuse tests
(agree them with agent-harness-designer) and, when MCP is in scope, the deploy probes. Add drills for the kill switch,
secret rotation and memory restore. Hand the table to agent-eval-designer. At Prove, this plan is the red-team pass.

**12. State residual risk and owners.** What remains after controls, who accepts it, and what triggers a re-review:
new tool, new data source, new user population, model or prompt change, incident.

**Review mode:** run every step against the real code and config; Steps 9-11 become the Fix and Tests columns of the
review. Every finding needs evidence (file:line, config key or observed behaviour), a concrete fix and where it goes,
and an effort estimate (S/M/L). Read the live configuration, not only the infrastructure code: full-replace updates
and setup wizards change security settings without a code change. Say what you could not verify. Where a number you need is missing (refund volume,
reviewer headcount), show the arithmetic with a labelled assumption and ask for the real figure.

## Decision guide

**Situations**

| Situation | Recommended | Why | Watch out for |
|---|---|---|---|
| Agent reads untrusted content, holds private data, can send out | Cut one leg per run: taint-gated egress, recipient/domain allowlist, request-scoped tokens | One injected instruction is enough otherwise | Hidden channels: URL query strings, rendered images, PR or comment creation |
| Agent must act on what untrusted content says | Plan-then-execute or dual LLM | Untrusted text can change values, not which tools run | Utility loss; test that the quarantined model has no tools |
| Tool needs a credential | Broker injects it at execution | The model never sees it, so it can't leak it | stdio servers inheriting the full environment |
| Free-form SQL or shell is requested | Intent-level tools; if unavoidable, read-only replica, bound parameters, destructive-clause rejection, alerts | Every reasoning error becomes an outage otherwise | "Read-only" accounts that can still call functions with side effects |
| Third-party MCP server | Resolve as `server::name`, pin its version and every approved definition (recheck each session, halt on drift), show descriptions, re-consent on tool-list change, minimal env, gate its tools like your own | Descriptions and results are injection vectors, and an approved server can change later | Treating MCP auth as an injection defence; it isn't one |
| Running or publishing an MCP server | Auth middleware on every request including `tools/list`, scope per tool, the four-check token pipeline then exchange, loopback bind, Host check, signed releases, an anonymous probe on every deploy | Most of the risk sits in defaults | A manifest that declares auth while the handler never checks it |
| Agent acts on records for a user | Permission tier per action; authorise as granted scope ∩ user entitlements per object and function; separate execute identity | Checking only the agent's scope reproduces broken object- and function-level authorization | An agent service account that can read everything |
| A guardrail runs in parallel with generation, or output streams | Release nothing until every verdict is in; buffer or check in windows; the guard returns a blocking decision | Otherwise whichever finishes first decides what the user sees | Pipelines that return the output together with a failed result |
| Several agents cooperate | Per-agent identity, token exchange per hop (same subject, next-hop audience, scope never widens), mTLS or audience-bound tokens, schema'd signed messages, receiver-side gate, hop limits | Attribution, revocation, no privilege laundering | Shared service account; forwarding the received token; delegation that widens rights |
| Gate is a policy engine in front of tools (managed gateway) | Backends callable only by the gate; state checks in handlers; every tool given an explicit allow; rules shipped log-only, then enforced; mode switch held by a separate role | A gateway sees identity and arguments, not the record's real state | Default deny breaking reads; a forbid on a missing field never firing; one permission that turns enforcement off |
| Long-term or shared memory | Validated writes with provenance, tenant isolation, purge and restore | Poison outlives the session | Saving tainted runs as exemplars |
| Guardrail latency budget is tight | Deterministic inline; small model only on the uncertain band; LLM judge async | Regex is microseconds, LLM checks hundreds of ms | Blocking whole answers where redaction would do |
| Users can't judge commands | Least privilege and sandboxing, not per-command approval | Approval protects only experts | Approval prompts as a liability shield |
| Approval is the only barrier on a high-value action | Add hard caps that hold after yes, action-first reviewer view, approval bound to a digest of the exact arguments | The agent can talk the reviewer into it | Persuasive agent narratives shown first; executing whatever call is on the thread |
| The product's purpose needs all three legs (inbox, browser assistant) | Keep the egress cut; reduce prompts with structured extraction or a quarantined summariser, per-recipient-class autonomy, batched drafts | Taint-gating alone makes nearly every send ask | Rubber-stamping; summaries of untrusted text are still untrusted |
| Agent opens links found in untrusted content | Reader service: links referenced by ID, no model-built URLs, every redirect hop re-checked, no credentials, one-click links to a human, egress proxy | Opening a link is a send and can perform an action | Unsubscribe, confirm, magic-login and tracking links |
| Stated architecture is the risk (agent on the user's broad token) | Name it as a finding; scoped delegated token or a token-holding proxy | Every other control sits on top of that token's reach | Provider scopes too coarse to separate read from send |

**Sandbox quick pick** (details in [sandboxing.md](references/sandboxing.md))

| Code source | Minimum tier |
|---|---|
| Model composes your own governed tools only | Capability-scoped interpreter; each host call through the gate |
| Model code on internal data, no untrusted input in the run | Hardened container: non-root, read-only root, one writable dir, network off |
| Code shaped by untrusted content, user uploads, runtime installs | gVisor or microVM, or an ephemeral cloud sandbox if data may leave |
| Browser or desktop computer use | Dedicated VM/container, separate profile with no personal sessions, domain allowlist, confirmation for consequential actions |
| `exec`/`eval` on the host | Never |

**Oversight tier per action**

| Action class | Default | Hard limit | Can autonomy be earned? |
|---|---|---|---|
| Outside policy | Refuse | n/a | No |
| Read-only | Act and log | Tenant scope, rate, size | n/a |
| Reversible write | Ask, then act and notify with undo once earned | Per-action and per-day caps | Yes, per action class, measured |
| Reply to the principal (recipient taken by code from the authenticated session or a verified record, never from inbound content; only the principal's own data) | Draft then send; act and notify once earned | Fixed recipient, per-thread cap | Yes, per action class |
| Message to anyone else: replies to inbound senders, new recipients, calendar invites with attendees, shares, notifications | Draft first, or delayed send with a cancel window | Recipient-class allowlist, rate cap, content limited to the current thread | Per recipient class, measured; never for new external recipients while tainted |
| Any egress after untrusted content entered the run, except a reply in the tainting thread (below) | Ask, or deny | Recipient/domain allowlist | No while tainted; reduce prompts with [controls-catalog.md](references/controls-catalog.md) §4 |
| Irreversible, financial, deletion, permission change | Ask every time | Amount, volume, scope caps | Only low-value sub-classes inside caps |

Which row wins after taint: a reply to the existing participants of the thread whose content tainted the run, carrying
only that thread's content (no links, attachments or data from elsewhere), follows the message row and can earn
autonomy per recipient class. Any other destination after taint (new recipients, forwards, shares, invites) follows
the taint row: ask or deny, never promoted.

Who is the principal? For an email assistant it is the mailbox owner, so a reply to an inbound sender goes to an
outsider: "message to anyone else", not "reply to the principal". For a support agent the customer is the principal
only once verified (a logged-in session, or the address on record for the order, never the From header).

**Escalation signal**

| Signal | Use |
|---|---|
| Consequence, value, policy ambiguity, failed validation, first-time pattern | Primary, deterministic |
| Agreement across 3-5 samples, trained classifier, conformal or OOD detection | Secondary, reversible middle tier, after calibration |
| Model's stated confidence | Don't route on it until calibrated on your labelled outcomes |

## Output

Fill the template for the mode. Rules for both:
- Open with the top three risks and fixes; the reader may stop there.
- Tables over prose. Every threat or finding names its path and the control that stops it; every control names where
  it lives and whether the model can bypass it.
- Include the trust-boundary flow (mermaid or text) and the trifecta table.
- Mark assumptions and unverified items explicitly.
- Every ID you reference (TH-, C-, RT-, F-) is defined in its own table; oversight rows point to C-IDs.
- No attack payloads; technique classes and trace properties only.
- Length: short form about one page; review two to five pages; a full threat model of a multi-tool agent may run six
  to ten pages because the tables carry it. If the user wants it brief, use compact mode: summary, trifecta table, P0/P1
  register rows, their controls, oversight table, P0/P1 tests, and one line listing what was left out. Omit genuinely
  N/A sections with one line saying why.

Short form for "is it safe to give my agent access to X":

```
Verdict: yes | yes, with conditions | not yet
Worst reachable outcome: <one line>
Trifecta with X added: private data <y/n>, untrusted content <y/n>, external channel <y/n>
Conditions before enabling (P0/P1): <3-6 bullets: scope, gate, credential, sandbox, approval>
Oversight tier for X's actions: <table of 2-5 rows>
Tests to run first: <2-3 technique classes with trace properties>
```

## Quality bar

Before returning, check:
- [ ] Every tool and every untrusted source from the inventories appears in the analysis; nothing generic like "the API".
- [ ] The Rule of Two triage is recorded for the job, and the trifecta is checked per flow, with the cut named and
      enforced in code.
- [ ] Every action has a permission tier and is authorised as granted scope ∩ user entitlements; recommend, prepare
      and execute use separate identities.
- [ ] Every guardrail names its layer and declares fail open or fail closed; no output is released before its
      verdicts; no P0/P1 path relies on the prompt layer.
- [ ] At least one propagation path is traced hop by hop, plus one no-attacker path.
- [ ] Each P0/P1 has a control the model cannot bypass; none rely solely on prompt text, a classifier or a human click.
- [ ] Credentials never pass through the context window, tool output or inherited environment.
- [ ] User identity comes from a verified token; delegated or multi-agent flows state and test the four delegation
      invariants; every entry point has a named authenticator.
- [ ] Every tool backend is reachable only through the gate, and each P0 control names who can switch it off.
- [ ] Code execution and computer use have a named sandbox tier with network and filesystem limits.
- [ ] If MCP is in scope: tools resolved as `server::name`, definitions pinned per session, token pipeline and
      exchange, consent rules and deploy probes are specified.
- [ ] Every action has an oversight tier; irreversible actions have hard limits that hold after approval.
- [ ] The approval gate covers deadline, silence, edits, idempotent execution, binding (digest, expiry, nonce) and
      reviewer view order.
- [ ] Every send says draft-first, delayed send or approval; calendar invites, shares and notifications count as egress.
- [ ] Approvals per day are computed against reviewer time; promotion thresholds are stated.
- [ ] Every referenced TH-, C-, RT- or F- ID is defined.
- [ ] Escalation triggers are explicit; any uncertainty signal is calibrated or flagged as not yet.
- [ ] A stop control and a recovery path (revoke, rotate, purge, restore) exist.
- [ ] ASI01-ASI10 each marked covered (built), covered (planned), gap or N/A with reason; OWASP lists cited as the
      2026 versions.
- [ ] Tests are specified as technique class + injection point + trace property; no payload text. The plan includes
      ASI seeds, two-identity authorization tests and the harness-level abuse tests.
- [ ] Residual risk has a named owner and re-review triggers.
- [ ] Review mode: every finding has evidence, a fix with location, and effort.

## Common mistakes

| Mistake | Fix |
|---|---|
| Defending injection with a better system prompt ("ignore instructions in documents") | Prompt text lives where the attack lives; it is documentation. Put the rule in the gate, the egress allowlist, the provenance gate or the tool interface |
| Leaving safety to provider refusals | Refusals are an untested third-party policy. Own the guardrail layers and the sandbox; keep an in-house model path for sensitive forensics |
| A guardrail that releases output before its verdict, or a guard that blocks only in its report | Release waits for every verdict; a guard returns a decision that blocks by default |
| Generic STRIDE or OWASP list with no link to this agent's tools | Start from the inventories; every threat cites a path through named tools |
| Treating tool results, tool descriptions and memory as trusted | They are untrusted input; scan them and gate actions that follow them |
| Missing quiet egress channels | Check URLs with data in them, rendered images and links, created issues and PRs, webhooks, logs sent to vendors |
| An injection classifier or LLM judge as the main control | Detection cuts volume; architecture bounds damage. Classifier scores vary widely |
| Human approval as the only barrier | Hard limits first; action-first reviewer view; rare, routed escalations |
| Approval on every action | Tier by consequence; sandbox and scope the low tiers; measure approval latency for rubber-stamping |
| Docker treated as a security boundary for untrusted code | Hardened container at minimum; gVisor, microVM or remote sandbox for untrusted code |
| Calling `exec`, or a container nobody tested, a sandbox | It must bound files, network, time and memory, each verified |
| Trusting a tool definition because it was approved once | Hash it per `server::name` and recheck every session; halt on drift |
| Authorising on the agent's scope alone | Granted scope ∩ user entitlements, per object and function; test the same call under two identities |
| Approving the thread, not the action | Bind a digest of the exact arguments, an expiry and a nonce; the executor recomputes the digest |
| Quoting one autonomy threshold as the books' rule | State the spread; gate promotion on case counts as well as rates |
| Confusing jailbreak with injection | Jailbreak attacks the vendor's policy; injection attacks your tools' authority. Different controls |
| Routing escalations on the model's stated confidence | Deterministic consequence triggers first; calibrated uncertainty second |
| Side effect placed before the interrupt, or execution keyed by approval ID | Propose, pause, execute in separate steps; key the write from durable run state, so a re-approval after a timeout cannot send twice |
| Forgetting recovery | Per-agent kill switch, rotation, memory purge and restore, audit log |
| Citing the OWASP LLM 2025 list | Use the 2026 lists (agentic 2025-12, LLM 2026-08) in [owasp-mapping.md](references/owasp-mapping.md) |
| Writing example attack strings in the test plan | Name the technique class and the trace property; payloads live in the harness |
| Equal weight on every finding | Apply the P0-P3 rule; lead with the top three |
| Accepting the stated architecture when it is the risk | Name it as a finding, propose the alternative, model it anyway |
| Taint-gating every send in an inbox assistant and stopping there | Count the prompts; cut them with structured extraction and per-recipient-class autonomy |
| Treating "reply" as safe whoever receives it | Identify the principal; replies to outsiders are external communication |
| Accepting the user as a `user_id` string from a trusted caller | Take identity from a signed, validated token; remove "act as user X" permissions with an explicit deny |
| Policy conditions on a value the model supplies (status, balance, owner) | Check state in the handler against the system of record; the gateway keeps coarse limits |
| Approving a gate without asking how else the backend can be called, or who can turn the gate off | Restrict each backend to the gate's identity; put mode and rule changes behind a separate role with alarms |
| Calling a hash stored next to each audit row "tamper-evident" | Write-once storage, hash chaining, or a keyed MAC the writers can't compute |

## Sources

Distilled from these books (chapter numbers), cited in the reference files by key:
- DEFGUIDE: *AI Agents: The Definitive Guide*, ch. 2 (human-in-the-loop interrupts), 6 (tool governance, sandboxing,
  code mode), 8 (OWASP agentic red-teaming), 10 (memory hygiene), 12 (threat modeling, runtime scanner).
- SYSTEMS: *Systems Thinking for Agentic AI*, ch. 7, 9, 10, 11 (guardrail layers, trust boundaries, approvals, safe
  degradation), 18.
- MCP: *AI Agents with MCP*, ch. 4, 6 (elicitation), 7 (server security, lethal trifecta, MCP Colors), 8.
- BUILDAPPS: *Building Applications with AI Agents*, ch. 3, 4, 11, 12 (threat vectors, MAESTRO, oversight failure
  modes), 13 (human-agent collaboration).
- MESH: *Agentic Mesh*, ch. 5, 8, 11 (secrets, injection, recovery), 12 (identity, authorization), 13.
- EVALS: *AI Evals in Practice*, ch. 10 (guardrail pipeline).
- ILLUSTRATED: *An Illustrated Guide to AI Agents*, ch. 7, 10 (code tools, coding-agent attack surface).
- DLLMA: *Designing Large Language Model Applications*, ch. 10 (guardrails and verifiers).
- AGENTICAI: *Agentic Artificial Intelligence*, ch. 5, 10 (trust dial).
- ENTERPRISE: *The Agentic Enterprise*, ch. 6, 7 (calibrated trust, inbox-deletion incident).
- HARDMCP: *Hardening MCP Servers*, ch. 1 to 10 (scan data, sinks, supply chain, rug pulls, authentication, prompt-layer
  controls, tokens, consent, agent-layer boundaries, operational defaults).
- PLAYBOOK: *Agentic AI Playbook*, ch. 2 (five-factor scoring, move-up conditions), 4 (earned-autonomy stages,
  reversibility test), 9 (Rule of Two, three guardrail layers).
- PRODGUIDE: *Agentic AI Systems: The Complete Guide for Building Production AI Agents*, ch. 12 (permission tiers per
  action, confirmation gates).
- AISEC: *Agentic AI for Cybersecurity*, ch. 7 (separate identities per phase), 10 (OWASP agentic controls and tests,
  MAESTRO, CoSAI Risk Map).
- APIARCH: *Mastering API Architecture*, ch. 6 (STRIDE per element, DREAD, fail open or closed), 7 (object- and
  function-level authorization, scopes versus entitlements).
- FASTGENAI: *Building Generative AI Services with FastAPI*, ch. 6 (streaming), 9 (input and output guardrails).

Andrew Ng, The Batch letters (deeplearning.ai):
- Blenders Versus Bombs, or Why California's Proposed AI Law is Bad for Everyone (2024-06-05),
  https://www.deeplearning.ai/the-batch/blenders-versus-bombs-or-why-californias-proposed-ai-law-is-bad-for-everyone
- Agentic Coding and Agentic Software Testing Go Together (2025-09-17),
  https://www.deeplearning.ai/the-batch/agentic-coding-and-agentic-software-testing-go-together
- Context for Coding Agents (2026-03-09), https://www.deeplearning.ai/the-batch/crowdsourced-context-for-coding-agents
- Let's Help Agents Share Their Work (2026-03-16), https://www.deeplearning.ai/the-batch/lets-help-agents-share-their-work
- When Guardrails Go Wrong (2026-07-24), https://www.deeplearning.ai/the-batch/when-guardrails-go-wrong
- Open Models, Open Harnesses, Open Security (2026-07-31),
  https://www.deeplearning.ai/the-batch/open-models-open-harnesses-open-security
- Who's Responsible for Irresponsible AI? (2026-09-18), https://www.deeplearning.ai/the-batch/whos-responsible-for-irresponsible-ai

Code read for patterns and gaps (read 2026-10-18, not run): github.com/Nicolepcx/ai-agents-the-definitive-guide,
github.com/kylestratis/ai_agents_mcp_examples, github.com/PacktPublishing/AI-Evals-in-Practice,
github.com/HandsOnLLM/An-Illustrated-Guide-To-AI-Agents, github.com/sinanuozdemir/building-agentic-ai,
github.com/santosomar/AI-agents-for-cybersecurity, github.com/Ali-Parandeh/building-generative-ai-services,
github.com/andrewyng/aisuite, github.com/humanlayer/12-factor-agents, github.com/cosai-oasis/secure-ai-tooling.

External (dated list in [owasp-mapping.md](references/owasp-mapping.md)): OWASP Top 10 for Agentic Applications 2026;
OWASP Top 10 for LLM Applications 2026; CoSAI Risk Map; Google Workspace and Microsoft Graph scope documentation
(provider notes in controls-catalog.md §3, 2026-10-19); MCP Security Best Practices and elicitation (spec 2026-07-28); Beurer-Kellner et al., Design
Patterns for Securing LLM Agents against Prompt Injections (2025); Anthropic posts on Claude for Chrome, Claude Code
sandboxing, computer use, and measuring agent autonomy; Xiong et al. (ICLR 2024); EU AI Act Article 14.

Practitioner lab notes (AWS AgentCore and data labs, 2026-10). The AWS documentation pages confirmed against them are
listed in [aws-implementation-notes.md](references/aws-implementation-notes.md) §Sources.
