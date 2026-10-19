# Tool contracts

Depth for steps 5 to 7 and 13 of the procedure. A tool is an API whose callers are a model and a harness. This file covers what the contract states, how writes become safe to retry, how responses change without breaking prompts and evals, and how a result names the valid next actions. Ownership, inventory, lifecycle and retirement are in [catalog-governance.md](catalog-governance.md). Citation keys are listed under Sources in SKILL.md.

## §1 Why an agent needs a stricter contract

The API design books used here (APIARCH, APIMGMT, RESTCOOK, all from 2022) predate LLM agents. Carrying their rules over to tools is an inference, supported where PRODGUIDE, the MCP book and HARDMCP overlap with them [PRODGUIDE ch7], [MCP ch5], [HARDMCP ch4]. An agent is a harder client than a programmer in four ways, and each one tightens a familiar API rule:

1. **It repeats itself.** The loop retries, the model reissues calls, the harness replays steps after a crash. Every write needs an idempotency rule.
2. **It reads prose.** An error needs a category for the harness and a sentence for the model.
3. **It cannot read a changelog.** Prompts, examples, eval cases and other agents encode a tool's shape, and none of them can make the deliberate decision to adopt a new major version that semantic versioning assumes [APIARCH ch1 §Semantic Versioning]. Never breaking a published tool is the default.
4. **It cannot see server state.** A result that names the valid next actions saves it a guess.

The contract has three readers:

| Reader | Reads | Uses it to |
|---|---|---|
| The model | Name, description, input schema, error sentence, next actions | Choose and fill the call, recover from errors |
| The harness | Permission tier, retry and idempotency rule, failure category, reversibility | Decide what may run, whether to retry, when to stop or compensate |
| Owner and auditor | Receipt, log fields, version, owner, lifecycle stage | Prove what happened; change or retire the tool safely |

## §2 The contract fields

PRODGUIDE's template is short, and every field changes behaviour [PRODGUIDE ch7]:

| Field | What to write | What it changes |
|---|---|---|
| Name and purpose | The single action and its outcome | Selection; what "done" means |
| Inputs | Required and optional fields, types, validation | A missing required field is never guessed: ask, or propose a labelled default for approval |
| Outputs | The receipt (§3) | Whether the agent can verify success, and so whether it may claim it |
| Failure categories | One fixed list (§4) | One behaviour per category |
| Retry policy | When, how many times, when to escalate | Bounded retries and a "needs human" state instead of spinning [PRODGUIDE ch16] |
| Idempotency rule | How reruns avoid duplicates (§5) | Whether retries, replays and redelivered events are safe |
| Permission tier | One of four tiers: read-only, draft-only, approval required, or auto-execute, the last kept rare | What runs without a person and what the preview shows (tool-design-rules §7) |
| Logging requirement | What enters the run record | Audit, debugging, per-version usage counts for retirement |

Add three fields from the other books:
- **Owner and version.** Without them a registry entry cannot be changed or retired [SYSTEMS ch18 §18.5 Tool Platforms and Registries].
- **Reversibility and the compensating action** (§6).
- **Operational constraints:** when the tool may be used at all [AGENTICAI ch5]. This is where "never discount stock tagged for ageing" lives, enforced in the handler.

**One source.** Keep the contract as data beside the code and generate from it the tool description, the published schema, the registry entry and the harness configuration, so the text the model reads and the rule the harness enforces cannot drift. APIMGMT makes the same point for every expression of an interface model [APIMGMT ch5 §Changing the Interface Model]. DEFGUIDE pins and hashes the contract for the length of a run, so a change mid-run cannot alter what "valid" means [DEFGUIDE ch5].

**Allowed actions.** Pair the contracts with an allowed-actions table (tool, action, default tier, receipt) and deny everything off it. PRODGUIDE also keeps a deny list stable across agents: no deleting, external sending, spending, billing changes or credential handling [PRODGUIDE ch7]. An entry leaves the deny list only through a reviewed contract with an approval tier.

## §2a Retrofitting a context object

