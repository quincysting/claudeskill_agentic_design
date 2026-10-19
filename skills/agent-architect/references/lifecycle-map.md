# Lifecycle map: from decision to production

Citation keys such as [PLAYBOOK ch2] point to the book list under Sources in SKILL.md; a citation that starts with NG names an Andrew Ng letter listed there by title and date.

Start here when the work spans more than one design question: a new agent from idea to production, or a review of an agent that already runs. The map has three parts. Four **stages** order the work. Eight **perspectives** cut across every stage, and each has exactly one owner skill, so nothing gets designed twice. A **gate** closes each stage: a short list of exit criteria, each supplied by a named skill. The team moves on only when the gate passes. Without the gates the nine skills are separate reviews; the gates join them into one path.

This skill owns none of the eight perspectives. It owns the shape and authority of each step, the loop contract, sizing and this map. Read it first, at Decide, to plan the calls. At Design it produces the architecture, and at Run its rollout plan says how each step's authority is raised.

## The four stages

| Stage | Question it answers | Skills that lead | Leaves behind |
|---|---|---|---|
| Decide | Is this worth building, and how much autonomy can it start with? | agentic-business-case (concreteness, data readiness, starting level, business case); agent-tool-designer (usable APIs); agent-eval-designer (eval budget) | A concrete one-sentence use case, a fundable case or a pilot-only verdict, a scored starting level |
| Design | What shape, what authority, which controls, which models? | agent-architect, agent-threat-modeler, agent-model-selector; agent-tool-designer (tool boundaries) | An architecture design doc with the loop contract, a threat model with permission tiers, a model plan |
| Build | Do the tools, the runtime and the knowledge hold the design? | agent-tool-designer, agent-harness-designer, agent-context-designer, agent-eval-designer (first suite) | Tool contracts, a harness design, a retrieval and memory spec, a smoke suite and a baseline |
| Prove and run | Does it work, and can it run and widen safely? | agent-eval-designer, agent-threat-modeler (red team), agent-harness-designer (harness tests), agent-ops-reviewer (Run gate) | A release decision, a readiness review, live monitoring, a rollout with promotion and rollback rules |

Prove and run has two gates: Prove before launch, and Run before each rollout stage and each widening of autonomy.

## Perspectives and their owners

| Perspective | Owner | Others that feed it |
|---|---|---|
| API contracts (tools are APIs; the agent is an API) | agent-tool-designer | agent-harness-designer for the agent's own service endpoint |
| Tool access | agent-threat-modeler | agent-tool-designer defines the per-tool scopes and permission tiers that the threat modeler audits |
| Harness | agent-harness-designer | agent-architect writes the loop contract the harness enforces |
| Guardrails | agent-threat-modeler | agent-eval-designer measures false passes and false blocks |
| Evals | agent-eval-designer | agent-ops-reviewer runs the online signal |
| Security hardening | agent-threat-modeler | agent-tool-designer for MCP server contracts |
| Context and knowledge | agent-context-designer, from Design on | agentic-business-case runs the data readiness audit at Decide; agent-eval-designer for retrieval scoring |
| Cost and operations | agent-ops-reviewer: cost per successful run, at run level, human review minutes included | agentic-business-case for ROI, payback and the funding verdict; agent-model-selector compares configurations on cost per solved task; agent-architect sets per-run caps and sizing |

agent-model-selector owns no perspective; it supplies the Design gate's model per role.

## What each perspective asks at each stage

