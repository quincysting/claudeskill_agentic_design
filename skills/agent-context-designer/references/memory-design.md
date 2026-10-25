# Memory design reference

Depth for Procedure steps 2 and 5. Citation keys are expanded in SKILL.md under Sources.

Contents: 1 Information map (state, memory, knowledge) · 2 Do you need long-term memory · 3 Types by update semantics (temporal graph memory) · 4 Write policy (4.5 governed entry; 4.6 write gate; 4.7 proposed and approved writes, expiry, correction) · 5 Read policy (growth worksheet) · 6 Scope, privacy, deletion (binding every store, employer-run assistants; 6.1 cleaning up a running system) · 7 Consolidation and forgetting · 8 Threads, checkpoints and concurrent writers · 9 Multi-agent memory · 10 Agent-written notes and memory tools · 11 Poisoning (summary)

Keep three things apart. The **context window** is the input of one call. **Memory** is state outside the model that survives the call. **Context** is what you put in the window for this step. Storing something is not the same as putting it in the prompt [SYSTEMS ch9]. There are two decisions to design: what the assembler reads into each call, and what the write gate lets into durable memory.

A second cut, by lifecycle, decides what may become memory at all [PRODGUIDE ch8]. **State** is what the current run tracks: goal, plan, payload previews, tool receipts, pending approvals, open questions. When the run ends it becomes the run record, which is evidence for debugging and evaluation, not memory (the run record belongs to agent-harness-designer). **Memory** is what is kept across runs to remove repeated friction: preferences, constraints, defaults and stable facts. **Knowledge** lives in documents and systems of record and is retrieved when needed, because it changes and retrieval brings provenance [PRODGUIDE ch8 §Memory Is a Tool With Consequences]. The read rule follows: consult memory for how the user wants things done, and retrieval for what is true [PRODGUIDE ch8 §A Memory Architecture That Scales Without Code]. Facts copied into memory go stale and lose their source, so the agent is wrong and still sounds right.

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

Store preferences as facts with an upsert rule [DEFGUIDE ch10], not as episodes [AGENTICAI ch7]. An episode log of every mention forces the model to reconcile contradictions at read time. Storage options: in-process (fast, lost on restart), database (exact, durable, no semantic match), vector store (semantic, approximate), or hybrid, which is the common production choice of exact records plus semantic projections [SYSTEMS ch9]. If memory is a handful of keyed categories plus a few recent notes, a key lookup is enough and a vector store adds nothing. Add one only when the number of items outgrows what you can inject or select by key. When a design spans several store types (a key/range store for threads, a graph, a search index, a relational source of record), choose each by its access pattern and give every item one home (retrieval-pipeline.md §5.1).

**Temporal graph memory.** Semantic memory need not be key-value. A knowledge graph stores facts as (head, relation, tail) triplets, and a temporal graph also records when each fact held [KGRAG ch7 §A formal definition of graphs and knowledge graphs]. That suits memory about entities whose relations change (who owns which account, since when, and who owned it before). Give each edge a valid-from and valid-to instead of overwriting it, so supersession keeps the history and "as of" questions have an answer. The graph needs the same update, cleaning and deletion pipelines as any store [KGRAG ch7 §Knowledge hosting and deployment]; building one is in retrieval-pipeline.md §5.2. For free-form preferences, keyed records stay simpler.

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
- Identity: take the user and tenant from the verified session, never from a client-supplied string or the model's output [DEFGUIDE ch10]. That includes memory exposed as tools (section 10).

