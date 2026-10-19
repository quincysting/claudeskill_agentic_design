# MCP servers and clients, A2A, Skills: design and review

Depth for step 11. Version-specific names, codes and dates are in [current-facts-2026-10.md](current-facts-2026-10.md); this file covers the design decisions that change slowly. Citation keys are listed under Sources in SKILL.md.

## §1 What MCP is and is not

MCP is a standard client-server protocol between an agent host and capabilities it does not own. It turns M models × N tools of custom connectors into M + N [MCP ch1]. The host runs one MCP client per server, each client relays messages for one server and decides what reaches the model, and servers expose tools, resources and prompts over JSON-RPC [MCP ch2].

Keep it in proportion:
- MCP is an **integration contract**. Choosing the workflow, enforcing business rules and being the main security boundary are jobs for other layers [SYSTEMS ch7].
- To the model, an MCP tool is just another function definition. MCP changes who writes, hosts and distributes the tool, not how the model calls it.
- Trust is split three ways. The **server** guards its own resources (tokens, scopes, per-tenant access). The **client** guards the user (which servers, which tools, which consents; tool definitions and results are untrusted input) [MCP ch4]. The **agent runtime** still enforces policy. None replaces the others.

## §2 Choosing the integration

| Question | If yes |
|---|---|
| Will anyone other than this one agent use the capability (other hosts, teams, customers)? | MCP server |
| Does it need per-user auth, or must it run off the agent's machine? | Remote MCP server with OAuth |
| Is it only for your own agent, in your own codebase? | Native function calling; add MCP later if reuse appears |
| One developer, a shell, and a CLI the model already knows? | CLI (cheaper in tokens than an equivalent server for that user) |
| Production agent with no shell, or no CLI exists? | Not a CLI [MCP ch2] |
| Is the gap procedure (how to use existing tools well), not access? | Agent Skill |
| Do users need tool detail only sometimes? | Ship a Skill beside the MCP server to load detail on demand [MCP ch2] |
| Is the counterpart a whole agent owned by another team or company, with its own tools and policies, and you want an outcome? | A2A |
| Are both sides your agents in one deployment? | Function call or subagent; A2A adds latency without isolation |

Skills carry instructions and optionally scripts, but a script runs with the tools and credentials the agent already has. A Skill brings no service, no auth flow and no remote execution [ILLUSTRATED ch5], [MCP ch2]. Use that as the dividing line between a Skill and a server.

## §3 Server design

**Primitives: who decides when it is used** [MCP ch5]

| Primitive | Controller | Use for | Not for |
|---|---|---|---|
| Tool | Model | Actions and lookups the model should choose | Data the host should attach on its own |
| Resource (URI-addressed data) | Application | Context the host attaches, large or binary data, data a tool links to | Anything the model must decide to fetch (make it a tool) |
| Prompt (parameterised template) | User | Tested workflows the user invokes, like `/code-review` | Expecting the model to pick prompts itself |

Nothing enforces the controller column: a client may call anything. Design for the intended path and document it [MCP ch5].

**Server checklist**
- [ ] Tools cut from agent stories and namespaced; a modest number of active tools (the MCP book warns at 12-20 [MCP ch5]); users also run other servers.
- [ ] Deterministic tool order; cache hints set if the list is stable.
- [ ] Inputs typed and validated by the SDK from the same type the handler reads (no hand-maintained schema beside the code), plus business validation and state checks in the handler. For each output type, an output schema with structured content and a text rendering.
- [ ] Results in one envelope (tool-contracts §3): receipts for writes, wrapped collections, opaque IDs, and state-dependent next actions in results, never by changing `tools/list`.
- [ ] Errors: model-fixable and business-rule failures as tool errors with readable messages and a problem-details body with a category (tool-contracts §4); protocol errors only for unknown tool, malformed request, missing client capability. Check how your SDK maps exceptions: in Python SDK v2 only `ToolError` text reaches the model.
- [ ] No per-connection state. Cross-call state through explicit handles that are authorised on every call.
- [ ] Side-effecting tools idempotent under re-sent requests.
- [ ] Confirmations through elicitation; secrets, payments and third-party consent through URL-mode elicitation only.
- [ ] Long jobs through the Tasks extension if your SDK and target clients support it, otherwise a start tool plus a status tool.
- [ ] Large data as resource links or URLs, not inline Base64; messages under about 100 KB [MCP ch8].
- [ ] stdio servers log to stderr only, because stdout carries the protocol [MCP ch8].
- [ ] Every path parameter resolved and checked for containment before use. Tool parameters get no automatic traversal protection [MCP ch7].
- [ ] Database and shell access through parameterised queries, allowlists, restricted accounts and sandboxing [MCP ch7]; free-form query tools follow the single rule in tool-design-rules §7.
- [ ] Remote: TLS, authentication on every request, per-object and per-tool access control, rate limiting [MCP ch7], [MCP ch8], with limits and quotas per principal, per client and per tool (tool-design-rules §7).
- [ ] No token pass-through: the server holds its own downstream credentials [MCP ch7].
- [ ] No deprecated features in new code (sampling, roots, protocol logging).
- [ ] Tested in an inspector, with automated tests on the critical paths and a tool-choice eval run against several models, since a server author does not pick the user's model [MCP ch7]. Tests run with the credentials and token scopes real callers have, not an admin's.
- [ ] One supported install path: a remote URL, a registry entry, a container image or a bundle [MCP ch7]. Registered in the catalogue with an owner, a version and a namespace; changes follow tool-contracts §8 and retirement follows catalog-governance §5.