Keys from run state, authorization from a verified identity and confinement to a workspace all need facts the model must not supply. Many tool layers call `tool.execute(**model_args)` and have no channel for them. Add one without breaking existing tools:
1. Define one small context type: the caller's verified identity, the run ID and step, the workspace root, a deadline.
2. The executor passes it only to tools that declare it, through a reserved keyword parameter found by signature inspection (or a second method whose default calls the old one and drops the context). Existing read tools run unchanged.
3. The reserved name never appears in the published schema, and the executor rejects a call whose model arguments include it, so the model cannot fill identity or the run ID.
4. Migrate write tools first. Until a write tool takes the context, it runs draft-only or is refused (fail closed).

```python
import inspect

def run_tool(tool, model_args: dict, ctx) -> dict:
    if "ctx" in model_args:                                   # reserved: never model-filled
        return problem("invalid_input", "Unknown argument 'ctx'.")
    if "ctx" in inspect.signature(tool.execute).parameters:
        return tool.execute(**model_args, ctx=ctx)
    if tool.writes:                                           # unmigrated write tools fail closed
        return problem("business_rule", f"{tool.name} is not enabled for this agent yet.")
    return tool.execute(**model_args)                         # unmigrated read tools run as before
```

In a review, a missing context channel is one P1 seam finding. The defects it causes (no key, no authorization) are rated once, where they occur (SKILL.md, Review mode).

## §3 Receipts, previews and the result envelope

**Receipt.** A write's success result lets the agent and an auditor confirm what happened without another call: the object's ID and link, the fields as applied (they may differ from the fields requested), a status, the idempotency key echoed back and the contract version. "Done" fails the contract, because a success and a silent no-op look the same. An agent that cannot verify an action must not claim it [PRODGUIDE ch7].

**Preview.** The exact request shown to a person before an approval-tier call runs: titles, recipients, owners, amounts. Approving the payload is a control; approving "Shall I proceed?" approves intent without details [PRODGUIDE ch7]. For irreversible actions add a confirm phrase that names the action [PRODGUIDE ch12], and store the preview, the approver, the time and then the receipt, linked by run ID [PRODGUIDE ch16]. Binding the approval to the payload is in tool-design-rules §7.

**One envelope for every result:**

```json
{
  "status": "committed",
  "receipt": {
    "refund_id": "rf_2291",
    "url": "https://billing.example.com/refunds/rf_2291",
    "applied": {"order_id": "ord_123456", "amount_cents": 4500},
    "idempotency_key": "run_81:billing_refund_order:ord_123456",
    "contract_version": "1.3.0"
  },
  "next_actions": [
    {"tool": "billing_get_refund", "reason": "check settlement", "safe": true, "needs_approval": false}
  ]
}
```

`status` comes from a fixed set (for example `ok` for reads, `committed`, `rejected`, `pending_approval`, `needs_human`). Then comes a `receipt`, `data` or `problem`, then `next_actions` and a `cursor` where they apply. In MCP the envelope travels in `structuredContent`, described by the tool's `outputSchema`; servers must conform to a declared output schema, clients should validate against it, and a serialised text copy helps older clients (current facts). Give the model a one-line summary in the text block and the harness the full object. The envelope also settles a point the specification leaves open, whether an error result must match the output schema: an error is one more shape the schema allows.

## §4 Failure categories and the error body

PRODGUIDE maps five categories to protective behaviours: authentication failures escalate at once, invalid inputs trigger correction instead of retries, rate limits pause and retry conservatively, timeouts trigger verification, and "not found" makes the agent ask which record was meant instead of creating one [PRODGUIDE ch7]. Adding the categories from the HTTP books and the MCP specification gives this working set:

| Category | Retry? | Who acts next | What the model is told |
|---|---|---|---|
| `invalid_input` | Not until corrected | The model | The field, the rule, the fix |
| `auth` | Never | A person | That access is missing; nothing about other people's data |
| `not_found` | No | The model asks the user | Which record was meant; do not create one |
| `conflict` (stale version, duplicate, reused key) | No; re-read first | The model or harness | The current version or the existing ID |
| `rate_limited` | Yes, after the wait, capped | The harness | Nothing unless the budget runs out |
| `unavailable` | Yes, with backoff, capped | The harness | Nothing unless retries run out |
| `outcome_unknown` | Only after verification (§5) | The harness | That it may have happened and is being checked |
| `business_rule` | No | The model tells the user | The rule, in one sentence |

