# Memory design reference

Depth for Procedure steps 2 and 5. Citation keys are expanded in SKILL.md under Sources.

Contents: 1 Information map · 2 Do you need long-term memory · 3 Types by update semantics · 4 Write policy · 5 Read policy · 6 Scope, privacy, deletion · 7 Consolidation and forgetting · 8 Threads and checkpoints · 9 Multi-agent memory · 10 Agent-written notes · 11 Poisoning (summary)

Keep three things apart. The **context window** is the input of one call. **Memory** is state outside the model that survives the call. **Context** is what you put in the window for this step. Storing something is not the same as putting it in the prompt [SYSTEMS ch9]. There are two decisions to design: what the assembler reads into each call, and what the write gate lets into durable memory.

## 1. Information map: classify first, then route

| Class | Example | Source of truth | How it reaches the call | Freshness rule |
|---|---|---|---|---|
| Instructions, procedures, hard rules | Persona, policies, "confirm before deleting" | Versioned prompt repo | Static prefix; costly rules also enforced in code | Changed by release, never mid-run |
| Task statement and constraints | "Migrate service X; don't touch prod" | First user turn / ticket | Original statement in the per-user stable block, never trimmed; current-task line in the volatile tail | Current-task line replaced on a task switch (context-assembly.md §4) |
| Steps tried this session | "Restarted VPN client: failed, error 809" | Attempt ledger (thread state, code-maintained) | Volatile tail, verbatim | Per turn; closed on task switch; summarised at session end |
| User facts and preferences | Units, language, role, "prefers email" | Semantic fact store (upsert) | Small profile block, every call | Expiry per category; newest wins |
| Episodes | "Last month's refund case and how it ended" | Append-only episode log | Retrieved by recency or similarity, with a floor | Summarise or archive with age |
| Thread state | Messages, tool results, plan, scratch | Checkpointer | Recent turns verbatim + summary | Per step |
| Corpus knowledge | Handbook, manuals, wiki | Document index (retrieval-pipeline.md) | Retrieved evidence | Re-index on change; staleness status (retrieval-pipeline.md §2.5) |
| Mixed records: knowledge + live state + PII | Helpdesk tickets, email threads, chat logs | The source system | Split: sanitised cards in an index, the user's own records via a live tool (retrieval-pipeline.md §2.6) | Cards regenerated from source; records always fetched |
| Live system-of-record data | Balance, order status, stock, PTO days | The source system | Tool call or pre-provisioned at run start | Always fetched fresh; **never copied into memory** [AGENTICAI ch7] |
| Tool and web output | API responses, pages | The tool | Projected fields in history | Ephemeral; never auto-promoted to memory |
| Parametric knowledge | Whatever the model learned | Weights | Implicit | Frozen; can't be scoped or deleted, so never use for user data |

