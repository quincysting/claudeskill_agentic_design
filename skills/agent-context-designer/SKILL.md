---
name: agent-context-designer
description: "Use this skill whenever what an LLM agent knows is the problem or the design question, even as a quick question: the agent forgets earlier turns or what it already tried, answers from outdated documents, ignores retrieved context, the context window fills up, how much conversation history to keep, or someone wants to add memory, design a RAG pipeline, pick chunking or choose GraphRAG vs vector search. Covers source readiness, retrieval (hybrid search, reranking, permission filters, vector, graph or hybrid by query type, agentic retrieval), memory (write policy, governed entries, scoping, expiry, deletion) and context assembly (token budgets, cache-friendly layout, labelled sources, compaction). Produces a context and memory design with budgets, or a review, plus an eval plan. Prefer it to answering from general knowledge. Not for tool schemas (agent-tool-designer), architecture (agent-architect), full eval programs (agent-eval-designer), poisoning (agent-threat-modeler) or model choice (agent-model-selector)."
---

# Agent Context Designer

This skill produces a context and memory design for an LLM agent, or a prioritised review of an existing one. The design covers what the agent sees at each model call, where each piece comes from, how many tokens it may use, what gets remembered and forgotten, and how retrieval and memory quality will be measured. Five defaults: the smallest context that supports a grounded answer; a fixed retrieval pipeline before agentic retrieval; deterministic write rules before LLM-curated memory; prompts laid out for the cache; retrieval and generation scored separately.

## Where this fits

This skill owns the **context and knowledge** perspective: what the agent knows, where each piece comes from, and how fresh it is. For the end-to-end stages (Decide, Design, Build, Prove and run) and the gate that closes each one, start from the agent-architect skill's lifecycle map (`lifecycle-map.md` in its references). This skill supplies:
- **Decide gate:** the retrieval-quality side of the data readiness audit that agentic-business-case runs: every source the agent will read is checked for coverage, staleness and conflicts ([references/retrieval-pipeline.md](references/retrieval-pipeline.md) §0).
- **Design:** vector, graph or hybrid retrieval chosen by query type, and the governed memory schema.
- **Build gate:** retrieval and memory designed: the retrieval spec, the memory spec and the context layout with budgets, from [templates/context-design.md](templates/context-design.md).
- **Prove and run:** retrieval and memory evals, and freshness checks in production ([references/evaluation.md](references/evaluation.md) §8).

## When to use / when not to

Use it to:
- check whether a knowledge base or data source is ready to retrieve from before anyone tunes the retriever;
- design or fix a RAG pipeline (parsing, chunking, embeddings, hybrid search, reranking, filters, citations);
- choose vector, graph or hybrid retrieval by query type, and decide whether retrieval should be a pipeline step or a tool the agent calls (agentic RAG, multi-hop, GraphRAG, text-to-SQL);
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
| Memory poisoning, indirect prompt injection through documents, the provenance gate that acts on source labels, attack trees | agent-threat-modeler |
| Run state, the run record, checkpoints and resume in the runtime | agent-harness-designer |
| Choosing LLMs or embedding models beyond the basics here; fine-tuning | agent-model-selector |
| Production monitoring, SLOs, cost dashboards beyond context metrics | agent-ops-reviewer |
| Whether the project, or a data clean-up, pays off | agentic-business-case |

## Inputs to gather first

When reviewing code, read it before asking anything. Find the prompt-assembly function, the retriever and index config, every memory write, the checkpointer config, the tool definitions, and a logged prompt or trace of a real call. Count tokens per part from that trace instead of estimating. List every file in the reviewed folder as read or not read, tests, lock files and example environment files included, and take the library versions that inferred labels name from the lock file.

Ask only what you can't find:
1. **Task and calls.** What the agent does. Which model calls happen per request (planner, executor, sub-agents, summariser, judge). Single-turn, chat, or long-running (how many steps or hours).
2. **Knowledge.** Sources (docs, wikis, tickets, databases, APIs, web), formats (PDF tables, scans, HTML), total size in tokens, change rate, who owns and reviews each source and when it was last reviewed, and which systems of record hold live data.
3. **Users and permissions.** Single or multi-tenant? Do document permissions differ per user? Where does identity come from? In a single-company deployment, "tenant" means whatever boundary matters there (business unit, region, role group).
4. **Continuity.** Do the same users come back? Do tasks recur? What must carry across sessions? Any retention or deletion obligations?
5. **Query mix.** Conceptual vs literal (IDs, error codes, SKUs), multi-hop, relationship chains or corpus-wide themes, the share of questions the corpus can't answer, and real failing examples.
6. **Model and budget.** Context window, prompt-caching support, output size, latency target, cost per request or task.
7. **Current state** (for reviews). Chunking, k, retrieval type, filters, what sits in the system prompt, history handling, memory writes, token counts, cache hit rate, observed failures.