### 4.4 Update rules (apply at write time, not read time)
1. Supersede: a new fact that contradicts an old one in the same category marks the old one `superseded` and links to it.
2. Replace single-valued categories (units, timezone, display language) instead of appending.
3. Dedupe by normalised content or key.
4. Drop candidates below a confidence threshold (the book's example uses 0.7).
5. Cap the total per user; when it's full, merge or evict the least used.
6. Resolve known contradictions deterministically ("dark mode" against "light mode": newest wins) [DEFGUIDE ch10].

### 4.5 The governed memory entry
PRODGUIDE gives every long-term entry eight fields: key, value, category, source, confidence, last verified, TTL and sensitivity [PRODGUIDE ch8 §A Memory Architecture That Scales Without Code]. Combined with the hygiene fields above:
```
memory_id, org_id, user_id, type (fact|episode|procedure),
key, value | value_ref, category (preference|constraint|default|stable_fact),
source (user_confirmed:<msg_id> | approved_artifact:<id> | tool_receipt:<id> | tool:<name> | admin | consolidation),
confidence (verified|inferred, or a classifier score), last_verified_at, ttl_days, expires_at,
sensitivity (low|restricted|forbidden), status (proposed|active|superseded|expired|deleted),
reason, created_at, updated_at, supersedes, last_retrieved_at, retrieval_count
```
- **Category** selects the update rule (4.4) and the approval rule (4.7). Keep personal preferences apart from business defaults so one category doesn't pollute the other [PRODGUIDE ch8 §Memory Write Rules, Expiration, and Correction].
- **Source and confidence** let the read path treat inferred entries with caution. An inferred entry never overrides a verified one.
- **A TTL on every entry.** PRODGUIDE's examples run from 60 days for an owner map to 365 for a tone preference [PRODGUIDE ch8 §A Memory Architecture That Scales Without Code]. An expired entry counts as unknown: refresh it from the tool or document that owns it, or ask the user to confirm ("I have this as your default; is it still right?"). Never use it silently in the meantime [PRODGUIDE ch8 §Memory Write Rules, Expiration, and Correction].
- **Sensitivity** `forbidden` means the value is never stored. Credentials, secrets, financial details and personal data stay out unless explicitly required and approved, and even then the entry holds a reference (`value_ref`: a record ID or link) instead of the raw value. Store an identifier or link instead of raw message content whenever that is enough [PRODGUIDE ch8 §Memory Write Rules, Expiration, and Correction]. Confidential client material and privileged communications are the same case: keep a reference to the record in the system that holds it, never the content. When an entry concerns a business record (a case, matter, account or claim), tie its retention to that record, so it expires when the record closes or its retention period ends, whichever comes first.
- **Reason** names the future friction the entry removes. An entry nobody can justify in one sentence ("this saves time later") is deleted at the next review.

### 4.6 Minimal write gate (pattern sketch)
Validation runs on every candidate, whatever its source: tool output and web pages carry API keys and account numbers as often as user text does. The gate only decides what becomes a proposal; the approval rule in 4.7 decides what becomes active. The explicit-request pattern is narrow on purpose: "always" or "never" would turn "I never got my refund" into memory. The 0.8 cut-off is an example threshold on the candidate classifier's score. It is a different knob from the fact-confidence threshold in 4.4 rule 4 (the book's example uses 0.7); set each from a labelled sample of your own candidates.
```python
import re
EXPLICIT = re.compile(r"\b(remember (that|this|my)|from now on|call me)\b", re.I)
AUTO_OK = set()  # categories that have earned automatic writes (4.7): empty at launch, e.g. {"units"} later
CLASSIFIER_MIN = 0.8  # example cut-off on the classifier score; not the fact-confidence threshold (4.4)

def gate(candidate, source, session):
    validate(candidate)                        # every source: size cap + secret/PII patterns; raises on failure
    if source != "user":                       # tool, web, document or agent text: a proposal at most
        return ("proposed", candidate)
    if EXPLICIT.search(candidate.text) or classifier(candidate.text) >= CLASSIFIER_MIN:
        return ("proposed", candidate)         # user text is a proposal too; promote() applies 4.7
    return ("drop", None)

def promote(proposal, approved_by=None):       # the 4.7 rule, in code
    earned = (proposal.source.startswith("user_confirmed") and proposal.category in AUTO_OK
              and proposal.sensitivity == "low")
    return "active" if earned or approved_by else "proposed"

def upsert(store, session, fact):              # scope comes from the session, not the model
    ns = (session.org_id, session.user_id, "fact")
    old = store.get(ns, fact.category)
    if old and old.value == fact.value: return  # dedupe
    store.put_if(ns, fact.category, fact, supersedes=old and old.id,
                 expect_version=old.version if old else 0)  # conditional: reload on conflict (section 8)
```

