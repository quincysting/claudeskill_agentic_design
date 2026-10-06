# MCP servers and clients, A2A, Skills: design and review

Depth for step 11. Version-specific names, codes and dates are in [current-facts-2026-10.md](current-facts-2026-10.md); this file covers the design decisions that change slowly. Citation keys are listed under Sources in SKILL.md.

## §1 What MCP is and is not

MCP is a standard client-server protocol between an agent host and capabilities it does not own. It turns M models × N tools of custom connectors into M + N [MCP ch1]. The host runs one MCP client per server, each client relays messages for one server and decides what reaches the model, and servers expose tools, resources and prompts over JSON-RPC [MCP ch2].

Keep it in proportion:
- MCP is an **integration contract**. It does not decide the workflow, enforce business policy or act as the primary security boundary [SYSTEMS ch7].
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
- [ ] Inputs typed and validated by the SDK, plus business validation in the handler. For each output type, an output schema with structured content and a text rendering.
- [ ] Errors: model-fixable and business-rule failures as tool errors with readable messages; protocol errors only for unknown tool, malformed request, missing client capability. Check how your SDK maps exceptions: in Python SDK v2 only `ToolError` text reaches the model.
- [ ] No per-connection state. Cross-call state through explicit handles that are authorised on every call.
- [ ] Side-effecting tools idempotent under re-sent requests.
- [ ] Confirmations through elicitation; secrets, payments and third-party consent through URL-mode elicitation only.
- [ ] Long jobs through the Tasks extension if your SDK and target clients support it, otherwise a start tool plus a status tool.
- [ ] Large data as resource links or URLs, not inline Base64; messages under about 100 KB [MCP ch8].
- [ ] stdio servers log to stderr only, because stdout carries the protocol [MCP ch8].
- [ ] Every path parameter resolved and checked for containment before use. Tool parameters get no automatic traversal protection [MCP ch7].
- [ ] Database and shell access through parameterised queries, allowlists, restricted accounts and sandboxing [MCP ch7]; free-form query tools follow the single rule in tool-design-rules §7.
- [ ] Remote: TLS, authentication on every request, per-object and per-tool access control, rate limiting [MCP ch7], [MCP ch8].
- [ ] No token pass-through: the server holds its own downstream credentials [MCP ch7].
- [ ] No deprecated features in new code (sampling, roots, protocol logging).
- [ ] Tested in an inspector, with automated tests on the critical paths and a tool-choice eval run against several models, since a server author does not pick the user's model [MCP ch7].
- [ ] One supported install path: a remote URL, a registry entry, a container image or a bundle [MCP ch7].

**Gating by state on a stateless protocol.** A 2026-07-28 server must not vary `tools/list` per connection or as a side effect of earlier requests. It may vary the list by the authorization on the request. So:
- *Permission tiers* (read-only vs can-refund) map to OAuth scopes. The list shows what the token allows, and step-up authorization unlocks more.
- *Workflow order* (look up before refund) cannot be expressed by hiding tools. The handler re-checks the precondition from the backend and returns a tool error naming the missing step.
- A server-wide list change (`list_changed`) reaches every subscribed client. It is for deploys and feature flags, not for one user's progress.
- *Per-task exposure* is possible only where the tool list is assembled per turn: in a host or client you run, which can hand the model a subset of a server's tools. Older stateful revisions (2025-11-25 and earlier) let a server change one session's list, but an SDK v2 server also serves stateless clients, so do not build workflow order on it.

**Approval inside a tool call.** Use form-mode elicitation through the SDK's input mechanism. In Python SDK v2 that is a resolver-filled parameter hidden from the model's schema (code in current facts). Three rules:
1. Decide in the resolver, from the arguments, whether to ask at all (small amounts can pass without a prompt).
2. Treat decline and cancel as "do nothing", and say so in the result.
3. Plan for clients without elicitation. The call then fails with a protocol error before the tool body runs, which is safe but leaves the user stuck. Offer a propose-only companion tool (`refunds_request`) that records the pending action and returns a reference for a human to approve in your UI. Never fall back to executing.

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

The MCP book's verdict: for production there is no real alternative to Streamable HTTP [MCP ch8]. For stdio, install only from trusted sources, pin versions, sandbox, and pass only the secrets the server needs instead of the whole environment. A "local" HTTP server is still a network server: bind it to 127.0.0.1 and validate the Origin header [MCP ch8]. For remote servers behind serverless platforms, CDNs or gateways that buffer responses, run stateless with plain JSON responses [MCP ch7]. The current spec defines only stdio and Streamable HTTP; anything else (WebSocket included) is a custom transport you maintain [MCP ch8].

