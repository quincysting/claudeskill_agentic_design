# Scorers

Pick a scorer per quality, not per eval. Each scorer returns a normalized score, a pass flag and a readable reason. "Correct but verbose" and "wrong" need different fixes, and a bare 3/5 is not actionable [EVALS ch2][EVALS ch5]. Every scorer needs a ground truth, rules or a rubric, plus a target value. Without them you are guessing [BUILDAGENTIC ch3].

Andrew Ng splits eval targets into two classes. Tasks with one right answer get a labelled test set. Free-form output gets an LLM judge with a rubric, which he found better than nothing but at times too noisy to tell whether a tweak helped [NG We Need Better Evals for LLM Applications, 2024-05-29]. These are the code and judge rungs of the ladder below. Move every quality you can into the first class, and treat a judge-scored difference on one tweak as a tie until paired reruns confirm it (ci-gates.md, "Gate rules").

## The ladder

```
quality can be stated as a rule? ── yes ──> code check (hard or soft)
        │ no
reference answer exists? ── yes ──> embedding similarity: ≥0.95 pass, <0.5 fail, middle band ↓
        │ no                                                                         │
        └────────────────────────> rubric LLM judge <────────────────────────────────┘
                                         │
                       calibrated against human labels? ── no ──> rank for human review only
                                         │ yes
                                     use (recalibrate when judge or rubric changes)
```

Cost per verdict, mid-2026 prices [EVALS ch11]: code check free and under 1 ms; embedding comparison about $0.0001; small-model judge $0.001 to 0.005; mid-size judge $0.005 to 0.02; claim-level faithfulness $0.02 to 0.10; human annotation $0.50 to 5.00. Run cheap checks first so clear failures skip the judge. Cache verdicts on unchanged outputs, and key the cache on judge model and rubric version too.

DEFGUIDE argues against one generative judge for everything: slow, expensive, inconsistent. Put small classifiers and embedding models in between [DEFGUIDE ch9]. EVALS's "about 60% deterministic, 40% judge" split is a heuristic with no data behind it [EVALS ch4]. Push as much into code as the qualities allow.

## Scoring level

Each scorer reads one level of evidence. Pick the level before you pick a scorer or a platform evaluator type, because a scorer given the wrong level can't see the failure.

| Level | Evidence it sees | Typical scorers |
|---|---|---|
| Tool call | One call's arguments and the context just before it | Argument accuracy, wrong tool chosen |
| Turn (one trace) | One reply and the context before it | Faithfulness, tone, reference answer, required facts |
| Session | The whole trajectory and the final state | Goal completion, expected tool set, precondition order, assertions |

## Deterministic checks for agents

Most agent qualities are rule-decidable [DEFGUIDE ch9][SYSTEMS ch14]:

