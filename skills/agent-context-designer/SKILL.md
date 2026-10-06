---
name: agent-context-designer
description: "Design or review what an LLM agent knows at each model call. Covers the retrieval/RAG pipeline (parsing, chunking, hybrid search, reranking, permission filters, agentic retrieval), agent memory (what to remember, write policy, stores, scoping, forgetting, deletion) and context assembly (per-part token budgets, cache-friendly prompt layout, compaction, long-running tasks). Produces a context and memory design with budgets, or a prioritised review of an existing one, plus a plan to evaluate retrieval and memory quality. Use when the user says 'add memory to my agent', 'design a RAG pipeline', 'my agent forgets', 'context window is filling up', 'chunking strategy', 'agentic RAG', 'context engineering' or 'prompt caching layout', or asks why answers ignore retrieved documents. Not for tool schema design (agent-tool-designer), overall architecture (agent-architect), full eval programs (agent-eval-designer), memory-poisoning threat models (agent-threat-modeler) or model choice (agent-model-selector)."
---

# Agent Context Designer

This skill produces a context and memory design for an LLM agent, or a prioritised review of an existing one. The design covers what the agent sees at each model call, where each piece comes from, how many tokens it may use, what gets remembered and forgotten, and how retrieval and memory quality will be measured. Five defaults: the smallest context that supports a grounded answer; a fixed retrieval pipeline before agentic retrieval; deterministic write rules before LLM-curated memory; prompts laid out for the cache; retrieval and generation scored separately.

## When to use / when not to

Use it to:
- design or fix a RAG pipeline (parsing, chunking, embeddings, hybrid search, reranking, filters, citations);
- decide whether retrieval should be a pipeline step or a tool the agent calls (agentic RAG, multi-hop, GraphRAG, text-to-SQL);
- add memory ("remember users across sessions", "my agent forgets"), or clean up memory that has gone stale, duplicated or leaky;
- control a filling context window: trimming, compaction, tool-result bloat, sub-agent context, long-running tasks;
- lay out prompts for prompt caching or cut input-token cost;
- evaluate retrieval or memory quality.

Hand off instead:

| Need | Skill |
|---|---|
| Workflow vs agent, control loop, overall system shape | agent-architect |
| Tool schemas, descriptions and errors, including the search tool's interface | agent-tool-designer |
| A full eval program: datasets, judges, CI gates, statistics | agent-eval-designer (this skill supplies retrieval and memory metrics) |
| Memory poisoning, indirect prompt injection through documents, attack trees | agent-threat-modeler |
| Choosing LLMs or embedding models beyond the basics here; fine-tuning | agent-model-selector |
| Production monitoring, SLOs, cost dashboards beyond context metrics | agent-ops-reviewer |
| Whether the project pays off | agentic-business-case |

## Inputs to gather first

When reviewing code, read it before asking anything. Find the prompt-assembly function, the retriever and index config, every memory write, the checkpointer config, the tool definitions, and a logged prompt or trace of a real call. Count tokens per part from that trace instead of estimating.

Ask only what you can't find:
1. **Task and calls.** What the agent does. Which model calls happen per request (planner, executor, sub-agents, summariser, judge). Single-turn, chat, or long-running (how many steps or hours).
2. **Knowledge.** Sources (docs, wikis, tickets, databases, APIs, web), formats (PDF tables, scans, HTML), total size in tokens, change rate, who curates it, and which systems of record hold live data.
3. **Users and permissions.** Single or multi-tenant? Do document permissions differ per user? Where does identity come from? In a single-company deployment, "tenant" means whatever boundary matters there (business unit, region, role group).
4. **Continuity.** Do the same users come back? Do tasks recur? What must carry across sessions? Any retention or deletion obligations?
5. **Query mix.** Conceptual vs literal (IDs, error codes, SKUs), multi-hop, the share of questions the corpus can't answer, and real failing examples.
6. **Model and budget.** Context window, prompt-caching support, output size, latency target, cost per request or task.
7. **Current state** (for reviews). Chunking, k, retrieval type, filters, what sits in the system prompt, history handling, memory writes, token counts, cache hit rate, observed failures.

