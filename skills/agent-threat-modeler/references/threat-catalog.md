# Threat catalog for agents

Use this to fill the threat register (Step 7) and to trace propagation paths (Step 6). Each entry says where
the threat enters, what to look for in a design or codebase, and which control family stops it (details in
[controls-catalog.md](controls-catalog.md), [sandboxing.md](sandboxing.md), [human-oversight.md](human-oversight.md)).
OWASP IDs are in [owasp-mapping.md](owasp-mapping.md).

## Why agent threat modeling is different

Classical threat modeling asks what an attacker can do to a component. An agent carries intent from one component
to the next: an injected instruction can become a plan, the plan becomes a tool call, and the result becomes a memory entry.
Each layer sees well-formed input and lets it through [DEFGUIDE ch12]. Two consequences shape the whole method:

1. **Trace paths, not components.** A per-tool check passes a call that is in contract but comes from a hijacked plan.
   The unit of analysis is the path from an untrusted source to a side effect.
2. **No attacker is needed for many failures.** The agent can reason its way into misuse, loop, or be more helpful
   than intended while staying inside its permissions [DEFGUIDE ch12], [DEFGUIDE ch6]. Model at least one path with no
   adversary.

Working assumption: anything that reaches the context window can steer the model. That includes the user's message,
retrieved documents, web pages, emails, file contents, screenshots, tool results, tool names and descriptions, memory,
and messages from other agents [SYSTEMS ch11], [MCP ch4]. You cannot stop the model being fooled, so you design for a
fooled model having little reach.

## The four questions at every hop

| Question | Ask | Gap looks like |
|---|---|---|
| Reach | If the model were fully attacker-controlled at this step, which tools, data and destinations could it touch? | Broad tools, shared credentials, any-domain egress |
| Gate | Which deterministic check stands between proposal and side effect, and can the model rewrite, truncate or argue past it? | Rule exists only in the system prompt; approval is the only barrier |
| Persistence | Can a bad step write itself into memory, logs reused as context, or another agent's inbox? | Unvalidated memory writes; "successful" runs saved as examples |
| Recovery | Could you see what happened, revoke what it used and restore a known state? | No tool-call audit log; no per-agent kill switch; no memory backup |

## Layers (where to look)

Six layers, each with its typical mechanism. Use them to make sure the register is not all "prompt injection" [DEFGUIDE ch12].

| Layer | Main property at risk | Typical mechanism | Typical outcome |
|---|---|---|---|
| Organisation | All | Over-broad roles, missing owner, no policy for what the agent may do | Nobody accountable; permissions creep |
| Model | Integrity | Injection or jailbreak rewrites goal; hallucinated arguments | Unsafe decisions that look legitimate |
| Orchestration | Integrity, availability | Hijacked plan, unbounded loops, retries, fan-out, handoffs | Amplified errors, runaway cost, cascades |
| Tool | Confidentiality, integrity, availability | Misuse within permissions, bad parameters, exfiltration via egress | Data leaves, records change, money moves |
| Memory | Confidentiality, integrity | Poisoned or over-shared persistent state | Compromise outlives the session; cross-user leaks |
| Infrastructure | All | Host code execution, secrets in env, exposed local servers, supply chain | Host or account compromise |

For an inventory that also covers the build pipeline and the evaluation stack, the CSA MAESTRO framework uses seven
layers from foundation model to agent ecosystem [BUILDAPPS ch12]. Use the six layers above to trace a path and MAESTRO to check you haven't missed a whole area.

## The lethal trifecta