### 4.7 Proposed and approved writes, expiry and correction
Treat a memory write like a draft-first tool call: the agent proposes, and a person or a rule approves [PRODGUIDE ch8 §Memory Write Rules, Expiration, and Correction].
- **Proposal.** A candidate that passes the gate (4.6) becomes a memory-update proposal: key, value, category, reason, source, TTL, sensitivity. It is easy to approve or reject and leaves a trail in the run record.
- **Who approves.** Early on, a person approves every write. Automatic writes come later, per category, once that category's proposals are reliably right, and only for low-risk categories (formatting, units, language). Constraints, defaults that steer actions other people see, and restricted categories keep approval. A personal assistant learning low-risk preferences can skip it where approval prompts annoy more than they protect.
- **Timing.** Save only after a decision is confirmed. A default the agent guessed because information was missing is not memory until the user confirms it; otherwise one-off assumptions become permanent behaviour.
- **Correction.** "Don't do that anymore" becomes a proposal that shows the current entry, the new value and its TTL. After approval the old entry is superseded (4.4), the agent confirms the change, and later behaviour follows it.
- **Keep it small.** PLAYBOOK asks four questions of every item (what is stored, who may update it, how long it lasts, when it is reviewed) and one test: what task does this memory improve next time [PLAYBOOK ch4 §Memory: What to Keep, What to Let Go]. A periodic review prunes unused entries and refreshes expired ones.

The gate decides what becomes a candidate; the proposal decides what becomes memory. This complements the automatic hygiene in 4.4 rather than replacing it.

## 5. Read policy

- Inject only the memory this decision needs, not the full stored history. Retrieval from memory is a filtering problem: what is relevant now, what is too old or weak, what should be summarised first, and what stays stored but out of the prompt [SYSTEMS ch9].
- Score candidates by relevance, recency and importance with a **minimum similarity floor**, not a fixed top-k ([AGENTICAI ch7]; [ILLUSTRATED ch4]).
- Use a canonical **profile** per user as the source of truth, small and always injected, and treat semantic-search rows as projections of it. Ad hoc captures sit under transient keys as `proposed` until promoted. Keep extraction and application of updates as separate, testable steps (the companion notebook to [DEFGUIDE ch10]).
- Freshness: expiry per category; volatile data is fetched, not recalled; stored state must not stop the agent from re-verifying when the situation needs it [SYSTEMS ch9].
- **Inspectable trail:** log which memory IDs were injected into each call, with their scores and the reason they were selected. Otherwise a bad answer gets blamed on the model when an injected memory caused it [SYSTEMS ch9].
- **Memory search over a shared index is filtered retrieval.** When every user's memories sit in one vector index and a namespace or user filter picks out the caller's, apply retrieval-pipeline.md §3.2. Check that the scope filter runs inside the approximate search, not after its candidate cut-off, and keep a per-scope recall slice in the tests. A memory-only review runs this check too. It fails first for users with few items and for old items that newer ones crowd out.

**Growth worksheet.** For an assistant with many users over months, size the store before launch, mark every input "est." until the pilot measures it, and re-run the sheet with measured write rates:

