# Production-readiness review: <agent name>

Date: <YYYY-MM-DD> · Reviewer: <name> · Scope: <launch | scale-up to N/day | post-incident> · Mode: <full | lite | no-loop, no-tool profile>
Evidence base: <code only: no logs, traces, dashboards or owners | code and runtime evidence | description only> · Shipping candidate reviewed: <variant, when the folder holds several>

## Verdict

**<Ready | Ready with conditions | Not ready>**: <one sentence: the deciding blockers or gaps>. Run gate: <pass | fails on rows …>. <Code only: "Ready" is never given; not-assessable items are listed in the discovery plan.>

<When evidence is missing (checklist, "Missing evidence"): **Provisional <verdict>**. Floor <x%> (assumed items at 0) gives <verdict>; ceiling <y%> (assumed items at 2) gives <verdict>, both over assessable items only. Assumed blockers: <IDs>. A blocker seen at 0, or stated absent by its owner, keeps "Not ready" firm.>

<Stubs and missing components: <each stub or absent component, the wiring assumed (from docstrings or README), and the items and verdict that change if it is false>.>

**P0 first** (the full table is under "Prioritised fixes"):

| # | Fix | Due | Owner |
|---|---|---|---|
| 1 | <top P0, e.g. purge and re-mask stored payloads; privacy owner told> | <date or week N> | |

<Three to five rows. Questions for the privacy or legal owner (for example, whether data already exposed must be reported) go here as open items: the review flags them and does not decide them; not legal advice.>

## Confirm first

<Every inferred or assumed fact a finding or score rests on. Severity above already assumes the fact holds.>

| Fact | Tag (inferred: behaviour and version; assumed) | Findings and scores it moves | How to confirm | Who |
|---|---|---|---|---|

## Discovery plan

<When the review is too speculative to score (it replaces the item scores until the evidence arrives), and in a code-only review for the items not assessable from code.>

| Evidence needed | Items it settles | Who holds it | How to get it | Time |
|---|---|---|---|---|

## Context and assumptions

- System: <one paragraph: what it does, users, volume now and on the busiest day, interactive or background>
- Evidence reviewed: <repos, files, dashboards, traces, configs; and what you could not see>
- Credentials found: <file:line and kind only (for example "messaging app secret literal"); never a value or any fragment of one>
- Assumptions (replace with measurements): <numbered list; every number here is labelled "assumed", including model per tier and the peak-hour factor>
- Other variants (not scored): <each variant's defects, when the folder holds several versions of the system>

## Run map

```
<entry> -> <step: model, p, calls, cap> -> <step ...> -> <answer>
           tools: <name (read|write), timeout, retries>
           stop: <caps and the stop reasons they produce>
```

## Blockers

| ID | Blocker | Score | Tag (seen, observed, told, inferred, assumed) | Evidence | Fix (P0) |
|---|---|---|---|---|---|

## Run gate

Before rollout stage: <internal | limited beta | monitored scale>. A row passes when every item it maps to scores 2, seen or observed; each failing row is a P0 fix.

| Row | Items (scores) | Pass or fail | Evidence | Fix |
|---|---|---|---|---|
| 1. Run record | B8 | | | |
| 2. Idempotent side effects | A4 | | | |
| 3. Tiers, approval, kill switch | G5, G7 | | | |
| 4. Redaction and retention | C1, C4 | | | |
| 5. Safe-mode replay | G1, G8 | | | |
| 6. KPIs and reruns | I9, F3 | | | |
| Monitoring live | B1, D3, D7 | | | |
| Autonomy expansion | written conditions, owner | <written and owned | missing> | | handed to agent-threat-modeler |

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
| K. Servers and supply chain | | | | |
| **Total** | | | | |

<N/A items are left out of Max, with the reason in the item table (J4 on managed APIs; G1 with no write tools; K1 when nothing listens locally; K8 only when every server is on stdio or loopback and traces stay on the host; K9 when no request field names a server-side resource). In a code-only review, items not assessable from code are also left out of Max and listed in the discovery plan.>

<details><summary>Item scores</summary>

| ID | Item | Score | Tag (seen, observed, told, inferred, assumed) | Evidence (file:line, config, link) or "no evidence" |
|---|---|---|---|---|

</details>

## Cost and latency snapshot

Prices as of <date>, source <URL>; tiers: <small = model, mid = model, …>. <A tier with no looked-up price is "stand-in for <model>": its dollar figures are order of magnitude, and findings rest on shares, ratios and what-ifs.>
- Per request: expected <$>, likely high (every step at its p95; above a true p95) <$>, capped ceiling <$> (<ratio>x expected; a bound, not a forecast). With no caps: "UNBOUNDED now; <$> with proposed caps <list>".
- Per successful run: <$> at <success rate> success, <review minutes> of review at <$ per minute> (human review <share>), or "not computed: <missing inputs>".
- Per month: <$> at <N>/day expected; <$> at peak (expected × busiest day's volume × 30).
- Per-step share: <top steps>. Latency: <p50/p95 measured or estimated>. Gap to target: <…>.
- Peak load per model at peak-hour factor <x> (default 3 = 24 h ÷ 8 busy hours, assumed until measured): <calls, uncached input and output tokens per minute> vs provider limits.
- Quality baseline for cost levers: <eval set, pass rate with interval, cost per successful run> or "none yet: build it first (agent-eval-designer)".

## Prioritised fixes

| # | Priority | Fix | Where | Verify by | Effort | Owner | Due |
|---|---|---|---|---|---|---|---|
| 1 | P0 | | | | S/M/L | | <date, or "week N" from the review date> |

<Append plan sections from templates/ops-cost-plan.md when they apply: 3 (cost model and levers) and 4 (latency) if the user also asked for a cost or latency cut; 5 (tracing) if any B item scores below 2; 9 (alerts) if any D item scores below 2; 14 (week-by-week rollout) if the review targets a date.>

## Handed to sibling skills

- <agent-architect | agent-harness-designer | agent-eval-designer | agent-threat-modeler | agent-model-selector | agent-context-designer | agent-tool-designer | agentic-business-case>: <what and why>

## Measure next

<the 3 to 5 measurements that would most change this review, and where to get them>
