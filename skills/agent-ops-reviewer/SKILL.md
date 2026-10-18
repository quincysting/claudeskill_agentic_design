---
name: agent-ops-reviewer
description: Reviews an LLM agent's production readiness and plans its operations and cost. Applies the Run gate (run record, idempotent writes, tiers and kill switch, redaction, safe-mode replay, KPIs, live monitoring) and scores OpenTelemetry GenAI tracing, logging, alerts, online evals, CI gates, shadow and canary releases, the service boundary and MCP supply-chain defaults. Models cost per successful run (review minutes included), per-run caps with a safe fallback, a capped ceiling (script), cost levers, caching, routing, p95 and peak capacity. Returns a scored review with prioritised fixes, or an ops and cost plan. Use for "is my agent production ready", a launch go/no-go, "agent costs too much", "reduce latency", "set up tracing or monitoring", "CI regression tests", "agent cost estimate", or a cost or quality incident. Not for runtime design (agent-harness-designer), architecture (agent-architect), offline evals (agent-eval-designer), threat models (agent-threat-modeler) or model choice (agent-model-selector).
---

# Agent Ops Reviewer

This skill produces one of two things for an LLM agent: a production-readiness review with a scored checklist and prioritised fixes, or an operations and cost plan covering tracing, logging, alerts, online evals, CI gates, releases, the improvement loop, and the cost and latency model. It bounds and measures the work before anyone buys capacity. Observability supplies evidence and evaluation supplies judgment, so the two are joined by trace ID. Every production failure becomes a test, and the system is priced on expected cost and judged on cost per successful run, with caps set from the capped ceiling.

**Perspective owned:** Cost and operations (ROI belongs to agentic-business-case). **Stage:** Prove and run. The end-to-end map of stages, perspectives, owners and gates is agent-architect's lifecycle map (lifecycle-map.md); start there when the work spans more than operations. This skill applies the **Run gate**: PRODGUIDE's six-item readiness gate, monitoring live, and the conditions for widening autonomy, which it checks are written down and hands to agent-threat-modeler (human oversight) to judge.

## When to use / when not to

Use it when someone:
- asks "is my agent production ready", wants a launch go/no-go, or is about to scale traffic;
- wants tracing, logging, dashboards or alerts for an agent, or says their alerts are noisy or missing;
- wants regression tests in CI for prompts, models or tools, or says "our eval CI is always red";
- says the agent costs too much, wants a cost estimate or budget, or needs lower latency;
- has had an incident and wants to know what should have caught it.

Hand off instead:
- The agent's shape, patterns and loop contract go to **agent-architect**. The runtime around the loop (run record, state and checkpoints, budget checks, cancellation, kill switch, safe-mode replay, streaming, serving the agent as an API, deployment shape) goes to **agent-harness-designer**. This skill reviews both: it checks that caps, fuses, stop reasons, the kill switch and replay exist and work; those skills design them.
- Offline eval datasets, scorers, judge calibration and sample sizes go to **agent-eval-designer**. This skill runs those evals in CI and on production traffic.
- Threat models, guardrail content, sandboxing, red-teaming, permission tiers, approvals and the conditions for widening autonomy go to **agent-threat-modeler**. This skill checks where guardrails sit, what they cost in latency, and that tiers, approvals and server defaults are in place (checklist G7, K).
- Picking or comparing models goes to **agent-model-selector**. This skill finds which steps could move to a cheaper tier and how to prove the move worked.
- Prompt layout for cache hits and context trimming design go to **agent-context-designer**; tool granularity, result shapes, idempotency keys and receipts go to **agent-tool-designer**.
- ROI and the business case go to **agentic-business-case**. Pass it this skill's cost per successful run, review minutes included.

## Inputs to gather first

Ask for these or read them from the code, configs and dashboards. Don't ask for anything you can read yourself. When an answer is missing, write an explicit assumption into the output and keep going. Track what you actually saw: each piece of evidence is seen, told (an owner described it) or unverified, and that mix decides whether the verdict is provisional (step 4).

