# MCP hardening: hosts, clients and servers

Use this when the agent connects to MCP servers (host or client side), or when the team runs or publishes a server.
MCP is an integration contract, not a security boundary [SYSTEMS ch7]. The specification covers authorization and
transport, but injection through tool content, definitions that change after approval and most operational defaults
are left to you. Give every control below a test that behaves like an anonymous or hostile caller and reruns on every
deploy: a declared control proves nothing until the running system refuses [HARDMCP ch5].

Dated facts (as of 2026-10, verify before quoting): the current specification is 2026-07-28 (its changelog and
security page checked 2026-10-19). An early-2026 scan of
more than 11,500 public servers graded about one in fourteen as failing; about 78% pinned no dependencies, 81% ran
unsandboxed, 86% published no way to report a vulnerability, and no release carried a verified signature
[HARDMCP ch1]. Keep these figures out of rules; they show why defaults, not the spec, set most of the risk.

## 1. Tool identity and definition integrity (host side)

| Control | How | Test (rerun every session or deploy) | Source |
|---|---|---|---|
| Resolve tools by `server::name` | The host or a gateway prefixes every tool with the server that offered it before the model reads the list. An unqualified name offered by two servers is refused, never settled by registration order, which nobody controls | Two servers offer the same name: the call is refused as ambiguous | [HARDMCP ch9] |
| Pin approved definitions per session | At approval, hash a canonical form of the whole definition (sorted keys; description, parameter schema and every other field, since an unhashed field is where a payload hides). Recompare at every session; on mismatch halt the call and show a readable diff | Changed description on an approved tool: call halted, re-approval required | [HARDMCP ch4] |
| Remember offenders | Keep a local record of each server's unannounced changes; a server with one on file starts every session from suspicion. Don't borrow trust from marketplace ratings | A server that changed, reverted and changed again is halted the second time too | [HARDMCP ch4] |
| Tier by capability, not wording | Tools that sign, move money, send mail, mint account identifiers or touch authentication are sensitive: a change re-prompts a person with refusal as the default. Other changes are logged. Re-tier when a tool gains a capability | Mutated payment tool waits for a person; mutated memo tool logs and proceeds | [HARDMCP ch4] |
| Scan descriptions at load | Quarantine descriptions with instruction markers for human review. A tripwire that raises the attacker's cost, not a wall | Description containing a known marker is held, not shown to the model | [HARDMCP ch6] |
| Fence and label each source | Render descriptions in a bounded, lower-trust block; strip cross-tool directions; attach provenance and a trust label when content enters context, never later | A description that tries to steer another tool has no effect on it | [HARDMCP ch6] |
| Scope context per server and tenant | Each server and each tenant sees only its own slice; clear it when the task ends | A server reading another server's results, or another tenant's, is denied | [HARDMCP ch9] |
| Least agency per server | The fewest tools and scopes the server's role needs; write down what each server is for; don't connect a capable server for a small job | A narrow server's call to a payment tool is denied whatever reached its context | [HARDMCP ch9] |
| Show and re-consent | Show tool descriptions to the user; re-obtain consent when the tool list changes | A new or changed tool is unavailable until consent | [MCP ch4] |

A minimal canonical hash (fresh, illustrative), stored per `server::name` at approval:

```python
import hashlib, json

def definition_hash(tool: dict) -> str:
    # Every field the server sent, in a stable form, so reordering never alarms and any edit does.
    return hashlib.sha256(json.dumps(tool, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
```

## 2. Supply chain (build side)

- Pin the whole resolved dependency tree to versions and hashes, not only the names you typed; a hash mismatch fails
  the install [HARDMCP ch3].
- Audit the pins against advisories as a build gate that fails rather than warns, on a schedule as well as on change.
  Tag libraries that could forge, leak or bypass an identity (token and JWT parsers, cryptography, the TLS-terminating
  HTTP client) for a shorter update window [HARDMCP ch3].
- Install prebuilt, hash-checked artifacts only, so no install script runs; build the rare exception once, reviewed,
  in an isolated environment [HARDMCP ch3].
- Install from a vetted private index that acts as a name allowlist; typosquats sit one keystroke from a real name
  and can arrive several levels deep in the tree [HARDMCP ch3].
- Pin the server version you approved and prefer vetted registries; an update is a new approval, and section 1 still
  rechecks its definitions every session.
- Verify a signed release before launch and keep an inventory of every server, version and place it runs
  [HARDMCP ch10]. Catalogue lifecycle and retirement: agent-tool-designer.
- One-click local install commands run only after the user sees the full command and consents (spec 2026-07-28).

Tool names in the book (pip-compile, pip-audit, cosign) are examples, not endorsements.

## 3. The front door (server side)

- One authentication middleware on every request, `tools/list` included: a public catalogue maps the attack surface
  for free. The middleware validates the token (section 4); it doesn't just check that a header is present
  [HARDMCP ch5].
- Refuse uniformly ("unauthorized"); keep the reason for your own logs, so a caller can't learn which check failed
  [HARDMCP ch5].
- Authorise each call for the specific tool, with a scope per tool [HARDMCP ch5], and evaluate it as granted scope
  intersected with the user's own entitlements ([controls-catalog.md](controls-catalog.md) §2 Access rules). The MCP
  book's OAuth example requires read and write scope for every tool [MCP repo: ch7/03_mcp_oauth_resource_server]; don't
  copy that.
- Probe the live endpoint on every deploy and on a schedule in production: an anonymous `tools/list` and an anonymous
  call must both be refused, and a refusal that turns into a response alerts. In the scan, 24 of 77 endpoints that
  declared authentication answered anonymous callers [HARDMCP ch5].
- Tool code treats every argument as attacker-written: no `eval`, shell strings or unsafe deserialisation on tool
  input; resolve paths before the root check; resolve URLs and refuse private ranges [HARDMCP ch2]. The Python SDK
  checks resource-template parameters but not tool parameters [MCP ch7].

## 4. Token acceptance and exchange

A valid signature proves a token is authentic, not that it was issued for you. Run these checks in order and refuse
uniformly at the first failure [HARDMCP ch7]:

1. **Signature**, with the algorithm pinned, against the pinned issuer's keys.
2. **Audience**: the token names this server as its resource (resource indicators, RFC 8707).
3. **Issuer**: matches the authority pinned in configuration. Clients also check the issuer on the authorization
   response (RFC 9207) and distrust whatever a discovery document announces.
4. **Expiry**.

These four are the minimum. The full receiver checklist (token type, client allowlist, scope, policy claims, a
per-actor ceiling at the resource, fail closed on a missing claim) is in [controls-catalog.md](controls-catalog.md) §3.

