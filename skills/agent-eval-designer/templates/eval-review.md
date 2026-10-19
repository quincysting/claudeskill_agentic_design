# Eval review: <agent / suite name>

*Reviewed <date> · material read: <files, dataset version, reports, CI config>*

## Verdict

<One or two sentences: what this suite can and cannot currently detect, and whether its numbers support the decision being made on them.>

## Findings

Severity: **Critical**: the suite can pass while the agent fails. **High**: the numbers cannot support the decisions made on them, or a judge is untrusted. **Medium**: maintainability, cost, coverage gaps. **Low**: style.

Evidence label per fact: **seen** (code, config, data or a document read; file:line or section) · **observed** (logs, traces, metrics, a report's per-task results or a test run) · **told** (the user or owner said so, unchecked) · **inferred** (seen code plus an unchecked library or platform behaviour; name it and its version) · **assumed** (no evidence). Severity follows the consequence if an inferred or assumed fact holds.

| # | Severity | Location | Finding | Evidence (seen / observed / told / inferred / assumed) | Impact | Fix |
|---|---|---|---|---|---|---|

## Confirm first

<Every inferred or assumed fact a finding rests on, with the artefact that would confirm it.>

## What the current numbers mean

| Reported | Tasks (sent / scored / errored) | Recomputed interval / test (missing = failed) | Reading |
|---|---|---|---|
| <a number with no per-task results behind it> | <what is known> | not recomputable: no per-task results | Treat as unverified; keep per-task results from now on |

## First three changes

1.
2.
3.

## Out of scope / handed off

<online monitoring → agent-ops-reviewer; attack coverage → agent-threat-modeler; …>

## Review plus plan

<Only when the user also wants a plan ("Both" in SKILL.md). Keep the sections above as the review, then append the eval-plan.md sections in order. In the plan's §12 Rollout, the week-1 build list is the Critical findings above, fixed before any new task is added.>
