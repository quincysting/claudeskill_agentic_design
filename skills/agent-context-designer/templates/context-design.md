# Context & memory design: <system name>

**Assumptions:** <what you assumed because it wasn't given; mark each so the user can correct it. Single-company deployment? Then say what "tenant" maps to (business unit, region, role group).>

Include a section marked *(optional)* only when its condition holds. Otherwise write one line saying why it doesn't apply, or drop it.

## 0. Decisions in brief
<5-8 bullets: retrieval mode and why; memory types kept (or "no long-term memory, because…"); what the user asked to "remember" that will be fetched live instead; layout and budget headline; compaction approach; top risks; the first thing to build and the metric that unlocks the next>

## 1. Model calls

| Call | Decision it makes | Model / window | Prefix tokens | Input p50/p95 (measured or est.) | Output allowance | Calls per request |
|---|---|---|---|---|---|---|

## 2. Information map

| Information | Class | Source of truth | Reaches the call via | Freshness / expiry |
|---|---|---|---|---|

## 3. Retrieval
- **Mode:** <none / cached corpus / always-retrieve / gate / agentic / GraphRAG / text-to-SQL> because <named reason>.
- **Sources and indexes:** one line per index: content, trust tier (official / derived / community), ACL, owner. Mixed records (tickets, email, chat): what goes into a sanitised index and what stays a live lookup.
- **Index time:** parsing checks per format; chunking rule; chunk context prepended; metadata schema incl. `tenant_id`, `acl_groups`, `version` or derived `status` and `last_modified`; re-index and deletion triggers.
- **Staleness:** version source, or for undated documents the detection signals, age limits per document type, and the owner review queue.
- **Query time:** query handling (split instructions, rewriting yes/no and why); BM25 ∥ dense, fused with RRF (k=…); ACL pre-filter from the session; candidates …; reranker …; floor …; chunks passed …; per-source quotas and trust order; evidence item format with IDs, date and status; not-found behaviour; error routing.
- **Agentic controls** *(optional: only if the agent controls retrieval)*: mandatory-search rule; first retrieval in code?; budgets (hops / calls / tokens / seconds); stop and abstain rule; what is carried between hops.
- **Caches:** key (incl. permission scope and index version) and invalidation.

## 4. Memory
Long-term memory warranted? <yes/no + the recurrence evidence>

| Type | Store | Key / scope | Write trigger | Decider | Validation | Update rule | Expiry / forgetting | Deletion path | Read path (floor, cap) |
|---|---|---|---|---|---|---|---|---|---|

- **Thread state:** checkpointer, retention, where the raw transcript is kept; current-task line and attempt ledger (chat) or progress record (long runs): who writes them, cap, what happens at session end.
- **Replay/fork policy** *(optional: only if threads are replayed or forked)*: is long-term memory versioned or rolled back?
- **Multi-agent topology** *(optional: only with sub-agents or several agents)*: shared vs local memory, sub-agent persistence mode.

## 5. Context assembly
Give the main call the full layout and budget. For every other call, add one row to the short-form table, noting only what differs from the main call.

**Layout (main call)**
```
shared static:    …   identical for every user
per-user stable:  …   changes at session start / compaction
append-only:      …
volatile tail:    …   rebuilt every turn (current-task line, ledger, evidence, date, latest input)
```

**Budget (main call)**

| Bucket | Ceiling (tokens) | Owner | Overflow rule |
|---|---|---|---|
| Output allowance | | | |
| Shared prefix (tools + system + rules) | | | |
| Per-user block (identity, profile, original task) | | | |
| Session summary | | | |
| Progress record *(optional: long runs)* | | | |
| Recent turns | | | |
| Current-turn tool results | | | |
| Current-task line + attempt ledger *(optional: chat)* | | | |
| Recalled memory | | | |
| Evidence | | | |
| **Ceiling total** (must be < window) | | | |
| **Target p95 total** (from the measured prefix and the degradation curve) | | | |

**Other calls (short form)**

| Call | Model | Sees | Input cap | Output cap | Runs how often |
|---|---|---|---|---|---|

**Compaction:** trigger (starting value and how it will be tuned); kept verbatim; must-survive checklist; summary cap; raw transcript location; survival test.
**Tool results / definitions:** projection rules; clearing policy (batch size); toolset fixed per run?
**Sub-agents** *(optional)*: brief contents; return size; persistence mode.
**Long runs** *(optional: runs beyond one window or session)*: progress record; checkpoints; just-in-time loading.
**Cost** *(when there is a target)*: estimate or low/high range, the assumption that drives it, and the measurements that will replace it.

## 6. Safety and privacy
- Permission enforcement points; identity source; cache scoping.
- Untrusted-content rule for memory writes and for instructions.
- Deletion map (every copy, including sanitised cards derived from deleted records).
- Hand-offs: <what goes to agent-threat-modeler>

## 7. Evaluation
- Test-set slices and sizes (incl. unanswerable, identifier, per-scope, stale-version, undated near-duplicates, cross-source conflicts, multi-session, tried-step repeat, task switch).
- Retrieval: recall@k at each stage and per index, MRR, by slice. Generation: faithfulness, completeness, abstention, citation correctness.
- Memory: the five abilities + write precision/recall, deletion and leak tests.
- Context: cache hit rate, tokens per bucket p50/p95, compaction survival, cost per task.
- Online: sampling rate, judge model family.

## 8. Rollout

| Stage | Build | Measure before moving on | Target |
|---|---|---|---|

## 9. Open questions
