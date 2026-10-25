# Context & memory review: <system name>

**Scope reviewed:** <every file in the folder marked read or not read, tests, lock files and example environment files included; library versions from the lock file; traces and configs read; what was not available>
**Verdict:** <2-3 sentences: the biggest risk, the biggest quality loss, the biggest cost waste>

## Measured baseline
| Call | Input tokens p50/p95 | Of which prefix | Cache-read share | Chunks passed | Memory items injected | Notes |
|---|---|---|---|---|---|---|
<Mark "est." where you could not measure. Code-only review (no trace): count the static prompt text from the source (system prompt, tool definitions, fixed instructions) with the model's tokenizer, give every other bucket (history, recalled memory, evidence, tool results) as a low/high range with the assumption that drives it, and name the trace or log field that will replace each estimate.>

## Findings
Severity: **P0** leaks data across users or tenants (memory, threads, checkpoints, caches), loses a safety constraint, or persists secrets or untrusted content · **P1** measurable answer-quality loss (missed retrieval, forgetting, contradictions, stale facts) · **P2** cost or latency waste. Untrusted content is third-party text (documents, web pages, tool output, other users' text); the user's own statements are proposals under the approval rule. Rate a persisted-injection path carried in the user's own statements by what the stored content can trigger now and name the change that raises it (for example, adding a tool that acts); persisted third-party content stays **P0**. Missing deletion, expiry or inspection on durable personal memory: **P0** where privacy duties apply or the deployment is organisation-wide, **P1** otherwise.

Evidence label per fact: **seen** (code, config or document read; file:line) · **observed** (logs, traces, metrics, test run) · **told** (owner or user said so, unchecked) · **inferred** (seen code plus an unchecked library or platform behaviour; name it and its version) · **assumed** (no evidence). Severity follows the consequence if an inferred or assumed fact holds.

| ID | Sev | Layer | Finding (evidence: file:line / trace, with label) | Why it matters | Fix | Verify by |
|---|---|---|---|---|---|---|
| F1 | P0 | retrieval / memory / assembly | | | | |

## Confirm first
<Every inferred or assumed fact a finding rests on, with what would confirm it.>

## Fix order
1. <P0s, in dependency order; a data-handling P0 includes the clean-up of what is already stored (purge or re-mask, cache invalidation, backfill) with a deletion log>
2. <quick wins: changes under a day with clear gains that stand alone, e.g. moving a timestamp out of the prefix. Name any change a quick win depends on; when it removes a step or an edge, check that the user-facing reply still appears>
3. <P1s, each with its before/after metric>
4. <P2s>

## Target design deltas
<Only the parts of the design that change. Use templates/context-design.md sections for the new layout, budget table and memory spec.>

## Evaluation to add
<Test slices and metrics that would have caught these findings, and that must pass before each fix ships.>

## Hand-offs
<What goes to agent-threat-modeler, agent-tool-designer, agent-eval-designer, agent-architect, agent-ops-reviewer, agent-model-selector>

## Open questions
<Include questions for the privacy or legal owner (retention, privilege, whether an exposure must be reported); this review flags them and does not decide them.>
