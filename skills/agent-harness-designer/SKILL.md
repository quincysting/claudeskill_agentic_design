---
name: agent-harness-designer
description: Design or review the runtime (harness) of a production AI agent, returning a design doc or review findings. Covers the agent loop, run record and state, checkpointing and resume, budgets checked before every call, stop rules, approvals bound to the exact action, cancellation, kill switch and draft-only mode, safe-mode replay, streaming, serving the agent as an API, deployment shape, framework vs own loop (LangGraph, Claude Agent SDK, OpenAI Agents SDK) and harness tests. Use for "design the agent runtime", "review my agent harness", "checkpointing and resume", "kill switch", "streaming and cancellation", "serve my agent as an API", "LangGraph or our own loop", "test the harness". Unlike generic harness-construction skills for coding assistants, it designs and reviews the runtime of one production agent. Hands off architecture shape to agent-architect, tool contracts to agent-tool-designer, security controls to agent-threat-modeler, eval plans to agent-eval-designer, readiness review to agent-ops-reviewer.
---
# Agent Harness Designer

Produces a harness design, or a review of an existing harness, for one agent: the code around the model that runs the loop, records every run, survives restarts and human waits, enforces limits before every call, serves its callers, and lets an operator stop it. The stance: reliability lives in the runtime, not the prompt; the run record is the spine everything else reads; every limit and switch is harness state checked in code at every call; a tutorial loop is a starting point, not a service.

**Perspective owned:** Harness (at every stage). The agent's own service endpoint is designed here under the API-contracts perspective, whose owner is agent-tool-designer: this skill applies that skill's contract rules to the endpoint. **Stage:** Build, returning at Prove for the harness tests. The end-to-end map of stages, perspectives, owners and gates is agent-architect's lifecycle map; start there when the work spans more than the runtime.

## When to use / when not to

Use when:
- An agent's shape is decided (or the agent exists) and someone must build or choose its runtime: framework or own loop, state store, checkpoints, resume after a crash or a human wait.
- Someone reports runs that never stop, budgets that do not hold, duplicate side effects after a retry or restart, an approved action that ran with different arguments, no way to stop the agent quickly, or streams that break on disconnect.
- An agent must be served: an API for it, long runs behind HTTP, webhooks and queues, scheduled runs, serverless limits.
- A harness needs review before production, or harness tests need writing.

Hand off by name; do not design these in depth here:

| Concern | Skill |
|---|---|
| Whether each step is code, workflow or agent; patterns; single vs multi-agent; authority per step; the lifecycle map | agent-architect |
| Tool names, schemas, descriptions; idempotency, receipts and reversibility at the tool; error categories; tool versioning; MCP servers | agent-tool-designer |
| What goes into each model call: retrieval, memory, compaction | agent-context-designer |
| Threats, permission tiers per action, who approves and what they see, guardrail content, sandboxing | agent-threat-modeler |
| Eval suites, scorers, statistics (this skill supplies the harness test slice and the run-record contract) | agent-eval-designer |
| Tracing backend, dashboards, alerts, cost tuning, the production readiness gate, rollout | agent-ops-reviewer |
| Model per role; the bake-off protocol | agent-model-selector |
| Configuring a coding assistant's own harness (hooks, settings, project instructions) | not this skill |

## Inputs to gather first

Read the user's code and docs before asking. Ask only for facts that change a decision; assume and label the rest.

1. **The agent's shape and loop contract:** steps, which are agent loops, tools with risk tiers, budgets, exits. An agent-architect design doc, if there is one.
2. **Trigger and caller:** an interactive user, an API client, a webhook or business event, a schedule. Who waits for the result, and how long.
3. **Run length:** typical and worst-case duration, human waits (minutes or days), the longest tool call.
4. **Side effects:** every write; reversible or not; does the backend accept an idempotency key or offer a lookup by key or by target.
5. **Hosting:** framework already in use, host type and its time limits, available stores, number of workers or replicas.
6. **Load:** runs per day, peak arrivals, concurrent streams per client.
7. **Operations:** who must be able to stop it and how fast; audit and retention rules for run data.
8. **Review mode:** loop code; framework config (checkpointer, interrupts, caps); server and handler code; state store code; 3 to 5 run traces, one of them a failure or a restart; incident notes.

