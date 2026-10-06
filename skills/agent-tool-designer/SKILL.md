---
name: agent-tool-designer
description: Designs and reviews the tools an LLM agent calls, and the MCP servers and clients that carry them. Covers tool granularity, naming, input schemas, descriptions, result shape, errors the model can act on, idempotency, permissions and approvals, tool count and selection strategy, and protocol choice (native function calling, MCP, CLI, Agent Skill or A2A) with MCP transports and auth. Produces a tool specification set or a review with prioritised fixes. Use for "design tools for my agent", "review my tool definitions/schema", "build an MCP server", "review my MCP server", "MCP vs function calling", "too many tools", "agent picks the wrong tool", "agent ran the action twice", "A2A", or exposing an API to agents. Not for overall agent architecture (agent-architect), memory or RAG (agent-context-designer), full eval programs (agent-eval-designer), production monitoring and cost (agent-ops-reviewer), deep security review of tools (agent-threat-modeler) or model choice (agent-model-selector).
---

# Agent Tool Designer

This skill produces a tool specification set for an agent, or a review of existing tools, MCP servers or clients with prioritised fixes. It treats a tool as a public API whose caller is a model. The model only requests a call, and your code decides whether it runs. So cut tools by intent and by permission, make the contract executable, return errors the model can act on, make side effects safe to repeat, and measure tool choice instead of trusting any tool-count rule.

## When to use / when not to

Use it when someone:
- is defining the tools for a new agent, or wrapping an existing API, database or service for agents;
- shares tool definitions, function schemas or MCP server code and asks for a review;
- reports that the agent picks the wrong tool, fills bad arguments, loops, skips a required step, or repeats a side effect;
- has "too many tools" or high token cost from tool definitions;
- is building or reviewing an MCP server or MCP client (transports, auth, elicitation, statelessness, distribution);
- asks MCP vs native function calling vs a CLI vs an Agent Skill, or whether to use A2A between agents.

Hand off instead:
- Single agent vs workflow vs multi-agent, the control loop and step limits go to **agent-architect**. This skill can say "split into subagents" as a selection strategy, but the topology decision belongs there.
- Retrieval, memory and context-window budgets go to **agent-context-designer** (tool *results* that feed context are shaped here).
- A full evaluation program (datasets, judges, statistics, CI gates) goes to **agent-eval-designer**. This skill specifies only the tool-choice eval.
- Tracing, dashboards, alerting and cost monitoring in production go to **agent-ops-reviewer**.
- Prompt injection, data exfiltration, sandbox escape, OAuth threat analysis and red-teaming go to **agent-threat-modeler**. This skill applies baseline controls and flags when a deeper review is needed.
- Model shortlists go to **agent-model-selector**; whether the agent is worth building goes to **agentic-business-case**.

## Inputs to gather first

Read the code if you have it; ask only for what the code cannot tell you (three to five questions at most). Write anything still unknown into an "Assumptions" list instead of stalling. Mark an assumption **blocking** when a recommendation flips if it is wrong (for example "the refunds API honours idempotency keys"), and say what to check.

