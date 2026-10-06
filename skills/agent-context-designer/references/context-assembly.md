# Context assembly reference

Depth for Procedure steps 6-7. Citation keys are expanded in SKILL.md under Sources.

Contents: 1 Per-call inventory · 2 Token budget · 3 Layout for caching · 4 History control and compaction · 5 Tool results and tool definitions · 6 Sub-agent isolation · 7 Long-running tasks · 8 Context observability

Context is rebuilt at every step, not accumulated by accident [BUILDAPPS ch5 §Context Engineering]. The operations: **track** everything that might matter later; **select** what this step needs; **compress**; **order**; **isolate** sub-tasks; **budget** each part; **lay out for the cache** ([ILLUSTRATED ch4]; [ILLUSTRATED ch10 §Context Management]; [SYSTEMS ch12 §12.9 Token Budgeting]). The target is the smallest context that supports a grounded answer, not the size of the window [SYSTEMS ch12 §12.9 Token Budgeting].

## 1. Per-call inventory

List every model call in one request or run (planner, executor, sub-agent, summariser/compactor, judge, router). For each one, record:

| Call | Decision it makes | Model / window | Static prefix (tokens) | Dynamic parts | Measured p50/p95 input | Output allowance | Calls per request |
|---|---|---|---|---|---|---|---|

Take the numbers from a real trace with the provider's tokenizer or its usage fields. A characters-divided-by-4 estimate is acceptable only when labelled as an estimate. The multiplier matters: when every step of a workflow repeats a 5,000-token shared prefix, one user query can cost 30,000 prefix tokens before any generation [DEFGUIDE ch11].

**Cost per call, in input-price units**, for comparing designs before you have a bill:
```
input_cost ≈ uncached_tokens × 1.0  +  cache_read_tokens × read_mult  +  cache_write_tokens × write_mult
cost_per_task ≈ Σ over calls (input_cost × input_price + output_tokens × output_price)
```
Take `read_mult` and `write_mult` from the provider (provider-notes.md; typically 0.1 and 1.25). With an end-of-prompt breakpoint, the uncached tail is what gets written. Then confirm the estimate by replaying logged sessions through the new assembler.

**When most inputs are guesses**, give a low/high range instead of one number, state which assumption drives the spread, and list what to measure first:
1. model calls per user turn or per task, by call type;
2. input tokens per call, split by bucket;
3. cache-read share of input tokens;
4. output tokens per call, including thinking;
5. turns per session or steps per task.

Compute a low and a high case (for example cache-read share 40% against 80%, and turns per session at p50 against p90), then replace the range with a measurement from 20-50 logged sessions replayed through the new assembler.

**Short form for auxiliary calls.** Give the main call(s) the full budget table and layout. Routers, compactors, memory extractors and judges need one line each: model, what they see, input cap, output cap, how often they run.

## 2. Token budget

### 2.1 Buckets
Seven buckets, each with a ceiling the orchestrator enforces instead of letting every component append freely [SYSTEMS ch12 §12.9 Token Budgeting]: system and developer instructions (plus tool definitions), user request, conversation summary, retrieved evidence, tool results, memory, output allowance.

### 2.2 Method
1. **Reserve the output allowance** first: max output tokens, plus thinking tokens if the model uses them.
2. **Measure the static prefix** (tool definitions + system + procedural rules). If it is large, look at the tool list first (section 5).
3. **Evidence** = number of chunks passed (3-5) × measured chunk size + per-item header (IDs, title, date).
4. **Memory** = profile block cap (a few hundred tokens is typical for preferences) + recalled items cap (top few above the floor).
5. **History** = recent turns verbatim up to a cap, newest first, kept in chronological order. Everything older goes into the summary bucket.
6. **Tool results** = per-result cap, projecting only the fields the next step needs. Store the full result outside the window with a handle (ID, path, URL) so it can be reloaded. This bucket covers results from the current turn's tool loop. Results from earlier turns sit in the history bucket and are reduced to one-line notes with handles at the next compaction.
7. **Check the sum**: everything above + output allowance < window, with headroom. Then ask whether a smaller total would do as well. Long inputs degrade quality even when they fit (provider-notes.md, Context Rot).
8. **Set a target p95, not just a ceiling.** With a large window the ceiling check passes trivially. Start the target at the measured prefix plus the buckets this call actually needs, and lower it if the length-degradation curve (evaluation.md §7) shows quality dropping earlier. The window is a hard limit, not a goal.

