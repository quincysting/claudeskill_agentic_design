# Tool design rules

Depth for steps 2 to 9 of the procedure. Citation keys ([MCP ch5] and so on) are listed under Sources in SKILL.md.

A tool definition has two readers. The model reads the name, description and schema as prompt text, which is why wording changes selection accuracy. Your runtime reads the same schema as a contract to enforce. Design for both: words that make the right choice obvious, and types and checks that make a wrong call impossible to execute.

## §1 Granularity: cut by intent, then by permission

**Agent stories.** Write what the agent wants to accomplish from its own point of view, one sentence each: "the agent wants to tell Bob in a DM that the deploy finished." Give each story one tool. A tool generator working from a chat API would emit three tools for that story (resolve user, open channel, post message); the story needs one [MCP ch5].

**Why fewer, end-to-end tools.** At 95% accuracy per tool choice, an action that needs five sequential choices succeeds about 77% of the time (0.95^5). Because every turn re-sends earlier turns, the MCP book estimates the five-call version at about 8 times the tokens and nearly 7 times the cost of one call [MCP ch5]. A chain of N steps at per-step reliability p succeeds with p^N: at 98% per step, ten steps fall below 82% [DEFGUIDE ch5].

**Where to stop consolidating.** Split again when:
- two intents need different required fields (otherwise the schema cannot say what is required, and the model must guess);
- two intents need different permissions (read vs write, own records vs any record, reversible vs irreversible);
- one intent would need more than about five or six parameters (smaller models handle many-parameter tools badly [ILLUSTRATED ch5]);
- the tool would return wildly different shapes depending on a flag.

**Consolidating with an `action` enum.** Anthropic's tool guidance (2026) suggests grouping related operations behind an `action` parameter to reduce near-duplicate choices. That holds when every action takes the same parameters and needs the same permission, as with `github_pr(action: open|close|reopen, pr_number)`. It fails for `social_media(platform, action, content, **kwargs)`, where `action` decides which other fields are required. That shape moves the selection problem into argument filling, where the schema can no longer help. **Rule:** same fields and same permission → one tool with an enum is fine; otherwise split.

**Generated tools.** OpenAPI or SDK generators are fine as a first draft and as the source of types. The MCP book calls one-to-one generation the most common antipattern [MCP ch2]; SYSTEMS builds on OpenAPI but exposes only *selected* capabilities [SYSTEMS ch7]. Use the spec for types; design the surface from stories.

**Read vs action tools.** Retrieval tools (sensors) can be retried and cached freely. Action tools (actuators) need idempotency, authorization and sometimes approval [MESH ch4]. Keep the two kinds in separate tools.

## §2 Names and descriptions

**Names.**
- Use the `service_verb_object` pattern: `billing_refund_order`, `crm_find_contacts`, `calendar_create_event`. Pick one scheme (prefix by service) and keep it everywhere.
- Make every name distinct from its neighbours. A name that is too general (`process_data`, `handle_request`) gets called when it is not needed [BUILDAPPS ch4].
- Prefix every name with a namespace per service or server. This stops one server's `search` shadowing another's and lets tool search match a whole group [MCP ch5].
- In a host that connects servers it did not write, a prefix each server picks for itself is not enough. The host or gateway resolves every tool as `server::name`, with the server identity taken from its own configuration rather than the server's self-reported name, and pins a hash of each approved definition so a later rewrite halts the client with a diff [HARDMCP ch9], [HARDMCP ch4]. Shadowing and pinning are agent-threat-modeler's; what a description edit then means for callers is in tool-contracts §8.
- Use only `A-Z a-z 0-9 _ -`, at most 64 characters. That is the strictest limit among the targets checked: MCP allows 128 characters and dots, Claude's API 128 without dots, OpenAI's API and the Claude connector directory 64 (per-target table in current facts).
- Leave room for prefixes added downstream. A gateway that aggregates servers or API targets usually prefixes each tool with the target name, and some hosts add their own prefix. The budget applies to the final name the model sees, so keep target and tool names short (current facts, "Managed MCP gateways").

**Description template** (three to six sentences; longer for complex tools):

```
<What it does, in one sentence, with the object it acts on.>
Use when <situations>. Do not use for <near-miss cases>; use <sibling_tool> instead.
<Inputs: meaning, units, formats, where the value usually comes from (e.g. "order_id from crm_find_orders").>
<Preconditions: what must be true or called first.>
Returns <shape, key fields>. <Side effects, limits, latency or cost if notable.>
<Failure behaviour the model should expect, e.g. "Fails if the order is not paid.">
```

