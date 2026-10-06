# Pilot design, scale gates and portfolio review

Load this for steps 8-9 of Mode A.

## 1. What the first pilot should prove

The books disagree. AGENTICAI wants a quick win with results in three to six months [AGENTICAI ch8]. MESH wants an MVP that proves the platform scaffolding: identity, observability, explainability, fleet coordination [MESH ch15]. ENTERPRISE wants pilots that test networks of agents on real data platforms [ENTERPRISE ch4]. BUILDAPPS starts with one bounded workflow [BUILDAPPS ch2].

**Verdict: narrow in scope, production-shaped in plumbing.** One bounded use case, run on real data and integrations, with tracing, evals, cost metering and registration from day one. A pilot on demo data proves nothing about scale. A network of agents in the first pilot makes results hard to attribute. Test the platform effect with the second and third use cases on the same plumbing.

## 2. Pilot principles [ENTERPRISE ch4]

- Connect to the real data platforms and registries, so results aren't polluted by inconsistent data.
- Design for portability from the start: common agent interfaces, standard data contracts for tools, no business logic hardcoded in one vendor's framework.
- Governance from day one: registration, guardrails, risk classification, human review where needed.
- Baselines, control groups and operational KPIs.
- Exit criteria agreed before day one.
- Users in every review. AGENTICAI's insurer had claims adjusters in every two-week sprint review, and they caught claim types that needed special handling [AGENTICAI ch11].

## 3. Choosing the control