If answers are missing, state your assumptions and design for the conservative case: multi-tenant, per-user permissions, a corpus that changes weekly, returning users.

If the system runs on AWS, map each decision with [references/aws-implementation-notes.md](references/aws-implementation-notes.md).

## Procedure

1. **Frame the job.** Decide whether this is a design or a review, and which layers are in scope: retrieval, memory, assembly. List every model call, and write one line per call saying what decision it makes and what it must know to make it. A memory-only system (no document corpus) skips steps 3 and 4, but memory search over a shared index is still filtered retrieval, so step 5 keeps that rule.

2. **Map the information.** Classify each piece of information the calls need and pick its route into the call, using the information-map table in [references/memory-design.md](references/memory-design.md) §1. Three rules hold throughout. Live system-of-record data is fetched at run time, never copied into memory. Corpus knowledge is retrieved, not memorised or fine-tuned in. A rule whose violation is costly goes in the prefix and is also enforced in code. A source that is knowledge, live state and personal data at once (helpdesk tickets, email, chat logs) is split: sanitised cards in an index, the user's own records through a live tool ([references/retrieval-pipeline.md](references/retrieval-pipeline.md) §2.6).

3. **Choose the retrieval mode** with table A below. Default to a fixed always-retrieve pipeline. Any agent control over retrieval needs a named reason: several sources, dependent lookups, or a corpus too varied for one query. For a small, stable corpus with no per-user permissions, consider a cached prefix and no retriever. Choose the store by query type: keyword plus vector hybrid by default; a graph only for relationship or corpus-wide questions that hybrid measurably fails and that you can keep current; then route between the stores ([references/retrieval-pipeline.md](references/retrieval-pipeline.md) §1.1).

4. **Design the retrieval pipeline** by working through [references/retrieval-pipeline.md](references/retrieval-pipeline.md) in order:
   - audit the sources first: answers to the top 30 to 50 questions, retired and conflicting documents archived, an owner and review schedule, the 90% rule for structured decision fields (not articles), volatile data behind a live query (§0);
   - check parsing on every real format;
   - chunk by document structure, with document and section context prepended;
   - attach metadata, including allow groups, deny scopes (ethical walls, information barriers, legal holds), section role and version (§2.3);
   - run BM25 and dense search in parallel, fuse by rank (or by weighted normalised scores when one side should count more), and apply the permission filter, allow and deny both, inside the search (§3.2);
   - retrieve wide (about 50), rerank, and pass 3-5 (more for synthesis across sources, tuned on that slice);
   - set a relevance floor and a not-found path, and give every item a citable ID;
   - verify citations in code: cited IDs in this request's evidence set, quotes verbatim, a support check per claim, unsupported claims removed or flagged "unverified", non-authoritative parts labelled (§3.8);
   - for primary-authority corpora (case law, statutes, standards), take staleness from an authoritative status feed, not from age (§2.5);
   - handle staleness: version metadata, or for undated documents a derived status, age limits and an owner review queue (§2.5);
   - make indexing idempotent (stable chunk IDs, upsert) and check every ingest: per-source counts, a canary query, backfill for what the trigger missed (§2.5, §2.7);
   - for governed numbers, use a metric catalog instead of text-to-SQL, give recurring list, filter and count questions vetted query templates, check the accuracy of any machine-labelled filter field, and run every table query under the caller's row and column entitlements (§5);
   - with several indexes, rerank the pooled candidates together, cap each source, and order evidence by trust tier (§3.4);
   - for a graph, load validated triplets and hold them to the quality bar; generated graph or SQL queries run read-only under the caller's entitlements, from templates or an allowlist, with graph writes only on the ingest path (§5.2, §5.3).

   For agentic retrieval, add a mandatory-search rule, a first retrieval in code wherever grounding is required, budgets enforced in code with an abstain exit, and notes with source IDs carried between hops.