**Gating by state on a stateless protocol.** A 2026-07-28 server must not vary `tools/list` per connection or as a side effect of earlier requests. It may vary the list by the authorization on the request. So:
- *Permission tiers* (read-only vs can-refund) map to OAuth scopes. The list shows what the token allows, and step-up authorization unlocks more.
- *Workflow order* (look up before refund) cannot be expressed by hiding tools. The handler re-checks the precondition from the backend and returns a tool error naming the missing step.
- A server-wide list change (`list_changed`) reaches every subscribed client. It is for deploys and feature flags, not for one user's progress.
- *Per-task exposure* is possible only where the tool list is assembled per turn: in a host or client you run, which can hand the model a subset of a server's tools. Older stateful revisions (2025-11-25 and earlier) let a server change one session's list, but an SDK v2 server also serves stateless clients, so do not build workflow order on it.

**Discovery happens in three layers.** Each answers a different question and changes at a different rate:

| Layer | Question it answers | Changes when | Where it lives |
|---|---|---|---|
| Catalogue | Which servers exist, and which are approved here? | A server is published, approved or retired | Registry, private subregistry, gateway [MCP ch9] |
| Tool list | What may this caller ever invoke on this server? | A deploy, or the caller's authorization | `tools/list` and list-changed notifications |
| Result | What makes sense next, in this state? | Every call | `next_actions` in the tool result [RESTCOOK ch3 §3.5], [RESTCOOK ch4 §4.9] |

A server that adds `refund_approve` to its list once a refund is pending breaks the middle layer's rule, defeats caching and pinned definitions, and gives two replicas two answers. Put the actions that are valid now in the result instead (tool-contracts §10). The outer layer has its own gap: the MCP Registry holds metadata and package pointers, not liveness, so checking that a catalogued server is up is the gateway's job [MCP ch9 §MCP Registry], [RESTCOOK ch5 §5.13]. Running the catalogue is in catalog-governance.md.

**Approval inside a tool call.** Use form-mode elicitation through the SDK's input mechanism. In Python SDK v2 that is a resolver-filled parameter hidden from the model's schema (code in current facts). Three rules:
1. Decide in the resolver, from the arguments, whether to ask at all (small amounts can pass without a prompt).
2. Treat decline and cancel as "do nothing", and say so in the result.
3. Plan for clients without elicitation. The call then fails with a protocol error before the tool body runs, which is safe but leaves the user stuck. Offer a propose-only companion tool (`refunds_request`) that records the pending action and returns a reference for a human to approve in your UI: a signed-in page in the system of record that decides on an explicit submit, never on opening the link (tool-design-rules §7). Never fall back to executing.

Host approval prompts (for example, Claude prompting on tools marked destructive) are a useful extra layer. Users and administrators can change those settings, so they do not replace the server's own gate. An elicitation answer only shows that the client said yes (a host can be set to answer automatically). Approvals that need a named, signed-in approver go through the propose-only path.

## §3a Serving tools into a host you do not control

When the server runs inside Claude Desktop or claude.ai connectors, an IDE, or a partner's agent:
- **Not yours:** the model, the system prompt, `tool_choice`, strict mode, tool search or deferred loading, parallel calls, result truncation, timeouts, and any task or conversation ID. Design as if none of them exists.
- **Yours:** the tool list and its descriptions, validation, authorization, state checks, idempotency on business keys, elicitation requests, error messages, result size, and the server `instructions` text (guidance only).
- **Check the host's support before relying on a feature:** the transports it accepts, elicitation, annotation handling, auth flow, result-size and timeout caps. Host notes as of 2026-10 are in current facts. Where a feature is unverified for a host, design a path that works without it.
- **Test in the real host** as well as in an inspector. Hosts differ in how they surface errors, approvals and large results.

