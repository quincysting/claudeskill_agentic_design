# Production-readiness review: <agent name>

Date: <YYYY-MM-DD> · Reviewer: <name> · Scope: <launch | scale-up to N/day | post-incident> · Mode: <full | lite>

## Verdict

**<Ready | Ready with conditions | Not ready>**: <one sentence: the deciding blockers or gaps>.

<When evidence is missing (checklist, "Missing evidence"): **Provisional <verdict>**. Floor <x%> (unverified items at 0) gives <verdict>; ceiling <y%> (unverified items at 2) gives <verdict>. Unverified blockers: <IDs>. A blocker seen at 0 keeps "Not ready" firm.>

## Discovery plan

<Only when the review is too speculative to score; it replaces the item scores until the evidence arrives.>

| Evidence needed | Items it settles | Who holds it | How to get it | Time |
|---|---|---|---|---|

## Context and assumptions

- System: <one paragraph: what it does, users, volume now and on the busiest day, interactive or background>
- Evidence reviewed: <repos, files, dashboards, traces, configs; and what you could not see>
- Assumptions (replace with measurements): <numbered list; every number here is labelled "assumed", including model per tier and the peak-hour factor>

## Run map

```
<entry> -> <step: model, p, calls, cap> -> <step ...> -> <answer>
           tools: <name (read|write), timeout, retries>
           stop: <caps and the stop reasons they produce>
```

## Blockers

| ID | Blocker | Score | Tag (seen, told, U) | Evidence | Fix (P0) |
|---|---|---|---|---|---|

## Scorecard

| Area | Points | Max | % | Biggest gap |
|---|---|---|---|---|
| A. Bounded execution | | | | |
| B. Tracing | | | | |
| C. Logging and redaction | | | | |
| D. Monitoring and alerts | | | | |
| E. Online evals | | | | |
| F. CI gates and versioning | | | | |
| G. Release and rollback | | | | |
| H. Improvement loop | | | | |
| I. Cost and latency | | | | |
| J. Deployment and capacity | | | | |
| **Total** | | | | |

<N/A items are left out of Max, with the reason in the item table (J4 on managed APIs; G1 with no write tools).>

<details><summary>Item scores</summary>

| ID | Item | Score | Tag (seen, told, U) | Evidence (file:line, config, link) or "no evidence" |
|---|---|---|---|---|

</details>

## Cost and latency snapshot

Prices as of <date>, source <URL>; tiers: <small = model, mid = model, …>.
- Per request: expected <$>, likely high (~p95) <$>, capped ceiling <$> (<ratio>x expected; a bound, not a forecast). With no caps: "UNBOUNDED now; <$> with proposed caps <list>".
- Per month: <$> at <N>/day expected; <$> at peak (expected × busiest day's volume × 30).
- Per-step share: <top steps>. Latency: <p50/p95 measured or estimated>. Gap to target: <…>.
- Peak load per model at peak-hour factor <x> (default 3 = 24 h ÷ 8 busy hours, assumed until measured): <calls, uncached input and output tokens per minute> vs provider limits.
- Quality baseline for cost levers: <eval set, pass rate with interval, cost per successful task> or "none yet: build it first (agent-eval-designer)".

## Prioritised fixes

| # | Priority | Fix | Where | Verify by | Effort | Owner | Due |
|---|---|---|---|---|---|---|---|
| 1 | P0 | | | | S/M/L | | <date, or "week N" from the review date> |

<Append plan sections from templates/ops-cost-plan.md when they apply: 3 (cost model and levers) and 4 (latency) if the user also asked for a cost or latency cut; 5 (tracing) if any B item scores below 2; 9 (alerts) if any D item scores below 2; 14 (week-by-week rollout) if the review targets a date.>

## Handed to sibling skills

- <agent-architect | agent-eval-designer | agent-threat-modeler | agent-model-selector | agent-context-designer | agent-tool-designer | agentic-business-case>: <what and why>

## Measure next

<the 3 to 5 measurements that would most change this review, and where to get them>
