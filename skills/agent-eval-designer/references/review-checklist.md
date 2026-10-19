# Reviewing an existing eval setup

Work in this order. Each section ends sooner than the next, and the first one finds the defects that make every later number meaningless.

## 1. Can the suite fail? (Critical)

Read the scorer and runner code, especially the early-return branches. These defects let a broken agent pass. Most were found in the companion code of the source books and in related open-source repositories, the rest in hands-on platform labs, so expect them in hand-written harnesses and hosted evaluators too.

| Defect | What to look for | Real instance | Fix |
|---|---|---|---|
| Scorer passes when the expectation is empty | `if not expected_tools: return 1.0` and similar | Both books' tool scorers return a perfect score when the expected tool list is empty, whatever the agent called. The "no tool should be called" cases the books recommend then test nothing (EVALS `ToolCallCorrectness`, BUILDAPPS `tool_metrics` and `param_accuracy`; as read 2026-10-18) [EVALS repo: project/cap08/evalkit/scorers/agent.py] [BUILDAPPS repo: src/common/evaluation/metrics.py] | Mark no-tool tasks explicitly and assert `len(calls) == 0`; make an empty expectation on any other task a dataset error |
| Scorer passes when labels or data are missing | `if not ground_truth: return pass`; `if not trajectory: return 1.0` | EVALS `ContextRecall` passes a case with no ground-truth contexts; `MultiTurnCoherence` returns 1.0 when there is no trajectory; BUILDAPPS `phrase_recall` returns 1.0 when no phrases are listed (as read 2026-10-18) [EVALS repo: project/cap07/evalkit/scorers/rag.py] [EVALS repo: project/cap08/evalkit/scorers/agent.py] [BUILDAPPS repo: src/common/evaluation/metrics.py] | Missing labels or transcripts fail loudly (exception or explicit "unscorable" status counted against the suite) |
| Runner drops errored cases | `except: ... continue` or `return None` in the batch loop, then averaging what's left | BUILDAPPS batch runner prints `[SKIPPED]` and averages the remaining examples, so an agent looks better as it breaks more [BUILDAPPS repo: src/common/evaluation/batch_evaluation.py] | Errored trial = failed trial; report the error rate; stop the run above about 5% errors [EVALS ch2] |
| Platform average over a shrinking denominator | Hosted batch or online evaluators report a mean over the sessions they found, so failed invocations and sessions whose traces never arrived disappear | Lab practice: a sender logged and skipped invocations that threw, and the platform scored only sessions with spans, so the batch average covered an unknown subset | Compare sessions sent, sessions scored per evaluator, and errors. Recompute the headline from per-session results with missing = failed (the scale's floor for a mean score; statistics.md, "Mean scores"), and report sent / scored / errored |
| Judge rubric cannot express the failure | Scale levels that describe only politeness or relevance; a scale copied from a template for another dimension; no level a fluent wrong answer would land in | Lab practice: a ready-made "response quality" judge gave top marks to any polite, on-topic answer; a tone judge kept a faithfulness template's scale | Run the judge on 5 to 10 known-bad outputs (fluent but wrong, off-policy). If any scores at the top level, the judge cannot gate. Rewrite the levels around the failure and add the known-bad outputs to the calibration set |
| Judge errors become silent scores | `except: pass` inside a judge loop | EVALS `ContextRelevance` swallows judge errors, which then count as irrelevant chunks [EVALS repo: project/cap07/evalkit/scorers/rag.py]; other judge scorers turn API errors into a 0.0 "agent failure"; evalkit's concurrent runner scores a crashed scorer as 0 [EVALS repo: project/cap11/evalkit/runners/concurrent.py] | Separate infrastructure errors from verdicts; retry, then mark unscorable |
| Hard check averaged away | Case passes when the *mean* of scorer scores clears a threshold | EVALS runner: a case passes on the average of its scorers, so a failed schema or safety check can be outweighed by good tone [EVALS ch2] | Hard checks are an all-must-pass gate; soft scores are reported separately |
| Grading the reply, not the state | Scorer reads only `final_answer` | Common; the agent says "booked" and nothing was booked | Predicate on sandbox state after the run |
| Oracle leaks to the system under test | Expected answer or route appears in the agent's prompt during replay | DEFGUIDE's replay helper puts the expected handoff and reference answer into the candidate model's prompt [DEFGUIDE ch9] | The oracle goes to the scorer only |
| "Replay" that is not a run | A model is asked to describe the steps it would take | Same helper scores a JSON description of a run, not a run [DEFGUIDE ch9] | Re-execute the agent against recorded or stubbed tool responses |
| Judge's self-reported aggregate trusted | Score taken from a `faithfulness_score` or `pass` field the judge writes | EVALS `Faithfulness` uses the judge's own score field rather than counting supported claims [EVALS repo: project/cap07/evalkit/scorers/rag.py] | Compute the score in code from per-claim or per-criterion verdicts |
| Harness cannot credit correct behaviour | Asking a clarifying question or refusing is scored as failure | BUILDAGENTIC's 0% email-tool result: strong models asked for the missing recipient [BUILDAGENTIC ch5] | Read transcripts behind outlier results; add "must ask" as an accepted outcome |
| Test passes on words already in the input | An assertion that a word appears anywhere in the transcript or messages, when the user's own turn contains it | A support-agent test asserts that "refund" appears in some message; the messages include the user's "Refund?", so it passes whatever the agent does [BUILDAPPS repo: tests/frameworks/langgraph_agents/test_langgraph_customer_support_agent.py] | Assert on the tool call, its arguments and its bounds, never on text that contains the input. Remove the tool once and confirm the test goes red |
| Eval tests a copy, not the system | Tool definitions written into the eval by hand | A tool-choice eval hard-codes input schemas instead of loading the server's tools [MCP repo: ch7/01_simple_evaluation/test.py] | Load definitions from the live server or registry at run time |
| Scorer reads a field nothing writes | Scorers that read case metadata or a trace field, where nobody can name the code that fills it | evalkit's trajectory scorers read tools, iterations and tool errors from metadata nothing in its repository fills, so efficiency scores 0 and the coherence judge passes with "No trajectory" [EVALS repo: project/cap08/evalkit/scorers/agent.py] | A run-record contract: name the writer of every field a scorer reads, and fail loudly when one is missing (datasets-and-harness.md, "Run-record contract") |
| Capped run averaged as if complete | An eval runner with a cost cap that stops early and still reports an average | evalkit's cost-capped runner estimates cost from latency and, once over budget, averages the cases it reached with only a printed warning [EVALS repo: project/cap11/evalkit/runners/cost_aware.py] | Cost from recorded usage; a capped run reports how many tasks ran and is not a valid result |
| A guard that blocks only in its report | Guardrail code that returns the output next to a failing result and leaves the caller to act | evalkit's guardrail pipeline returns the blocked output beside the failing results [EVALS repo: project/cap10/evalkit/production/pipeline.py], and its substring profanity check fails "hello" [EVALS repo: project/cap10/evalkit/production/guardrails.py] | The guard returns a decision and blocks by default. Evaluate what reached the user, and report false-block beside false-pass rates. Guard design belongs to agent-threat-modeler |
| Exits and resumes nobody tested | Exhausted, capped or failed runs returned like finished ones; resume never run in a fresh process | An agent library declares a "max turns exceeded" status but returns an exhausted run like a finished one [RELATED repo: aisuite/aisuite/client.py]; a research graph routes the step cap, completion and errors to one summarise step [BUILDAGENTIC repo: deep_research/deep_research_graph.py]; a teaching agent returns "Max steps reached without completion." as an answer [ILLUSTRATED repo: src/illustrated_agents/agent.py]; an agent template reads its thread store on resume without awaiting it, which only a kill-while-paused test would show [RELATED repo: 12-factor-agents/packages/create-12-factor-agent/template/src/server.ts] | The harness slice (datasets-and-harness.md, "Harness test slice"), and a hard check that each trial's exit status matches its expected exit |
| The agent can edit its own tests or evals | Tests, scorers or eval data inside the agent's write scope; no hash check before scoring | Ng reports a coding agent that modified test code to pass more easily [NG Agentic Coding and Agentic Software Testing Go Together, 2025-09-17] | Read-only suite, human review of changes, hash check before scoring (ci-gates.md, "The agent must not edit its own evals") |

## 2. Do the scorers measure the right thing? (High)

- [ ] Tool scoring is set-based with precision as well as recall. Recall-only set scoring ignores extra calls; a "partial refund" agent that also calls `refund_full_order` passes.
- [ ] Order is enforced only for pairs where it matters, not as an exact sequence.
- [ ] Argument comparison normalises types and formats. Strict dict equality fails `"88412"` vs `88412` (BUILDAPPS `param_accuracy` compares dicts with `==`) [BUILDAPPS repo: src/common/evaluation/metrics.py].
- [ ] Efficiency penalises identical repeated calls, not distinct calls to the same tool. EVALS `TrajectoryEfficiency` penalises any repeated tool name, so looking up two orders counts as redundancy [EVALS repo: project/cap08/evalkit/scorers/agent.py].
- [ ] "Task success" is not a blend of soft metrics. BUILDAPPS `task_success` averages phrase recall and tool recall, so an agent that called the right tool and said nothing useful scores 0.5 [BUILDAPPS repo: src/common/evaluation/metrics.py].
- [ ] Embedding or BLEU-style similarity is not used where exact values matter (IDs, amounts, dates).
- [ ] Negative, stress and safety tasks exist and are tagged.
- [ ] Expected tools exist in the live tool registry; stale cases fail for dataset reasons [EVALS ch8].
- [ ] Mocks can fail (timeouts, empty results, declines).

## 2a. Is the comparison fair? (High)

These three skew a comparison between models or versions without making the suite unable to fail.

| Defect | Symptom | Evidence to look for | Fix |
|---|---|---|---|
| The judge sees which model, prompt or version produced the output | One candidate wins on judge scores but not on code checks; the gap shrinks when names are hidden | Model names, version tags or provider-specific formatting in the judge prompt; a fixed order in pairwise prompts | Blind the judge, randomise order, run both orders. Re-score a sample blind once to estimate the bias in past results |
| The sample was filtered on a success signal | Pass rates far above production; few negative cases; no failures to learn from | The dataset query or export filter (`resolved = true`, thumbs up, no escalation) | Rebuild from all outcomes, tag the old set and report it separately; draw the held-out split from the rebuilt sample |
| Recorded multi-turn conversations replayed against a different model or prompt | The user's turns stop making sense mid-conversation; long or looping transcripts | Replay code that feeds recorded user messages in order regardless of the agent's replies | A validated persona simulator, or scripted turns with branches (datasets-and-harness.md, requirement 10) |

## 3. Can the numbers support the decisions made on them? (High)

- [ ] Every reported rate has a task count and an interval. A "99%" on 30 cases is 83 to 99%.
- [ ] Comparisons are paired on the same tasks and dataset version, with a sign test or bootstrap over tasks.
- [ ] Trials are not counted as independent samples.
- [ ] Repeated trials exist for stochastic, side-effecting agents, and pass^k is reported.
- [ ] A held-out split exists and was not used for prompt iteration.
- [ ] The "best of N experiments" was confirmed on held-out data [EVALS ch13].
- [ ] A 30-case first suite is used as a smoke suite and not quoted as a release rate (statistics.md, "What a 30-case first suite can and cannot show").
- [ ] The agent runs at production settings (model version, temperature, prompt, tools, step limit).
- [ ] Every trial in a run recorded the same prompt and config version, read back from the trial, not assumed from the deploy.
- [ ] Results are broken down by tag; cost and latency sit beside quality.

## 4. Is the judge trustworthy? (High)

- [ ] Rubric has defined levels, three to five criteria, practical questions, reasons before scores.
- [ ] Calibrated on 50+ human-labelled cases from this task, with κ and false-pass rate, not only within-one agreement or correlation. EVALS's calibration and agreement code report neither (as read 2026-10-18) [EVALS repo: project/cap05/evalkit/scorers/calibration.py] [EVALS repo: project/cap09/evalkit/annotation/agreement.py].
- [ ] Calibration set includes fluent-but-wrong outputs and enough failures.
- [ ] Judge from a different family than the agent; lowest-variance sampling it accepts (temperature 0, or fixed prompt plus majority of three where non-default sampling is rejected).
- [ ] Judge model and rubric versions pinned and part of the verdict cache key. EVALS's cache keys on scorer name, output and expected answer only [EVALS repo: project/cap11/evalkit/runners/cache.py]. A judge upgrade then silently reuses old verdicts, and two different questions with the same output share a verdict.
- [ ] Recalibration scheduled and triggered by judge or rubric changes.
- [ ] If prompts are tuned against judge scores, a held-out evaluator nobody tunes against is reported at release (llm-judges.md).

## 5. Does the gate behave? (Medium to High)

- [ ] Cases are keyed by stable IDs. EVALS's detector keys them by the first 100 characters of input, so cases with a shared preamble collide [EVALS repo: project/cap06/evalkit/ci/regression.py].
- [ ] Deterministic regressions block; judge-scored flips are rerun before they count.
- [ ] Tolerance came from three runs of the unchanged system.
- [ ] Baselines are saved by decision, with dataset and judge versions recorded.
- [ ] Model migrations go through the same gate. EVALS `validate_migration` approves whenever the pass-rate drop is within tolerance, however many cases regressed [EVALS repo: project/cap13/evalkit/workflow/migration.py].
- [ ] The suite has an owner, a flaky-case triage, and an incident-to-task loop.
- [ ] The harness slice (resume, stop rules, budget, cancel, kill switch, kill while paused) runs and blocks on failure.
- [ ] The suite is read-only to the agent, and its hashes are checked before scoring.
- [ ] Eval cost and wall time per tier are written down and fit the cadence (ci-gates.md, "The budget line").

## "Our evals pass but production fails"

Go down the table and stop at the first row whose check confirms. In one book's example a chatbot scored 92% on its golden set and 78% on sampled production traffic in its first week. The gap came from edge-case fee questions, mixed languages and pasted error messages that the golden set lacked [EVALS ch10].

| Symptom or finding | Likely cause | Check | Fix |
|---|---|---|---|
| Suite has never failed a known-bad version | Scorers that cannot fail (section 1) | Run the suite against a deliberately broken agent (no tools, wrong tool, empty reply) | Fix early-return branches; add this "broken agent" run to CI as a canary for the suite itself |
| Offline score rises while complaints or escalations rise | Treat the instrument as broken until explained: a shrinking denominator, mixed prompt versions, reference-free judges rewarding wrong answers, or tuning to the dev set | Sessions sent vs scored (section 1); one prompt and config version per run; the divergence list of high reference-free scores with failed reference-based or state checks; the held-out evaluator's score | Fix whichever check fails. Every report shows one production signal (complaint or escalation rate, supplied by agent-ops-reviewer) beside the offline headline; the monitoring itself stays with that skill |
| Production inputs look different | Friendly or stale test set [SYSTEMS ch14] | Compare length, language, task mix, pasted content, multi-intent rate between suite and a sample of production traces | Add sampled production cases and the stress variants; weight tasks by traffic mix |
| Failures happen mid-conversation | Suite is single-turn; simulator too cooperative [EVALS ch8] | Compare turns, clarifications and volunteered information against real conversations | Multi-turn tasks with persona simulators, adversarial personas |
| Users report "it said it did X" | Reply graded, not state | Look for scorers that read only the final answer | State predicates; reply-matches-actions check |
| Intermittent failures users can't reproduce | Single trial per task | Rerun failing production inputs (de-identified) 3–5 times in the eval harness, with write tools stubbed; above about 80% failure means a systematic bug [BUILDAPPS ch10] | k ≥ 3 trials; report pass^k |
| Tool errors, timeouts, partial data in production | Mocks always succeed | Inspect the mock layer | Fault injection in some tasks |
| Score went up as prompts were tuned, production didn't | Overfit to the dev set [EVALS ch14] | Score the held-out split; if none, write 30 fresh tasks from recent traffic, de-identified first (datasets-and-harness.md, "Real user data") | Held-out split for release decisions |
| Users report wrong facts, quality scores are high | Only reference-free judges (helpfulness, coherence, tone) | List trials with a high reference-free score and a failed reference-based or state check; if no such check exists, that is the finding | Add reference-based or state checks on a labelled slice; use the divergent trials as calibration cases (scorers.md, "Divergence check") |
| Judge says pass, humans say fail | Uncalibrated or lenient judge | Label 50 recent production outputs; compute false-pass rate | Rewrite rubric with practical questions; recalibrate |
| Eval and production configs differ | Different model version, temperature, prompt, tool list, context or memory state | Diff the configs | Run evals from the production config |
| Suite fine, production degrades over weeks | Drift in inputs, tools or the model behind an alias | Version pins; compare this month's production failures to the suite's tags | Incident-to-task loop within a day; pin model versions; online monitoring via agent-ops-reviewer |
| Average fine, one segment terrible | One number hides a tag | Break down by tag, tenant, language, tool | Gate on critical tags separately |
| Runs that "finished" but did nothing, or reports that stop halfway | Capped or failed runs leave through the success path | Read status and stop reason in those sessions' run records; force each stop in a test | Harness slice; exit status as a hard check; the harness fix goes to agent-harness-designer |
| Scores jumped after the agent got write access to the repository or eval folder | The agent edited tests or eval data | Diff tests, data, scorers and judge prompts against the baseline's hashes | Read-only suite; hash check before scoring |
