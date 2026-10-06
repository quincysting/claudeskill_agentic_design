# Single agent or several, and how they coordinate

Citation keys such as [SYSTEMS ch13] point to the book list under Sources in SKILL.md.

A split is a purchase. You buy **isolation**: each role gets a narrower context, smaller tool set, narrower permissions, its own output contract and its own eval. You pay a **handoff** at every boundary: context packaged, a model call, output validated and merged, a trace entry, a new place for errors. A single agent centralises responsibility; a multi-agent system distributes it and then pays to coordinate it [SYSTEMS ch13]. Add the fewest agents that work, and weigh each one's coordination cost against what it adds [BUILDAPPS ch8].

Engineering test for "multi-agent": more than one model-driven loop, each with its own instructions, context and tools, in one workflow. A fixed sequence of LLM calls with role names is a workflow.

## Default and verdict

**Start with one agent.** The books disagree here more than anywhere else; single-agent-first holds up better because:
- The pro-split evidence in the books is arithmetic, analogy or cited claims; the costs (coordination, latency, debugging, ping-pong handoffs) are documented in several books and in measured external work.
- Most pro-split mechanisms are available inside one agent (below).
- Measured gains appear in one shape of work: parallel, breadth-first, answer-returning subtasks.

External measurements (as of 2026-10):
- Anthropic's research system (Opus lead, Sonnet subagents) beat single-agent Opus by 90.2% on an internal breadth-first research eval, using about 15× chat-level tokens; token usage alone explained 80% of performance variance on BrowseComp (Anthropic, 2025-06).
- Kim et al. (260 configurations, six benchmarks, three model families): +80.8% on decomposable financial reasoning, −70.0% on sequential planning; negative returns once a single agent already exceeds about 45% accuracy; error amplification 17.2× for independent agents versus 4.4× for centrally coordinated ones (arXiv 2512.08296, v3 2026-04).
- MAST: 14 failure modes in three groups (system design, inter-agent misalignment, task verification) from 1,600+ traces across seven frameworks; a whole class of failure exists only because there is more than one agent (Cemri et al., arXiv 2503.13657).

## Split test

For each proposed agent, answer SYSTEMS's five questions [SYSTEMS ch13]:
1. Can its responsibility be described on its own?
2. Does it need different context?
3. Does it need different tool access?
4. Does it have a different output contract?
5. Would separating it make debugging easier?

Mostly no → merge it back. Then split only when at least one holds:
- **A real boundary:** different data access or sensitivity, permissions, tool set, or evaluation criteria [SYSTEMS ch18]. Example: a router that sees only categories runs on a managed API while a retrieval agent touching PII runs on a self-hosted model [DEFGUIDE ch11] [ENTERPRISE ch1].
- **Breadth-first parallel work** whose subagents return answers, not parts of one artifact, and the token budget allows several times the single-agent cost.
- **Independent lifecycle:** one role must change, release or be certified alone (a compliance agent updated for new regulations without touching the others [AGENTICAI ch3]; a qualification prompt change that cannot regress emailing [BUILDAGENTIC ch4]).

Keep one agent when: the work is sequential and tightly coupled (most coding, single-document writing); the feature is interactive and latency-bound; the failures are tool-choice errors; or you cannot yet see inside the single agent [SYSTEMS ch13].

**Answer or artifact?** Subagents that search and report answers parallelise well. Parallel workers building pieces of one artifact make conflicting implicit decisions they cannot see (Cognition, 2025-06). Shared artifacts need one writer or a sequential pipeline with an explicit decisions record.

## Fix inside one agent first

| Symptom | Fix before splitting |
|---|---|
| Too many tools; wrong tool chosen | Tool search or hierarchical tool selection, coarser higher-order tools [BUILDAPPS ch8] (agent-tool-designer) |
| Context too big or noisy | Per-step context assembly, compaction (agent-context-designer) |
| Needs a clean context for a sub-question | Subagent as a tool: called like a function, returns an answer, control stays with the caller [ILLUSTRATED ch8] |
| Stuck in a "default mode" loop | Loop detector, evidence-triggered reflection, a reviewer step |
| Wants a second opinion | Actor-critic or verifier step; this is test-time compute, not decomposition [BUILDAPPS ch8] |

