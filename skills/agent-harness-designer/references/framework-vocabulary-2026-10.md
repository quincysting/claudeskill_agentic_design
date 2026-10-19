# Framework vocabulary (as of 2026-10)

Citation keys such as [AISEC ch4] point to the book list under Sources in SKILL.md.

Dated facts, kept out of the vendor-neutral procedure. Read from the vendors' documentation on 2026-10-18, and the LangGraph limit and cancel cells on 2026-10-19 (pages listed at the end). Names, defaults and options change between releases: check the current documentation before relying on any cell. A cell that says "not on the fetched pages" was not confirmed either way.

## Generic part to framework term

| Generic part (this skill) | LangGraph | Claude Agent SDK | OpenAI Agents SDK |
|---|---|---|---|
| Who owns the loop | You define the graph: state, nodes, edges [AISEC ch4 §Using LangGraph Agent Workflows] | The SDK runs it: prompt, tool calls, results, repeat | `Runner.run`, `run_sync`, `run_streamed` |
| Run identity | `thread_id` in the config | `session_id` on the result | A session, or a resumable `RunState` |
| Durable state | Checkpointer: `InMemorySaver` loses everything on restart; Postgres for production, SQLite for development | Sessions that can be resumed and forked; a `session_store` adapter for stateless hosts | Client-side sessions or server-side conversation IDs |
| Pause for a person | `interrupt()`, then `Command(resume=...)` on the same thread; the node reruns from its start | Permission modes, a `canUseTool` callback, `PreToolUse` hooks | Approval interruptions, resumed from `RunState` |
| Caps and forced exits | `recursion_limit` counts super-steps (a super-step is one pass over the nodes active together) and raises `GraphRecursionError`. Its default was 25 up to 1.0.5, 10,000 from 1.0.6 and 10,007 from 1.2.0, and an environment variable, `LANGGRAPH_DEFAULT_RECURSION_LIMIT`, overrides it (read from the published wheels, 2026-10-19; check `langgraph/_internal/_config.py` for your version); it is a top-level config key, not inside `configurable`; a `RemainingSteps` value lets a node finish early before the limit | `max_turns`, `max_budget_usd`; results `error_max_turns`, `error_max_budget_usd` | `max_turns` raises `MaxTurnsExceeded` unless an error handler supplies a fallback |
| Draft-only analogue | Your own flag | `permission_mode="plan"` (explore and plan, no edits) | Your own flag |
| Replay and fork | Replay re-executes every node after the chosen checkpoint, model and tool calls included; `update_state` forks | Fork a session | Not on the fetched pages |
| Cancel | No cancel call on the fetched pages. `RunControl.request_drain(reason)` (langgraph 1.2 or later) stops at the next super-step boundary, lets a running node finish, saves a resumable checkpoint and raises `GraphDrained`; a per-node `TimeoutPolicy` (`run_timeout`, `idle_timeout`; async nodes only) cancels one attempt with `NodeTimeoutError` and discards its writes | A cancelled request ends as `error_during_execution` | `cancel(mode="after_turn")` leaves a resumable `RunState` |

What still belongs to you in all three: the run record header, budget counters in checkpointed state, the approval digest and expiry, the kill switch levels, the disconnect policy and the harness tests. Map each row of harness-components.md §1 to "framework does it", "framework helps", or "we build it" before you adopt one.

## Where the guard runs

The guard (cancel, kill flags, budgets) must run before every model and tool call. Where each kind of framework lets you put it, as of 2026-10; confirm every point against the installed version:
- **Agent factories with middleware or hooks.** LangChain's `create_agent` takes middleware: `before_model` runs before every model call and can end the run by returning `jump_to` set to `"end"` (the hook declares that target with `@hook_config(can_jump_to=...)`); `wrap_model_call` and `wrap_tool_call` wrap every model and tool call and can decline to call the handler, which skips the call. Put the guard there, not in a node or a prompt. Whether a skipped tool call must return a `ToolMessage` in your version was not on the page read (2026-10-20).
- **A graph you write.** A guard node, or a check at the top of every node that calls a model or a tool, with the counters in graph state.
- **Claude Agent SDK.** A `PreToolUse` hook can deny a tool call before it runs, so tool-call budgets, kill flags and cancel are checked per tool call. Model calls and spend are compared with `max_turns` and `max_budget_usd` after each response (as of 2026-10, `max_turns` 0 means no turn limit and `max_budget_usd` 0 is rejected at start-up; confirm against the installed version) (control-loop.md, "Where budgets bite").
- **OpenAI Agents SDK.** Not on the fetched pages; check its hooks and guardrails for a refusal before each call before relying on one.

## Defaults to watch

