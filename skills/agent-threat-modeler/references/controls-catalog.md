# Controls catalog

Pick controls in this order: **eliminate → narrow → gate → isolate → contain injection → detect → recover**.
Earlier families bound the damage of anything that gets through later ones. A control that lives only in the
prompt is documentation, not a control: context can be truncated, summarised away or argued around [ENTERPRISE ch7],
[SYSTEMS ch11].

For every control you recommend, state: what it stops (threat IDs), where it lives (service, file, gateway),
whether the model can bypass or edit it, and what it costs (latency, utility, operator time).

## 1. Eliminate and narrow capabilities

The cheapest control is a capability that does not exist.

- Replace generic power tools with intent-level tools: `get_order(order_id)` not `execute_sql(query)`;
  `create_draft_reply(ticket_id, body)` not `send_email(to, body)` [BUILDAPPS ch4], [SYSTEMS ch7].
- Write tools fill server-side query templates; the model supplies parameters only [MESH ch11].
- Read-only jobs get read-only database accounts and read-scoped tokens.
- If free-form SQL or shell is truly needed, the minimum is: reject destructive clauses, bind parameters,
  least-privilege account, log every call, alert on large deletes or schema changes [BUILDAPPS ch4]. Prefer running
  it in a sandbox against a replica.
- Default-deny visibility: an agent sees only the tools and registries granted to it; new agents start with fewer
  tools and earn more [MESH ch5], [AGENTICAI ch5].

## 2. The policy gate (single enforcement point)

Exactly one code path turns a model proposal into a side effect. The model emits a structured request; the gate decides.

**Make the gate unavoidable.** The backend behind each tool accepts calls only from the gate's identity (resource
policy, network policy, or an allowlist of calling workloads). Anything else that holds invoke rights on the backend
skips every rule. In a review, list who can call each backend directly, through every endpoint, alias and version.

**What a gateway policy can and can't see.** A policy engine in front of tools evaluates the caller's identity, the
tool and the arguments. It can enforce allowlists, caps on argument values, identity and tenant rules, and session
counts. It can't know a record's real state, so a condition on a value the model supplies ("status is not shipped") is
a hint, not a control. Facts about the world (status, balance, owner) are checked in the handler, or in a lookup the
gate calls, against the system of record. Use both: the gateway for coarse, auditable limits, the handler for state. A
single gate is right; a single place for every rule, with rule-free handlers behind it, is not.

Checks, in this order:

1. **Allowlist, default deny.** Unknown tool → deny.
2. **Registered and discovered.** The tool was granted to this agent for this task.
3. **Caller authority.** The end user (not only the agent) may perform this action on this resource; tenant matches.
4. **Budget.** Calls per task, parallel calls, wall time, money, tokens. Time spent waiting for a human does not count
   against the agent's timeout [DEFGUIDE ch6].
5. **Arguments.** Schema (types, required fields) then semantics: IDs exist and belong to the tenant, paths resolve
   inside the allowed root, URLs and recipients on allowlists, amounts and counts under hard caps. Content checks on
   free-text arguments (§6).
6. **Flow rules.** Taint: once untrusted content has entered the run, egress tools need approval or are denied.
   Resource scoping: a session that started on resource A may not touch resource B (the per-repository rule from the
   trifecta case in [MCP ch7]). Order rules ("tool B only after tool A") and per-session call caps are flow rules too;
   some gateways keep this session state in their policy engine.
7. **Risk-tier routing.** Act and log / act and notify / ask a human / refuse ([human-oversight.md](human-oversight.md)).
   Hard limits (step 5) are checked before any human is asked, so an approval can never exceed them.
8. **Execute** with the credential injected here and an idempotency key.
9. **Post-process.** Validate the result; mark it as untrusted data before it re-enters context; set the taint flag if
   the tool brings outside content.
10. **Audit.** Record proposal, decision, reason, approver, arguments (redacted), result status.