Weighing common pro-split claims:
- *"Smaller contexts are more reliable."* True; the mechanism is context hygiene, available in one agent.
- *"Errors compound, so decompose."* Per-hop failure multiplies too; what lowers error in MESH's own account is decomposition plus deterministic execution and per-step verification [MESH ch6], which a planner plus code executor also has.
- *"Fine-grained tools cost up to 45× more."* That compares fine-grained command-line tools with higher-order tools [ENTERPRISE ch1]; it argues for coarser tools, not more agents. The source cites the figure without demonstrating it.
- *"One agent per tool."* Reported without measurements, and the same account needed "translator agents" after a day-one crash because agents could not share information [AGENTICAI ch3].
- *"Debate among diverse models scores higher."* An ensemble effect on verifiable questions [AGENTICAI ch6]; useful for answer quality, irrelevant to whether to decompose a workflow.

## If you split: the controlled runtime

Separate a **reasoning plane** (model-driven roles) from a **control plane** in code: authorisation, orchestrator, schema and policy checks, state, approval gates, tool execution, timeouts, cost limits, tracing [SYSTEMS ch13]. Agents propose; the runtime decides.

### Topology

Words mean different things in different sources; say which you mean.

| Topology | Means | Use when | Watch out |
|---|---|---|---|
| Orchestrator-workers (supervisor) | One coordinator assigns, collects, reconciles | The default | Coordinator creep: it starts summarising, judging, repairing until it is the single agent again with expensive helpers [SYSTEMS ch13]. Keep it in code |
| Planner-executor | A model plans; code executes and can reject the plan [SYSTEMS ch13] [MESH ch6] | Ambiguous requests acting on real systems | Only one model role: the best-supported "decomposition" |
| Boundary specialists | Read-only retriever, no-tool reviewer, one narrow validated action path [SYSTEMS ch13] | Roles differ in permissions, data or criteria | Specialists sharing the same context, tools and schema are role theatre |
| Review / actor-critic / safeguard | One generates, another accepts or rejects against a rubric [BUILDAPPS ch8] [ENTERPRISE ch1] | Clear rubric, affordable extra calls | Cap at 1 to 2 rounds or "the system performs confidence rather than producing value" [SYSTEMS ch13] |
| Hierarchy (teams of teams) | Supervisors of supervisors [DEFGUIDE ch2] [MESH ch14] | Many specialists in distinct sub-domains; one chain of control | Harder to debug; a flat supervisor with five workers often suffices |
| Peer handoff / swarm | The receiver takes over the conversation [DEFGUIDE ch2] | Conversations that move between experts | Low repeatability; default handoffs may forward full history; ping-pong [BUILDAGENTIC ch5] |
| Network / democratic | Any agent messages any other | Rarely | Expensive in messages, hard to predict |
| Event-driven fleet | Per-agent queues, pub/sub, replay [MESH ch7] [MESH ch10] | Long-running async work, many instances | Overkill for request/response features |
| Cross-organisation over A2A | Remote agent owned by another team or company [ILLUSTRATED ch8] | Real organisational boundary | Authorisation outside the prompt; protocol details: agent-tool-designer |

### Coordinator

- The control plane (policy, budgets, audit) has one deterministic owner. That is ordinary infrastructure and can be replicated.
- An LLM coordinator that makes every routing judgment is the single point of failure to avoid [ENTERPRISE ch6]. If a model routes, its output is a constrained choice: an enum of specialists plus FINISH [DEFGUIDE ch2].
- Centrally coordinated agents amplified errors far less than independent ones (4.4× versus 17.2×, Kim et al.).

### Communication