1. **Request path.** Entry point, steps, the model each step calls, tools (marked read or write, and which writes are irreversible or move money), sub-agents and loops. In code, look for the loop (`while`, graph definitions, `max_iterations`, `max_turns`, `recursion_limit`).
2. **Caps and failure handling.** Limits on tokens, model calls, tool calls, retries and plan steps; what a capped run returns; retries and backoff, timeouts, any per-session cost cap, fallback model; the kill switch and how it is flipped. Search for `max_`, `timeout`, `retry`, `backoff`, `tenacity`, kill or draft-only flags and fallback config. A framework default counts as "not decided".
3. **Traffic.** Requests per day now and expected, the peak-to-average ratio, interactive or background, and whether a user is waiting.
4. **Tokens and cost.** Typical input and output tokens per call (from provider usage fields or traces), shared prefix size, cache use (`cache_control`, cache-read token fields), last month's invoice, provider rate limits; the success rate under the SLA and the human review and cleanup minutes per run.
5. **Telemetry today.** OTel SDK, vendor tracer (Langfuse, LangSmith, Phoenix, Datadog…), what is logged (prompts? tool results? user data?), where it goes, retention.
6. **Data rules.** PII, credentials, regulated data, residency, retention obligations.
7. **Evals.** Is there an offline suite and a baseline? A CI job? Online sampling? Who reviews failures?
8. **Release.** How changes ship; whether prompts, tool definitions and configs are versioned; feature flags; rollback.
9. **Targets.** p95 latency, cost per request or per month, quality bar.
10. **Owners.** Who gets paged, and who owns quality, cost and latency.
11. **Servers and builds.** The agent service and every tool or MCP server the team runs: where each listens, how its releases are built, pinned, signed and inventoried.

If the system runs on AWS, map each decision with [references/aws-implementation-notes.md](references/aws-implementation-notes.md).

## Procedure

1. **Pick the deliverable.** For an existing or about-to-launch agent, write a readiness review ([templates/readiness-review.md](templates/readiness-review.md)). For an agent being designed, or a "how should we run this" question, write an ops and cost plan ([templates/ops-cost-plan.md](templates/ops-cost-plan.md)). For a pure cost or latency complaint, write sections 2 to 4 of the plan only. When the user asks for both a verdict and a cost cut (common before launch or scale-up), use the review template and append plan sections 3 and 4 (cost model with levers, latency plan). When any B (tracing) item scores below 2, append plan section 5; when any D (alerting) item does, append section 9, so the tracing and alert requirements in the Quality bar have a place. When the review targets a date, also append plan section 14 (week-by-week rollout) so every P0 and P1 fix lands before it.

2. **Draw the run map.** Write the request path as a compact text flow with, per step, the model tier, trigger probability p, average calls when triggered, and the cap. Any step without a cap gets `cap: NONE`; that is a finding.
   ```
   request -> router (small, p=1, 1 call, cap 1)
           -> agent loop (large, p=0.9, ~2.2 calls, cap: NONE)  tools: order_lookup (read), issue_refund (write)
           -> output guard (small, p=1, 1 call)  -> answer        stop: final_answer | ??? 
   ```

3. **Sweep the evidence and score.** Go through [references/readiness-checklist.md](references/readiness-checklist.md) area by area, A to K. Score each item 0, 1 or 2 against concrete evidence (file and line, config, dashboard, trace) and write the evidence next to the score. Planned work scores 0; a framework default left unexamined (a default recursion limit, a default retry policy) scores at most 1. Tag each score seen, told (at most 1) or U (unverified, scores 0), and apply the checklist's N/A rules (J4 on managed APIs; G1 when no tool writes; K1 when nothing listens locally). If the run map is assumed, or more than half the blockers or applicable items are U, stop scoring item by item: deliver a discovery plan and a provisional verdict instead (checklist, "Missing evidence"). Use lite mode only for internal pilots with no write tools.

