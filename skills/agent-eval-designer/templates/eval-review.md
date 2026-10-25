# Eval review: <agent / suite name>

*Reviewed <date> · material read: <files, dataset version, reports, CI config>*

## Verdict

<One or two sentences: what this suite can and cannot currently detect, and whether its numbers support the decision being made on them. If the verdict rests on an unanswered question, write it as a condition with both branches, e.g. "blocked for every user-facing stage if any restricted source is indexed; otherwise only a stage over unrestricted sources is open".>

**Pin check (SKILL.md step 0, done first):** <each model the agent and judge use: status, page, date checked; or "unchecked" (assumed)>

## Findings

Severity: **Critical**: the suite can pass while the agent fails. **High**: the numbers cannot support the decisions made on them, or a judge is untrusted. **Medium**: maintainability, cost, coverage gaps. **Low**: style.

Evidence label per fact: **seen** (code, config, data or a document read; file:line or section) · **observed** (logs, traces, metrics, a report's per-task results or a test run) · **told** (the user or owner said so, unchecked) · **inferred** (seen code plus an unchecked library or platform behaviour; name it and its version) · **assumed** (no evidence). Severity follows the consequence if an inferred or assumed fact holds.

| # | Severity | Location | Finding | Evidence (seen / observed / told / inferred / assumed) | Impact | Fix |
|---|---|---|---|---|---|---|

## Confirm first

<Every inferred or assumed fact a finding rests on, with the artefact that would confirm it. Open with the facts that decide the verdict: for retrieval, whether every indexed source is meant for every user (and who decides); then any pin whose status is unchecked.>

## What the current numbers mean

| Reported | Tasks (sent / scored / errored) | Recomputed interval / test (missing = failed) | Reading |
|---|---|---|---|
| <a number with no per-task results behind it> | <what is known> | not recomputable: no per-task results | Treat as unverified; keep per-task results from now on |
| <any result from a suite whose pin is retired or unchecked> | <what is known> | pin check: <retired / unchecked> | Retired: the suite cannot run as configured, so recent results are unverified. Unchecked: it may not run; confirm before reading any result |

## First three changes

1.
2.
3.

## Out of scope / handed off

<online monitoring → agent-ops-reviewer; attack coverage → agent-threat-modeler; …>

## Review plus plan

<Only when the user also wants a plan ("Both" in SKILL.md). Keep the sections above, in the order above, as the review: it ends with "First three changes" and then "Out of scope / handed off", so both come before the plan, never after it. Then append the eval-plan.md sections in order. In the plan's §12 Rollout, the week-1 build list opens with any open pin-check item, then the Critical findings above, fixed before any new task is added. For a chat answer, use the compressed form in SKILL.md ("Both"), with the same order.>
