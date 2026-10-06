# Tool count, selection strategies and the tool-choice eval

Depth for steps 10 and 12. Citation keys are listed under Sources in SKILL.md.

## §1 How many tools

The books give ceilings without measurements: about six [AGENTICAI ch5], start below ten [ILLUSTRATED ch5], and a drop-off at 12-20 active tools that the author expects to move [MCP ch5]. Claude's tool docs (2026-10) put the degradation point at 30-50 available tools for their models. The one controlled measurement in the source library used 15 distinct tools, 80 questions and tool order shuffled between runs; larger models beat GPT-4.1-Nano and a 3-billion-parameter model [BUILDAGENTIC ch5]. The companion code's numbers: frontier models picked the expected tool 99.2-99.9% of the time when they called one, GPT-4.1-Nano 93.9%, the 3B model 86.1%. Runs where the model called no tool were excluded, so these are selection accuracies, not task success rates.

**Conclusion:** the ceiling depends on the model, on how much descriptions overlap and on definition size, not on a universal number. Default to loading every tool up to roughly 15-20 distinct tools or about 10k tokens of definitions, then let the tool-choice eval decide.

**Context cost is the other half.** Every definition is sent on every call [MCP ch2]. Anthropic measured a five-server setup with 58 tools at about 55,000 tokens before the conversation started (Advanced tool use, 2025-11). Measure your own: count tokens for the full `tools` array once (Claude's API has a token-counting endpoint; OpenAI publishes its tokenizer) and multiply by calls per task. Without a tokenizer, divide the character count of the serialised array by 4 for English text and JSON, and label the result an estimate. Claude's API also wraps the definitions in a tool-use system prompt of its own, so the real cost is somewhat higher.

**Prompt caching.** Tool definitions sit near the start of the prompt, so any change there invalidates the cache for everything after it [BUILDAGENTIC ch1]. Return tools in a deterministic order (the MCP spec asks servers to), avoid rebuilding the list with different contents every turn, and prefer mechanisms that append discovered tools later in the conversation (deferred loading) over ones that edit the prefix.

## §2 Strategy ladder

Move down only when the eval or the token bill shows the current rung failing.

1. **Load all, curated.** Merge overlapping tools, tighten descriptions, remove tools nobody calls (check the logs). This fixes most "picks the wrong tool" reports.
2. **Static scoping.** Show the subset that fits the caller's role, scopes or the workflow state (e.g. refund tools only after an order is identified). It is deterministic and cheap, and it doubles as a permission control. Risk: hiding a tool a later step needs. Scoping by workflow state needs control of the request (your own loop, or a host or client you run); an MCP server can scope only by the caller's authorization.
3. **Tool search with deferred loading.** Start each turn with a search tool plus the few most-used tools. Other definitions enter context only when a search returns them. The MCP book builds this on the client [MCP ch4], and Claude offers it as a server-side tool. In Anthropic's tests it cut definition tokens by about 85% and raised accuracy on an MCP evaluation from 49% to 74% for one model and from 79.5% to 88.1% for another (Advanced tool use, 2025-11). It costs one or two extra calls per tool-using turn. The system prompt must name the tool categories and tell the model to search before concluding a tool does not exist.
4. **Semantic pre-filtering** (embed tool descriptions, retrieve top-k for the user's message). It is common in the books [BUILDAPPS ch5], [ILLUSTRATED ch5], [DLLMA ch10], and BUILDAPPS's own comparison flags its weakness: semantic collisions between similar tools [BUILDAPPS ch5]. Retrieval keyed on the first message also misses a tool needed at step three. Prefer tool search (the model can search again mid-task). If you pre-filter anyway, measure retriever recall separately from selection accuracy.
5. **Hierarchical selection.** Pick a group, then a tool in it. It is more accurate on large sets of similar tools, slower because of the extra sequential calls, and the groups need maintenance [BUILDAPPS ch5].
6. **Code mode** (programmatic tool calling, CodeAct). The model writes a short program that calls tools as functions in a sandbox, and only the final result returns to the context. Use it for loops, filtering, aggregation and fan-out: eight cities times two tools made sixteen calls with zero model round trips [DEFGUIDE ch6]. Anthropic reported a 37% token cut on complex research tasks (Advanced tool use, 2025-11), and the CodeAct paper up to 20% higher success than JSON actions across 17 models (2024). It needs all of these: a deny-by-default interpreter, no credentials or network inside the sandbox, every external call routed back through the host so it can apply an allowlist, budget or approval [DEFGUIDE ch6], [MCP ch4]. An injection that reaches the model can now become code, so hand this design to agent-threat-modeler for review. Keep "orchestrate a fixed, vetted tool set in code" apart from "agent writes new tools at runtime", which loses repeatability [BUILDAPPS ch4].
7. **Subagents as tools.** Wrap a group of tools in a specialist agent exposed to the orchestrator as one tool [ILLUSTRATED ch8]. It is justified when groups differ in data access, permissions or success criteria. Try rungs 1-5 inside one agent first, because splitting adds coordination overhead [BUILDAPPS ch8]. The topology decision goes to agent-architect.

**Multi-server hosts.** Tool-choice accuracy falls as MCP servers are added, through name collisions and overlapping descriptions. Measure before and after adding a server, and watch for wrong tools, hallucinated arguments, long loops and ping-ponging between two tools [MCP ch2].

**Reasoning effort.** Reasoning models are often said to choose tools better [ILLUSTRATED ch5]. A follow-up run in the Building Agentic AI companion code, on the same 15-tool setup, found no gain from higher reasoning effort for single-step selection among distinct tools. For example, gpt-oss-20b scored 94.5% at high effort against 97.5% at medium. Do not buy reasoning tokens to fix selection; fix descriptions and the tool set, and measure per task.

**Position bias** exists but was small for frontier models choosing among distinct tools: tools in the first three positions were picked 20.35% of the time against 20.13% expected [BUILDAGENTIC ch5]. Shuffle order in evals; keep it fixed in production for caching.

## §3 Tool-choice modes

| Mode | Use for | Note |
|---|---|---|
| auto (default) | Most turns | The model may answer without a tool, ask a question or call several |
| required / any | A turn where some tool must be called | Removes the option to ask a clarifying question |
| a named tool | A step that must call exactly this tool | Strongest; not available on every model or with every thinking setting (current facts) |
| none | Turns that must not act (summarise, confirm with the user) | Tools stay defined, so the cache stays warm |

Forcing trades flexibility for predictability [BUILDAPPS ch4]. Force only truly mandatory steps, and enforce them in code where forcing is unsupported.

## §4 The tool-choice eval

This is the minimum every tool design ships with. The full program (judges, statistics, CI) belongs to agent-eval-designer.

**Dataset.**
- 3-5 natural prompts per tool, worded the way users write, not copied from the description.
- 3-5 prompts for each confusable pair (tools with overlapping purpose, or found confused in logs). Most selection errors show up in these pairs.
- Multi-step cases where the right first call matters (lookup before action).
- **Negative cases, about 20-30% of the set:** the right move is to ask for missing details, call no tool (answerable from context), or decline (out of scope or not permitted). A set of only answerable, fully specified prompts flatters the agent [BUILDAGENTIC ch5].
- Expected outcome per case: tool name, or one of `ask | none | decline`, plus key argument values where they matter.
- A held-out 20-30% that you do not look at while tuning descriptions, so the descriptions do not overfit (Writing tools for agents, 2025-09).

**Runs.** Use the real definitions and system prompt, at production settings. Run each case at least 3 times with tool order shuffled each run [BUILDAGENTIC ch5]. Use stub tool handlers that return realistic results, so multi-step cases can proceed.

**Metrics.**
- Selection accuracy, overall and per tool.
- Per-tool precision (when chosen, was it right?) and recall (when needed, was it chosen?). Low precision on A plus low recall on B is a confused pair [BUILDAGENTIC ch5].
- A confusion matrix of expected vs chosen, including ask, none and decline.
- Argument validity rate (passes schema and business validation) and argument accuracy on key fields.
- Calls per task, definition tokens per call, total tokens and latency per task (Writing tools for agents, 2025-09).
- No-call rate and clarifying-question rate, reported separately rather than silently dropped.

**Re-run triggers.** Adding or removing a tool or server [MCP ch2], changing any description, name or schema, changing the model or its settings [MCP ch7], changing the system prompt's tool instructions.

Minimal harness sketch (provider-agnostic; adapt the call):

```python
import random, collections

def run_eval(cases, tools, call_model, runs=3):
    # cases: [{"prompt": str, "expect": "tool_name" | "ask" | "none" | "decline"}]
    # call_model(prompt, tools) -> "tool_name" | "ask" | "none" | "decline"  (classify the first turn)
    conf = collections.Counter()
    for case in cases:
        for _ in range(runs):
            shuffled = random.sample(tools, len(tools))   # shuffle order every run
            conf[(case["expect"], call_model(case["prompt"], shuffled))] += 1
    labels = {e for e, _ in conf} | {g for _, g in conf}
    report = {}
    for t in labels:
        tp = conf[(t, t)]
        chosen = sum(v for (e, g), v in conf.items() if g == t)
        needed = sum(v for (e, g), v in conf.items() if e == t)
        report[t] = {"precision": tp / chosen if chosen else None,
                     "recall": tp / needed if needed else None}
    acc = sum(v for (e, g), v in conf.items() if e == g) / sum(conf.values())
    return acc, report, conf
```

Read the confusion counts, not just the accuracy. A 95% overall score can hide one tool at 50% recall.