| Quantity | Work it out as | Check |
|---|---|---|
| Items per user | writes per user per month × months kept, minus expiries and merges | Against the per-user cap (4.4 rule 5): what is merged or evicted when the cap is hit |
| Index rows | items per user × users (× embedded fields per item, if more than one) | Against the engine's limits per index and per partition |
| Index size | rows × (vector size + metadata) | Storage cost and memory needed to serve the index |
| Embedding cost per month | new or changed items per month × tokens per item × price per token | Changing the embedding model re-embeds every row |
| Recall by item age | the recall slice split by age (for example under 1, 1 to 6, over 6 months) and by items per user | A drop for old items or small scopes as the store grows |

## 6. Scope, privacy and deletion

- Namespace every record by organisation, user and memory type. Keep an organisation-shared segment that only admins can write [DEFGUIDE ch10].
- **Bind every store a client-supplied identifier can reach.** The memory namespace is one per-user store. Thread state and checkpoints are another, and they hold every turn verbatim; run histories, thread lists and caches are more. Bind each one to the authenticated user:
  - scope keys (organisation, user) come from the authenticated request; remove any shared default user and any environment-variable fallback for them, and fail closed when identity is missing;
  - a thread or run records its owner at creation, and every read, resume, list and delete checks that owner against the caller (section 8), because knowing a thread ID chosen by the client grants no access by itself;
  - name the framework hook that carries the authenticated identity into the run (an auth handler, request context or config injection) and the store's access-control hook, and verify both at the version pinned in the lock file; until checked they are inferred.

  Leak tests cover reading, resuming and listing another user's thread as well as their memory (evaluation.md §6).
- Scope by agent kind: personal agents default to isolated memory; team agents get shared, access-controlled spaces; organisation-wide agents run under retention, logging and audit rules; users can inspect and delete what is kept about them [BUILDAPPS ch13 §Shared Memory and Context Boundaries].
- Typical obligations under privacy law (for example GDPR or CCPA; which apply depends on the jurisdiction, so confirm with the privacy owner): collect only what is needed, pseudonymise before storing, let users view, edit and delete, and make "forget this" reach every copy, backups included within a documented window [AGENTICAI ch7]. Whether a duty applies, and whether anything already exposed must be reported, is the organisation's privacy or legal owner's decision. The design flags it; it doesn't decide it, and none of this is legal advice.
- **Employer-run assistants.** When an organisation runs the assistant for its staff, the employment lifecycle drives scope. A leaver's memory is deleted on a documented schedule. A transfer or role change deletes or rescopes entries tied to the old role, team or clients, and removes the person's write access to shared segments they no longer belong to. Who inside the organisation may read an employee's memory (the employee only, a manager, HR, IT support, auditors) is an explicit scope rule with an audit log, never an admin default. Which readers are allowed, the retention after leaving, and whether staff must be consulted are open questions for the privacy owner.
- A wall or barrier change (retrieval-pipeline.md §2.3) is a deletion for the newly barred user: purge their recalled memory, session state and checkpoints that hold content from that scope, and invalidate their scope-keyed caches.
- **Deletion map.** A deletion must reach every copy:

| Copy | Delete how |
|---|---|
| Fact/episode records | Hard delete or tombstone, then purge |
| Embedding index rows | Delete by `memory_id` |
| Derived summaries, consolidated profiles | Recompute without the item |
| Sanitised cards built from deleted source records (tickets, email) | Delete the card or regenerate it from the remaining records (retrieval-pipeline.md §2.6) |
| Graph nodes and edges extracted from deleted items | Delete by source link, which needs traceability from every triplet to its source (retrieval-pipeline.md §5.2) |
| Thread checkpoints and transcripts | Redact or expire per retention policy |
| Retrieval and answer caches | Invalidate by user scope |
| Logs, traces, eval datasets | Retention policy; redact on request. A hosted tracing service holds every conversation and recalled memory, so it is a copy here and a third party to name to the privacy owner |
| Backups | Erase within a documented window, or record the deletion and suppress the item on any restore |

- Storage location is also a UX choice. Client-side context is fast but lost across devices; server-side gives continuity at some privacy and latency cost; hybrids are common [BUILDAPPS ch3 §Context Retention and Continuity].