## §5 Authorization (remote servers)

Server, as an OAuth resource server:
- Publish protected-resource metadata. Answer unauthenticated requests with 401 and a pointer to that metadata, plus the scopes needed.
- Accept only tokens issued for this server (audience check). Reject everything else, and never forward a client's token downstream.
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

The protocol identifies the client application and binds tokens to a server. It does not give an agent an identity that survives delegation (user → agent A → agent B → tool). Per-hop scoped, short-lived tokens and an audit trail of "on whose behalf" remain your design work [MESH ch12], [ENTERPRISE ch6]. Confused-deputy setups (a server proxying a third-party OAuth provider with its own static client ID) need agent-threat-modeler [MCP ch7].

## §6 Client and host design

- [ ] One client per server; tools namespaced per server so one server cannot shadow another's tool [MCP ch4].
- [ ] Translate MCP tool names to the model API's allowed characters (some APIs reject the dots MCP allows) and keep a reverse map.
- [ ] Show users new tool definitions and get consent before first use; re-ask whenever the server's list changes [MCP ch4].
- [ ] Treat descriptions, annotations and results as untrusted input. Never base trust decisions on annotations from servers you do not control.
- [ ] Show the inputs of sensitive calls to the user before sending; confirmation UI names the server that is asking.
- [ ] Handle elicitation accept, decline and cancel; let the user cancel at any time; never collect secrets through form mode.
- [ ] Timeouts on every call. On a lost connection, retry with backoff and resend; dedupe non-idempotent calls, because a resend redoes the action [MCP ch4].
- [ ] Budget the tool list: count definition tokens per server and apply the selection ladder (scoping, tool search) when it grows.
- [ ] One translator per model family from MCP tool types to the provider's format, to stay model-agnostic [MCP ch4].
- [ ] Pin local server versions; prefer servers from a trusted registry or your own subregistry of approved servers [MCP ch4], [MCP ch9].
- [ ] Log every call with server, tool, arguments, outcome and latency; propagate trace context.

**Gateways.** A gateway puts many servers behind one authenticated endpoint, can expose a subset of tools, and can enforce per-request policy no single server sees. In the 2025 GitHub MCP incident a malicious pull request told an agent to copy private repository data into a public one. A gateway rule refusing cross-repository access within one request blocked it [MCP ch7]. Use a gateway or a private subregistry once you have many servers, one auth story to enforce, or a vetted-server policy [MCP ch9].

## §7 A2A

Use it when the other side is an agent you do not control, with its own tools, data, model and policies, and you want an outcome rather than a function result [ILLUSTRATED ch8]. The remote agent publishes an agent card (identity, endpoint, skills, security schemes) at a well-known URL. The client authenticates as the card says, sends a task, and gets status updates, follow-up questions (input required, auth required) and finally artifacts. The card's "skills" describe capabilities and are unrelated to Agent Skills.

Design points:
- MCP for tools, A2A between agents; treat proprietary agent protocols with caution [ENTERPRISE ch8].
- The wire format is settled; trust between organisations, authorization across delegation chains, rate limiting and abuse resistance are still mostly yours [BUILDAPPS ch8].
- Long tasks are first-class: design for streamed progress, input-required pauses and push notifications instead of blocking calls.
- A2A can also act as a governance plane. One design puts an A2A "governor" between a planner and its MCP servers that checks every tool request against allowlists, budgets and approval rules and records each decision [DEFGUIDE ch6].
- Start from the official specification and SDKs. Several book examples use pre-1.0 field names and the old card path [BUILDAPPS ch8].

## §8 Review order for an MCP server

1. Transport and deployment fit (production on Streamable HTTP, stateless).
2. Auth: audience check, no pass-through, scopes, 401 and 403 behaviour.
3. Tool surface: intent-level, namespaced, count, descriptions, schemas (run the tool-design checks).
4. Error mapping in the actual SDK: does the model see the messages you wrote?
5. Side effects: idempotency under resend, approvals via elicitation, handles.
6. Injection surfaces: paths, SQL, shell, fetched content; the lethal trifecta across the server's tools (hand off if present).
7. Deprecated or removed features, and SDK version pinning.
8. Tests, inspector runs, tool-choice eval across models, distribution path.
