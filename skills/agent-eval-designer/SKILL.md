---
name: agent-eval-designer
description: Designs and reviews offline evaluation for LLM agents. Covers what to measure (outcome as final state, trajectory and tool use, safety, cost), building a versioned task set or golden dataset with negative cases, choosing a scorer per quality (code checks, then LLM-as-judge, then humans), calibrating LLM judges, repeated trials with pass@k and pass^k, eval statistics (confidence intervals, sample sizes, paired comparisons) and which checks gate CI. Produces an eval plan document or a review of an existing eval setup. Use for "how do I evaluate my agent", "write an eval plan", "LLM-as-judge", "can I trust my judge", "how many test cases do I need", "golden dataset", "trajectory evaluation", "is this improvement real", "my evals pass but production fails". Not for production monitoring, tracing, online evals or alerting (agent-ops-reviewer), red-team attack design (agent-threat-modeler) or picking a model shortlist (agent-model-selector).
---

# Agent Eval Designer

This skill produces an evaluation plan for an LLM agent, or a review of an eval setup that already exists. It treats an eval as a measuring instrument. Grade the state the agent leaves behind, check every rule-decidable quality in code before any judge runs, trust a judge only after it has been compared with human labels, run each task more than once, and put an interval on every number. A suite that cannot fail, or whose differences sit inside its own noise, does more harm than having no suite, because people believe it.

## When to use / when not to

Use it when someone:
- is about to launch or scale an agent and asks what to test, or asks for an eval plan;
- needs a golden dataset or task set, trajectory or tool-use scoring, or RAG scoring inside an agent;
- is writing, debugging or trusting an LLM judge;
- asks how many cases they need, or whether a gain between two prompt, model or tool versions is real;
- wants an existing harness, scorer set or CI gate reviewed, or says "our evals pass but production fails".