If answers are missing, state your assumptions and design for the conservative case: multi-tenant, per-user permissions, a corpus that changes weekly, returning users.

## Procedure

1. **Frame the job.** Decide whether this is a design or a review, and which layers are in scope: retrieval, memory, assembly. List every model call, and write one line per call saying what decision it makes and what it must know to make it.

2. **Map the information.** Classify each piece of information the calls need and pick its route into the call, using the information-map table in [references/memory-design.md](references/memory-design.md) §1. Three rules hold throughout. Live system-of-record data is fetched at run time, never copied into memory. Corpus knowledge is retrieved, not memorised or fine-tuned in. A rule whose violation is costly goes in the prefix and is also enforced in code. A source that is knowledge, live state and personal data at once (helpdesk tickets, email, chat logs) is split: sanitised cards in an index, the user's own records through a live tool ([references/retrieval-pipeline.md](references/retrieval-pipeline.md) §2.6).

3. **Choose the retrieval mode** with table A below. Default to a fixed always-retrieve pipeline. Any agent control over retrieval needs a named reason: several sources, dependent lookups, or a corpus too varied for one query. For a small, stable corpus with no per-user permissions, consider a cached prefix and no retriever.

4. **Design the retrieval pipeline** by working through [references/retrieval-pipeline.md](references/retrieval-pipeline.md) in order:
   - check parsing on every real format;
   - chunk by document structure, with document and section context prepended;
   - attach metadata, including ACLs and version;
   - run BM25 and dense search in parallel, fuse by rank, and apply the permission filter inside the search;
   - retrieve wide (about 50), rerank, and pass 3-5;
   - set a relevance floor and a not-found path, and give every item a citable ID;
   - handle staleness: version metadata, or for undated documents a derived status, age limits and an owner review queue (§2.5);
   - with several indexes, rerank the pooled candidates together, cap each source, and order evidence by trust tier (§3.4).

   For agentic retrieval, add a mandatory-search rule, a first retrieval in code wherever grounding is required, budgets enforced in code with an abstain exit, and notes with source IDs carried between hops.

5. **Decide whether long-term memory is warranted.** It pays only when users or tasks recur. If neither does, stop at thread state plus retrieval and say so. Otherwise, fill one memory-spec row per type kept, using [references/memory-design.md](references/memory-design.md) §3 to §7: store, key and scope, write trigger, decider, validation, update rule, expiry, deletion path, read path. Default write path: rules plus an optional cheap classifier on the hot path. LLM extraction runs only in batch (every N turns, at session end, or in a background worker) and only proposes candidates; code accepts, dedupes and supersedes them. This rule is for durable memory. Per-turn task state in chat (the current-task line and the attempt ledger) is thread state that code maintains every turn ([references/context-assembly.md](references/context-assembly.md) §4).

6. **Assemble each call.** Build a full budget table and layout for the main call(s) with [references/context-assembly.md](references/context-assembly.md) §2 to §6, and a one-line short form for auxiliary calls (router, compactor, extractor, judge). Reserve the output allowance, measure the static prefix, give each bucket a ceiling, an owner and an overflow rule, and set a target p95 total below the ceiling. Lay out shared static prefix → per-user stable block → append-only history → volatile tail (anything that changes every turn). Hard constraints go in the shared prefix and the original task statement in the per-user block. In chat, a current-task line in the tail follows task switches. Write the compaction spec (trigger, what stays verbatim, the must-survive list), the tool-result projection and clearing rules, and the sub-agent brief and return size. If the user has a cost target, estimate cost per call and per task with the formula in context-assembly.md §1. When the inputs are mostly guesses, give a low/high range, name the assumption that drives it, and list the measurements that will replace it.

7. **Handle long runs** if a run outgrows one window or one session. Use the recipe in [references/context-assembly.md](references/context-assembly.md) §7: a progress record that is always injected, tested compaction, batched tool-result clearing, sub-agents for heavy reading, just-in-time loading by identifier, and checkpoints for resume.