1. **Tasks.** What the agent must accomplish, written as agent stories ("the agent wants to refund one paid order"). Which steps are mandatory, and which outcomes are irreversible?
2. **Current surface.** Existing tool definitions or schemas, handler code, the API or OpenAPI spec being wrapped, MCP server or client code.
3. **Side effects.** For each operation: read, additive write, destructive write, send, spend. Is it reversible? Does the backend accept idempotency keys?
4. **Identity and permissions.** On whose behalf calls run, how the caller is authenticated, tenant boundaries, which actions need human approval.
5. **Model and runtime.** Provider and model, whether strict schema mode and forced `tool_choice` are available, the host (own loop, framework, IDE, Claude Code or Desktop, other MCP hosts), parallel calls. **Whose host is it?** If the tools run inside a host you do not control (Claude Desktop or claude.ai connectors, an IDE, a partner's agent), then `tool_choice`, strict mode, tool search, the system prompt and the task ID are not yours. Every control has to live in the server (see "Where enforcement can live" in the Decision guide).
6. **Consumers and deployment.** Only your agent, or other teams and third parties? Local or remote, single or multi-tenant? Number of servers and tools connected, and token cost of the definitions.
7. **Evidence of failure.** Transcripts or logs of wrong picks, bad arguments, retries, loops or duplicate actions.

## Procedure

1. **Frame the job and find the bug class.** Decide: design or review, tool layer, protocol layer, or both. In a review, map each symptom to where it lives before proposing fixes:

   | Symptom | Where the fix lives |
   |---|---|
   | Wrong tool, or no tool when one was needed | Tool list, names, descriptions, selection strategy |
   | Bad or hallucinated arguments | Schema, parameter descriptions, examples, validation |
   | Unsafe or unwanted action | Granularity, authorization in code, approvals (never the prompt) |
   | Misread result, wrong next step | Result shape |
   | Loops, repeated failures, duplicate side effects | Error contract, idempotency, loop limits |
   | Required step skipped | Enforcement in code or `tool_choice`, not instructions |

2. **Cut the tool set from agent stories.** Write one story per thing the agent needs to accomplish and give each story one tool that completes it end to end. Do not mirror REST endpoints one to one: keep the small endpoints as private helpers behind the tool. Then split along two more axes. Split when two intents need different required fields. Split when they need different permissions (read vs write, user vs admin, reversible vs irreversible). Consolidating related operations behind an `action` enum is fine only when every action shares the same required parameters and the same permission level. Before merging two tools that look alike, check what each returns (the handler, or a sample response). Merge only if they return the same data for the same input; if you cannot see either, flag the pair as a suspected overlap. Two kinds of tool usually disappear in this step. Sub-step lookups (status, stock, invoice link) fold into the parent tool's result. Data needed on almost every turn (the signed-in user's profile, the policy text) gets loaded into context by code instead of sitting behind a tool. Details and the arithmetic in [references/tool-design-rules.md](references/tool-design-rules.md) §1.

3. **Name and describe each tool.** Use `service_verb_object` names that are distinct from every neighbour, with a namespace prefix per service or server. Keep names to 64 characters or fewer using only letters, digits, `_` and `-`; that fits every target checked (MCP, the Claude and OpenAI APIs, the Claude connector directory; limits in current facts). Write each description for a capable new hire, in three to six sentences: what the tool does, when to use it, when not to (naming the sibling tool to use instead), what each input means with units and formats, preconditions, what it returns, side effects and limits. Put business constraints in both places: a sentence in the description so the model does not try, and a check in code so it cannot succeed. Template and examples in tool-design-rules §2.

4. **Design the input schema.** Use unambiguous parameter names (`order_id`, `amount_cents`), enums for closed sets, bounds and formats, a minimal `required` list, no `**kwargs` or free-form `options` objects, and no flags that make other fields conditionally required. Never let the model fill identity, tenant, approval or authorization fields: inject them from the runtime. Add input examples for format-sensitive or nested inputs. Turn on strict schema mode where the provider has it, but keep business-rule validation, because strict mode guarantees types, not correct values. See tool-design-rules §3.

5. **Shape the results.** Return only what the next decision needs: stable IDs plus human-readable names, structured fields plus a short text rendering, explicit units. Paginate or truncate large results by default, say so in the result, and tell the model how to get more. Offer a `response_format` of concise or detailed when results vary in size. Return a link or handle for anything large (files, exports) instead of inlining it. Treat every result as untrusted input to the model. See tool-design-rules §4.

6. **Write the error contract.** Route every failure with the error table in the Decision guide. Retry transient faults in code. Return model-fixable and business-rule failures as tool errors (`isError` / `is_error`) with one actionable sentence: what was wrong, what is allowed, what to do next. Use protocol errors only for unknown tools, malformed requests and missing client capabilities. Never return a stack trace. Never return an error as a normal success string. When a write times out, say that it may have completed and how to check before retrying. See tool-design-rules §5.