### 6.1 Cleaning up a running system

A review that finds memory breaking these rules in a live system has two jobs. Fixing the write path stops new damage; the entries the old design already stored stay until someone removes them. The fix includes the clean-up:
1. **Inventory** each store: categories, counts, ages and sources, plus the summaries, embeddings, checkpoints, caches and logs derived from them.
2. **Move system-of-record facts out**: delete the copied value and read it live (section 1).
3. **Purge** forbidden categories (secrets, raw personal, confidential or privileged content, anything the current scope rules bar) from every copy in the deletion map.
4. **Backfill** the governed fields on what stays: category, source `migrated` with confidence `inferred` until a person confirms it, TTL and sensitivity. An entry nobody can classify expires.
5. **Log** what was deleted (IDs, category, store, date and reason, never the content), then re-run the leak and deletion tests (evaluation.md §6).

Whether data that was already exposed must be reported to anyone is the privacy or legal owner's decision; the review flags it with the inventory attached.

## 7. Consolidation and forgetting

| Mechanism | What | Watch out for |
|---|---|---|
| Time-based pruning / expiry | Drop or archive by age, per category | Expiring something still true; set TTL per category |
| Compression | Summarise old episodes | Summaries of summaries over-compress [ILLUSTRATED ch4] |
| Usage-based decay | Strengthen items that keep being retrieved; fade the rest (MemoryBank's forgetting curve) [ILLUSTRATED ch4] | Popular-but-wrong items get stronger |
| Periodic merge | Merge many small facts into one consolidated profile; drop stale contradictions, newest wins [DEFGUIDE ch10] | **LLM rewrites degrade memory when repeated** [ENTERPRISE ch5 §Memory and Planning]; keep originals versioned and validate the merge |
| Explicit removal | User or admin deletes; outdated facts superseded | Must reach every copy (section 6) |

LLM-curated memory (A-MEM's linked, self-rewriting notes; MemoryBank's portraits) suits research and personal assistants, where recall quality matters more than predictability [ILLUSTRATED ch4]. In production, adopt it only with a measured gain, provenance on every record, and an edit/delete path. The cheap deterministic path is the default because cost, predictability and auditability all favour it.

## 8. Thread state, checkpoints, replay and concurrent writers

- Checkpoint thread state after every step, keyed by thread ID. That gives crash recovery, human-in-the-loop pauses and replay [DEFGUIDE ch10].
- Time travel (rewind to an earlier checkpoint, edit, fork) is useful for debugging and audit. It **rewinds the thread, not the long-term store**, so decide explicitly whether durable memory is versioned or rolled back on replay [DEFGUIDE ch10].
- Treat checkpoint payloads and stored memory as untrusted text when they are read back.
- **Thread ownership.** The checkpointer keys state by thread ID, and that ID usually comes from the client. Store the owner (organisation and user from the authenticated request) with the thread when it is created, and check it before every read, resume, fork, list and delete; a list returns only the caller's threads. Enforcing this in the runtime belongs to agent-harness-designer; this skill checks that the rule exists and that a leak test covers it (evaluation.md §6).
- **Concurrent writers.** Two writers can hold the same thread or record: a retry and a resume, two replicas, a redelivered event, two turns arriving together, one user in two tabs or on two devices writing user-scoped memory. Make writes conditional. Create only if the key doesn't exist; update only if the stored version equals the version you read, then increment it. When the condition fails, reload and decide again. Never blind-overwrite. The alternative is one writer by construction: every event for a thread goes through a single consumer (partitioning by thread or case belongs to agent-architect).
- **When the store has no conditional write** (some key-value and memory stores accept only a plain put), pick one of two: route every write for a scope through one writer (a per-user queue), or accept last-writer-wins for low-value free-text items and say so. Size the finding by how likely a collision is. New items with fresh unique IDs never collide, so only two simultaneous updates of the same existing item can lose one. That is usually minor for a free-text preference and serious for state that other people act on.
- **Append-only logs** (turns, episodes, ledger entries) need IDs that can't collide: a conditional create with retry, an atomic counter, or a time-ordered unique ID (UUIDv7, ULID). Reading the last ID and adding one is a race. Two concurrent appends get the same ID and the second silently replaces the first.

```python
class StaleWrite(Exception): ...

def save(store, key, state, read_version):            # read_version is 0 when the key was absent
    ok = store.put_if(key, {**state, "version": read_version + 1},
                      expect_version=read_version)      # stored version must still equal what we read
    if not ok:
        raise StaleWrite(key)                           # caller reloads and decides again
```

- **Read contract.** Specify how the thread store returns a thread: explicit sort order (chronological for replay), page size and continuation, and the empty-thread case. Test it with a three-turn fixture: the turns come back 1, 2, 3, and a new thread returns an empty list, not an error. A flipped sort flag silently reverses the conversation and breaks any logic that reads "the last turn".

## 9. Multi-agent memory

| Topology | Good | Bad |
|---|---|---|
| Per-agent local | Clean contexts | Agents drift apart; duplicated knowledge |
| Shared global store | One source of truth | Every agent's context fills with the others' noise; needs concurrency control (conditional writes, section 8) |
| **Hybrid** (local working state + shared durable facts and coordination artifacts) | What most production systems use [DEFGUIDE ch10] | Needs clear ownership of shared writes |

Pass a sub-agent the current task brief, not the parent's history. Choose its persistence explicitly: per-invocation (remembers nothing between calls), per-thread (keeps its own history within the thread) or stateless (also loses interrupts and crash recovery) [DEFGUIDE ch10]. Messages between agents are shared context too, and need the same budgeting [ILLUSTRATED ch4].

## 10. Agent-written notes and memory tools

- Giving the agent a write tool (an evidence log, a notes file, a memory directory) works for long tasks that span context resets, and for tasks that repeat [BUILDAGENTIC ch4 §Experiment: The Extended Mind Thesis and Agentic Memory]. Every note is an unreviewed model output, so add validation, provenance, size caps, expiry, and an edit/delete path.
- A file-based memory tool also needs path-traversal checks and sensitive-data stripping, which provider memory tools leave to the application (provider-notes.md).
- **Notes that other agents will read.** Ng's coding agents save workaround notes when documentation falls short, and his plan is for agents to share feedback on documentation with other agents, with an opt-out ([NG Context for Coding Agents, 2026-03-09]; [NG Let's Help Agents Share Their Work, 2026-03-16]). The control that follows is derived, not Ng's claim: a note one agent writes and another reads as context is an injection channel. Review shared notes before other agents read them, store each with its author, source and status, and render it fenced and labelled like any other source (context-assembly.md §9).
- **Memory tools take their scope from the request, not the model.** When memory is exposed as tools (a memory server over a tool protocol, a memory API the agent calls), the server binds the scope keys (tenant, user, session) and the author role from the authenticated request context. They are not tool parameters. A model-chosen session key is a cross-session read path, and a model-chosen role lets an injected instruction write a forged user turn that later reads back as the user's own words. The model writes only as itself (an assistant note or a `proposed` fact); the application writes user turns from the actual user message. Test it: call the read tool with another session's ID and expect a refusal. Tool interface rules belong to agent-tool-designer.

## 11. Poisoning (summary; threat model → agent-threat-modeler)

Untrusted content gets written to memory and comes back later as trusted context. Agents that write and retrieve memory aggressively are easier to exploit, and prompt-injection defences don't fully cover this path [DEFGUIDE ch10]. The minimum controls belong in any memory design: provenance on every record, no automatic promotion from tool, web or document text, validation before write, monitoring for unusual write volume or content, and treating read-back memory as data, not instructions: fenced and labelled with the provenance it was stored with (context-assembly.md §9). Hand attack trees, red-team cases and cross-session exploitation to agent-threat-modeler.