5. **Decide whether long-term memory is warranted.** It pays only when users or tasks recur. If neither does, stop at thread state plus retrieval and say so. Otherwise, fill one memory-spec row per type kept, using [references/memory-design.md](references/memory-design.md) §3 to §7: store, key and scope, write trigger, decider, validation, update rule, expiry, deletion path, read path. Default write path: rules plus an optional cheap classifier on the hot path. LLM extraction runs only in batch (every N turns, at session end, or in a background worker) and only proposes candidates; code accepts, dedupes and supersedes them. Each durable entry carries category, source, confidence, last verified, a TTL and a sensitivity level; an expired entry counts as unknown; entries hold references instead of raw content or personal data; and writes that steer actions other people see go through a proposal a person approves until that category has earned automatic writes (memory-design.md §4.5, §4.7). This rule is for durable memory. Per-turn task state in chat (the current-task line and the attempt ledger) is thread state that code maintains every turn ([references/context-assembly.md](references/context-assembly.md) §4). Memory search over one shared vector index is filtered retrieval: the scope filter runs inside the approximate search, not after its cut-off, with a per-scope recall slice ([references/retrieval-pipeline.md](references/retrieval-pipeline.md) §3.2). For many users over months, size the store with the growth worksheet in memory-design.md §5 (items per user per month × users × months, a per-user cap, recall by item age, index size). Wherever more than one writer can touch a thread or record (a retry and a resume, replicas, concurrent turns), writes are conditional or go through one writer per scope, and the thread store has a tested read order (memory-design.md §8). When reviewing a running system, the fix also cleans up what the old design already stored: inventory, move system-of-record facts out, purge forbidden content, backfill the governed fields, log the deletions (memory-design.md §6.1).

6. **Assemble each call.** Build a full budget table and layout for the main call(s) with [references/context-assembly.md](references/context-assembly.md) §2 to §6, and a one-line short form for auxiliary calls (router, compactor, extractor, judge). Reserve the output allowance, measure the static prefix, give each bucket a ceiling, an owner and an overflow rule, and set a target p95 total below the ceiling. Lay out shared static prefix → per-user stable block → append-only history → volatile tail (anything that changes every turn). When per-user data changes mid-session (another tab or device writes), keep the session-start snapshot in the per-user block, add the changes as a delta in the tail, and re-snapshot at compaction or the next session (context-assembly.md §3). A cache-layout finding or fix states the provider's minimum cacheable length and its opt-in mechanism (explicit breakpoints or automatic caching), and checks the proposed cached span against both: a prefix below the minimum saves nothing ([references/provider-notes.md](references/provider-notes.md)). Hard constraints go in the shared prefix and the original task statement in the per-user block. Fence and label every block with its origin and trust when it enters, recalled memory and agent-written notes included (context-assembly.md §9). In chat, a current-task line in the tail follows task switches. Write the compaction spec (trigger, what stays verbatim, the must-survive list), the tool-result projection and clearing rules, and the sub-agent brief and return size. If the user has a cost target, estimate cost per call and per task with the formula in context-assembly.md §1. When the inputs are mostly guesses, give a low/high range, name the assumption that drives it, and list the measurements that will replace it.

7. **Handle long runs** if a run outgrows one window or one session. Use the recipe in [references/context-assembly.md](references/context-assembly.md) §7: a progress record that is always injected, tested compaction, batched tool-result clearing, sub-agents for heavy reading, just-in-time loading by identifier, and checkpoints for resume.