The retry column follows RESTCOOK: a client error will not succeed if repeated unchanged, a server error or dropped connection may. Back off exponentially, retry at most three times, and remember that retries compound: about 90 seconds across three sequential calls through one faulty gateway [RESTCOOK ch7 §7.16]. Conflicts come from conditional writes, which fail with 412 when the resource changed since it was read [RESTCOOK ch3 §3.6]. The SKILL.md error-routing table says which of these the model sees at all.

**The body is RFC 9457 problem details**, which obsoletes RFC 7807 (current facts): a `type` URI, a fixed `title`, the `status`, an occurrence-specific `detail` and an `instance`, plus documented extension members of your own, and no debugging information [RESTCOOK ch5 §5.12]. One piece of client code should handle every error, status codes must be accurate, and an error never hides inside a 2xx response [APIARCH ch1 §Error Handling]. RFC 9457 adds that clients ignore extension members they do not recognise.

```json
{
  "type": "https://tools.example.com/problems/business-rule",
  "title": "Order not refundable",
  "status": 422,
  "detail": "Order ord_123456 is 'shipped'; refunds need status 'delivered'. Tell the user the refund is possible after delivery.",
  "instance": "/runs/run_81/steps/3",
  "category": "business_rule",
  "retryable": false
}
```

In MCP, return it as a tool execution error (`isError: true`), with `detail` as the text and the object in the structured block. Keep `detail` about the interface, not the implementation, and never let an `auth` problem confirm that someone else's record exists.

How that maps onto the MCP Python SDK v2 (current facts): `raise ToolError(detail)` in a high-level `MCPServer` tool returns the text only, with `structured_content` empty. To return both, build the result in a low-level handler: `content` holds the `detail` sentence, `structured_content` holds the envelope with its `problem`, and `is_error` is true. If a tool must stay on the high-level server, the category can travel only as a fixed token in the text that the client maps back, the weaker option. The SDK puts its own prefix in front of the message (`Error executing tool <name>: business_rule: Order ord_123456 is ...`, as of 2026-10; confirm against the installed version), so the client matches the category token after that prefix, never as the first token of the text. Either way, declare an output schema whose envelope allows the `problem` shape (§3): the SDK's own client rejects structured content that fails the declared schema, and neither the specification nor the SDK documentation says whether error results are exempt.

## §4a Wrapping a backend whose errors are unstructured

Many APIs a tool wraps answer failures with an HTML page, a bare status line or a body nobody documented. The tool needs an adapter between the backend and the model. It maps each response to one category, logs the raw body with the run ID, and gives the model only the category and one sentence. HTML, stack traces and raw bodies never reach the model.

| Backend response | On a read | On a write that was sent |
|---|---|---|
| 400 or 422 naming a field | `invalid_input` | `invalid_input` |
| 401, 403 | `auth` | `auth` |
| 404 | `not_found` | `not_found` (nothing was created) |
| 409, 412 | `conflict` | `conflict`: re-read before anything else |
| 429 | `rate_limited`, honour `Retry-After` | `rate_limited` if the backend documents that a 429 is not processed (most do; confirm yours), else `outcome_unknown` |
| 500, 502, 504, connection reset, timeout after sending | `unavailable`: retry with backoff, capped | `outcome_unknown`: verify by key or lookup before any retry |
| 503, or a failure before the request left (DNS, refused connection, TLS) | `unavailable` | `unavailable` only if it failed before sending or the backend documents a 503 as not processed; otherwise `outcome_unknown` |
| 2xx with an HTML or unparseable body | `unavailable` | `outcome_unknown` |

The write column prevents double charges. `unavailable` is retried with backoff, so a 502 filed as `unavailable` after a charge that did commit charges the customer twice behind a backend that does not deduplicate. Only a failure before sending, or a response the backend documents as "not processed", may be retried blind. Contract tests force each row through the real client (§9).

**The category must survive every hop.** The MCP book's example client drops both the error flag and the structured content, and its agent joins the remaining text [MCP repo: ch3/12_make_tool_calls/client.py], [MCP repo: ch3/12_make_tool_calls/agent.py]. A server that answers a timed-out create with "Please try again" in plain text, and no flag, invites exactly the duplicate a contract prevents [BUILDAGENTIC repo: sdr_multi_agent/mcp_servers/hubspot_server/mcp_server.py]. A contract test forces each category and asserts that it reaches the harness and the model through the real client (§9).

