# Agent use-case shortlist: <organisation / department>

Decision: <what is being decided, by whom, by when>
Scope of inventory: <teams, processes covered; how tasks were collected: workshop / workload mapping / interviews>
Definitions used: feasibility = <...>; effort = <...>; time-saved scale = absolute / relative to this candidate set (top fifth = 5); matrix cut-offs = impact ≥14/20 and ease (feas. + effort) ≥11/15 count as high, a score at the cut-off counts as high, within one point = borderline (convention)

## Readiness (organisation level)

| Dimension | R/A/G | Evidence | Consequence for the cases |
|---|---|---|---|
| Leadership alignment | | | |
| Technical infrastructure | | | |
| Governance and risk | | | |
| Architecture | | | |
| Technical resources | | | |
| Change management | | | |

## Fit gate

| # | Task as one sentence (owns X, for Y, under Z, produces artifacts) | Concrete enough to prototype? | Volume/month | Min/item | Error cost if uncaught | Checkable before effect? | Hard blocker? | Gate result |
|---|---|---|---|---|---|---|---|---|
| | | pass / rewrite | | | low / high | yes / no + how | none / which | automate · automate behind check · assist · keep with people · redesign first · not an agent |

## Scores (gate survivors only)

| # | Task | Impact /20 (time, strategic, errors, scale) | Feas. /10 (process, data) | Effort /5 | Total /35 | Money/month (volume x min x rate) | Quadrant | Risk tier (T0-T3) | EU AI Act flag | Decision |
|---|---|---|---|---|---|---|---|---|---|---|
| | | 0+0+0+0 | 0+0 | | | <amount>, measured / assumed | quick win · strategic · low priority · avoid · borderline (<two cells>) | | none / Art. 50 / Annex III? | pilot · next · later · drop |

Ties and borderline tasks are decided on the fit result and money per month, not on more points or the quadrant label. Weak-link check on the leaders: any factor at 1 (PRODGUIDE's impact, frequency, data availability, risk, or the five factors below) rules a candidate out as the first pilot, whatever its total.

## Starting autonomy (pick and next in line)

| Task | Volume | Variability | Risk | Judgment | Action scope | Total /15 | Level range | Factors at 1 (constraints) | Actions needing approval each time |
|---|---|---|---|---|---|---|---|---|---|
| | 1-3 | 1-3 | 1-3 | 1-3 | 1-3 | | | | |

## Recommendation

- Pilot: <task>: why it wins (one line, citing gate + score + measurability of its unit metric)
- Next in line: <task>, <task>
- Redesign before automating: <task>: what must change first
- Rejected at the gate: <task>: reason
- Assumptions to verify (each with how to measure it): <...>
- Decide gate for the pilot: concreteness <pass/fail> · data preflight <pass / narrowed to ... / fail> · autonomy scored <total, level> · funding verdict <from the business case>