### 2.3 Overflow rule per bucket
| Bucket over budget | Do this | Not this |
|---|---|---|
| Evidence | Rerank harder, raise the floor, compress to the relevant passage, or ask a narrower question [SYSTEMS ch12 §12.9 Token Budgeting] | Truncate mid-chunk; silently drop the best chunk |
| History | Compact the middle (section 4) | Drop the first turn |
| Tool results | Project fields; clear old results in a batch | Paste the full JSON |
| Memory | Keep the profile, cut recalled items by score | Inject every match |
| Prefix | Trim tools, move rarely used instructions behind retrieval | Edit it every turn |

### 2.4 Budget sketch
```python
BUDGET = {"summary": 1500, "recent": 6000, "memory": 600, "evidence": 3000, "tool_results": 4000}

def fit(items, cap, count):                    # items already in priority order
    out, used = [], 0
    for it in items:
        n = count(it)
        if used + n > cap: break
        out.append(it); used += n
    return out

def assemble(prefix, user_block, summary, turns, task_state, recalled, evidence, count):
    recent = fit(turns[::-1], BUDGET["recent"], count)[::-1]   # newest win, chronology kept
    return [prefix,                       # shared: tools + system + rules, identical for every user
            user_block,                   # per-user stable: identity, profile, original task statement
            summary, *recent,             # append-only history (summary changes only on compaction)
            task_state,                   # volatile: current-task line + attempt ledger, rendered by code
            *fit(recalled, BUDGET["memory"], count),
            *fit(evidence, BUDGET["evidence"], count)]  # this step's material last
```
The numbers are placeholders. Derive yours from the method in 2.2 and the measured prefix.

## 3. Layout for caching

Providers reuse computation for a prompt prefix they have already seen. That works only if the cached part is **identical down to the token** and new input is **appended at the end** [ILLUSTRATED ch10 §Context Management]. An agent loop fits this naturally, because each step is the previous context plus one action and one observation, so the whole earlier trajectory can be served from cache.

```
┌ shared static    tool definitions · system prompt · procedural rules · hard constraints     identical for every user; fixed for the run
├ per-user stable  identity, role, tenant · profile · original task statement · session summary · progress record*
│                                                                                              changes at session start and on compaction
├ append-only      conversation turns · tool calls · projected tool results                   only grows
└ volatile tail    current-task line · attempt ledger · recalled memory · evidence · date/time · latest input
                                                                                               rebuilt every turn
* only if it changes at milestones; a record that changes every step goes in the tail
```

- **Order rule: shared before per-user, rarely changing before often changing.** Per-user content belongs right after the shared prefix. The shared prefix is then cached across all users, and the per-user block across that user's turns. The rule against per-user text ahead of shared content is about user data inside or before the shared prefix; a per-user block after it is the intended layout.
- After compaction only the lower sections change, and the shared prefix stays cached [ILLUSTRATED ch10 §Context Management].
- **What a change costs.** A change at one position invalidates every token after it. On the next call, one change costs roughly (tokens after the change) × (write_mult − read_mult). A change to the per-user stable block therefore re-bills about the whole history once. That is acceptable when it happens no more often than compaction, which rewrites history anyway. Anything that changes every turn belongs in the volatile tail. Check with the cache-read share per call.
- Put per-step injected material at the **tail**. If you drop it next turn, only the tail's cache is lost. For evidence that code injects each turn: on the next turn, replace the chunk text with a one-line citation note (doc IDs) in history and retrieve fresh. Keeping every turn's chunks makes history grow fast; dropping them without a note loses what earlier answers were based on.

**Cache breakers to look for in a review:**

| Breaker | Fix |
|---|---|
| Timestamp or date in the system prompt | Move to the tail, or use day granularity |
| Non-deterministic serialisation (dict or JSON key order, set ordering) | Sort keys; stable formatting |
| Editing an old message (typo fixes, redaction mid-run) | Append corrections instead |
| Adding or removing tool definitions mid-run | Fixed toolset per run; mask tools instead of removing them, or accept the miss when tool search saves more than it costs |
| Per-user or per-tenant text before shared instructions | Shared first, then user-specific |
| Clearing old tool results one at a time | Clear in batches, and only when enough tokens are freed |
| Changing model settings or attachments mid-run | Keep them fixed within a run (provider-specific; see provider-notes.md) |