## §4b Read why the turn stopped before running a call

The contract assumes a tool receives the arguments the model meant to send. A client loop that runs every tool call in a response breaks that in three cases:
- **Cut off by the output limit.** The last tool call can be incomplete. Running it sends a write half its arguments, or a file tool half its content. Run no call from that turn; re-request with a higher limit, or ask for less output.
- **Paused by provider-hosted tools.** A turn that ran server-side tools (web search, code execution) can pause with no client call in it. Continue it the way the provider documents. Never return it as the final answer, and never read "no client calls" as "done" without checking why the turn stopped.
- **Refused.** A refusal is neither a success nor an empty answer. Record it and follow the refusal or fallback policy.

So the loop reads the stop reason first and runs tool calls only from a turn that stopped in order to call tools. In a review, running truncated arguments against a write tool is P1, and P0 when the write is irreversible. The stop values per provider are in current facts, "Stop reasons"; the loop itself belongs to agent-harness-designer.

## §5 Idempotency: make writes safe to retry

Repeating an operation must have no further effect. There are three mechanisms; a write uses whichever fits.

| Kind | How | Use for |
|---|---|---|
| Network idempotence | Methods that may be resent, such as PUT rather than POST [RESTCOOK ch3 §3.8] | Choosing the call shape when you own the API |
| Operation idempotence | A target state guarded by what you expect to find ("if the price is 100, set it to 105"), never a delta ("add 5%") [RESTCOOK ch3 §3.8] | Updates |
| Request identity | A client-chosen ID written with PUT-create (`If-None-Match: *`), or an idempotency key the backend deduplicates on [RESTCOOK ch5 §5.15], [PRODGUIDE ch16] | Creates and sends, which have nothing to guard |

**Operation idempotence first.** A half-done batch of guarded replacements can be rerun, because rows whose value no longer matches are skipped; a half-done batch of deltas cannot. The guard (a version or ETag from the read the agent relied on) also turns "acted on stale data" into a `conflict` instead of a silent overwrite when two agents, or an agent and a person, edit one record [RESTCOOK ch3 §3.6].

**Request identity for creates and sends.** Use PUT-create where you own the backend and a key where you wrap a POST API you do not. If the backend supports neither, write the run ID into the object's metadata and look for it before creating [PRODGUIDE ch7]. MCP's `idempotentHint` describes operation idempotence only, and it is a hint.

**The key comes from durable run state.** Three details decide whether it works:
- **Origin.** Derive the key from the run ID, the action and the intended target [PRODGUIDE ch16], for example `run_81:billing_refund_order:ord_123456`. A random key is safe only if it is created once and stored in the run record before the first attempt. The model's tool-call ID and the attempt number never work: they change on every reissue, retry, resume and replay. A fresh random request ID per run means nothing downstream can recognise the repeat [RELATED repo: apis-and-agents/job-control/index.js].
- **Width.** Run, action and target allow one such action per target per run. If a plan legitimately refunds one order twice, add the plan step or a line-item ID. A hash of all the arguments is too narrow: a rephrased `reason` produces a new key and a second refund.
- **Backend behaviour.** Write it into the contract. The IETF Idempotency-Key draft returns the first result for a completed repeat, 422 for a reused key with a different payload, 409 while the first request is still running and 400 for a missing key, and asks the server to publish an expiry. The draft expired without becoming an RFC, so these are convention, not standard (current facts).

**Verify before retry.** A write that timed out or lost its reply is `outcome_unknown`: it may or may not have happened. The safe next step is to check whether it completed, by reading the target, looking the request up by its key or reconciling, with capped attempts and a "needs human" state at the end [PRODGUIDE ch16]. Retry only if verification finds nothing, and with the same key, so a request still in flight meets the backend's 409 instead of creating a twin. A send that cannot be looked up afterwards needs provider-side idempotency, or a draft that a person sends. The same holds in client code that calls tools across a process or network boundary, such as an MCP client: a timeout or transport error on any tool that is not read-only maps to `outcome_unknown`, never to a plain failure with the error flag set, because the model reads a plain failure as permission to call again.

**Duplicates also arrive from outside the loop.** Stateless MCP transports re-send a broken request instead of resuming it [MCP ch4 §Following Best Practices]; event-driven agents get at-least-once delivery [PRODGUIDE ch16]; and a durable-workflow step that wraps a model call and its tool calls repeats every tool call in it when retried [BUILDAPPS repo: src/frameworks/langgraph_agents/supply_chain/temporal_supply_chain_multi_agent.py]. Keep one keyed side effect per retried unit. Where the harness records the key, checkpoints and replays is agent-harness-designer's subject.

**No run ID.** An MCP server inside a host you do not control never sees the run. Key on the business object and rely on the handler's state check (tool-design-rules §6).

Harness sketch (provider-neutral):

```python
class OutcomeUnknown(Exception):
    """Timeout or lost reply: the write may have happened."""

def execute_write(tool, target_id, args, run, backend, max_attempts=3):
    key = f"{run.id}:{tool}:{target_id}"                  # same on retry, resume and replay
    run.record("intent", tool=tool, key=key, args=args)   # saved before the first attempt
    for attempt in range(1, max_attempts + 1):
        try:
            receipt = backend.call(tool, args, idempotency_key=key)
        except OutcomeUnknown:
            receipt = backend.find_by_key(key)            # verify before any retry
            if receipt is None:
                backend.backoff(attempt)
                continue                                  # retry with the SAME key
        except backend.Problem as p:                      # categorised problem-details body
            run.record("problem", key=key, problem=p.body)
            return {"status": "rejected", "problem": p.body}
        run.record("receipt", key=key, receipt=receipt, attempts=attempt)
        return {"status": "committed", "receipt": receipt}
    run.record("needs_human", key=key)
    return {"status": "needs_human", "idempotency_key": key}
```

Tests that keep it true: the same key twice gives one object and one receipt; a backend that commits and then times out gives no second object and `attempts == 1`; a reused key with a new payload gives a `conflict`.

## §6 Compensation and reversibility

RESTCOOK gives three ways to undo a write: a second conditional write that restores the old value; an undo command backed by stored history, which for multi-service actions needs every service's cooperation [RESTCOOK ch3 §3.9]; or a short local undo window, by keeping history or by delaying the change and dropping it if an undo arrives [RESTCOOK ch7 §7.17]. Its workflow pattern makes this systematic: each task supports Execute, Repeat and Revert, each carries a request ID, and Revert succeeds without acting if Execute never ran [RESTCOOK ch7 §7.1]. That last property is what an agent needs after an `outcome_unknown` step.

A prototype orchestrator falls into two traps: it reverts every step whether or not the command is declared reversible, logs a failed revert as a warning and moves on [RELATED repo: apis-and-agents/job-control/index.js], [RELATED repo: apis-and-agents/engine/design.json]. The rules:
1. Every write declares `reversible`. A reversible one names its revert action, keyed by request ID and safe to call when the write never happened.
2. Irreversible steps run last, behind an approval bound to the previewed payload.
3. A failed compensation escalates to a person. It is never only a log line.
4. Prefer drafts: a draft email can be deleted, a sent one cannot [PRODGUIDE ch7].

MCP cannot carry rule 1. Its annotations are four hints (`readOnlyHint`, `destructiveHint`, `idempotentHint`, `openWorldHint`) with no reversibility hint and no version field. "Destructive" is not "irreversible": the schema calls a tool non-destructive when it makes only additive updates, and sending an email is additive and permanent (current facts). Keep reversibility in your own contract and catalogue, where the harness reads it.

## §7 Responses that can evolve

- **Wrap every collection.** A bare JSON array cannot gain a next-page link without becoming an object, which breaks every consumer [APIARCH ch1 §Collections and Pagination]. Return `{"items": [...], "next_cursor": "...", "truncated": true, "total": 47}`. The model also needs to know it has not seen everything. The MCP specification allows arrays as structured content and uses one in its own example; allowed is not advisable.
- **No personal data in identifiers.** APIARCH rejects an email as a resource ID because paths get cached and logged [APIARCH ch1 §REST API Standards and Structure]. For agents the leak is wider: an argument lands in the transcript, the trace, the prompt cache, eval datasets and sometimes memory. Use opaque IDs, and pass an email as a field only when it is genuinely the input.
- **Sensitive fields stay out of results.** National IDs, bank and card data, health data, salary and similar regulated fields are not returned unless an agent story needs them. When one does, the field comes from a separate tool with its own scope, masked by default. No tool returns every record of a personal-data collection; lists need a filter and a page size. A CI test scans tool results for these field patterns (an ID-number or card-number shape) and fails on a hit.
- **Handles are names, not permissions.** Re-check authorization on every call, state the lifetime in the creating tool's description, and return a tool error when a handle expires (tool-design-rules §6).
- **Leave room to add.** Extend with parallel properties instead of replacements (keep `name`, add `given_name` and `family_name`) and with extension objects. All of it relies on consumers ignoring what they do not understand [RESTCOOK ch3 §3.10], [RESTCOOK ch2].
- **Strict inputs, tolerant outputs.** No book states this rule; this skill infers it from RESTCOOK's rule that consumers ignore what they do not understand. Input schemas reject unknown arguments (`additionalProperties: false`), because a hallucinated argument is a bug. Output schemas allow additional properties, so adding a result field never breaks a client that validates.

## §8 Change without breaking the model

RESTCOOK's three rules define a breaking change: take nothing away, redefine nothing, make every addition optional [RESTCOOK ch2]. A tool's interface is wider than a code API's, because one of its consumers reads prose:

| Change | Breaks code callers? | Breaks model callers? |
|---|---|---|
| Add an optional input with a default | No | Rarely; re-run the tool-choice eval |
| Add a required input, or tighten validation | Yes | Yes |
| Rename or remove a field | Yes | Yes: prompts, examples and eval assertions name it |
| Add an output field | No, if unknowns are ignored | No, but every call pays its tokens |
| Change a default, unit, sort order or page size | The shape survives, the meaning does not | Yes |
| Rename a failure category | Yes, for the harness | No |
| Reword the description | No | Possibly: selection can shift, and pinned clients halt |

**Description edits are changes.** A prompt tuned against one version of a contract can break when fields change, and a model may rely on a response shape that later disappears [SYSTEMS ch18 §18.5 Tool Platforms and Registries]. Clients that pin definitions hash each approved definition and halt with a diff when it drifts [HARDMCP ch4]. Ship a description change as a versioned change with a changelog, so re-approval is quick, and re-run the tool-choice eval. Why clients pin, and how: agent-threat-modeler.

**Never break by default.** The consumers of a tool are prompts, eval suites and other agents, and none of them can make the upgrade decision a major version assumes, so RESTCOOK's position is the right default: add, don't change, and fork only when forced [RESTCOOK ch3 §3.11]. When a break is unavoidable, use APIARCH's mechanics: a new version in a new location beside the old one, with semantic versioning saying which kind of release this is [APIARCH ch1 §API Versioning]. For a tool the new location is a new name. MCP tools have no version field, but names such as `DATA_EXPORT_v2` are legal, so `crm_create_contact_v2` beside `crm_create_contact` is visible to every reader, the model included. Run both until callers have moved, then retire the old one with usage data ([catalog-governance.md](catalog-governance.md) §5). The exception is a tool with one consumer in the same repository: there a lockstep change is fine, because the tool, the prompt and the evals change in one commit.

**Exposure overrides the deprecation window.** "Never break" governs compatible evolution, not exposure. When the published tool is itself the vulnerability (it returns personal data in bulk, runs an irreversible action without the approval its tier needs, or bypasses authorization), disable it at once under the same name: every call returns a structured tool error (category `business_rule`, not retryable) whose sentence names the replacement, if there is one. Notify the owners of the calling agents from the catalogue ([catalog-governance.md](catalog-governance.md) §2) and record an incident. The replacement then follows the normal rules, and the disabled name is retired through catalog-governance §5.

**Upstream changes.** The tool owner owns the model-facing contract, and the adapter (§4a) decouples it from the API it wraps. When a partner renames a field (`confirmation_no` becomes `booking_ref` next quarter), the adapter maps the new name and the tool's contract stays as it was. Put the upstream spec under the same CI: diff it on every pull and run the contract tests against the partner's sandbox, so a rename fails a build instead of a booking. A change of meaning upstream (units, enum values, a default) is a break for the tool as well and ships as a v2 under the rules above. Record the upstream API and its version in the catalogue entry, so its owner knows whom a change will hit.

## §9 Contract checks in CI

1. **Schema diff.** Diff definitions, schemas, enums and failure categories against the last release, and fail on any unversioned break. Diff tools are tied to a specification version: APIARCH's found no breaking change at all when run against an older one [APIARCH ch1 §OpenAPI Specification and Versioning]. Prove the step with a planted break.
2. **Producer contract tests.** One example interaction per tool and per failure category, failures included [APIARCH ch2 §How a Contract Is Implemented], run through the real client so you see what the model and the harness actually receive: error flag, category and structured content. They run against a sandbox, a recorded backend or a stub with test credentials, never against production writes.
3. **Consumer-driven contracts.** Within one organisation APIARCH prefers contracts the consumer submits [APIARCH ch2 §Consumer-driven contracts]. For agents, the consuming agent's tool-choice eval and golden runs play that role, provided they load definitions from the running server. The MCP book's selection eval hand-writes its schemas, so a server change would never fail it [MCP repo: ch7/01_simple_evaluation/test.py].
4. **Keep CI away from production.** CI holds no production secrets. On GitHub, run these checks on the `pull_request` trigger, never `pull_request_target`, which runs in the base repository's context with its secrets and a write-scoped token, so checking out or running a fork's code there exposes them.

## §10 Next actions in results

For state-dependent tools, put the actions possible now inside the result, with their inputs and rules, so the client follows them instead of hard-coding a workflow [RESTCOOK ch3 §3.5]. The set can differ by user and by server state. When the list grows long, return the common actions inline and the rest from a separate "related" lookup [RESTCOOK ch7 §7.8].

Each entry in `next_actions`: the tool name, a one-line reason, the flags `safe`, `idempotent` and `reversible`, whether approval is needed, and arguments the server can prefill. A refund in `pending_approval` advertises `billing_approve_refund` and `billing_cancel_refund`, not `billing_refund_order`. The model makes fewer invalid calls, and the harness gets a server-computed list for narrowing the next turn's tools. The ALPS checklist makes this lintable: every transition typed safe, unsafe or idempotent with a return state, and every non-terminal state with an outbound transition [RELATED repo: ai-apis-design-with-alps/01-api-stories-to-alps/05-alps-verification-checklist.md].

Three rules:
- **Next actions grant nothing.** The harness intersects them with its allowlist and the permission tiers, because tool content may inform the model but never trigger an action [HARDMCP ch6].
- **They go in results, not in `tools/list`.** The MCP specification lets a tool list vary with the request's authorization but not per connection or as a side effect of other requests (current facts). The list says what a caller may ever do; `next_actions` says what makes sense now.
- **Keep the flags at the protocol edge.** One MCP projection of a service drops its declared safe, idempotent and reversible flags [RELATED repo: apis-and-agents/mcp-discovery/person-service-affordances-mcp.json]. Carry them in the envelope.

Skip the pattern for stateless lookups, and keep inline lists short: every advertised action costs tokens.

## §11 Contract review checklist

1. Does every tool have the eight contract fields plus owner, version, reversibility and operational constraints before production agents can call it, all generated from one source?
2. Does every write return a receipt (ID, link, applied fields, status, key, contract version), and is the agent barred from claiming an action without one?
3. Are updates replacements guarded by a version or ETag, so a stale agent gets a `conflict`?
4. Do creates and sends carry a key from durable run state, honoured by the backend, with duplicate, conflict and expiry behaviour written down?
5. Is a timeout `outcome_unknown`, with a named verification read before any retry, a cap and a "needs human" state?
6. Does every failure carry a category from one fixed list in a problem-details body plus one sentence for the model, and does a test prove both survive the real client?
7. Does each write declare `reversible` and name a revert keyed by request ID, with irreversible steps last behind an approval bound to the preview?
8. Is every result an envelope, with cursors or `truncated` flags on lists, opaque identifiers, strict inputs and outputs that tolerate added properties?
9. Does CI diff definitions, schemas, enums and categories against the last release, block unversioned breaks and prove itself with a planted break?
10. Do consuming agents' tool-choice evals and golden runs load definitions from the live server?
11. Do state-dependent tools return flagged `next_actions` that the harness intersects with its allowlist, and does `tools/list` stay stable per authorization?
12. Does an adapter map every status and error page of a wrapped backend to a category (§4a), with a 5xx or timeout after a write was sent filed as `outcome_unknown`, and does CI diff the upstream spec and run contract tests against its sandbox (§8)?