7. **Make side effects safe.** For every write, send or spend:
   - give it an idempotency key derived from the task and the operation (not the model's call ID, which changes on every reissue) and confirm the backend honours it. With no task ID (an MCP server in someone else's host), key on the business object instead. Either way, the handler's state check (remaining refundable amount, current status) is what stops a duplicate;
   - set a timeout and bounded retries with backoff;
   - require approval for irreversible, high-value or externally visible actions, enforced by the runtime or the protocol (MCP elicitation), not by a description. Set the threshold no higher than what a front-line human may do without sign-off, and start lower. Where the client cannot ask the user, degrade to propose-only: the tool records a pending action that a human approves outside the model, and it never executes;
   - carry state between calls as explicit opaque handles that are authorised on every call, with their lifetime stated in the description.

   For tools the agent cannot finish without and you do not control, name a fallback and an escalation path. See tool-design-rules §6.

8. **Set permissions.** Decide authorization in code from the caller's identity, never from the model's arguments or the prompt. Use least-privilege credentials per tool, read-only credentials for read-only agents, and start new agents on read tools first (progressive access). Filter the visible tool list by the caller's scopes. Filter by task state only where you build the list per turn (your own loop, or a host or client you control); an MCP server can filter by authorization alone. Annotations such as `readOnlyHint` or `destructiveHint` inform clients and enforce nothing. If one agent combines private data, untrusted content and an outbound channel (the lethal trifecta), or runs model-written code, flag it and hand the deep review to **agent-threat-modeler**. See tool-design-rules §7.

9. **Enforce mandatory steps outside the prompt.** If a step must happen (look up the policy before answering, check the order before refunding), call it in code before the model runs, block completion until it has happened, or force it with `tool_choice` where the model and settings support forcing. Some current models reject forced tool choice: check [references/current-facts-2026-10.md](references/current-facts-2026-10.md). A prompt line helps but is not a guarantee. In an MCP server, two of these levers are gone: the tool list cannot change with one user's task state, and the host owns `tool_choice`. Enforce in the handler instead: it checks the precondition itself and returns a tool error naming the prerequisite ("call orders_get first"). See tool-design-rules §8.

10. **Pick the selection strategy for the tool count.** Use the tool-count table in the Decision guide and [references/tool-selection-and-evals.md](references/tool-selection-and-evals.md). Start by loading everything and measuring. Move to scoping, tool search with deferred loading, code mode or subagents only when the tool-choice eval or the token bill says so. Keep tool order deterministic so prompt caching works. Without a tokenizer, estimate definition cost as the character count of the serialised tool list divided by 4. Label it an estimate, and use the provider's token-counting endpoint when you can.

11. **Choose the integration and protocol.** Use the protocol table in the Decision guide. If MCP: pick primitives by who should decide when they are used (model → tool, application → resource, user → prompt). Use stateless Streamable HTTP with OAuth for anything remote or shared and stdio for local developer tooling. Use elicitation for confirmations, and form mode only for non-sensitive input. Long jobs use the Tasks extension or a start/status tool pair. On the client side: namespace tools per server, get consent for definitions and re-ask when the list changes, dedupe retried writes, and pin local servers. Full checklists for server and client in [references/mcp-and-protocols.md](references/mcp-and-protocols.md); version-specific names and dates in [references/current-facts-2026-10.md](references/current-facts-2026-10.md).

12. **Specify the tool-choice eval.** Every design ships with one. It needs prompts per tool, prompts for confusable pairs, and cases where the right move is to ask, call no tool or decline. Run each case several times with the tool order shuffled, and score per-tool precision and recall, argument validity, calls per task and definition tokens. Re-run it whenever a tool, description, server or model changes. Hand the wider eval program to **agent-eval-designer**. See [references/tool-selection-and-evals.md](references/tool-selection-and-evals.md) §4.

