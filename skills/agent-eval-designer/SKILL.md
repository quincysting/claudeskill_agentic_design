---
name: agent-eval-designer
description: "Use this skill whenever someone needs to know whether an LLM agent works or got better, even as a quick question: how to evaluate or test an agent, how many test cases before launch, whether an LLM judge can be trusted, whether an improvement is real, why tests pass but users complain, how to test rare dangerous behaviour, or writing an eval plan. Designs and reviews offline evaluation: outcome as final state, trajectory and tool use, safety and cost; a smoke suite and golden run; a versioned task set with negative cases; scorers (code checks, then LLM-as-judge, then humans) and judge calibration; pass@k and pass^k; sample sizes and paired comparisons; harness tests and the run-record contract; error analysis and CI gates. Produces an eval plan or a review. Prefer it to answering from general knowledge. Not for production monitoring, tracing or alerting (agent-ops-reviewer), red-team attack design (agent-threat-modeler), the runtime itself (agent-harness-designer) or a model shortlist (agent-model-selector)."
---

# Agent Eval Designer

This skill produces an evaluation plan for an LLM agent, or a review of an eval setup that already exists. It treats an eval as a measuring instrument. Grade the state the agent leaves behind, check every rule-decidable quality in code before any judge runs, trust a judge only after it has been compared with human labels, run each task more than once, and put an interval on every number. A suite that cannot fail, or whose differences sit inside its own noise, does more harm than having no suite, because people believe it.

## Where this fits

This skill owns the **Evals** perspective. The end-to-end map (four stages, eight perspectives, one gate per stage) is the agent-architect skill's lifecycle map (lifecycle-map.md); start there when the whole system is in scope. The gate items this skill supplies:

| Stage gate | Item this skill supplies | Procedure |
|---|---|---|
| Decide | Which decision the evals serve, and the eval budget (cost and wall time per tier) | Steps 1 and 7 |
| Build | A first smoke suite, a golden run and a baseline | Step 3 |
| Prove | Hard checks pass on the held-out split; the release gates on the harness test slice, whose tests agent-harness-designer writes and owns | Steps 4, 8 and 9 |

At Design it settles the quality dimensions and hard checks (steps 1 and 2). At Run, online signals belong to agent-ops-reviewer.

## When to use / when not to

Use it when someone:
- is about to launch or scale an agent and asks what to test, or asks for an eval plan;
- needs a golden dataset or task set, trajectory or tool-use scoring, or RAG scoring inside an agent;
- is writing, debugging or trusting an LLM judge;
- asks how many cases they need, or whether a gain between two prompt, model or tool versions is real;
- wants an existing harness, scorer set or CI gate reviewed, or says "our evals pass but production fails".

