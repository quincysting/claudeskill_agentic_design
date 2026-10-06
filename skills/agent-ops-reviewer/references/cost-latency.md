# Cost and latency: model, levers, deployment

Load this for steps 12 to 15 of the procedure: estimating cost per request, choosing levers, planning latency and deciding where each agent runs. Prices and provider features change monthly; everything marked "as of 2026-10" must be rechecked against the provider's page before it goes into a decision.

## 1. The two sums

```
cost per request = Σ steps  P(step runs) × (1 − memo hit) × calls per run
                            × (input tok × input price × cache factor + output tok × output price)
                   × (1 + retry and repair overhead)  + non-model cost per request
cache factor     = fresh share + cached share × read multiplier + written share × write multiplier
latency          = Σ critical path (prefill + decode per model call, retrieval, tool, orchestration time)
```

An agent's cost belongs to the workflow, not the model. One request may end after one call; another plans, retrieves, calls tools, reflects and synthesises. The price list sets the unit cost and your loop decides how many units you buy. Price the system on the **expected** value, budget and alert on the **likely high** (about p95) request, and size caps and fuses from the **capped ceiling**. A ceiling exists only when every loop, tool budget and retry policy has a hard maximum the runtime enforces.

## 2. The estimation method (no code needed)

Fill one row per step on the request path. Use traced numbers where you have them, assumptions where you don't, and mark which is which.

| Step | Model tier | p (triggers) | calls when triggered | max calls (cap) | tok in | tok out | cached share | memo share |
|---|---|---|---|---|---|---|---|---|
| router | small | 1.0 | 1 | 1 | 3,000 | 50 | 0.8 | 0 |
| reasoning loop | large | 0.7 | 3 | 12 | 12,000 | 400 | 0.7 | 0 |
| … | | | | | | | | |

1. **Expected calls** per step = p × (1 − memo) × calls. Sum them: that is the agentic multiplier (an illustrative support flow comes to 4.8 model calls for "one request" before retries).
2. **Cost per call** = (tok in × cache factor × input price + tok out × output price) / 1,000,000.
3. **Expected cost** = Σ expected calls × cost per call, × (1 + retry rate), + non-model cost (embeddings, vector queries, re-ranking, paid tool APIs, search fees, observability storage, online-eval sampling).
4. **Likely high** (about a p95 request) = every step fires at its p95 calls and p95 input size from traces, cache as normal. Use it for budgets and alert thresholds. Without traces the script assumes 2x calls and 1.5x input and says so.
5. **Capped ceiling** = Σ max calls × cost per call with no cache and input at its capped size (context grows in loops), × (1 + retries allowed per call). It assumes every step hits its cap at once with every call retried to the limit, so it is a bound, not a forecast: the built-in example gives 106x expected, against 6.4x for the likely high. Use it to size fuses and to state exposure if a bad prompt or tool drives many requests to their caps.
   **No caps, no ceiling.** If any step lacks a cap, report the current ceiling as "UNBOUNDED", then rerun with the caps you propose and report that figure separately, labelled "with proposed caps".
6. **Per-step share** = each step's expected cost / total. The lever goes where the share is, not where the code is easiest to change.
7. **Monthly** = expected × requests per day × 30. Compare with the invoice; a material gap means a missing step, retries, non-model costs or wrong token counts. **Monthly at peak** = expected × the busiest day's volume × 30: what a month would cost if every day looked like the peak day. It is a planning upper figure, not a forecast.
8. **Cost per successful task** = expected cost / task success rate (from evals). Use this, not cost per request, to compare variants.

Run the same arithmetic with `scripts/cost_model.py`:

```
python scripts/cost_model.py --example > spec.json   # edit: prices (dated), steps, volume
python scripts/cost_model.py spec.json
```

