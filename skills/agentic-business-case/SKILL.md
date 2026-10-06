---
name: agentic-business-case
description: 'Decide where AI agents belong in an organisation and how to run them. Mode A: pass/fail fit gates, then a 35-point scorecard, a scored shortlist, a one-page business case with a monthly ROI model, sensitivity and evidence grades (A controlled comparison to E vendor claim), and a pilot with a control group, exit/kill criteria and scale gates. Mode B: a governance and operating-model plan covering agent registry, risk tiers and certification, accountability and audit, platform team structure, lock-in and EU AI Act duties dated as of 2026-10. Use for "where should we use AI agents", "build a business case for an agent", "agent ROI", "prioritise agent use cases", "pilot plan", "agent governance", "agent registry", "operating model for agents", "EU AI Act and agents", or an ROI review. Not for agent design (agent-architect), per-request cost (agent-ops-reviewer), security and approval controls (agent-threat-modeler), eval suites (agent-eval-designer), model choice (agent-model-selector), or legal advice.'
---

# Agentic Business Case and Governance

This skill produces one of two things. Mode A is a scored use-case shortlist plus a one-page business case and pilot plan. Mode B is a governance and operating-model plan for an estate of agents. The stance: a business case is a measurement plan with a forecast attached; pass/fail gates outrank scores; most published agent ROI numbers are anecdotes, so the base case runs on the organisation's own measured baseline and every figure carries an evidence grade.

## When to use / when not to

Use when someone wants to:
- find or rank tasks for agents, or check whether a requested agent is the right one;
- build or review a business case, an ROI model or a vendor's ROI claim;
- design a pilot that can prove or kill value, or decide whether to scale;
- set up governance once agents multiply: registry, tiers, certification, owners, platform team, lock-in, EU AI Act.

Hand off instead:

| Need | Skill |
|---|---|
| Agent or workflow? Loop, topology, autonomy design | agent-architect |
| Cost per request, caching, routing, latency (this skill takes run cost as an input) | agent-ops-reviewer |
| Threat model, approval gates, sandboxing, agent identity mechanics | agent-threat-modeler |
| Eval datasets and scorers behind certification and vendor bake-offs | agent-eval-designer |
| Which model, fine-tune or not | agent-model-selector |
| Tool and API contracts | agent-tool-designer |
| Memory, retrieval, context | agent-context-designer |

This skill flags regulatory duties, but it doesn't classify a system legally. Counsel confirms.

## Inputs to gather first

Ask for what's missing. If the user can't answer, proceed on stated assumptions and list them under "Assumptions to verify". Never invent a baseline silently.

**Mode A (use cases, business case, pilot)**
1. The decision, the decider, the budget and the deadline.
2. Candidate tasks, or the department to inventory. For each: volume per month, minutes per item, loaded hourly cost, error or rework rate and cost per error, systems touched and how data is reached (API, UI, export, paper), whether the process is documented, who owns it.
3. What a wrong result costs if nobody catches it, and how errors are caught today.
4. KPIs the business already tracks for this work, and whether a measured baseline exists.
5. Organisational readiness: data platform, observability, existing AI governance, change capacity.
6. Who is affected (customers, employees, applicants), personal data, jurisdiction (EU?), and whether the sector is regulated (bank, insurer, investment firm, lender).
7. Existing vendors, contracts and build-or-buy preferences.

**Mode B (governance)**
1. The estate: number of agents, builders, stacks, what each reads and writes, which are in production, low-code agents included.
2. Existing bodies: risk committee, model risk, change board, data governance, CISO.
3. How model calls and tools are wired today (direct vendor keys? gateway?), and what is logged and for how long.
4. Org shape: business units building agents, central platform team or not.
5. EU exposure: provider or deployer, Annex III areas touched, workplace use, sector regulators.

## Procedure

### Mode A: from candidate tasks to a pilot