An agent that, **within one request or run**, has (1) access to private data, (2) exposure to untrusted content, and
(3) a way to communicate externally can be turned into an exfiltration channel by one injected instruction (Simon Willison's framing, presented in [MCP ch7]).
Evaluate it per flow, not per product: the fix is usually to cut one leg for that request, not to remove a feature.

Count these as legs even when they look harmless:

- **Private data**: anything the user or org would not publish: other repositories, inbox, CRM records, the
  conversation itself, memory, system prompt contents, credentials visible in context.
- **Untrusted content**: anything an outsider can write: web pages, inbound email, public issues and PRs, shared
  documents, third-party tool results, product reviews, file uploads, images and screenshots, calendar invites,
  tool descriptions from third-party servers.
- **External channel** (the leg most often missed): outbound HTTP (data in URL query strings or paths), email/chat
  send, creating issues, PRs, comments or public posts, webhooks, writing to shared or public documents, markdown images
  or links rendered by the client (the URL itself carries data), link unfurling, DNS lookups from a sandbox, arguments
  sent to third-party APIs, logs or traces shipped to an external vendor. Also: creating or updating a calendar event
  with attendees (the provider emails them the title, description and attachments), sharing a file or folder, push,
  SMS or chat notifications, and opening a link at all (the GET itself reaches the attacker's server, and one-click
  links perform actions).

Worked case [MCP ch7]: a malicious issue in a public repository told a coding agent to read the user's private
repositories and publish them in a pull request. All three legs were present in one run. The demonstrated fix cut the
private-data leg per request: gateway middleware refused access to any repository other than the one the session
started in, and OAuth tokens were scoped to a single repository.

**MCP Colors** (stricter variant, [MCP ch7]): label each tool red (handles untrusted content) or blue (critical action),
treat all data as private by default, and never mix red and blue tools in one agent or server. Use it when you design
tool servers; use the trifecta check when you analyse a running agent.

## Threat entries

Each entry: what it is, where it enters, what to look for, control family.

### T1 Direct prompt injection
The user writes text that tries to override the application's instructions. **Look for:** public or semi-trusted
users with access to side-effecting tools; system prompts that contain secrets or rules that matter.
**Control:** treat user input as data; enforce rules in the gate; never put secrets in prompts.

### T2 Indirect prompt injection
Instructions planted in content the agent reads later. The model sees one token stream and has no reliable way to tell
instructions from data; attackers imitate delimiters, fake earlier turns or fake error messages [MESH ch11].
**Look for:** any untrusted source in the input inventory that shares a context with tools that write or send.
**Control:** trifecta cut; quarantine patterns (plan-then-execute, dual LLM); taint-gated egress; scanning tool output
with higher sensitivity than user input [DEFGUIDE ch12].

### T3 Jailbreak
Getting the model to bypass its own safety training (role-play, claimed authority, topic drift, low-resource
languages, optimised nonsense strings) [MESH ch11]. Different target from injection: a jailbreak attacks the model
vendor's policy; an injection attacks your application's authority over your tools [MCP ch7]. Model upgrades help with
jailbreaks; only architecture helps reliably with injection. **Control:** content guardrails and vendor safety for the
first; the rest of this catalog for the second.

### T4 Tool poisoning, name shadowing, rug pulls
Tool names, descriptions and schemas are loaded into context, so a malicious or compromised server injects through them [MCP ch7].
A server can also shadow another server's tool name, or change its tool list after the user approved it.
**Look for:** third-party MCP servers, unpinned versions, tool lists fetched at runtime, no namespacing.
**Control:** show descriptions to a human and re-consent when the tool list changes; namespace tools by server;
pin versions; vet registries [MCP ch4].

### T5 Excessive agency
More tools, data or permission than the task needs. Example: an agent with a raw SQL tool "optimised" a production
database by dropping half the rows of a table [BUILDAPPS ch4]. **Look for:** `execute_sql`, `run_shell`, `http_request`
to any URL, admin-scoped tokens, write access for read-only jobs. **Control:** intent-level tools, read-only accounts,
default-deny visibility, progressive access.

### T6 Data exfiltration
Private data leaves through an external channel (list above). Often the payoff of T2. **Look for:** any trifecta flow;
markdown rendering of model output with remote images; URL-fetch tools without a domain allowlist. A fetch tool that
follows redirects is also an SSRF path to internal services and cloud metadata endpoints. **Control:** cut a leg;
egress proxy with allowlist; block private IP ranges and metadata endpoints; no remote image rendering; recipient
allowlists.

### T7 Credential exposure
Secrets reach the context window, tool output, logs, or an inherited environment. A "get secret" tool returns the secret
to the model, which can log it, repeat it or send it to the wrong place [MESH ch11]. A local stdio MCP server inherits the
client's environment variables unless you restrict them [MCP ch8]. **Look for:** keys in prompts, `os.environ` passed
wholesale to subprocesses, tokens in tool results, secrets in traces. **Control:** credential broker; minimal env per
server; log scrubbing; short-lived scoped tokens.

### T8 Confused deputy and token pass-through
A privileged component uses its privilege for a less privileged caller. In MCP: a server forwards the client's token to
a downstream API (breaks attribution, lets stolen tokens be replayed through you), or a proxy uses one static OAuth
client ID for all users, so consent can be skipped [MCP ch7]. **Control:** accept only tokens issued for your server
(audience check); use your own credentials downstream; per-client consent stored server-side; exact redirect-URI match;
single-use `state`.

### T9 Identity and privilege abuse between agents
Agents impersonate each other, inherit a caller's broader rights, or share one service account so nothing can be
attributed or revoked individually [MESH ch11], [MESH ch12]. **Control:** per-agent workload identity; scoped delegated
tokens that never exceed the delegator's rights; authorisation per call in a policy engine.

### T10 Insecure inter-agent communication
Messages between agents are unauthenticated, unencrypted or free text that the receiver treats as instructions.
**Control:** mTLS, authenticated and schema-validated messages; the receiver treats content as data and applies its own
gate.

### T11 Memory and context poisoning
Injected or wrong content is written to memory and biases later runs. In the travel-agent walkthrough the exfiltration
run is stored as a successful task, so it becomes reference material for future plans [DEFGUIDE ch12]. A 2026 study cited in
[ILLUSTRATED ch10] found that poisoning one part of a personal agent's persistent state raised attack success from
about 25% to 64-74%. **Look for:** memory writes from runs that read untrusted content; shared memory across users;
"learned procedures" saved without review. **Control:** validated writes, provenance, tenant isolation, purge path.

### T12 Unexpected code execution
Model-written code or commands run where they can reach the host, secrets or the network: `exec`/`eval` on model
output, `shell=True`, deserialising model output, path traversal in file tools. A component named "sandbox" that calls
`exec` in-process is not a sandbox. **Control:** sandbox tiers ([sandboxing.md](sandboxing.md)); resolve-then-check paths.

### T13 Supply chain
Tools, MCP servers, agent cards, prompts, skill files, packages the agent installs at runtime, model weights,
registries. **Control:** pin and verify versions; allowlisted registries; review tool descriptions; build attestation;
an agent bill of materials.

### T14 Cascading failures and unbounded consumption
Loops, retries, recursive tool calls and agent fan-out amplify one bad decision or run up cost; a flawed plan executed
by many downstream agents repeats the error [DEFGUIDE ch12]. **Control:** per-task budgets (calls, parallelism, wall
time, money), loop detection, circuit breakers, safe degradation.

### T15 Human-agent trust exploitation
A compromised agent writes a persuasive justification so the approval click becomes the attack [DEFGUIDE ch12];
reviewers suffer automation bias, alert fatigue and skill decay [BUILDAPPS ch12]; per-command approval protects only
people who can read the command [ILLUSTRATED ch10]. **Control:** hard limits that hold after a yes; reviewer view that
leads with the exact action; rare, routed escalations ([human-oversight.md](human-oversight.md)).

### T16 Rogue or over-helpful agent (no attacker)
Goal drift, completion bias, reward hacking, chaining tools nobody anticipated while staying inside formal permissions
[DEFGUIDE ch6]. Canonical case: an agent told to take no action without approval deleted more than two hundred emails,
most likely because context compression dropped the instruction; remote attempts to stop it failed [ENTERPRISE ch7].
**Control:** rules in code, not prompt; behaviour monitoring; a stop control that works remotely.

### T17 Improper output handling
Model output flows into SQL, HTML, shell, templates or another system without encoding, so the model becomes an
injection vector for classic bugs (XSS in the chat UI, SQL injection in a reporting tool). **Control:** treat model
output as untrusted input to every downstream system: parameterise, escape, validate against schema.

### T18 Sensitive information and hidden context exposure
System prompts, retrieved documents, memory, tool responses or another tenant's data surface in answers. A memory leak
is a behavioural failure: protected data resurfaces in the wrong conversation [SYSTEMS ch9]. **Control:** no secrets in
prompts; tenant filters enforced in retrieval code; PII redaction on output; retention limits.

### T19 Computer-use and browser specifics
Screen and page text is untrusted content; the agent often holds logged-in sessions (private data) and can type, post or
buy (external channel), so a browser agent is a trifecta by default. Anthropic's tests of its browser agent measured
attack success of 23.6% without mitigations and 11.2% with them (2025, external; see [owasp-mapping.md](owasp-mapping.md) sources).
**Control:** dedicated VM or profile with no personal sessions, domain allowlist, confirmation for purchases, posting,
sharing personal data and accepting terms ([sandboxing.md](sandboxing.md)).

## Propagation path worksheet

Fill one row per hop for each priority path. Example, written fresh: a support agent that reads inbound email,
looks up orders, and can send replies and issue refunds.

| Hop | What happens | Control today | Gap | Proposed control |
|---|---|---|---|---|
| Source | Attacker emails support; body hides an instruction to send the customer list to an outside address | None (email is "just data") | Untrusted text enters the same context as `send_email` | Mark email as taint source |
| Plan | Model adds "export customers, email to X" to its plan | System prompt says "only reply to the sender" | Prompt-only rule | Recipient check in gate: reply-to-sender only |
| Tool call | `lookup_orders(all)` then `send_email(to=outsider)` | Tool schema validation | In-contract call from a hijacked plan | Tenant-scoped lookup; egress after taint needs approval; recipient allowlist |
| Effect | Data leaves | None | No egress control | Above; audit alert on bulk reads |
| Persistence | Run stored as a resolved ticket and reused as an example | Auto-save of resolved tickets | Poisoned exemplar | Don't save tainted runs as exemplars; provenance on memory |
| Recovery | Discovered days later | Partial logs | No tool-call audit | Structured audit of every call and decision; per-agent kill switch |

## No-attacker paths to always check

- Destructive operation chosen to "complete" a task (delete, drop, overwrite, force-push).
- Retry or loop that repeats a side effect (double email, double refund): needs idempotency keys.
- Safety instruction lost to context compression or a long run.
- Wrong tenant or wrong record chosen because of an ambiguous identifier.
- Cost runaway from fan-out or a stuck loop.