It prints expected, likely high and capped ceiling per request (or UNBOUNDED), monthly cost at expected volume and at the peak-day run rate, per-step share including non-model cost, latency and peak load per tier. Steps run in sequence unless marked `parallel` or given a shared `stage`. Each default the script had to fill in (missing `max_tok_in`, guessed p95, no cap, no peak volume) gets a warning line. The three what-ifs are prompt cache off; every step on the cheapest tier, printed as a BOUND because it ignores quality and repair cost (an upper limit on routing savings, never a recommendation); and the most expensive step's calls halved (the loop lever). `--selftest` runs the self-check alone; it also runs before every report. Partial `prices` merge per tier and field; edited prices without `prices_as_of` print as UNDATED. Example output with the built-in spec (prices as of 2026-10-06; small = Haiku 4.5, mid = Sonnet 5.5):

```
model calls/request   expected 6.2   cap 21
cost/request          expected $0.0391   likely high (~p95 request) $0.2498
capped ceiling        $4.1533 (106x expected): every step at its cap, no cache, max retries; a bound, not a forecast
per month (30 days)   $11,725 at 10,000/day; $29,313 at the peak-day run rate (25,000/day)
share: router 2.9%, retrieval 2.6%, reasoning 72.7%, reflection 13.9%, guardrails 2.8%, other (non-model) 5.1%
what-ifs: prompt cache off +110%; BOUND all steps on 'small' -43%; 'reasoning' calls halved -36%
```

In this example the reasoning loop holds about three quarters of spend, so routing the three small steps to an even cheaper model moves the total by single digits, while losing the prompt cache doubles the bill.

**Getting real numbers.** Pull per-step input, output and cache-read tokens from traces (`gen_ai.usage.input_tokens`, `gen_ai.usage.output_tokens`, `gen_ai.usage.cache_read.input_tokens`, `gen_ai.usage.cache_write.input_tokens`) or from the provider's usage fields; take p and calls from span counts per trace; take the 95th or 99th percentile of input tokens at the cap for `max_tok_in`. Count tool definitions and the provider's tool-use system prompt as input tokens on every call that offers tools.

**What the model leaves out.** Context that grows inside a loop (use per-iteration trace data, not a flat average); token counts that change when you switch model families (tokenizers differ, see the price snapshot); fixed costs (GPU reservations, platform fees, on-call). Replace every assumption with a traced number as soon as you have one.

## 3. Price snapshot (as of 2026-10-06)

Source: Anthropic pricing page, platform.claude.com/docs/en/about-claude/pricing, read 2026-10-06; OpenAI flex processing guide, developers.openai.com/api/docs/guides/flex-processing, read 2026-10-06. Recheck before use. Model choice itself belongs to **agent-model-selector**; these numbers are here so the cost model has dated defaults.

Tier names are the ones `scripts/cost_model.py` uses. When a user says "frontier model" or "small model" without naming one, map it to a row here and list the mapping as an assumption.