| Situation | Control design | Why | Watch out |
|---|---|---|---|
| High volume, errors cheap or capped | **Random split** of eligible items (e.g. 50/50) for a fixed window | Cleanest: same period, same mix | Randomise by item or customer, not by agent choice. Keep routing logged |
| Several teams, regions or sites | **Staggered rollout**: switch units on at different dates; compare switched vs not-yet-switched in the same weeks | Controls for seasonality; used in the 5,179-agent support study ([NBER w31161](https://www.nber.org/papers/w31161), external) | Units must be comparable; watch spillover between teams |
| Moving live volume over anyway | **Staged rollout as control**: 10 → 25 → 50 → 75 → 100%, comparing each stage's agent traffic with the traffic still handled the old way | Gets speed and rigour together | Don't jump stages while metrics are unstable |
| Revenue, retention or quality outcomes | **Holdout**: a fixed set of customers or accounts never gets the agent | These effects are slow and noisy | Keep the holdout long enough, and big enough |
| Low volume, high stakes | **Shadow mode**: the agent runs on live inputs, a person decides, compare agent vs human decisions | Measures accuracy with no exposure | Proves accuracy, not value; human time doesn't fall yet |
| None of the above possible | **Before/after** with a seasonally matched baseline | Better than nothing | Grade B at best. Avoid peak-month baselines and holiday end points |

**Rough sample size** (standard statistics, Lehr's rule: 80% power, two-sided 5% significance): per arm, n ≈ 16 x variance / (difference to detect)². For a rate p, variance = p(1 − p).
- Reopen rate 8%, detect a 2-point change: 16 x 0.08 x 0.92 / 0.02² ≈ 2,950 items per arm.
- Handling time mean 5 min, SD 4 min, detect 0.5 min: 16 x 16 / 0.25 ≈ 1,020 per arm.

Divide by monthly volume per arm to get the window. If it's longer than about three months, widen the effect you need to detect, pool similar request types, or accept a staggered design and say so.

## 4. Timing

- **Stabilisation period first.** Agree 2-4 weeks of tuning before the measurement window opens. The transition dip (J-curve) makes early weeks look worse than steady state [AGENTICAI ch10]. Novelty can make them look better.
- **Measurement window**: at least one full business cycle (month-end, weekly peaks), and long enough for the sample size above.
- Set controls up early. Once a tool is indispensable, people stop accepting the no-agent arm. METR found developers withholding tasks they didn't want to do without AI ([METR 2026](https://metr.org/blog/2026-02-24-uplift-update/), external).

## 5. What to measure

| Kind | Metrics |
|---|---|
| Unit metric | The one in the business case, e.g. cost per resolved request |
| Model drivers | Containment, escalation handling time, wrong-outcome rate and cost, run cost per item: the inputs to the ROI model |
| Guardrails | Reopen rate, CSAT, complaint rate, error rate on sampled items. Must be no worse than control |
| Risk | Failure modes seen, policy violations, incidents, override and escalation rates |
| Adoption | Share of eligible work routed to or used with the agent, user feedback |
| Platform | Tracing coverage, eval suite pass rate, on-call in place, cost metered per agent |

AGENTICAI's balanced scorecard groups these into operational efficiency, employee impact, customer experience and the agent's autonomous handling rate (40% to 75% of cases in six months in its example) [AGENTICAI ch10]. Report against pre-deployment baselines on a fixed cadence. Never use self-reported productivity as the measure.

## 6. Exit and kill criteria (agreed before day one)

Scale only when all three hold [ENTERPRISE ch4]:
- **Proven value**: benefit above a threshold set in advance. Tie it to the ROI model: net value at the measured rates, applied to full volume, at or above the model's net at the agreed containment floor (business-case-and-roi.md §6).
- **Acceptable risk profile**: stable error rates, controlled failure modes, no unbounded failure mode, governance compliance, limited reputational and financial exposure.
- **Platform readiness**: data, infrastructure and support teams can carry production volume.

Also check change readiness (training, process change, frontline adoption) and report to senior management on the same criteria.

**Kill criteria**: the containment kill line from the floor rule (business-case-and-roi.md §6), applied after the tuning period; a wrong-outcome ceiling; any unbounded failure mode. Write them as numbers with dates. Without them the pilot never scales and never dies, which ENTERPRISE calls "pilot purgatory".

## 7. Scaling up

AGENTICAI's insurer is the best worked path in the books [AGENTICAI ch11]: three weeks of process redesign (systems touched cut from seven to three), six two-week sprints with adjusters in every review, then live traffic at 10% in week 1, 25% in week 2, 50% in week 3, 75% in week 4 and full deployment in week 5. The reported results after six months are grade B or C: information-gathering time down 70%, 85% of standard correspondence automated, processing time down 45%.

Gate each stage: metrics stable for the stage window, no new failure mode, comparison with old-way traffic still favourable. Roll back one stage on breach.

## 8. Portfolio and platform

The books disagree on per-use-case versus portfolio ROI. ENTERPRISE treats agent ROI as a platform-and-portfolio measure over time [ENTERPRISE ch4]. AGENTICAI argues for an enterprise-wide case but works its example as one department's three-year ROI [AGENTICAI ch10], [AGENTICAI ch11].

**Verdict: fund the platform on the portfolio; judge each agent on its own unit metric with a kill rule.** DBS does both: a shared platform, plus retiring models with no measured benefit. Its shared data platform and AI library cut model delivery from about 12-15 months to 2-3 [ENTERPRISE ch4]. A portfolio argument without per-agent kill rules hides the agents that lose money.

Cadence:
- Monthly: each agent's unit metric, cost per item, and incidents against its business case.
- Quarterly: portfolio review. Retire or rescope agents without measured benefit; reallocate platform cost.
- Platform leading indicators (they show the platform getting faster, not that any agent pays): time from idea to production (JPMorganChase's metric [ENTERPRISE ch4]), share of new agents built on shared actions and templates, active users.

Cost first or revenue first? Pets at Home steers toward revenue because "Cost efficiency is always capped" [AGENTICAI ch12]. Start where measurement is cleanest (cost, time, errors) to earn credibility, but don't rank the whole portfolio on savings. Revenue and quality cases need holdouts and leading indicators while they mature.

Pipeline mix: rank by feasibility, value and demonstration potential, and mix low-risk efficiency projects with stretch ones [MESH ch15].