8. **Run the safety and privacy pass.** Check each of these:
   - permissions are filtered before ranking, and every cache is keyed by permission scope and index version;
   - user and tenant IDs come from the authenticated session;
   - tool, web and document text never becomes durable memory or instructions without a reviewed step;
   - deletion reaches every copy (the deletion map in [references/memory-design.md](references/memory-design.md) §6).

   Flag poisoning and injection paths, and hand the threat model to agent-threat-modeler.

9. **Plan evaluation** with [references/evaluation.md](references/evaluation.md):
   - retrieval recall@k at each stage, per query type and permission scope;
   - faithfulness, completeness and abstention, with unanswerable questions in the set;
   - the diagnosis table, to decide which stage to fix;
   - memory tests on the five abilities, plus leak and deletion tests;
   - cache hit rate, tokens per bucket, and compaction survival.

   Every addition gets a before/after measurement.

10. **For reviews, rank findings.** P0 means it leaks across users or tenants, loses a safety constraint, or persists secrets or untrusted content. P1 means a measurable loss of answer quality. P2 means wasted cost or latency. Every finding carries evidence (file:line or trace), why it matters, the fix, and how to verify it. Put P0s first, then quick wins, then P1s with their metrics.

11. **Write the output** from the template, check it against the quality bar, and fix anything that fails.

## Decision guide

### A. Retrieval mode
| Situation | Pattern | Why | Watch out for |
|---|---|---|---|
| Small, stable corpus (roughly under 200k tokens), same for every user | Whole corpus in a cached prefix | Simplest; caching keeps repeat cost low | Breaks when the corpus grows or permissions differ; long prompts lose the middle |
| Private or changing corpus; most questions need it | Always-retrieve pipeline: hybrid + filters + rerank | Testable, cacheable, predictable | Route greetings and chit-chat around retrieval |
| Proprietary, regulated or fast-changing knowledge | Always retrieve, instruct abstention | The model's confident priors are wrong here | Letting the model decide whether to look |
| Several sources, or the next lookup depends on the last result | Retrieval as a tool in a bounded loop | Picks sources, takes second hops | One measurement: ~1.9x latency, ~3.5x cost; agents skip optional search; budgets in code |
| Answer lives in tables | Text-to-SQL with retrieved schema hints | Retrieval means writing a query | Read-only role; fallback on failure |
| Questions walk relations or ask for corpus-wide themes | GraphRAG, after testing those question types | Chunk retrieval handles them badly | LLM extraction cost on every change; wrong edges are worse than none |
| Repetitive task with a bank of solved examples | Retrieved few-shot examples | Cheap quality gain | Few or conflicting examples |

### B. Retrieval symptom → fix
Check stages in order: indexed → in candidates → in reranked top k → in the prompt → used correctly.

| Symptom | Likely stage | Fix first |
|---|---|---|
| Right document never in the candidates | Parsing, chunking, query | Inspect parsed text; re-chunk with section context; add BM25; rewrite only for vocabulary mismatch |
| Error codes, SKUs, names missed | Dense-only search | Hybrid with rank fusion; identifier queries in the test set |
| Right chunk at rank 15 | Ranking | Rerank the top ~50 and pass 3-5. Don't raise k into the prompt |
| Answer misses a unit or scope ("figures in millions") | Chunk lost its document context | Prepend document and section context at index time |
| Confident answer when nothing relevant exists | No floor, no not-found path | Calibrated floor; instructed abstention; unanswerable test cases |
| Good evidence ignored | Generation | Grounding and citation instructions; fewer, better chunks; stronger model |
| Content from another tenant or role appears | Filtering or caching | ACL metadata, filtered inside the search; caches keyed by scope |
| Superseded policy quoted | Freshness | Version metadata; retire old versions; recency as tie-breaker among near-duplicates |
| Outdated page quoted and the corpus has no version fields | Freshness | Derived status from markers, near-duplicates and age; owner review queue; date in the evidence header |
| Case history or forum answer overrides the official doc | Multi-index fusion | Rerank pooled candidates, per-source quotas, trust tiers in the prompt |
| Agent answers without searching | Agent control | "Always search before answering X" plus a trace check, or a first retrieval in code |

