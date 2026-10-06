# Business case: <agent / use case>

Sponsor: <name, role> · Process owner: <name> · Business owner / safety owner (if it proceeds): <names> · Date: <YYYY-MM-DD>

## One page

| Field | Content |
|---|---|
| Evidence status | Validated: baseline facts measured (<source, period>) / **UNVALIDATED: pilot required** (assumed: <inputs>). Script verdict: fundable / pilot only / not fundable |
| Decision requested | <fund a pilot of N weeks for <pilot spend> / scale at <full one-off cost> / stop>. An unvalidated case asks for pilot spend only |
| Scope | <in scope request types, channel> · Out of scope: <...> |
| Gate result | <fit quadrant; why errors are caught before effect; risk tier> |
| Unit of value | <metric the business already tracks, e.g. cost per resolved request at reopen rate ≤ baseline> |
| Baseline | <value, measured over <period>, source system (exported history counts if it records effort)>, or "not yet measured: pilot week 0-N measures it" |
| Benefit type | Capacity / cash. Destination of freed hours: <backlog, hiring freeze, redeployment> |
| Costs | Pilot spend <x> (at risk if killed) · full one-off to deployment <x>, of which build & integration <x> · change mgmt & training <x> · escalations & QA <x/month> · wrong outcomes <x/month> · run cost <x/item> · platform share <x/month> · knowledge clean-up <x> |
| Net value (model) | Capacity-valued <x/month>, net cash <x/month>, payback <n> months; combined pessimistic <x/month>; breakeven containment <p%>; kill line <q%> → net <y/month> |
| What decides it | Top 2-3 pilot uncertainties from the sensitivity table and how the pilot measures each; baseline facts still to measure |
| Risks | Strategic: <..> · Organisational: <..> · Governance/compliance: <..> · Operational: <..> · Liability: <..> (each with owner + mitigation) |
| Build / buy | <per layer: what is bought, what is built, exit route> |
| Regulation | <EU AI Act class + duties and dates; GDPR Art. 22? Art. 50 disclosure?> |
| Measurement | <control design, split, stabilisation weeks, measurement window, sample size> |
| Exit criteria | Value: <threshold> · Risk: <error ceiling, no unbounded failure mode> · Platform: <tracing, eval suite, on-call, cost metering> |
| Kill criteria | <containment floor by date> · <wrong-outcome ceiling> · <any unbounded failure mode> |

## Evidence used

| Figure | Value | Grade (A-E) | Source | Used in base case? |
|---|---|---|---|---|
| | | | | yes only if own baseline or A/B |

Context only (grade C-E, not in the numbers): <published figures, labelled>

## Model

Inputs (each marked measured / assumed; list the measured ones in `measured`):

```json
{"currency": "EUR", "measured": ["volume", "human_min", "rate"],
 "volume": 0, "human_min": 0, "rate": 0, "contained": 0, "escalated_min": 0, "qa_share": 0, "qa_min": 0,
 "run_cost": 0, "err_rate": 0, "err_cost": 0, "platform": 0, "pilot_cost": 0, "build": 0, "cash_share": 0,
 "ranges": {"contained": [0, 0], "escalated_min": [0, 0], "err_cost": [0, 0]}}
```

Output: <paste the scripts/roi_model.py output>

Left out of the model: <transition dip, harder residual items, CSAT effects, ...>

## Pilot plan

| Item | Plan |
|---|---|
| Weeks 0-N | Baseline measurement (if missing), process fixes, knowledge clean-up |
| Build | <sprints, users in every review> |
| Stabilisation | <2-4 weeks of tuning; not counted> |
| Measurement window | <weeks, control arm, routing rule> |
| Metrics | Unit metric · model drivers · guardrails · risk · adoption · platform |
| Rollout if exit criteria met | 10 → 25 → 50 → 75 → 100%, stage gates: <...> |
| Reporting | <cadence, audience>; after scale: monthly unit metric, quarterly portfolio review with retire rule |

## Assumptions to verify

1. <assumption>: measured by <how>, by <date>