If item 2, 4 or 5 is unknown and cannot be inferred, ask at most three questions in one message. Otherwise proceed and list the assumptions.

On AWS, map each decision with [references/aws-implementation-notes.md](references/aws-implementation-notes.md). If the cloud is unknown or not AWS, skip that file and say so.

## Procedure

Design mode runs steps 1 to 10. Review mode runs step R first, then steps 1 to 10 for the target design.

**R. Review the as-is harness.** Map what actually runs, from code and traces, not docs: where the loop lives, where state is stored (process memory, a file, a shared store), where each limit is checked (before each call, once per turn, never), what each exit returns, what a restart does. Run the audit checklist and the tutorial-harness table in `references/harness-components.md`. Record each finding with severity, evidence (file:line, config key, run ID), fix, and the test that would have caught it. For each reported incident (a duplicate email, a runaway run), name the structural cause and say how to confirm it from the logs. When only a description is supplied (no code, config or traces), label each finding's evidence as stated, inferred or confirmed, and carry every inferred finding into "Confirm first" or the risks.

1. **Frame the runtime.** Write the agent's responsibility sentence (from the architecture if it exists), the trigger, the caller, the run class (interactive seconds, job minutes, long-running with waits) and the side-effect inventory: each write, its reversibility, its target (the business object a key is built from) and whether the backend dedupes or can be queried. If no one has decided an action's authority (an irreversible message with no approval rule, say), flag it for agent-architect and agent-threat-modeler and give each tool a tier flag so the harness supports either answer.

2. **Choose framework or own loop.** Use the decision guide below. Apply the exit test: you can see the exact prompt on every call and every state transition, set every budget, tell a forced stop from success, swap the model provider, and replace any component. List what the framework owns and what you still build; in the three frameworks this skill maps, the run record header, budget counters in state, approval binding, kill switch levels, disconnect policy and harness tests are yours. Vendor terms and defaults: `references/framework-vocabulary-2026-10.md`.

3. **Write or adopt the loop contract.** If agent-architect set it, adopt its numbers and add the runtime parts; otherwise write the decision contract, the gate order, risk tiers, stop conditions, failure classes and exit statuses, including `cancelled`. Detail and a tested loop skeleton: `references/control-loop.md`.

4. **Design the run record and state.** Run IDs are issued by the server per principal, or derived from the event's source and ID; never defaulted. The record is append-only: a header (agent, prompt, policy, tool-schema and model versions, permission tier, input reference, limits) and typed events. Derive the typed state the gate reads (status, counters, pending approval, last event number). Store it where every worker can read it; one writer per run or conditional writes; a schema version on every checkpoint; retention and redaction per field. `references/harness-components.md` §2 and control-loop.md, "State and checkpoints".

5. **Make side effects safe.** Save the intent before every side effect and the receipt after. Key each write from run state (run, action, target, or the business key). On a timeout, look the key up; if nothing is found, retry at most once with the same key; if the outcome is still unknown, end `escalated` with reason `outcome_unknown`. A backend with neither a key nor a lookup gets no automatic retry for that write; list it under "Confirm first" (control-loop.md, failure table). On resume, an intent without a receipt means look up, then record or execute; never ask the model again. Pause for approval in one step and execute in the next; bind the approval to a digest of the exact action and arguments, an expiry and a nonce, and have the executor recompute it. Put irreversible steps last. In a durable engine, one side effect per activity.

6. **Set budgets where they bite.** For each budget: a number, a basis, checked before every model and tool call, counters in checkpointed state, the clock paused during human waits, shared across delegated work, a warning at about 80% and a stop at 100%, the hard cap one maximum call below the real limit. A forced stop ends `partial` with the reason, never `completed`. control-loop.md, "Where budgets bite".