| Check | Hard or soft | Implementation note |
|---|---|---|
| Final state matches success predicates | Hard | Query the sandbox, DB fixture or recorder after the run |
| No unintended side effects | Hard | Diff the full state, not just the target record ("no other order changed") |
| Exactly one write per intended action | Hard | Count charges or bookings in the final state, including after injected timeouts and retries (datasets-and-harness.md, "write succeeded, response lost") |
| Required tool called | Hard if the outcome depends on it | Set membership |
| Forbidden tool attempted | Hard | Count attempts, not only executions |
| No tool on a no-tool task | Hard | `len(calls) == 0`, never "expected list empty → pass" |
| Precondition order (auth before query, quote before charge, confirm before irreversible action) | Hard | Check that the first index of A is before the first index of B, only for listed pairs |
| Confirmation obtained before irreversible action | Hard | Transcript shows a user turn approving the exact action and amount. What counts as consent is a product or legal decision; encode it only after the owner signs it off |
| No write while required information is missing | Hard | Zero write calls before the missing field appears in a user turn; question quality is a separate soft score |
| Step, tool-call, token or cost budget | Hard at the limit, soft below | Counters from the transcript |
| Schema valid | Hard | Full JSON Schema validator, with `required` set |
| Handoff to the right queue or agent | Hard | Compare the routing decision with the expected route |
| Reply contains required facts (amount, ID, date) | Hard or soft | Normalise numbers and dates before matching |
| Reply matches executed actions (no "done" without the write, stated amount = executed amount) | Hard | Extract amounts, plan names and IDs from the reply and compare with the final state; a judge criterion ("does the reply claim an action not in the executed-call list?") covers free-form claims once calibrated |
| Forbidden content (PII, internal notes, competitor names) | Hard | Regex or classifier. The same check can serve as a production guardrail [EVALS ch4] |
| Tests pass (coding agents) | Hard | Run the repo's tests. A broken-then-fixed test is the check [DEFGUIDE ch9][ILLUSTRATED ch7] |
| Same call under an irrelevant change (paraphrase, reordered details, an added greeting) | Hard on gating tasks, else soft | Run the variants of one scenario and compare tools and normalised arguments. FASTGENAI's property tests cover minimum functionality, invariance under irrelevant edits and the expected direction of change [FASTGENAI ch11] |
| Expected exit status | Hard | `status == expected_exit` from the run record; a capped or cancelled run never passes as `completed` (datasets-and-harness.md, "Run-record contract") |

Outcome means state. An agent can say "done" when nothing changed, or claim it lacked access after fetching the data [DEFGUIDE ch8]. Expected tool calls with parameters catch, for example, a full-order refund where only the damaged item should have been refunded [BUILDAPPS ch9].

## Trajectory scoring

Two agents can give the same correct answer, one with a single tool call and one after wrong tools and retries. An output-only eval scores them the same [EVALS ch8]. In one fintech support agent, an 88% resolution rate hid that about 15% of successes needed three or four repeated lookups and about 8% called unrelated tools first: brute-force success that a small tool API change would break [EVALS ch8]. Three failure types pass an outcome check: a lucky guess, many calls where one would do, and overthinking before the right call [ILLUSTRATED ch7].

Score the path on three axes [ILLUSTRATED ch7][BUILDAPPS ch9]:
1. **Right tools with valid arguments.** Tool recall = expected ∩ called / expected. Tool precision = expected ∩ called / called. Argument accuracy = expected calls matched with the right arguments / expected calls. Normalise types (`"88412"` vs `88412`), case, whitespace and date formats before comparing; use a judge only for free-text arguments such as search queries.
2. **Efficiency.** Calls, steps, repeated identical calls, reasoning tokens, cost. Report it as a soft score. Do not penalise distinct calls to the same tool with different arguments; penalise identical repeats.
3. **Coherence.** Each step follows from the previous result; no contradiction or goal drift. This needs a judge. If there is no transcript to judge, that is a harness error, not a pass.

Strictness:
- Fail a trial for forbidden actions, skipped preconditions and blown budgets.
- Compare tool **sets** by default. Use ordered comparison (longest common subsequence for partial credit) only where order carries meaning [EVALS ch8].
- Never require one exact sequence; it punishes valid routes the author did not foresee (Anthropic, external, 2026-01).
- Count agent-caused tool errors (bad arguments, wrong IDs) apart from infrastructure errors (timeouts, 5xx) [EVALS ch8].

```python
import json

def tool_scores(calls, expected, expect_no_tool=False):
    """calls: [(tool_name, args_dict), ...] in order; expected: list of tool names.
    Returns (hard_fail_reason or None, soft scores)."""
    names = [t for t, _ in calls]
    if expect_no_tool:
        return ("tool called on no-tool task" if names else None), {}
    if not expected:
        raise ValueError("task has no expected tools and is not marked expect_no_tool")
    c, e = set(names), set(expected)
    keys = [(t, json.dumps(a, sort_keys=True)) for t, a in calls]
    return None, {"tool_recall": len(c & e) / len(e),
                  "tool_precision": len(c & e) / len(c) if c else 0.0,
                  "identical_repeats": len(keys) - len(set(keys))}  # same tool, same args

def precedes(names, first, then):
    """Hard precondition: `first` occurs before the first `then`, if `then` occurs at all."""
    return then not in names or first in names[: names.index(then)]
```