8. **Run the safety and privacy pass.** Check each of these:
   - permissions are filtered before ranking, and every retrieval and answer cache is keyed by permission scope and ingest generation (a counter that every ingest passing its checks advances, incremental runs included; retrieval-pipeline.md §2.5, §6);
   - the ACL model has deny rules as well as allow lists, evaluated inside the search; a new wall or barrier propagates to index metadata, invalidates scope-keyed caches and purges the barred user's recalled memory and session state, with a test for a user walled off after the fact (retrieval-pipeline.md §2.3);
   - every store a client-supplied identifier can reach is bound to the authenticated user: memory namespaces, thread and checkpoint IDs, run histories and caches. Thread ownership is recorded at creation and checked on every read, resume and list; scope keys have no default identity and no environment fallback; memory tools get scope keys and author role from the server. Name the framework hook that carries the authenticated identity into the run and verify it at the pinned version (memory-design.md §6, §8, §10);
   - table and metric queries run with the caller's row and column entitlements, not a shared service role (retrieval-pipeline.md §5);
   - generated graph and SQL queries run read-only, scoped to the caller, from templates or an allowlist, with row limits and timeouts, and graph writes happen only on the ingest path (retrieval-pipeline.md §5.3);
   - every assembled block carries its origin and trust label, so the provenance gate that agent-threat-modeler specifies can refuse tool calls triggered by content (context-assembly.md §9);
   - tool, web and document text never becomes durable memory or instructions without a reviewed step;
   - deletion reaches every copy, hosted tracing included (the deletion map in [references/memory-design.md](references/memory-design.md) §6); in an employer-run assistant, leaving, transfer and role change trigger deletion or rescoping, and who inside the organisation may read an employee's memory is an explicit scope rule (memory-design.md §6);
   - logged questions and conversations enter test sets only de-identified and with the data owner's permission (evaluation.md §1).

   Flag poisoning and injection paths, and hand the threat model to agent-threat-modeler. Data-protection, confidentiality and privilege questions (retention duties, who inside the organisation may read stored memory, sending client text to a model provider, whether a past exposure must be reported) go to the organisation's privacy or legal owner: flag them as open questions and don't decide them. Nothing here is legal advice.

9. **Plan evaluation** with [references/evaluation.md](references/evaluation.md):
   - retrieval recall@k at each stage, per query type and permission scope;
   - faithfulness, completeness and abstention, with unanswerable questions in the set;
   - the diagnosis table, to decide which stage to fix;
   - memory tests on the five abilities, plus leak and deletion tests;
   - cache hit rate, tokens per bucket, and compaction survival.

   Every addition gets a before/after measurement.

10. **For reviews, rank findings.** P0 means it leaks across users or tenants, loses a safety constraint, or persists secrets or untrusted content. Untrusted content is third-party text: documents, web pages, tool output, other users' text; the user's own statements are proposals under the approval rule. Rate a persisted-injection path carried in the user's own statements by what the stored content can trigger now (P1 while it only shapes that user's replies, P0 once it reaches a tool that acts or another user), and name the change that raises it; persisted third-party content stays P0. Missing deletion, expiry or inspection on durable personal memory is P0 where privacy duties apply or the deployment is organisation-wide, P1 otherwise. P1 means a measurable loss of answer quality. P2 means wasted cost or latency. The scope line lists every file as read or not read. With no trace, build the baseline from code: count the static prompt text from the source, give the other buckets as low/high ranges, and name the trace that will replace each estimate. Every finding carries evidence (file:line or trace), why it matters, the fix, and how to verify it. Tag each fact a finding rests on: **seen** (read in code, config or a document supplied for this review; cite file:line or section), **observed** (shown by logs, traces, metrics or a test run), **told** (stated by an owner or user and not checked), **inferred** (follows from seen code plus a library, platform or language behaviour not checked here; name the behaviour and the version it depends on) or **assumed** (no evidence). Severity follows the consequence if an inferred or assumed fact holds, and every inferred or assumed fact also goes under "Confirm first". A measured token count is observed; a number marked "est." is inferred or assumed. Put P0s first, then quick wins, then P1s with their metrics. A data-handling defect in a live system is fixed in two parts: the forward fix, and the clean-up of records the old design already wrote (re-index with ACLs, purge or re-mask stored copies, invalidate caches, backfill governed fields), with a deletion log.

11. **Write the output** from the template, check it against the quality bar, and fix anything that fails.

## Decision guide

