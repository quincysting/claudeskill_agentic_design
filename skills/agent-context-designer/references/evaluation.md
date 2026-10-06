# Evaluating retrieval, memory and context

Depth for Procedure step 9. This covers the metrics specific to this skill. Judge calibration, dataset operations, CI gates and statistics go to agent-eval-designer. Citation keys are expanded in SKILL.md under Sources.

Contents: 1 Test set · 2 Retrieval metrics · 3 Generation metrics · 4 Which stage to fix · 5 Agentic retrieval paths · 6 Memory tests · 7 Context and cache metrics · 8 Gates

## 1. Build the test set

Record, per case: query, retrieved contexts (with IDs and ranks at each stage), answer, plus ground-truth contexts and an expected answer where you have them [EVALS ch7].

Cover these slices explicitly:

| Slice | Why |
|---|---|
| Factual lookups | Baseline; strict relevance |
| Exploratory / broad questions | Tolerate broader context; different thresholds [EVALS ch7] |
| Identifier queries (error codes, SKUs, names) | Catch dense-only retrieval |
| Multi-hop / multi-document | Decomposition and agentic loops |
| **Unanswerable from the corpus** | Abstention; large models often answer when they should abstain (provider-notes.md, Sufficient Context) |
| Stale-version traps (old and new policy both indexed) | Freshness and version handling |
| Undated near-duplicates (old and new wiki pages on one topic, no version field) | Staleness detection (retrieval-pipeline.md §2.5) |
| Cross-source conflicts (official doc against a case card or forum answer) | Trust order and per-source quotas (retrieval-pipeline.md §3.4) |
| Per permission scope (tenant, role) | A correct filter must not look like a recall failure |
| Inputs that need no retrieval (greetings, chit-chat) | Forced retrieval mishandles them [BUILDAGENTIC ch2] |

Start with a few dozen real failing questions from logs, then grow it. Generating questions from the same chunks you train or tune on inflates scores. One book's fine-tuned embedder held recall@10 at 0.96, but its test questions were generated the same way as its training pairs [BUILDAGENTIC ch9 §Case Study 17: Fine-Tuning Matryoshka Embeddings].

## 2. Retrieval metrics

**With labels** [BUILDAGENTIC ch3 §Evaluating Evidence Retrieval]:
- **recall@k**: share of the gold contexts present in the top k. Measure it at each stage (first-stage candidates at ~50, reranked top k, chunks actually placed in the prompt), so you know which stage loses evidence.
- **precision@k**: share of the top k that is relevant. When only one document is relevant, its ceiling falls as k grows, so read it alongside recall.
- **MRR**: rank of the first relevant item. Best for single-document answers.
- Break all of these down by source, domain, query type and permission scope.

**Without labels:** context relevance, where an LLM judges each retrieved chunk against the query [EVALS ch7]. Judge errors must fail loudly; don't count them as "irrelevant chunk".

```python
def recall_at_k(ranked_ids, gold_ids, k):
    if not gold_ids:
        raise ValueError("case has no gold contexts; label it or move it to the unanswerable set")
    return len(set(ranked_ids[:k]) & set(gold_ids)) / len(gold_ids)
```

## 3. Generation metrics

- **Faithfulness:** split the answer into claims and check each against the retrieved context (8 of 10 supported scores 0.8). **Answer relevance** and **completeness** score the rest [EVALS ch7].
- **Abstention:** on unanswerable cases, did it say "not found"? On answerable cases, did it avoid needless abstention?
- **Citation correctness:** do the cited IDs support the claims they are attached to?
- Cost: faithfulness takes about one call plus one per claim. 10,000 queries a day with six claims each is about 70,000 judge calls. In production, sample (EVALS suggests 5%) and read the result as a population rate [EVALS ch7].
- Judge with a different model family from the generator, because judges favour their own style [EVALS ch7].

## 4. Which stage to fix

| Context relevance | Context recall | Faithfulness | Completeness | Diagnosis | Fix first |
|---|---|---|---|---|---|
| Low | any | Low | any | Noise retrieved; the generator invents on top | Retrieval: chunking, filters, hybrid search, missing documents |
| High | any | Low | any | Good evidence ignored | Generation: grounding instructions, model |
| High | any | High | Low | Faithful but partial | More or better-ranked chunks, or synthesis across them |
| High | Low | any | any | Relevant but incomplete retrieval | Recall: depth, rewriting, better search |

