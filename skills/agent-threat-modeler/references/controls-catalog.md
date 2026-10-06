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
Checks, in this order:

1. **Allowlist, default deny.** Unknown tool → deny.
2. **Registered and discovered.** The tool was granted to this agent for this task.
3. **Caller authority.** The end user (not only the agent) may perform this action on this resource; tenant matches.
4. **Budget.** Calls per task, parallel calls, wall time, money, tokens. Time spent waiting for a human does not count
   against the agent's timeout [DEFGUIDE ch6].
5. **Arguments.** Schema (types, required fields) then semantics: IDs exist and belong to the tenant, paths resolve
   inside the allowed root, URLs and recipients on allowlists, amounts and counts under hard caps.
6. **Flow rules.** Taint: once untrusted content has entered the run, egress tools need approval or are denied.
   Resource scoping: a session that started on resource A may not touch resource B (the per-repository rule from the
   trifecta case in [MCP ch7]).
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

## 3. Credentials and identity

- **Broker, not tool.** Non-LLM code that executes the call adds the credential from a vault, per the agent's
  configuration. The model decides *that* a call is needed and never sees the value. A "get_secret" tool is the wrong
  design because its output returns to the model [MESH ch11].
- **Short-lived and scoped.** Per task or per resource where possible (single-repository tokens instead of personal
  access tokens [MCP ch7]); rotate on a schedule and on demand.
- **Per-agent identity.** Each agent has its own workload identity (for example SPIFFE/SPIRE-style), separate from human
  users, so you can scope, attribute and revoke one agent without stopping the rest [MESH ch12].
- **Delegation.** When acting for a user, use delegated tokens that never exceed the user's rights; record both
  identities in the audit log.
- **No pass-through.** A server accepts only tokens issued for itself (audience check) and uses its own credentials
  downstream [MCP ch7].
- **Local servers.** Pass a stdio MCP server only the environment variables it needs [MCP ch8].
- **Logs.** Scrub secrets and personal data from logs, traces and caches; set retention [BUILDAPPS ch12].
- **Provider scope granularity.** Some providers can't separate reading from sending, or composing from sending, in
  one OAuth scope. Then keep the token in a proxy service that exposes only intent-level operations (create draft,
  reply in thread X) and enforces recipients and rates there; the agent never holds the token. An agent running on the
  user's own full-scope token is a finding, not a premise.

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
  uses 0.2 and 0.8 [DEFGUIDE ch12]; tune yours on a labelled set).
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

## 8. Multi-agent links

- mTLS between agents; authenticated, schema-validated messages; the receiver applies its own gate [MESH ch11].
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
- Proxies with a static client ID: per-client consent stored server-side, exact redirect-URI matching, single-use
  `state` set only after consent [MCP ch7].
- Block private IP ranges during OAuth metadata discovery (SSRF); use an egress proxy.
- Bind state handles to the verified user; possession of a handle is not authentication.
- Progressive scope minimisation: start with low-risk scopes, step up on demand.
- Validate paths and arguments in tool code. Per [MCP ch7], the Python SDK checks resource-template parameters but not tool parameters.

The MCP spec does not solve prompt injection or tool poisoning through tool content; that stays the host's job.
MCP is an integration contract, not a security boundary [SYSTEMS ch7].

## 10. Detection and recovery

- **Audit log** per tool call: agent identity, user identity, tool, redacted arguments, gate decision and reason,
  approver, result status, trace ID. Machine-readable, so audits and red-team graders can use it.
- **Behavioural baselines**: request rate per agent and tool, message volume between agent pairs, data volume read,
  spend. Raise anomalies for human review; quarantine automatically when an agent touches critical data or expensive
  services outside baseline [MESH ch11].
- **Alerts on AI-specific signals**: invalid structured output, rising refusals, abnormal loop depth, unexpected approval
  frequency, repeated fallbacks [SYSTEMS ch11].
- **Kill switch**: per agent and global, server-side (revoke credentials, halt the queue), reachable remotely, tested in
  drills. A local process kill is not enough [ENTERPRISE ch7].
- **Rotation**: rotate secrets on demand; for secrets you can't rotate, remove them from the agent's reach [MESH ch11].
- **Restore**: back up configuration, registry and memory; restore a known-good state [MESH ch11].
- **Runbook**: detect → quarantine agent → revoke and rotate → scope the blast radius from the audit log → purge
  poisoned memory → restore → add the path to the regression suite → re-enable at a lower autonomy level.