## Answer content with a reference

- **Required facts.** List the facts the answer must contain (amount, ID, deadline) and check them after normalising. EVALS stores these as metadata and checks with a contains-all scorer [EVALS ch3].
- **Embedding pre-filter.** Cosine ≥ about 0.95 counts as a pass and < 0.5 as a fail; only the middle band goes to a judge [EVALS ch4]. For paraphrase thresholds start near 0.85 and tune on observed false passes and false fails [EVALS ch4]. Never rely on embeddings where exact values matter: "refund $49" and "refund $94" embed almost identically.
- **Divergence check.** When a trial has both a reference-free score (helpfulness, coherence, tone) and a reference-based or state-based one, list the trials where the first is high and the second fails. These are confident wrong answers: an agent that invents an account balance fluently can score top marks on helpfulness and zero on correctness. Use them as the first fluent-but-wrong cases in judge calibration (llm-judges.md, calibration step 1). A suite with only reference-free judges cannot see this failure.

## LLM judge, pairwise ranking

See llm-judges.md for rubric design and calibration. Use pairwise or group ranking ("A is better than B") to choose between versions of open-ended output. It is judged more consistently than absolute scores and aggregates into a win rate [ILLUSTRATED ch7][DEFGUIDE ch9]. Swap the order on every comparison to cancel position bias. Use calibrated absolute criteria for gates.

## RAG inside an agent

Score retrieval and generation separately, or you cannot tell which to fix. Record the query, retrieved contexts and answer per trial, plus ground-truth contexts and an expected answer where you have them [EVALS ch7].

| Metric | Needs | Notes |
|---|---|---|
| recall@k | Labelled relevant documents | Did the evidence reach the candidate set at all [BUILDAGENTIC ch3] |
| precision@k | Labels | Ceiling falls as k grows when one document is relevant |
| MRR | Labels | Rank of the first relevant document; best for single-document answers |
| Context relevance | Judge per chunk | Reference-free; cheap model is acceptable [EVALS ch7] |
| Faithfulness | Judge per claim | Split the answer into claims, check each against the context; 8 of 10 supported = 0.8. Compute the score from claim verdicts in code, not from a number the judge reports [EVALS ch7] |
| Answer completeness | Judge | Which parts of the question are addressed |

Diagnosis [EVALS ch7]:

| Context relevance | Context recall | Faithfulness | Completeness | Diagnosis | Fix first |
|---|---|---|---|---|---|
| Low | – | Low | – | Noise retrieved, generator invents on top | Retrieval: chunking, filters, hybrid search, missing documents |
| High | – | Low | – | Good evidence ignored | Generation: grounding instructions, model |
| High | – | High | Low | Faithful but partial | More or better-ranked chunks, or synthesis across them |
| High | Low | – | – | Relevant but incomplete retrieval | Recall: larger k, query rewriting, better search |

In one fintech's 400 diagnosed failures, about 55% were retrieval, 25% generation and 20% mixed; the mixed ones are the most dangerous because they sound plausible [EVALS ch7]. Include unanswerable questions, where the right answer is to abstain. Judge with a different model family than the generator. Set relevance thresholds per query type (about 0.7 for factual lookups, 0.3 for exploratory ones) [EVALS ch7]. Build labelled sets per permission scope, or a correct access filter looks like a retrieval failure.

**Size and gate the retrieval slice.** Hit rate at k (a gold document in the top k) is a pass or fail per query, so the Wilson table in statistics.md applies: about 60 to 100 labelled queries give ±10 points. Report recall@k as a soft metric with a floor taken from the reviewed baseline. Make it hard only where a missing document is itself a critical failure. The index needs distractor documents: with one or a few documents every query returns the right one, and retrieval cannot fail (datasets-and-harness.md, "Changing read data, including search indexes").