Denials return a short reason to the model so it can degrade gracefully instead of retrying blindly [DEFGUIDE ch6].

**Separation rule:** an agent may not discover tools and execute them in the same run. A hijacked plan relies on the
pivot from "what can I reach?" to "use it" [DEFGUIDE ch6].

At enterprise scale, put the gate in a policy engine (for example Open Policy Agent) that can allow, deny, throttle or
quarantine based on identity, task context and past behaviour [MESH ch12].

Minimal sketch (fresh, illustrative; add real schema validation, persistence and rate limits):

```python
POLICY = {  # anything not listed is denied
    "search_kb":     {"tier": "read"},
    "fetch_url":     {"tier": "read", "taints": True, "check": lambda a: domain_allowed(a["url"])},
    "create_ticket": {"tier": "reversible"},
    "send_email":    {"tier": "egress", "check": lambda a: a["to"] in run_ctx().allowed_recipients},
    "issue_refund":  {"tier": "irreversible", "check": lambda a: 0 < a["amount"] <= 200},
}

def gate(run, name, args):
    rule = POLICY.get(name)
    if rule is None:                         return deny(run, name, "not allowed")
    if run.calls >= run.max_calls:           return deny(run, name, "budget exhausted")
    if not schema_ok(name, args):            return deny(run, name, "bad arguments")
    if not rule.get("check", lambda a: True)(args):
        return deny(run, name, "over limit")  # hard limit: checked before any human
    tier = rule["tier"]
    if tier == "egress" and run.tainted:
        tier = "irreversible"                 # trifecta cut on the egress leg
    if tier == "irreversible" or (tier == "reversible" and name not in run.earned):
        return request_approval(run, name, args)   # resumes into execute() in a later step
    return execute(run, name, args)           # injects credential, sets run.tainted if rule["taints"]
```

**If the gate is a declarative policy engine** (Cedar, OPA/Rego and similar), write rules with its semantics in mind:
- Default deny blocks every tool that has no explicit allow, harmless reads included. Give every tool an allow before
  turning enforcement on.
