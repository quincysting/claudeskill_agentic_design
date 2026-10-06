# Reviewing an existing eval setup

Work in this order. Each section ends sooner than the next, and the first one finds the defects that make every later number meaningless.

## 1. Can the suite fail? (Critical)

Read the scorer and runner code, especially the early-return branches. These defects let a broken agent pass. Every one was found in published companion code for books on agent evaluation, so expect them in hand-written harnesses too.

| Defect | What to look for | Real instance | Fix |
|---|---|---|---|
| Scorer passes when the expectation is empty | `if not expected_tools: return 1.0` and similar | Both books' tool scorers return a perfect score when the expected tool list is empty, whatever the agent called. The "no tool should be called" cases the books recommend then test nothing (EVALS `ToolCallCorrectness`, BUILDAPPS `tool_metrics` and `param_accuracy`) | Mark no-tool tasks explicitly and assert `len(calls) == 0`; make an empty expectation on any other task a dataset error |
| Scorer passes when labels or data are missing | `if not ground_truth: return pass`; `if not trajectory: return 1.0` | EVALS `ContextRecall` passes a case with no ground-truth contexts; `MultiTurnCoherence` returns 1.0 when there is no trajectory; BUILDAPPS `phrase_recall` returns 1.0 when no phrases are listed | Missing labels or transcripts fail loudly (exception or explicit "unscorable" status counted against the suite) |
| Runner drops errored cases | `except: ... continue` or `return None` in the batch loop, then averaging what's left | BUILDAPPS batch runner prints `[SKIPPED]` and averages the remaining examples, so an agent looks better as it breaks more | Errored trial = failed trial; report the error rate; stop the run above about 5% errors [EVALS ch2] |
| Judge errors become silent scores | `except: pass` inside a judge loop | EVALS `ContextRelevance` swallows judge errors, which then count as irrelevant chunks; other judge scorers turn API errors into a 0.0 "agent failure" | Separate infrastructure errors from verdicts; retry, then mark unscorable |
| Hard check averaged away | Case passes when the *mean* of scorer scores clears a threshold | EVALS runner: a case passes on the average of its scorers, so a failed schema or safety check can be outweighed by good tone [EVALS ch2] | Hard checks are an all-must-pass gate; soft scores are reported separately |
| Grading the reply, not the state | Scorer reads only `final_answer` | Common; the agent says "booked" and nothing was booked | Predicate on sandbox state after the run |
| Oracle leaks to the system under test | Expected answer or route appears in the agent's prompt during replay | DEFGUIDE's replay helper puts the expected handoff and reference answer into the candidate model's prompt [DEFGUIDE ch9] | The oracle goes to the scorer only |
| "Replay" that is not a run | A model is asked to describe the steps it would take | Same helper scores a JSON description of a run, not a run [DEFGUIDE ch9] | Re-execute the agent against recorded or stubbed tool responses |
| Judge's self-reported aggregate trusted | Score taken from a `faithfulness_score` or `pass` field the judge writes | EVALS `Faithfulness` uses the judge's own score field rather than counting supported claims | Compute the score in code from per-claim or per-criterion verdicts |
| Harness cannot credit correct behaviour | Asking a clarifying question or refusing is scored as failure | BUILDAGENTIC's 0% email-tool result: strong models asked for the missing recipient [BUILDAGENTIC ch5] | Read transcripts behind outlier results; add "must ask" as an accepted outcome |

## 2. Do the scorers measure the right thing? (High)

- [ ] Tool scoring is set-based with precision as well as recall. Recall-only set scoring ignores extra calls; a "partial refund" agent that also calls `refund_full_order` passes.
- [ ] Order is enforced only for pairs where it matters, not as an exact sequence.
- [ ] Argument comparison normalises types and formats. Strict dict equality fails `"88412"` vs `88412` (BUILDAPPS `param_accuracy` compares dicts with `==`).
- [ ] Efficiency penalises identical repeated calls, not distinct calls to the same tool. EVALS `TrajectoryEfficiency` penalises any repeated tool name, so looking up two orders counts as redundancy.
- [ ] "Task success" is not a blend of soft metrics. BUILDAPPS `task_success` averages phrase recall and tool recall, so an agent that called the right tool and said nothing useful scores 0.5.
- [ ] Embedding or BLEU-style similarity is not used where exact values matter (IDs, amounts, dates).
- [ ] Negative, stress and safety tasks exist and are tagged.
- [ ] Expected tools exist in the live tool registry; stale cases fail for dataset reasons [EVALS ch8].
- [ ] Mocks can fail (timeouts, empty results, declines).