| Perspective | Decide | Design | Build | Prove and run |
|---|---|---|---|---|
| API contracts | Does a usable API exist for every system the agent must touch, or is the gap named and costed? | Tool boundaries, read versus write, what each tool returns | Contract fields: receipts, failure categories in one error format, idempotency key, permission tier, versioning, valid next actions in results | Schema diff and contract tests in CI, a tool inventory with owners, a retirement plan for old versions |
| Tool access | Rule of Two triage: does any run need untrustworthy inputs, access to sensitive systems or private data, and the ability to change state or communicate externally at once? A change to a sensitive system (a merge, a deploy, a payment) counts even when no private data is involved | A permission tier per action (read-only, draft-only, execute with approval, auto-execute); separate identities to recommend, prepare and execute | Token exchange per hop; effective scope is the granted scope intersected with the user's entitlements; tools named server::name | Per-call authorisation audit; the same call tried under two identities; consent review |
| Harness | Framework or own loop, and what leaving it would cost | The loop contract: decision contract, budgets, stop rules, exit statuses, approval pauses | Run record, durable state, checkpoints, budgets checked before every model and tool call, streaming, cancellation, kill switch and draft-only mode, deployment shape (request, event, schedule) | Resume, stop, budget, cancel and kill-switch tests; safe-mode replay; a harness bake-off with the model held fixed |
| Guardrails | Risk sits in the application, not in the model | Three layers (prompt, input and output screening, hard limits in code); fail-open or fail-closed declared per check | Input and output guardrails, tool-output validation, provenance gate, egress allowlist | False-pass and false-block rates; red-team seeds |
| Evals | Which decision the evals serve; eval cost and wall time as a budget line | Quality dimensions and hard checks | A first smoke suite (10 normal, 10 edge, 10 adversarial), a golden run and a baseline; error analysis | Hard checks on a held-out split as the release gate; judge calibration; online signal |
| Security hardening | Data classes and regulation | STRIDE per element on a data-flow diagram; OWASP Agentic Top 10 and MAESTRO mapping | MCP hardening: definition pinning, supply chain, loopback binding, encryption on every hop, signed releases | Red-team plan, incident kill switch, disclosure contact |
| Context and knowledge | The data readiness audit (agentic-business-case); the same sources checked for retrieval quality (agent-context-designer) | Vector, graph or hybrid retrieval by query type; a governed memory schema | Retrieval pipeline, ingest checks, cache-friendly context layout | Retrieval and memory evals; freshness checks |
| Cost and operations | ROI, payback and the funding verdict (agentic-business-case) | Per-run caps (tokens, calls, retries, steps) and sizing at volume; cost per solved task per model configuration | Tracing; cost per successful run, review minutes included | Readiness gate, p50 and p95, canary, alarms with sample floors |

Five notes on the matrix:
- **Harness bake-off.** The harness can matter as much as a model upgrade on some tasks, or not at all. The one controlled comparison so far, a single-author preprint (Arjmandi, arXiv 2609.11987, 2026-09, https://arxiv.org/abs/2609.11987), found no reliable average gap, gaps that varied by task family, and a 1.2 to 1.6x difference in cost per solved task. Hold the model fixed, vary the harness, and expect no fixed gain.
- **Smoke suite.** A 30-case first suite is a smoke test, not a release gate: 27 of 30 passing gives a 95% interval of roughly 74 to 97%.
- **Data readiness.** The audit uses the documentation test for knowledge articles (hand them to someone who does not do the job, and fix them wherever that person gets stuck), a rule that structured fields used for decisions or customer-facing output be at least 90% complete and accurate, and warnings for stale content and blank fields [PLAYBOOK ch3]. The 90% rule does not apply to knowledge articles. When the user's own facts already fail it (half the case files missing fields the decision uses), the Decide gate fails now; it is not an open item to design around. Narrow the pilot to the slice that passes, or put the data fix in Decide. An agent step that flags missing data does not replace the audit or the narrowing. For personal data the audit also records provenance (source, collection date, the source's terms), the lawful basis or permission for the intended use in each region, and the notice duties that follow. Data scraped from a site, or taken against a source's terms, fails the gate until the data owner and counsel sign off; agentic-business-case holds the legal analysis.
- **Decide questions without a Decide call.** The Tool access and Harness rows ask questions at Decide (the Rule of Two triage; framework or own loop), but their owners are first called at Design and Build. agent-architect raises both at step 0 and records the answers as constraints; agent-threat-modeler and agent-harness-designer answer them in full later.
- **Where risk sits.** Ng's framing: safety is a property of applications, not of models, so the same model can be harmless in one product and dangerous in another [NG Blenders Versus Bombs, or Why California's Proposed AI Law is Bad for Everyone, 2024-06-05]. Assess and guard the application.

## Stage gates (exit criteria)

