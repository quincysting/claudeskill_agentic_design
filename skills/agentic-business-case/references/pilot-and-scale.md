# Pilot design, scale gates and portfolio review

Load this for step 5 of Mode A (the data preflight, §3) and steps 8-9 (pilot, scale, portfolio), and when a vendor offers a free pilot or prices by outcome (§10).

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

## 3. Data preflight: is the data ready? (Decide gate item)

Run it on the pick before any source is connected and before the business case is final: its failures narrow the scope and its fixes become cost lines. It prevents the commonest failure in PLAYBOOK's telling: the agent works in testing, gives inconsistent answers on real data, and the team swaps models and rewrites prompts for weeks before anyone looks at the blank CRM fields and the out-of-date knowledge base [PLAYBOOK ch3]. Confident wrong answers do more damage than obvious failures, because people trust them.

1. **Capture the real workflow.** Sit with the person who does the work while they do it. Each "it depends", "usually" or "unless" is a decision point the write-up needs. The write-up answers five questions: what triggers the workflow; what information exists at the start and where it comes from; which steps follow and what is decided at each; how the common exceptions are handled; what success, failure and escalation look like [PLAYBOOK ch3]. Give it a version, a last-reviewed date and an owner, and update the agent's instructions in the same cycle whenever the process changes.
2. **Documentation test.** Someone who does not do the job follows the write-up without help. Where they get stuck, the agent will too; fix the document, not the prompt [PLAYBOOK ch3]. This applies the book's advice to treat an agent like a new colleague in their first month [PLAYBOOK ch1]. A process that fails the test counts as "process not proven" in the fit gate (fit-and-scoring.md §3) until it passes.
3. **Audit only the fields the task uses.** List the fields and sources the task depends on, and audit those rather than the whole estate. PLAYBOOK sets 90% as the bar: a structured field the agent decides on, or shows to customers, should be filled in and correct in at least nine records out of ten [PLAYBOOK ch3]. Warning signs: CRM records with more than 20% of fields blank, duplicate customers, or no update in 90 days; databases with more than 10% of key fields blank, or one value stored in different formats across tables; knowledge-base articles nobody has edited in over 12 months [PLAYBOOK ch3]. The 90% rule is for structured decision fields; knowledge-base content is judged by the question test in step 4. All of these thresholds are one author's rules of thumb, not measured cut-offs. Tighten them where a wrong field costs more (a payment amount, a credit limit), and record the thresholds you used.
4. **Knowledge-base audit.** List the 30 to 50 questions or cases the agent will face and check that each has a clear, current answer. Archive retired content, since an agent can't tell a live policy from a retired one unless that is made explicit. Resolve contradictions, or the agent will use one version on some runs and the other on the rest [PLAYBOOK ch3]. The clean-up is a cost line (business-case-and-roi.md §3, knowledge clean-up).
5. **Stable or live.** Stable knowledge (policies, procedures, product documentation) belongs in a knowledge base reviewed on a schedule; volatile data (order status, inventory, balances) is queried live, not cached [PLAYBOOK ch3]. A cached price list quotes old prices; querying static documents live costs latency and money. agent-context-designer designs the retrieval for the sources that pass.
6. **Owners.** Each source has a named owner who reviews it on a schedule: quarterly at minimum, monthly for anything customer-facing [PLAYBOOK ch3]. A rising escalation rate on one topic often means its content has gone stale.
7. **Provenance and lawful basis for personal data.** For every source that holds personal data, scraped or purchased lists included, record where it came from (source, collection date, the source's terms of use), its named owner, the lawful basis or permission for the use the agent will make of it in each region it touches, and any duty to tell the people concerned. Data scraped, bought without clear terms, or used against a source's terms fails the preflight until the data owner and the privacy or legal owner sign off. This skill flags the question and records the answer; the privacy or legal owner decides it, and none of this is legal advice. The architecture side of the same check sits in agent-architect's lifecycle map (Decide gate).

**The gate.** PLAYBOOK's readiness checklist has ten items [PLAYBOOK ch3]:

| # | Item | Ready / needs work / not started |
|---|---|---|
| 1 | Workflow documented: steps, decisions and exceptions | |
| 2 | Write-up reviewed by the person who does the work daily | |
| 3 | Every source the agent will use audited | |
| 4 | Key fields in connected sources at least 90% complete | |
| 5 | Knowledge base answers the top questions the agent will face | |
| 6 | Outdated or conflicting documents removed or archived | |
| 7 | A named owner for each source | |
| 8 | A review schedule for the knowledge base | |
| 9 | Test cases for normal, edge and failure scenarios (agent-eval-designer) | |
| 10 | A human review step defined for agent outputs | |

Step 7 (provenance and lawful basis) is not one of PLAYBOOK's ten items and is not counted against the "two or three" rule: a personal-data source without a recorded basis fails on its own.

If more than two or three items are not ready, narrow the pilot to the workflow with the cleanest data and the clearest documentation rather than delaying the whole project [PLAYBOOK ch3]. Don't connect the agent to a source that failed its audit with a plan to fix it later. A financial services firm that launched on data it knew was poor got wrong answers at machine speed, and repairing trust took longer than fixing the data would have [PLAYBOOK ch3]. Record the result as pass, pass after narrowing (name the slice), or fail.

**Access has a price.** Reaching the data can be a cost line or a blocker. Ng reports a SaaS vendor asking more than $20,000 for an API key to his team's own customer data, and advises buying software that lets you control your data [NG Tear Down Data Silos!, 2025-11-05]. Put the access cost in the case and the export terms in build or buy (business-case-and-roi.md §8).

**Clean data is not a reason to pick a use case.** PLAYBOOK warns the other way too: a bank automated internal reporting because the data was there, the reports changed no decisions, and the failed pilot cut the appetite for the next one [PLAYBOOK ch4]. Choose the use case by value (fit-and-scoring.md); the preflight then decides which slice of it goes first.

## 4. Choosing the control

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

## 5. Timing

- **Stabilisation period first.** Agree 2-4 weeks of tuning before the measurement window opens. The transition dip (J-curve) makes early weeks look worse than steady state [AGENTICAI ch10]. Novelty can make them look better.
- **Measurement window**: at least one full business cycle (month-end, weekly peaks), and long enough for the sample size above.
- Set controls up early. Once a tool is indispensable, people stop accepting the no-agent arm. METR found developers withholding tasks they didn't want to do without AI ([METR 2026](https://metr.org/blog/2026-02-24-uplift-update/), external).

## 6. What to measure

| Kind | Metrics |
|---|---|
| Unit metric | The one in the business case, e.g. cost per resolved request |
| Model drivers | Containment, escalation handling time, wrong-outcome rate and cost, run cost per item: the inputs to the ROI model |
| Guardrails | Reopen rate, CSAT, complaint rate, error rate on sampled items. Must be no worse than control |
| Risk | Failure modes seen, policy violations, incidents, override and escalation rates |
| Adoption | Share of eligible work routed to or used with the agent, user feedback |
| Platform | Tracing coverage, eval suite pass rate, on-call in place, cost metered per agent |

AGENTICAI's balanced scorecard groups these into operational efficiency, employee impact, customer experience and the agent's autonomous handling rate (40% to 75% of cases in six months in its example) [AGENTICAI ch10]. Report against pre-deployment baselines on a fixed cadence. Never use self-reported productivity as the measure.

## 7. Exit and kill criteria (agreed before day one)

Scale only when all three hold [ENTERPRISE ch4]:
- **Proven value**: benefit above a threshold set in advance. Tie it to the ROI model: net value at the measured rates, applied to full volume, at or above the model's net at the agreed containment floor (business-case-and-roi.md §6).
- **Acceptable risk profile**: stable error rates, controlled failure modes, no unbounded failure mode, governance compliance, limited reputational and financial exposure.
- **Platform readiness**: data, infrastructure and support teams can carry production volume.

Also check change readiness (training, process change, frontline adoption) and report to senior management on the same criteria.

**Kill criteria**: the containment kill line from the floor rule (business-case-and-roi.md §6), applied after the tuning period; a wrong-outcome ceiling; any unbounded failure mode. Write them as numbers with dates. Without them the pilot never scales and never dies, which ENTERPRISE calls "pilot purgatory".

## 8. Scaling up

AGENTICAI's insurer is the best worked path in the books [AGENTICAI ch11]: three weeks of process redesign (systems touched cut from seven to three), six two-week sprints with adjusters in every review, then live traffic at 10% in week 1, 25% in week 2, 50% in week 3, 75% in week 4 and full deployment in week 5. The reported results after six months are grade B or C: information-gathering time down 70%, 85% of standard correspondence automated, processing time down 45%.

Gate each stage: metrics stable for the stage window, no new failure mode, comparison with old-way traffic still favourable. Roll back one stage on breach.

**Widen one dimension per stage.** PRODGUIDE's rule keeps a rollout attributable: each stage widens volume, use cases or autonomy, never more than one, or nobody can tell what caused what [PRODGUIDE ch18]. The traffic stages above widen volume only; add request types and autonomy in stages of their own. Its stages:

| Stage | What runs | Judge it on |
|---|---|---|
| 0 Preflight | Boundaries written down: the one-sentence job, a permission tier per tool action, irreversible actions behind approval. Deliverable: a deployment contract readable in two minutes (what the agent may do, will never do, needs approval for, and what success means under the SLA) | Can the owner state the contract? If not, it isn't ready |
| 1 Internal, draft-first | The team's own real work; drafts and payload previews, nothing irreversible | Review minutes per run |
| 2 Limited beta | Small volume, low-risk workflows, approved execution of specific actions; draft-only mode one switch away | Review minutes, p95 latency, tool errors, duplicates and success under the SLA; flip to draft-only on any break |
| 3 Monitored scale | Coverage widens first (categories, teams, sources); autonomy last, for specific low-risk actions | Weeks of low duplicate, error and review rates before any action moves to auto-execute |

PRODGUIDE adds that draft-first systems which are quick to approve often deliver most of the return [PRODGUIDE ch18]. That is practitioner judgment (grade C), but it shapes the case: while approvals stay, review minutes stay in the cost line (`qa_share` 1.0, `qa_min` the review time). Draft-only mode and the kill switch are runtime features; agent-harness-designer designs them, and the plan checks they exist before stage 2.

## 9. Portfolio and platform

The books disagree on per-use-case versus portfolio ROI. ENTERPRISE treats agent ROI as a platform-and-portfolio measure over time [ENTERPRISE ch4]. AGENTICAI argues for an enterprise-wide case but works its example as one department's three-year ROI [AGENTICAI ch10], [AGENTICAI ch11].

**Verdict: fund the platform on the portfolio; judge each agent on its own unit metric with a kill rule.** DBS does both: a shared platform, plus retiring models with no measured benefit. Its shared data platform and AI library cut model delivery from about 12-15 months to 2-3 [ENTERPRISE ch4]. A portfolio argument without per-agent kill rules hides the agents that lose money.

Cadence:
- Monthly: each agent's unit metric, cost per item, and incidents against its business case.
- Quarterly: portfolio review. Retire or rescope agents without measured benefit; reallocate platform cost.
- Platform leading indicators (they show the platform getting faster, not that any agent pays): time from idea to production (JPMorganChase's metric [ENTERPRISE ch4]), share of new agents built on shared actions and templates, active users.

Cost first or revenue first? Pets at Home steers toward revenue because "Cost efficiency is always capped" [AGENTICAI ch12]. Start where measurement is cleanest (cost, time, errors) to earn credibility, but don't rank the whole portfolio on savings. Revenue and quality cases need holdouts and leading indicators while they mature.

Pipeline mix: rank by feasibility, value and demonstration potential, and mix low-risk efficiency projects with stretch ones [MESH ch15].

## 10. Free pilots and outcome pricing

PLAYBOOK prices agent services against the labour they replace, a far bigger budget than software: an agent replacing $5,000 a month of work can charge $1,000 and still leave the client strong value [PLAYBOOK ch7]. Its route to a first client is a 30-day free pilot that shows results before a paid plan [PLAYBOOK ch7].

- **Seller:** the 30-day pilot is a sales device, not a measurement. To turn it into evidence, take the baseline before the month starts, name the unit metric, and add a control or at least a seasonally matched comparison. One month may sit inside the transition dip (§5).
- **Buyer:** a vendor's free pilot read as before/after is grade B at best (business-case-and-roi.md §5). Hold it to the same exit and kill criteria as your own pilot (§7).
- **Price as a ceiling:** an outcome price is worth paying only below the fully loaded cost of the work it replaces, review minutes and wrong outcomes included. Enter how the vendor charges: a price per item in scope goes in `run_cost`; a price per completed item goes in `fee_per_closed`, which the model charges only on items the agent closes, so breakeven stays exact; a per-attempt fee on top goes in `run_cost`. The script then shows whether any net is left.