1. **Frame.** Write one line: the decision, the budget, the deadline. Define each candidate as a workflow slice with inputs, outputs and a success test, never a job role. Fix scope that is too narrow, too broad or too vague (references/fit-and-scoring.md §1).
2. **Inventory.** Use the workshop questions, or workload mapping with the 20/80 rule for a large department (§2). If the user brought one favourite agent, list 5-10 neighbouring tasks anyway. The requested agent is often not the best opportunity.
3. **Fit gate, pass/fail, before any score.** For each task, ask what an uncaught error costs and whether a wrong result can be caught cheaply before it takes effect. Place it in the quadrant, then apply the hard blockers (§3): tacit knowledge, no authority to act, process not proven or flawed, no data access, no owner. Also ask whether plain code or a fixed LLM workflow would do; if unsure, flag it for agent-architect. Each task gets one result: automate, automate behind a check, assist, keep with people, redesign first, or not an agent. Split tasks that straddle cells (monitoring vs acting; flagging fraud vs deciding fraud). One slice can mix a fixed-workflow path and an agent path (status lookups vs order changes); label each path. Two edge cases: if the check before effect means a person redoes most of the work (re-reading every document), the saving disappears, so model it as approvals on every item and treat the task as assist at best when review takes half the manual time or more; and a use that is high-risk by law (Annex III, consumer credit) is not a blocker by itself but sets tier T3 and adds compliance cost and lead time.
4. **Score the survivors** on the 35-point rubric: impact 20, feasibility 10, effort 5 reverse-scored (§4). Write down the team's definitions of feasibility and effort first. In a large organisation, score time saved relative to the candidate set and record addressable money per month (volume x minutes x rate) as the tie-break. Keep risk tier and EU AI Act flag in separate columns, never folded into the points. Place each task on the matrix (impact vs ease); a task within one point of a cut-off is borderline and is decided on fit result and money, not on the quadrant label. Pick one pilot plus one or two next in line. The pilot should be a quick win whose errors are checkable and whose unit metric the business already tracks.
5. **Readiness** once for the organisation, six dimensions red/amber/green (§5). Each red becomes a cost line or a named risk in every case. A red on governance starts Mode B alongside the pilot.
6. **Business case** for the pick, on templates/business-case.md (references/business-case-and-roi.md):
   - unit of value: a KPI already tracked; baseline measured over a stated period. Exported system history (ITSM, CRM, helpdesk) counts as measured if it covers the business cycle and records effort, not open-to-close elapsed time;
   - separate **baseline facts** (volume, handling time, rate: measure them now) from **pilot uncertainties** (containment, escalation time, error rate and cost: only a pilot measures them) and **estimates** (run cost, platform: get quotes);
   - all cost lines, including humans still in the loop, wrong outcomes, change management, platform share; pilot spend kept apart from the full one-off cost;
   - each benefit labelled capacity or cash, with a destination for freed hours;
   - every figure graded A-E. **The base case uses only the organisation's own baseline plus grade A/B evidence.** C-E go in a labelled context box. If any baseline fact is assumed, head the case "UNVALIDATED: pilot required" and ask only for the pilot spend;
   - run `python scripts/roi_model.py inputs.json` with `currency`, `measured`, `pilot_cost`, `cash_share` and realistic `ranges`. Report capacity-valued net and net cash, payback, pilot spend at risk, breakeven containment, the combined pessimistic case the script builds, the drivers in each group, and its verdict.
7. **Risks and sourcing.** Cover all five risk categories, each with an owner and a mitigation; allocate liability (contracts, logs, insurance). Decide build or buy per layer on differentiation, data sensitivity, staffing and exit options (§7-8).
8. **Pilot** (references/pilot-and-scale.md):
   - choose the control from the decision guide below and size it with n ≈ 16·variance/difference² per arm;
   - run on production data and integrations, with tracing, cost metering and registration;
   - allow 2-4 weeks of stabilisation before the measurement window;
   - write exit criteria (value, risk, platform readiness) and kill criteria as numbers with dates, before day one. Tie them to the model. Set the containment range from evidence before looking at breakeven, and never move it afterwards. If its low end is at least breakeven + 10 points, kill below that low end and set the exit threshold to the model's net there. If it is lower, the case is **pilot only**: fund the pilot spend, kill below breakeven + 10 points, and build no full case until containment is measured. If even its high end is under breakeven + 10 points, the case is **not fundable**. If the combined pessimistic case goes negative, say so; the pilot must measure those drivers before any scale decision.
9. **Scale and portfolio.** Roll out in stages (10 → 25 → 50 → 75 → 100%), comparing each stage with traffic still handled the old way. After launch, review the unit metric monthly and the portfolio quarterly; retire agents with no measured benefit. Fund the platform on the portfolio, but judge each agent on its own metric.
10. **Check regulation** for the pick (step 6 of Mode B, applied to one use case) and put duties and dates in the case.

### Mode B: governance and operating model

Use references/governance-operating-model.md and templates/governance-plan.md.