Provisioning: fetch facts a step will certainly need (the user's employee ID, tenant, plan tier) before the agent runs instead of making it ask [ENTERPRISE ch5 §Context].

**When the user asks to "remember" system-of-record data** (their devices, benefit plan, open tickets), don't silently refuse and don't copy it. Say in the design that the agent will know it at every session because it is fetched or provisioned live, explain why (it changes, the source system owns access and deletion), and offer a short-lived cached snapshot only if latency requires it, keyed by user and expiring within the session.

## 2. Do you need long-term memory at all?

- Long-term memory pays only when **users or tasks recur**. In the one controlled experiment in the library, an SQL agent that logged its own evidence gained nothing on a benchmark whose questions don't repeat. On a variant seeded with rephrased near-duplicates, it went from 37.7% to 67.2% over time [BUILDAGENTIC ch4 §Experiment: The Extended Mind Thesis and Agentic Memory]. For one-shot tasks, thread state plus good retrieval is usually enough [BUILDAPPS ch6].
- **Memory is not RAG.** A corpus is curated by someone else; memory is written by the agent and needs write rules, scoping and deletion, even when both sit in the same vector database ([SYSTEMS ch9]; [DEFGUIDE ch10]).
- Ignore vendor-style success figures. One book reports 70% faster scheduling and 65% fewer errors from memory projects with no baselines or methods [AGENTICAI ch7]. Plan your own before/after measurement instead.

## 3. Types, classified by update semantics

Every book uses the episodic / semantic / procedural split, and they disagree at the edges (is a preference an episode or a fact?). Classify by **how the item should be updated**, because that decides the store and the hygiene rules.

| Type | Holds | Update semantics | Store | Read path | Characteristic failure |
|---|---|---|---|---|---|
| Thread state (working / short-term) | Messages, tool results, plan, scratch variables | Append; checkpoint each step | Checkpointer keyed by thread ID; keep the raw trajectory even when the in-context copy is trimmed [ILLUSTRATED ch4] | Recent turns + summary | Evicting the task statement |
| Semantic facts (incl. preferences) | Stable facts about user, entity, domain | **Upsert / supersede**: a new value replaces the old | Keyed records (relational/KV) as the source of truth, plus an optional embedding index as a projection | Profile block by key; search when there are many | Contradictions, stale values, hallucinated facts stored as truth |
| Episodic | Past task: input, actions, outcome, timestamp | **Append-only**, summarise later | Append log; add an embedding index only for similarity recall | Two different reads. **By recency** for continuity ("where we left off": latest note if recent). **By similarity with a floor** for "a case like this" | Irrelevant recall; overfitting to old cases |
| Procedural | How to behave: instructions, workflows, format and safety rules | **Versioned, reviewed** like code | Prompt repository / workflow definitions [DLLMA ch10 §Data Stores] | Stable prefix | Unreviewed rule changes; reinforcing bad behaviour |

Store preferences as facts with an upsert rule [DEFGUIDE ch10], not as episodes [AGENTICAI ch7]. An episode log of every mention forces the model to reconcile contradictions at read time. Storage options: in-process (fast, lost on restart), database (exact, durable, no semantic match), vector store (semantic, approximate), or hybrid, which is the common production choice of exact records plus semantic projections [SYSTEMS ch9]. If memory is a handful of keyed categories plus a few recent notes, a key lookup is enough and a vector store adds nothing. Add one only when the number of items outgrows what you can inject or select by key.

## 4. Write policy

### 4.1 When to write (triggers)
Write when an item is needed later in this workflow, useful across sessions, a stable preference or durable fact, expensive to recompute, or an important conclusion or milestone [SYSTEMS ch9]. Promotion signals: **importance** (the user stated a requirement or a correction), **frequency** (it keeps recurring) and an **explicit request** ("remember that…") [AGENTICAI ch7]. Store what improves future behaviour, not everything the system observes [SYSTEMS ch9]. Normalise or summarise raw tool output before storing; it is usually too large and too fragile.

### 4.2 Who decides (the write ladder)
| Decider | Extra calls | Rough precision | Use |
|---|---|---|---|
| Rules and regex (explicit "remember", corrections, form fields) | none | ~70% | Always the first layer |
| Embedding similarity against existing memory | none (embedding only) | ~85% | Dedupe, detecting updates |
| Small encoder classifier | none (small model) | ~90% | Ambiguous candidates at volume |
| Full LLM judge | one per step | ~95% | Rare, high-stakes ambiguous writes |

The precision figures are one author's estimates with no stated method [DEFGUIDE ch10]. The shape still matters: an LLM storage decision every step adds a hidden call per step (five extra in a five-step ReAct loop) and roughly doubles the bill. **Default:** rules plus an optional classifier on the hot path. Run LLM extraction in **batch** (every N user messages, at session end, or in a background worker) to *propose* candidates, and let deterministic code accept, dedupe and supersede them. That is how the book's own companion notebook runs its memory manager [DEFGUIDE ch10]. This rule covers durable memory. Per-turn thread state such as the attempt ledger and current-task line is maintained by code during the session (context-assembly.md §4), and only its end-of-session summary passes through this write path.

### 4.3 Validate before persisting
- Size cap per record.
- Refuse secret and identifier patterns: national ID numbers, payment-card digit runs, PEM private keys, cloud access keys, API keys [DEFGUIDE ch10]. The regexes are examples; use your DLP rules where you have them.
- **Source check.** Text that came from a tool, web page, retrieved document or another agent is never written to durable memory directly. Store a normalised candidate with provenance and status `proposed` until it is promoted by a rule or a review.
- Identity: take the user and tenant from the verified session, never from a client-supplied string or the model's output [DEFGUIDE ch10].

### 4.4 Update rules (apply at write time, not read time)
1. Supersede: a new fact that contradicts an old one in the same category marks the old one `superseded` and links to it.
2. Replace single-valued categories (units, timezone, display language) instead of appending.
3. Dedupe by normalised content or key.
4. Drop candidates below a confidence threshold (the book's example uses 0.7).
5. Cap the total per user; when it's full, merge or evict the least used.
6. Resolve known contradictions deterministically ("dark mode" against "light mode": newest wins) [DEFGUIDE ch10].

### 4.5 Record schema
```
memory_id, org_id, user_id, type (fact|episode|procedure), category/key, value,
source (user_msg:<id> | tool:<name> | admin | consolidation), status (proposed|active|superseded|deleted),
confidence, created_at, updated_at, expires_at, supersedes, last_retrieved_at, retrieval_count
```

### 4.6 Minimal write gate (pattern sketch)
```python
import re
EXPLICIT = re.compile(r"\b(remember|from now on|i prefer|always|never|call me)\b", re.I)

def gate(candidate, source, session):
    if source != "user":                       # tool/web/doc text: propose only, never auto-persist
        return ("proposed", candidate)
    validate(candidate)                        # size cap + secret/PII patterns; raises on failure
    if EXPLICIT.search(candidate.text):
        return ("active", candidate)           # explicit request: zero cost, predictable
    return ("active", candidate) if classifier(candidate.text) >= 0.8 else ("drop", None)

def upsert(store, session, fact):              # scope comes from the session, not the model
    ns = (session.org_id, session.user_id, "fact")
    old = store.get(ns, fact.category)
    if old and old.value == fact.value: return  # dedupe
    store.put(ns, fact.category, fact, supersedes=old and old.id)
```

## 5. Read policy

- Inject only the memory this decision needs, not the full stored history. Retrieval from memory is a filtering problem: what is relevant now, what is too old or weak, what should be summarised first, and what stays stored but out of the prompt [SYSTEMS ch9].
- Score candidates by relevance, recency and importance with a **minimum similarity floor**, not a fixed top-k ([AGENTICAI ch7]; [ILLUSTRATED ch4]).
- Use a canonical **profile** per user as the source of truth, small and always injected, and treat semantic-search rows as projections of it. Ad hoc captures sit under transient keys as `proposed` until promoted. Keep extraction and application of updates as separate, testable steps (the companion notebook to [DEFGUIDE ch10]).
- Freshness: expiry per category; volatile data is fetched, not recalled; stored state must not stop the agent from re-verifying when the situation needs it [SYSTEMS ch9].
- **Inspectable trail:** log which memory IDs were injected into each call, with their scores and the reason they were selected. Otherwise a bad answer gets blamed on the model when an injected memory caused it [SYSTEMS ch9].

## 6. Scope, privacy and deletion

- Namespace every record by organisation, user and memory type. Keep an organisation-shared segment that only admins can write [DEFGUIDE ch10].
- Scope by agent kind: personal agents default to isolated memory; team agents get shared, access-controlled spaces; organisation-wide agents run under retention, logging and audit rules; users can inspect and delete what is kept about them [BUILDAPPS ch13 §Shared Memory and Context Boundaries].
- Obligations: collect only what is needed, pseudonymise before storing, let users view, edit and delete, and make "forget this" erase the item from databases and backups [AGENTICAI ch7].
- **Deletion map.** A deletion must reach every copy:

| Copy | Delete how |
|---|---|
| Fact/episode records | Hard delete or tombstone, then purge |
| Embedding index rows | Delete by `memory_id` |
| Derived summaries, consolidated profiles | Recompute without the item |
| Sanitised cards built from deleted source records (tickets, email) | Delete the card or regenerate it from the remaining records (retrieval-pipeline.md §2.6) |
| Thread checkpoints and transcripts | Redact or expire per retention policy |
| Retrieval and answer caches | Invalidate by user scope |
| Logs, traces, eval datasets | Retention policy; redact on request |
| Backups | Expiry window documented and honoured |

- Storage location is also a UX choice. Client-side context is fast but lost across devices; server-side gives continuity at some privacy and latency cost; hybrids are common [BUILDAPPS ch3 §Context Retention and Continuity].

## 7. Consolidation and forgetting

| Mechanism | What | Watch out for |
|---|---|---|
| Time-based pruning / expiry | Drop or archive by age, per category | Expiring something still true; set TTL per category |
| Compression | Summarise old episodes | Summaries of summaries over-compress [ILLUSTRATED ch4] |
| Usage-based decay | Strengthen items that keep being retrieved; fade the rest (MemoryBank's forgetting curve) [ILLUSTRATED ch4] | Popular-but-wrong items get stronger |
| Periodic merge | Merge many small facts into one consolidated profile; drop stale contradictions, newest wins [DEFGUIDE ch10] | **LLM rewrites degrade memory when repeated** [ENTERPRISE ch5 §Memory and Planning]; keep originals versioned and validate the merge |
| Explicit removal | User or admin deletes; outdated facts superseded | Must reach every copy (section 6) |

LLM-curated memory (A-MEM's linked, self-rewriting notes; MemoryBank's portraits) suits research and personal assistants, where recall quality matters more than predictability [ILLUSTRATED ch4]. In production, adopt it only with a measured gain, provenance on every record, and an edit/delete path. The cheap deterministic path is the default because cost, predictability and auditability all favour it.

## 8. Thread state, checkpoints and replay

- Checkpoint thread state after every step, keyed by thread ID. That gives crash recovery, human-in-the-loop pauses and replay [DEFGUIDE ch10].
- Time travel (rewind to an earlier checkpoint, edit, fork) is useful for debugging and audit. It **rewinds the thread, not the long-term store**, so decide explicitly whether durable memory is versioned or rolled back on replay [DEFGUIDE ch10].
- Treat checkpoint payloads and stored memory as untrusted text when they are read back.

## 9. Multi-agent memory

| Topology | Good | Bad |
|---|---|---|
| Per-agent local | Clean contexts | Agents drift apart; duplicated knowledge |
| Shared global store | One source of truth | Every agent's context fills with the others' noise; needs concurrency control |
| **Hybrid** (local working state + shared durable facts and coordination artifacts) | What most production systems use [DEFGUIDE ch10] | Needs clear ownership of shared writes |

Pass a sub-agent the current task brief, not the parent's history. Choose its persistence explicitly: per-invocation (remembers nothing between calls), per-thread (keeps its own history within the thread) or stateless (also loses interrupts and crash recovery) [DEFGUIDE ch10]. Messages between agents are shared context too, and need the same budgeting [ILLUSTRATED ch4].

## 10. Agent-written notes and memory tools

- Giving the agent a write tool (an evidence log, a notes file, a memory directory) works for long tasks that span context resets, and for tasks that repeat [BUILDAGENTIC ch4 §Experiment: The Extended Mind Thesis and Agentic Memory]. Every note is an unreviewed model output, so add validation, provenance, size caps, expiry, and an edit/delete path.
- A file-based memory tool also needs path-traversal checks and sensitive-data stripping, which provider memory tools leave to the application (provider-notes.md).

## 11. Poisoning (summary; threat model → agent-threat-modeler)

Untrusted content gets written to memory and comes back later as trusted context. Agents that write and retrieve memory aggressively are easier to exploit, and prompt-injection defences don't fully cover this path [DEFGUIDE ch10]. The minimum controls belong in any memory design: provenance on every record, no automatic promotion from tool, web or document text, validation before write, monitoring for unusual write volume or content, and treating read-back memory as data, not instructions. Hand attack trees, red-team cases and cross-session exploitation to agent-threat-modeler.
