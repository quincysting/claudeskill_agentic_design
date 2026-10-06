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
- Use only `A-Z a-z 0-9 _ -`, at most 64 characters. That is the strictest limit among the targets checked: MCP allows 128 characters and dots, Claude's API 128 without dots, OpenAI's API and the Claude connector directory 64 (per-target table in current facts).

**Description template** (three to six sentences; longer for complex tools):

```
<What it does, in one sentence, with the object it acts on.>
Use when <situations>. Do not use for <near-miss cases>; use <sibling_tool> instead.
<Inputs: meaning, units, formats, where the value usually comes from (e.g. "order_id from crm_find_orders").>
<Preconditions: what must be true or called first.>
Returns <shape, key fields>. <Side effects, limits, latency or cost if notable.>
<Failure behaviour the model should expect, e.g. "Fails if the order is not paid.">
```

This covers the five parts of a tool specification: identity, inputs, outputs, operational constraints and error handling [AGENTICAI ch5]. Write it as you would explain the code to a capable new hire: make explicit the context you hold implicitly. Then ask a model where the description is vague or overlaps with another tool [MCP ch5].

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
- **Keep `required` minimal and meaningful.** Defaults go in the schema and the description.
- **No catch-alls.** `**kwargs`, `options: object` and `extra: string` leave nothing to validate and invite hallucinated fields. Set `additionalProperties: false`.
- **No conditional requirements.** If `mode=x` requires `a` and `mode=y` requires `b`, split the tool (§1).
- **Never model-filled:** caller identity, tenant, role, approval status, auth tokens, idempotency keys. The runtime injects them. A parameter the model can fill is a parameter an injected instruction can fill.
- **Free-text fields asking "why"** should ask for a short explanation or the supporting evidence, not the model's step-by-step reasoning. Some providers refuse to emit reasoning into parameters (see current facts).
- **Input examples** help with nested, optional-heavy or format-sensitive inputs. In Anthropic's tests, adding them raised accuracy on complex parameter handling from 72% to 90% (Advanced tool use, 2025-11). Each example costs prompt tokens on every call.
- **Strict mode** (constrained decoding to the schema) guarantees shape, not truth. Provider limits apply (unsupported keywords, caps on strict tools per request), and it does not hold when the model refuses or runs out of tokens. Keep business validation either way. See current facts.
- **Validate with a schema library** (Pydantic, jsonschema, zod), not regular expressions [ILLUSTRATED ch5]. Validate against the schema first, then against business rules: a request can be well formed and still not allowed [SYSTEMS ch4].

## §4 Results

- **Structured beats prose for the next decision** [SYSTEMS ch7]. Return a JSON object with stable field names and also a short text rendering where the protocol expects text (MCP: `structuredContent` plus a text block).
- **Names next to IDs.** Return `{"id": "usr_8812", "name": "Dana Ruiz"}`, not just an opaque ID the model must carry blind. Return stable, meaningful identifiers (slugs, UUIDs), not internal row pointers.
- **Only high-signal fields.** Drop internal metadata, nulls and audit columns. Each extra field costs tokens on this turn and every later turn.
- **Bound the size.** Paginate or truncate by default, state in the result that it was truncated, and say how to get more ("47 more; call again with page=2 or narrow the date range"). Offer `response_format: concise|detailed` when callers sometimes need full records. In Anthropic's Slack example the concise form took 72 tokens and the detailed one 206 (Writing tools for agents, 2025-09).
- **Large payloads go out of band.** Return a URL, a presigned link or a resource link plus a summary. Base64 inflates binary by about a third, and the MCP book suggests keeping messages under about 100 KB [MCP ch8].
- **Results are untrusted input.** A web page, email or ticket body returned by a tool can carry instructions. Mark external content as data (fenced, labelled with source), strip active content you do not need, and never let a result widen the agent's permissions. Deep treatment: agent-threat-modeler.
- **Be deterministic where you can.** The same input over the same state gives the same output; inconsistent tools make orchestration fragile [SYSTEMS ch7].