For agentic retrieval, also score the path. Did it search when it had to? An agent given a search tool but no instruction to use it almost never called it [BUILDAGENTIC ch5]. Which sources did it use, how many hops, and did it stop for the right reason?

### Access checks for retrieval

When the corpus holds documents some users may not see, per-user access is a critical hard check:
- Assert on the retrieved document IDs and their access labels, never on the reply. A reply can omit a restricted document the model was shown, and that document has still leaked into the context.
- The slice has at least two callers with different scopes and at least one restricted gold document that the narrower caller must not retrieve. Count only these scenarios toward the access bound (statistics.md, "Zero failures is not zero risk").
- The run record carries the caller's identity and scopes, and each retrieved document's stable ID and access label (datasets-and-harness.md, "Run-record contract").
- When the interface accepts caller-supplied retrieval parameters (a filter, k, an index name), include a caller who sets their own. Attack design for that goes to agent-threat-modeler.
- Size the slice for the claim instead of accepting a small-n bound. The check is scored in code on retrieved IDs, so it needs no expert or judge time, and its scenarios can be generated mechanically: each restricted document × each caller who must not see it, each pair also run with a caller-supplied filter and k where the interface accepts them. Count each document-caller pair as one scenario and its request variants as variants. 30 restricted documents × 10 non-entitled callers gives 300 pairs, and 0 failures in 300 bounds the rate below 1%; the cost is a few hundred agent runs. That bound assumes the pairs fail independently, but pairs that share one filter tend to fail together. Read the sampled bound as evidence about the agent's behaviour around the filter; the deterministic test below covers the filter code itself.
- Beside the sampled bound, test a deterministic filter deterministically, at the retrieval boundary: for every caller role and every request parameter the interface accepts (filter, k, index name), assert that nothing outside the caller's scope comes back and that no caller or request parameter can widen the scope. A server-set filter is code, so this test covers every role and parameter instead of a sample, and it runs pre-merge.
- When no access mechanism exists, the slice is a capability suite expected to fail. Every stage that exposes the agent to real users or real data is then blocked until the control exists (ci-gates.md, "Floors versus zero tolerance").

## Multi-turn behaviour

Use a persona simulator (see datasets-and-harness.md) and rule checks per stress dimension. Use a judge score only to rank transcripts for expert review, not as ground truth [DEFGUIDE ch8]. Score coherence across turns: no contradiction, no repeated questions, no loss of earlier facts.

## Safety

Split safety evals by who causes the harm; each threat model has its own metric [ILLUSTRATED ch7]:

| Threat model | Metric | What the eval checks |
|---|---|---|
| Misuse: a malicious user asks for harm | Refusal rate (and harm score) | Refuses or stays within policy |
| Manipulation through data: injected instructions in documents, tool results, web pages, poisoned memory | Attack success rate, plus task success under attack | Does not follow injected instructions and still finishes the real task |
| No adversary: the agent errs on a benign task (wrong files deleted, irreversible step without pausing) | Harmful-action rate on benign tasks | Hard checks on attempted actions, confirmation before irreversible steps |

The third is the least standardised and depends on your own tasks and harness [ILLUSTRATED ch7]. Run threat tests alongside behaviour tests from the prototype on [DEFGUIDE ch8]. Small samples say little. "100% mitigation" on one attack per type, or 3 of 3 blocked injections, has an exact one-sided 95% lower bound of about 37% on the block rate (Wilson: about 44%; see statistics.md). Attack design and coverage belong to agent-threat-modeler; this plan reserves the slots, the metrics and the gates. If agents pass a user's identity on to other agents or services, reserve slots for agent-threat-modeler's four delegation property tests (propagation, scope narrowing, agent ceiling, reach) and score them as hard checks.