4. **Apply the blockers, the Run gate and the verdict rule.** Blockers: per-run caps ending in a partial result (A1), session cost fuse (A2), end-to-end trace ID (B1), redaction before export (C1), versioned prompts, tools and configs (F1), no write tools in shadow or replay (G1), a kill switch flipped without a redeploy (G5, when any tool writes). Any blocker at 0 means "Not ready", whatever the total. Then mark each Run gate row pass or fail (checklist, "Run gate"): the six items, monitoring live, and the autonomy expansion conditions, which pass when they are written and owned. "Ready" needs a passing gate; every failing row is a P0 fix. Use the checklist's verdict rule as written, without rounding up. When any blocker or more than a quarter of applicable items are U, label the verdict "Provisional" and give the floor (U at 0) and ceiling (U at 2) with the verdict each gives. A blocker seen at 0 keeps "Not ready" firm.

5. **Specify tracing.** Use the trace schema in [references/observability.md](references/observability.md) §1 to §2: one trace ID through every model call, tool, MCP call, retrieval and validation; a span per step; versions, tokens including cache reads, decisions, and an agent-level stop reason and the run ID on the root, so traces, eval verdicts and audit entries join through the run record (observability.md §1, "The run record is the join"; checklist B8). Map fields to the OpenTelemetry GenAI conventions where they exist, say they are Development status (as of 2026-10), pin library versions, and put what the spec lacks under one custom namespace (`app.stop_reason`, `app.run_id`, `app.cost.usd`, `app.degraded`). Normalise each provider's token fields to the spec's meaning, carry trace context into worker threads, and read the trace ID for logs inside the active span (observability.md §1 to §2).

6. **Set the logging and redaction policy.** Use metadata on every run and payloads only for a sampled share plus failures, escalations and incidents. Mask before export, never after. Keep two records: an audit log (actions, approvals, outcomes; long retention; tamper-evident) and a debug payload store (masked, sampled, short retention, restricted access). Content capture stays off by default in production. See [references/observability.md](references/observability.md) §3.

7. **Define metrics and alerts.** Use the metrics by layer (observability.md §4). Alert on outcomes over windows with a minimum sample count, in three layers (digest, warning, page). Alert text names the component, version and example traces. Use drift statistics to explain a change, never to page. Give every rate alert a denominator floor, alert on per-request metrics split by segment rather than totals, and validate each alert on a regression window and a benign window before trusting it. Write the alert table and the quality-alert runbook (observability.md §6).

8. **Set up online evals.** Score asynchronously in a worker. Sample by hashing the request ID, stratify by task type and risk, and always capture failures, escalations and guardrail hits. Size windows from the interval table (observability.md §5), not from intuition. Attach verdicts to traces as `gen_ai.evaluation.result`. Budget eval spend at 5 to 15% of inference spend. Live traffic has no reference answer, so helpfulness or tone judges alone cannot see a confident wrong answer: add groundedness against the trace's own tool results and a weekly labelled sample (observability.md §5).

9. **Design the CI regression gate.** Follow [references/ci-gate.md](references/ci-gate.md). Trigger on PRs touching prompts, models, tools, configs or datasets. Deterministic checks get zero tolerance. Judge-scored flips must reproduce on rerun and pass a paired test. The tolerance comes from three runs of the unchanged system. Post named cases to the PR, and change baselines only after review. Choose judge-per-PR or nightly from PR volume.

10. **Stage releases.** Shadow first, with write tools routed to a recorder or dry-run stub. Then a canary at 1 to 5% for at least 24 hours with version-tagged telemetry and automatic rollback on written triggers (success under the SLA, p95, duplicate side effects, cost per successful run, review minutes), flipping to draft-only or rolling back (checklist G2, G5). Use A/B only for questions about user behaviour. Keep in-flight sessions on their starting version. A prompt or config read at runtime is pinned to a version and released like code (checklist F1), and a per-tool smoke set runs after every deploy or config change (checklist G6). See [references/observability.md](references/observability.md) §7.