### C. Memory: what to keep and where
| State | Store and update rule | Read path | Watch out for |
|---|---|---|---|
| Current task: messages, tool results, plan | Checkpointed thread state, append; raw trajectory kept | Recent turns verbatim + summary | Trimming evicts the task statement |
| Preferences, durable facts | Keyed records, upsert/supersede, dedupe at write | Small profile block every call | Contradictions accumulate; stale values |
| Past tasks and outcomes | Append-only episodes with timestamps | By recency for "where we left off"; by similarity, above a floor, for "a case like this" | Pays only when users or tasks recur |
| How to behave | Versioned, reviewed procedures | Stable prefix | Unreviewed self-edits |
| Balances, orders, stock, entitlements, devices | Not memory: the system of record | Tool call or provisioned at run start | Copying volatile data into memory; tell the user it will be fetched live |
| Steps tried this session; current problem | Attempt ledger + current-task line: thread state appended by code | Volatile tail, verbatim, never summarised | Letting the LLM rewrite it; losing it at compaction |
| Tickets, email, chat logs | Split: sanitised cards indexed; own records via live tool | Cards as `derived` evidence; records by tool | Raw records in a shared index |
| Secrets, card numbers, national IDs | Never stored | None | Validate every write |

### D. Who decides what to remember
| Decider | Extra cost | Use for |
|---|---|---|
| Rules (explicit "remember", corrections, form fields) | None | Always the first layer |
| Similarity against existing memory | Embedding only | Dedupe; detecting updates |
| Small classifier | Low | Ambiguous candidates at volume |
| LLM extractor in batch; code accepts | One call per N turns or per session | Rich conversational facts, off the hot path |
| LLM judge every turn | About one extra call per step | Rare high-stakes cases, with a measured gain |

### E. Context pressure
| Symptom | Technique | Watch out for |
|---|---|---|
| Long chat, early turns irrelevant | Rolling window + pinned task statement | Losing goals and constraints |
| Long chat or run, middle still matters | Compaction with a must-survive checklist | Summaries of summaries; dropped constraints |
| Tool outputs dominate | Project needed fields; clear old results in batches; keep handles | Each clearing breaks the cache from that point |
| Dozens of tool definitions | Fixed small set per run; tool search or code execution for big catalogues | A tool-list change invalidates the whole cache |
| Sub-task needs heavy reading | Sub-agent: brief in, ~1-2k tokens out | It may need parent context you didn't brief |
| Work spans sessions or resets | Progress file + checkpoints | Unvalidated agent-written notes |
| Agent re-suggests steps the user already tried | Code-maintained attempt ledger in the tail | Ledger written as free text by the LLM |
| User switches problems mid-chat | Replace the current-task line, close the ledger, or offer a new thread | Overwriting the original task statement |
| High input cost with a repeated prefix | Shared prefix → per-user block → append-only → volatile tail; measure cache reads | Timestamps, reordered JSON, per-user text inside the shared prefix |

### F. Starting values (tune by measurement)
| Knob | Start | Basis |
|---|---|---|
| First-stage candidates per retriever | ~50 | Wide for recall; reranking narrows it |
| Chunks passed to the model | 3-5 reranked | Five focused chunks often beat twenty loose ones [SYSTEMS ch5] |
| RRF k | 60 | Common engine default (provider-notes.md) |
| Chunking | Structure-aware + section context | No book gives an ideal size; test 2-3 against real queries [DLLMA ch11] |
| Relevance floor | Calibrated per model and query type | Absolute similarity scores vary by model |
| Fact confidence to persist | ~0.7 (example) | [DEFGUIDE ch10] |
| Online faithfulness sampling | ~5% of traffic | Judge cost [EVALS ch7] |
| Sub-agent return size | ~1,000-2,000 tokens | provider-notes.md |
| Compaction trigger (chat) | Recent turns over ~6-8k tokens or 15-20 turns; compact down to about half | This skill's default; move it after a length-degradation test |
| Compaction trigger (long agent run) | Well below the window | Provider tool-result clearing defaults to ~100k tokens |
| Per-source quota, several indexes | At most 2 lower-tier items among 4-5; at least 1 official slot when one passes the floor | This skill's default; check per-index recall |
| Age limit before `needs_review` | ~12 months for how-tos and procedures; longer for stable policy | This skill's default; set per document type |