Hand off instead:
- Online evals on live traffic, sampling, tracing, dashboards, alerting, shadow and canary releases go to **agent-ops-reviewer**. This skill delivers the offline suite, baseline and gate that skill builds on.
- Designing attacks and red-team campaigns goes to **agent-threat-modeler**, including security tests of the implementation, infrastructure and runtime behaviour, not only refusals (scorers.md, "Safety"). This skill reserves the safety slots, metrics and gates.
- Building the runtime the agent runs in (loop, run record, checkpoints, budgets, cancellation, kill switch) goes to **agent-harness-designer**. This skill owns the eval side of the run-record contract and puts the harness test slice in the plan; that skill owns the harness side.
- Architecture choices go to **agent-architect**, tool schema fixes to **agent-tool-designer**, retrieval and memory design to **agent-context-designer**, model shortlists to **agent-model-selector** (then use this skill's paired comparison to choose on your own tasks), and ROI to **agentic-business-case**.

A single-call LLM feature with no tools can use the same procedure; skip the trajectory and pass^k parts.

A fixed multi-step read-only agent (router, plan, retrieve, respond; no writes) uses this profile:
- hard checks: the run completes with the expected exit, the route is valid, no retrieval happens on turns that need none (assert on this turn's retrievals, not on state carried from earlier turns), every citation resolves to a retrieved document, and per-user access holds (scorers.md, "RAG inside an agent");
- pass^k only for the consistency of the critical checks (access, for example); one trial on read-only slices in routine runs, three at release;
- no write sandbox and no lost-acknowledgement tests;
- the harness slice reduces to stop rules, step and budget caps, edge faults and cancel, plus resume and kill-while-paused only if the served shape persists state between turns (step 4);
- when the model writes the plan (variable length, fan-out per step), add stress tasks for an empty, an overlong and a duplicate-step plan, and check that each ends in its expected exit. Record the framework's default recursion or step limit as the effective cap (inferred, version named). Plan-length and fan-out limits the runtime does not enforce stay report-only.

The offline suite says nothing about load, concurrency, rate limits or behaviour at 10,000 simultaneous users. Say so in the plan and point to load testing and production monitoring. Language coverage and compliance rules (PCI, privacy) do belong here, as tags and hard checks. If a sibling skill isn't installed, the plan still names the hand-off work and proposes an owner.

## Inputs to gather first

Ask for these or find them in the code. If an answer is missing, write the assumption into the plan's "Assumptions" section instead of stalling.

1. **Task types and mix.** What users ask for, rough share of each, single-turn or multi-turn, number and kind of users.
2. **Tools.** Each tool, read or write, and which writes are irreversible or move money or data. For each write tool: is there a sandbox, test account or stub?
3. **Success per task type**, stated as a final state or a checkable answer, and who can confirm it (a named domain expert).
4. **Worst failures.** Costly, unlawful, embarrassing or irreversible outcomes. These become hard checks and safety slots.
5. **Existing material.** Prompts tested so far, logs or traces, incidents and support tickets, eval code, judge prompts, CI config.
6. **The decision the eval serves.** Launch go/no-go, version comparison, regression protection or model migration. Sizes and gates follow from this.
7. **Constraints.** PR and release cadence, eval budget per run and per month, how long developers will wait for a result, expert hours per month for labelling.
8. **Production settings.** Model and version, temperature, prompt version, tool list, step limit, the interface production serves through, and any settings a caller or console can override. Evals run at these settings. Every model ID found here goes through the pin check (Procedure, step 0) before anything else.
9. **Policies and who owns them.** Rules the agent must follow (approval limits, refund rules, data handling) and the person who decides each. Include the ones that look obvious and aren't, such as whether "card on file" plus "book it" counts as consent to charge.
10. **The harness.** What the runtime records per run (fields, exit statuses, stop reasons), and whether it has checkpoints, budgets, cancellation and a kill switch.
11. **Who may see what (retrieval).** Is every indexed source meant for every user, and who decides? This often decides the verdict. When nobody can answer yet, write the verdict as a condition ("blocked for every user-facing stage if any restricted source is indexed; otherwise only a stage over unrestricted sources is open") and put the question first under "Confirm first".

If the system runs on AWS, map each decision with [references/aws-implementation-notes.md](references/aws-implementation-notes.md).

When reviewing, also collect the dataset (size, sources, version), scorer code, runner, judge prompt, any calibration data, a recent report, and the rule CI uses to pass or fail. Read the code, not just the README: the defects that matter most are in edge-case branches (see [references/review-checklist.md](references/review-checklist.md)).

## Procedure

0. **Pin check (required, before step 1, in plan and review mode alike).** List every model ID the agent and the judge use: pins in code and config, library defaults, and IDs taken from environment variables. Look each one up on its provider's lifecycle page and record the status (active, deprecated with a retirement date, retired), the page and the date checked. Pages (as of 2026-10):
   - Anthropic: https://platform.claude.com/docs/en/about-claude/model-deprecations
   - OpenAI: https://developers.openai.com/api/docs/deprecations
   - Google Gemini API: https://ai.google.dev/gemini-api/docs/deprecations; Vertex AI, page now titled "Model versions and lifecycle | Gemini Enterprise Agent Platform": https://docs.cloud.google.com/vertex-ai/generative-ai/docs/learn/model-versions
   - A cloud platform sets its own dates, which can differ from the model provider's, so check that platform's table too. Amazon Bedrock splits its table in two: https://docs.aws.amazon.com/bedrock/latest/userguide/model-lifecycle.html covers models launched on or after 2026-09-07, with dates on each model card, and https://docs.aws.amazon.com/bedrock/latest/userguide/model-lifecycle-legacy.html covers earlier models, most Claude IDs included. On the legacy page the state can differ by Region, so check the Region you call. An alias such as "latest" moves: record the version it resolved to.

   Then act on the result:
   - **Retired:** requests to it fail, so the existing suite cannot be the system under test and its recent results are unverified. Re-baseline first: the owner picks a current model (agent-model-selector for the shortlist), you run the smoke suite and golden run on it, and you save a reviewed baseline before any comparison or launch claim. Severity High, Critical when it is the production configuration.
   - **Deprecated with a date:** a migration task through the model-migration gate, scheduled before that date (ci-gates.md, "Model migrations, optimisers, best-of-many").
   - **Lookup not possible** (no network, or told not to browse): status "unchecked", labelled assumed, never inferred (a remembered date is not evidence). It sits at the top of "Confirm first" (second only to the access question in Inputs item 11) and is a blocking week-1 item. "What the current numbers mean" says the suite may not run as configured, and the plan names the pinned model "to be confirmed" rather than as the system under test.

1. **Name the decision and the quality dimensions.** List three to six dimensions, typically outcome correctness, path and tool use, safety and policy, communication, and cost and latency. For each, write what a failure looks like, how bad it is, and whether it is *hard* (any failure fails the trial) or *soft* (scored and reported). Hard checks never get averaged with soft scores.

2. **Define success as checkable criteria per task type.** Prefer a predicate on the final state ("one booking exists for these passengers on flight X at ≤ the quoted fare, and the card was charged once") over a judgment of the reply. Mark which criteria are rule-decidable; only the rest may go to a judge. An agent saying "done" is not evidence of anything. Before a policy becomes a hard check, get its owner to sign it off, and record the rule, owner and date in the plan. An undecided policy is an open question: score it report-only until it is decided, so the suite doesn't silently encode the eval author's guess. When the decision itself (a launch, a model choice) depends on unsigned policies (an approval limit, what counts as consent), get them signed before the comparison. Until then, gate only on hard checks that need no policy (exactly one write, the write matches the request, nothing else changed, the reply matches the action) and say the comparison is incomplete. The same holds for a launch: when the main quality dimensions (scope, abstention, groundedness) are report-only because their policies are unsigned, the launch verdict says "incomplete" and lists each signature needed, from whom and by when.

3. **Build the task set.** Follow [references/datasets-and-harness.md](references/datasets-and-harness.md).
   - Sources, best first: real failures (incidents, tickets, bad traces), real logs, expert-written cases, then synthetic drafts that a person reviews. The expected answer must never come from the model under test. Sample logs across all outcomes, never only sessions a success signal marked (a "resolved" click, a thumbs up, no escalation), or the failures the suite exists to catch are missing.
   - Real user data enters a dataset only after personal data and secrets are removed or pseudonymised, and only where the data owner and the customer terms allow eval use and sending the text to the judge's provider and to annotators. Keep access control and a retention period on the sets, and let deletion requests reach them (datasets-and-harness.md, "Real user data").
   - Pre-launch, with no real failures yet:
     - rewrite the existing prompts as seeds;
     - borrow real inputs from wherever people do the task today;
     - harvest logs from a staff dogfood and a small beta (on real users or real data, each is a user-facing stage with the preconditions in step 11);
     - seed safety tasks from a threat model;
     - fill gaps with reviewed synthetic drafts, reporting the real-input slice separately.
     The section "Before launch" in datasets-and-harness.md says how much synthetic is acceptable.
   - Composition: every tool, multi-tool chains, and **negative cases** (no tool needed, nothing to report, must refuse, must ask, must escalate). Add stress variants: ambiguity, frustration, missing information, partial tool failure, slow tools, irrelevant context and injected instructions inside tool output.
   - Each task has an ID, a `scenario_id` shared by its variants, prompt, starting state, clock, success criteria, hard rules, expected exit status, tags (task type, tool, difficulty, source, risk) and the dataset version.
   - In week 1, build a **first smoke suite**: 10 normal, 10 edge and 10 adversarial cases plus failure cases, success as a binary SLA predicate, a baseline saved before the first change, a golden run kept whole, and one change per iteration. At 27 of 30 its interval is about 74 to 97%, so it catches large regressions only and is never the release gate (datasets-and-harness.md, "First suite").
   - Start with 20 to 50 tasks for discovery, then size for the decision with step 8. Hold out a test split scored only at release. Size it for the precision the release claim needs (step 8), not as a fixed share; 20 to 30% of a few hundred tasks gives only about ±7 to 10 points. When the deadline cannot fund the size the claim needs, say so: about 60 held-out scenarios give roughly ±8 points at a 90% pass rate and ±10 at 80%. State the bound that supports, and keep human approval on consequential outputs until the held-out set reaches 250 to 400. An agent with no consequential action has nothing to approve; it uses the staged cohort rule in step 11 instead. When the only data is a small or biased sample (only "resolved" sessions, say), draw the held-out split from the rebuilt all-outcome sample, state when it will reach the needed size, and use the 60-scenario bound until it does.
   - For a tool or feature not built yet, write its tasks first as a *capability suite*, expected to fail at the start. Move tasks into the regression suite once they pass, and report the two suites separately.

4. **Specify the harness.** Each trial starts from a fresh environment. Write tools go to a sandbox or a recorder, never to real systems, and the eval environment holds test credentials only. Every trial records the transcript (tool calls, arguments, results, reply, tokens, cost, stop reason) and the final state. Crashes and timeouts count as failed trials and are reported as an error rate. The oracle (expected answer, expected route) goes to the scorer only, never into the agent's prompt. Run at production settings. Before trusting the suite, run it once against a deliberately broken agent (tools disabled, empty replies; for retrieval, a retriever that returns nothing and one that returns an irrelevant document). It must go red.
   - Run evals through the interface production uses. A server API with persistent threads carries state between turns while the client sends only the new turn, so multi-turn tasks go through that API, not through a direct in-process call to the agent's code. Decide which harness tests apply (resume, kill while paused) from the served shape, not from how the code assembles the agent. When a caller or console can override settings per request (prompts, models, retrieval parameters), log the effective configuration and the dependency versions per trial (datasets-and-harness.md, requirement 6).
   - For retrieval, run against a frozen index snapshot with an ID, distractors included, and key gold documents by a stable source identifier (datasets-and-harness.md, "Changing read data, including search indexes").
   - Fix the clock per task, and serve live read data (prices, seats, inventory, balances) from synthetic fixtures or versioned recordings. A live vendor sandbox runs only as a non-gating smoke test.
   - For write tools that move money or book things, inject "write succeeded, response lost" faults (timeout after commit, duplicate user message, restart mid-task) and check for exactly one write.
   - Validate a multi-turn user simulator against real or dogfood conversations before trusting it. Never replay recorded user turns against a different model or prompt: its replies differ, so the recorded turns stop fitting. Use the simulator or scripted turns with branches.
   - Details for all three: datasets-and-harness.md.
   - If the scorer reads trials from traces or logs instead of the harness's own recorder, the telemetry pipeline is part of the instrument. Check that export is live before sending traffic, wait on each trial's spans with a deadline, sample eval sessions at 100%, and treat a trace that never arrives as a harness fault to rerun and report, never a silently dropped trial (datasets-and-harness.md, requirement 13).
   - Record the prompt and config version each trial actually ran with. A run that mixes versions is a harness error (requirement 6).
   - Agree the **run-record contract** with the harness. Scorers read only fields the harness writes; a missing field makes the trial unscorable and counts against the suite; a trial whose exit status differs from its expected exit fails (datasets-and-harness.md, "Run-record contract").
   - Add the **harness test slice**: resume after a crash, each stop rule, budget exhaustion, cancel mid-run, the kill switch, kill while paused then resume, and faults at the network edge. Scripted model, hard checks, any failure blocks. agent-harness-designer owns how the runtime passes them (datasets-and-harness.md, "Harness test slice").
   - Keep the suite out of the agent's reach. Tests, eval data, scorers and judge prompts are read-only to it, and the runner checks their hashes before scoring. This is a derived control, prompted by Ng's report of a coding agent editing its tests (ci-gates.md, "The agent must not edit its own evals").

5. **Choose a scorer per quality, cheapest adequate first.** Use [references/scorers.md](references/scorers.md) and the decision table below. The ladder is code check, then embedding pre-filter (only with a reference answer), then rubric LLM judge, then human. Ng's two eval classes fit the ladder: one-right-answer tasks get a labelled set and code checks, and free-form output gets a rubric judge, which can be too noisy to settle a single tweak. For trajectories: fail on forbidden actions, skipped preconditions and blown budgets; compare tool *sets* (recall, precision, argument accuracy) and check order only where it carries meaning; report efficiency as a soft score; never require one exact sequence. For RAG inside the agent, score retrieval and generation separately, and treat per-user access as a critical hard check asserted on the retrieved document IDs, never on the reply (scorers.md, "Access checks for retrieval"). For safety, cover the three threat models: misuse, manipulation through data, and benign-task harm. Decide which level each scorer reads (tool call, turn or session), and pair every reference-free judge (helpfulness, coherence, tone) with a reference-based or state check on a labelled slice; only that pairing exposes confident wrong answers (scorers.md, "Scoring level" and "Divergence check").

6. **Design and calibrate each judge.** Follow [references/llm-judges.md](references/llm-judges.md).
   - Write a versioned rubric with three to five weighted criteria and defined score levels, phrased as the workflow's practical questions ("is every claim supported by the retrieved policy?", "should this message be sent?"). It returns JSON with reasons, uses the lowest-variance settings the provider and API version accept (temperature 0 where allowed; on Claude, omit temperature, top_p and top_k, because as of 2026-10 API version 2026-10-21 returns a 400 error for any value on every model and 2023-06-01 does so for non-default values on Claude 4.7 and later; without them, rely on a fixed versioned prompt, structured output and a majority of three samples), and comes from a different model family than the agent where possible.
   - Before a judge gates anything, have a person label 50 to 100 cases from this task, including fluent-but-wrong outputs. Report chance-corrected agreement (Cohen's κ on pass/fail) and the judge's **false-pass rate**. Until then the judge ranks outputs for human review and nothing more.
   - Pin the judge model and rubric version, and recalibrate whenever either changes.
   - When comparing models, prompts or versions, the judge never learns which one wrote an output: strip names and version tags, randomise order, and run pairwise comparisons in both orders.
   - If people tune prompts against judge scores, keep one release-time evaluator they don't tune against (llm-judges.md, "Held-out evaluator").
   - When expert hours are scarce, shrink the judge's job rather than skip calibration. Move every checkable quality into code, calibrate only the criteria that gate, and do one criterion per labelling round, highest risk first.

7. **Set trials and reliability metrics.** Run every task at least 3 times (5 is better) for customer-facing or side-effecting agents, and report pass^k next to pass@1, computed per task and then averaged. Use pass@k only where a verifier allows retries or when comparing training checkpoints. See [references/statistics.md](references/statistics.md). Fit trial counts to the budget by risk: more trials on side-effecting slices, one on read-only slices in nightly runs. Estimate the cost per run from measured agent cost per trial, not just judge cost ([references/ci-gates.md](references/ci-gates.md), "Agent inference cost"). Write cost and wall time per tier into the plan as a budget line at the Decide stage (ci-gates.md, "The budget line").

8. **Do the statistics before promising anything.** Use [references/statistics.md](references/statistics.md).
   - Put a 95% interval (Wilson) and a task count on every rate. For a judge score on a 1-to-N scale, either turn it into pass or fail with a threshold fixed before the run, or bootstrap a paired mean over scenarios; a missing score counts at the scale's floor (statistics.md, "Mean scores").
   - Size the suite for the decision. ±10 points needs about 60 to 100 tasks, ±5 about 250 to 400. Claiming a failure rate below 1% with zero observed failures takes about 300 independent tasks that can produce that failure. Repeated trials of one task don't count toward that. If the count can't be reached before launch, state the bound the suite does support and recommend a human approval on that action until it can (no consequential action: step 11's cohort rule).
   - A zero-failure bound counts only the scenarios that can produce that failure: the ones holding the restricted document, the injected instruction or the forbidden action. Give one row per critical check with its own exercising n. 0 failures in 15 entitlement scenarios bounds that rate at about 18 to 20% whether the suite has 15 scenarios or 2,000; never quote the whole-suite count (statistics.md, "Zero failures is not zero risk").
   - Compare versions **paired** on the same tasks: count the tasks that flipped each way and use a sign test, or bootstrap per-task differences. Resample tasks (or scenarios), not trials.
   - Quote each number from the right split. PR comparisons come from the dev split, release rates and their intervals from the held-out split only, and hard-check results from both.
   - Count effective tasks. Variants of one scenario fail together, so n_eff = n / (1 + (m − 1)ρ). For zero-failure bounds, count scenarios until ρ has been estimated. To raise power, add scenarios, not variants.
   - State the smallest difference the suite can detect: about 2.8 × √(d / n), where d is the share of tasks that flip between runs of the unchanged system, and never below 6/n; headline the larger of the two. Differences inside it are ties.

9. **Define the gates.** Use [references/ci-gates.md](references/ci-gates.md).
   - Deterministic regressions are never tolerated.
   - Release floors are a separate rule. Critical hard checks (money or irreversible action without consent, duplicate write, wrong account, cross-customer data, a document outside the caller's access) need 100% on every trial, on their exercising slices, before any stage that exposes the agent to real users or real data (step 11). Where no money moves, a hard check is critical when its failure is irreversible, reaches someone outside the team with no human check after it, or sits in output a person is expected to act on without re-checking (a missed high-risk clause in a review the lawyer relies on). The owner classifies each hard check. A floor below 100% is allowed only for non-critical hard checks, with each failure listed as a known limitation.
   - A run that ends in the wrong exit with no harm done (a crash, a timeout, an error with no reply) is a hard check but not a critical one: it gets a floor, and each failure is listed. Transient provider errors (rate limits, server errors, network timeouts) are rerun as harness faults and reported in the error rate. The check becomes critical only when a crash can leave a partial irreversible or external action behind (ci-gates.md, "Floors versus zero tolerance").
   - A judge-scored flip counts only if it reproduces on rerun, and the net change is tested with a paired sign test. Set the tolerance just above the spread of three runs of the unchanged system.
   - Pick tiers by PR volume: pre-merge, PR judge run or nightly, release. The release gate adds the held-out split.
   - Deterministic scoring is free, but running the agent to produce transcripts is not. Keep pre-merge to a small critical subset at 1 trial. Re-score cached transcripts only when expectations, labels or scorer code changed; if the prompt, tools, fixtures or clock changed, the transcripts no longer match and the agent reruns.
   - Eval CI holds test credentials and no production secrets. On GitHub, trigger it with `pull_request`, never `pull_request_target`, which runs in the base repository's context with its secrets and a write-scoped token, so checking out or running a fork's code there exposes them (ci-gates.md, "CI safety").
   - Choosing between models or versions: zero critical failures on every trial; the hard-check rate not worse by a confirmed paired difference; pass^k on side-effecting slices not worse by more than the MDE. A difference inside the MDE is a tie, decided on cost per solved task as agent-model-selector defines it, or on agent-ops-reviewer's cost per successful run when review time differs. The bake-off controls (same harness, an equal prompt budget per model, provider defaults set explicitly) come from agent-model-selector (ci-gates.md, "Choosing between models or versions").
   - Save a new baseline only by decision after review. Model migrations go through the same gate as prompt edits.
   - Hand online sampling and alerting to agent-ops-reviewer.

10. **Plan operations.** Name an owner. Every production failure becomes a reviewed task within about a day. Set the labelling budget (about 50 annotations a month is a workable minimum) and the eval spend budget. Do the schedule arithmetic: labels needed (gating criteria × task types × 50 to 100) divided by monthly capacity (hours × measured labels per hour) gives the months until the judge can gate ([references/llm-judges.md](references/llm-judges.md), "Labelling schedule"). Budget expert hours for writing expected outcomes too (gold documents, required facts): scenarios × minutes per scenario. 200 scenarios at an assumed 10 minutes each is about 33 hours. Then add it up: authoring hours plus labelling hours (double-labelled share included) plus calibration rounds, divided by monthly expert hours, gives the month the "Before launch" items can finish. State that month. If it falls after the launch date, start with the held-out split and say so. Check expected tools against the live tool registry at load time, and review quarterly to retire stale cases. Drive iteration with trace-level error analysis: read the traces of failing cases step by step, attribute each failure to the step that did worse than a person would, and fix the largest share first, one change at a time. Remove a scaffolding step only when the traces and a paired run support it ([references/scorers.md](references/scorers.md), "Error analysis").

11. **Write the output and check it** against the Quality bar below. Include a short rollout: what exists by the end of week 1, by launch, and after launch.
   - Every stage that exposes the agent to real users or real data (a dogfood on real data, a pilot, a beta) requires the critical hard checks to pass on their exercising slices first. A smaller cohort is a size stage, not a substitute for a critical check.
   - When a critical check cannot pass by construction because its control does not exist (no per-user access filter while restricted content is in scope, say), the verdict is "blocked for every user-facing stage" and names the missing control. The only alternative is a stage whose data cannot trigger the failure (a corpus with no restricted documents, say), and the plan says so.
   - For an agent with no consequential action, "keep human approval" has nothing to approve. Stage the rollout by cohort instead: for each stage, the cohort size, visible sources and in-product feedback, and the bound that stage's suite supports. The template's §12 has the table.

**Review mode.** When asked to review an existing setup, do the pin check (step 0) first, then steps 1 and 2 from what you find, then work through [references/review-checklist.md](references/review-checklist.md): first the "cannot fail" checks (scorers that pass on empty or missing data, dropped errors, platform averages that lose failed or trace-less sessions, judge scales no wrong answer can fall into, averaged hard checks, oracle leakage, tests that match words already in the input, scorers reading fields nothing writes, guards that block only in their report, untested exits and resumes, an agent that can edit its own evals, agent tests missing from the merge path, assertions on a value the code always sets, test settings identical to the defaults, grounding tests the model's prior knowledge can pass), then statistics, judge calibration and gates. Then check that comparisons are fair (section 2a: a judge that can see which model wrote an output, a sample filtered on success, recorded user turns replayed against another model). Report the pin check's result as a finding wherever a pin is retired, deprecated or unchecked, with the severity and actions step 0 gives, and carry it into "What the current numbers mean". Tag each fact a finding rests on: **seen** (read in code, config or a document supplied for this review; cite file:line or section), **observed** (shown by logs, traces, metrics or a test run), **told** (stated by an owner or user and not checked), **inferred** (follows from seen code plus a library, platform or language behaviour not checked here; name the behaviour and the version it depends on) or **assumed** (no evidence). Severity follows the consequence if an inferred or assumed fact holds, and every inferred or assumed fact also goes under "Confirm first", each with the artefact that would confirm it. A number you cannot recompute because there are no per-task results is reported as "not recomputable", not trusted. A claim that the code lacks a timeout, retry or limit must allow for the client library's defaults: label the impact inferred and name the library version, or "unpinned" when there is no lock file. Unpinned dependencies with no lock file are a reproducibility finding of their own. For "evals pass but production fails", use the symptom table in that file. When the existing pass rule is unstated (how a judge score and a rule combine into pass or fail), record your reading as an assumption and the gap as a finding ("the pass rule is not written down"). Report findings by severity with the exact location, then a fix for each.

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
| Deadline funds only about 60 held-out tasks | 60 | 3 | About ±8 at 90%, ±10 at 80%; state that bound and keep human approval on consequential outputs (no such action: staged cohorts, step 11) |
| Detect a 5-point gain between versions | Paired: about 300 at d = 0.10; unpaired about 900 per version | 3 | MDE ≈ 2.8 × √(d / n); two-sample power |
| Claim critical-failure rate < 1% with no failures seen | About 300 independent tasks (scenarios, or n_eff) that can produce that failure, per critical check | 1+ | Rule of three: upper bound ≈ 3/n, n = exercising scenarios only (0 of 15 → about 18 to 20%) |
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
| Choosing between two versions | Pairwise comparison, both orders, win rate; the judge is not told which version is which |
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

**Eval review.** Fill [templates/eval-review.md](templates/eval-review.md): a verdict line ("this suite can / cannot currently detect X"), findings ordered by severity (Critical: the suite can pass while the agent fails; High: numbers can't support the decisions made on them; Medium: maintainability and cost), each with location, evidence, impact and fix, then "Confirm first", "What the current numbers mean", the three changes to make first, and "Out of scope / handed off". When the verdict depends on a question nobody has answered yet (who may see which sources, Inputs item 11), write it as a condition with both branches, and put the question first under "Confirm first".

**Both.** When the user has a suite and also wants a plan, return one document: the eval-review template's sections first, then the eval-plan template's sections (eval-review.md, "Review plus plan"). The review half ends with the first three changes and then "Out of scope / handed off", so both sit after the findings and before the plan, never at the end of the document. The plan's week-1 build list opens with any open pin-check item, then the Critical fixes, all done before any new task is added. A "Both" review opens at least review-checklist.md (every row of §1), statistics.md and scorers.md. In a file deliverable, plan sections that do not apply can collapse into one "Not applicable" list with a reason for each.

For a chat answer, use the compressed form: verdict, findings table, Confirm first, what the current numbers mean, first three changes, then the plan's summary, task composition, gates and rollout (with its user-facing stages). Offer the full templates on request.

Keep both concrete: name tools, task types and failure modes from the user's system, not generic placeholders. Where code helps (a predicate, a scorer, a gate), give a short fresh snippet.

## Quality bar

Before returning, check that the output:
- [ ] grades outcomes on final state for every task type that changes something;
- [ ] has negative cases (no tool, nothing to report, refuse, ask, escalate) and stress variants;
- [ ] calls a 30-case first suite a smoke suite, with a golden run checked on its hard properties and a baseline saved before the first change;
- [ ] says where tasks come from before launch (seeds, borrowed real inputs, dogfood, threat-model seeds, reviewed synthetic) and reports the real-input slice separately;
- [ ] encodes only policies whose owner has signed them off;
- [ ] fixes the clock and freezes live read data, and tests lost acknowledgements on money and booking writes;
- [ ] gives each task success criteria, tags and a dataset version, with expected answers not generated by the model under test;
- [ ] puts every rule-decidable quality in code, with hard checks gating rather than averaged;
- [ ] gives each judge a versioned rubric with defined levels, and a calibration plan with κ and false-pass rate, before it gates;
- [ ] fails trials on forbidden actions and skipped preconditions without demanding one exact path;
- [ ] stubs or sandboxes write tools, starts every trial clean, and is shown to fail against a deliberately broken agent;
- [ ] if trials are read from telemetry, checks the pipeline before traffic, waits per trial, samples eval sessions at 100% and reports missing traces as harness faults;
- [ ] records the prompt and config version per trial and rejects runs that mix versions;
- [ ] names the run-record fields each scorer reads and their writer, fails trials on missing fields, and checks each trial's exit status against its expected exit;
- [ ] includes the harness test slice (resume, stop rules, budget, cancel, kill switch, kill while paused) as blocking hard checks, with the harness side handed to agent-harness-designer;
- [ ] keeps tests, eval data, scorers and judge prompts out of the agent's write scope, with a hash check before scoring;
- [ ] counts errored and missing trials as failures (recomputing any platform average from per-session results) and reports the error rate;
- [ ] runs multiple trials and reports pass^k for side-effecting or customer-facing agents;
- [ ] puts an interval and task count on every rate, sizes the suite for the decision, and compares versions paired;
- [ ] says which split each number comes from, sizes the held-out split for the release claim, and counts effective tasks where variants cluster;
- [ ] states the minimum detectable difference and how it was estimated;
- [ ] includes a reviewed-baseline policy, and release floors that are 100% for critical hard checks;
- [ ] estimates cost and wall time per run, agent inference included, as a budget line per tier, with trial counts set by risk;
- [ ] plans trace-level error analysis to choose the next fix;
- [ ] uses gates with zero tolerance for deterministic regressions and rerun-confirmed, sign-tested judge regressions;
- [ ] breaks results down by tag, with cost and latency beside quality;
- [ ] names an owner, the incident-to-task loop and the budgets;
- [ ] de-identifies real user data before it enters a dataset, judge prompt or annotation queue, with the owner's consent, retention and deletion rules stated;
- [ ] keeps the judge blind to which model or version produced an output, and samples across all outcomes;
- [ ] for a model or version choice, states the decision rule (critical floors, confirmed paired differences, ties inside the MDE decided on cost per solved task) and hands the bake-off controls to agent-model-selector;
- [ ] recomputes every count in the summary (tasks, findings per severity, labels) from the body before returning;
- [ ] is consistent across sections: the hard gates in the summary, the dimension table, the scorer table and the release gate agree; a hard "no errors in any trial" does not sit beside a release error-rate floor; call and step caps match the plan's own call arithmetic; no uncalibrated judge blocks in any tier; a cap the runtime does not enforce stays report-only until an owner sets it; every critical-bound row has a quality dimension, a scorer, a gate and a place in the stage preconditions; summary hard gates carry the same report-only qualifiers as the dimension and scorer tables; an expected route or answer that encodes an unsigned policy (scope, abstention) is report-only, or limited to clear-cut cases, until the policy is signed;
- [ ] gives each critical zero-failure bound its own row, counting only the scenarios that can produce that failure;
- [ ] lets no user-facing stage (dogfood on real data, pilot, beta) start before the critical hard checks pass on their exercising slices, says "blocked" and names the control when one is missing, and, for an agent with no consequential action, stages the rollout by cohort rather than by human approval;
- [ ] ran the pin check (step 0) first: every model the agent and judge use, defaults included, has a status from its provider's lifecycle page with the page and date checked, or is "unchecked" (assumed), listed at the top of "Confirm first" and in week 1 as a blocking item; a retired or unchecked pin is never named as the system under test, and a retired one is replaced and re-baselined before any comparison;
- [ ] classifies a crash, timeout or no-reply exit as a hard non-critical check (a floor, failures listed, transient provider errors rerun), unless a crash can leave a partial irreversible or external action;
- [ ] for a launch whose main quality dimensions are report-only, says "incomplete" and lists the signatures needed;
- [ ] cites credentials by file:line and kind (for example "messaging app secret literal"), never by value or any fragment of it; the same holds for keys in URLs, logs and saved state, and public vendor defaults may be named. Before returning, searches the draft for every credential literal found in the input and removes each one;
- [ ] lists assumptions and hands off online monitoring and red-teaming to the sibling skills.

In review mode (and the review half of "Both"), also check that the output:
- [ ] ran the "cannot fail" checks in review-checklist.md before statistics and judges;
- [ ] gives each finding its location, evidence, impact and fix;
- [ ] recomputes every reported number from per-task results, missing counted as failed;
- [ ] records an unstated pass rule as an assumption and a finding;
- [ ] writes a verdict that rests on an unanswered question (who may see which sources) as a condition with both branches, and puts that question first under "Confirm first";
- [ ] tags each fact a finding rests on seen, observed, told, inferred or assumed, lists every inferred or assumed fact under "Confirm first", and marks numbers it cannot recompute as "not recomputable";
- [ ] closes the review with the three changes to make first, then "Out of scope / handed off"; in "Both" these close the review half, before the plan begins.

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
| Lowering the agent's temperature to make evals stable | Evaluate at production settings; stabilise only the judge (temperature 0 where the provider and API version allow it; otherwise omit the parameter and use a fixed prompt plus majority of three samples) |
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
| Quoting a hosted evaluator's batch average as the result | It averages the sessions it found. Recompute from per-session results with missing = failed; report sent, scored and errored |
| Gating on a platform's built-in judges | Generic, uncalibrated rubrics: calibrate on your labels first, or use them to rank only |
| Editing a runtime-read prompt while a run is still sending | Pin one prompt and config version per run; assert it before scoring |
| Treating the 30-case first suite as the release gate | It is a smoke suite: 27 of 30 is 74 to 97%. Release numbers come from a held-out split sized for the claim |
| A test that asserts a word appears somewhere in the transcript | The user's own turn may contain it. Assert on the tool call, its arguments and bounds; remove the tool once and watch the test fail |
| Scorers reading fields nothing writes | Run-record contract: name each field's writer; a missing field is unscorable, never 0 or pass |
| Grading a guardrail by what it reported | Evaluate what reached the user; report false-block beside false-pass |
| Never forcing a stop, a cancel or a resume | Harness test slice; a capped or cancelled run never scores as completed |
| Letting the agent under test write to its tests or evals | Read-only suite, reviewed changes, hash check before scoring |
| Picking the next fix from the average score | Trace-level error analysis: fix the step with the largest share of failures |
| Treating eval runs as free and instant | Budget cost and wall time per tier at the Decide stage |
| Letting the judge see which model wrote each answer | Strip names and tags, randomise order, run both orders |
| Building the set from sessions marked "resolved" | Sample across all outcomes; the failures are what the suite is for |
| Replaying recorded conversations against a new model | Simulator or scripted turns with branches; recorded user turns only fit the model they were recorded with |
| Bounding a critical failure with the whole suite's count (3/200) when only 15 scenarios can trigger it | Count exercising scenarios only, one row per check: 0 of 15 is about 18 to 20% |
| Starting a pilot before the access or injection checks exist, because the cohort is small | A smaller cohort is a size stage; critical checks pass first, or the verdict is "blocked" with the missing control named |
| Trusting a default model pin without looking it up, or carrying a retired pin as the system under test | Pin check first (step 0) on the provider's lifecycle page; a retired pin cannot run, so re-baseline on a current model before any comparison |
| Making "the run exits with a reply" a critical check | Hard but non-critical: a floor with failures listed, transient provider errors rerun; critical only if a crash can leave a partial irreversible action |
| Keying gold documents by a content hash or a store-assigned ID | Stable source identifier; a frozen index snapshot; re-index means a new dataset version |
| Copying tickets and traces into the eval set as they are | Remove or pseudonymise personal data and secrets first; confirm the data terms allow eval use |

## Sources

These notes draw on the books below. They are independent study notes, not affiliated with or endorsed by the authors or publishers cited. Book chapters by key:
- EVALS: *AI Evals in Practice* (Caio Incau, 2026), ch1 to ch9, ch11, ch13, ch14, and its companion `evalkit` code (scorers, runner, regression detector, calibration and agreement modules).
- ILLUSTRATED: *An Illustrated Guide to AI Agents*, ch7 (benchmarks, trajectory evaluation, pass@k and pass^k, safety by threat model).
- SYSTEMS: *Systems Thinking for Agentic AI*, ch14 (path and result, negative cases, practical judge rubrics, human failure labels).
- BUILDAPPS: *Building Applications with AI Agents*, ch9, ch10 (component and end-to-end tests, tool recall, precision and parameter accuracy), and its companion evaluation code.
- DEFGUIDE: *AI Agents: The Definitive Guide*, ch8, ch9 (stress personas, early threat tests, traces to benchmarks).
- BUILDAGENTIC: *Building Agentic AI*, ch3, ch4, ch5 (retrieval metrics, rubric grader, tool-selection study).
- MESH: *Agentic Mesh*, ch6; ENTERPRISE: *The Agentic Enterprise*, ch6; DLLMA: *Designing Large Language Model Applications*, ch5; MCP: *AI Agents with MCP*, ch7.
- PRODGUIDE: *Agentic AI Systems: The Complete Guide for Building Production AI Agents*, ch13 (30-case first suite, SLA success, baseline, golden run, one change per iteration) and ch16 (run record, kill switch).
- PLAYBOOK: *Agentic AI Playbook*, ch4 (failure cases, four failure patterns).
- FASTGENAI: *Building Generative AI Services with FastAPI*, ch11 (property tests; why model tests are slow and costly).
- AISEC: *Agentic AI for Cybersecurity*, ch10 (the four evaluation areas of the OWASP GenAI red-teaming guide).

NG: Andrew Ng, The Batch letters (deeplearning.ai), cited as `[NG <title>, <date>]`:
- "Why We Need More Compute for Inference" (2024-04-24): https://www.deeplearning.ai/the-batch/why-we-need-more-compute-for-inference
- "We Need Better Evals for LLM Applications" (2024-05-29): https://www.deeplearning.ai/the-batch/we-need-better-evals-for-llm-applications
- "Agentic Coding and Agentic Software Testing Go Together" (2025-09-17): https://www.deeplearning.ai/the-batch/agentic-coding-and-agentic-software-testing-go-together
- "Improve Agentic Performance with Evals and Error Analysis, Part 1" (2025-10-15): https://www.deeplearning.ai/the-batch/improve-agentic-performance-with-evals-and-error-analysis-part-1
- "Improve Agentic Performance with Evals and Error Analysis, Part 2" (2025-10-22): https://www.deeplearning.ai/the-batch/improve-agentic-performance-with-evals-and-error-analysis-part-2
- "Three Key Loops for Building Great Software" (2026-06-26): https://www.deeplearning.ai/the-batch/three-key-loops-for-building-great-software

Code repositories cited as `[KEY repo: path]` in the references (read, not run, 2026-10-18):
- EVALS: https://github.com/PacktPublishing/AI-Evals-in-Practice
- BUILDAPPS: https://github.com/MichaelAlbada/BuildingApplicationsWithAIAgents
- BUILDAGENTIC: https://github.com/sinanuozdemir/building-agentic-ai
- ILLUSTRATED: https://github.com/HandsOnLLM/An-Illustrated-Guide-To-AI-Agents
- MCP: https://github.com/kylestratis/ai_agents_mcp_examples
- APIARCH (*Mastering API Architecture*): https://github.com/masteringapi/attendees
- RELATED aisuite: https://github.com/andrewyng/aisuite
- RELATED 12-factor-agents: https://github.com/humanlayer/12-factor-agents

Practitioner lab notes (AWS AgentCore and data labs, 2026-10).

External (checked 2026-10):
- Anthropic, "Demystifying evals for AI agents" (2026-01): https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents
- E. Miller, "Adding Error Bars to Evals" (2024-11): https://arxiv.org/abs/2411.00640
- Zheng et al., "Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena" (2023-06): https://arxiv.org/abs/2306.05685
- Zhu et al., "Establishing Best Practices for Building Rigorous Agentic Benchmarks" (2025-07): https://arxiv.org/abs/2507.02825
- Cemri et al., "Why Do Multi-Agent LLM Systems Fail?" (MAST, 2025-03, rev. 2025-10): https://arxiv.org/abs/2503.13657
- AWS, "AgentCore Evaluations: Evaluation types" (checked 2026-10-11): https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/evaluations-types.html
- AWS, "AgentCore ground truth evaluations" (checked 2026-10-11, re-checked 2026-10-19): https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/ground-truth-evaluations.html
- Anthropic, Model deprecations, API parameter deprecations (temperature, top_p, top_k removed in API version 2026-10-21, 400 on any value; earlier versions reject non-default values on Claude 4.7 and later; checked 2026-10-25): https://platform.claude.com/docs/en/about-claude/model-deprecations. The same page is the model lifecycle table for the pin check (as of 2026-10).
- Anthropic, "Migrating to API version 2026-10-21", section "Sampling parameters are removed" (checked 2026-10-25): https://platform.claude.com/docs/en/api/migration-2026-10-21
- Model lifecycle pages for the pin check (as of 2026-10): OpenAI, Deprecations: https://developers.openai.com/api/docs/deprecations; Google, Gemini deprecations: https://ai.google.dev/gemini-api/docs/deprecations; Google Cloud, Vertex AI "Model versions and lifecycle" (now titled under Gemini Enterprise Agent Platform): https://docs.cloud.google.com/vertex-ai/generative-ai/docs/learn/model-versions; AWS, Amazon Bedrock model lifecycle (models launched on or after 2026-09-07): https://docs.aws.amazon.com/bedrock/latest/userguide/model-lifecycle.html; AWS, Amazon Bedrock model lifecycle (Legacy) (earlier models; state can differ by Region; checked 2026-10-25): https://docs.aws.amazon.com/bedrock/latest/userguide/model-lifecycle-legacy.html

All intervals, sample sizes and test probabilities in this skill were computed with standard binomial formulas; the code is in references/statistics.md.