11. **Close the improvement loop.** Turn every confirmed failure into a reviewed test case within a day. Triage by root cause, change one thing per round, and record each change as problem, change and measurement. Optimiser output and any self-adaptation pass the same gate; nothing rewrites its own prompts in production. See observability.md §8.

12. **Build the cost model.** Fill the worksheet in [references/cost-latency.md](references/cost-latency.md) §2, or write a spec and run `python scripts/cost_model.py spec.json` (run it without arguments for the example and self-check). Report expected, likely high (about p95) and capped ceiling cost per request, the ceiling's ratio to expected (a bound, not a forecast), per-step share, monthly cost at expected volume and at peak (expected × the busiest day's volume × 30), and cost per successful run: (expected cost + review minutes × value per minute) / success rate, where a success met its SLA inside guardrails (cost-latency.md §2, step 8; the script prints it when the spec sets `success_rate`). When the success rate or review time is unknown, say so and list it under "Measure next". With no caps, report the ceiling as UNBOUNDED for the current system, rerun with the caps you propose, and report that ceiling separately. Name the model behind each tier, date every price and name its source (snapshot in §3; recheck it). Mark each input as measured or assumed; the script's warnings list the defaults it filled in. To check traced cost against the bill, use a per-call ledger plus a low-cardinality metric (cost-latency.md §2, "Attributing cost").

13. **Choose cost levers in order.** Start at the step with the largest share and work down the stack in [references/cost-latency.md](references/cost-latency.md) §4: bound the work (per-run caps that end in a partial result and the smallest unblocking question), then fewer calls, fewer tokens, reuse (caches), a cheaper model per step or a cheap mode per case (risk-based routing, §6), a cheaper pricing tier, and only then engine and hardware. For each lever, state the expected effect from the model's what-ifs, the metric that proves it worked, and the guard against quality loss (cost per successful run on the eval set), and ship it by canary with rollback triggers. No lever that changes prompts, context, models or call counts ships before a quality baseline exists. With no eval set, the first fix is a minimal baseline (cost-latency.md §4, "No eval set yet"), designed with **agent-eval-designer**; only caps set above the traced p99, moves of offline work to batch, and a cache-layout change that moves volatile fields below the cache point without changing the wording (after a paired shadow check, same section) go ahead before it.

14. **Plan latency.** Read p50 and p95 per phase and the jitter, not averages. Decompose p95 into model time (prefill and decode), retrieval, tools, orchestration and loop iterations. Fix the tail first (caps, timeouts that cancel), then sequential calls (merge, parallelise reads with no data dependency, carrying trace context into the workers), then prompt length (time to first token), then perception (streaming, async jobs for work over about 30 s). See cost-latency.md §8.

15. **Decide where each agent runs.** Classify each agent or step by data sensitivity and load shape (cost-latency.md §9). Default to a managed API behind a gateway, and move a step only with a named reason. For any scale-up, compute peak requests and tokens per minute per model (formula in the same section; peak-hour factor 3 until measured) and compare them with the provider's limits; a shortfall is P0 because limit increases take time. Check that each host's maximum execution time exceeds the agent's capped latency ceiling (cost-latency.md §9, checklist J5). Serving design is agent-harness-designer's; here you score the service boundary (schemas, no inference on the request event loop, per-client limits and stream throttling: checklist J6, J7, A9) and send gaps there.

16. **Prioritise the fixes.** P0 covers blockers and anything that can spend without bound, leak data, act twice, or exceed provider limits at peak. P1 covers gaps that stop you detecting or diagnosing a regression. P2 covers optimisations and hygiene. Within a tier, order by risk removed or money saved per unit of effort. Every fix names what to change, where, how to verify it, its effort, its owner and when it is due: a date when there is a target date, otherwise "week N" from the review date.