| Tier | Model | Input / output per MTok | Cache read (x that model's input) |
|---|---|---|---|
| small | Claude Haiku 4.5 | $1 / $5 | 0.1x ($0.10 per MTok) |
| mid | Claude Sonnet 5.5 | $2 / $10 | 0.1x ($0.20 per MTok) |
| large | Claude Opus 5.5 | $4 / $20 | 0.05x ($0.20 per MTok) |
| frontier | Claude Fable 5.1 | $10 / $50 | 0.025x ($0.25 per MTok) |

Take the cache-read multiplier from the row of the model the step calls; it is the only cache price that differs by model. Models not listed use 0.1x.

| Item | Value (USD) |
|---|---|
| Prompt cache write, 5-minute | 1.25x base input on every model (pays off after 1 read) |
| Prompt cache write, 1-hour | 2x base input on every model (pays off after 2 reads) |
| Batch API | 50% off input and output; stacks with caching; not with fast mode |
| US-only inference (`inference_geo: "us"`) | 1.1x on all token categories; cloud regional endpoints carry a 10% premium |
| Fast mode (research preview, Opus models) | premium price, e.g. Opus 5.5 $8 in / $40 out |
| Tool-use system prompt | about 290 to 680 extra input tokens per call that offers tools, by model, plus the tool definitions themselves |
| Web search (server tool) | $10 per 1,000 searches plus tokens |
| Tokenizer | Claude 4.7 and later produce about 30% more tokens for the same text than 4.6 and earlier; re-measure token counts after a model-family switch |
| OpenAI flex processing | batch-rate pricing for synchronous calls; slower; may return `429 Resource Unavailable` (not billed); retry with backoff or fall back to the standard tier |

Older book figures for eval cost (mid-2026, see ci-gate.md) and GPU rental (early 2026) are dated; treat them as orders of magnitude.

## 4. Levers, in order

Work down the stack. The top three change how many units you buy and need only code; the bottom three discount each unit and need progressively more evaluation and infrastructure.

| # | Lever | What to do | Typical effect | Prove it with | Risk |
|---|---|---|---|---|---|
| 1 | **Bound the work** | Cap loop steps, tool calls, retries, tokens and cost per task type; per-session cost and turn fuse with handoff | Removes the tail; saves what capped sessions spend today (read it from traces) | max and p99 cost per session, stop-reason mix | Caps too tight cut success; set from the success-rate curve by step count |
| 2 | **Fewer calls** | Move routing, validation, formatting, permission checks and schema repair to code; merge classify + choose + fill into one structured call; drop reflection where evals show no gain | Proportional to calls removed | calls per request, task success | Merging steps on high-risk actions that need a separate check |
| 3 | **Fewer tokens per call** | Token ceiling per prompt section; 3 to 5 re-ranked chunks, not 10; trim tool results to the fields the next step needs; summarise old turns ("context janitor": keep system prompt and last turns, drop the middle with a note) | Large in loops, because every kept token is paid again on each later step; also cuts time to first token | input tokens per call by step | Dropping facts the next step needs; check with evals |
| 4 | **Reuse finished work** | Cache-stable prompt prefix (layout details: **agent-context-designer**); application caches for stable, non-personalised work; planner-decision memoisation | Prompt cache: input cost on cached share falls to 0.1x (lower on the top tiers, see section 3); app caches skip whole calls | cache-read token share, hit rate per cache, correctness spot checks | App caches can serve stale or cross-user results (section 5) |
| 5 | **Cheaper model per step** | Small models for classify, extract, guard; strong model for planning and the answer; cascade where most inputs are easy (section 6). Shortlist with **agent-model-selector** | Real only on steps with a large share | cost per *successful* task, repair rate | Repairs and retries erase the saving |
| 6 | **Cheaper pricing tier** | Batch for evals, enrichment, backfills, nightly reports; flex for latency-tolerant synchronous work; regional pricing only when residency requires it | About 50% on the moved share | share of spend on batch or flex | Never for work a user waits for |
| 7 | **Engine and hardware** | Self-host narrow, steady, high-volume steps; quantization, prefix caching, speculative decoding (section 9) | Step-shaped; wins only at high utilisation | cost per million tokens at measured utilisation | Ops burden, cold starts, quality loss from quantization |

Rule of thumb: when one step holds more than half the spend, levers 1 to 4 on that step come before anything else. A cheaper system that answers worse has been degraded rather than optimised, so compare variants on cost per successful task against the eval set (**agent-eval-designer**).

**No eval set yet: baseline before levers.** "Without hurting quality" needs a measured quality, so no lever that changes prompts, context, models or the number of calls ships before a baseline exists. Order the work:
1. Trace per-step tokens, calls and stop reasons (the cost model needs them anyway). If only final answers are logged, this comes first.
2. Build a minimal baseline: about 100 real requests sampled from traces, stratified by task type and including recent failures; a pass or fail rule per case (deterministic checks where possible, a rubric otherwise); three runs of the unchanged system to measure the noise band. Record a pass rate with its interval (100 cases resolve about ±7 points at an 85% pass rate) and the cost per successful task.
3. Apply levers one at a time, each measured against the baseline.

Safe to ship before the baseline: caps and fuses set above the traced p99 (they stop runaway sessions without touching typical ones) and moving offline jobs to batch. Dataset design, scorers and judge calibration belong to **agent-eval-designer**; hand it the sampled traces and the task types.

## 5. Caches

| Cache | Where | Saves | Correctness risk | Rules |
|---|---|---|---|---|
| KV cache | Inside one generation | Recomputing the prompt per token | None | Automatic |
| Prefix cache | Self-hosted engine (vLLM, SGLang, TGI) across requests | Prefill of shared prefixes | None; eviction under memory pressure shows as tail latency | Turn it on; stable prefix first |
| Provider prompt cache | Billed by the API | Input cost on cached share (read 0.1x on most models, per-model values in section 3; write 1.25x or 2x; as of 2026-10) and some latency | None; a changed prefix silently stops hits | Put stable content first; alert on cache-read share dropping after a deploy |
| Application caches (response, retrieval, embedding, tool result, planner decision) | Your code | Whole calls | Stale answers; one user's result served to another | Key by tenant, permission scope and the full decision context; TTL where the world changes; never store failed or invalid results; read-only tools only |

Planner-decision memoisation: key on the full planner context (task, facts gathered, tools available, tools that recently returned nothing new); look up exact, then normalised, then semantic above a high threshold with guards. A high hit rate with no new facts means the agent is looping; alert on it. Savings depend on how often your states repeat; one illustrative run avoided about half of planner calls, yours may avoid none.

Reasoning models and caching: early measurements found reasoning-model caches rarely hit; current APIs keep the cache across prior thinking blocks on newer models, so measure cache-read tokens rather than assume either way.

## 6. Routing and cascades

- **Task-based routing** (per step): small model classifies, extracts and guards; strong model plans and answers. Start with cheap heuristics (task type, keywords) before a trained router. Learned routers trained on preference data have reported more than halving cost at equal quality on public benchmarks (RouteLLM, 2024); verify on your own traffic.
- **Cascade** (per input): try the small model, escalate on low confidence. With per-request costs c_small and c_large and a share s that stops at the small model, the cascade costs c_small + (1 − s) × c_large. It beats large-only only when **s > c_small / c_large**, and only if the confidence signal is validated against labelled outcomes (agreement across reruns or a separate checker beats self-reported confidence).
- **Judge it on cost per successful task**: (expected cost + repair cost) / success rate. A cheap model that produces invalid tool arguments can cost more than it saves.

## 7. Resilience is also cost policy

- **Retries**: an agent that succeeds 60% of the time reaches about 99% after five independent attempts, at about five times the tokens. If reliability comes from retries, put the retry rate in the cost model. Retry only transient errors (timeouts, 429, 5xx) with jittered backoff and a max; fail fast on client errors.
- **Timeouts are soft by default; hard ones must be designed.** A timeout that leaves the generation or tool running keeps billing. Cancel downstream work on timeout.
- **Three breakers**: per dependency (stop calling an unhealthy service for a while), per session (cost or turn fuse that halts and hands off; a provider's account-level cap is far too coarse), per output stream (pause a component after N unusable outputs in a window).
- **Fallback model**: decided at design time and tested through the whole pipeline in CI. Structured output in tiers: provider strict-schema mode, local validation with a bounded re-ask carrying the error, and last, canonicalising onto the product's enums with conservative defaults. Valid JSON is not consistent decisions: check action-triggering fields (priority, refund amount) across runs and models.

## 8. Latency

Decompose p95, not the mean, into: model time (prefill, felt as time to first token, grows with prompt length; decode, one token at a time, bound by memory bandwidth), retrieval, tools, orchestration, and loop iterations. Agents are slow mostly because of sequential calls and long contexts.

| Symptom | Lever |
|---|---|
| p95 far above p50 | Loop iterations and retries in the tail: cap steps, add tool timeouts that cancel, check the stop-reason mix of slow traces |
| Time to first token high | Shorter prompt, stable cached prefix, fewer tools offered per call |
| Many sequential calls | Merge steps; run independent reads in parallel (raises downstream peak load; avoid speculative fan-out under load). At the extreme, parallel sub-agents cut research time by up to 90% while using about 15 times the tokens of a chat (Anthropic, 2025-06) |
| Long answers | Stream tokens; show progress |
| Work over about 30 s | Async job with ID, status, cancel and streamed progress over SSE or WebSockets; common gateways cut REST calls at 30 s |
| Inline checks slow | Guardrail budget about 10 ms regex, 50 ms embedding, 100 ms total; LLM checks go asynchronous unless they guard an irreversible action |
| Bursts | Rate limits per user or tenant, bounded queues, priorities, explicit rejection or degradation ("a queue that grows without limits is a delayed failure") |
| Speed matters for some users only | Premium fast tiers only on paths where users wait |

## 9. Where each agent runs

Place each agent, not the whole system: the data a step touches decides sensitivity; its traffic decides load shape.

| | Bursty load | Steady, high volume |
|---|---|---|
| **Open data** | Managed API behind a gateway (default start) | Managed API; consider a self-hosted lane for a narrow, high-volume step a small open model handles at your quality bar |
| **Restricted data** | Dedicated endpoint with isolated tenancy, or a regional/residency option | Your weights in your VPC (or on-prem when required) |

- Start on managed APIs behind a gateway that makes provider and model a config value. Move one agent only with a named reason: data that cannot leave, or a steady step whose GPUs you can keep busy. API cost rises smoothly with traffic; self-hosted cost rises in steps because GPUs come whole.
- Partition by sensitivity: a supervisor routing by category need not run where a retrieval agent reads raw PII.
- Count data gravity: inference on one cloud and vectors on another can cost more in egress per retrieval step than in inference.
- Separate services per agent only when load, owners or permissions differ; each hop adds latency and failure modes.
- **Peak capacity check** before any scale-up, per model: peak requests/min = the busiest day's requests ÷ 1,440 × peak-hour factor; model calls/min = that × expected calls per request on that model; input tokens/min = calls/min × average input tokens; output tokens/min likewise. The peak-hour factor is the busiest hour's traffic over the average hour's. Default 3, which assumes all traffic falls in an 8-hour working day (24 ÷ 8); replace it with the ratio measured from gateway logs or traces, and label it assumed until then. On current Claude models cache reads do not count toward the input-tokens-per-minute limit, while cache writes and uncached input do (as of 2026-10), so compare uncached input tokens with that limit; other providers may count all input. Compare each with the provider's requests-, input-token- and output-token-per-minute limits for your tier, keep headroom for retries, and request increases early. A second route to the same model (another region or cloud endpoint) adds capacity and doubles as a fallback; regional endpoints may carry a price premium.

**If you self-host** (sizing rules, as of 2026-10; measure on your hardware):
- Weights: parameters × (bits ÷ 8) × 1.2 for overhead; an 8B model at 16 bits is about 19 GB. Measured usage runs higher with cache and batch memory.
- KV cache bytes = sequence length × layers × KV heads × head dim × 2 × bytes per value. A 7B-class model with 28 layers, 4 KV heads of dim 128 at 16 bits holds about 56 KiB per token: one 32,000-token agent context is about 1.75 GiB. Size concurrency from this at real context lengths, not from parameter count.
- Cold start: a measured first request after deploy took about 125 s against 0.28 s warm. Keep weights on persistent storage and a warm minimum where latency matters.
- Prefix caching on. Expect a cache-invalidation tax when the system prompt changes or fresh context is injected early.
- Quantization saves 4 to 8 times memory with a task-dependent accuracy loss; 8-bit can be slower than 16-bit without kernel support. Evaluate the quantized checkpoint on your tasks; prefer the model developer's own quantized releases.
- Speculative decoding helps per-token latency on memory-bound servers at low to moderate load and shrinks as batches fill; a draft model untuned for your domain can make it slower. Measure acceptance rate on your traffic; another replica may be cheaper.
- vLLM, SGLang and TGI expose OpenAI-compatible APIs: keep the backend a config choice.