| Gate | Exit criterion | Supplied by |
|---|---|---|
| Decide | The use case passes the concreteness test: a team could build a first prototype from its one-sentence description [NG Concrete Ideas Make Strong AI Startups, 2024-07-24] | agentic-business-case; agent-architect's responsibility sentence is the same sentence |
| Decide | The data readiness audit passed (for personal data: provenance, lawful basis per region and notice duties recorded and signed off), or the pilot is narrowed to the slice that passes | agentic-business-case; agent-context-designer checks the same sources for retrieval quality |
| Decide | A starting autonomy level scored on volume, variability, risk, judgment and action scope, with any factor at 1 named as a constraint [PLAYBOOK ch2] | agentic-business-case; agent-architect turns it into authority per step at Design (autonomy-and-shape.md) |
| Decide | The business case is fundable, or the work is a pilot only | agentic-business-case |
| Decide | A usable API exists for every system the agent must touch, or the gap is named and costed | agent-tool-designer |
| Decide | The decision the evals serve, and the eval budget, are written down | agent-eval-designer |
| Design | Architecture: a shape and an authority per step, patterns, topology, the loop contract (budgets with numbers, stop rules, exits) and sizing | agent-architect |
| Design | A threat model with Rule of Two triage, and a permission tier for every action | agent-threat-modeler |
| Design | Tool boundaries, read versus write, and what each tool returns | agent-tool-designer |
| Design | A model per role | agent-model-selector |
| Build | Tool contracts reviewed: receipts, failure categories, idempotency, permission tier, versioning | agent-tool-designer |
| Build | The harness has a run record, checkpoints, cancellation and a kill switch | agent-harness-designer |
| Build | Retrieval and memory designed: retrieval spec, memory spec, context layout with budgets | agent-context-designer |
| Build | A first smoke suite, a golden run and a baseline | agent-eval-designer |
| Prove | Hard checks pass on the held-out split | agent-eval-designer |
| Prove | Harness tests pass: resume, stop, budget, cancel, kill switch | agent-harness-designer writes and owns the tests; agent-eval-designer gates the release on them |
| Prove | The red-team pass is done and its Critical findings are fixed | agent-threat-modeler |
| Prove | Schema diff and contract tests run in CI; the tool inventory has owners; old versions have a retirement plan | agent-tool-designer |
| Run | PRODGUIDE's six-item readiness gate passes before each rollout stage [PRODGUIDE ch16] | agent-ops-reviewer |
| Run | Monitoring is live: traces, p50 and p95, cost per successful run, alarms with sample floors | agent-ops-reviewer |
| Run | The conditions for widening autonomy are written down and met (below) | agent-ops-reviewer checks they are written; agent-threat-modeler judges them per action class; agent-architect's rollout section gives each step's stages and rollback trigger |

The skill that owns an unfinished gate item marks it planned or open, with the reason. A gate passes when every item is done or has an accepted, written exception.

**Move-up conditions.** PLAYBOOK asks for three things before more autonomy: proven reliability at the current level, written rules for the new actions, and a recovery plan for their failure modes [PLAYBOOK ch2]. Its reliability threshold varies by chapter: about 80% of outputs approved without changes over 30 to 60 days in ch2, and 85% over 30 days, then 90% over 60, in ch4's stages [PLAYBOOK ch4]. Read the spread as judgment, not measurement, and add the case count it leaves out: 30 days at five cases a week is about 20 cases, too few to tell 80% from 65%. Stages, entry criteria and rollback triggers per step: autonomy-and-shape.md, "Raising authority over time".

## Order of calls: a new agent