17. **Check the Quality bar below, then hand back** in the template's shape.

## Decision guide

**Symptom → first move**

| Situation | Check first | Recommended move | Why | Watch out for |
|---|---|---|---|---|
| Bill up, traffic flat | Per-step cost share, calls per request, cache-read share, retry rate, by version | Find the step and the deploy that moved; restore the cache prefix or cap the loop | Cost changes come from calls × tokens × price; one of the three moved | Optimising the router while the loop holds most of the spend |
| A few sessions burn the budget | Distribution of cost per session, stop reasons of the top 1% | Per-session cost and turn fuse with handoff | The provider's account cap is far too coarse to stop one looping session | Fuse set below what successful long sessions need; set it from the success curve |
| p95 latency high, p50 fine | Loop iterations, retries and tool latency in slow traces | Step caps, tool timeouts that cancel, parallel independent reads | The tail is extra iterations and retries, not slow tokens | Parallel fan-out raises downstream peak load |
| Time to first token high | Prompt length, cache hit rate | Trim context, stable cached prefix, fewer tools offered, streaming | Prefill grows with prompt length | Trimming facts the next step needs |
| Quality dropped, no errors | Sampled pass rate by stratum and version; tool error rate; recent deploys | Read the lowest-scoring traces, then roll back or escalate upstream | Agents degrade silently; an error rate stays flat | Paging on drift statistics instead of outcomes |
| CI eval gate always red | Flip rate of the unchanged system | Rerun flips plus a paired sign test; deterministic checks keep zero tolerance | Judge noise makes any-flip gates fail most runs | Loosening the deterministic checks too |
| Alerts ignored | False-alarm rate, samples per window | Minimum sample count, longer windows, three layers | A 30-sample window cannot see a 5-point drop | Tightening thresholds instead of adding samples |
| Eval spend rising | Cost per scorer | Deterministic first, cache verdicts (key includes judge version), batch tier | Judges dominate eval cost | A cheaper judge without recalibration |
| Cost cut wanted, no eval set | Whether any outcome is labelled or traced per step | Step-level tracing, then a minimal baseline, then one lever at a time | "Without hurting quality" needs a measured quality | Judging a cheaper variant by reading a few outputs |
| No access to code or traces | Which blockers you can see at all | Discovery plan plus a provisional verdict with floor and ceiling | Unseen is not the same finding as absent | Scoring unseen items 0 and presenting "Not ready" as if you had looked |
| Stopping the agent means a rollback and redeploy | How the switch is flipped and how long a flip takes to reach running workers | Draft-only and abort flags the gate reads at every call (design: agent-harness-designer) | A redeploy is the slowest way to stop a running incident | A flag read once at startup, which still needs a restart |
| Cheaper model or mode looks good per call | Success rate and review minutes for each variant | Compare cost per successful run on the eval set | Failures, repairs and longer review cost more than the call saved | Leaving review minutes out when the variants differ in review time |

**Online-eval sampling by volume**

| Requests/day | Sample | Plus |
|---|---|---|
| Under about 100 | All | Nothing extra needed |
| 100 to 10,000 | 5 to 20%, stratified; oversample rare and high-risk strata | All failures, escalations, guardrail hits |
| Over 10,000 | 1 to 5%, stratified | Same; raise the rate for any stratum you need to watch within hours |

**Release strategy**

| Change | Strategy |
|---|---|
| Prompt, model, planner or tool change | Shadow (writes stubbed) → canary 1 to 5% ≥ 24 h → full |
| Question about user behaviour | A/B with sticky assignment and per-variant state |
| Urgent fix for an active incident | Gate fast tier → canary with a short watch window → full; backfill the test case |
| Model migration | Same gate as any PR, then shadow and canary; never a looser rule |

**Judge in CI**