## §4 Transport

| Consideration | stdio | Streamable HTTP |
|---|---|---|
| Where it runs | Subprocess of the host | Network service (local or remote) |
| Auth | None; trust is the local process boundary; credentials from the environment | OAuth 2.1 bearer tokens on every request (or API keys for simple cases) |
| Scaling | One server process per client | Stateless requests behind any load balancer or serverless |
| Main risks | Arbitrary code with the user's privileges; inherits environment variables | Network: TLS, per-request auth, DNS rebinding for local HTTP servers |
| Use for | Personal and developer tooling, local files | Anything shared, multi-user or production |

The MCP book's verdict: for production there is no real alternative to Streamable HTTP [MCP ch8]. For stdio, install only from trusted sources, pin versions, sandbox, and pass only the secrets the server needs instead of the whole environment. An HTTP server meant for one developer's machine is reachable over the network like any other, so listen on the loopback address (127.0.0.1) only and check the Origin header [MCP ch8]. For remote servers behind serverless platforms, CDNs or gateways that buffer responses, run stateless with plain JSON responses [MCP ch7]. The current spec defines only stdio and Streamable HTTP; anything else (WebSocket included) is a custom transport you maintain [MCP ch8].

## §5 Authorization (remote servers)

This section applies to HTTP transports. A stdio server has no bearer token: it authorises through its launch configuration and the environment it is given (which binary, which arguments, which credentials). Per-tool scopes therefore need an HTTP transport. On stdio, split read and write tools into separate servers or launch profiles with different credentials, and keep token checks out of stdio handlers and their tests.

Server, as an OAuth resource server:
- Publish protected-resource metadata. Answer unauthenticated requests with 401 and a pointer to that metadata, plus the scopes needed.
- Validate every inbound token in this order, and fail closed when a claim is **missing**, not only when it is wrong:
  1. Signature, with the algorithm pinned (never `none`, never whatever the token header names).
  2. `exp` present and in the future, `nbf`, and a maximum lifetime (`exp` minus `iat`). A check written as "reject if `exp` is set and past" accepts tokens that never expire.
  3. Issuer.
  4. Audience is this server. Reject everything else, and never forward a client's token downstream.
  5. Token type is an access token. ID tokens from the same identity provider verify against the same keys, so check `typ` or the provider's token-use claim.
  6. Client on an allowlist (the applications and partner agents you onboarded).
  7. The scopes this tool needs.
  8. Any policy claim you rely on, for example that the subject is a person.
  9. When agents call for users, the calling agent stays within a per-actor ceiling the server keeps itself.
- Take the user and tenant from the verified subject, never from a tool argument or a header the caller sets. Platforms often copy the subject into their own audit logs, so use opaque or pairwise subject IDs, not emails.
- **Verified, not asserted, identity.** Never offer or build on an "act as user `<id>`" or "get a token for user `<id>`" call that trusts a plain user ID from any caller holding a permission: it lets every holder impersonate every user. Behind a gateway or runtime that validates tokens for you, decode claims without verifying them only for logging, and only if every route to the server (every version, alias and endpoint) passes a verifying authorizer.
- On insufficient scope, return 403 `insufficient_scope` listing *all* scopes the operation needs in one challenge, not one at a time.
- Keep the advertised scope set minimal and let clients step up for more.

Client:
- Discover the authorization server from the metadata. Register in the current preferred way (see current facts). Use PKCE plus a `resource` parameter naming the server.
- Validate the issuer in the authorization response. Store credentials keyed by issuer. Send the bearer token on every request and never in the URL.
- On a scope challenge, re-authorise with the union of old and new scopes, with a retry limit.

**Another organisation's agent calling on behalf of its own users.** First decide the authorization grain.
- *Partner-level*: any record that came through that partner. The partner is a confidential client (pre-registration or the client-credentials extension), and the server checks every object against the partner's channel or account.
- *End-user-level*: only records of the specific end user. This needs an assertion of the user from the partner's identity provider that your authorization server trusts (Enterprise-Managed Authorization, token exchange or a signed user assertion).

Either way, expose a separate, smaller partner tool set rather than your internal agent's tools, rate-limit per partner, and log the partner and end-user reference on every call.