### A. Retrieval mode
| Situation | Pattern | Why | Watch out for |
|---|---|---|---|
| Small, stable corpus (roughly under 200k tokens), same for every user | Whole corpus in a cached prefix | Simplest; caching keeps repeat cost low | Breaks when the corpus grows or permissions differ; long prompts lose the middle |
| Private or changing corpus; most questions need it | Always-retrieve pipeline: hybrid + filters + rerank | Testable, cacheable, predictable | Route greetings and chit-chat around retrieval |
| Proprietary, regulated or fast-changing knowledge | Always retrieve, instruct abstention | The model's confident priors are wrong here | Letting the model decide whether to look |
| Several sources, or the next lookup depends on the last result | Retrieval as a tool in a bounded loop | Picks sources, takes second hops | One measurement: ~1.9x latency, ~3.5x cost; agents skip optional search; budgets in code |
| Answer lives in tables, exploratory question | Text-to-SQL with retrieved schema hints | Retrieval means writing a query | Read-only role carrying the caller's row and column entitlements; fallback on failure |
| Recurring list, filter or count questions over records | Vetted parameterised templates the model fills; code checks and binds the values | Same answer every time, auditable, no generated SQL | Machine-labelled filter fields need a sampled accuracy check, disclosed in the answer |
| Answer is a governed number (KPI, regulatory ratio, financial figure) | Metric catalog: match the metric by description above a floor, run its vetted parameterised query in code, answer from the returned value | One definition per number, auditable, no generated SQL | Catalog drift; a description that matches while the scope doesn't (check scope values in code) |
| Questions walk relations or ask for corpus-wide themes, and hybrid measurably fails on them | A graph beside hybrid search, with a router (retrieval-pipeline.md §1.1) | Chunk retrieval handles them badly | LLM extraction cost on every change; wrong edges are worse than none; fails on questions that name no entity; generated queries need a read-only, caller-scoped path |
| Repetitive task with a bank of solved examples | Retrieved few-shot examples | Cheap quality gain | Few or conflicting examples |

### B. Retrieval symptom → fix
Check stages in order: indexed → in candidates → in reranked top k → in the prompt → used correctly.

| Symptom | Likely stage | Fix first |
|---|---|---|
| Confident wrong answers from outdated or contradictory articles | Sources | Readiness audit before tuning: archive retired content, merge conflicts, owner and review date (§0) |
| Relationship question answered with loosely related chunks | Store choice | Check the query type; build a graph only if hybrid fails on a test set of such questions (§1.1) |
| "Not found" for documents that should be there, right after an ingest that succeeded | Ingest | Per-source counts and a canary query after every run; backfill; re-index after pipeline changes (retrieval-pipeline.md §2.7) |
| New documents answerable only hours after an ingest | Ingest timing or caching | Compare the job's finish time with the first query that finds them; look for caches keyed without the ingest generation, the index refresh interval, and missed files that only a late retry or reconcile picks up (retrieval-pipeline.md §2.5, §2.7) |
| Right document never in the candidates | Parsing, chunking, query | Inspect parsed text; re-chunk with section context; add BM25; rewrite only for vocabulary mismatch |
| Small tenant or narrow role gets few or no results | Filter applied after the approximate-search cut-off | Filtered or iterative approximate search, or a partition per scope; per-scope recall slice (§3.2) |
| Graph lookup returns nothing for entities that should match | Missing links at ingest | Required-path checks after ingest; an empty traversal from an unlinked entity is an error state (§5) |
| Error codes, SKUs, names missed | Dense-only search | Hybrid with rank fusion; identifier queries in the test set |
| Right chunk at rank 15 | Ranking | Rerank the top ~50 and pass 3-5. Don't raise k into the prompt |
| Answer misses a unit or scope ("figures in millions") | Chunk lost its document context | Prepend document and section context at index time |
| Confident answer when nothing relevant exists | No floor, no not-found path | Calibrated floor; instructed abstention; unanswerable test cases |
| Good evidence ignored | Generation | Grounding and citation instructions; fewer, better chunks; stronger model |
| Cites a real source that does not support the claim, or quotes a dissent or summary as the finding | Generation | Cite-and-verify contract in code: cited IDs in the evidence set, verbatim quotes, a support check per claim, unsupported claims removed or flagged, section roles labelled (§3.8) |
| Content from another tenant or role appears, or a walled user still sees a barred matter | Filtering or caching | ACL metadata with allow groups and deny scopes, filtered inside the search; caches keyed by scope and invalidated on a wall change (§2.3) |
| Overruled or amended authority cited as current | Freshness (primary authority) | Status from an authoritative feed, re-checked at answer time; age rules don't apply (§2.5) |
| Superseded policy quoted | Freshness | Version metadata; retire old versions; recency as tie-breaker among near-duplicates |
| Outdated page quoted and the corpus has no version fields | Freshness | Derived status from markers, near-duplicates and age; owner review queue; date in the evidence header |
| Case history or forum answer overrides the official doc | Multi-index fusion | Rerank pooled candidates, per-source quotas, trust tiers in the prompt |
| Agent answers without searching | Agent control | "Always search before answering X" plus a trace check, or a first retrieval in code |

