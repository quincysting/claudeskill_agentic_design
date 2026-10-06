# Tool review: <agent or server name>

## Summary
- <five lines: tool count now and proposed, integration, selection strategy, riskiest tool and its control, what to fix first>

**Verdict:** <one line: e.g. "Safe to keep running only after P0-1 and P0-2; tool choice will stay unreliable until the search/fetch overlap is fixed.">

**Scope reviewed:** <files, tool definitions, server and client code, logs; if no logs or transcripts, say so and mark findings "inferred">. **Model and host:** <…>. **Not reviewed:** <…>.

## Findings

Priority: **P0** wrong irreversible action, duplicate side effect, cross-tenant access or security exposure · **P1** measurable wrong tool, bad arguments, loops or task failure · **P2** tokens, latency, maintainability · **P3** polish.

| ID | Priority | Where (tool / file:line) | Issue | Evidence | Fix |
|---|---|---|---|---|---|
| P0-1 | P0 | | | | |
| P1-1 | P1 | | | | |

## Rewritten definitions
<For the two or three worst tools: the new name, description and schema as JSON, plus the runtime checks that go with them.>

## Re-cut tool set and integration (when the request also asks for design)
<Depth: an inventory row for every tool in the new set; a full spec block from tool-spec.md for every write, send, spend or destructive tool; definition JSON only for read tools; one shared error-contract table; the protocol section if asked, with the alternative you rejected. Say what was removed or folded and why.>

## Already sound
- <what to keep, so it is not changed by accident>

## Confirming the fixes
- Tool-choice eval: <cases to add, especially the confused pairs and negative cases; runs; ship bar>.
- Checks to add in code or tests: <idempotency replay test, authorization test, timeout path>.

## Assumptions
- <assumption> (**blocking** if a finding or fix depends on it; how to check)

## Hand-offs
- <agent-threat-modeler: …> · <agent-eval-designer: …> · <agent-architect: …> · <agent-ops-reviewer: …>