- Both SDKs leave turn and budget caps unset unless you set them. Set them explicitly and test the forced exit.
- LangGraph's default recursion limit (10,000 or 10,007 super-steps in current releases, 25 before 1.0.6) is far above the loop budgets in control-loop.md, so the default never acts as a budget. Set `recursion_limit` explicitly as a backstop above your own pre-call step guard, and map `GraphRecursionError` to `partial` with `max_steps` (harness-tests.md §4).
- A LangGraph drain is a pause with a checkpoint, not a cancel. To cancel, write the cancel signal into run state first, so the drained run ends `cancelled` instead of being resumed by the next worker; use the drain alone for shutdown, so another worker resumes the run.
- The Claude Agent SDK compares spend with its cap after each response, so a run can overshoot by one response plus what running subagents spend before they stop; its documentation says to leave headroom. Set the cap one maximum call below the real limit.
- LangGraph's in-memory checkpointer is the one tutorials use. In a multi-worker service it means lost state and cross-worker misses.
- On resume after `interrupt()`, LangGraph restarts the whole node, so code before the interrupt runs again; never put a side effect in the same node as the interrupt [DEFGUIDE ch2 §Designing Human-in-the-Loop Workflows].
- Framework replay is an experiment, not a reproduction (harness-components.md §5).

## MCP cancellation changed with the 2026-07-28 revision

Before it, a client cancels with a `notifications/cancelled` message carrying the request ID [MCP ch6 §Request Cancellation]. In the 2026-07-28 revision (checked 2026-10-19), how a client cancels depends on the transport: over Streamable HTTP, closing the request's response stream is the cancellation and the server must treat a disconnect as one, with no notification; over stdio the client still sends `notifications/cancelled` with the request ID. Either way the tool may see cancellation only as its own handler being cancelled. Catch cancellation in the tool itself and clean up in `finally`.

## Durable workflow engines

Temporal persists progress so a crashed run resumes at its last completed activity; workflow code must be deterministic, so model and tool calls go in activities [BUILDAPPS ch8 §Orchestration and Workflow Engines]. AWS Step Functions and Lambda durable functions: aws-implementation-notes.md.

## Provider-swap layers

A library that offers one interface over several providers is not neutral. As of aisuite 0.2.0 (2026-09), its Anthropic adapter injects a default `max_tokens` and maps unknown stop reasons, a refusal among them, onto an ordinary stop [RELATED repo: aisuite/aisuite/providers/anthropic_provider.py]. Log the effective request parameters and the native stop reason, whatever library you use.

## The framework exit test

Before adopting a framework, answer yes to all five, or write down the gap:
1. Can you see the exact prompt sent on every call?
2. Can you see every state transition, and where state is stored?
3. Can you set every budget, and does a forced stop end with a status you can tell from success?
4. Can you swap the model provider without rewriting the loop? Prototype against more than one provider, so switching stays cheap [NG What Comes After Tokenmaxxing?, 2026-08-07].
5. Can you replace any one component (store, tool layer, tracing) without replacing the framework?

A harness can also refuse work outright: when two commercial coding harnesses declined a security review of his team's own open-source project, Ng's team finished it with an open harness and open-weight models [NG Open Models, Open Harnesses, Open Security, 2026-07-31]. Keep an alternative path for work the default harness may refuse.

## Book snapshots

The LangGraph code in DEFGUIDE and BUILDAGENTIC and the framework list in [BUILDAPPS ch1 §Agentic Frameworks] predate most current persistence and approval APIs; the ideas carry over, the names may not. KGRAG argues that frameworks share components and that the model's capabilities "most condition the result" [KGRAG ch4 §Choosing an LLM agent framework]; the only controlled evidence so far, one single-author preprint (harness-tests.md §5), found the harness changed cost per solved task and changed quality only on some task families, so test on your tasks rather than assume.

## Pages read (2026-10-18)

- LangGraph persistence: https://docs.langchain.com/oss/python/langgraph/persistence
- LangGraph time travel: https://docs.langchain.com/oss/python/langgraph/use-time-travel
- LangGraph interrupts: https://docs.langchain.com/oss/python/langgraph/interrupts
- LangGraph graph API, "Recursion limit" (2026-10-19): https://docs.langchain.com/oss/python/langgraph/graph-api
- LangGraph fault tolerance, "Graceful shutdown" and "Timeouts" (2026-10-19): https://docs.langchain.com/oss/python/langgraph/fault-tolerance
- LangGraph recursion-limit default per release, `langgraph/_internal/_config.py` in the published wheels (2026-10-19): https://pypi.org/project/langgraph/
- MCP 2026-07-28, cancellation (2026-10-19): https://modelcontextprotocol.io/specification/2026-07-28/basic/utilities/cancellation
- Claude Agent SDK, agent loop: https://code.claude.com/docs/en/agent-sdk/agent-loop
- OpenAI Agents SDK, running agents: https://openai.github.io/openai-agents-python/running_agents/
- LangChain custom middleware (2026-10-20): https://docs.langchain.com/oss/python/langchain/middleware/custom