### C. Memory: what to keep and where
| State | Store and update rule | Read path | Watch out for |
|---|---|---|---|
| Current task: messages, tool results, plan | Checkpointed thread state, append with collision-free IDs and conditional writes; raw trajectory kept | Recent turns verbatim + summary, in a tested order | Trimming evicts the task statement; concurrent appends overwrite each other |
| Preferences, durable facts | Keyed records, upsert/supersede, dedupe at write | Small profile block every call | Contradictions accumulate; stale values |
| Past tasks and outcomes | Append-only episodes with timestamps | By recency for "where we left off"; by similarity, above a floor, for "a case like this" | Pays only when users or tasks recur |
| How to behave | Versioned, reviewed procedures | Stable prefix | Unreviewed self-edits |
| Balances, orders, stock, entitlements, devices | Not memory: the system of record | Tool call or provisioned at run start | Copying volatile data into memory; tell the user it will be fetched live |
| Steps tried this session; current problem | Attempt ledger + current-task line: thread state appended by code | Volatile tail, verbatim, never summarised | Letting the LLM rewrite it; losing it at compaction |
| Tickets, email, chat logs | Split: sanitised cards indexed; own records via live tool | Cards as `derived` evidence; records by tool | Raw records in a shared index |
| Entity relations that change over time | Temporal graph edges with valid-from and valid-to | Traversal from the entity, "as of" a date | No pipeline to keep the graph current |
| Secrets, card numbers, national IDs | Never stored | None | Validate every write |