Track **cache-read tokens / total input tokens** per call. Manus calls cache hit rate the single most important production metric for an agent and reports an input-to-output token ratio of about 100:1 (external; provider-notes.md).

## 4. History control and compaction

| Technique | Use when | Watch out for | Source |
|---|---|---|---|
| Rolling window / trimming | Short sessions; recent turns carry the signal | The first message often holds the goal; an agent that loses it starts inferring the task from follow-ups [ENTERPRISE ch5 §Memory and Planning] | [BUILDAPPS ch6] |
| **Compaction:** keep the prefix and the newest turns verbatim, summarise the middle | Long sessions and long agent runs (**default**) | Fidelity loss; lost constraints | [DEFGUIDE ch7]; [DEFGUIDE ch10] |
| Tool-result clearing | Tool outputs dominate the window | Each clearing invalidates the cache from that point | provider-notes.md |
| Keyword (BM25) recall over old history | Users refer back to exact names, IDs, codes | Paraphrased references | [BUILDAPPS ch6] |
| Semantic recall over past turns (reserved slice of the window) | Long-lived assistants where old exchanges become relevant again | Short sessions | [BUILDAPPS ch6] |
| Virtual context paging | Very long-lived personal assistants | Complexity; a summary plus a fact store usually suffices | [DLLMA ch12 §RAG for Memory Management] |

