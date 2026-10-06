# Provider features and external findings (as of 2026-10)

These facts go stale fast. Before quoting a number to a user, re-check the linked page. Everything here is external to the books.

## Prompt caching

**Anthropic** ([prompt caching](https://platform.claude.com/docs/en/build-with-claude/prompt-caching), checked 2026-10)
- The cached prefix is ordered tools → system → messages. Changing tool definitions invalidates everything. Changing `tool_choice`, adding or removing images, or changing thinking or effort settings invalidates the messages cache. Toggling web search or citations, or switching speed mode, invalidates system and messages.
- Up to 4 explicit `cache_control` breakpoints. There is also automatic caching: a top-level `cache_control` moves the breakpoint forward to the last cacheable block as the conversation grows.
- Lookback: the system checks at most 20 block positions per breakpoint for an earlier cache write. In very long turns, place an extra breakpoint.
- Minimum cacheable length: 512 to 4,096 tokens depending on the model. Check the page's table for your model.
- Price: cache writes cost 1.25x base input for the 5-minute TTL (the default) and 2x for the 1-hour TTL. Cache reads cost 0.1x base input for most models, and less on some newer ones.
- Never put the breakpoint on a block that changes every request (timestamp, the incoming message). You pay a cache write every time and never get a read.

**OpenAI** ([prompt caching](https://developers.openai.com/api/docs/guides/prompt-caching), checked 2026-10)
- Caching is automatic for prompts of 1,024 or more tokens. Newer models (GPT-5.6+) keep a cache for about 30 minutes after the last write or reuse and support explicit breakpoints (`prompt_cache_breakpoint`). Earlier models use implicit breakpoints with in-memory retention (minutes, up to an hour) or an extended 24h retention option.
- `prompt_cache_key` helps routing on older models and gives separate accounting on newer ones. It never guarantees a hit.
- Cached reads cost about 0.1x input on most current models.
- Their advice matches the layout rule: stable instructions and shared reference material first; timestamps and user-specific content after.

Other providers have similar prefix caching with different minimums and TTLs. Check the current docs; the layout rule is the same everywhere.

## Context management APIs (Anthropic, checked 2026-10)

- [Context editing](https://platform.claude.com/docs/en/build-with-claude/context-editing): **tool-result clearing** removes the oldest tool results once input passes a trigger (default 100,000 input tokens), keeps the most recent 3 tool uses by default, and supports `clear_at_least` (skip clearing unless enough tokens are freed to justify breaking the cache), `exclude_tools`, and an option to clear tool inputs too. **Thinking-block clearing** is separate. Keeping thinking blocks preserves the cache; clearing them invalidates it from that point. Recent large models keep prior thinking by default.
- The same page names **server-side compaction** as the primary strategy for long conversations, with context editing for finer control.
- [Memory tool](https://platform.claude.com/docs/en/agents-and-tools/tool-use/memory-tool): a client-side file directory that the model checks before a task and writes to as it works. The application must handle path-traversal protection, size caps, expiry and stripping sensitive data. The page describes a multi-session pattern built on a progress log.

Dated book claim: one book says reasoning models' thinking tokens are discarded between calls, which breaks caching [BUILDAGENTIC ch7]. That was specific to the models and APIs it tested. Check current provider behaviour.

## Retrieval findings

- [Contextual Retrieval](https://www.anthropic.com/engineering/contextual-retrieval) (Anthropic, 2024-09): a small model writes 50-100 tokens situating each chunk in its document, prepended before both embedding and BM25 indexing. The top-20 retrieval failure rate fell from 5.7% to 3.7% with contextual embeddings, to 2.9% with contextual BM25 added, and to 1.9% with a reranker scoring the top 150 and keeping 20. With prompt caching, the one-off cost was about $1.02 per million document tokens. For knowledge bases under about 200,000 tokens, the post suggests skipping retrieval and caching the whole corpus in the prompt.
- [Elastic RRF reference](https://www.elastic.co/docs/reference/elasticsearch/rest-apis/reciprocal-rank-fusion): reciprocal rank fusion ships as a built-in hybrid query type, with k defaulting to 60.
- [Sufficient Context](https://arxiv.org/abs/2411.06037) (2024-11): separates "the context contains enough to answer" from "the context is relevant". Large models answered well with sufficient context but often answered wrongly instead of abstaining without it. Abstaining on a sufficiency signal raised the share of correct answers among those given by 2-10%.
- [Context Rot](https://www.trychroma.com/research/context-rot) (Chroma, 2025-07): 18 models; performance varies significantly with input length even on simple tasks, distractors hurt more at longer lengths, and a coherent haystack hurt more than a shuffled one.
- [Multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system) (Anthropic, 2025-06): start with short, broad queries and then narrow. Effort rules: 1 agent with 3-10 tool calls for fact-finding, 2-4 sub-agents for comparisons, 10+ for complex research. Agents used about 4x the tokens of chat and the multi-agent system about 15x. Reported failures included endless searching for nonexistent sources and preferring SEO content farms to authoritative sources.

## Context engineering guidance

- [Effective context engineering for AI agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents) (Anthropic, 2025-09): treat context as a finite attention budget with diminishing returns; keep lightweight identifiers in context and load content just in time. Three long-horizon techniques: compaction, structured note-taking outside the window, and sub-agents that return condensed results of roughly 1,000-2,000 tokens.
- [Context Engineering for AI Agents: Lessons from Building Manus](https://manus.im/blog/Context-Engineering-for-AI-Agents-Lessons-from-Building-Manus) (2025-07): cache hit rate is the most important production metric; an input-to-output ratio of about 100:1; no timestamps in the prefix; append-only context with deterministic serialisation; mask tools instead of removing them mid-run; use the file system as restorable external memory; keep failed actions in context.

## Memory evaluation

- [LongMemEval](https://arxiv.org/abs/2410.10813) (ICLR 2025): 500 questions across five abilities (information extraction, multi-session reasoning, temporal reasoning, knowledge updates, abstention). The authors report about a 30% accuracy drop for commercial assistants and long-context models over sustained interactions, and frame memory as indexing, retrieval and reading, with fixes at each stage.