- Write "allow unless X" as one conditional allow (permit tool T when the argument isn't X). A lone forbid also leaves
  everything else denied.
- Forbid beats allow, so keep forbids for cross-cutting guardrails that must win over any allow: tenant mismatch, an
  injection score, a kill flag.
- Make every field a rule reads required in the tool schema, or guard it with an existence check. In Cedar a policy
  whose condition errors (a missing attribute, for example) is skipped. For a permit that is harmless, since the call
  stays denied, but a forbid on an absent optional field silently stops applying.
- Approval gates live outside the engine. The engine only allows or denies a call; it can't see whether a human
  approved, and it doesn't route anything. For a gated action class, the agent's principal gets a permit only for a
  request or propose tool (`request_refund_approval`, not `issue_refund`). A separate executor identity, allowed by
  its own rule, runs the approved action keyed by approval ID after re-checking the hard limits and the record's state
  ([human-oversight.md](human-oversight.md) §3).

**Shipping a gate rule.** Rules need their own release process:
- Lint: reject a rule with no condition, or a forbid with no exception, unless the reason is written next to it. Where
  the engine can flag rules that always allow or always deny, run that analysis and justify any override in writing.
- Roll out in log-only (shadow) mode beside the enforced set, and enforce once its decisions on real traffic match
  what you expected.
- After every change, confirm each rule reached an active state and shows up in decision logs. Rule creation can be
  asynchronous and fail after the console reported success, and log-only evaluation can fail silently when a
  permission is missing. A rule that failed to deploy turns an allow into an outage and a forbid into a hole. Alarm on
  any rule that isn't active, and on decision logs going quiet.

AWS mapping: [aws-implementation-notes.md](aws-implementation-notes.md).

## 3. Credentials and identity

- **Broker, not tool.** Non-LLM code that executes the call adds the credential from a vault, per the agent's
  configuration. The model decides *that* a call is needed and never sees the value. A "get_secret" tool is the wrong
  design because its output returns to the model [MESH ch11].
- **Short-lived and scoped.** Per task or per resource where possible (single-repository tokens instead of personal
  access tokens [MCP ch7]); rotate on a schedule and on demand.
- **Per-agent identity.** Each agent has its own workload identity (for example SPIFFE/SPIRE-style), separate from human
  users, so you can scope, attribute and revoke one agent without stopping the rest [MESH ch12]. Federate these
  identities into the identity provider and privileged-access system the organisation already treats as authoritative;
  a parallel identity store splits the audit trail. When agents are split to separate data, the boundary has to exist
  in their credentials, not only in prompts or tool lists. Verify it with a negative test (a policy simulation or a
  real call) showing each agent's identity is denied every other agent's stores, and review the effective permissions,
  not the policy names.
- **Delegation.** When acting for a user, use delegated tokens that never exceed the user's rights; record both
  identities in the audit log. Across more than one hop, apply the invariants in "Delegation chains" below.
- **Verified, not asserted, identity.** The user an agent acts for is proven by a token the identity provider signed
  and the receiver validated (checklist below), not passed as a string by a trusted caller. An "act as user `<id>`" or
  "get a token for user `<id>`" API is impersonation for every principal allowed to call it. Remove that permission,
  and add an explicit deny so a later broad allow can't restore it.
- **Acting for a person, or as itself, by design.** If an agent should only ever act for a signed-in person, turn off
  its own machine-to-machine (client credentials) grant and have receivers require a claim that marks a human subject.
  An agent that can mint tokens as itself becomes a standalone privileged principal once compromised.
- **Unverified decoding.** Reading claims without checking the signature is acceptable only for logging, and only where
  every route to the code (every version, alias and endpoint) has a verifying authorizer in front. Otherwise forged
  claims become identity.
- **No pass-through.** A server accepts only tokens issued for itself (audience check) and uses its own credentials
  downstream [MCP ch7].
- **Local servers.** Pass a stdio MCP server only the environment variables it needs [MCP ch8].
- **Logs.** Scrub secrets and personal data from logs, traces and caches; set retention [BUILDAPPS ch12]. Platforms
  often copy the token subject into their own audit logs, so use opaque or pairwise subject IDs, not emails.
- **Provider scope granularity.** Some providers can't separate reading from sending, or composing from sending, in
  one OAuth scope. Then keep the token in a proxy service that exposes only intent-level operations (create draft,
  reply in thread X) and enforces recipients and rates there; the agent never holds the token. An agent running on the
  user's own full-scope token is a finding, not a premise.

### Delegation chains

When agent A calls agent B, or a resource, for a user, A exchanges the token it received for a new one (OAuth 2.0
Token Exchange, RFC 8693, or the identity provider's on-behalf-of flow). It never forwards the token it received. Four
invariants hold at every hop:

1. **Same subject.** The user's subject (`sub`) is unchanged end to end. Identity travels in the token, never as a
   `user_id` field in the message.
2. **Audience is the next hop only.** Each token is minted for exactly one receiver, so a token stolen at one hop is
   useless at the next.
3. **Scope never widens.** Effective rights = what the user holds ∩ the acting agent's ceiling ∩ what this task
   needs. A read path never carries a write scope.
4. **The actor is recorded.** The token names the acting agent (the `act` claim from RFC 8693, or `azp` /
   `client_id`), and every audit row stores subject and actor together.

Enforce reach in three places, so one misconfiguration isn't enough:
- **Issuance.** The identity provider mints a given audience only for clients wired to call it, and caps scopes at the
  client's ceiling.
- **Invocation.** The receiving agent rejects tokens not addressed to it.
- **Resource.** The API validates the token again and applies its own per-actor ceiling.

Terminal resources consume tokens and never exchange them. Prefer sender-constrained tokens (mutual-TLS-bound or DPoP)
where the platform supports them; otherwise keep lifetimes to minutes. Managed agent platforms increasingly broker the
exchange and propagate caller identity for you. Use that, and check the four invariants either way. One test per
invariant: [red-team-test-plan.md](red-team-test-plan.md) §Delegation tests.

### What a receiver checks in a token

Validate every inbound token in this order, and fail closed when a claim is **missing**, not only when it is wrong:

1. Signature, with the algorithm pinned (never `none`, never whatever the token header names).
2. `exp` present and in the future; `nbf`; a maximum lifetime (`exp` minus `iat`). An authorizer that skips the expiry
   check when `exp` is absent accepts tokens that never expire.
3. Issuer.
4. Audience is this service.
5. Token type is an access token. ID tokens from the same identity provider verify against the same keys, so check
   `typ` or the provider's token-use claim.
6. Client or actor on an allowlist.
7. Required scope present.
8. Policy claims, for example that the subject is a person.
9. At a resource: the actor's rights stay within a per-actor ceiling the resource keeps itself.

Take the user or customer from the verified subject, never from a request parameter. For the MCP server side of this
checklist, see agent-tool-designer.

AWS mapping: [aws-implementation-notes.md](aws-implementation-notes.md).

## 4. Breaking the trifecta

Cut one leg per request, in code. Options per leg:

| Leg | Cuts that keep the feature | Cost |
|---|---|---|
| Untrusted content | Allowlist sources (domains, repos, senders); fetch through a reader that extracts schema'd fields only; quarantined reader (dual LLM) | Less coverage; extraction can drop context |
| Private data | Request-scoped tokens and tenant filters; don't load private data into a run that reads untrusted content; split into two agents with no shared context | Some tasks need both; then use a quarantine pattern |
| External channel | Taint-gated egress (approval or deny after untrusted input); egress proxy with domain allowlist; recipient allowlists; no client-side rendering of remote images or auto-unfurled links from model output; drafts instead of sends | Friction on legitimate sends; approvals need a reviewer who can judge |

### When the product needs all three legs

An inbox assistant, a browser agent or a personal assistant with calendar access reads untrusted content and holds
private data by definition, and sending is the feature. Taint-gated egress still applies, but if every inbound email
taints the run, nearly every send asks. Count it first: sends per day × share that would ask = approvals per day
([human-oversight.md](human-oversight.md) §4). If that is more than the principal will read, they will rubber-stamp and
the gate stops protecting anyone. Reduce prompts without removing the cut:

| Technique | How it reduces prompts | What still holds | Limit |
|---|---|---|---|
| Structured extraction | An isolated call reduces untrusted text to typed fields (intent from a fixed list, dates, amounts, IDs that must match records); only those reach the planner. Lift taint only for fields that can't carry instructions (enums, validated dates, known IDs) | Free text never steers tool choice | Loses nuance; free-text fields stay tainted |
| Quarantined summariser (dual LLM) | A model without tools reads the raw content and returns variables the planner passes along by reference | The planner never reads raw untrusted text | A summary shown to the planner as prose is still untrusted; anything copied into a send stays tainted |
| Per-recipient-class autonomy | Sends to classes that earned it (the principal, existing thread participants, the internal domain) run as act-and-notify or delayed send; new external recipients always ask | Exfiltration to a new address needs a human | A compromised known contact; keep content limits |
| Content limits on automatic sends | Automatic replies may contain only data from the current thread, with no links or attachments from other sources | Other private data can't ride out | Some replies need approval anyway |
| Batched drafts | Drafts queue and the principal approves a batch at set times | Same approval, fewer interruptions | Latency; batch fatigue, so show diffs and keep batches small |
| Delayed send with cancel | Sends wait in a queue for a cancel window ([human-oversight.md](human-oversight.md) §3) | Time to catch mistakes without a prompt per send | Works only if someone watches the queue; doesn't replace caps |

The gate on the egress leg stays in code either way; these patterns change who is asked and how often, not whether the
check runs.

### Opening links from untrusted content

A link in an email or page is chosen by whoever wrote it. Opening it is a send (the request reaches their server, and
data can ride in the URL) and can be an action (unsubscribe, confirm, approve, magic login, one-click purchase).

1. **Reader service.** A separate fetcher with no cookies, sessions or credentials, behind the egress proxy, returns
   extracted text or fields as untrusted data. The agent never fetches directly.
2. **No model-built URLs.** The model refers to a link by an ID assigned when the source was parsed; the reader resolves
   the ID to the original URL. The model can't compose, edit or append parameters.
3. **Re-check every redirect hop**: https only, domain allow and deny lists, private IP ranges and metadata endpoints
   blocked after DNS resolution, hop limit.
4. **Read-only requests.** GET only, no form posts or script-driven submissions; if rendering is needed, a sandboxed
   headless browser with an empty profile.
5. **State-changing links go to a person.** Classify unsubscribe, confirm, verify, approve, login and tracking-token
   links by URL pattern and link text; never open them automatically; the principal clicks them.
6. **Log** every fetch with the source message ID.

## 5. Containing injection when you can't cut a leg

From "Design Patterns for Securing LLM Agents against Prompt Injections" (Beurer-Kellner et al., 2025, external). Principle: once an
agent has read untrusted input, that input must have no way to trigger consequential actions. Every pattern trades
utility for that guarantee.

| Pattern | How | Fits | Cost |
|---|---|---|---|
| Action selector | Model only maps the request to one of a fixed set of actions; never sees tool output | Routers, command palettes | No open-ended work |
| Plan-then-execute | Commit to the tool sequence before reading untrusted data; data can change values, not which tools run | Workflows with a known shape | Can't adapt to what it reads |
| LLM map-reduce | Each untrusted item processed in an isolated call with constrained output (label, number, schema) | Triage, classification, ranking many documents | Cross-item reasoning lost |
| Dual LLM | Privileged planner with tools never sees raw untrusted text; a quarantined model without tools reads it and returns symbolic variables the planner passes along | Assistants over email or web with private data | Engineering complexity; planner reasons over references, not content |
| Code-then-execute | Model writes a program up front; untrusted data flows through variables, with capability tracking | Multi-step tool composition | Needs a governed interpreter ([sandboxing.md](sandboxing.md)) |
| Context minimisation | Drop the user's original prompt and untrusted spans before later steps | Multi-turn flows where earlier text is no longer needed | Loses context |

Code mode (programmatic tool calling) keeps intermediate results out of the model's context, but injection can now
steer the code the model writes, so the interpreter must be deny-by-default and each host function must still pass the
gate [DEFGUIDE ch6].

Prompt-level techniques (separating instructions from content, delimiters, rejecting inputs that contain your section
markers, warning the model about injection) only lower the likelihood. [MESH ch11] recommends them and still concedes
that the best protection is limiting what the agent can access. Use them, but never count them as the control for a
P0 or P1 path.

## 6. Tiered guardrails

| Tier | What | Where | Latency |
|---|---|---|---|
| 1 Deterministic | Unicode normalisation, invisible-character flags, regex families (injection markers, exfiltration patterns such as URLs with encoded data), schema checks, allow/deny lists, PII patterns | Inline, every request and every tool result | Microseconds [EVALS ch10] |
| 2 Small model or classifier | Injection/jailbreak classifier, topic classifier | Inline only on the uncertain band of tier-1 scores, with a cache | Tens to hundreds of ms |
| 3 LLM judge | Policy or alignment check on the plan or output | Uncertain band only, or in parallel with delivery | Hundreds of ms or more [EVALS ch10] |
| 4 Online eval | Quality and safety sampled after delivery | Async, sampled | None for the user |

Design rules:
- Weight by trust context: tool output gets higher injection and exfiltration sensitivity than authenticated staff
  input [DEFGUIDE ch12].
- Map the score to allow / human review / block, and invoke the judge only between two thresholds (the book's scanner
  uses 0.2 and 0.8 [DEFGUIDE ch12]; tune yours on a labelled set). Before enforcing, run the check in shadow
  (log-only) mode and set thresholds on the observed score distribution.
- Scan the free-text **arguments of proposed calls** (reasons, notes, message bodies) as well as inputs and results.
  Injection markers in an argument mean the plan was steered upstream: deny or route to a human, as a forbid no allow
  can override. It is still detection, not the control for a P0 path. Test each such rule with a paired call
  ([red-team-test-plan.md](red-team-test-plan.md) §Gate rule tests).
- Choose the on-fail action per validator: fix or redact (deliver the rest), re-ask, filter one field, refrain, log only,
  raise [DLLMA ch10]. Prefer modification to blocking; a guardrail that blocks good answers can be worse than none [EVALS ch10].
- Start from untrusted defaults, measure a bypass baseline with an automated red-team harness, tune only the categories
  that fail [DEFGUIDE ch12].
- Detector quality varies widely: on the vendor-run PINT benchmark one commercial detector scored 92.5% and Llama Prompt
  Guard 61.4% [BUILDAPPS ch12]. Whatever you deploy leaves a residue the architecture must absorb.
- Output handling: encode model output for its destination (HTML escape, parameterised SQL, no `shell=True`).

## 7. Memory hygiene

- Write gate before persistence: size limits, sensitive-pattern rejection, source allowlist, confidence threshold,
  contradiction and duplicate checks [DEFGUIDE ch10].
- Provenance on every entry: source, run ID, agent, time, content hash; append-only log for shared memory; re-verify at
  each stage [BUILDAPPS ch12].
- Tenant and user isolation enforced in the retrieval code, plus retention limits [SYSTEMS ch9].
- Do not store runs that read untrusted content as exemplars or "learned procedures" without review.
- Keep a purge path: find all entries from a source or run and delete them; back up memory so you can restore a
  known-good state.
- **Memory exposed as tools** (a memory MCP server, a memory API the agent calls): the server binds tenant, user,
  session and author role from the authenticated request context; they are not tool parameters. The model writes only
  as itself (assistant note, proposed fact); user turns are written by the application from the real user message.
  Otherwise a model-chosen session key is a cross-session read, and a forged "user" turn reads back later as the
  user's own words. Test it: call the read tool with another session's ID and expect a refusal. Memory design detail:
  agent-context-designer.

## 8. Multi-agent links

- mTLS between agents; authenticated, schema-validated messages; the receiver applies its own gate [MESH ch11]. Where
  the runtime authenticates callers by bearer token instead (managed agent runtimes typically do), use audience-bound,
  short-lived signed tokens per hop (§3 Delegation chains).
- Agent-to-agent messages carry no `user_id` or tenant fields that the receiver trusts. Identity comes from the
  verified token (§3).
- Delegation never grants more than the delegator holds; no shared service accounts.
- Loop limits, hop counts and circuit breakers on agent-to-agent calls; safe degradation when a dependency fails
  (partial result, defer, escalate; stop if a required check fails) [SYSTEMS ch11].

## 9. MCP-specific controls (as of 2026-10, spec 2026-07-28)

Client and host side:
- Show tool descriptions to users; re-obtain consent when a server's tool list changes; namespace tools by server [MCP ch4].
- Pin server versions; prefer vetted registries; review descriptions as untrusted text.
- Prefer stdio for local servers; if HTTP, bind to 127.0.0.1 and validate the Origin header (DNS rebinding) [MCP ch8].
- Consent before running one-click local server install commands.

Server side:
- OAuth 2.1 resource server: validate token audience and scopes; never pass client tokens downstream [MCP ch7].
  Audience and scope are two of the receiver checks in §3; run all of them.
- Proxies with a static client ID: per-client consent stored server-side, exact redirect-URI matching, single-use
  `state` set only after consent [MCP ch7].
- Block private IP ranges during OAuth metadata discovery (SSRF); use an egress proxy.
- Bind state handles to the verified user; possession of a handle is not authentication.
- Progressive scope minimisation: start with low-risk scopes, step up on demand.
- Validate paths and arguments in tool code. Per [MCP ch7], the Python SDK checks resource-template parameters but not tool parameters.

The MCP spec does not solve prompt injection or tool poisoning through tool content; that stays the host's job.
MCP is an integration contract, not a security boundary [SYSTEMS ch7].

## 10. Detection and recovery

- **Audit log** per tool call and per delegation hop: trace ID, user subject and acting agent, audience and scope of
  the token used, tool, redacted arguments, gate decision and reason, approver, result status. Decoded claims only,
  never raw tokens. Machine-readable, so audits and red-team graders can use it. Mint the trace ID at the entry point;
  downstream services accept it only from an authenticated upstream, never from a caller-supplied header or query
  string.
- **Tamper-evident** means write-once storage (object lock, an append-only ledger), each record hash-chained to the one
  before it, or a keyed MAC whose key the writers don't hold. A hash stored next to each row only proves the row is
  self-consistent: anyone who can rewrite the row can recompute it.
- **Failed audit writes.** For irreversible actions, decide whether a failed audit write blocks the action. Default:
  it does. Never swallow the error.
- **Credential issuance is audited too**: every token or secret handed to an agent (which agent, on whose behalf,
  audience, scope, time, outcome). Many platforms treat these as high-volume data events and record them only when
  asked. Check that enabling them doesn't silently turn off other audit categories on the same trail.
- **Behavioural baselines**: request rate per agent and tool, message volume between agent pairs, data volume read,
  spend. Raise anomalies for human review; quarantine automatically when an agent touches critical data or expensive
  services outside baseline [MESH ch11].
- **Alerts on AI-specific signals**: invalid structured output, rising refusals, abnormal loop depth, unexpected approval
  frequency, repeated fallbacks [SYSTEMS ch11].
- **Alerts on identity signals**: token-fetch and authorization failures per agent, and authentication attempts against
  agents from unexpected callers. Emit zeros so an alarm doesn't sit in "no data".
- **Canaries**: plant fake records or tokens an agent should never read or send, and alert when one appears in a log,
  trace or outbound request.
- **Protect the controls themselves.** The permission to change the gate's mode (enforce or log-only), detach its
  policies, or replace an endpoint's authorizer is the permission to disable every control at once. Log-only mode
  still logs "would have denied", so a switched-off gate looks like a working one. Give that permission to a separate,
  narrowly held role, require a second person for changes, and alarm on every change to gate mode, rule set,
  authorizer and allowed clients.
- **Configuration drift.** Update APIs that replace the whole configuration drop any field you don't resend
  (authorizer, header forwarding, environment), and may publish the result as the new default version. Build each
  update from the current state, and after every deploy diff the security fields (authorizer, allowed audiences and
  clients, header forwarding, gate attachment and mode) against the approved baseline. Setup wizards can add grants
  nobody asked for, such as a default scope on a new client, so read back effective grants afterwards.
- **Kill switch**: per agent and global, server-side (revoke credentials, halt the queue), reachable remotely, tested in
  drills. A local process kill is not enough [ENTERPRISE ch7].
- **Rotation**: rotate secrets on demand; for secrets you can't rotate, remove them from the agent's reach [MESH ch11].
- **Restore**: back up configuration, registry and memory; restore a known-good state [MESH ch11].
- **Runbook**: detect → quarantine agent → revoke and rotate → scope the blast radius from the audit log → purge
  poisoned memory → restore → add the path to the regression suite → re-enable at a lower autonomy level.

AWS mapping: [aws-implementation-notes.md](aws-implementation-notes.md).
