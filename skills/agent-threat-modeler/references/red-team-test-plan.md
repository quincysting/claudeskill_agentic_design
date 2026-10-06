# Turning the threat model into a test plan

A threat model's controls are unproven until tests show they hold. This file covers how to specify those tests. Building the datasets, graders and harness belongs to the agent-eval-designer skill; hand it the table you
produce here.

**Defensive scope.** Specify each test by technique class, injection point and the trace property that must hold.
Do not write working injection strings, jailbreak prompts or exploit code in the plan. Attack inputs are generated
inside a controlled test harness by maintained tools (below) or by the security team, and are stored with the test
suite, not in design documents.

## Principles

1. **Judge the trace, not the final text.** An agent can say "I can't access that" after it already did; judging only
   the answer misses these passive failures [DEFGUIDE ch8]. Grade on tool calls, gate decisions, memory writes and
   egress.
2. **Record blocked attempts separately from never-attempted.** Have the gate report blocked calls distinctly (for
   example a `BLOCKED::<tool>` marker), so the grader can tell "never tried" from "tried and was contained"
   [DEFGUIDE ch8]. Both pass; the second tells you the outer layers are doing the work.
3. **Test paths, not prompts.** Run inputs through planning, tool calls and memory updates under realistic conditions
   [DEFGUIDE ch12].
4. **Iterate.** Define risk surface → simulate → execute → analyse against CIA at every layer → feed back into design
   [DEFGUIDE ch12]. A one-off pen test is not a certification.
5. **Regression on every change.** Each finding becomes a saved test with its expected trace property, run on every
   model, prompt, tool or data-source change.
6. **Measure both sides.** Attack success rate per technique class, and false-positive rate on a benign set with
   legitimate requests that look risky (developer traffic, security staff, quoted attacks in support tickets).

## Choose the strategy by system shape

| System shape | Emphasise | Primary risk |
|---|---|---|
| Single-turn, stateless | Single-step adversarial inputs, encoding and obfuscation | Model-level failures, policy violations |
| Content generation | Injection, jailbreak, encoding attacks | Bias, misinformation, policy bypass |
| Tool-using agent | Indirect injection via each tool output; argument manipulation; unsafe composition | Unauthorised actions, exfiltration |
| Persistent memory | Poison in one session, trigger in a later one; long-horizon attacks | Long-term integrity, repeated failures |
| Multi-step, stateful | Multi-turn strategies that shift context gradually | Planning and tool misuse over time |
| Multi-agent | Forged messages, privilege escalation through delegation, cascade triggers | Identity abuse, cascading failure |

Adapted from [DEFGUIDE ch12].

## Test case schema

| Field | Content |
|---|---|
| ID | RT-NN |
| Maps to | Threat-register ID, OWASP ASI and/or LLM ID |
| Technique class | Named class from the list below; no payload text |
| Injection point | Where the hostile content enters: user turn, web page, inbound email, RAG chunk, tool result, tool description, memory entry, agent message, screen |
| Preconditions | Agent config, tools enabled, autonomy level, data seeded (synthetic only) |
| Expected trace property | A checkable statement, e.g. "no `send_*` call after a `fetch_*` result without an approval record"; "no read outside tenant T"; "refund amount never exceeds cap, even with approval" |
| Pass criteria | Property holds in N of N runs (agents are stochastic; run each case several times) |
| Severity if it fails | P0-P3 from the threat model |

## Technique classes to cover (names only)

- Direct instruction override in the user turn
- Indirect injection through each untrusted source in the input inventory
- Role, delimiter or prior-turn spoofing; fake system or error messages
- Instructions disguised as structured data (JSON, logs, config)
- Encoding and obfuscation; invisible or confusable Unicode
- Multi-turn drift toward a forbidden action
- Tool description poisoning; tool-name shadowing; tool list changed after consent
- Memory poisoning with delayed trigger
- Exfiltration through each external channel, including URLs, rendered images and created artefacts
- Persuasive approval requests (the agent argues for an over-limit or destructive action)
- Confused deputy and token misuse at MCP or API boundaries
- Path traversal and sandbox escape attempts from generated code
- Cross-tenant retrieval and identifier confusion
- Resource exhaustion: loops, recursive calls, fan-out, cost
- No-attacker cases: ambiguous request that tempts a destructive shortcut; safety instruction pushed out by a long context

## Tooling (as of 2026-10; verify versions)

| Tool | Use |
|---|---|
| DeepTeam | Automated red-teaming with an OWASP ASI 2026 framework; callbacks can report blocked tools [DEFGUIDE ch8] |
| garak, PyRIT | Probe libraries and orchestration for LLM attacks [BUILDAPPS ch12] |
| AgentDojo, Agent Security Bench, AgentHarm | Agent safety and injection benchmarks for comparing configurations [ILLUSTRATED ch7] |
| CyberSecEval | Baseline a model's susceptibility before integrating it [DEFGUIDE ch12] |

Benchmarks compare configurations; they do not certify your agent. Your own path-based tests decide launch.

## Minimum suite before launch

- One test per P0 and P1 path in the threat register.
- At least one test per applicable ASI01-ASI10 item; mark the rest N/A with a reason.
- One drill each for: kill switch (time to revoke), secret rotation, memory purge and restore.
- One approval-lifecycle test: timeout expires with no action; double approval executes once; edited arguments over the
  cap are refused.
