# Current facts (as of 2026-10)

**As of 2026-10.** Everything in this file ages fast: spec revisions, SDK names, provider limits and protocol versions. Before quoting any of it in a deliverable, check the date. If it is much later than 2026-10, or the user's code uses different names, verify against the linked source and say which version you are assuming. Book code written before mid-2026 uses older MCP APIs (see the last section).

## MCP specification 2026-07-28 (current revision)

Source: https://modelcontextprotocol.io/specification/2026-07-28/changelog

- **Stateless.** There is no `initialize` handshake and no `Mcp-Session-Id`. Every request carries its protocol version and client capabilities in `_meta`. List results must not vary per connection, but they may vary by the authorization on the request (for example, only the tools the caller's scopes allow).
- **`server/discover`** must be implemented by servers; clients may call it for up-front version selection.
- **Multi round-trip requests (MRTR)** replace server-initiated requests. The server returns `resultType: "input_required"` with `inputRequests` (and optionally `requestState`). The client retries the original request under a new JSON-RPC ID with `inputResponses`. Every result carries `resultType` (`complete` or `input_required`).
- **No resumability.** A broken stream loses the in-flight request, and the client re-issues it with a new ID. Side-effecting tools therefore need deduplication.
- **`subscriptions/listen`** is the only long-lived stream, for opted-in change notifications (tools, prompts, resources). `ping` and `logging/setLevel` are removed.
- **Caching.** `tools/list`, `prompts/list`, `resources/list`, `resources/read` and `resources/templates/list` results carry `ttlMs` and `cacheScope` (`public` or `private`). Servers should return tools in a deterministic order.
- **HTTP headers.** Streamable HTTP POSTs carry `Mcp-Method` and `Mcp-Name`. The `x-mcp-header` schema extension mirrors a primitive tool parameter into an `Mcp-Param-{name}` header for routing; never mark secrets or PII with it.
- **Tasks** moved to an official extension (`io.modelcontextprotocol/tasks`): `tools/call` returns a task handle, and the client polls `tasks/get`.
- **Elicitation:** form mode for flat, non-sensitive schemas; URL mode for OAuth consent, payments and credentials. Clients answer accept, decline or cancel.
- **Schemas:** `inputSchema` and `outputSchema` accept any JSON Schema 2020-12 keywords; `structuredContent` can be any JSON value. When returning structured content, also return its serialised JSON in a text block for older clients. For a no-parameter tool, use `{"type": "object", "additionalProperties": false}`.
- **Stateful tools** (non-normative guidance): mint opaque handles, authorise each call against the handle, state the handle's lifetime in the description, and return a tool execution error for an expired handle.

**Tool names** (spec, SHOULD): 1-128 characters, case-sensitive, only `A-Z a-z 0-9 _ - .`, unique within a server. Clients aggregating servers should prefix with a server identifier; `serverInfo.name` is not guaranteed unique.

**Tool names and schema key by target** (checked 2026-10):

| Target | Schema key in a definition | Name rule |
|---|---|---|
| MCP spec (wire) | `inputSchema` (plus optional `outputSchema`) | SHOULD be 1-128 chars of `A-Z a-z 0-9 _ - .`, case-sensitive |
| Claude Messages API | `input_schema` | `^[a-zA-Z0-9_-]{1,128}$` (no dots) |
| Claude connector directory (MCP servers listed by Anthropic) | `inputSchema` | 64 characters or fewer |
| OpenAI function calling | `parameters` | `a-z A-Z 0-9 _ -`, at most 64 characters |
| Portable choice | as the target requires | at most 64 characters, letters, digits, `_`, `-` |

**Tool annotations** (all hints; clients must treat them as untrusted unless the server is trusted):

| Field | Default | Meaning |
|---|---|---|
| `readOnlyHint` | false | Does not modify its environment |
| `destructiveHint` | true | May destroy or overwrite (meaningful only when not read-only) |
| `idempotentHint` | false | Repeating with the same arguments has no further effect (only when not read-only) |
| `openWorldHint` | true | Interacts with an open world of external entities (web search: true; memory store: false) |

**Errors.** Protocol errors are JSON-RPC errors for an unknown tool, a malformed request or a server error. Tool execution errors are results with `isError: true` for API failures, input validation errors and business-logic errors. Clients should pass tool execution errors to the model. Codes: -32602 invalid params (now also resource not found), -32603 internal error, -32020 header mismatch, -32021 missing required client capability, -32022 unsupported protocol version.

**Authorization** (HTTP transports; stdio takes credentials from the environment). Source: https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization
- Servers must publish OAuth Protected Resource Metadata (RFC 9728), validate that tokens were issued for them (audience), answer invalid tokens with 401, and never accept or pass through other tokens.
- Clients must use PKCE and send the `resource` parameter (RFC 8707) in both authorization and token requests. They must send `Authorization: Bearer` on every request, never in the query string, and must validate a present `iss` against the recorded issuer (RFC 9207).
- Registration options: Client ID Metadata Documents (recommended), pre-registration, or Dynamic Client Registration (deprecated, kept for older authorization servers). Persisted client credentials are keyed by issuer.
- Insufficient scope: 403 with `error="insufficient_scope"` and all required scopes in one challenge. Clients step up with the union of old and new scopes, with a retry limit.

**Deprecated in 2026-07-28** (work for at least twelve months; eligible for removal in the first revision released on or after 2027-07-28): Roots (pass paths as arguments or configuration), Sampling (call a model provider directly), protocol Logging (log to stderr or use OpenTelemetry), Dynamic Client Registration, HTTP+SSE transport, `includeContext` values `thisServer`/`allServers`. Source: https://modelcontextprotocol.io/specification/2026-07-28/deprecated

**Extensions** (optional, named `vendor/name`): MCP Apps (UI resources in a sandboxed iframe), OAuth Client Credentials, Enterprise-Managed Authorization, Tasks. Support across clients was thin when the MCP book was written; check the clients your users run.

## MCP Python SDK v2 (`mcp>=2.0`)

Sources: https://py.sdk.modelcontextprotocol.io/whats-new/, https://py.sdk.modelcontextprotocol.io/servers/handling-errors/

| Purpose | v2 name |
|---|---|
| High-level server (was `FastMCP`) | `from mcp.server import MCPServer` (module `mcp.server.mcpserver`) |
| Tool decorator | `@mcp.tool(name=, title=, description=, annotations=, structured_output=)`; schema inferred from type hints and `Annotated[..., Field(...)]` |
| Annotations | `from mcp.types import ToolAnnotations` (also `mcp_types`); snake_case fields `read_only_hint`, `destructive_hint`, `idempotent_hint`, `open_world_hint` |
| Model-visible tool failure | `raise ToolError("...")`, from `mcp.server.mcpserver.exceptions` |
| Protocol error (model sees nothing) | `raise MCPError(code=INVALID_PARAMS, message=...)`, `from mcp import MCPError` |
| Any other exception | The model gets a generic "Error executing tool <name>" and the traceback goes to the server log |
| User input mid-call | Parameter `Annotated[ElicitationResult[Model], Resolve(fn)]`, where `fn` returns `Elicit(message, Model)`. Results are `AcceptedElicitation`, `DeclinedElicitation` or `CancelledElicitation`. The parameter is hidden from the model's schema. A client without the capability fails the whole call with a protocol error ("Elicitation not supported") before the tool runs. The resolver works on both protocol eras; `ctx.elicit()` inside the body works only on legacy (2025-11-25 or earlier) connections. |
| Context | `ctx: Context` parameter, e.g. `await ctx.report_progress(...)` |
| Run | `mcp.run()` for stdio; `mcp.run(transport="streamable-http", stateless_http=True, json_response=True)` for remote; `mcp.streamable_http_app(...)` to mount in Starlette |
| Auth (resource server) | `MCPServer(..., token_verifier=MyVerifier(), auth=AuthSettings(issuer_url=..., resource_server_url=..., required_scopes=[...]))`; `TokenVerifier`, `AccessToken` from `mcp.server.auth.provider`; `AuthSettings` from `mcp.server.auth.settings` |
| Cache hints | `cache_hints=` on the server constructor (e.g. a `tools/list` TTL) |
| Client | `from mcp import Client` (also `mcp.client`): one async context manager taking a URL, `StdioServerParameters` or a transport; the legacy `ClientSession` is reachable as `client.session` |
| Wire types | Separate `mcp-types` package; Python attributes snake_case (`is_error`, `input_schema`), wire format camelCase |

Behaviour notes: v2 serves 2025-11-25 and 2026-07-28 clients side by side. The WebSocket transport is gone. Tasks are not implemented. OpenTelemetry is on by default. Sync handlers run on a worker thread. URI templates reject path traversal by default, but tool parameters get no such protection. HTTP uses `httpx2`.

Gotcha: the MCP book's error example raises `ValueError` for a model-recoverable error and says the message reaches the model [MCP ch5]. Under the current v2 docs, only `ToolError` text does. Use `ToolError`.

Development: the MCP book runs servers in MCP Inspector with `uv run mcp dev server.py` [MCP ch5].

**Approval gate with elicitation (v2, verified against the SDK's elicitation docs).** A resolver receives the tool's other arguments by name and returns either the value (no prompt) or `Elicit(message, Model)`. The tool always receives an `ElicitationResult`; a value returned directly arrives wrapped as `AcceptedElicitation`. A client without elicitation gets a protocol error ("Elicitation not supported") before the tool body runs. The SDK offers no capability query, so pair the tool with a propose-only path.

```python
from typing import Annotated
from pydantic import BaseModel, Field
from mcp.server import MCPServer
from mcp.server.mcpserver import AcceptedElicitation, Elicit, ElicitationResult, Resolve
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations

mcp = MCPServer("acme-billing")
NO_PROMPT_LIMIT_CENTS = 5_000          # below this, no confirmation; an assumption for the owner

class Approve(BaseModel):
    approve: bool = Field(title="Issue this refund?")

async def approve_refund(order_id: str, amount_cents: int) -> Approve | Elicit[Approve]:
    if amount_cents <= NO_PROMPT_LIMIT_CENTS:
        return Approve(approve=True)
    return Elicit(f"Refund {amount_cents / 100:.2f} on order {order_id}?", Approve)

@mcp.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=True))
async def billing_refund_order(
    order_id: str,
    amount_cents: Annotated[int, Field(gt=0, le=20_000)],
    approval: Annotated[ElicitationResult[Approve], Resolve(approve_refund)],
) -> dict:
    """Refund part of a delivered order after the user confirms. Over 200.00, or if this
    client cannot show a confirmation, use billing_request_refund instead."""
    match approval:
        case AcceptedElicitation(data=Approve(approve=True)):
            pass
        case _:
            return {"status": "not_refunded", "reason": "user declined or cancelled"}
    order = await load_order_for_caller(order_id)        # your code: auth + ownership
    if amount_cents > order.refundable_cents:            # state check: the real duplicate guard
        raise ToolError(f"Only {order.refundable_cents} cents remain refundable on {order_id}.")
    key = f"refund:{order_id}:{amount_cents}"            # natural key; backend dedupes resends
    return await issue_refund(order_id, amount_cents, idempotency_key=key)
```

`billing_request_refund` (not shown) is the propose-only companion. It validates the same way, stores a pending refund, and returns a reference for a human to approve in your own UI. It never moves money.

## Claude API tool use (Anthropic)

Sources: https://platform.claude.com/docs/en/agents-and-tools/tool-use/define-tools, https://platform.claude.com/docs/en/agents-and-tools/tool-use/tool-search-tool, https://platform.claude.com/docs/en/build-with-claude/structured-outputs

- **Names** must match `^[a-zA-Z0-9_-]{1,128}$`. No dots, so translate MCP names that contain them.
- **Descriptions:** the docs call detailed descriptions the most important factor and suggest at least 3-4 sentences, more for complex tools. They recommend consolidating related operations behind an `action` parameter and namespacing by service.
- **`input_examples`**: schema-valid example inputs; each costs about 20-50 tokens (simple) to 100-200 (nested). Not supported on server tools.
- **`tool_choice`**: `auto` (default), `any`, `tool` (named), `none`. `any` and `tool` return a 400 on Claude Opus 5.5, Sonnet 5.5, Fable 5.1 and Mythos 5.1, and with manual extended thinking. On those, use `auto` with strict tool use plus enforcement in code. Forced choice also suppresses text before the tool call. Changing `tool_choice` invalidates cached message blocks.
- **Strict tool use** (`strict: true`) constrains decoding to the schema. Reported limits: some JSON Schema keywords are unsupported (numeric bounds and string-length limits among them), there is a cap on strict tools per request (20 when checked), no guarantee on enum capitalisation, and no guarantee when the model refuses or hits the token limit. Keep business validation.
- **Tool search tool:** `tool_search_tool_regex_20251119` or `tool_search_tool_bm25_20251119`. Set `defer_loading: true` on the other tools, keep the 3-5 most-used non-deferred, and never defer the search tool. It returns 5 tools by default and supports up to 10,000 deferred tools. The docs recommend it at 10 or more tools or over 10k tokens of definitions, and say selection degrades past 30-50 tools. Deferred tools are excluded from the cached prefix, so caching survives. With the MCP connector, set `defer_loading` on the `mcp_toolset` config.
- **Parameters asking "why":** ask for a short explanation or evidence, not reasoning. Asking for step-by-step reasoning can trigger a refusal.
- **Tool result errors:** return `is_error: true` in the `tool_result`.

## OpenAI function calling

Source: https://developers.openai.com/api/docs/guides/function-calling, and the `name` field docstring in the openai-python SDK types.
- The definition uses `parameters` for the JSON Schema. Names are `a-z A-Z 0-9 _ -`, at most 64 characters.
- Strict mode requires `additionalProperties: false` on every object and every property listed as required; optional fields take a `null` type option.
- `tool_choice`: auto, required, a forced function, or `allowed_tools` (a restricted subset). `parallel_tool_calls: false` limits a turn to zero or one call.
- The guide's soft suggestion is fewer than 20 functions available at the start of a turn.

Other providers have their own equivalents. Check their current docs, and do not assume one provider's limits apply to another.

## MCP hosts: Claude Desktop, claude.ai, Claude Code (and others)

Sources (checked 2026-10-06): https://claude.com/docs/connectors/building, https://claude.com/docs/connectors/building/review-criteria, https://claude.com/docs/connectors/custom/add-unlisted, https://claude.com/docs/connectors/getting-started, https://code.claude.com/docs/en/mcp. "Unknown" means the docs checked did not say; test in the host before relying on it.

| Topic | claude.ai, Desktop, mobile (connectors) | Claude Code |
|---|---|---|
| Remote servers | Streamable HTTP (legacy HTTP+SSE still accepted), added as a custom connector by URL (no review; Free, Pro and Max users add it to their own account, Free limited to one; on Team and Enterprise an Owner adds it for the organisation), from the Anthropic directory (reviewed), or inside a plugin. Claude calls remote connectors from Anthropic's cloud, so the server must be reachable from the public internet over HTTPS (localhost or VPN-only servers will not work; put internal APIs behind a public, authenticated MCP endpoint or use a local desktop extension) | HTTP (recommended), SSE (deprecated), plus a non-standard WebSocket option with header-only auth |
| Local servers | Desktop only: a desktop extension (MCPB bundle, runs with the user's permissions; organisations can disable or restrict extensions). No plain stdio config in the docs checked | stdio, configured per project, user or local scope |
| Tool-list consent | User reviews the OAuth access when connecting. Per tool: Allow once or Always allow on first use; later Always allow, Needs approval or Blocked in settings. Whether a changed tool list triggers a new prompt: unknown | Project-scoped servers (`.mcp.json`) wait for approval in a trusted workspace. On `list_changed`, the new list is fetched with no re-approval described. Per-tool permission rules apply at call time |
| Auth | OAuth with per-user sign-in, a static credential an org Owner enters once, or none. Claude's client follows the 2025-03-26, 2025-06-18 and 2025-11-25 authorization specs and registers through Dynamic Client Registration or the other documented ways, so keep DCR or pre-registration working even though 2026-07-28 deprecates DCR. Redirect URI `https://claude.ai/api/mcp/auth_callback`. | OAuth 2.0 via `/mcp`; pre-configured client ID and secret; dynamic headers helper. Loopback redirect. |
| Protocol revision | Not stated beyond the auth specs above (unknown whether 2026-07-28 is used); a server on SDK v2 serves both eras | v2 runtime on the TypeScript SDK 2.0; uses 2026-07-28 with HTTP servers that support it |
| Not supported | Resource subscriptions, sampling, "advanced or draft capabilities" | n/a |
| Elicitation | Unknown: not in the supported list, and "advanced or draft capabilities" are listed as unsupported. Design for its absence (propose-only) | Supported: form and URL mode dialogs (declared as client capabilities on 2026-07-28 connections). Users can auto-answer with an `Elicitation` hook |
| Approvals | Annotations set the default: read-only tools can run without per-call confirmation, destructive tools always prompt. The user (or an org admin) can override per tool | Permission rules per tool, set by the user |
| Tool loading | Unknown | Tool search with deferred loading by default (`ENABLE_TOOL_SEARCH=false` turns it off); tools appear as `mcp__<server>__<tool>` |
| Result size | About 150,000 characters | 25,000 tokens by default, warning above 10,000 (`MAX_MCP_OUTPUT_TOKENS`) |
| Timeout | 240 s per tool call | `MCP_TOOL_TIMEOUT`; calls running past 2 minutes move to the background |

**Directory review rules for Claude connectors:** every tool needs a `title` and the applicable `readOnlyHint` or `destructiveHint`; names are 64 characters or fewer; read and write operations go in separate tools (a catch-all `api_request` with a `method` parameter is rejected); descriptions must not instruct Claude beyond the tool's function; errors must be actionable, not "Internal Server Error"; connectors that transfer money or other financial assets are not accepted.

**Other hosts** (VS Code, Cursor, ChatGPT and others): not verified here. Check their docs for transports, elicitation, annotation handling, tool-count limits and result caps.

## A2A

Source: https://a2a-protocol.org/latest/specification/, https://github.com/a2aproject/A2A/releases

- v1.0.0 released 2026-03-12; v1.0.1 on 2026-05-28 (binding fixes).
- Three bindings: JSON-RPC 2.0, gRPC, HTTP+JSON. Task states include `INPUT_REQUIRED` and `AUTH_REQUIRED`. Streaming over SSE plus webhook push notifications.
- Agent card at `/.well-known/agent-card.json` (changed from `agent.json` in v0.3.0). The card declares security schemes (API key, HTTP auth, OAuth 2.0, OpenID Connect, mutual TLS); cards can be signed; authenticated clients can fetch an extended card.
- A2A sits in the same Linux Foundation body (Agentic AI Foundation) as MCP.

## Agent Skills

Source: https://agentskills.io/specification

- A directory with `SKILL.md`: YAML front matter with `name` (up to 64 lowercase letters, digits and hyphens, matching the directory) and `description` (up to 1,024 characters: what it does and when to use it), then instructions.
- Optional `scripts/`, `references/`, `assets/`. Progressive loading: about 100 tokens of metadata always in context, the body (under about 5,000 tokens and 500 lines) when activated, files when needed.
- Validator: `skills-ref validate`. Serving Skills through MCP was experimental when the MCP book went to press [MCP ch9].

## Dated material to distrust

- MCP code using `mcp.server.fastmcp`/`FastMCP`, `ClientSession` with explicit `initialize()`, `streamablehttp_client`, sampling or roots callbacks in new code, or the WebSocket transport is v1-era. Port it to v2 names or pin `mcp<2` to run it as written.
- Claims that MCP "has no standard security story" or runs over "HTTPS or WebSocket" predate the current spec [BUILDAPPS ch4], [DEFGUIDE ch5].
- A2A examples with `/.well-known/agent.json` or custom card fields are pre-1.0 [BUILDAPPS ch8].
- "Structured outputs encourage but do not force the schema" [BUILDAGENTIC ch1] is out of date where strict modes exist.