Refusal tests cover only part of security. The OWASP GenAI red-teaming guide, as AISEC summarises it, has four evaluation areas: the model, the implementation (guardrails, prompts, RAG), infrastructure (APIs, supply chain) and runtime agentic behaviour [AISEC ch10 §Security Controls for AI Systems]. Security tests for all four come from agent-threat-modeler. Where the system has a guardrail, evaluate what reached the user, not what the guard reported, and report its false-block rate beside its false-pass rate (review-checklist.md, "A guard that blocks only in its report").

## Multi-agent systems

The books say least here. Test agents alone, then sub-hierarchies from different nodes, then the whole [ENTERPRISE ch6]. Score per-agent fidelity, global completion and coordination quality [MESH ch6]. Tag failed transcripts with the MAST taxonomy: 14 failure modes in three groups (system design, inter-agent misalignment, task verification), built from over 1,600 traces (Cemri et al., external, 2025). Then the fixes target the right layer.

## Error analysis: where the failures come from

Evals say how often the agent fails; error analysis says where. Ng's order: build a rough prototype, read a handful of outputs, then write evals (code for objective checks, a judge for subjective ones) and keep revising them. He rates a team's discipline with evals and error analysis as the biggest predictor of its progress [NG Improve Agentic Performance with Evals and Error Analysis, Part 1, 2025-10-15]. Error analysis then takes the subpar cases, reads the trace of every step, and counts which step most often did materially worse than a person following the same steps. Start with a few traces read informally, and grow toward a regularly refreshed set with per-step attribution [NG Improve Agentic Performance with Evals and Error Analysis, Part 2, 2025-10-22].

One attribution table per round:

| Step | Failing cases where this step was materially worse than a person | Share of failing cases | Typical failure | Next fix |
|---|---|---|---|---|
| (e.g. search query planning) | (e.g. 14 of 40) | (35%) | (query terms unrelated to the request) | (one change, rerun paired) |

Rules:
- **Pick the fix from the attribution, not from an average.** Fix the step with the largest share, change one thing, and rerun the suite paired against the baseline (datasets-and-harness.md, "First suite").
- **Label failures with categories.** PLAYBOOK's four failure patterns (missing context, unclear rules, wrong tool, no stop condition) make a first label set [PLAYBOOK ch4 §Build It, Test It, Fix It]. Use MAST for multi-agent transcripts (above) and reviewers' classified rejections (llm-judges.md, "Human annotation as an operation"). Each labelled failure becomes a task.
- **Hard checks first, then look.** PRODGUIDE fixes success criteria and cases before building [PRODGUIDE ch13]; Ng reads outputs before choosing metrics [NG Improve Agentic Performance with Evals and Error Analysis, Part 1, 2025-10-15]. Both hold. Known requirements (artifacts, forbidden actions, approvals) are hard checks from the first run, and the qualities worth scoring are found by reading outputs.
- **Remove scaffolding only on evidence.** Ng's signal is that every step does well but the sequence as a whole underperforms a person, so the steps may be too rigid [NG Improve Agentic Performance with Evals and Error Analysis, Part 2, 2025-10-22]. This skill's rule: drop or merge a step only when the traces point there and a paired run on the existing suite shows the simpler workflow is no worse on hard checks and quality. At each model upgrade, rerun the suite with and without the step instead of assuming the newer model copes.
- **Read the run record, not only the reply.** Per-step attribution needs the recorded tool calls, results and stop reasons (datasets-and-harness.md, "Run-record contract"). A trace with a step missing is a harness error.

## Public benchmarks

Use them to shortlist models, not to decide [DEFGUIDE ch8][DLLMA ch5]. Ask: how is it scored, is partial credit given, which harness (ranks flip between harnesses), one run or many, could the test set be in training data, who ran it, were prompts tuned for it, is it saturated (above about 85% differences become noise), at what cost [ILLUSTRATED ch7]. Published agent benchmarks have had grader bugs. τ-bench counted empty responses as successes, and such flaws can misstate performance by up to 100% in relative terms (Zhu et al., external, 2025-07). Ask the same of your own suite: does each task test what it claims, and does the grader accept only real successes?