Hand off instead:
- Online evals on live traffic, sampling, tracing, dashboards, alerting, shadow and canary releases go to **agent-ops-reviewer**. This skill delivers the offline suite, baseline and gate that skill builds on.
- Designing attacks and red-team campaigns goes to **agent-threat-modeler**. This skill reserves the safety slots, metrics and gates.
- Architecture choices go to **agent-architect**, tool schema fixes to **agent-tool-designer**, retrieval and memory design to **agent-context-designer**, model shortlists to **agent-model-selector** (then use this skill's paired comparison to choose on your own tasks), and ROI to **agentic-business-case**.

A single-call LLM feature with no tools can use the same procedure; skip the trajectory and pass^k parts.

The offline suite says nothing about load, concurrency, rate limits or behaviour at 10,000 simultaneous users. Say so in the plan and point to load testing and production monitoring. Language coverage and compliance rules (PCI, privacy) do belong here, as tags and hard checks. If a sibling skill isn't installed, the plan still names the hand-off work and proposes an owner.

## Inputs to gather first

Ask for these or find them in the code. If an answer is missing, write the assumption into the plan's "Assumptions" section instead of stalling.

1. **Task types and mix.** What users ask for, rough share of each, single-turn or multi-turn, number and kind of users.
2. **Tools.** Each tool, read or write, and which writes are irreversible or move money or data. For each write tool: is there a sandbox, test account or stub?
3. **Success per task type**, stated as a final state or a checkable answer, and who can confirm it (a named domain expert).
4. **Worst failures.** Costly, unlawful, embarrassing or irreversible outcomes. These become hard checks and safety slots.
5. **Existing material.** Prompts tested so far, logs or traces, incidents and support tickets, eval code, judge prompts, CI config.
6. **The decision the eval serves.** Launch go/no-go, version comparison, regression protection or model migration. Sizes and gates follow from this.
7. **Constraints.** PR and release cadence, eval budget per run and per month, expert hours per month for labelling.
8. **Production settings.** Model and version, temperature, prompt version, tool list, step limit. Evals run at these settings.
9. **Policies and who owns them.** Rules the agent must follow (approval limits, refund rules, data handling) and the person who decides each. Include the ones that look obvious and aren't, such as whether "card on file" plus "book it" counts as consent to charge.

When reviewing, also collect the dataset (size, sources, version), scorer code, runner, judge prompt, any calibration data, a recent report, and the rule CI uses to pass or fail. Read the code, not just the README: the defects that matter most are in edge-case branches (see [references/review-checklist.md](references/review-checklist.md)).

## Procedure

1. **Name the decision and the quality dimensions.** List three to six dimensions, typically outcome correctness, path and tool use, safety and policy, communication, and cost and latency. For each, write what a failure looks like, how bad it is, and whether it is *hard* (any failure fails the trial) or *soft* (scored and reported). Hard checks never get averaged with soft scores.

2. **Define success as checkable criteria per task type.** Prefer a predicate on the final state ("one booking exists for these passengers on flight X at ≤ the quoted fare, and the card was charged once") over a judgment of the reply. Mark which criteria are rule-decidable; only the rest may go to a judge. An agent saying "done" is not evidence of anything. Before a policy becomes a hard check, get its owner to sign it off, and record the rule, owner and date in the plan. An undecided policy is an open question: score it report-only until it is decided, so the suite doesn't silently encode the eval author's guess.

3. **Build the task set.** Follow [references/datasets-and-harness.md](references/datasets-and-harness.md).
   - Sources, best first: real failures (incidents, tickets, bad traces), real logs, expert-written cases, then synthetic drafts that a person reviews. The expected answer must never come from the model under test.
   - Pre-launch, with no real failures yet:
     - rewrite the existing prompts as seeds;
     - borrow real inputs from wherever people do the task today;
     - harvest logs from a staff dogfood and a small beta;
     - seed safety tasks from a threat model;
     - fill gaps with reviewed synthetic drafts, reporting the real-input slice separately.
     The section "Before launch" in datasets-and-harness.md says how much synthetic is acceptable.
   - Composition: every tool, multi-tool chains, and **negative cases** (no tool needed, nothing to report, must refuse, must ask, must escalate). Add stress variants: ambiguity, frustration, missing information, partial tool failure, slow tools, irrelevant context and injected instructions inside tool output.
   - Each task has an ID, a `scenario_id` shared by its variants, prompt, starting state, clock, success criteria, hard rules, tags (task type, tool, difficulty, source, risk) and the dataset version.
   - Start with 20 to 50 tasks for discovery, then size for the decision with step 8. Hold out a test split scored only at release. Size it for the precision the release claim needs (step 8), not as a fixed share; 20 to 30% of a few hundred tasks gives only about ±7 to 10 points.
   - For a tool or feature not built yet, write its tasks first as a *capability suite*, expected to fail at the start. Move tasks into the regression suite once they pass, and report the two suites separately.

4. **Specify the harness.** Each trial starts from a fresh environment. Write tools go to a sandbox or a recorder, never to real systems. Every trial records the transcript (tool calls, arguments, results, reply, tokens, cost, stop reason) and the final state. Crashes and timeouts count as failed trials and are reported as an error rate. The oracle (expected answer, expected route) goes to the scorer only, never into the agent's prompt. Run at production settings. Before trusting the suite, run it once against a deliberately broken agent (tools disabled, empty replies). It must go red.
   - Fix the clock per task, and serve live read data (prices, seats, inventory, balances) from synthetic fixtures or versioned recordings. A live vendor sandbox runs only as a non-gating smoke test.
   - For write tools that move money or book things, inject "write succeeded, response lost" faults (timeout after commit, duplicate user message, restart mid-task) and check for exactly one write.
   - Validate a multi-turn user simulator against real or dogfood conversations before trusting it.
   - Details for all three: datasets-and-harness.md.

5. **Choose a scorer per quality, cheapest adequate first.** Use [references/scorers.md](references/scorers.md) and the decision table below. The ladder is code check, then embedding pre-filter (only with a reference answer), then rubric LLM judge, then human. For trajectories: fail on forbidden actions, skipped preconditions and blown budgets; compare tool *sets* (recall, precision, argument accuracy) and check order only where it carries meaning; report efficiency as a soft score; never require one exact sequence. For RAG inside the agent, score retrieval and generation separately. For safety, cover the three threat models: misuse, manipulation through data, and benign-task harm.

6. **Design and calibrate each judge.** Follow [references/llm-judges.md](references/llm-judges.md).
   - Write a versioned rubric with three to five weighted criteria and defined score levels, phrased as the workflow's practical questions ("is every claim supported by the retrieved policy?", "should this message be sent?"). It returns JSON with reasons, uses the lowest-variance sampling the provider accepts (temperature 0 where allowed; the newest Claude models reject non-default sampling parameters, so there rely on a fixed versioned prompt, structured output and a majority of three samples), and comes from a different model family than the agent where possible.
   - Before a judge gates anything, have a person label 50 to 100 cases from this task, including fluent-but-wrong outputs. Report chance-corrected agreement (Cohen's κ on pass/fail) and the judge's **false-pass rate**. Until then the judge ranks outputs for human review and nothing more.
   - Pin the judge model and rubric version, and recalibrate whenever either changes.
   - When expert hours are scarce, shrink the judge's job rather than skip calibration. Move every checkable quality into code, calibrate only the criteria that gate, and do one criterion per labelling round, highest risk first.

7. **Set trials and reliability metrics.** Run every task at least 3 times (5 is better) for customer-facing or side-effecting agents, and report pass^k next to pass@1, computed per task and then averaged. Use pass@k only where a verifier allows retries or when comparing training checkpoints. See [references/statistics.md](references/statistics.md). Fit trial counts to the budget by risk: more trials on side-effecting slices, one on read-only slices in nightly runs. Estimate the cost per run from measured agent cost per trial, not just judge cost ([references/ci-gates.md](references/ci-gates.md), "Agent inference cost").

8. **Do the statistics before promising anything.** Use [references/statistics.md](references/statistics.md).
   - Put a 95% interval (Wilson) and a task count on every rate.
   - Size the suite for the decision. ±10 points needs about 60 to 100 tasks, ±5 about 250 to 400. Claiming a failure rate below 1% with zero observed failures takes about 300 independent tasks. Repeated trials of one task don't count toward that. If the count can't be reached before launch, state the bound the suite does support and recommend a human approval on that action until it can.
   - Compare versions **paired** on the same tasks: count the tasks that flipped each way and use a sign test, or bootstrap per-task differences. Resample tasks (or scenarios), not trials.
   - Quote each number from the right split. PR comparisons come from the dev split, release rates and their intervals from the held-out split only, and hard-check results from both.
   - Count effective tasks. Variants of one scenario fail together, so n_eff = n / (1 + (m − 1)ρ). For zero-failure bounds, count scenarios until ρ has been estimated. To raise power, add scenarios, not variants.
   - State the smallest difference the suite can detect: about 2.8 × √(d / n), where d is the share of tasks that flip between runs of the unchanged system, and never below 6/n. Differences inside it are ties.

9. **Define the gates.** Use [references/ci-gates.md](references/ci-gates.md).
   - Deterministic regressions are never tolerated.
   - Release floors are a separate rule. Critical hard checks (money or irreversible action without consent, duplicate write, wrong account, cross-customer data) need 100% on every trial. A floor below 100% is allowed only for non-critical hard checks, with each failure listed as a known limitation.
   - A judge-scored flip counts only if it reproduces on rerun, and the net change is tested with a paired sign test. Set the tolerance just above the spread of three runs of the unchanged system.
   - Pick tiers by PR volume: pre-merge, PR judge run or nightly, release. The release gate adds the held-out split.
   - Deterministic scoring is free, but running the agent to produce transcripts is not. Keep pre-merge to a small critical subset at 1 trial, and re-score cached transcripts when only scorers or data changed.
   - Save a new baseline only by decision after review. Model migrations go through the same gate as prompt edits.
   - Hand online sampling and alerting to agent-ops-reviewer.

10. **Plan operations.** Name an owner. Every production failure becomes a reviewed task within about a day. Set the labelling budget (about 50 annotations a month is a workable minimum) and the eval spend budget. Do the schedule arithmetic: labels needed (gating criteria × task types × 50 to 100) divided by monthly capacity (hours × measured labels per hour) gives the months until the judge can gate ([references/llm-judges.md](references/llm-judges.md), "Labelling schedule"). Check expected tools against the live tool registry at load time, and review quarterly to retire stale cases.

11. **Write the output and check it** against the Quality bar below. Include a short rollout: what exists by the end of week 1, by launch, and after launch.

**Review mode.** When asked to review an existing setup, do steps 1 and 2 from what you find, then work through [references/review-checklist.md](references/review-checklist.md): first the "cannot fail" checks (scorers that pass on empty or missing data, dropped errors, averaged hard checks, oracle leakage), then statistics, judge calibration and gates. For "evals pass but production fails", use the symptom table in that file. Report findings by severity with the exact location, then a fix for each.

## Decision guide

**Which scorer for which quality**

| Quality | First choice | Escalate to | Watch out for |
|---|---|---|---|
| Final state correct (record written, booking made, tests pass) | Code predicate on the environment after the run | Judge only for free-text fields of the state | Grading the reply instead of the state |
| Schema, required fields, length, forbidden content | Validator or regex | — | Schemas without `required` accept `{}` |
| Required tool, forbidden tool, precondition order, step or cost budget | Code check on the transcript, hard | — | Exact-sequence matching fails valid routes |
| Tool arguments | Field-by-field comparison after normalising types and formats | Judge for free-text arguments such as search queries | Strict dict equality fails `"123"` vs `123` |
| Efficiency (calls, steps, tokens, cost) | Counters, soft score | — | Penalising legitimate repeats (two orders, two lookups) |
| Answer with a reference | Required-facts check; embedding pre-filter (≥0.95 pass, <0.5 fail) | Rubric judge for the middle band | Embeddings miss wrong IDs, dates and amounts |
| Open-ended quality, tone, helpfulness | Rubric judge with practical questions | Pairwise for choosing versions; humans to calibrate | Rewarding fluency and length |
| Grounding (RAG) | Claim-by-claim faithfulness, computed from claim verdicts | Strong judge from another family | Trusting a judge's self-reported aggregate |
| Safety | Code checks on attempted and executed actions; refusal check | Judge, then a red team (agent-threat-modeler) | Treating 3 of 3 blocked attacks as proof |
| Multi-turn behaviour | Simulated user plus rule checks ("ambiguity → clarifying question") | Judge ranks transcripts for expert review | A simulator that is too cooperative |

**How many tasks and trials**

| Goal | Tasks | Trials per task | Basis |
|---|---|---|---|
| Find failures (week 1) | 20–50, mostly from real failures | 1–3 | Any failure teaches; claim no rates |
| Report a rate within ±10 points | 60–100 | 3 if outputs vary | Wilson half-width at 50–80% |
| Report a rate within ±5 points | 250–400 (in the held-out split, for a release claim) | 3 | Same |
| Detect a 5-point gain between versions | Paired: about 300 at d = 0.10; unpaired about 900 per version | 3 | MDE ≈ 2.8 × √(d / n); two-sample power |
| Claim critical-failure rate < 1% with no failures seen | About 300 independent tasks (scenarios, or n_eff) | 1+ | Rule of three: upper bound ≈ 3/n |
| Reliability of a side-effecting agent | As above | 3–8; report pass^k | pass^k needs trials per task well above k |

**How strict about the path**

| Situation | Rule |
|---|---|
| Forbidden action, missing confirmation before an irreversible step, skipped precondition, blown budget | Hard fail |
| Order matters for specific pairs (authenticate before query, quote before charge) | Check precedence of those pairs only |
| Several valid routes | Required tools ⊆ called tools; report extra calls as precision |
| Extra steps, retries, tokens | Soft efficiency score; report it, don't gate on it unless it breaks a budget |

**Which reliability number**

| Situation | Report |
|---|---|
| User gets one attempt, or actions have side effects | pass^k (k = 3 to 8) beside pass@1 |
| A verifier lets the system retry until success (tests, validators) | pass@k |
| Choosing between training checkpoints | pass@k |
| Always | pass@1 with an interval and the error rate |

**Judge setup**

| Situation | Setup |
|---|---|
| Reference answer and narrow rubric | A smaller judge may do; measure agreement first |
| No reference (faithfulness, helpfulness, policy) | Strongest affordable judge, different family from the agent |
| Choosing between two versions | Pairwise comparison, both orders, win rate |
| Gating | Absolute criteria with a calibrated pass/fail decision |
| Not yet calibrated | Use it to rank outputs for human review only |
| High-stakes run (model migration, launch) | Median of three judges; spread ≥ 0.4 on a 0–1 scale goes to a human |

**CI tiers by PR volume**

| PRs touching prompts, tools, models or datasets | Pre-merge | Nightly | Release |
|---|---|---|---|
| A few a week | Critical subset with deterministic scorers, then the judge suite on the dev split (path-filtered) | — | Hard checks on all tasks; release rates from held-out; consensus judging |
| Dozens a day | Critical subset with deterministic scorers, 1 trial (agent calls still cost) | Full judge suite on the dev split | Same as above |

## Output

**Eval plan.** Fill [templates/eval-plan.md](templates/eval-plan.md). Open with a five-line summary: the decision, the suite size and why, the hard gates, the three biggest risks the plan addresses, and what to build first. Then fill every section. Each number either cites its basis (a computed interval or a named heuristic) or is labelled an assumption to revisit. Include the dimension table, task composition table, scorer table, calibration plan, metrics and statistics, gates, safety slots, operations and rollout.

**Eval review.** Fill [templates/eval-review.md](templates/eval-review.md): a verdict line ("this suite can / cannot currently detect X"), findings ordered by severity (Critical: the suite can pass while the agent fails; High: numbers can't support the decisions made on them; Medium: maintainability and cost), each with location, evidence, impact and fix, then the three changes to make first.

**Both.** When the user has a suite and also wants a plan, write the review first, then the plan. The plan's week-1 rollout fixes the Critical findings before adding any new task.

Keep both concrete: name tools, task types and failure modes from the user's system, not generic placeholders. Where code helps (a predicate, a scorer, a gate), give a short fresh snippet.

## Quality bar

Before returning, check that the output:
- [ ] grades outcomes on final state for every task type that changes something;
- [ ] has negative cases (no tool, nothing to report, refuse, ask, escalate) and stress variants;
- [ ] says where tasks come from before launch (seeds, borrowed real inputs, dogfood, threat-model seeds, reviewed synthetic) and reports the real-input slice separately;
- [ ] encodes only policies whose owner has signed them off;
- [ ] fixes the clock and freezes live read data, and tests lost acknowledgements on money and booking writes;
- [ ] gives each task success criteria, tags and a dataset version, with expected answers not generated by the model under test;
- [ ] puts every rule-decidable quality in code, with hard checks gating rather than averaged;
- [ ] gives each judge a versioned rubric with defined levels, and a calibration plan with κ and false-pass rate, before it gates;
- [ ] fails trials on forbidden actions and skipped preconditions without demanding one exact path;
- [ ] stubs or sandboxes write tools, starts every trial clean, and is shown to fail against a deliberately broken agent;
- [ ] counts errored trials as failures and reports the error rate;
- [ ] runs multiple trials and reports pass^k for side-effecting or customer-facing agents;
- [ ] puts an interval and task count on every rate, sizes the suite for the decision, and compares versions paired;
- [ ] says which split each number comes from, sizes the held-out split for the release claim, and counts effective tasks where variants cluster;
- [ ] states the minimum detectable difference and how it was estimated;
- [ ] includes a reviewed-baseline policy, and release floors that are 100% for critical hard checks;
- [ ] estimates cost per run including agent inference, with trial counts set by risk;
- [ ] uses gates with zero tolerance for deterministic regressions and rerun-confirmed, sign-tested judge regressions;
- [ ] breaks results down by tag, with cost and latency beside quality;
- [ ] names an owner, the incident-to-task loop and the budgets;
- [ ] lists assumptions and hands off online monitoring and red-teaming to the sibling skills.

## Common mistakes

| Mistake | Fix |
|---|---|
| Recommending an LLM judge for everything | Code checks first; judge only what needs understanding |
| Quoting "LLM judges agree with humans 80–90% of the time" as a property of the user's judge | Agreement is measured per task, chance-corrected; until then judge scores only rank |
| One overall average as the headline | Hard-check pass rate, then per-dimension and per-tag rates with intervals |
| Claiming "99%" or "100% safe" from 30 cases | 29/30 has a 95% interval of about 83–99%; zero failures in n means up to about 3/n |
| Treating 50 tasks × 5 trials as 250 samples | Intervals come from tasks; trials only sharpen per-task estimates and feed pass^k |
| Checking the reply ("I've booked it") | Check the sandbox state |
| Exact tool-sequence matching | Set comparison, ordered pairs only where order matters, efficiency as soft score |
| Scorers that return a pass when the expected list or label is empty | Negative cases assert that nothing was called; missing labels fail loudly |
| Dropping crashed cases from the average | Errored trial = failed trial; report the error rate |
| Lowering the agent's temperature to make evals stable | Evaluate at production settings; stabilise only the judge (temperature 0 where the provider allows it, otherwise fixed prompt plus majority of three samples) |
| Generating expected answers with the agent's own model | Expert-confirmed expectations; synthetic cases are drafts |
| Iterating prompts against the whole suite | Keep a held-out split for release decisions |
| Expected route or answer inside the agent's prompt during replay | The oracle goes to the scorer only |
| Gate that fails on any single flipped judge case | Rerun flips; sign-test the net change; zero tolerance only for deterministic checks |
| Forgetting cost: a "better" version at twice the tokens | Report cost and latency per task beside quality |
| Letting the eval plan drift into monitoring design | Stop at the offline suite and gate; hand off to agent-ops-reviewer |
| Quoting a ±5 interval for the whole suite when the release is decided on a 75-task held-out split | Release intervals come from the held-out split; size it for the claim |
| Counting 6 phrasings of one scenario as 6 independent tasks | Count scenarios, or use n_eff, for bounds and intervals |
| Encoding the eval author's guess at a policy (what counts as consent) as a hard check | Owner signs off first; undecided rules are report-only |
| Calling deterministic pre-merge checks "free" | Scoring is free; agent runs aren't. Budget agent inference per run |
| Live read data and wall-clock dates in tasks | Fixed clock; fixtures or versioned recordings |
| Testing only clean failures of write tools | Inject "committed but timed out" and check for exactly one write |

## Sources

Distilled from a cross-book study guide; book chapters by key:
- EVALS: *AI Evals in Practice* (Caio Incau, 2026), ch1 to ch9, ch11, ch13, ch14, and its companion `evalkit` code (scorers, runner, regression detector, calibration and agreement modules).
- ILLUSTRATED: *An Illustrated Guide to AI Agents*, ch7 (benchmarks, trajectory evaluation, pass@k and pass^k, safety by threat model).
- SYSTEMS: *Systems Thinking for Agentic AI*, ch14 (path and result, negative cases, practical judge rubrics, human failure labels).
- BUILDAPPS: *Building Applications with AI Agents*, ch9, ch10 (component and end-to-end tests, tool recall, precision and parameter accuracy), and its companion evaluation code.
- DEFGUIDE: *AI Agents: The Definitive Guide*, ch8, ch9 (stress personas, early threat tests, traces to benchmarks).
- BUILDAGENTIC: *Building Agentic AI*, ch3, ch4, ch5 (retrieval metrics, rubric grader, tool-selection study).
- MESH: *Agentic Mesh*, ch6; ENTERPRISE: *The Agentic Enterprise*, ch6; DLLMA: *Designing Large Language Model Applications*, ch5; MCP: *AI Agents with MCP*, ch7.

External (checked 2026-10):
- Anthropic, "Demystifying evals for AI agents" (2026-01): https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents
- E. Miller, "Adding Error Bars to Evals" (2024-11): https://arxiv.org/abs/2411.00640
- Zheng et al., "Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena" (2023-06): https://arxiv.org/abs/2306.05685
- Zhu et al., "Establishing Best Practices for Building Rigorous Agentic Benchmarks" (2025-07): https://arxiv.org/abs/2507.02825
- Cemri et al., "Why Do Multi-Agent LLM Systems Fail?" (MAST, 2025-03, rev. 2025-10): https://arxiv.org/abs/2503.13657

All intervals, sample sizes and test probabilities in this skill were computed with standard binomial formulas; the code is in references/statistics.md.