**Compaction spec. Write it, don't improvise it:**
- **Trigger.** For chat, start compacting when the recent-turns bucket passes its ceiling. A starting point (this skill's default, not a book finding) is about 6-8k tokens or 15-20 turns, compacting the oldest turns down to about half the ceiling so it runs every few turns rather than every turn. For long agent runs, use a threshold well below the window (provider tool-result clearing defaults to around 100k input tokens). In both cases, move the trigger once you have a length-degradation curve (evaluation.md §7), and prefer natural boundaries such as a finished sub-task or a task switch.
- **Kept verbatim:** the static prefix, the original task statement, the current-task line and attempt ledger (next subsection), the last N turns, and the most recent tool results.
- **Summary prompt as a must-survive checklist**, specific to the domain [ILLUSTRATED ch10 §Context Management]:
  - goal and acceptance criteria; constraints and approval rules
  - user preferences and decisions made (with who decided)
  - progress: steps done, steps remaining, current step
  - identifiers: file paths, record IDs, URLs, names, versions
  - errors hit and approaches already tried, so the agent doesn't repeat them
  - open questions waiting on the user
  - for code agents: environment, code-style preferences, when to run tests and commit
- **Cap** the summary (one book's example: at most eight bullets that preserve preferences and decisions [DEFGUIDE ch10]).
- **Keep the raw transcript** outside the window. Re-summarise from raw where possible, because summaries of summaries over-compress [ILLUSTRATED ch4] and repeated LLM rewriting degrades memory [ENTERPRISE ch5 §Memory and Planning].
- **Test it:** run long scripted sessions, compact, then check that every must-survive item is still used correctly.

### Task state in chat: current-task line and attempt ledger

Chat agents switch problems mid-conversation and re-suggest fixes the user already tried. Code maintains this task state as structured thread state. It is not LLM-written memory, and it never lives only inside the compaction summary.

- **Original task statement.** Keep it where it is (the first turn in history, mirrored in the per-user stable block). Compaction never drops it.
- **Current-task line** (≤50 tokens, volatile tail). When the user switches problems, code or a validated structured tool call (`set_current_task(summary)`) replaces the line and appends a short task-switch marker to history. If the new problem is unrelated, offer a new thread; one thread per problem keeps ledgers and summaries clean.
- **Attempt ledger** (≤300 tokens, volatile tail). One line per attempt: `step | how | outcome (worked / failed + error / skipped) | source (tool-call ID or user turn)`. Code appends entries from tool calls and their results. For steps the user performed, the model calls a structured `record_attempt(step, outcome)` tool that code validates (known step, outcome from an enum, length cap). On a task switch, close the ledger with a one-line outcome.
- **How this fits the batch-only rule.** That rule covers *durable* memory decided by an LLM. The ledger is thread state: per session, structured, validated by code, and discarded or summarised when the session ends. At session end the batch extractor may turn a closed ledger into one episodic note.
- **Compaction.** Keep the ledger and the current-task line verbatim; never summarise them. If the ledger outgrows its cap, collapse finished or abandoned branches to one line each.
- **Ledger and progress record.** Both follow the same pattern. The long-run progress record (section 7) tracks the plan: what comes next. The ledger tracks what was tried: what not to repeat. A long run can have both.

**Constraints never live only in compactable context.** In one reported incident, an agent told to confirm before acting deleted over two hundred emails, most likely because compaction dropped the "wait for approval" instruction [ENTERPRISE ch7]. Put rules in the never-compacted prefix so the model follows them, and enforce the costly ones in code (approval gates, tool permissions), where compaction can't remove them.

## 5. Tool results and tool definitions

- **Results:** pass only the fields the next step needs [SYSTEMS ch12 §12.8 Prompt and Context Optimization]. Keep lightweight identifiers in context and load content just in time (Anthropic's context-engineering guidance, external). Manus keeps failed actions and errors in context so the model doesn't repeat them (external).
- **Definitions** are sent on every call. Options [MCP ch4 §Optimizing Your Tool List with Context Engineering]:
  - a small fixed toolset per agent or per run (best for caching);
  - a tool-search tool that adds definitions on demand (good for large catalogues, but it changes the most cache-sensitive block);
  - tools exposed as code stubs that the model calls from a sandboxed script, which keeps intermediate results out of the window (the chapter cites a 98.7% token reduction reported by Anthropic).
- Masking tools versus removing them is a real conflict between sources. Choose by measuring cache hit rate against tool-selection accuracy. Tool interface design goes to agent-tool-designer.

## 6. Sub-agent isolation

- A sub-agent that reads twenty documents and returns a paragraph keeps those documents out of the orchestrator's window ([ILLUSTRATED ch4]; [DEFGUIDE ch10]).
- **Brief in:** task, constraints, the IDs and handles it needs, output format, budget. **Condensed result out:** findings with source IDs, roughly 1,000-2,000 tokens (Anthropic's guidance, external). Don't pass the parent history.
- Decide the sub-agent's persistence mode (memory-design.md section 9).
- Avoid isolation when the sub-task truly needs the parent's full history. Write a better brief instead.

## 7. Long-running tasks (beyond one window or one session)

Recipe, in order of adoption:
1. Cache-friendly layout and a pinned task statement (sections 3 and 4).
2. A **progress record** (plan or to-do file) that the agent updates and that is always injected: in the per-user stable block if it changes only at milestones, in the volatile tail if it changes every step (section 3). Writing notes to a file outside the window is one of Anthropic's three long-horizon techniques (external), and [ILLUSTRATED ch4] suggests tracking plan artifacts the same way. Chat agents use the attempt ledger (section 4) for the same purpose.
3. Compaction with a tested must-survive list.
4. Tool-result clearing in batches, keeping handles to reload.
5. Sub-agents for heavy reading or search.
6. Just-in-time loading by identifier (paths, URLs, record IDs) instead of preloading.
7. Checkpoints after each step for resume, plus a multi-session pattern: at session start, read the progress log and recent changes; at session end, update the log (provider-notes.md, memory tool).
8. Hard constraints enforced in code throughout.

Provisioning: fetch facts the run will certainly need (IDs, tenant, entitlements) before it starts [ENTERPRISE ch5 §Context]. Reserve "slots" for items business rules say must always be present [MESH ch5 §Agent Context Engineering].

## 8. Context observability

Log per model call:
- input tokens per bucket; output tokens; cache-read and cache-write tokens;
- IDs and scores of injected evidence and memory items, and why each was selected [SYSTEMS ch9];
- compaction and clearing events: when, tokens before and after, what was dropped;
- prompt template version and tool-set hash, so you can explain a sudden cache-hit drop.

These let you answer "why did the agent say that?" and "why did cost double?" from the trace instead of guessing. Dashboards and alerting go to agent-ops-reviewer.