1. **Size the estate and the trigger.** Inventory every agent, low-code ones included. Governance becomes necessary when the first agent writes to a system of record or a second team builds agents. Plan a day-1 minimum and later additions; don't prescribe the full apparatus for three agents.
2. **Register.** Set up four registries: agent, action catalog, model, prompt/config. Use the agent-registry minimum schema. Make registration a deploy-pipeline step, and have the control plane refuse unregistered agents.
3. **Tier and certify.** Put every agent in T0-T3. The tier sets certification depth, approvals, recertification cadence and what the control plane passes. Bind each certificate to version plus configuration fingerprint. Recertify on model, prompt or tool change, on expiry, and on error-budget breach; pin model versions.
4. **Enforce and prove.** Agents get no direct path to models, systems of record or each other. The gateway checks registration, certification and allowed tools on every call, enforces cost ceilings, and writes traces with version and owner to tamper-evident storage. Agent identity and per-action approval mechanics go to agent-threat-modeler.
5. **Assign accountability.** Name an owner for each of the four areas. Give every agent a business owner and a safety owner. For T2/T3 agents, answer the five second-layer RACI questions and say where code enforces each one. Handle liability through contracts, logs and insurance.
6. **Regulation.** Screen each use case: prohibited practice? Annex III? Art. 6(3) derogation (never with profiling)? Provider or deployer? Art. 50 disclosure? Map each duty to a registry field, trace, oversight assignment or workforce step, with its date (references/eu-ai-act-2026-10.md). Compare each date with today's date and mark it "applies now" or "from <date>". For regulated sectors (banking, insurance, investment services, credit), add the sector regimes from §7 of that file. Mark the result "not legal advice; counsel to confirm".
7. **Operating model.** Central platform, federated builders: the platform team owns gateway, registry, eval framework and paved road; business units own domain agents and KPIs; enabling teams own standards and reviews. Extend existing committees before creating new ones, and make every committee decision end as a registry field. Fill roles before creating new job titles.
8. **Lifecycle.** Define states and transitions. At intake, reject tasks a plain program does better. At retirement, revoke credentials, archive the record and logs, and notify users. Reconcile live credentials against the registry on a schedule.
9. **Portability.** Put a neutral model access layer in place. Separate prompt intent from model-specific wording and run evals per target model. Make eval assets exportable and put tools behind open contracts. Test: could one agent move provider within a sprint?
10. **Workforce.** Augmentation first. Inform workers (and their representatives) before workplace deployment. Give people an appeal path for agent decisions affecting role or pay, plus reskilling and a transition council.
11. **Sequence** the plan in phases with exit checks. For an existing estate: put the gateway in front first, then migrate one agent at a time, highest risk first.

## Decision guide

**Fit quadrant: what to build**

| Uncaught error cost | Checkable before effect? | Build | Watch out for |
|---|---|---|---|
| Low | Yes | Autonomous agent with monitoring | Proving the agent beats plain automation on cost |
| High | Yes | Agent behind a coded check or human approval | Approval fatigue; caps must live in code; if a person must redo the work to check it, cost approvals on every item |
| Low | No | Assist: agent drafts, people sample | Sampling rate too low to spot drift |
| High | No | Keep with people; at most evidence-gathering | High impact scores that tempt you past the gate |

**Choosing the pilot control**

| Situation | Control | Why | Watch out for |
|---|---|---|---|
| High volume, capped errors | Random split | Same period, same mix | Routing must be random, not agent-chosen |
| Several comparable teams or sites | Staggered rollout | Handles seasonality | Spillover between teams |
| Moving volume over anyway | Staged 10/25/50/75/100%, each stage vs old-way traffic | Speed and rigour together | Skipping stages while unstable |
| Revenue or retention outcome | Customer holdout | Slow, noisy effects | Holdout too small or too short |
| Low volume, high stakes | Shadow mode | Accuracy with no exposure | Proves accuracy, not value |
| Nothing else possible | Seasonally matched before/after | Better than nothing | Grade B at best |

**Evidence grade: how to use a number**

| Grade | Example | Use |
|---|---|---|
| A controlled comparison | Cohort split, staggered rollout | Forecast, with interval |
| B before/after, live system | Ticket counts pre/post go-live | Direction; check seasonality and peak baselines |
| C practitioner case | Consultant's "285% ROI" | Proof it can be done; not in base case |
| D survey or self-report | "Developers felt 20% faster" | What people believe |
| E vendor or press claim | "Up to 50%" | Upper bound at best |