## §5 Errors the model can act on

**The routing question:** could the model, or a better model, or this model with more information, do something useful with this failure? If yes, return a tool error it can read. If no, handle it in code (retry, fallback, escalate) or reject at the protocol level [MCP ch5]. "Something useful" includes telling the user why the action cannot happen. That is why the current MCP spec lists input validation errors and business-logic errors as tool execution errors, and keeps protocol errors for unknown tools, malformed requests and server faults. The MCP book's example raises a protocol error for "grades not posted yet" [MCP ch5]. Under the current spec that is better returned as a tool error the model can relay.

**Message pattern:** what was wrong, what is allowed or what the state is, what to do next. One or two sentences. No stack traces, no internal codes without meaning.

| Instead of | Return |
|---|---|
| `KeyError: 'ord_12'` | `No order ord_12 for this customer. Check the ID with crm_find_orders.` |
| `400 Bad Request` | `start_date must be today or later (got 2026-09-30). Ask the user for a new date.` |
| `Refund failed` | `Order ord_123456 is 'shipped'; refunds need status 'delivered'. Tell the user the refund is possible after delivery.` |
| `TimeoutError` (on a write) | `Billing timed out; the refund may still complete. Call billing_get_order to check before retrying.` |

**Two retry loops, both bounded** [DEFGUIDE ch5]. The inner loop re-asks the model with the validation error, up to two or three times. The outer loop is the orchestrator: it decides whether to rerun the step, ask the user or stop. Unbounded re-asks burn tokens and can loop.

**Validate, retry, fall back, log** [BUILDAPPS ch4]. After each model turn, check the right tool was called, the JSON parsed, and nothing failed at runtime. Retry transient faults with exponential backoff and jitter. When retries run out, fall back (backup service, cached data, safe default, ask the user). Log every step.

## §6 Side effects, state and resilience

**Idempotency.** Retries, client re-sends after dropped connections and the model reissuing a call all happen in production. Repeating an operation must not repeat its effect [SYSTEMS ch4]. Under stateless MCP a dropped request is re-sent, so deduplicating non-idempotent calls is the client's and host's job [MCP ch4].

```python
import hashlib, json

def idempotency_key(task_id: str, tool: str, args: dict) -> str:
    # Same task + same operation + same arguments -> same key, however often the model reissues it.
    # Never use the model's tool-call ID: it changes on every reissue.
    material = json.dumps({"t": task_id, "tool": tool, "args": args}, sort_keys=True)
    return hashlib.sha256(material.encode()).hexdigest()[:32]
```

Pass the key to a backend that stores it and returns the first result for repeats. If the backend cannot, keep a dedupe table in your runtime keyed the same way. Decide deliberately whether "the same refund twice in one task" is a duplicate (usually yes) or two intended actions (then the arguments must differ, e.g. a line-item ID).

**No task ID.** An MCP server running in Claude Desktop, an IDE or a partner's agent never sees your task or conversation ID, and stateless MCP has no session to borrow one from. Two layers then do the work:
1. **The state check stops duplicates.** The handler re-reads the business object and refuses what its state does not allow: refund at most the remaining refundable amount, cancel only an order not yet cancelled, ship only what is unshipped. A second identical refund then fails with a readable error ("Order already refunded in full") whether or not anything deduplicated it.
2. **A natural key catches the exact resend.** Key on the business object and the operation's arguments (`order_id`, `amount_cents`, line items) within a short window, such as 10 minutes, so a transport resend lands on the first result. Be aware that this also blocks a deliberate second refund of the same amount in that window. Make such a refund distinguishable (a line item, a reason code, a client-supplied request reference) or have the model say why it is retrying.

Never key on the model's tool-call ID or on a timestamp.

**Timeouts.** Every call gets one, set from the backend's p99 latency plus a margin, not a blanket 30 s. Reads can retry twice with backoff. Writes retry only with an idempotency key, and only in code. A timeout on a write means "unknown", not "failed": say so in the message and offer a status tool.