| PR volume touching prompts, models or tools | Pre-merge | Nightly |
|---|---|---|
| A few a week | Deterministic + judge on every PR in scope | Full suite with repeats |
| Dozens a day | Deterministic only | Full suite with the judge; issue on regression |

**Where each agent runs**

| Data the step touches | Load | Default |
|---|---|---|
| Open | Bursty or low | Managed API behind a gateway |
| Open | Steady, high, narrow task | Managed API; self-host lane only if a small open model meets the bar and GPUs stay busy |
| Restricted | Bursty | Dedicated endpoint or residency-pinned API |
| Restricted | Steady | Own weights in your VPC or on-prem |

**Caches**

| Cache | Use when | Never when |
|---|---|---|
| Provider prompt cache | Any repeated long prefix (layout: agent-context-designer) | No exclusion; monitor cache-read share and the write-to-read ratio |
| Response or tool-result cache | Stable, non-personalised, read-only work | Answers depend on permissions or fresh state, unless keyed by scope with a TTL |
| Planner-decision memo | Loops revisit the same fact states | Keys miss the context, no TTL in a changing world |

## Output

Hand back the filled template: [templates/readiness-review.md](templates/readiness-review.md) for a review, [templates/ops-cost-plan.md](templates/ops-cost-plan.md) for a plan. Every output includes:
- a one-line verdict (review), marked Provisional with floor and ceiling when evidence is missing, or the targets table (plan); a discovery plan when the review is too speculative to score;
- for a review, the Run gate table with each row pass or fail;
- the run map;
- assumptions, numbered, each marked "assumed" until measured;
- for a review, the blockers table, the area scorecard and item scores with evidence;
- the cost snapshot: expected, likely high and capped ceiling $ per request (or UNBOUNDED plus the ceiling with proposed caps), cost per successful run with its review share (or the missing inputs named), per-step share, monthly at expected volume and at peak, the model behind each tier, prices with date and source;
- prioritised fixes (P0, P1, P2) with where, how to verify, effort and owner;
- hand-offs to sibling skills, and the three to five measurements that would most change the conclusions.

Put the verdict, blockers and P0 fixes on the first screen. Keep item-level scores in a collapsible block or appendix.

## Quality bar

Check the output against each item before returning it:
- [ ] Every score cites evidence or says "no evidence", and carries its tag (seen, told, U). Nothing scores 2 on a promise.
- [ ] The verdict follows the checklist's rule, says "Provisional" with floor and ceiling when the rule requires it, and blockers are listed before anything else.
- [ ] The Run gate is reported row by row; "Ready" appears only with a passing gate; each failing row is a P0 fix; the autonomy row is handed to agent-threat-modeler.
- [ ] The cost model shows expected, likely high and capped ceiling (or UNBOUNDED now plus a separate figure with proposed caps), cost per successful run with review minutes priced in (or the missing inputs named), per-step share and monthly totals at expected volume and at peak; every tier names its model; every price carries a date and a source; assumed inputs are labelled.
- [ ] Caps quoted in the run map, cost table, latency plan and fixes are the same numbers, and per-request exposure is stated as min(session fuse, capped ceiling).
- [ ] Every cost lever has a quality baseline to be measured against, or waits for one.
- [ ] Each recommended lever names the metric that will prove it worked and the guard against quality loss.
- [ ] Every alert has a window, a minimum sample count, a severity and a route; none fires on a single request.
- [ ] No LLM call goes on the request path without a latency budget and a reason it cannot be asynchronous.
- [ ] Content capture is off by default in production, and masking happens before export.
- [ ] OTel GenAI attribute names are marked Development status as of the review date, with versions pinned.
- [ ] Shadow and replay plans stub every write tool.
- [ ] Fixes are ordered by risk and effort, and each has a verification step and an owner (or "owner: TBD").
- [ ] Work belonging to a sibling skill is handed off, not redesigned here; runtime and serving gaps name agent-harness-designer as the owner of the fix design.
- [ ] No invented measurements. Estimates are labelled as estimates.