7. **Add the operator controls.** Cancel: a signal in run state, checked at safe points, delivered to long tools, ending `cancelled`. Kill switch, two levels: draft-only (routine; execution off, planning and previews on; a flag read at every call, no redeploy) and abort (incident; revoke credentials, cancel queued and running work, deny new calls, snapshot the audit trail, restart only with a person's approval). Safe-mode replay on the same mechanism; say whether a replay is an experiment (fresh model calls) or a reproduction (recorded outputs). Name the triggers for each level and a drill schedule. `references/harness-components.md` §4 and §5.

8. **Serve and deploy.** Pick the deployment shape by trigger (table below). Design the agent's own endpoint: create a run with an idempotency key (202 Accepted for long work), a status resource, an event stream from the record with resume by last event ID, cancel, and an approval decision call; validated request schemas, problem-details errors, per-principal access checks, per-client limits. Keep three layers (API, workers, model server or provider) and no blocking work on the request event loop. Set the disconnect policy per run type and finish output checks before text is released. Plan shutdown and drain. `references/serving-and-deployment.md`.

9. **Plan the harness tests.** Pick the rows of the test table that apply, with a scripted model and an out-of-process store, and give agent-eval-designer the run-record contract and the fixed stop-reason list. If the choice is between harnesses, plan a bake-off with the model held fixed (pass rate by task family and cost per solved task, as agent-model-selector defines it) with agent-model-selector. `references/harness-tests.md`.

10. **Write and check.** Fill `templates/harness-design.md`. Put the 3 to 5 assumptions that most change the design in a "Confirm first" block after the summary. Run the audit checklist in `references/harness-components.md` against your own draft, then the Quality bar; fix and re-run before returning.

## Decision guide

### Framework or own loop

| Situation | Pick | Why | Watch out for |
|---|---|---|---|
| A graph of steps with human pauses; checkpoints and forks wanted | Graph framework with a durable checkpointer shared by all workers | Persistence and interrupts come built in | The in-memory checkpointer tutorials use; the paused step reruns from its start on resume; caps you never set |
| The vendor's agent loop is the product (coding, files, shell) | Vendor agent SDK | Loop, tool execution, compaction and permission modes come built in | Turn and budget caps unset by default; budget checked after each response, so it overshoots; the run record is still yours |
| Few steps, strict audit, high-impact actions, every transition must be visible | Own loop over the provider SDK, with a real store | Every prompt, transition and limit is code you read | Re-inventing persistence badly; use a database, not a file |
| Long runs, waits of hours or days, flaky dependencies | Durable workflow engine, model and tool calls in activities or steps | Resumes at the last completed step | Determinism rules; an activity wrapping several side effects repeats them all on retry |
| You cannot say what the framework owns | Do not adopt it yet | Lock-in without understanding | Write the exit-test answers first |

Keep provider swaps cheap whichever you pick: prototype against more than one provider, log effective request parameters and the provider's native stop reason, and rerun the full suite after any swap.

### Deployment shape by trigger

| Trigger | Shape | Must have | Breaks when |
|---|---|---|---|
| A caller waits; work fits the request timeout | Single service | Run ID and header at entry; draft and execute as distinct states; on approval, load by run ID and check the payload against the stored preview | Work regularly outlasts the timeout: switch to a job |
| A caller starts work longer than a few seconds | 202 Accepted + status resource + event stream | Run ID, status, refresh interval, numbered events | Clients poll with no refresh hint, or hold a request open |
| Webhook or business event | Receiver + queue + workers | Receiver verifies, validates, maps the event to an allowed workflow, derives the run ID from source and event ID, enqueues, acknowledges; never calls the model; dead-letter path | The loop runs in the handler: the sender retries and the work runs twice |
| A clock | Scheduled run | A run packet per run as the review surface; incremental by default with periodic full reconciliation | Drift nobody reviews |
| Long work while a user watches or steers | Foreground + background agents | Background worker on the run record; a foreground agent that informs the user and routes feedback | Both write the same state |

### Streaming and disconnect policy

| Run type | Transport | On disconnect |
|---|---|---|
| Interactive turn | SSE | Cancel; record `cancelled` |
| Client talks back mid-stream | WebSocket | Cancel or pause, by product decision; record it |
| Background job with a watcher | SSE from the record | Keep running; reconnect with the last event ID resends the gap |
| Nobody watching | Status resource only | Not applicable |
| Output must pass a check first | Buffer, or check each window before release | Same as its run type |

### Where each limit is enforced

| Limit | Checked | Lives in | On hit |
|---|---|---|---|
| Model calls, tool calls, steps | Before every call | Run state | `partial`, with `max_steps` or `budget:<name>` |
| Tokens and cost | Before every call against what remains; updated after each response | Run state | Warn at about 80%, stop at 100% |
| Wall time | Before every call; paused during human waits | Run state (active time) | `partial` |
| Retries | Per failure class | Run state | `escalated`, `retries_exhausted` |
| Delegated work | The parent's budget is passed down; a handoff cannot reset it | Parent run state | As above |
| Approval lifetime | By the executor, immediately before the call | Approval record | Expired: nothing runs; a new approval |
| Kill flags and cancel | Before every call | Flag store and run state | `cancelled` |

Budget numbers themselves (steps, re-asks, review rounds) start from agent-architect's budget table and are resized from eval worst cases.

### Kill switch levels

| Level | Stops | Keeps | Restart |
|---|---|---|---|
| Cancel (one run) | That run, at the next safe point | Its record | A new run |
| Draft-only (routine) | Every side-effecting call; previews recorded instead | Reads, planning, drafting | Flip back once the cause is understood |
| Abort (incident) | Everything: credentials revoked, queued and running work cancelled, new calls denied | An immutable audit snapshot | Human review and a fresh start approval |

## Output

Return one markdown document following `templates/harness-design.md`, in this order:

0. Summary (4 to 6 sentences), then "Confirm first" with the 3 to 5 assumptions that most change the design.
1. Runtime frame: trigger, caller, run class, side-effect inventory.
2. Framework decision: what it owns, what you build, defaults set explicitly, exit-test answers.
3. Loop contract, or a reference to the architecture doc plus runtime additions.
4. Run record and state.
5. Checkpoints, idempotency, approvals, compensation.
6. Budgets and stops, with exit statuses and their sinks.
7. Operator controls: cancel, draft-only, abort, replay, triggers, drill.
8. Service endpoint and deployment shape.
9. Harness tests and the run-record contract.
10. Decision log: decision, alternatives, rationale, revisit-when.
11. Handoffs to sibling skills.
12. Risks and open questions.

**Stage gates.** The doc must give someone enough to sign off two gates. Build: the harness has a run record, checkpoints, cancellation and a kill switch. Prove: the harness tests pass (resume, stop, budget, cancel, kill switch). Say in the summary which items pass, which are planned and which are open. The other gate items belong to the owning skills (agent-architect's lifecycle map lists them).

In review mode the order is: Summary and "Confirm first", then the findings table (severity, finding, evidence labelled stated, inferred or confirmed, fix, test, sorted by severity), then the target design with each section's Status line marked keep, change or add, then a migration order that fixes Critical items first. If the user asked a narrow question ("where should the budget check go?"), answer it directly with the relevant rows and skip the template.

## Quality bar

Check every item before returning; fix and re-check any that fail. An item that depends on an input the user has not given passes if the doc states it as an assumption or open question.

- [ ] Every run has a server-issued or event-derived run ID, scoped to its principal, and an append-only record with a header and typed events.
- [ ] State and checkpoints live in a store every worker shares, never process memory; checkpoints carry a schema version; one writer per run or conditional writes.
- [ ] Every side effect has an intent before and a receipt after, a key derived from run state, a lookup before any retry, and a stated resume rule for an intent without a receipt.
- [ ] Every budget has a number and a basis, is checked before every model and tool call, lives in checkpointed state, pauses during human waits and is shared across delegated work.
- [ ] Every stop ends in a named status with a reason from the fixed list (harness-tests.md §4); a forced stop is never `completed`; `cancelled` is distinct from `failed`; every non-completed status has a durable sink.
- [ ] Approvals are bound to a digest of the exact action and arguments, an expiry and a nonce; the executor recomputes the digest; pause and side effect are separate steps.
- [ ] Draft-only and abort are flags read at every call, flipped without a redeploy, with named triggers, a drill and a stated time for a flip to reach running workers (method: harness-components.md §4); abort revokes credentials.
- [ ] Cancellation reaches long tools, which clean up; the disconnect policy is set per run type.
- [ ] Streaming is a view of the record with numbered events and resume by last event ID; output checks finish before text is released.
- [ ] Serving keeps blocking work off the request event loop, separates API, workers and model server, limits each client, checks per-principal access, and drains on shutdown; the endpoint has schemas and problem-details errors.
- [ ] The deployment shape is named by trigger; event receivers never call the model and deduplicate by event ID.
- [ ] Safe-mode replay exists, and the doc says whether replays are experiments or reproductions.
- [ ] The framework's owned parts are listed, its relevant defaults are set explicitly, and provider swaps are logged.
- [ ] The harness tests have "passes when" criteria, run in CI against an out-of-process store, and the run-record contract is handed to agent-eval-designer.
- [ ] Fast-aging facts (framework names, defaults, service limits) are dated and hedged; sibling concerns are handed off by name.

## Common mistakes

| Mistake | Fix |
|---|---|
| Shipping the tutorial harness: in-memory checkpointer behind several workers, a `"default"` thread ID, a `while True` tool loop, a step cap that returns an ordinary answer | Run the tutorial-harness table in harness-components.md; every row it matches is a finding |
| Checking the budget once per turn, or keeping counters in an object outside state | Check before every model and tool call; keep counters in checkpointed state |
| Routing the step cap or an error through the success path | Distinct statuses with reasons; a test that forces each exit |
| Putting the approval check and the write in one step | Pause in one step, execute in the next, behind the key |
| Executing whatever call is on the thread after "approved" | Bind the approval to a digest, an expiry and a nonce; recompute before executing |
| A kill switch that means a redeploy, or lives in the system prompt | Flags in harness state, read at every call; drill them |
| Treating framework replay as reproduction | Reproduce from recorded outputs; experiment with side effects off |
| Running the loop inside the webhook handler | Verify, validate, enqueue, acknowledge; process in a worker |
| A blocking model call or query inside an async handler | Async clients, a worker pool, a separate model server |
| Cancel-on-disconnect by accident (the coroutine died) or never | A policy per run type, recorded in the run |
| Streaming tokens and checking the whole answer afterwards | Buffer, or check each window before release |
| A status or progress endpoint that invokes or streams the graph itself, which in some frameworks resumes the run | The API reads the run record; only workers run the loop |
| Retrying a durable activity that wraps model and tool calls | One side effect per activity, keyed |
| Declaring a status or a `requires_approval` label and never enforcing it | Refuse to start when a labelled tool has no policy wired; test every label by forcing it |
| Quoting a fixed score gap between harnesses, or swapping the model and calling it an upgrade test | Bake off with the model held fixed and compare cost per solved task; the harness may matter as much as a model upgrade on some tasks, or not at all, and it reliably moves cost |
| Keeping critical switches and corrections in the context window | Flags, budgets and tiers are harness state; a person's correction is done only when it is in the persisted spec and the stop check |
| Designing tool schemas, threat models or eval suites here | Mark the attachment point and hand off to the sibling skill |

## Sources

Distilled from the books below. In `references/`, a citation such as [PRODGUIDE ch16] names one of these books and a chapter, and a citation with `repo:` names a file in a companion or related repository; each reference file restates the point it relies on, so the sources are not needed to use the skill.

- PRODGUIDE: *Agentic AI Systems: The Complete Guide for Building Production AI Agents*, ch2, 14, 16, 17, 18.
- SYSTEMS: *Systems Thinking for Agentic AI*, ch6, 8, 10, 13, 16, 17.
- DEFGUIDE: *AI Agents: The Definitive Guide*, ch2, 5, 6, 7.
- RESTCOOK: *RESTful Web API Patterns and Practices Cookbook*, ch2, 3, 5, 7.
- FASTGENAI: *Building Generative AI Services with FastAPI*, ch2, 4, 5, 6, 7, 9, 12.
- MCP: *AI Agents with MCP*, ch6.
- AGENTICAI: *Agentic Artificial Intelligence*, ch8, 11.
- BUILDAPPS: *Building Applications with AI Agents*, ch1, 8.
- BUILDAGENTIC: *Building Agentic AI*, ch2, 5.
- ILLUSTRATED: *An Illustrated Guide to AI Agents*, ch6.
- ENTERPRISE: *The Agentic Enterprise*, ch7.
- MESH: *Agentic Mesh*, ch5.
- AISEC: *Agentic AI for Cybersecurity*, ch4 (defensive material only).
- APIARCH: *Mastering API Architecture*, ch7.
- KGRAG: *Building AI Agents with LLMs, RAG, and Knowledge Graphs*, ch4.
- EVALS: *AI Evals in Practice* (companion code only).

Andrew Ng, The Batch letters:
- Agentic Coding and Agentic Software Testing Go Together (2025-09-17): https://www.deeplearning.ai/the-batch/agentic-coding-and-agentic-software-testing-go-together
- Agents Running in Parallel Get There Faster (2025-08-27): https://www.deeplearning.ai/the-batch/agents-running-in-parallel-get-there-faster
- Improve Agentic Performance with Evals and Error Analysis, Part 2 (2025-10-22): https://www.deeplearning.ai/the-batch/improve-agentic-performance-with-evals-and-error-analysis-part-2
- Build an Autonomous Agent Using This Simple Recipe! (2025-12-10): https://www.deeplearning.ai/the-batch/build-an-autonomous-agent-using-this-simple-recipe
- Agents on the Desktop (2026-06-12): https://www.deeplearning.ai/the-batch/agents-on-the-desktop
- Make All Your Tokens (and Your Brainwork) Count (2026-07-10): https://www.deeplearning.ai/the-batch/make-all-your-tokens-and-your-brainwork-count
- Open Models, Open Harnesses, Open Security (2026-07-31): https://www.deeplearning.ai/the-batch/open-models-open-harnesses-open-security
- What Comes After Tokenmaxxing? (2026-08-07): https://www.deeplearning.ai/the-batch/what-comes-after-tokenmaxxing-how-to-avoid-getting-locked-in-to-just-one-ai-provider
- The AI Engineering Skills Map Part 2 (2026-08-21): https://www.deeplearning.ai/the-batch/he-ai-engineering-skills-map-in-detail-building-and-deploying-ai-applications
- Who's Responsible for Irresponsible AI? (2026-09-18): https://www.deeplearning.ai/the-batch/whos-responsible-for-irresponsible-ai

Repositories (read, not run, 2026-10):
- Companion code: github.com/Nicolepcx/ai-agents-the-definitive-guide (DEFGUIDE), github.com/kylestratis/ai_agents_mcp_examples (MCP), github.com/PacktPublishing/AI-Evals-in-Practice (EVALS), github.com/HandsOnLLM/An-Illustrated-Guide-To-AI-Agents (ILLUSTRATED), github.com/sinanuozdemir/building-agentic-ai (BUILDAGENTIC), github.com/MichaelAlbada/BuildingApplicationsWithAIAgents (BUILDAPPS), github.com/santosomar/AI-agents-for-cybersecurity (AISEC, the multi-agent harness specification), github.com/masteringapi/attendees (APIARCH), github.com/Ali-Parandeh/building-generative-ai-services (FASTGENAI).
- Related (key RELATED): github.com/humanlayer/12-factor-agents, github.com/andrewyng/aisuite, github.com/mamund/apis-and-agents.

Practitioner lab notes (AWS AgentCore and data labs, 2026-10), the source of the lab-tagged rows in [references/aws-implementation-notes.md](references/aws-implementation-notes.md).

External (checked 2026-10):
- LangGraph persistence, time travel and interrupts: https://docs.langchain.com/oss/python/langgraph/persistence , https://docs.langchain.com/oss/python/langgraph/use-time-travel , https://docs.langchain.com/oss/python/langgraph/interrupts
- LangGraph recursion limit and graceful shutdown (fetched 2026-10-19): https://docs.langchain.com/oss/python/langgraph/graph-api , https://docs.langchain.com/oss/python/langgraph/fault-tolerance
- Claude Agent SDK, agent loop: https://code.claude.com/docs/en/agent-sdk/agent-loop
- OpenAI Agents SDK, running agents: https://openai.github.io/openai-agents-python/running_agents/
- Arjmandi, Harness or Model? (arXiv 2609.11987, 2026-09): https://arxiv.org/abs/2609.11987
- Anthropic, How we built our multi-agent research system (2025-06): https://www.anthropic.com/engineering/multi-agent-research-system
- RFC 9457, Problem Details for HTTP APIs: https://www.rfc-editor.org/rfc/rfc9457.html
- Anthropic, Effective harnesses for long-running agents (2025-11): https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents
