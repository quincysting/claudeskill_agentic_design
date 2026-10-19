# Tool review: <agent or server name>

## Summary
- <five lines: tool count now and proposed (definitions, distinct names and servers, provider-hosted tools included), integration, selection strategy, riskiest tool and its control, what to fix first; recount every number here from the body before returning>
- <stubs and missing components, if any: each one, the wiring assumed, and the findings that change if the assumption is wrong>

**Verdict:** <one line: e.g. "Safe to keep running only after P0-1 and P0-2; tool choice will stay unreliable until the search/fetch overlap is fixed.">

**Use:** <reference code that teams copy | internal tool | public product>; every priority below is rated against it. **Input:** <code only: no logs, traces, dashboards or owners, so runtime facts are inferred | code plus logs, traces or owner answers>. **Variant reviewed:** <the shipping candidate, when the folder holds several variants of one system; otherwise "one system">.

**Scope reviewed:** <files, tool definitions, server and client code, logs; if no logs or transcripts, say so>. **Model and host:** <…>. **Not reviewed:** <…>.

## Findings

Priority: **P0** wrong irreversible action, duplicate side effect, cross-tenant access or security exposure · **P1** measurable wrong tool, bad arguments, loops or task failure · **P2** tokens, latency, maintainability · **P3** polish.

Calibration: P0 needs an exploitable path or destructive default reachable as shipped under the stated use. A missing extension seam is P1 and its consequences are not counted again. With no logs, a P1 names its trigger in the code path, and a gap with no trigger is P2 or P3. Fill "Becomes P0 when" for every lower finding that can grow.

Evidence: label each fact **seen** (code, config or a supplied document; file:line), **observed** (logs, traces, metrics, a test run), **told** (an owner or user, unchecked), **inferred** (seen code plus a named library, platform or language behaviour and its version) or **assumed** (no evidence). Severity follows the consequence if an inferred or assumed fact holds. Cite credentials by file:line and kind, never by value.

| ID | Priority | Becomes P0 when | Where (tool / file:line) | Issue | Evidence (seen / observed / told / inferred / assumed) | Fix |
|---|---|---|---|---|---|---|
| P0-1 | P0 | n/a | | | | |
| P1-1 | P1 | <trigger, or "no plausible path"> | | | | |

## Other variants (when the folder holds several)
- <variant: its defects, not rated against the shipping candidate>

## Rewritten definitions
<For the two or three worst tools: the new name, description and schema as JSON, plus the runtime checks that go with them.>

## Re-cut tool set and integration (when the request also asks for design)
<Depth: an inventory row for every tool in the new set; a full spec block from tool-spec.md for every write, send, spend or destructive tool; definition JSON for each read tool you add or change (an unchanged read tool keeps only its inventory row); one shared error-contract table; the protocol section if asked, with the alternative you rejected. Say what was removed or folded and why.>

## Already sound
- <what to keep, so it is not changed by accident; each claim needs the same evidence as a finding>

## Confirming the fixes
- Tool-choice eval: <cases to add, especially the confused pairs and negative cases; runs; ship bar>.
- Checks to add in code or tests: <idempotency replay test (same key twice, commit-then-timeout), authorization test, timeout path with verification, one contract test per failure category through the real client, schema diff in CI with a planted break; run them under the agent's own credentials>.

## Confirm first
- <each inferred or assumed fact: the log line, trace, test or eval case that would confirm or clear it>

## Assumptions
- <assumption> (**blocking** if a finding or fix depends on it; how to check)

## Hand-offs
- <agent-threat-modeler: …> · <agent-eval-designer: …> · <agent-architect: …> · <agent-harness-designer: …> · <agent-ops-reviewer: …>