### D. Who decides what to remember
| Decider | Extra cost | Use for |
|---|---|---|
| Rules (explicit "remember", corrections, form fields) | None | Always the first layer |
| Similarity against existing memory | Embedding only | Dedupe; detecting updates |
| Small classifier | Low | Ambiguous candidates at volume |
| LLM extractor in batch; code accepts | One call per N turns or per session | Rich conversational facts, off the hot path |
| LLM judge every turn | About one extra call per step | Rare high-stakes cases, with a measured gain |
| A person approves a proposal | Attention, not tokens | Early builds; constraints, defaults other people see, restricted categories |

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
| Chunks passed to the model | 3-5 reranked for single-answer lookups; more for synthesis across sources | Five focused chunks often beat twenty loose ones [SYSTEMS ch5]; tune the synthesis count on that slice's recall and faithfulness |
| RRF k | 60 | Common engine default (provider-notes.md) |
| Weighted hybrid instead of RRF | Keyword weight 0.3-0.5 on normalised scores | [KGRAG ch6]; check which end of the weight means keyword |
| Evidence order | Rank order for 3-5 chunks; alternate (strongest at both edges) for a wide top k | [DLLMA ch12], [KGRAG ch6] |
| Structured decision fields | At least 90% complete and accurate | [PLAYBOOK ch3]; a rule for fields, not articles |
| Knowledge-base review | Quarterly at minimum, monthly for customer-facing content | [PLAYBOOK ch3] |
| Memory TTL | On every entry; 60-365 days by category in one book's examples | [PRODGUIDE ch8] |
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
- [ ] Layout is shared prefix → per-user stable block → append-only → volatile tail. Nothing per-user or time-dependent sits inside or before the shared prefix, serialisation is deterministic, and anything that changes every turn sits in the tail. A cache-layout finding or fix names the provider's minimum cacheable length and opt-in mechanism, and the cached span meets them.
- [ ] Hard constraints sit in the never-compacted prefix and costly ones are also enforced in code. The original task statement survives compaction; in chat, a current-task line and an attempt ledger track task switches and tried steps.
- [ ] Every source passed the readiness audit before indexing (top questions answered, retired and conflicting content archived, owner and review schedule). The 90% rule is applied to structured decision fields, not to articles, and volatile data is a live query.
- [ ] The store follows the query types: hybrid by default; a graph only with a measured hybrid failure on relationship or corpus-wide questions and a plan to keep it current; routing accuracy is scored.
- [ ] A graph is built from validated triplets, with writes only on the ingest path. Generated graph and SQL queries run read-only under the caller's entitlements, from templates or an allowlist, with row limits and timeouts.
- [ ] Retrieval is hybrid, or a measurement shows one side adds nothing. It reranks before passing, passes few chunks, has a floor and a not-found path, and returns citable IDs.
- [ ] Indexing is idempotent, and every ingest is checked (per-source counts, a canary query); a zero count fails the run.
- [ ] Permission filtering happens inside the search, before ranking, with deny rules (walls, barriers, holds) as well as allow lists; caches are keyed by permission scope and ingest generation, and a wall change purges caches, recalled memory and session state for the barred scope.
- [ ] Cited answers pass a cite-and-verify check in code: cited IDs in the request's evidence set, quotes verbatim, a support check per claim, unsupported claims removed or flagged, non-authoritative parts labelled.
- [ ] A review of a running system includes the clean-up of data the old design already stored, with a deletion log; legal, privacy and privilege questions go to the privacy or legal owner as open questions.
- [ ] Each memory type has a store, scope, trigger, decider, validation, update rule, expiry, deletion path and read path.
- [ ] Durable entries carry category, source, confidence, last verified, TTL and sensitivity. Expired entries count as unknown, references replace raw content and personal data, and writes that steer actions other people see are proposed and approved.
- [ ] No per-turn LLM memory call without a measured gain.
- [ ] Every memory candidate is scanned for secrets and personal data whatever its source; tool, web and document text never becomes durable memory without a reviewed step; user text is a proposal under the approval rule; and identity comes from the session (memory tools included: scope keys and author role are bound by the server).
- [ ] Every store a client-supplied ID can reach (memory namespaces, thread and checkpoint IDs, run histories, caches) is bound to the authenticated user: thread ownership is checked on read, resume and list, no scope key falls back to a default identity or an environment variable, the framework's identity hook is verified at the pinned version, and leak tests cover another user's thread as well as their memory.
- [ ] State and memory with more than one possible writer use conditional writes or a single writer per thread or scope; none is a blind overwrite unless last-writer-wins is accepted for a low-value item with its collision likelihood stated.
- [ ] Table and metric queries carry the caller's row and column entitlements; governed numbers come from a metric catalog.
- [ ] Live system-of-record data is fetched, not memorised.
- [ ] Every assembled block is fenced and labelled with its origin when it enters, recalled memory and agent-written notes included, so a provenance gate in code can act on the labels.
- [ ] Agentic retrieval, if present, has a named reason, a mandatory-search rule, budgets in code and an abstain exit.
- [ ] Evaluation scores retrieval and generation separately, covers unanswerable, identifier and per-scope cases, and includes memory update, abstention and deletion tests plus cache hit rate.
- [ ] Every proposed addition has a before/after metric, and the rollout is staged.
- [ ] Hand-offs to sibling skills are named where the work leaves this skill's scope.
- [ ] Credentials are cited by file:line and kind (for example "messaging app secret literal"), never by value or any fragment of it; the same holds for keys in URLs, logs and saved state, and public vendor defaults may be named. Before returning, the draft is searched for every credential literal found in the input and each one is removed.

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
| An allow-list-only ACL for a firm with ethical walls or information barriers | Deny scopes evaluated in the search; a wall change also purges caches and memory (retrieval-pipeline.md §2.3) |
| Trusting the model's citations because the IDs look real | Check in code that cited IDs were in the evidence, quotes are verbatim and each claim is supported (retrieval-pipeline.md §3.8) |
| Fixing the write path of a leaky memory and leaving the old entries in place | Clean up what is stored: inventory, purge, backfill, deletion log (memory-design.md §6.1) |
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
| Next turn ID = last ID + 1, or an unconditional overwrite of state more than one writer can reach | Conditional create or versioned update, or a time-ordered unique ID; reload on conflict (memory-design.md §8) |
| Memory tools that take `session_id`, `user_id` or `role` as model-filled parameters | The server binds scope and role from the authenticated request; test with another session's ID |
| Binding the memory namespace to the user while threads stay addressable by any client-chosen ID | Record the thread's owner at creation and check it on read, resume and list; leak-test another user's thread (memory-design.md §8) |
| Treating a finished ingest as a populated index | Per-source counts and a canary query after every run; zero fails the run (retrieval-pipeline.md §2.7) |
| Text-to-SQL for a governed number, or any table query under one shared read-only role | Metric catalog with vetted, parameterised queries; the caller's row and column entitlements at the data layer |
| Writing the same item to two stores from the request path | One canonical store; other stores are projections built by an idempotent job (retrieval-pipeline.md §5.1) |
| Tuning the retriever over a knowledge base nobody audited | Audit the sources first; no reranker recovers an answer the corpus gets wrong (retrieval-pipeline.md §0) |
| Applying the 90% completeness rule to knowledge-base articles | It is a threshold for structured decision fields; articles pass the coverage, staleness and documentation checks |
| Adding a graph because GraphRAG "works better", or replacing vector search with it | Hybrid by default; a graph only for measured relationship or corpus-wide failures, then route |
| Model-written Cypher or SQL run through an account that can write, or a shared read-only role | Writes only on the ingest path; read-only, caller-scoped queries from templates or an allowlist (retrieval-pipeline.md §5.3) |
| Using memory as a knowledge base, or saving raw messages to be safe | Memory for preferences, constraints and defaults; facts retrieved with a citation; store references and the smallest useful unit |
| Rendering recalled memory or another agent's notes as plain prompt text | Fence and label with the stored provenance; a gate in code refuses content-triggered calls (context-assembly.md §9) |