13. **Write the output** in the shape below and check it against the Quality bar.

**Review mode.** Do step 1 first, then walk steps 2 to 12 as a checklist against what exists. Report each finding with its location (tool name, file and line), the evidence, the fix, and a rewritten definition for the worst offenders. Prioritise by consequence:
- **P0:** can cause a wrong irreversible action, a duplicate charge or send, cross-tenant access, or a security exposure (including a lethal-trifecta tool combination, or free-form SQL, shell or code reachable from untrusted input);
- **P1:** causes measurable wrong tool choice, bad arguments, loops or task failure;
- **P2:** token cost, latency or maintainability;
- **P3:** polish.

No logs or transcripts? Review from the definitions and code, mark such findings "inferred", and for each suspected failure name the log line or eval case that would confirm it.

**Fast path (five tools or fewer).** Run step 1; steps 2 to 6 as one pass over each definition; steps 7 and 8 for write, send and spend tools only; step 12 with two or three cases per tool. Skip step 10. Do step 11 only if a protocol is in question. Use the same output shape.

## Decision guide

**Granularity**

| Situation | Do | Why | Watch out for |
|---|---|---|---|
| Wrapping a REST API with many small endpoints | One tool per agent story; endpoints become private helpers | Each extra call compounds error and re-sends context | Generators that emit one tool per endpoint |
| Related operations with identical parameters and permissions | One tool with an `action` enum | Fewer near-duplicate choices | Drifting into actions that need different fields |
| One tool reads and writes, or mixes user and admin power | Split by permission | Approval and authorization attach per tool | "manage_x" tools with a mode flag |
| `action` decides which other fields are required | Split into separate tools | The schema can then state what is required | Smaller models fail on many-parameter tools |
| Free-form power (raw SQL, shell, arbitrary HTTP) | Narrow named operations; staff-only query tools follow tool-design-rules §7 | A broad tool eventually does the broad thing | Relying on the prompt to keep it safe |

**Error routing**

| Failure | Route | Message to model |
|---|---|---|
| Transient (timeout on a read, 429, 503) | Retry in code with backoff and a cap; the model never sees it unless retries run out | After cap: "Service X unavailable; try later or use Y" |
| Bad argument the model can fix (format, range, unknown name) | Tool error | Field, what is allowed, an example of a valid value |
| Business rule blocks it (not refundable, over limit, outside hours) | Tool error | The rule, the current state, the next step (often "tell the user") |
| Needs a human (approval, missing secret, payment) | Elicitation or escalation, not a tool error | n/a |
| Write timed out, outcome unknown | Tool error | "May have completed; call `x_get_status` before retrying" |
| Unknown tool, malformed request, missing client capability | Protocol error to the client | n/a |
| Bug or unhandled exception | Generic error to model, full trace to logs | "Internal error in tool X" |

**Tool count and selection** (defaults; confirm with the tool-choice eval)

| Situation | Strategy | Watch out for |
|---|---|---|
| Up to about 15-20 distinct tools, definitions under about 10k tokens | Load all, deterministic order | Overlapping descriptions matter more than count |
| More tools, but the task state or role tells you which apply | Static scoping per state, role or scope | Scoping out a tool needed at a later step |
| Dozens to thousands of tools, many servers, or definitions over about 10k tokens | Tool search with deferred loading; keep the 3-5 most-used tools always loaded | The prompt must tell the model to search before giving up |
| Many similar tools in groups | Hierarchical: pick a group, then a tool | Extra sequential model calls |
| Loops, filtering, aggregation, many calls per task | Code mode in a deny-by-default sandbox | Needs a real sandbox, no credentials inside, per-call gate |
| Tool groups with different data access, permissions or success criteria | Subagents exposed as tools (decide with agent-architect) | Coordination overhead; try scoping and search first |

