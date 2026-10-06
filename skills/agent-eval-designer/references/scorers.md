# Scorers

Pick a scorer per quality, not per eval. Each scorer returns a normalized score, a pass flag and a readable reason. "Correct but verbose" and "wrong" need different fixes, and a bare 3/5 is not actionable [EVALS ch2][EVALS ch5]. Every scorer needs a ground truth, rules or a rubric, plus a target value. Without them you are guessing [BUILDAGENTIC ch3].

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

For agentic retrieval, also score the path. Did it search when it had to? An agent given a search tool but no instruction to use it almost never called it [BUILDAGENTIC ch5]. Which sources did it use, how many hops, and did it stop for the right reason?

## Multi-turn behaviour

Use a persona simulator (see datasets-and-harness.md) and rule checks per stress dimension. Use a judge score only to rank transcripts for expert review, not as ground truth [DEFGUIDE ch8]. Score coherence across turns: no contradiction, no repeated questions, no loss of earlier facts.

## Safety

Split safety evals by who causes the harm; each threat model has its own metric [ILLUSTRATED ch7]:

| Threat model | Metric | What the eval checks |
|---|---|---|
| Misuse: a malicious user asks for harm | Refusal rate (and harm score) | Refuses or stays within policy |
| Manipulation through data: injected instructions in documents, tool results, web pages, poisoned memory | Attack success rate, plus task success under attack | Does not follow injected instructions and still finishes the real task |
| No adversary: the agent errs on a benign task (wrong files deleted, irreversible step without pausing) | Harmful-action rate on benign tasks | Hard checks on attempted actions, confirmation before irreversible steps |

The third is the least standardised and depends on your own tasks and harness [ILLUSTRATED ch7]. Run threat tests alongside behaviour tests from the prototype on [DEFGUIDE ch8]. Small samples say little. "100% mitigation" on one attack per type, or 3 of 3 blocked injections, has a 95% lower bound around 44% (see statistics.md). Attack design and coverage belong to agent-threat-modeler; this plan reserves the slots, the metrics and the gates.

## Multi-agent systems

The books say least here. Test agents alone, then sub-hierarchies from different nodes, then the whole [ENTERPRISE ch6]. Score per-agent fidelity, global completion and coordination quality [MESH ch6]. Tag failed transcripts with the MAST taxonomy: 14 failure modes in three groups (system design, inter-agent misalignment, task verification), built from over 1,600 traces (Cemri et al., external, 2025). Then the fixes target the right layer.

## Public benchmarks

Use them to shortlist models, not to decide [DEFGUIDE ch8][DLLMA ch5]. Ask: how is it scored, is partial credit given, which harness (ranks flip between harnesses), one run or many, could the test set be in training data, who ran it, were prompts tuned for it, is it saturated (above about 85% differences become noise), at what cost [ILLUSTRATED ch7]. Published agent benchmarks have had grader bugs. τ-bench counted empty responses as successes, and such flaws can misstate performance by up to 100% in relative terms (Zhu et al., external, 2025-07). Ask the same of your own suite: does each task test what it claims, and does the grader accept only real successes?