## Sources

These are independent notes that paraphrase and cite the works below; they are not affiliated with or endorsed by the authors or publishers. Citation keys used in this skill and its references:
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
- **PRODGUIDE**: *Agentic AI Systems: The Complete Guide for Building Production AI Agents*, ch8 (state, memory and knowledge; the governed memory entry; write, expiry and correction rules), ch9 (conflict rules and source quality).
- **PLAYBOOK**: *Agentic AI Playbook*, ch1 (new-hire framing), ch3 (data readiness: knowledge-base audit, warning signs, the 90% rule for decision fields, the documentation test, answer-first writing, stable and volatile data), ch4 (memory governance questions).
- **KGRAG**: *Building AI Agents with LLMs, RAG, and Knowledge Graphs*, ch5 (RAG vs fine-tuning, fine-tuning the embedder), ch6 (weighted hybrid search, query routing, chunk reordering), ch7 (knowledge graphs, building a graph with an LLM, graph quality, graph-guided retrieval, limits, HybridRAG).
- **HARDMCP**: *Hardening MCP Servers*, ch6 (fenced and labelled sources, blocking actions triggered by content).

Andrew Ng, The Batch letters (cited by title and date with the NG key):
- *Context for Coding Agents*, 2026-03-09: https://www.deeplearning.ai/the-batch/crowdsourced-context-for-coding-agents
- *Let's Help Agents Share Their Work*, 2026-03-16: https://www.deeplearning.ai/the-batch/lets-help-agents-share-their-work
- *Make All Your Tokens (and Your Brainwork) Count*, 2026-07-10: https://www.deeplearning.ai/the-batch/make-all-your-tokens-and-your-brainwork-count

Companion repo (read as a pattern; never copy its credentials cell): KGRAG, https://github.com/PacktPublishing/Modern-AI-Agents (chapter 7 notebook on building a graph and answering through generated Cypher).

Practitioner lab notes (AWS AgentCore and data labs, 2026-10). They are the source of the guidance on concurrent writes, memory tool scope, ingest checks, metric catalogs, store choice, idempotent indexing, graph integrity, vector indexes and data-layer entitlements, and of [references/aws-implementation-notes.md](references/aws-implementation-notes.md).

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
- https://github.com/langchain-ai/langchain-neo4j/blob/main/libs/neo4j/langchain_neo4j/chains/graph_qa/cypher.py (checked 2026-10-19)

AWS documentation (checked 2026-10-11, and 2026-10-19 for the last three; used in [references/aws-implementation-notes.md](references/aws-implementation-notes.md)):
- https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/specify-long-term-memory-organization.html
- https://docs.aws.amazon.com/opensearch-service/latest/developerguide/serverless-genref.html
- https://docs.aws.amazon.com/opensearch-service/latest/developerguide/serverless-configure-neural-search.html
- https://docs.aws.amazon.com/bedrock/latest/userguide/knowledge-base-build-graphs.html
- https://docs.aws.amazon.com/neptune-analytics/latest/userguide/query-APIs-execute-query.html