**Where enforcement can live**

| Control | Your own agent loop | MCP server in a host you do not control |
|---|---|---|
| Mandatory step | Code before the turn, completion gate, tool exposure by state, forced `tool_choice` if the model allows | Handler checks the precondition and returns a tool error naming the prerequisite |
| Which tools are visible | Filter per turn by role, scope or task state | The list may vary by the caller's authorization (scopes), never by task state or connection |
| Schema guarantee | Strict mode where offered, plus validation | Server-side validation only |
| Approval | A runtime step the model cannot skip | Elicitation where the client supports it; otherwise propose-only. Host prompts driven by `destructiveHint` help but are the user's setting, not your control |
| Duplicate side effects | Key from task ID and operation | Key from the business object, plus a state check |
| Tool count and token cost | Scoping, tool search, code mode | Keep the server small; the host decides how it loads tools |
| Result size and timeout | Your choice | The host's caps (current facts) |

**Integration choice**

| Situation | Choose | Why |
|---|---|---|
| Tools used only by your own agent, one codebase | Native function calling | No protocol overhead; MCP adds nothing here |
| Capability reused by several hosts or teams, needs per-user auth, or must run off the agent's machine | MCP server (remote, Streamable HTTP, OAuth) | Write once, any MCP host can use it |
| Local developer tooling, files on the user's machine | MCP over stdio | Lowest latency; trust comes from the local process |
| One developer, has a shell, the tool is a well-known CLI (`gh`, `kubectl`) | Let the agent run the CLI | Already in training data, cheapest in tokens |
| The gap is know-how (a workflow over existing tools), not access | Agent Skill (optionally shipped beside an MCP server) | Loaded on demand; brings no service or auth |
| The counterpart is an agent owned by another team or company, and you want an outcome | A2A | Delegates a whole task to an opaque agent |
| Both agents are yours, in one process | Function call or subagent, not A2A | An A2A hop adds latency without isolation |

## Output

**Tool specification set** (design). Fill [templates/tool-spec.md](templates/tool-spec.md). Start with a five-line summary: number of tools and why that cut, the protocol and transport, the selection strategy, the riskiest tool and its control, and what to build first. Then give:
- the inventory table;
- one spec block per tool (definition JSON, description, parameters, result, errors, side effects, authorization, approval, timeouts);
- mandatory-step enforcement;
- the protocol section (if MCP: primitives, transport, auth, client obligations);
- the tool-choice eval;
- assumptions and hand-offs.

**Review** (existing tools or servers). Fill [templates/tool-review.md](templates/tool-review.md). It holds the same five-line summary and a verdict line, then findings ordered P0 to P3, each with location, evidence, impact and fix. After the findings come rewritten definitions for the worst two or three tools, what is already fine, the eval that will confirm the fixes, and hand-offs.

**Both at once.** A review that also asks a design question (a protocol choice, a new integration, a re-cut tool set) uses the review template, filling its "Re-cut tool set and integration" section to this depth:
- an inventory row for every tool in the new set;
- a full spec block (from the spec template) for every write, send, spend or destructive tool;
- the definition JSON alone for read tools;
- one shared error-contract table;
- the protocol section if a protocol was asked about.

**Schema key spelling.** Use the target's own key in definitions: `inputSchema` for MCP (wire format; SDKs usually infer it from type hints), `input_schema` for the Claude API, `parameters` for OpenAI. Say which target the JSON is for.

Keep both concrete: use the user's tool names, fields and failure cases. Small fresh code is welcome where it encodes a pattern (a validation gate, an idempotency key, an MCP handler). Never paste large framework boilerplate.

## Quality bar

