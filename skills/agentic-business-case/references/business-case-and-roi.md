# Business case, ROI model and evidence grades

Load this for steps 6-7 of Mode A, or when checking someone else's ROI claim.

A business case is a measurement plan with a forecast attached. The forecast gets the project funded; the baseline and the control are what let you decide later. No generic ROI template survives contact with a real use case. Define your own units of value, make the agent measurable against them, and promote only agents that show value within acceptable risk [ENTERPRISE ch4].

## 1. What goes in

Combine AGENTICAI's four-part case [AGENTICAI ch10] with ENTERPRISE's unit-of-value, platform-allocation and exit-criteria fields [ENTERPRISE ch4]:

| Part | Content |
|---|---|
| Success metric first | Set the target before any design (AGENTICAI's newsletter project: creation time from 15 to 3 hours a week [AGENTICAI ch8]) |
| Quantitative benefits | Unit of value x volume, net of every cost line below |
| Qualitative benefits | Consistency, traceability, employee and customer experience, resilience. Measure them; don't price them unless you can |
| Costs | All seven lines in §3, including change management and the transition dip |
| Risks | Five categories (§7), each with an owner and a mitigation |
| Measurement | Baseline, control design, window (see pilot-and-scale.md) |
| Exit and kill criteria | Written before the pilot starts |

**Value layers** [ENTERPRISE ch2]: (1) operational productivity, (2) outcome quality and resilience (consistent, logged, traceable decisions), (3) new business models, which the book itself calls nascent. A first agent's case claims layer 1 in the numbers, measures layer 2, and keeps layer 3 in the narrative.

## 2. Unit of value and baseline

Pick a unit the business already tracks so nobody can dispute the baseline, and so the agent shows up in KPIs leaders already watch [ENTERPRISE ch5]. Candidates from ENTERPRISE ch4: decisions automated, hours of human work avoided, risk incidents prevented, line-hours recovered, incremental revenue. Good units are per item: cost per resolved request, cycle time per claim, errors per 1,000 invoices.

Baseline rules:
- Measure it; don't estimate it. If it isn't measured yet, the first pilot task is to measure it, and the case says so.
- State the period: at least 4-8 weeks, covering the business cycle (month-end, seasonal peaks).
- Exported system history (ITSM, CRM, helpdesk, workflow logs) counts as a measured baseline when it covers that period and records person-minutes of effort per item, not open-to-close elapsed time. Mark those inputs measured; no new measurement window is needed. If the history holds only elapsed time, sample effort for a few weeks before the pilot.
- Keep three kinds of input apart. **Baseline facts** (volume, handling time, rate) exist today: measure them before the pilot. **Pilot uncertainties** (containment, escalation time, error rate and cost, review load) only a pilot can measure. **Estimates** (run cost, platform share) come from quotes. A case whose baseline facts are assumed is **unvalidated**: it can ask for pilot spend, never for the full build.
- Measure the guardrail metrics too (reopen rate, CSAT, error rate), so the agent can't buy the unit metric with quality.
- Self-reported time ("I spend 60-70% on admin") is a lead for where to look, not a baseline.

## 3. Cost lines (total cost of ownership)

| Line | Notes |
|---|---|
| Build and integration | Integration with systems of record usually dominates. For Siemens it was MES, SCADA, PLC and ERP integration, justified only by reuse across many lines and plants [ENTERPRISE ch4] |
| Change management and training | One insurer put 40% of its budget here [AGENTICAI ch10] |
| Transition dip | Productivity falls while people learn to work with agents, then rises: a J-curve [AGENTICAI ch10]. Cost it as lost output in the first weeks |
| Humans still in the loop | Escalated items, QA sampling, approvals. Usually the largest running line. If a person approves every item, cost the approval at full review minutes on every item (`qa_share` 1.0); when review takes half the manual time or more, the saving is gone (fit-and-scoring.md §3) |
| Wrong outcomes | Error rate x cost per error: refunds, rework, goodwill, regulatory exposure |
| Running cost per item | Model, tools, infra. Get it from agent-ops-reviewer; usually the smallest line in support-style work |
| Platform share | Allocated data, orchestration, governance, monitoring, on-call [ENTERPRISE ch4] |
| Knowledge clean-up | Conflicting source documents: people resolve them, an agent silently picks one or blends both [AGENTICAI ch12]. Audit and fix before the pilot |

## 4. Capacity versus cash

Freed hours are capacity. They become cash only when hiring stops, overtime ends, contractors leave, or people move to revenue-earning work. AGENTICAI's insurer case turns 45,000 person-hours a year into "$3.2 million in direct cost savings" [AGENTICAI ch11]; that is only true if the organisation acts on the hours. Every case labels each benefit capacity or cash and names where freed hours go (a backlog, a hiring freeze, redeployment). Announce redeployment early: job-loss fear is an organisational risk [ENTERPRISE ch4].

## 5. Evidence grades

Grade every number before it goes into a slide. The books mix grades freely and rarely say which is which.

| Grade | What it is | Use it as | Example |
|---|---|---|---|
| A. Controlled comparison | Random split, staggered rollout or holdout; measured outcome | A forecast, with its confidence interval | DBS compares with-AI and without-AI cohorts per use case and retires models with no measured benefit; the book describes the method but gives no figures [ENTERPRISE ch4] |
| B. Before/after on a live system | Same metric pre and post, no control | Direction and rough size; check seasonality, peak-month baselines, channel shifts | ENTERPRISE's intranet ticket chart: peak month right before go-live, December as the end point [ENTERPRISE ch3] |
| C. Practitioner case | Authors' or consultants' own engagements, method not shown | Proof that something is possible | 285% three-year ROI for the insurer [AGENTICAI ch11]; 40-50% migration savings with unsized phases [ENTERPRISE ch3] |
| D. Survey, self-report, early company figure | Respondent counts, perceived productivity | What people do or believe | A 167-company study that sampled only "successful implementations" [AGENTICAI ch1]; earnings-call mentions counted as adoption [DLLMA ch1] |
| E. Vendor or press claim | Press release, conference talk, "up to" figures | An upper bound at best | Vendor-reported insurance and asset-management results [ENTERPRISE ch2]; Siemens's "up to 50%" ambition [ENTERPRISE ch4] |

Rules:
- **The base case uses only the organisation's own measured baseline plus grade A or B evidence.** C-E numbers go in a context box, labelled.
- In the books the most rigorous method (DBS's cohorts) comes with no numbers, and the largest numbers come with the weakest methods. Expect that pattern elsewhere.
- Red flags: survivorship ("companies with agents in production"); self-reported speed-ups; a before/after starting from a peak month; percentages with no denominator; "up to"; ROI with no cost lines shown; three-year ROI from a pilot.
- **Add-back test**: add back what a comparison omits (build cost, calibration, review time) and see if the conclusion changes. ENTERPRISE's hackathon judging (~$7,000 compute vs 15,000+ person-hours of review) survives it, since the hours cost tens of times the compute at any plausible rate [ENTERPRISE ch9]. A figure that can't be recomputed from what's given stays grade C.

**Published evidence worth knowing (external, as of 2026-10)**
- METR randomised trial, 2025: 16 experienced open-source developers took 19% longer with AI tools, yet believed they were 20% faster ([METR 2025](https://metr.org/blog/2025-07-10-early-2025-ai-experienced-os-dev-study/)). A 2026 follow-up (57 developers, 800+ tasks) moved estimates to 18% and 4% less time, both intervals including zero, and found 30-50% of developers withholding tasks they didn't want to do without AI ([METR 2026](https://metr.org/blog/2026-02-24-uplift-update/)). Lesson: never use perceived productivity, and set controls up before the tool becomes indispensable.
- Brynjolfsson, Li and Raymond: 5,179 support agents, staggered access to an AI assistant, +14% issues resolved per hour on average, +34% for novices, little change for the most experienced ([NBER w31161](https://www.nber.org/papers/w31161)). An assistant, not an agent, but the design to copy: staggered rollout as control, an existing unit metric, effects split by group.
- Gartner (June 2025) forecast that over 40% of agentic AI projects will be cancelled by end of 2027 for cost, unclear value or weak risk controls, and that only about 130 of thousands of "agentic" vendors are real ([as reported](https://techresearchonline.com/news/gartner-agentic-ai-projects-termination-forecast/), 2026-08). A poll-based forecast, grade D; the three causes map onto the three exit criteria.

## 6. The monthly model

Run `scripts/roi_model.py` (Python standard library only). With no argument it runs a demo and self-check; with a JSON file of inputs it models your case. Inputs:

| Key | Meaning | Where it comes from |
|---|---|---|
| volume | items per month in scope | baseline fact: system counts |
| human_min | person-minutes of effort per item today, not open-to-close time | baseline fact: measured or system history |
| rate | loaded cost per person-hour | baseline fact: finance |
| contained | share the agent closes with no person (0 for assist-only) | pilot uncertainty |
| escalated_min | person-minutes per item the agent doesn't close (for assist mode, the new handling time) | pilot uncertainty; often higher than human_min once the easy items are gone |
| qa_share, qa_min | share of agent-closed items a person checks (1.0 if every item needs approval), minutes each | pilot uncertainty; QA plan |
| run_cost | agent cost per item | estimate: agent-ops-reviewer |
| err_rate, err_cost | wrong outcomes per closed item, cost each | pilot uncertainty; finance or risk for cost |
| platform | monthly platform share, monitoring, on-call | estimate: platform team |
| pilot_cost | one-off spend before the scale decision; the money at risk if the pilot is killed | estimate |
| build | total one-off cost to full deployment, pilot included: build, integration, change management, training | estimate |
| cash_share | share of freed hours that turns into cash (hiring stopped, overtime or contractors cut) | the plan for freed hours; 0 until someone commits to it |
| currency | label for every amount, e.g. "EUR" | |
| measured | list of inputs backed by own data | mark honestly; the verdict depends on it |
| ranges | realistic low/high per input, set from evidence before you look at breakeven | your judgment; default x0.5..x2; `contained` has no default |

It prints baseline cost, each cost line, capacity freed (hours and FTE, labelled capacity, not cash; negative when the agent adds human work), net per month valued at capacity and as cash, payback, pilot spend at risk, breakeven containment and the floor, the combined pessimistic case, sensitivity tables per input group sorted by swing, and a verdict. Varying `human_min` scales `escalated_min` with it, since escalated items get faster or slower with the work itself.

What the demo shows (20,000 items, 5 min, $40/h, 70% contained): net about $29,900/month, payback 4 months. Model cost x5 cuts net by about 11%; containment 70% to 40% cuts it by about 55%; wrong-outcome cost $25 to $100 cuts it by about 70%. **Containment, escalation time and the cost of a wrong outcome usually decide the case; the model bill rarely does.** Token price starts to decide it when the replaced work is cheap per item or the agent makes many calls per item; hand that to agent-ops-reviewer. The pilot must measure the top drivers in the pilot-uncertainty group well. Baseline facts at the top of their own table get measured before the pilot, not left to it.

Use the outputs to set thresholds, in this order. First set the realistic containment range from evidence (a shadow run, a sample of tickets the agent could close, a comparable deployment), then read breakeven. Never move the range afterwards to pass the test. The floor rule:

| Realistic containment range | Verdict | Kill line |
|---|---|---|
| Low end ≥ breakeven + 10 points | Fundable: pilot now, scale on exit criteria | Below the low end; exit threshold = the model's net there |
| Low end below that, high end ≥ breakeven + 10 points | Pilot only: fund `pilot_cost`, no full build until containment is measured | Below breakeven + 10 points |
| High end < breakeven + 10 points | Not fundable: the pilot could not pass its own kill line | None; don't start |

Any assumed baseline fact turns "fundable" into "pilot only" and heads the case "UNVALIDATED: pilot required". The script applies these rules and prints the verdict. It also builds the combined pessimistic case: pilot uncertainties and estimates at their bad ends, baseline facts held, because measuring settles them. If that case goes negative, say so; the pilot must measure those drivers before anyone decides to scale.

**Risk-reduction cases**: price the incidents prevented. EVALS funds evaluation work from incident cost: about 12 engineering hours per incident, three a quarter, $150 an hour, so $5,400 a quarter in direct cost before user impact [EVALS ch13].

## 7. Risks: five categories [ENTERPRISE ch4]

| Category | What it looks like with agents | Typical mitigation |
|---|---|---|
| Strategic | Committing to the wrong platform or vendor, or investing too little relative to competitors | Build/buy per layer, gateway and portable contracts, small reversible first step |
| Organisational | Skills gaps, job-loss fear, shadow AI built outside governance | Redeployment plan announced early, training budget, central registration |
| Governance and compliance | Hallucination, bias, data leakage, weak explainability, different rules per country | Evals, guardrails, logging, regulatory screening (eu-ai-act-2026-10.md) |
| Operational | Errors compounding across interacting agents at volume | Caps in code, reconciliation, staged rollout, kill switch |
| Liability | An agent's decision causes loss or a breach. Agents are tools, so liability sits with the deployer, its decision-makers and vendors | Contracts that allocate responsibility, documented oversight, audit logs, insurance. A tribunal held Air Canada responsible for a fare policy its chatbot invented [AGENTICAI ch11] |

## 8. Build or buy, per layer [ENTERPRISE ch4]

Four criteria per layer: is it differentiating or available on the market; data sensitivity and regulation; can you staff and run it for years; interoperability and exit options.

| Layer | Default | Why |
|---|---|---|
| Base models, cloud, commodity tools | Buy | Not differentiating |
| Model access gateway | Build thin or buy neutral | Must stay vendor-neutral; it's your exit route |
| Orchestration, guardrails, policy | Build or tightly shape | Once systems act, this carries your risk policy, and coupling to one vendor's framework raises switching costs |
| Domain agents, prompts, tool contracts | Build | Business logic and data |
| Fine-tuned models on own data | Build if justified (see agent-model-selector) | Proprietary asset |
| Evaluation assets | Own, whatever tool runs them | Must export: datasets, annotations, per-case results, scorer configs [EVALS ch12] |

A well-built internal agent can be reused across units or sold; Siemens plans to sell industrial agents through a marketplace [ENTERPRISE ch4]. Count reuse only when a second consumer is committed.

Before buying a product sold as an "agent", run a bake-off on your own eval set (agent-eval-designer). Many such products are rebadged chatbots.

## 9. When the agent is the product

If the user sells agents rather than uses them, the economics differ: agent-as-a-service sells an outcome, not a tool [AGENTICAI ch9]. Map the customer's value chain (handoffs, decision nodes), pain points, capability fit and integration effort. Treat capability demos as capability evidence, not business-model evidence: AGENTICAI's eight-hour autonomous "start a business" run reports no sales [AGENTICAI ch9].