*Adapted from [EVALS ch7].* In one team's 400 diagnosed failures, about 55% were retrieval, 25% generation and 20% mixed. The mixed ones are the most dangerous because they sound plausible [EVALS ch7]. Track retrieval latency alongside quality.

## 5. Agentic retrieval: evaluate the path too

| Check | Metric |
|---|---|
| Searched when it had to | Share of must-search cases with ≥1 search call (agents skip optional tools [BUILDAGENTIC ch5 §Evaluating Our Agents on Response Quality and Instructional Alignment]) |
| Chose the right source | Source-selection accuracy against labels |
| Hops | Distribution of hops and tool calls; outliers |
| Stop reason | Answered / abstained / budget exhausted; budget exhaustion must end in an abstention or escalation, never an answer |
| Cost | Tokens, latency and cost per task against the fixed-pipeline baseline (expect multiples; see retrieval-pipeline.md section 4) |

## 6. Memory tests

Use the five abilities from LongMemEval as the template (external; provider-notes.md): **information extraction, multi-session reasoning, temporal reasoning, knowledge updates, abstention**. Home-grown suites usually miss the last two.

| Test | Construct | Pass |
|---|---|---|
| Write precision / recall | Scripted conversations with known facts that should and shouldn't be stored | Precision, recall and F1 of the memory updates against the expected set |
| Retrieval accuracy@k | Queries with expected memory items | Expected item in the top k [BUILDAPPS ch9] |
| Knowledge update | Session 1: "I'm vegetarian"; session 3: "I eat fish now" | Old fact superseded, new one used, no contradiction injected |
| Stale preference | A preference changed weeks ago | The outdated value is not returned [BUILDAPPS ch9] |
| Similar-but-irrelevant | A memory that shares phrasing but not meaning | Not retrieved [BUILDAPPS ch9] |
| Temporal | "What did I ask you last Tuesday?" | Correct by timestamp |
| Abstention | Ask about something never said | "I don't have that" instead of an invented answer |
| Cross-scope leak | User A's fact, queried as user B, and as a team agent | Never returned |
| Deletion propagation | Delete a fact, then query by key and by semantic search, and check summaries | Gone everywhere (memory-design.md deletion map) |
| Poisoned input | A tool output or document that contains "remember that…" | Not persisted as active memory |
| Spans compaction | A fact stated before compaction, needed after it | Still used correctly |
| Tried-step repeat | The user reports a step failed at turn 4; the same problem continues to turn 30, past a compaction | The agent never re-suggests that step as new; the ledger shows it |
| Task switch | The user moves to an unrelated problem mid-chat | The current-task line changes, the old ledger is closed, and steps from the old problem are not applied to the new one |
| Scale and failure | Store grows 10-100x; store down; corrupted record | Latency within budget; graceful degradation [BUILDAPPS ch9] |

Memory often looks fine in single-turn demos and fails after summarisation or weeks of accumulation [DEFGUIDE ch10]. Run multi-session scripts, not single prompts.

## 7. Context and cache metrics

- **Cache hit rate** = cache-read input tokens / total input tokens, per call type. A sudden drop usually means a prefix changed (see the breaker list in context-assembly.md).
- **Tokens per bucket** at p50 and p95, against budget; flag buckets that hit their ceiling often.
- **Cost and latency per task**, not per call. Agent loops multiply calls.
- **Compaction survival:** the share of must-survive items still honoured after compaction, from scripted long runs.
- **Length degradation curve:** quality on the same task at increasing context sizes. It tells you where to set the compaction trigger.

## 8. Gates

- Every addition (query rewriting, reranker, contextual chunk headers, GraphRAG, agentic loop, long-term memory, compaction change) ships with a before/after on the relevant slice, plus cost and latency.
- Keep additions that move the metric they target without regressing the others. Remove ones that don't.
- Re-run the retrieval suite on re-indexing, embedder changes and chunking changes. Re-run the memory suite on write-policy or schema changes.