## 3. Can the numbers support the decisions made on them? (High)

- [ ] Every reported rate has a task count and an interval. A "99%" on 30 cases is 83 to 99%.
- [ ] Comparisons are paired on the same tasks and dataset version, with a sign test or bootstrap over tasks.
- [ ] Trials are not counted as independent samples.
- [ ] Repeated trials exist for stochastic, side-effecting agents, and pass^k is reported.
- [ ] A held-out split exists and was not used for prompt iteration.
- [ ] The "best of N experiments" was confirmed on held-out data [EVALS ch13].
- [ ] The agent runs at production settings (model version, temperature, prompt, tools, step limit).
- [ ] Results are broken down by tag; cost and latency sit beside quality.

## 4. Is the judge trustworthy? (High)

- [ ] Rubric has defined levels, three to five criteria, practical questions, reasons before scores.
- [ ] Calibrated on 50+ human-labelled cases from this task, with κ and false-pass rate, not only within-one agreement or correlation. EVALS's calibration and agreement code report neither.
- [ ] Calibration set includes fluent-but-wrong outputs and enough failures.
- [ ] Judge from a different family than the agent; lowest-variance sampling it accepts (temperature 0, or fixed prompt plus majority of three where non-default sampling is rejected).
- [ ] Judge model and rubric versions pinned and part of the verdict cache key. EVALS's cache keys on scorer name, output and expected answer only. A judge upgrade then silently reuses old verdicts, and two different questions with the same output share a verdict.
- [ ] Recalibration scheduled and triggered by judge or rubric changes.

## 5. Does the gate behave? (Medium to High)

- [ ] Cases are keyed by stable IDs. EVALS's detector keys them by the first 100 characters of input, so cases with a shared preamble collide.
- [ ] Deterministic regressions block; judge-scored flips are rerun before they count.
- [ ] Tolerance came from three runs of the unchanged system.
- [ ] Baselines are saved by decision, with dataset and judge versions recorded.
- [ ] Model migrations go through the same gate. EVALS `validate_migration` approves whenever the pass-rate drop is within tolerance, however many cases regressed.
- [ ] The suite has an owner, a flaky-case triage, and an incident-to-task loop.

## "Our evals pass but production fails"

Go down the table and stop at the first row whose check confirms. In one book's example a chatbot scored 92% on its golden set and 78% on sampled production traffic in its first week. The gap came from edge-case fee questions, mixed languages and pasted error messages that the golden set lacked [EVALS ch10].

| Symptom or finding | Likely cause | Check | Fix |
|---|---|---|---|
| Suite has never failed a known-bad version | Scorers that cannot fail (section 1) | Run the suite against a deliberately broken agent (no tools, wrong tool, empty reply) | Fix early-return branches; add this "broken agent" run to CI as a canary for the suite itself |
| Production inputs look different | Friendly or stale test set [SYSTEMS ch14] | Compare length, language, task mix, pasted content, multi-intent rate between suite and a sample of production traces | Add sampled production cases and the stress variants; weight tasks by traffic mix |
| Failures happen mid-conversation | Suite is single-turn; simulator too cooperative [EVALS ch8] | Compare turns, clarifications and volunteered information against real conversations | Multi-turn tasks with persona simulators, adversarial personas |
| Users report "it said it did X" | Reply graded, not state | Look for scorers that read only the final answer | State predicates; reply-matches-actions check |
| Intermittent failures users can't reproduce | Single trial per task | Rerun failing production inputs 3–5 times; above about 80% failure means a systematic bug [BUILDAPPS ch10] | k ≥ 3 trials; report pass^k |
| Tool errors, timeouts, partial data in production | Mocks always succeed | Inspect the mock layer | Fault injection in some tasks |
| Score went up as prompts were tuned, production didn't | Overfit to the dev set [EVALS ch14] | Score the held-out split; if none, write 30 fresh tasks from recent traffic | Held-out split for release decisions |
| Judge says pass, humans say fail | Uncalibrated or lenient judge | Label 50 recent production outputs; compute false-pass rate | Rewrite rubric with practical questions; recalibrate |
| Eval and production configs differ | Different model version, temperature, prompt, tool list, context or memory state | Diff the configs | Run evals from the production config |
| Suite fine, production degrades over weeks | Drift in inputs, tools or the model behind an alias | Version pins; compare this month's production failures to the suite's tags | Incident-to-task loop within a day; pin model versions; online monitoring via agent-ops-reviewer |
| Average fine, one segment terrible | One number hides a tag | Break down by tag, tenant, language, tool | Gate on critical tags separately |