**Governance weight by tier**

| Tier | Agent does | Gate | Recertify |
|---|---|---|---|
| T0 | Reads, drafts for the requester | Register + automated checks | Change; 12 months |
| T1 | Proposes actions a person approves | + eval suite + platform review | Change; 12 months |
| T2 | Acts within coded caps; customer-facing | + full certification, two owners, error budget, kill switch | Change; 6-12 months; budget breach |
| T3 | Decisions on people, safety, large money, EU high-risk | + independent validation, legal sign-off, regulatory duties | Change; 6 months |

**Disagreements in the sources, resolved**

| Question | Position to take | Why |
|---|---|---|
| What should the first project prove? | Narrow scope, production-shaped plumbing | Demo-data pilots prove nothing about scale; networks of agents blur attribution |
| Per-agent or portfolio ROI? | Fund platform on portfolio; each agent keeps a kill rule | Portfolio-only hides losing agents |
| Cost or revenue first? | Start where measurement is cleanest; don't rank on savings alone | Revenue cases need holdouts and time |
| How heavy should governance be? | Tier it | No source measures governance cost or benefit; one weight fits nobody |
| Is a natural-language policy a control? | No; enforce in code, write prose for people and tests | Instructions get dropped, e.g. under context compression |

## Output

**Mode A**: return, in this order:
1. **Shortlist**, filled from templates/use-case-shortlist.md: readiness, fit gate table, scores, recommendation.
2. **Business case**, filled from templates/business-case.md: the one-page table, evidence table, model inputs and pasted script output, pilot plan.
3. **Governance**: if the user asked for governance, a condensed Mode B plan (templates/governance-plan.md sections sized to the estate). Otherwise a starter, only if readiness shows governance red or agents already run unregistered: the Mode B day-1 minimum as dated actions with owners, plus any regulatory duty that already applies.
4. **Assumptions to verify**: each with how and when it gets measured.
5. **Open questions** for the sponsor (at most five).

Keep the one-page table to one page.

**Mode B**: templates/governance-plan.md filled in, sized to the estate, plus assumptions and open questions.

**Review of someone else's case or ROI claim**: grade each figure, run the add-back test, list missing cost lines, missing control and missing kill criteria, and give a verdict: fundable as is, fundable as a pilot only, or not fundable, with reasons.

## Quality bar

Before returning, check:
- [ ] Every candidate is a workflow slice with a success test, not a role.
- [ ] The fit gate ran before scoring, and no task that failed a hard blocker has a score.
- [ ] Risk tier and regulatory flag sit in their own columns, not in the points.
- [ ] The unit of value is an existing KPI; the baseline is measured with a stated period, or marked unmeasured with a plan.
- [ ] Cost lines include humans still in the loop, wrong outcomes, change management and platform share as well as model cost.
- [ ] Each benefit is labelled capacity or cash; freed hours have a destination.
- [ ] Every number carries a grade; the base case holds no C-E figures.
- [ ] Inputs are marked measured or assumed. If any baseline fact is assumed, the case is headed "UNVALIDATED: pilot required" and asks only for the pilot spend, however the checklist otherwise looks.
- [ ] The containment range was set before breakeven was known; the funding verdict (fundable, pilot only, not fundable) follows the floor rule.
- [ ] Numbers come from the script, not mental arithmetic; the largest pilot-uncertainty drivers are named and the pilot measures them; baseline facts are measured, not left to the pilot.
- [ ] The pilot has a control, a stabilisation period, a sample-size estimate, and exit and kill criteria tied to the model.
- [ ] All five risk categories have owners; liability is allocated.
- [ ] (Mode B) Every committee decision maps to a registry field or a control-plane check; tiers set certification weight; retirement revokes credentials.
- [ ] EU AI Act dates come from the reference file (Annex III from 2 Dec 2027, Annex I from 2 Aug 2028, Art. 50 from 2 Aug 2026), each marked "applies now" or "from <date>"; regulated sectors list their sector regimes; the "not legal advice" note is present.
- [ ] Sibling skills are named where their work starts.

## Common mistakes