The protocol identifies the client application and binds tokens to a server. It does not give an agent an identity that survives delegation (user → agent A → agent B → tool). That takes per-hop scoped, short-lived tokens and an audit trail of "on whose behalf" [MESH ch12], [ENTERPRISE ch6]. Each hop exchanges the token it received for a new one with the same subject, an audience naming only the next hop and scopes that never widen, and it never forwards the original. The full delegation-chain rules (the invariants, where to enforce reach, and the tests) are in agent-threat-modeler. Managed agent platforms increasingly broker the exchange and propagate caller identity; use them, but check those invariants either way. Confused-deputy setups (a server proxying a third-party OAuth provider with its own static client ID) need agent-threat-modeler [MCP ch7].

## §6 Client and host design

- [ ] One client per server; tools namespaced by a server identity the host assigns from its own configuration, never `serverInfo.name` (it need not be unique), and resolved as `server::name` so one server cannot shadow another's tool [MCP ch4], [HARDMCP ch9]. Approved definitions hashed and rechecked every session [HARDMCP ch4]; pinning detail in agent-threat-modeler.
- [ ] Translate MCP tool names to the model API's allowed characters (some APIs reject the dots MCP allows) and keep a reverse map.
- [ ] Get the user's consent to new tool definitions before first use [MCP ch4], then keep consent rare: group related scopes into one decision, default to deny, remember grants, and diff definitions in code every session and on every list-changed notification. Only a diff that adds a tool, widens a scope or changes a sensitive definition (signing, payments, email, auth) goes to a person; log the rest [HARDMCP ch8], [HARDMCP ch4]. A prompt that fires many times a day trains people to click Allow without reading [HARDMCP ch8].
- [ ] Treat descriptions, annotations and results as untrusted input. Never base trust decisions on annotations from servers you do not control.
- [ ] Show tool inputs to the user before calling the server, confirm sensitive operations, and keep a person able to deny any call (spec); confirmation UI names the server that is asking.
- [ ] Elicitation duties under the 2026-07-28 spec: name the requesting server; offer decline and cancel and handle all three answers; let the user review and edit form answers before they are sent; in URL mode show the full URL and its domain, never pre-fetch it, and open it only after explicit consent; never collect secrets, payments or credentials through form mode. Servers bind each elicitation to the client and user it was issued for (current facts). A 2026-07-28 server can elicit only inside a result for a client request; with 2025-11-25 servers, which send `elicitation/create` themselves, drop prompts no request asked for [HARDMCP ch9].
- [ ] Map every result without loss (sketch below): carry `isError` onto the model API's error flag; keep `structuredContent` for the harness; join every content block, not only the first; serialise structured data as JSON, never as the language's default string form; cap the size and say in the text that it was cut; pass annotations to the harness as hints only, never as a permission tier. Test it with a forced failure through the real client (tool-design-rules §5).
- [ ] Read a category from error text only after the SDK's prefix. In the Python SDK v2 a `ToolError` reaches the client as `Error executing tool <name>: <message>` (as of 2026-10; confirm against the installed version), so a category token sits after the prefix, never first. When the harness must act on the category, the server returns it in `structuredContent` from a low-level handler (tool-contracts §4).
- [ ] Read the model's stop reason before running any tool call from its turn (tool-contracts §4b).
- [ ] Fetch server-supplied URLs, OAuth metadata included, only through an allowlist [HARDMCP ch8]; the controls are agent-threat-modeler's.
- [ ] Timeouts on every call. On a lost connection, retry with backoff and resend; dedupe non-idempotent calls, because a resend redoes the action [MCP ch4]. A timeout or transport error on any tool that is not read-only maps to `outcome_unknown` (tool-contracts §5), never to a plain failure with the error flag set.
- [ ] Budget the tool list: count definition tokens per server and apply the selection ladder (scoping, tool search) when it grows.
- [ ] One translator per model family from MCP tool types to the provider's format, to stay model-agnostic [MCP ch4].
- [ ] Pin local server versions; prefer servers from a trusted registry or your own subregistry of approved servers [MCP ch4], [MCP ch9].
- [ ] A server that fails to connect at start-up stops the agent, or the agent runs marked degraded with the missing tools named; it is never skipped silently. Log the server's name and transport, never its environment, headers or arguments, which can carry secrets.
- [ ] Log every call with server, tool, arguments, outcome and latency; propagate trace context.

A result-mapping sketch for a Python client on SDK v2 that feeds the Claude Messages API (attribute names as of 2026-10; confirm against the installed version):