**State across calls** (carts, browser sessions, transactions, long jobs). Return an opaque handle from a create tool and take it as an argument on later calls. Authorise the caller against the handle on every call, because a handle is a name, not a permission. Give handles high entropy and a bounded lifetime, state the lifetime in the create tool's description, and return a tool error naming the expiry when a handle is stale, so the model can create a new one (MCP spec, Stateful Tools).

**Long-running work.** A start tool returns a job ID at once and a status tool reports progress and the result. On MCP, the Tasks extension standardises this when your SDK and clients support it.

**Resilience for tools you do not control** [AGENTICAI ch5]. Rate each tool on control (how much you influence its availability) and impact (how much the task depends on it). Low-control, high-impact tools are critical: give each a pre-built fallback, test it by simulating an outage, and when no fallback remains, escalate to a human with the failure, the task status and a proposed remedy. Agents re-plan around missing tools but do not invent new ones, so the backup must exist in advance [AGENTICAI ch5].

## §7 Permissions and approvals

- **A tool call is a request, not authority** [SYSTEMS ch7]. Treat it like an inbound request from an untrusted client: validate, authorise, log, bound.
- **Narrow over broad.** One documented agent "optimised" a database by dropping half the rows of a production table through a generic SQL tool [BUILDAPPS ch4]. Prefer named operations (`crm_get_account(account_id)`).
- **Free-form query and command tools (raw SQL, shell, arbitrary HTTP).** Never give one to an agent that serves end users or reads untrusted content (chat messages, emails, web pages, tickets); remove it in a review (P0). If staff need ad-hoc queries, put the tool in a separate staff-only agent or server with staff authentication and:
  - a read-only account on a replica, scoped to allowlisted views without secrets or unneeded PII;
  - parameter binding where it applies, DDL and bulk DML rejected, row and time limits;
  - every query logged, with alerts on unusual volume;
  - read and write never in one tool (a catch-all `api_request` with a `method` parameter fails Claude's connector directory review);
  - a description that names the target API or schema documentation.
- **Authorization in code** from the authenticated caller, per object (user A cannot touch user B's records) and per tool (admin tools only for admins). Do not reveal whether an object exists to someone not allowed to see it.
- **Least-privilege credentials per tool.** A read tool runs with read credentials even if the agent also has write tools.
- **Progressive access.** A new agent starts on read tools and earns write tools after it proves reliable, as with an inventory agent that queries stock before it may change orders or prices [AGENTICAI ch5].
- **Scope the visible list.** Show only the tools the caller's scopes permit. Filter by task state too wherever you assemble the list per turn: your own loop, or an MCP host or client you control (it can pass the model a subset of a server's tools). An MCP server cannot: its list may vary by the authorization on the request, not by task state (§8).
- **Approval** for irreversible, high-value, externally visible or bulk actions, enforced by the runtime (an approval step the model cannot skip) or by MCP elicitation, where the approval parameter is resolved by the server and never appears in the model-facing schema. If the host auto-approves, the gate degrades to a prompt, so the host's consent UI is part of the control. An elicitation answer shows only that the client said yes: users can set a host to answer automatically (Claude Code's Elicitation hook does this), and it never proves which person approved. When policy needs a named approver (a manager over a limit), use the propose-only path below with sign-in in your own UI.
- **Choosing the threshold.** Start from the existing human policy: the agent's limit is no higher than what a front-line employee may do without sign-off. Set it lower if the loss you would accept from one wrong action is lower. Irreversible actions that reach outside the company (payments out, emails to customers, deletions without undo) need approval at any amount until evals and production data show the agent is reliable; then raise limits step by step, as with progressive access. Write the threshold down as an assumption for the owner to confirm.
- **When nobody can be asked** (a client without elicitation, a batch run): degrade to propose-only. The tool records a pending action with a summary and returns its reference. A human approves it in your own UI, and the backend executes it, never the agent. A destructive tool that fails whenever approval is impossible is safe but useless; pair it with this path.
- **Annotations are hints.** `readOnlyHint`, `destructiveHint`, `idempotentHint` and `openWorldHint` help a trusted client decide what to confirm. Clients must not base decisions on annotations from untrusted servers (MCP spec).
- **Escalate to agent-threat-modeler** when an agent combines access to private data, exposure to untrusted content and a way to send data out (the lethal trifecta), when tools execute model-written code or shell, or when a server proxies third-party OAuth [MCP ch7].