- **Exchange, never pass through.** To call a downstream service, trade the validated token for one minted for that
  resource (OAuth token exchange or the identity provider's on-behalf-of flow); forwarding the client's token breaks
  the audience boundary and the audit trail [HARDMCP ch7], [MCP ch7]. Delegation invariants:
  [controls-catalog.md](controls-catalog.md) §3.
- **Client flow.** PKCE with S256 is required, and a plain challenge counts as none; an unguessable `state` value is
  bound to the session and checked on the callback [HARDMCP ch7]; redirect URIs match exactly [MCP ch7].
- **Proxies.** Obtain consent per client, store it server-side, set a single-use `state` only after consent, and bind
  each upstream request to client, scope and operation. A static upstream client ID plus open dynamic registration plus a reused consent cookie lets one client
  inherit another's grant: the confused deputy in [threat-catalog.md](threat-catalog.md) T8 [HARDMCP ch7], [MCP ch7].

## 5. Consent and the credential store

- **Unframeable consent.** Forbid framing of the consent screen (a `frame-ancestors` policy of none, or
  `X-Frame-Options: DENY`), require a fresh deliberate gesture on Allow, and use a same-site session cookie
  [HARDMCP ch8].
- **Rare, legible consent.** Ask only when the grant carries weight, group related scopes into one plainly worded
  decision, default to deny, remember safe grants and ask again only when the scope grows or the client changes.
  A flow that asks often is less secure than a clumsier one that asks rarely [HARDMCP ch8].
- **Discovery is an SSRF path.** Endpoints named in authorization-server metadata must resolve to public, expected
  destinations before the client fetches them: refuse private, loopback and link-local (cloud metadata) addresses
  after DNS resolution, then pin the validated endpoints. Treat every server-supplied URL the same way
  [HARDMCP ch8].
- **Small credential store.** Short-lived tokens fetched per task, encryption for whatever must persist, and a secrets
  manager that releases one credential at a time and logs each release, so a breached tool gets only what it asked
  for [HARDMCP ch8]. The model never sees any of them ([controls-catalog.md](controls-catalog.md) §3).
- **State handles** are bound to the verified user; holding one is not authentication. Start with low-risk scopes and
  step up on demand (spec 2026-07-28 security best practices).

## 6. Sampling, elicitation and roots

Each of these protocol features gives a server some control over your client. Govern them at the host; the book notes they were
still evolving when it went to press, so recheck the current spec [HARDMCP ch10].

| Feature | Risk | Host or client control | Source |
|---|---|---|---|
| Sampling | A server drives your model: spend on your bill, prompts it wrote, completions that steer the agent | The client picks the model, shows the prompt for review and may edit or deny it; per-server rate and spend caps; deny when no person is present; treat the completion as untrusted input | [HARDMCP ch9] |
| Elicitation | Phishing for secrets; prompts the user never started | No passwords, keys, tokens or payment credentials through form mode; URL mode for sensitive steps, whose page neither client nor model reads; elicit only while handling a request the client started, drop the rest; handle decline and cancel as real outcomes | [HARDMCP ch9], [MCP ch6] |
| Roots | A server reads or writes outside the paths it was given | The host checks every file access against the granted roots; in the protocol, roots are advice to the server | [HARDMCP ch9] |

For URL mode the current spec also requires the client to show the full URL and never prefetch it, and the server to
check that the user who finishes the flow is the one who started it (elicitation page, spec 2026-07-28).

## 7. Runtime defaults

| Default | Setting | Test | Source |
|---|---|---|---|
| Containment | Read-only filesystem, capabilities dropped, non-root; set in the deployment manifest, not left to operator habit | Manifest review shows the flags on every environment | [HARDMCP ch10] |
| Bind address | Loopback unless a remote endpoint is genuinely needed; stdio for local servers | A request from another host times out | [HARDMCP ch10], [MCP ch8] |
| Reach | Host header allowlist, Origin validation against DNS rebinding, and authentication, on every local HTTP or WebSocket listener the deployment runs, not only the MCP server. Loopback is not authentication: pages in the user's own browser can reach localhost ([sandboxing.md](sandboxing.md) §Local listeners) | A request with a foreign Host header, a request from another origin and an unauthenticated request are each refused | [HARDMCP ch10], [MCP ch8] |
| Wire | Encryption on every hop, server to server included. HARDMCP asks for encryption on every hop, not specifically mutual TLS; mTLS is one way to meet it and also authenticates the peer | A plaintext hop found in a traffic review is a finding | [HARDMCP ch10] |
| Provenance | Signed releases verified before launch; inventory; a published disclosure contact (`security.txt`) | An unsigned build fails to launch | [HARDMCP ch10] |
| Audit | Structured record of actor, tool, arguments and request ID; redaction runs in the logging path itself and covers tool outputs | A logged call that carried a token shows the event without the secret | [HARDMCP ch10] |
| Abuse | Idempotency keys against replay, per-identity rate limits against floods, a signature check on tasks other servers hand over | A replayed key is rejected; a burst is throttled; an unsigned delegated task is refused | [HARDMCP ch10] |

Idempotency keys and receipts are also tool-contract fields (agent-tool-designer).

## 8. Where these land in the threat model

| Section | Threats ([threat-catalog.md](threat-catalog.md)) | OWASP agentic ([owasp-mapping.md](owasp-mapping.md)) |
|---|---|---|
| 1 Tool identity and integrity | T4, T18, T20 | ASI01, ASI04 |
| 2 Supply chain | T13 | ASI04 |
| 3 Front door, 4 Tokens | T8, T9 | ASI02, ASI03 |
| 5 Consent and credentials | T6 (SSRF), T7, T8 | ASI03 |
| 6 Sampling, elicitation, roots | T2, T7, T12 | ASI01, ASI05 |
| 7 Runtime defaults | T13, T14 | ASI04, ASI08 |

External, dated: MCP Security Best Practices,
https://modelcontextprotocol.io/specification/latest/basic/security_best_practices (spec 2026-07-28, fetched 2026-10);
MCP elicitation, https://modelcontextprotocol.io/specification/latest/client/elicitation (fetched 2026-10).