## Common mistakes

- **Pricing from one model call.** One request is several calls (an illustrative support flow comes to 4.8 before retries). Fix: expected calls per step, plus the likely high and the capped ceiling.
- **Average without tail, or a ceiling sold as a forecast.** Fix: report the likely high (about p95) for budgets and the capped ceiling as a bound. If there are no caps there is no ceiling: report UNBOUNDED as the first finding, then the ceiling with proposed caps.
- **Optimising the wrong step.** Weeks on the router while the reasoning loop holds three quarters of the spend. Fix: per-step share from traces before choosing a lever.
- **Per-call price instead of cost per successful run.** A cheaper call that fails more often, needs repairs or takes longer to review costs more. Fix: compare (model + tools + review minutes × value per minute) / success rate on the eval set, repairs and retries included.
- **No kill switch, so stopping means a redeploy.** Fix: draft-only and abort flags the gate reads at every call, flipped without a redeploy and drilled (checklist G5).
- **A tutorial harness in production.** An in-memory checkpointer behind several workers, a default thread ID, a `while True` tool loop, a step cap that returns an ordinary answer. Fix: score A1, B8, G5 and G8 on the running service, not the demo, and hand the rebuild to agent-harness-designer (its tutorial-harness table).
- **Treating tracing as evaluation.** A complete trace of a wrong answer is still a wrong answer. Fix: sampled online evals joined to traces by ID.
- **Monitoring quality with reference-free judges only.** Helpfulness and tone judges rate a fluent invented answer highly. Fix: groundedness against the trace's own tool results, claim-versus-action checks and a periodic labelled sample.
- **Copying a provider's input-token field into the spec attribute.** Some providers leave cached tokens out of their input count, so uncached input comes out too low or negative downstream. Fix: map to the spec's meaning (input includes cached) in each adapter, with a test.
- **Alerting on single requests or tiny windows.** At an 85% pass rate a 30-sample window is ±12.8 points. Fix: minimum counts, longer windows for pages, layered alerts.
- **A gate that fails on any judge flip, or keys cases by input text.** Fix: zero tolerance only for deterministic checks; rerun and test judged flips; stable case IDs.
- **Shadowing with live write tools.** The shadow refunds the customer a second time. Fix: a recorder or dry-run stub for every write tool, tested.
- **Logging full prompts in production by default**, or scrubbing after storage. Fix: metadata by default, masking before export, sampled payloads in a separate store.
- **Keeping raw chain-of-thought as the audit record.** Fix: actions, decisions, approvals and short justifications.
- **Calling the OTel GenAI conventions stable.** As of 2026-10 they are Development status, in their own repository. Fix: pin versions and namespace custom attributes.
- **Undated prices, or token counts carried across model families.** Tokenizers differ (one provider's newer models produce about 30% more tokens for the same text). Fix: date prices and re-measure tokens after any model switch.
- **Soft timeouts.** The client gives up and the work keeps billing. Fix: timeouts that cancel downstream work.
- **Letting the agent tune itself in production.** Fix: optimisers and self-adaptation propose changes; the gate decides.
- **Recommending self-hosting without a utilisation number.** Fix: self-host only with restricted data or a steady, narrow, high-volume step whose GPUs stay busy.

## Sources

Distilled from these books (chapter numbers), plus current public documentation:
- Systems Thinking for Agentic AI: ch. 3 (prompt versioning), 4, 8, 10, 12 (performance and cost: budgets, cost drivers, latency, routing, caching, backpressure, timeouts, metrics), 14, 15 (observability: logs, metrics, traces, instrumentation, privacy, the architect's rules), 16.
- AI Evals in Practice: ch. 1, 6 (regression testing and CI), 10 (online evals, sampling, guardrails, alerting), 11 (eval cost and latency), 12 (tooling and lock-in), 13, 14 (improvement case study), 15.
- Building Applications with AI Agents: ch. 2, 8, 10 (monitoring in production), 11 (improvement loops, experimentation).
- AI Agents: The Definitive Guide: ch. 4, 7 (deployment, hardening, fallback models, inference backends), 8, 9 (traces to benchmarks), 11 (agentic cost multiplier, memoisation, infrastructure).
- Agentic Mesh: ch. 6, 9, 12. Designing Large Language Model Applications: ch. 5, 9, 13. Building Agentic AI: ch. 1, 4, 9. The Agentic Enterprise: ch. 1, 8. Agentic Artificial Intelligence: ch. 7, 8, 12. An Illustrated Guide to AI Agents: ch. 2, 10.

Added in the 2026-10 revision. In `references/`, a citation such as [PRODGUIDE ch17] names one of these books and a chapter; each reference file restates the point it relies on, so the books are not needed to use the skill.
- PRODGUIDE: *Agentic AI Systems: The Complete Guide for Building Production AI Agents*, ch. 14 (safe-mode replay), 16 (the production spine and the six-item readiness gate), 17 (cost per successful run, per-run caps with a safe fallback, risk-based routing, p95 and jitter, canary releases).
- PLAYBOOK: *Agentic AI Playbook*, ch. 2 and 4 (conditions for widening autonomy), 6 (run-level token cap, canary).
- HARDMCP: *Hardening MCP Servers*, ch. 3 (supply chain), 10 (operational defaults and runtime abuse).
- FASTGENAI: *Building Generative AI Services with FastAPI*, ch. 4 (schema validation at the service boundary), 5 (inference off the event loop), 9 (rate limits and stream throttling).

Andrew Ng, The Batch letters:
- Why We Need More Compute for Inference (2024-04-24): https://www.deeplearning.ai/the-batch/why-we-need-more-compute-for-inference
- Improve Agentic Performance with Evals and Error Analysis, Part 2 (2025-10-22): https://www.deeplearning.ai/the-batch/improve-agentic-performance-with-evals-and-error-analysis-part-2
- Make All Your Tokens (and Your Brainwork) Count (2026-07-10): https://www.deeplearning.ai/the-batch/make-all-your-tokens-and-your-brainwork-count
- What Comes After Tokenmaxxing? (2026-08-07): https://www.deeplearning.ai/the-batch/what-comes-after-tokenmaxxing-how-to-avoid-getting-locked-in-to-just-one-ai-provider

Public documentation:
- OpenTelemetry GenAI semantic conventions (read 2026-10-06; cache attributes rechecked 2026-10-11): https://github.com/open-telemetry/semantic-conventions-genai
- Anthropic pricing (read 2026-10-06): https://platform.claude.com/docs/en/about-claude/pricing
- Anthropic rate limits (read 2026-10-06): https://platform.claude.com/docs/en/api/rate-limits
- OpenAI flex processing (read 2026-10-06): https://developers.openai.com/api/docs/guides/flex-processing
- Anthropic, How we built our multi-agent research system (2025-06): https://www.anthropic.com/engineering/multi-agent-research-system
- vLLM speculative decoding docs: https://docs.vllm.ai/en/latest/features/speculative_decoding/
- RouteLLM (2024): https://arxiv.org/abs/2406.18665
- DSPy optimizers (2026-10): https://github.com/stanfordnlp/dspy/blob/main/docs/docs/learn/optimization/optimizers.md
- Practitioner lab notes (AWS AgentCore and data labs, 2026-10)
- Amazon Bedrock prompt caching (read 2026-10-11): https://docs.aws.amazon.com/bedrock/latest/userguide/prompt-caching.html
- Amazon Bedrock token burndown and quota accounting (read 2026-10-11): https://docs.aws.amazon.com/bedrock/latest/userguide/quotas-token-burndown.html
- Amazon Bedrock AgentCore ground truth evaluations (read 2026-10-11): https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/ground-truth-evaluations.html