| # | Stage | Call | For | Can run alongside |
|---|---|---|---|---|
| 1 | Decide | agentic-business-case | Concreteness test, fit gate, scorecard, five-factor starting level, data readiness audit, business case or pilot | 2 |
| 2 | Decide | agent-tool-designer, agent-eval-designer | A usable API for every system the agent touches; the decision the evals serve and the eval budget | 1 |
| 3 | Design | agent-architect | Step map, authority per step from the starting level, patterns, topology, loop contract, sizing | |
| 4 | Design | agent-threat-modeler | Rule of Two triage, threat model, permission tier per action, guardrail design | 5 to 7 |
| 5 | Design | agent-model-selector | Model per role, from the step map | 4, 6, 7 |
| 6 | Design | agent-tool-designer | Tool boundaries, read versus write, what each tool returns | 4, 5, 7 |
| 7 | Design | agent-eval-designer | Quality dimensions and hard checks | 4 to 6 |
| 8 | Build | agent-tool-designer | Tool contracts, with scopes and tiers checked against the threat model | 9 |
| 9 | Build | agent-context-designer | Retrieval choice by query type, memory schema, pipeline, context layout, for the sources that passed the audit | 8 |
| 10 | Build | agent-harness-designer | The runtime that enforces the loop contract | starts with 8 and 9; settles after 8 |
| 11 | Build | agent-eval-designer | First smoke suite, golden run, baseline | 8 to 10 |
| 12 | Prove | agent-eval-designer, agent-harness-designer, agent-threat-modeler, agent-tool-designer | Held-out release gate, harness tests, red-team pass, contract tests in CI | each other |
| 13 | Run | agent-ops-reviewer | Run gate before each rollout stage; monitoring; the written conditions for widening autonomy | |
| 14 | Run | agent-threat-modeler, agent-architect | Judge each autonomy increase per action class; update the per-step rollout plan | |

Skip step 1 when the use case is already chosen and funded, but keep its data readiness audit if no one has run it. Skip a skill whose perspective the system lacks (no retrieval, no context work at Build), and say so in the handoffs. The harness settles after the tool contracts because it relies on their idempotency keys and lookups; the loop and state design can start earlier.

**Timeline.** Map the stages to calendar weeks from the human-side lead times, not only the engineering estimate. Model risk review, security review, compliance sign-off, labelling hours and data owners are booked at Decide, on day 1; in a regulated firm they set the schedule. A fixed deadline narrows the scope or the starting autonomy, never the gates. External limits set the pace too: sender reputation and domain warm-up, third-party API quotas and tiers, vendor onboarding and contract review. Book them on day 1, alongside the people.

## Order of calls: reviewing an agent that already runs

1. **agent-architect in review mode first.** It maps what actually runs (step map, ownership table, agent count) and its findings show which perspectives are in trouble.
2. **agent-threat-modeler next** when the model holds a write or high-impact tool, reads untrusted content, or a Critical finding touches access.
3. **Then by symptom:**

| Symptom | First skill | Then |
|---|---|---|
| Duplicate side effects after a retry, restart or redelivered event | agent-harness-designer | agent-tool-designer (keys and lookups at the tool) |
| Runaway loops, budgets that do not hold, no fast way to stop the agent | agent-harness-designer | agent-architect (budgets and stop rules in the contract) |
| Wrong tool chosen, wrong arguments, errors the model cannot act on | agent-tool-designer | agent-eval-designer (tool-choice evals) |
| Answers ignore or contradict the documents; the context window fills up | agent-context-designer | agent-eval-designer |
| Cost or latency too high | agent-architect (steps that should be code or a workflow) | agent-ops-reviewer, then agent-model-selector |
| "Evals pass but production fails", or no evals at all | agent-eval-designer | agent-ops-reviewer |
| Unapproved or unsafe actions, injection | agent-threat-modeler | agent-harness-designer (approval binding, kill switch) |
| Is it still worth running? | agentic-business-case | |

4. **agent-eval-designer before any fix counts as done.** A fix that no test can fail has not been shown to work.
5. **agent-ops-reviewer last**, for the Run gate on the fixed system. Model swaps come after the structural fixes and are re-measured on the same eval set.

## Why agent-threat-modeler starts at Design and returns at Prove

Access rules and guardrails are design decisions. An action's permission tier decides whether the agent holds that tool at all, and that changes the tool set, the harness's approval pauses and the eval cases. A threat model written after tools and harness are built can only add patches. So the threat modeler runs at Design, on the architecture, before agent-tool-designer writes contracts and agent-harness-designer builds the runtime. It returns at Prove as the red-team pass against the built system, seeded from the guardrail design, and its findings can send work back to Build. At Run it judges each widening of autonomy.