## §8 Mandatory steps

Correct selection is never guaranteed: a model may skip a required step, choose the wrong capability or stop early [SYSTEMS ch7]. In one measured case, GPT-4.1 given a document-lookup tool but no instruction almost never called it and scored 47.8% on policy questions, barely above 44.4% with no tool. One system-prompt sentence telling it always to use the tool lifted it to 70.7%, while GPT-4.1-Nano ignored the same sentence in 45 of 232 cases [BUILDAGENTIC ch5].

Enforce, in order of strength:
1. **Run it in code** before or after the model turn (fetch the policy and put it in context; check the order before exposing the refund tool).
2. **Gate completion**: the workflow cannot finish until the precondition holds. In SYSTEMS's example, a code review cannot be marked complete until at least one changed file has been analysed [SYSTEMS ch7].
3. **Gate exposure**: the dependent tool is only visible after the prerequisite has succeeded (state-based scoping). This works in your own loop. An MCP server cannot do it: its tool list may vary by the caller's authorization but not per connection or task state. There the handler checks the precondition itself and returns a tool error naming the missing step.
4. **Force the call** with `tool_choice` set to required or a named tool, on models and settings that support forcing (some current models reject it; see current facts). Only the party that makes the model API call can do this; an MCP server author cannot.
5. **Instruct**, and regression-test the instruction per model. The instruction is necessary but never sufficient on its own.

Do not force tools on steps that are not truly mandatory. In one selection test, two frontier models "failed" every email-tool case because they asked for missing details instead of sending, which was arguably right [BUILDAGENTIC ch5].

## §9 Worked spec: one side-effecting tool

Definition the model sees (Claude API spelling `input_schema`; MCP uses `inputSchema`, OpenAI `parameters`):

```json
{
  "name": "billing_refund_order",
  "description": "Refund part or all of ONE delivered order to its original payment method. Use after billing_get_order has confirmed the order belongs to this customer and its total. Do not use for subscriptions; use billing_cancel_subscription. amount_cents is in the order's currency, in minor units, and cannot exceed the order total. Refunds over 50000 cents need a manager: tell the user instead of calling. Returns refund_id and status. Fails with a readable message if the order is not delivered or the amount is too high.",
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
def run_refund(raw: dict, ctx) -> dict:          # ctx: caller identity, task_id, services
    args = RefundArgs.model_validate(raw)          # 1 shape and ranges -> tool error naming the field
    order = ctx.billing.get_order(args.order_id)
    if not order or not ctx.user.may("refund", order):   # 2 authorization from identity, not args
        return tool_error(f"No refundable order {args.order_id} for this customer.")
    if order.status != "delivered" or args.amount_cents > order.total_cents:   # 3 business rules
        return tool_error(f"Order is '{order.status}', total {order.total_cents} cents; "
                          "only delivered orders, up to the total.")
    key = idempotency_key(ctx.task_id, "billing_refund_order", raw)          # 4 same refund, same key
    try:
        r = ctx.billing.refund(args.order_id, args.amount_cents, idempotency_key=key, timeout=10)  # 5 bounded
    except TimeoutError:
        return tool_error("Billing timed out; the refund may still complete. "
                          "Call billing_get_order to check before retrying.")
    return tool_ok({"refund_id": r.id, "status": r.status, "order_id": args.order_id})
```

What it shows: the intent-level name with a namespace, a description that says when not to use it and points to siblings, bounds that live in the schema and are enforced again in code, authorization from identity, business rules a schema cannot express, an idempotency key from the task and the operation, bounded execution, and a timeout message that prevents a blind retry. Approval for large refunds sits in the runtime or in an elicitation step, not in this schema.