```python
import json

def map_result(call_id: str, r, cap_chars: int = 20_000):
    """MCP CallToolResult -> (tool_result block for the model, structured envelope for the harness)."""
    parts = [b.text if b.type == "text" else f"[{b.type} content not shown]" for b in r.content]
    text = "\n".join(parts) or (json.dumps(r.structured_content)  # every block; JSON, never str()
                                if r.structured_content is not None else "(no content)")
    if len(text) > cap_chars:
        text = text[:cap_chars] + f"\n[truncated: {len(text) - cap_chars} more characters]"
    block = {"type": "tool_result", "tool_use_id": call_id, "content": text,
             "is_error": bool(r.is_error)}                         # the flag survives the hop
    return block, r.structured_content                             # category and receipt for the harness
```

**Gateways.** A gateway puts many servers behind one authenticated endpoint, can expose a subset of tools, and can enforce per-request policy no single server sees. In a 2025 researcher demonstration against the GitHub MCP server, a malicious issue in a public repository told an agent to copy private repository data into a public one (the MCP book describes the planted text as a pull request). A gateway rule refusing cross-repository access within one request blocked it [MCP ch7]. Use a gateway or a private subregistry once you have many servers, one auth story to enforce, or a vetted-server policy [MCP ch9].

A gateway is a control only when it is the only route: the servers and backends behind it accept calls only from the gateway's identity, and the gateway itself authenticates every caller (without that, identity-aware rules have no caller to check). Its policy rules see the request, not the record's state, so servers keep their own state checks (tool-design-rules §7). Managed gateways also tend to rename tools with a target prefix, negotiate an older protocol revision by default and return denials in their own shape; check each (current facts, "Managed MCP gateways").

## §7 A2A

Use it when the other side is an agent you do not control, with its own tools, data, model and policies, and you want an outcome rather than a function result [ILLUSTRATED ch8]. The remote agent publishes an agent card (identity, endpoint, skills, security schemes) at a well-known URL. The client authenticates as the card says, sends a task, and gets status updates, follow-up questions (input required, auth required) and finally artifacts. The card's "skills" describe capabilities and are unrelated to Agent Skills.

Design points:
- MCP for tools, A2A between agents; treat proprietary agent protocols with caution [ENTERPRISE ch8].
- The wire format is settled; trust between organisations, authorization across delegation chains, rate limiting and abuse resistance are still mostly yours [BUILDAPPS ch8].
- Long tasks are first-class: design for streamed progress, input-required pauses and push notifications instead of blocking calls.
- A2A can also act as a governance plane. One design puts an A2A "governor" between a planner and its MCP servers that checks every tool request against allowlists, budgets and approval rules and records each decision [DEFGUIDE ch6].
- Start from the official specification and SDKs. Several book examples use pre-1.0 field names and the old card path [BUILDAPPS ch8].
- Other inter-agent protocols exist (IBM's ACP, the Agent Name Service, Cisco's AGNTCY) [AISEC ch3]. ACP's status is unresolved: AISEC treats it as A2A's competitor, while ENTERPRISE reports it merged into A2A in late 2025 [ENTERPRISE ch8]. Plan on A2A between organisations and check ACP's own status before depending on it (current facts).

## §8 Review order for an MCP server

1. Transport and deployment fit (production on Streamable HTTP, stateless).
2. Auth: the receiver checklist in §5 (missing claims fail closed), no pass-through (own credential or an exchanged token per backend), no user IDs accepted as plain strings, scopes, 401 and 403 behaviour; every backend reachable only through the server or gateway that applies the checks.
3. Tool surface: intent-level, namespaced, count, descriptions, schemas (run the tool-design checks).
4. Error mapping in the actual SDK and the actual client: does the model see the messages you wrote, with the error flag, and does the harness get the category?
5. Contracts and side effects: receipts, idempotency under resend (key from run state, or a business-object key plus a state check), reversibility, approvals via elicitation, handles, next actions in results (tool-contracts).
6. Injection surfaces: paths, SQL, shell, fetched content; all three Rule-of-Two legs (untrustworthy inputs; sensitive systems or private data; the ability to change state or communicate externally) across the server's tools in one session, the lethal trifecta included (hand off to agent-threat-modeler if present).
7. Deprecated or removed features, SDK version pinning, and the catalogue entry (owner, version, namespace, retirement plan).
8. Tests and inspector runs under real callers' credentials, tool-choice eval across models, distribution path.