- **Default: orchestrator-mediated, typed messages.** Every message passes the orchestrator, which validates it, updates state and picks the next step: one place for schemas, permissions, retries, stop rules and logging [SYSTEMS ch13]. No free-form agent chat.
- **Event bus is a transport, not a contract.** Queues and pub/sub (Kafka, NATS JetStream, Redis Streams, RabbitMQ) decouple senders and give replay [MESH ch10] [BUILDAPPS ch8]; they carry the typed messages. Small messages with new information only; fetch history by conversation ID [MESH ch10].
- **Transport ladder:** in-process calls → message broker → actor framework (pays off beyond roughly 10 to 20 agents or under tight latency) → durable workflow engine for long runs [BUILDAPPS ch8].
- **Task lifecycle:** every task gets an ID and explicit states (e.g. ready, working, pending, error, complete), so a stalled task waits visibly [MESH ch10].
- **Shared state** (blackboard, workspace): append-only, attributed writes; record which version each step consumed [SYSTEMS ch13].

### Context passing

- Answer-returning subagent: pass the task and a named context slice, not the history. DEFGUIDE's orchestrator passes only the current turn [DEFGUIDE ch10]; passing everything down the chain overloads agents [ENTERPRISE ch6].
- Subagent whose output must cohere with decisions made elsewhere: share those decisions explicitly as a structured decisions record, or do not split.
- Subagent brief (Anthropic, 2025-06): objective, output format, tool and source guidance, task boundaries; scale effort to the query (1 agent with 3 to 10 tool calls for fact-finding; 2 to 4 subagents with 10 to 15 calls each for comparisons).
- Exact or sensitive values travel between agents through code, not through the model [ENTERPRISE ch1].

### Memory topology

Per-agent local (clean, drifts), shared global (one truth, noisy and token-hungry), hybrid (usual choice) [DEFGUIDE ch10]. Specialists can be per-invocation, per-thread, or stateless (no interrupts or recovery). Memory design detail: agent-context-designer.

### Caps and conflict

- Hard caps per run: model calls, tokens, wall time, hops, review rounds (1 to 2).
- Detect repeated messages between the same agents (tailspin): timeouts plus repetition detection [ENTERPRISE ch6].
- One written rule for disagreement (severity wins, policy wins, rank, or a human) and one owner of the final output [SYSTEMS ch13].
- Validation gates at every hop; sanity-check inputs that come from other agents; circuit breakers stop propagation. AGENTICAI's telecom case: one agent's misjudged capacity cascaded through four dependent agents into a service disruption [AGENTICAI ch6].
- Inter-agent messages and shared memory are untrusted input (poisoned memory spreads across agents [BUILDAPPS ch12]); threat-model with agent-threat-modeler.

### Reliability arithmetic for chains of agents

At 98% per agent: 3 agents ≈ 94.1%, 5 ≈ 90.4%, 10 ≈ 81.7%. With gates catching 90% of bad outputs per boundary: ≈ 99.4%, 99.0%, 98.0% [DEFGUIDE ch5]. Every boundary multiplies risk; validation at the boundary is what turns decomposition into reliability. Independence is assumed, so treat as intuition.

### Model per role

Size each role's model by its error cost: a cheap lead generator because a second agent re-checks it, a larger qualifier because a false positive means contacting someone who should not be contacted [BUILDAGENTIC ch4]. Model picks: agent-model-selector.

## Example shape: controlled two-specialist review

- Orchestrator in code; a call budget.
- Two read-only specialists (e.g. security, performance) run in parallel because they are independent.
- One message schema (`file, line, severity, claim, evidence`), validated at every hop; malformed output fails at that hop.
- Grounding filter in code: drop any finding whose evidence text does not appear in the input.
- A critic with no tools that may only remove findings: keep `critic_output ∩ critic_input`, so a critic that starts rewriting changes nothing.
- Conflict rule: per (file, line), highest severity wins.
- Any critical finding escalates to a person.
- Before adopting: run the same inputs through one agent with both scopes and compare precision, recall, latency and cost. If one agent is as good, keep one.

## Multi-agent eval and tracing hooks

One run ID propagated to every subagent, nested trajectories stored with the parent [MESH ch10]; per-agent evals plus end-to-end checks; failures labelled by MAST category. Design these with agent-eval-designer and agent-ops-reviewer.