Before returning, check that the output:
- [ ] ties every tool to an agent story, with no tool that simply mirrors an endpoint;
- [ ] has no tool mixing read and write, or two permission levels, and no `action` flag that changes required fields;
- [ ] gives every tool a namespaced name that is distinct from its neighbours and uses portable characters;
- [ ] gives every description purpose, when to use, when not to use (with the sibling named), inputs with units and formats, return shape and side effects;
- [ ] uses typed parameters with enums, bounds and formats, no catch-all objects, and no identity or approval fields for the model to fill;
- [ ] validates every call against the schema and then against business rules before execution;
- [ ] decides authorization in code from the caller's identity;
- [ ] routes every error class per the table, with one-sentence actionable messages and no stack traces;
- [ ] gives every side-effecting tool an idempotency key honoured by the backend (or a business-object key plus a state check), a timeout, and a "may have completed" message on timeout;
- [ ] gates irreversible or high-value actions behind runtime-enforced approval, with a stated threshold and a propose-only fallback where the client cannot ask the user;
- [ ] for tools served into a host you do not control, puts every control in the server and relies on no host feature it has not verified;
- [ ] enforces mandatory steps in code or with forced tool choice that the model supports;
- [ ] keeps results size-bounded, with names alongside IDs and pagination or links for large data;
- [ ] states the selection strategy with the tool count and definition token cost, in deterministic order;
- [ ] justifies the protocol choice; for MCP, checks transport, auth, statelessness, elicitation and client trust obligations against the current spec;
- [ ] includes a tool-choice eval with confusable pairs, ask, no-tool and decline cases, shuffled order and re-run triggers;
- [ ] puts version-specific claims (spec revision, SDK names, provider limits) with an "as of" date and lists the assumptions;
- [ ] hands deep security and the full eval program to the sibling skills when they are triggered.

## Common mistakes

| Mistake | Fix |
|---|---|
| Generating one tool per REST endpoint from an OpenAPI spec | Use the spec for types and validation; design the tool surface from agent stories |
| Quoting a universal tool limit ("max 6", "under 10", "20") as fact | The ceiling depends on the model and on description overlap; measure with a tool-choice eval |
| Recommending embedding-based tool retrieval for a dozen tools | Load all and measure; at scale prefer tool search, which can search again mid-task |
| "ALWAYS call X" in the system prompt as the guarantee | Call it in code, gate completion, or force it where supported |
| Putting `user_id`, `tenant_id`, `approved` or `is_admin` in the schema | Inject identity and approval from the runtime; the model never fills them |
| Returning "Error: ..." as a normal result string | Mark it as an error (`isError` / `is_error`) so the client and model treat it as one |
| Raising a protocol error for a business-rule failure | Tool error with the rule and the next step; protocol errors are for malformed or unknown requests |
| Raising a plain exception in MCP Python SDK v2 and expecting the model to read it | Raise `ToolError`; other exceptions reach the model as a generic error (see current facts) |
| Retrying writes after a timeout without a key | Idempotency key from task and operation; timeout message says "may have completed" |
| Trusting `destructiveHint` or `readOnlyHint` as a control | Annotations are hints from a possibly untrusted server; enforce in code and in the client |
| Designing MCP with sessions, `initialize`, `ping` or SSE resumption | 2026-07-28 MCP is stateless: explicit handles, retry instead of resume |
| Using sampling or roots in a new server, or WebSocket for a server others will install | Call the model provider directly; take paths as arguments; Streamable HTTP or stdio (WebSocket is non-standard, accepted only by some hosts) |
| Assuming `tool_choice`, strict mode or tool search for an MCP server used in Claude Desktop or an IDE | The host owns those; enforce in the handler |
| Planning to show or hide MCP tools by task state | Lists may vary by authorization only; gate in the handler, use scopes for tiers |
| Keying idempotency on a task ID the server never receives | Business-object key plus a remaining-amount or status check |
| A destructive tool that only works when the client supports elicitation | Fail closed and offer a propose-only path that a human approves outside the model |
| Forwarding the user's token to a downstream API | The server gets its own downstream credentials; accept only tokens issued for it |
| Using A2A between two of your own in-process agents | Function call or subagent; A2A is for opaque agents across team or org lines |
| Proposing a Skill when the gap is access or auth | Skills carry know-how; access needs a tool, CLI or server |
| Dots, spaces or long tool names | Up to 64 characters, letters, digits, `_`, `-`; MCP allows dots and 128 characters, but Claude's API rejects dots and OpenAI's caps names at 64 |
| Copying v1-era MCP code (`FastMCP`, `ClientSession` with `initialize()`) | Port to SDK v2 names or pin `mcp<2`; see current facts |
| A tool-choice eval of only easy, fully specified prompts | Add confusable pairs plus ask, no-tool and decline cases; shuffle order; repeat runs |