This covers the five parts of a tool specification: identity, inputs, outputs, operational constraints and error handling [AGENTICAI ch5]. Write it as you would explain the code to a capable new hire: make explicit the context you hold implicitly. Then ask a model where the description is vague or overlaps with another tool [MCP ch5]. "Lazy prompting" is no excuse for thin descriptions: Ng limits the advice to interactive work and excludes prompts in code that run repeatedly, which is what tool descriptions are [NG The Benefits of Lazy Prompting, 2025-04-02]. To stay lean safely, start short and add a sentence when a tool-choice eval case fails.

**Business constraints belong in the description and in code.** In one documented case an inventory agent used its pricing tools exactly as designed and marked premium wines for clearance. They were being aged on purpose, and about $100,000 of revenue was lost [AGENTICAI ch5]. The rule "never discount stock tagged for aging" belonged in the validation code, with one sentence in the description so the model would not try.

**Overlap is the main cause of confusion.** Two tools whose descriptions could both fit one request will be confused with each other [BUILDAPPS ch4]. When the eval shows a confused pair, rewrite one description to exclude the other's job explicitly ("Does not fetch a page by URL; use web_fetch_page for that").

Bad and good:

```json
{"name": "search", "description": "Search for things."}
```

```json
{"name": "kb_search_articles",
 "description": "Full-text search over published help-center articles (not internal wiki, not tickets). Use when the user asks how a product feature works or how to fix a known problem. Do not use for account-specific questions; use crm_get_account for those. query is plain words, not a question; 3-8 keywords work best. Returns up to 5 articles with id, title, url and a 300-character snippet, best match first. Returns an empty list, not an error, when nothing matches."}
```

## §3 Input schema