## Output

Use [templates/context-design.md](templates/context-design.md) for a design and [templates/context-review.md](templates/context-review.md) for a review. A review that proposes a redesign includes the changed design sections. Every output contains:
- a budget table with token numbers (measured, or marked "est.") and the layout for the main call, plus short-form rows for other calls;
- the retrieval spec with its defaults, plus what to measure before changing any of them;
- a memory spec table, or one sentence explaining why there is no long-term memory;
- the compaction spec, if any run can outgrow the window;
- a cost estimate against the user's target, if one was given: a number or a low/high range, marked "est.", with the measurements that will replace it;
- the evaluation plan: test-set slices, metrics, gates;
- a staged rollout saying what to build first and which measurement unlocks the next stage;
- assumptions, open questions, and hand-offs to sibling skills.

Name the rule behind each non-obvious decision in one phrase. Leave out general RAG or memory explanations the user didn't ask for.

## Quality bar

- [ ] The main call has a budget per bucket with a ceiling below the window and a target p95 total; other calls have a short form. Numbers are measured or marked as estimates.
- [ ] Layout is shared prefix → per-user stable block → append-only → volatile tail. Nothing per-user or time-dependent sits inside or before the shared prefix, serialisation is deterministic, and anything that changes every turn sits in the tail.
- [ ] Hard constraints sit in the never-compacted prefix and costly ones are also enforced in code. The original task statement survives compaction; in chat, a current-task line and an attempt ledger track task switches and tried steps.
- [ ] Retrieval is hybrid, or a measurement shows one side adds nothing. It reranks before passing, passes few chunks, has a floor and a not-found path, and returns citable IDs.
- [ ] Permission filtering happens inside the search, before ranking, and caches are keyed by permission scope.
- [ ] Each memory type has a store, scope, trigger, decider, validation, update rule, expiry, deletion path and read path.
- [ ] No per-turn LLM memory call without a measured gain.
- [ ] Tool, web and document text never becomes durable memory without a reviewed step, and identity comes from the session.
- [ ] Live system-of-record data is fetched, not memorised.
- [ ] Agentic retrieval, if present, has a named reason, a mandatory-search rule, budgets in code and an abstain exit.
- [ ] Evaluation scores retrieval and generation separately, covers unanswerable, identifier and per-scope cases, and includes memory update, abstention and deletion tests plus cache hit rate.
- [ ] Every proposed addition has a before/after metric, and the rollout is staged.
- [ ] Hand-offs to sibling skills are named where the work leaves this skill's scope.

## Common mistakes