## Sources

Distilled from a cross-book study guide (tool use and tool design; MCP and agent protocols). Book chapters by key:
- MCP: *AI Agents with MCP* (Kyle Stratis), ch1, ch2, ch3, ch4, ch5, ch6, ch7, ch8, ch9: tool design, the REST antipattern, error rule, client trust boundary, transports, OAuth, security taxonomy, evaluations, registry and extensions. Written against MCP 2026-07-28 and Python SDK 2.0.
- SYSTEMS: *Systems Thinking for Agentic AI*, ch4, ch7, ch18: the model requests and the runtime executes, system-level enforcement, the tool registry.
- BUILDAPPS: *Building Applications with AI Agents*, ch4, ch5, ch8: narrow stateful tools, validate-retry-fallback, selection strategies.
- AGENTICAI: *Agentic Artificial Intelligence*, ch5: five-part tool specification, Tool Resilience Framework, Progressive Tool Access.
- BUILDAGENTIC: *Building Agentic AI*, ch1, ch4, ch5, ch6: tool-selection measurements, position bias, code as action; plus its companion tool-selection notebooks.
- DEFGUIDE: *AI Agents: The Definitive Guide*, ch5, ch6: typed contracts, bounded re-asks, programmatic tool calling in a deny-by-default interpreter, A2A governance plane.
- ILLUSTRATED: *An Illustrated Guide to AI Agents*, ch5, ch8: tool lifecycle, native vs prompted calling, Skills, A2A.
- ENTERPRISE: *The Agentic Enterprise*, ch1, ch5, ch6, ch8; MESH: *Agentic Mesh*, ch4, ch6, ch12; DLLMA: *Designing Large Language Model Applications*, ch10.

External (checked 2026-10):
- MCP specification 2026-07-28: tools https://modelcontextprotocol.io/specification/2026-07-28/server/tools, changelog https://modelcontextprotocol.io/specification/2026-07-28/changelog, authorization https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization
- MCP Python SDK v2: https://py.sdk.modelcontextprotocol.io/whats-new/, https://py.sdk.modelcontextprotocol.io/servers/handling-errors/, https://py.sdk.modelcontextprotocol.io/handlers/elicitation/
- Claude as an MCP host: https://claude.com/docs/connectors/building, https://claude.com/docs/connectors/building/review-criteria, https://code.claude.com/docs/en/mcp
- OpenAI function calling: https://developers.openai.com/api/docs/guides/function-calling
- Anthropic, "Writing effective tools for agents" (2025-09): https://www.anthropic.com/engineering/writing-tools-for-agents
- Anthropic, "Advanced tool use" (2025-11): https://www.anthropic.com/engineering/advanced-tool-use
- Claude docs, define tools and tool search tool: https://platform.claude.com/docs/en/agents-and-tools/tool-use/define-tools, https://platform.claude.com/docs/en/agents-and-tools/tool-use/tool-search-tool
- A2A specification v1.0: https://a2a-protocol.org/latest/specification/
- Agent Skills specification: https://agentskills.io/specification
- Wang et al., "Executable Code Actions Elicit Better LLM Agents" (CodeAct, 2024): https://arxiv.org/abs/2402.01030