- **Parameter names say what they hold**: `customer_email` not `user`, `amount_cents` not `amount`, `start_date` not `date`.
- **Types and constraints are in the schema**, so the model reads them and the runtime enforces them: `enum` for closed sets, `minimum`/`maximum`, `pattern` for IDs (`^ord_[0-9]{6}$`), `format: date` with an example, `maxLength` on free text.
- **Dates and times** are ISO 8601 with an explicit time zone, or a separate `timezone` parameter. Money is an integer in minor units plus a currency code.
- **Writes take absolute values.** An update carries the new value plus the expected current value or version (§6, tool-contracts §5), never a relative change ("+5%", "add 2 days"). If the user speaks in percent, the agent reads the current value, computes the absolute one and passes that, so the preview shows the real number and a repeat is a no-op or a `conflict`.
- **Keep `required` minimal and meaningful.** Defaults go in the schema and the description.
- **A missing required value is never guessed.** A schema can require a field but cannot stop the model inventing a plausible value. Say in the parameter description to ask the user, or to propose a default labelled as an assumption for approval [PRODGUIDE ch7], and reject values the runtime can tell were invented (an order ID that is not in this customer's history).
- **No catch-alls.** `**kwargs`, `options: object` and `extra: string` leave nothing to validate and invite hallucinated fields. Set `additionalProperties: false`.
- **No conditional requirements.** If `mode=x` requires `a` and `mode=y` requires `b`, split the tool (§1). The one exception is a lookup that takes exactly one of two identifiers (`employee_id` or `work_email`): declare it with `oneOf` or say so in the description, and check it in the handler, returning a tool error when both or neither arrive. Anything more conditional than that becomes two tools.
- **Never model-filled:** caller identity, tenant, role, approval status, auth tokens, idempotency keys, and facts the server can look up (current status, balance, owner, remaining refundable amount). The runtime injects identity and approval; the handler reads state from the system of record. A parameter the model can fill is a parameter an injected instruction can fill: a confused or steered model that passes `current_status: "processing"` for a shipped order defeats every rule that trusts the field. The one allowed exception is an expected value used as a concurrency guard (a version or ETag, the price the user was shown, a balance the agent read): the handler compares it with the system of record and refuses on a mismatch, and never uses it as the value.
- **One definition for schema and handler.** Generate the published input schema from the type the handler validates with. A hand-written catalog kept beside the code drifts: the schema says `customer_ref` while the handler reads `customer_id`, or declares a string where the handler expects an integer, and every call fails. Add a contract test that calls each tool in the list response with its own schema example and expects no validation error.
- **The schema is the policy contract.** If a policy engine will govern the tool, every field a rule reads needs a precise type or enum, and should be required (a rule on an optional field the call left out may silently not apply). Free text can be governed only by classifiers.
- **Free-text fields asking "why"** should ask for a short explanation or the supporting evidence, not the model's step-by-step reasoning. Some providers refuse to emit reasoning into parameters (see current facts).
- **Input examples** help with nested, optional-heavy or format-sensitive inputs. In Anthropic's tests, adding them raised accuracy on complex parameter handling from 72% to 90% (Advanced tool use, 2025-11). Each example costs prompt tokens on every call.
- **Strict mode** (constrained decoding to the schema) guarantees shape, not truth. Provider limits apply (unsupported keywords, caps on strict tools per request), and it does not hold when the model refuses or runs out of tokens. Keep business validation either way. See current facts.
- **Validate with a schema library** (Pydantic, jsonschema, zod), not regular expressions [ILLUSTRATED ch5]. Validate against the schema first, then against business rules: a request can be well formed and still not allowed [SYSTEMS ch4].

## §4 Results

- **Structured beats prose for the next decision** [SYSTEMS ch7]. Return a JSON object with stable field names and also a short text rendering where the protocol expects text (MCP: `structuredContent` plus a text block).
- **Names next to IDs.** Return `{"id": "usr_8812", "name": "Dana Ruiz"}`, not just an opaque ID the model must carry blind. Return stable, opaque identifiers (slugs, UUIDs), not internal row pointers, and never personal data such as an email as an ID: arguments spread into transcripts, traces, caches and eval sets (tool-contracts §7).
- **An envelope, never a bare array.** Every result is an object (`status`, then `data`, `receipt` or `problem`, plus `next_actions` and a cursor where they apply), so a list can later gain pagination without breaking anyone. Writes return a receipt: ID, link, the fields as applied, status, idempotency key and contract version (tool-contracts §3, §7).
- **Valid next actions for state-dependent tools.** Return the actions possible now, flagged safe, idempotent or reversible, in the result rather than by changing the tool list; the harness still checks them against its allowlist (tool-contracts §10).
- **Only high-signal fields.** Drop internal metadata, nulls and audit columns. Each extra field costs tokens on this turn and every later turn.
- **Bound the size.** Paginate or truncate by default, state in the result that it was truncated, and say how to get more ("47 more; call again with the returned `next_cursor`, or narrow the date range"). Use an opaque cursor, never a page number: when items are added or removed between calls, page numbers skip or repeat items. Over a backend that only pages by number, the server issues the cursor itself, encoding the filters, a stable sort (for example created time, then ID) and a keyset position (the last sort key returned), and fetches the next items after that position. Offer `response_format: concise|detailed` when callers sometimes need full records. In Anthropic's Slack example the concise form took 72 tokens and the detailed one 206 (Writing tools for agents, 2025-09).
- **Batch tools report per item.** Return a status per item (done, failed with a reason, skipped) plus a count. A batch-level "ok" that hides failed items misleads the model. Retry only the failed items, each with its own idempotency key.
- **Large payloads go out of band.** Return a URL, a presigned link or a resource link plus a summary. Base64 inflates binary by about a third, and the MCP book suggests keeping messages under about 100 KB [MCP ch8].
- **Results are untrusted input.** A web page, email or ticket body returned by a tool can carry instructions. Mark external content as data (fenced, labelled with source), strip active content you do not need, and never let a result widen the agent's permissions. Deep treatment: agent-threat-modeler.
- **Be deterministic where you can.** The same input over the same state gives the same output; inconsistent tools make orchestration fragile [SYSTEMS ch7].

## §5 Errors the model can act on

**The routing question:** could the model, or a better model, or this model with more information, do something useful with this failure? If yes, return a tool error it can read. If no, handle it in code (retry, fallback, escalate) or reject at the protocol level [MCP ch5]. "Something useful" includes telling the user why the action cannot happen. That is why the current MCP spec lists input validation errors and business-logic errors as tool execution errors, and keeps protocol errors for unknown tools, malformed requests and server faults. The MCP book's example raises a protocol error for "grades not posted yet" [MCP ch5]. Under the current spec that is better returned as a tool error the model can relay.

**Message pattern:** what was wrong, what is allowed or what the state is, what to do next. One or two sentences. No stack traces, no internal codes without meaning.

**Flag it as an error.** Mark refusals and failures with the protocol's error flag (`isError` in MCP, `is_error` in the Claude API) as well as the readable message. A magic prefix inside a success result ("Rejected: ...") is easy for clients, graders and the model to miss. If a gateway or policy engine in front of the server can deny a call, check the shape in which that denial reaches the model (current facts, "Managed MCP gateways").

**Return errors as tool results, not exceptions, and keep the flag across hops.** A tool layer that raises on invalid arguments ends the run instead of giving the model a message it could act on [RELATED repo: aisuite/aisuite/utils/tools.py]. A client that unpacks results to text loses the flag: the MCP book's client keeps only the content, so the error text still reaches the model, but as an ordinary result, and `structuredContent` is gone [MCP repo: ch3/12_make_tool_calls/client.py]. Map `isError` onto the model API's error flag, keep the structured body for the harness, and test with a forced failure through the real client. Failure categories and the problem-details body are in tool-contracts §4.

| Instead of | Return |
|---|---|
| `KeyError: 'ord_12'` | `No order ord_12 for this customer. Check the ID with crm_find_orders.` |
| `400 Bad Request` | `start_date must be today or later (got 2026-09-30). Ask the user for a new date.` |
| `Refund failed` | `Order ord_123456 is 'shipped'; refunds need status 'delivered'. Tell the user the refund is possible after delivery.` |
| `TimeoutError` (on a write) | `Billing timed out; the refund may still complete. Call billing_get_order to check before retrying.` |

**Two retry loops, both bounded** [DEFGUIDE ch5]. The inner loop re-asks the model with the validation error, up to two or three times. The outer loop is the orchestrator: it decides whether to rerun the step, ask the user or stop. Unbounded re-asks burn tokens and can loop.

**Validate, retry, fall back, log** [BUILDAPPS ch4]. After each model turn, check the right tool was called, the JSON parsed, and nothing failed at runtime. Retry transient faults with exponential backoff and jitter. When retries run out, fall back (backup service, cached data, safe default, ask the user). Log every step.

## §6 Side effects, state and resilience

**Idempotency.** Retries, client re-sends after dropped connections, the model reissuing a call and the harness replaying a step all happen in production. Repeating an operation must not repeat its effect [SYSTEMS ch4]. Under stateless MCP a dropped request is re-sent, so deduplicating non-idempotent calls is the client's and host's job [MCP ch4]. Updates get operation idempotence (a new value guarded by the expected current one, never a delta); creates and sends get request identity (an idempotency key or a client-chosen ID). The three kinds are in tool-contracts §5.

```python
def idempotency_key(run_id: str, tool: str, target_id: str, step: str = "") -> str:
    # One intended effect = run + action + target (+ the plan step if the plan repeats it on purpose).
    # Taken from durable run state and recorded before the first attempt, so retry, resume and replay reuse it.
    # Never the model's tool-call ID or the attempt number (both change), nor a hash of every argument
    # (a reworded free-text field would make a new key).
    return ":".join(p for p in (run_id, tool, target_id, step) if p)
```

Pass the key to a backend that stores it and returns the first result for repeats. If the backend cannot, keep a dedupe table in your runtime keyed the same way. A second refund of the same order in one run is a duplicate unless the plan says otherwise; then the plan step or a line-item ID goes into the key. After a timeout, verify by key before any retry (tool-contracts §5).

**No run ID.** An MCP server running in Claude Desktop, an IDE or a partner's agent never sees your run, task or conversation ID, and stateless MCP has no session to borrow one from. Two layers then do the work:
1. **The state check stops duplicates.** The handler re-reads the business object and refuses what its state does not allow: refund at most the remaining refundable amount, cancel only an order not yet cancelled, ship only what is unshipped. A second identical refund then fails with a readable error ("Order already refunded in full") whether or not anything deduplicated it. The backend must repeat the check atomically with the write (a conditional write on the value read, or a lock), or two overlapping calls both pass it.
2. **A natural key catches the exact resend.** Key on the business object and the operation's arguments (`order_id`, `amount_cents`, line items) within a short window, such as 10 minutes, so a transport resend lands on the first result. Put in the key the target and the values that define the effect (the new value, the effective date, the version read), never free text (reason, notes), which a resend may reword. When the caller is a harness that holds a run ID, its key is injected by the runtime, never part of the model's schema, and takes precedence over the natural key. Be aware that this also blocks a deliberate second refund of the same amount in that window. Make such a refund distinguishable (a line item, a reason code, a client-supplied request reference) or have the model say why it is retrying.

Never key on the model's tool-call ID or on a timestamp.

**Give the model a way to verify.** After an `outcome_unknown`, something has to look the write up. If the create tool returns the existing record when it is called again with the same business key, the repeat is the check, and the timeout message says so. Otherwise ship a lookup read beside the write, by business key or by a client-supplied request reference (`billing_find_refunds(order_id)` returning the refunds already issued), and name it in the timeout message.

**Timeouts.** Every call gets one, set from the backend's p99 latency plus a margin, not a blanket 30 s. Reads can retry twice with backoff. Writes retry only with an idempotency key, and only in code. A timeout on a write means "unknown", not "failed": say so in the message and offer a status tool, and have the harness look the write up by key before any retry (tool-contracts §5). The same holds for a 5xx or a dropped connection after the request was sent; the status-to-category mapping is in tool-contracts §4a.

**Reversible or not.** Every write declares whether it can be undone and, if so, names its revert action keyed by request ID; irreversible steps run last, behind approval (tool-contracts §6).

**State across calls** (carts, browser sessions, transactions, long jobs). Return an opaque handle from a create tool and take it as an argument on later calls. Authorise the caller against the handle on every call, because a handle is a name, not a permission. Give handles high entropy and a bounded lifetime, state the lifetime in the create tool's description, and return a tool error naming the expiry when a handle is stale, so the model can create a new one (MCP spec, Stateful Tools).

**Long-running work.** A start tool returns a job ID at once and a status tool reports progress and the result. On MCP, the Tasks extension standardises this when your SDK and clients support it.

**Resilience for tools you do not control** [AGENTICAI ch5]. Rate each tool on control (how much you influence its availability) and impact (how much the task depends on it). Low-control, high-impact tools are critical: give each a pre-built fallback, test it by simulating an outage, and when no fallback remains, escalate to a human with the failure, the task status and a proposed remedy. Agents re-plan around missing tools but do not invent new ones, so the backup must exist in advance [AGENTICAI ch5].

## §7 Permissions and approvals

- **A tool call is a request, not authority** [SYSTEMS ch7]. Treat it like an inbound request from an untrusted client: validate, authorise, log, bound.
- **A permission tier per action.** Give each tool action one tier: read-only, draft-only, execute with approval, or auto-execute, kept for narrow, reversible actions already proven safe. Hold the tiers in an allowed-actions table (tool, action, default tier, receipt) and deny everything off it [PRODGUIDE ch7]. The tier belongs to the action, not the agent: one agent may read orders, draft refunds and issue them only after approval. An action moves to a more autonomous tier only on evidence: previews consistently right, receipts present, escalations made when information was missing [PRODGUIDE ch7].
- **Narrow over broad.** One documented agent "optimised" a database by dropping half the rows of a production table through a generic SQL tool [BUILDAPPS ch4]. Prefer named operations (`crm_get_account(account_id)`).
- **Free-form query and command tools (raw SQL, graph query languages such as Cypher, Gremlin or SPARQL, shell, arbitrary HTTP).** Never give one to an agent that serves end users or reads untrusted content (chat messages, emails, web pages, tickets, retrieved documents); remove it in a review (P0). Most agents need two or three fixed lookups, so prefer named, parameterised operations and, for graphs, named traversals (`graph_get_rules_for_entity(entity_id)`) over a query-language tool. If staff need ad-hoc queries, put the tool in a separate staff-only agent or server with staff authentication and:
  - a read-only account on a replica, scoped to allowlisted views without secrets or unneeded PII;
  - read-only enforced by the database, not by the tool. A driver or session "read" mode, or a read-only transaction, blocks writes at best; it can still let procedure and function calls, admin functions, loads from a URL and expensive reads through. Grant a role that can only read (no procedure execution, no external loads);
  - parameter binding where it applies, DDL and bulk DML rejected, a server-side statement timeout, and the row limit applied inside the query rather than after fetching the full result;
  - text filters only as a backup. A keyword denylist blocks harmless queries (a string literal containing "delete", a property named `set`) and misses whatever it forgot. If you add a guard, parse the query with the language's own parser and allowlist clause types;
  - every query logged, with alerts on unusual volume;
  - read and write never in one tool (a catch-all `api_request` with a `method` parameter fails Claude's connector directory review);
  - a description that names the target API or schema documentation.
- **Authorization in code** from the authenticated caller, per object (user A cannot touch user B's records) and per tool (admin tools only for admins). Do not reveal whether an object exists to someone not allowed to see it. The caller is proven by a verified token, never by a user ID passed as a string (receiver checklist in mcp-and-protocols §5).
- **A gateway or policy engine in front adds a layer; it does not replace the handler's checks.** It sees the caller, the tool and the arguments, so it suits allowlists, caps on argument values, identity and tenant rules, and call counts. It cannot see a record's real state, so a rule on a value the model supplies ("status is not shipped") is a hint, not a control. The handler still checks status, balance and ownership against the system of record, and still validates its own inputs. A single gate is right; rule-free handlers behind it are not.
- **Make the gate the only route.** The backend behind each tool accepts calls only from the gate's identity (resource policy, network policy, or an allowlist of calling workloads). Anything else that holds invoke rights skips every rule. In a review, list who can call each backend directly. Writing and operating the gate's rules goes to agent-threat-modeler.
- **Least-privilege credentials per tool.** Give each tool its own scope and check it in the tool on every call, so a token that reads documents cannot move money [HARDMCP ch5]. One scope pair demanded on every request (`read` and `write` for all tools, as in the MCP book's OAuth example) is the shape to avoid [MCP repo: ch7/03_mcp_oauth_resource_server/server.py]. A read tool runs on read credentials and a read-only connection even if the agent also has write tools. One text-to-SQL example opens a default read-write SQLite connection and runs the model's SQL as written [BUILDAGENTIC repo: text_to_sql/agent/react_agent_sql.ipynb]; for a file database, open it read-only at least (`sqlite3.connect(f"file:{path}?mode=ro", uri=True)`), and for a server database use a role that can only read (free-form query rule above). Validate IDs against an enum or pattern before they become file paths or database names.
- **Rate limits and quotas.** Set them per principal (user or tenant), per client (each application or partner agent) and per tool. Tools that create requests, spend, send or run expensive searches get lower limits than cheap reads, and a quota per day bounds a slow loop that stays under the per-minute limit. A hit returns HTTP 429 with `Retry-After`, surfaced to the harness as `rate_limited` (tool-contracts §4). Record the limits in the catalogue entry (catalog-governance §2), and put them in the description where the model can act on them ("at most 5 searches per minute; narrow the query instead of repeating it").
- **Test under the agent's own identity.** Run tool tests, inspector sessions and evals with the credentials and token scopes the agent has in production. An admin or developer credential hides missing grants and over-broad ones alike.
- **Progressive access.** A new agent starts on read tools and earns write tools after it proves reliable, as with an inventory agent that queries stock before it may change orders or prices [AGENTICAI ch5].
- **Scope the visible list.** Show only the tools the caller's scopes permit. Filter by task state too wherever you assemble the list per turn: your own loop, or an MCP host or client you control (it can pass the model a subset of a server's tools). An MCP server cannot: its list may vary by the authorization on the request, not by task state (§8).
- **Approve the payload, bound to what runs.** The person approves a preview of the exact payload (recipients, amounts, titles), not "Shall I proceed?" [PRODGUIDE ch7]; the MCP specification likewise asks clients to show tool inputs to the user before calling a server (current facts). The approval stores a digest of the exact action and arguments, an expiry and a nonce, and execution refuses if the digest changed or the approval expired. That record and its checks belong to the harness (agent-harness-designer) and the oversight design (agent-threat-modeler). The tool's side: build the preview from the same arguments it will execute, and accept nothing the preview did not show.
- **A declared approval label must be enforced in code.** A `requires_approval=True` or `risk_level="high"` field on a tool is metadata. In aisuite the executor consults an approval policy only if the caller passes one, and with none every call runs [RELATED repo: aisuite/aisuite/toolkits/shell.py], [RELATED repo: aisuite/aisuite/utils/tools.py]. Refuse to start an agent that registers an approval-labelled tool without an approval policy (fail closed), and test that an unapproved call is refused. Annotations behave the same way: `destructiveHint` drives some hosts' prompts, and users can switch those off.
- **Approval** for irreversible, high-value, externally visible or bulk actions, enforced by the runtime (an approval step the model cannot skip) or by MCP elicitation, where the approval parameter is resolved by the server and never appears in the model-facing schema. If the host auto-approves, the gate degrades to a prompt, so the host's consent UI is part of the control. An elicitation answer shows only that the client said yes: users can set a host to answer automatically (Claude Code's Elicitation hook does this), and it never proves which person approved. When policy needs a named approver (a manager over a limit), use the propose-only path below, with the approver signed in where the request is stored.
- **Choosing the threshold.** Start from the existing human policy: the agent's limit is no higher than what a front-line employee may do without sign-off. Set it lower if the loss you would accept from one wrong action is lower. Irreversible actions that reach outside the company (payments out, emails to customers, deletions without undo) need approval at any amount until evals and production data show the agent is reliable; then raise limits step by step, as with progressive access. Write the threshold down as an assumption for the owner to confirm.
- **Propose-only as the primary design.** When policy needs a named approver, or the action is irreversible and legally consequential (pay, employment, credit), propose-only is the design, not a fallback: the tool records a pending request with a summary and returns its reference; a person approves that stored request in the system of record, and the backend executes exactly that record, never the agent. A propose-only tool is a draft-only write: it takes an idempotency key, returns a receipt with a request ID, and comes with a status read and a cancel tool. The approval check passes when the approval happens in the system of record on the stored request. The approval page requires sign-in, checks that the signed-in person may approve that request (role and limit), shows the stored payload, and records the decision only on an explicit submit (POST). Opening the link (GET) never approves anything, because mail scanners and link previews open links on their own. Who may approve is agent-threat-modeler's subject.
- **When nobody can be asked** (a client without elicitation, a batch run): degrade to the same propose-only path. A destructive tool that fails whenever approval is impossible is safe but useless; pair it with this path.
- **Annotations are hints.** `readOnlyHint`, `destructiveHint`, `idempotentHint` and `openWorldHint` help a trusted client decide what to confirm. Clients must not base decisions on annotations from untrusted servers (MCP spec).
- **Escalate to agent-threat-modeler** when one session, without human review, combines all three legs of Meta's Rule of Two: (A) processing untrustworthy inputs, (B) access to sensitive systems or private data, (C) the ability to change state or communicate externally (Meta AI, 2025-10). agent-threat-modeler owns the triage and the controls. The lethal trifecta is its exfiltration case [MCP ch7]; untrustworthy input that can change state in a sensitive system (merging to `main`, editing a payment record) is the integrity case and counts even when the agent holds no secrets. Escalate too when tools execute model-written code or shell, or when a server proxies third-party OAuth [MCP ch7].

## §8 Mandatory steps

Correct selection is never guaranteed: a model may skip a required step, choose the wrong capability or stop early [SYSTEMS ch7]. In one measured case, GPT-4.1 given a document-lookup tool but no instruction almost never called it and scored 47.8% on policy questions, barely above 44.4% with no tool. One system-prompt sentence telling it always to use the tool lifted it to 70.7%, while GPT-4.1-Nano ignored the same sentence in 45 of 232 cases [BUILDAGENTIC ch5].

Ng puts the general point bluntly: an LLM given a tool, a task and a turn cap is "highly autonomous, moderately capable, and highly unreliable", and reliable agents need scaffolding, code that guides their steps [NG Build an Autonomous Agent Using This Simple Recipe!, 2025-12-10].

Enforce, in order of strength:
1. **Run it in code** before or after the model turn (fetch the policy and put it in context; check the order before exposing the refund tool).
2. **Gate completion**: the workflow cannot finish until the precondition holds. In SYSTEMS's example, a code review cannot be marked complete until at least one changed file has been analysed [SYSTEMS ch7].
3. **Gate exposure**: the dependent tool is only visible after the prerequisite has succeeded (state-based scoping). This works in your own loop. An MCP server cannot do it: its tool list may vary by the caller's authorization but not per connection or task state. There the handler checks the precondition itself and returns a tool error naming the missing step. A policy gateway in front of the server that supports session rules (call caps, "tool B only after tool A", no outbound calls after a sensitive read) can add order without per-task lists. It needs an authenticated caller to keep sessions apart, and it sees the call history, not the record's state, so the handler check stays.
4. **Force the call** with `tool_choice` set to required or a named tool, on models and settings that support forcing (some current models reject it; see current facts). Only the party that makes the model API call can do this; an MCP server author cannot.
5. **Instruct**, and regression-test the instruction per model. The instruction is necessary but never sufficient on its own.

Do not force tools on steps that are not truly mandatory. In one selection test, two frontier models "failed" every email-tool case because they asked for missing details instead of sending, which was arguably right [BUILDAGENTIC ch5].

## §9 Worked spec: one side-effecting tool

Definition the model sees (Claude API spelling `input_schema`; MCP uses `inputSchema`, OpenAI `parameters`):

```json
{
  "name": "billing_refund_order",
  "description": "Refund part or all of ONE delivered order to its original payment method. Use after billing_get_order has confirmed the order belongs to this customer and its refundable amount. Do not use for subscriptions; use billing_cancel_subscription. amount_cents is in the order's currency, in minor units, and cannot exceed what is still refundable on the order (the total minus earlier refunds). Refunds over 50000 cents need a manager: tell the user instead of calling. Returns refund_id and status. Fails with a readable message if the order is not delivered or the amount is too high.",
  "input_schema": {
    "type": "object",
    "properties": {
      "order_id": {"type": "string", "pattern": "^ord_[0-9]{6}$", "description": "e.g. ord_123456, from billing_get_order"},
      "amount_cents": {"type": "integer", "minimum": 1, "maximum": 50000},
      "reason": {"type": "string", "maxLength": 200, "description": "Short reason shown on the customer's receipt"}
    },
    "required": ["order_id", "amount_cents", "reason"],
    "additionalProperties": false
  }
}
```

Runtime gates, in order (handler sketch):

```python
def run_refund(raw: dict, ctx) -> dict:          # ctx: caller identity, run_id, services
    args = RefundArgs.model_validate(raw)          # 1 shape and ranges -> tool error naming the field
    order = ctx.billing.get_order(args.order_id)
    if not order or not ctx.user.may("refund", order):   # 2 authorization from identity, not args
        return tool_error(f"No refundable order {args.order_id} for this customer.")
    key = idempotency_key(ctx.run_id, "billing_refund_order", args.order_id)
    done = ctx.billing.find_refund(idempotency_key=key)  # 3 key first: a resend gets its original receipt
    if done:
        if done.amount_cents != args.amount_cents:       #   same key, new payload: a conflict, not a refund
            return tool_error(f"This run already refunded {done.amount_cents} cents on {args.order_id}.")
        return receipt(done, key)
    # 4 business rules, as a fast readable refusal. The remaining refundable amount (total minus earlier
    #   refunds, read from billing) stops a second run, which has a new key, from refunding again.
    if order.status != "delivered" or args.amount_cents > order.refundable_cents:
        return tool_error(f"Order is '{order.status}', {order.refundable_cents} cents still refundable; "
                          "only delivered orders, up to the refundable amount.")
    try:  # 5 bounded and conditional: billing refunds only if refundable_cents is still the value read
        r = ctx.billing.refund(args.order_id, args.amount_cents, idempotency_key=key,
                               expect_refundable_cents=order.refundable_cents, timeout=10)
    except ctx.billing.Conflict:                     # another refund landed between the read and the write
        return tool_error("The order changed while refunding. Call billing_get_order and check what is "
                          "still refundable before trying again.")
    except TimeoutError:
        return tool_error("Billing timed out; the refund may still complete. "
                          "Call billing_get_order to check before retrying.")
    return receipt(r, key)

def receipt(r, key: str) -> dict:                    # 6 a receipt, not "done"
    return tool_ok({"status": "committed", "receipt": {
        "refund_id": r.id, "url": r.url, "status": r.status, "idempotency_key": key,
        "applied": {"order_id": r.order_id, "amount_cents": r.amount_cents}}})
```

What it shows: the intent-level name with a namespace, a description that says when not to use it and points to siblings, bounds that live in the schema and are enforced again in code, authorization from identity, and an idempotency key from the run, the action and the target. The key is looked up before any state check, so a resend in the same run (a harness resume, a client retry after a lost reply) gets the original receipt instead of a "nothing left to refund" error that the model could report as a failed refund. Then come the business rules a schema cannot express: the remaining-amount check stops a second run, which carries a new key. That check in the handler is only a fast refusal. Two overlapping runs can both read the same remaining amount, so billing applies the refund only if that amount is unchanged, in one conditional write (a lock on the order does the same job), and the loser gets a readable conflict. Last come bounded execution, a timeout message that prevents a blind retry, and a receipt with the fields as applied. Approval for large refunds sits in the runtime or in an elicitation step, not in this schema.