| Mistake | Fix |
|---|---|
| Quoting industry statistics ("30-50% cost reduction", "285% ROI") as the forecast | Grade them; keep C-E out of the base case; forecast from the user's baseline |
| Filling unknown baselines with plausible numbers | Mark every input measured or assumed; make measuring the baseline pilot week 0 |
| Letting a high score override the gate (high-volume, high-stakes tasks score well) | Gate first; costly and uncheckable tasks become assist or stay with people |
| Treating the model bill as the main cost | Model escalations, QA, wrong outcomes and platform share; run the sensitivity |
| Counting freed hours as savings | Capacity unless hiring, overtime or contractors actually fall |
| Accepting before/after as proof | Require a control; label before/after grade B |
| Reading the pilot in week two, or at the novelty peak | Stabilisation period, then a full-cycle measurement window |
| Pilot with no kill rule | Containment floor and error ceiling, dated, before day one |
| First pilot as a multi-agent network on demo data | One bounded use case on real plumbing; platform effects from cases two and three |
| Governance as documents and meetings | Registry plus control-plane refusal; decisions become fields |
| MESH-style certification for every read-only helper | Tier it |
| Writing "the agent must not..." in the prompt and calling it a control | Enforce in tools and orchestration |
| Pre-Omnibus EU dates (Annex III in Aug 2026) or confident legal conclusions | Use the reference file's dates; mark "not legal advice; counsel to confirm" |
| False precision ("ROI 284.7%") | Ranges and scenarios, with the drivers named |
| Moving the containment range until the floor test passes | Set the range from evidence first; a low end under breakeven + 10 points means pilot only |
| Using ticket open-to-close time as handling time | Baseline is person-minutes of effort; elapsed time overstates it |
| Pushing volume, rate and handling time to their bad ends in the pessimistic case | Those are facts to measure; the pessimistic case moves pilot uncertainties and estimates only |
| Treating a "net value" built from freed hours as savings | Report capacity-valued net and net cash side by side |

## Sources

Distilled from these books (chapter numbers as in the original editions):
- *The Agentic Enterprise* (ENTERPRISE): ch2 value layers, fit and readiness; ch3 applications and figures; ch4 ROI, five risk categories, build vs buy, pilot and scale criteria; ch5 where to start; ch6 central registry and configuration hash; ch7 accountability, second-layer RACI, compliance logging; ch8 action catalog, neutral gateway, prompt portability, central platform with federated builders; ch9 mass-review cost case.
- *Agentic Artificial Intelligence* (AGENTICAI): ch1 adoption study; ch8 Three Circles, 35-point scorecard, prioritisation matrix; ch9 agent business models; ch10 four-part business case, balanced scorecard, governance council, J-curve; ch11 workload mapping, insurer business case and staged rollout; ch12 Pets at Home case.
- *Agentic Mesh* (MESH): ch5, ch7, ch8, ch9 registry and certification; ch12 trust framework; ch13 operating model, team roles, transition; ch14 factories and templates; ch15 roadmap.
- *Building Applications with AI Agents* (BUILDAPPS): ch1 organising for success; ch2 scoping a first agent; ch13 trust, governance, compliance.
- *AI Evals in Practice* (EVALS): ch12 lock-in checklist; ch13 incident-cost argument; ch15 running a shared platform.
- *AI Agents with MCP* (MCP): ch9 registries and gateways. *Systems Thinking for Agentic AI* (SYSTEMS): ch18 trust classes. *Designing Large Language Model Applications* (DLLMA): ch1.

External (fetched 2025-2026): Anthropic, Building effective agents, https://www.anthropic.com/engineering/building-effective-agents · METR 2025 study, https://metr.org/blog/2025-07-10-early-2025-ai-experienced-os-dev-study/ and 2026 update, https://metr.org/blog/2026-02-24-uplift-update/ · Brynjolfsson, Li, Raymond, NBER w31161, https://www.nber.org/papers/w31161 · Gartner forecast as reported, https://techresearchonline.com/news/gartner-agentic-ai-projects-termination-forecast/ · EU AI Act timeline, https://artificialintelligenceact.eu/implementation-timeline/ · Orrick on the Digital Omnibus, https://www.orrick.com/en/Insights/2026/07/EU-AI-Act-Update-Digital-Omnibus-Finalizes-8-Compliance-Changes · AI Act Articles 6, 12, 26 and Annex III at artificialintelligenceact.eu · MCP Registry, https://modelcontextprotocol.io/registry/about · A2A agent discovery, https://a2a-protocol.org/latest/topics/agent-discovery/ · NIST NCCoE agent identity concept paper, https://csrc.nist.gov/pubs/other/2026/02/05/accelerating-the-adoption-of-software-and-ai-agent/ipd
