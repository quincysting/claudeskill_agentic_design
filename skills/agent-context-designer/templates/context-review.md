# Context & memory review: <system name>

**Scope reviewed:** <files, traces, configs read; what was not available>
**Verdict:** <2-3 sentences: the biggest risk, the biggest quality loss, the biggest cost waste>

## Measured baseline
| Call | Input tokens p50/p95 | Of which prefix | Cache-read share | Chunks passed | Memory items injected | Notes |
|---|---|---|---|---|---|---|
<Mark "est." where you could not measure.>

## Findings
Severity: **P0** leaks data across users or tenants, loses a safety constraint, or persists secrets or untrusted content · **P1** measurable answer-quality loss (missed retrieval, forgetting, contradictions, stale facts) · **P2** cost or latency waste.

| ID | Sev | Layer | Finding (evidence: file:line / trace) | Why it matters | Fix | Verify by |
|---|---|---|---|---|---|---|
| F1 | P0 | retrieval / memory / assembly | | | | |

## Fix order
1. <P0s, in dependency order>
2. <quick wins: changes under a day with clear gains, e.g. moving a timestamp out of the prefix>
3. <P1s, each with its before/after metric>
4. <P2s>

## Target design deltas
<Only the parts of the design that change. Use templates/context-design.md sections for the new layout, budget table and memory spec.>

## Evaluation to add
<Test slices and metrics that would have caught these findings, and that must pass before each fix ships.>

## Hand-offs
<What goes to agent-threat-modeler, agent-tool-designer, agent-eval-designer, agent-architect, agent-ops-reviewer, agent-model-selector>

## Open questions