| Mistake | Fix |
|---|---|
| Defaulting to "vector DB, cosine, top-10" | Hybrid + rerank + pass 3-5; dense-only search misses identifiers |
| "Use a model with a bigger window" as the fix | Quality drops with length and distractors; select, budget, compact |
| Recommending agentic RAG by default | Fixed pipeline first; agent control only for a named reason, and budgeted |
| An LLM "should I remember this?" call every turn | Rules first, batch extraction, code decides |
| Storing every message, or everything, in a vector store | Classify by update semantics; facts upsert; store only what improves future behaviour |
| Treating RAG and memory as one thing | A curated corpus and agent-written state have different lifecycles and rules |
| Filtering permissions after top-k, or in app code only | ACL metadata, pre-filter from the session identity, scope-keyed caches |
| A timestamp or user name at the top of the system prompt | User text goes in the per-user block after the shared prefix, the timestamp in the tail; track cache-read tokens |
| Compaction prompt "summarise the conversation" | Domain must-survive checklist, constraints in the prefix, a survival test |
| Budgets invented without counting | Measure the prefix and chunk sizes from a real trace; label estimates |
| Quoting book or vendor percentages as expected gains | Treat them as anecdotes and plan a measurement |
| Switching embedders first | Fix parsing, chunking, filters and corpus gaps first; leading embedders differ little |
| Only end-to-end accuracy as the eval | Score retrieval and generation separately; use the diagnosis table |
| Fine-tuning knowledge into the model, or calling weights "private memory" | Retrieve knowledge; weights can't be scoped or deleted (model questions go to agent-model-selector) |
| Writing tool or web output straight into memory | Provenance, `proposed` status, promotion by rule or review |
| Indexing raw tickets or email threads into a shared corpus | Sanitised case cards with their own ACL and retention; the user's own records through a live tool |
| Agreeing to "remember my devices / plan / open tickets" by copying them into memory | Say they will be fetched live every session, and why |
| One cost number built on guesses | A low/high range, the assumption that drives it, what to measure first |

## Sources

Citation keys used in this skill and its references:
- **SYSTEMS**: *Systems Thinking for Agentic AI*, ch5 (RAG systems), ch9 (memory), ch12 (token budgeting, caching), ch16 (RAG integration, execution loop).
- **DLLMA**: *Designing Large Language Model Applications*, ch10 (interaction paradigms, data stores), ch11 (embeddings, chunking), ch12 (RAG pipeline, rerank, refine, memory paging).
- **DEFGUIDE**: *AI Agents: The Definitive Guide*, ch7 (context janitor), ch10 (agent memory, hygiene, topologies), ch11 (prefix cost).
- **ILLUSTRATED**: *An Illustrated Guide to AI Agents*, ch4 (memory, context engineering, agentic RAG), ch10 (context management for code agents).
- **BUILDAGENTIC**: *Building Agentic AI*, ch2 (text-to-SQL RAG), ch3 (retrieval evaluation, few-shot), ch4 (RAG vs agent, memory experiment), ch5 (BM25, tool-skipping, deep research), ch7 (context engineering), ch9 (Matryoshka embeddings).
- **BUILDAPPS**: *Building Applications with AI Agents*, ch3 (context retention), ch5 (context engineering), ch6 (knowledge and memory, GraphRAG), ch9 (memory tests), ch13 (shared memory scopes).
- **EVALS**: *AI Evals in Practice*, ch7 (evaluating RAG).
- **AGENTICAI**: *Agentic Artificial Intelligence*, ch7 (memory, consolidation, privacy).
- **ENTERPRISE**: *The Agentic Enterprise*, ch5 (memory degradation, context provisioning), ch7 (compaction incident).
- **MESH**: *Agentic Mesh*, ch1 (lost access rules), ch5 (context engineering, memory).
- **MCP**: *AI Agents with MCP*, ch4 (tool-list context engineering).

External (checked 2026-10; details in [references/provider-notes.md](references/provider-notes.md)):
- https://www.anthropic.com/engineering/contextual-retrieval
- https://www.anthropic.com/engineering/multi-agent-research-system
- https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents
- https://platform.claude.com/docs/en/build-with-claude/prompt-caching
- https://platform.claude.com/docs/en/build-with-claude/context-editing
- https://platform.claude.com/docs/en/agents-and-tools/tool-use/memory-tool
- https://developers.openai.com/api/docs/guides/prompt-caching
- https://manus.im/blog/Context-Engineering-for-AI-Agents-Lessons-from-Building-Manus
- https://www.trychroma.com/research/context-rot
- https://arxiv.org/abs/2411.06037 (Sufficient Context)
- https://arxiv.org/abs/2410.10813 (LongMemEval)
- https://www.elastic.co/docs/reference/elasticsearch/rest-apis/reciprocal-rank-fusion
