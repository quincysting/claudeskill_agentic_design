# Cost and latency: model, levers, deployment

Load this for steps 12 to 15 of the procedure: estimating cost per request and per successful run, choosing levers, planning latency and deciding where each agent runs. Prices and provider features change monthly; everything marked "as of 2026-10" must be rechecked against the provider's page before it goes into a decision. How the runtime enforces caps, and how the agent is served (API layer, workers, model server, streaming, deployment shape), is designed in **agent-harness-designer**; this file sets the numbers and checks the result.

## 1. The two sums

```
cost per request = Σ steps  P(step runs) × (1 − memo hit) × calls per run
                            × (input tok × input price × cache factor + output tok × output price)
                   × (1 + retry and repair overhead)  + non-model cost per request
cache factor     = fresh share + cached share × read multiplier + written share × write multiplier
latency          = Σ critical path (prefill + decode per model call, retrieval, tool, orchestration time)
```

An agent's cost belongs to the workflow, not the model. One request may end after one call; another plans, retrieves, calls tools, reflects and synthesises. The price list sets the unit cost and your loop decides how many units you buy. So token volume per task, not the per-call price, drives cost and speed: an agentic workflow can generate hundreds of thousands of tokens before anyone reads the output [NG Why We Need More Compute for Inference, 2024-04-24]. Price the system on the **expected** value, budget and alert on the **likely high** request (every step at its p95 at once, which sits above a true p95), and size caps and fuses from the **capped ceiling**. A ceiling exists only when every loop, tool budget and retry policy has a hard maximum the runtime enforces.

**How many tokens to spend.** In 2024 Ng welcomed workflows that burn hundreds of thousands of tokens and asked for cheaper, faster inference [NG Why We Need More Compute for Inference, 2024-04-24]; in 2026 he warns that past a point more tokens run into organisational bottlenecks and diminishing returns, and that sellers of tokens gain when you burn them [NG What Comes After Tokenmaxxing?, 2026-08-07]. PRODGUIDE says teams fail less because the agent is unintelligent than because it is unbounded [PRODGUIDE ch17]. The positions agree once the unit is right: spend tokens where they raise the success rate or cut human minutes, measured as cost per successful run (section 2, step 8), and cap each run so that a loop cannot decide the spend (section 4, "At a cap, stop cleanly").

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
4. **Likely high** = every step fires at its p95 calls and p95 input size from traces, cache as normal. Real requests rarely hit p95 on every step together, so in a multi-step pipeline this sits above a true p95 request: safe for budgets and alert thresholds, not a precise percentile. To quote a real p95, read it from the per-request cost distribution in traces. Without traces the script assumes 2x calls and 1.5x input and says so.
5. **Capped ceiling** = Σ max calls × cost per call with no cache and input at its capped size (context grows in loops), × (1 + retries allowed per call). It assumes every step hits its cap at once with every call retried to the limit, so it is a bound, not a forecast: the built-in example gives 121x expected, against 6.7x for the likely high. Use it to size fuses and to state exposure if a bad prompt or tool drives many requests to their caps.
   **No caps, no ceiling.** If any step lacks a cap on calls, input tokens or output tokens that the code sets (a framework or model default does not count; in the script, an absent or null `max_calls`, `max_tok_in` or `max_tok_out`), report the current ceiling as "UNBOUNDED", then rerun with the caps you propose and report that figure separately, labelled "with proposed caps".
6. **Per-step share** = each step's expected cost / total. The lever goes where the share is, not where the code is easiest to change.
7. **Monthly** = expected × requests per day × 30. Compare with the invoice; a material gap means a missing step, retries, non-model costs or wrong token counts. **Monthly at peak** = expected × the busiest day's volume × 30: what a month would cost if every day looked like the peak day. It is a planning upper figure, not a forecast.
8. **Cost per successful run** = (expected cost + review minutes × value per minute) / success rate. PRODGUIDE defines the cost of a run as model cost plus tool cost plus review minutes × value per minute [PRODGUIDE ch17 §The Economics of an Agent Run]; dividing by the success rate, so that failed runs are paid for by the successful ones, is this skill's step. Expected cost already holds model and tool cost. Review minutes are the human review and cleanup time per run, averaged over all runs; the value per minute is an internal rate, rough but kept consistent. A success is a run that met its SLA inside guardrails, a verified or approved outcome: count every output as a success and you optimise for chatter. Use this unit, not cost per request or per call, to compare variants and to hand to **agentic-business-case**. Leave the human term out only when review time is the same for every variant you compare. agent-model-selector compares model configurations on cost per solved task, the same spend without review minutes (its role-model-mapping.md §7); use this unit instead whenever the variants differ in review time. In the built-in example (85% success, half a minute of review at $40 an hour) review is about 90% of the total, which fits Ng's rule that AI tokens are cheap and human tokens are gold [NG Make All Your Tokens (and Your Brainwork) Count, 2026-07-10]. There, shorter review (scannable previews, receipts) moves the total more than any model lever. Once an application scales, know this number per query or per conversation [NG What Comes After Tokenmaxxing?, 2026-08-07].

Run the same arithmetic with `scripts/cost_model.py`:

```
python scripts/cost_model.py --example > spec.json   # edit: prices (dated), steps, volume
python scripts/cost_model.py spec.json
```

It prints expected, likely high (every step at its p95) and capped ceiling per request (or UNBOUNDED), monthly cost at expected volume and at the peak-day run rate, cost per successful run when the spec sets `success_rate` (with `review_minutes` and `value_per_minute`; a user spec never inherits these from the example), per-step share including non-model cost, latency and peak load per tier. Steps run in sequence unless marked `parallel` or given a shared `stage`. Each gap the script had to work around (a step with no call, input-token or output-token cap, guessed p95, no peak volume, a tier that names no model or is a stand-in) gets a warning line, and so does a `small` step whose `tok_in`, `p95_tok_in` or `max_tok_in` passes 100K tokens (it belongs on `small_long`). The what-ifs are prompt cache off; prompt cache churning (every cached token written and none read, as when the prefix changes per request; printed only when the spec caches something); every step on the cheapest tier the system already uses, printed as a BOUND because it ignores quality and repair cost (an upper limit on routing savings, never a recommendation; skipped when every step uses one tier); and the most expensive step's calls halved (the loop lever; skipped when that step makes one call). When nothing is cached yet, the first what-if is "prompt cache on" at 80% read and 5% written instead. Quote it only after checking that the stable prefix reaches the provider's minimum cacheable length (a per-model token count on its caching page) and that volatile content (timestamps, user names, request IDs, retrieved context) can move after the static text; the script checks neither, and a short single-call prompt may not be cacheable at all. A user spec inherits the example's `retry_rate`, `worst_retries`, `other_per_request` and `peak_hour_factor` when it leaves them out (only the success inputs and the peak-day volume are never inherited), so set each one, with 0 where it does not apply. `--selftest` runs the self-check alone; it also runs before every report. Partial `prices` merge per tier and field; edited prices without `prices_as_of` print as UNDATED. Top-level numbers you leave out (volume, retry rate, worst retries, other cost, peak-hour factor) keep the example's values, and so does the peak-day volume when `requests_per_day` is left out too; the script prints a warning naming each one. A null value, a p95 above its cap, or a spec that costs $0 stops with a one-line message. Example output with the built-in spec (prices as of 2026-10-19; small = Haiku 5.5 for prompts up to 100K tokens, mid = Sonnet 5.5):

```
model calls/request   expected 6.2   cap 21
cost/request          expected $0.0341   likely high $0.2272 (every step at its p95; above a true p95)
capped ceiling        $4.1111 (121x expected): every step at its cap, no cache, max retries; a bound, not a forecast
per month (30 days)   $10,218 at 10,000/day; $25,545 at the peak-day run rate (25,000/day)
cost/successful run   $0.4322 at 85% success: model and tools $0.0401, human review $0.3922 (91%)
share: router 0.3%, retrieval 0.3%, reasoning 77.9%, reflection 15.2%, guardrails 0.3%, other (non-model) 5.9%
what-ifs: prompt cache off +119%; cache churning +150%; BOUND all steps on 'small' -88%; 'reasoning' calls halved -39%
```

In this example the reasoning loop holds about three quarters of spend, and the three small-tier steps together less than 1%, so moving them anywhere changes the total by under a percent, while losing the prompt cache more than doubles the bill. A churning cache costs more than no cache at all, because every write carries the write premium.

**Getting real numbers.** Pull per-step input, output and cache-read tokens from traces (`gen_ai.usage.input_tokens`, `gen_ai.usage.output_tokens`, `gen_ai.usage.cache_read.input_tokens`, `gen_ai.usage.cache_write.input_tokens`) or from the provider's usage fields; take p and calls from span counts per trace; take the 95th or 99th percentile of input tokens at the cap for `max_tok_in`. Count tool definitions and the provider's tool-use system prompt as input tokens on every call that offers tools. Normalise provider usage fields first: some providers' input count leaves out cached tokens and others include them (observability.md §2). Cost uses uncached = input − cache read − cache write, with input taken in the spec's meaning (all input).

A reported "cache hit rate" can mean three things: the share of calls with any cache read, read tokens over cacheable tokens, or read tokens over all input. Find out which before using it. Then take cached share = cache read ÷ input and written share = cache write ÷ input from the usage fields, per step. If you only have a call-level rate, convert it with a stated assumption (for example, the size of the cached prefix on a hit) and mark the result assumed.

**What the model leaves out.** Context that grows inside a loop (use per-iteration trace data, not a flat average); token counts that change when you switch model families (tokenizers differ, see the price snapshot); fixed costs (GPU reservations, platform fees, on-call). Replace every assumption with a traced number as soon as you have one.

**Attributing cost.** Compute cost per model call from the four token classes (uncached input, cache read, cache write, output) × one dated price table, kept in one module rather than copied into each service. Put it on the span (`app.cost.usd`) and emit it twice:
1. A per-call ledger record keyed by tenant, workflow, agent, session and version, kept for drill-down and for monthly reconciliation against the provider's bill.
2. A metric with low-cardinality dimensions only (agent, model, tenant tier or task type). Never use session or user IDs as metric dimensions, because metric cost grows with every distinct value.

Per run, also count model calls, tokens and tool calls, plus review and cleanup minutes, and split cost by phase (planning, retrieval, drafting, verification, execution, reporting). Without the phase split a team shortens the final answer while verification and rework eat the budget [PRODGUIDE ch17 §The Economics of an Agent Run].

A gap of more than a few percent between the ledger and the invoice means a missing step, unpriced retries or wrong token semantics.

## 3. Price snapshot (as of 2026-10-19)

Source: Anthropic pricing page, platform.claude.com/docs/en/about-claude/pricing, read 2026-10-06, with the small tier and the cache-read multipliers re-checked 2026-10-19; OpenAI flex processing guide, developers.openai.com/api/docs/guides/flex-processing, read 2026-10-06. Recheck before use. This is the same snapshot as the agent-model-selector skill's model-landscape-2026-10.md, which owns model choice and the refresh procedure; if the two ever disagree, the one with the later date wins and the other is out of date. These numbers are here so the cost model has dated defaults.

Tier names are the ones `scripts/cost_model.py` uses. When a user says "frontier model" or "small model" without naming one, map it to a row here and list the mapping as an assumption.

| Tier | Model | Input / output per MTok | Cache read (x that model's input) |
|---|---|---|---|
| small | Claude Haiku 5.5, prompts up to 100K tokens | $0.10 / $0.50 | 0.1x ($0.01 per MTok) |
| small_long | Claude Haiku 5.5, prompts over 100K tokens | $0.50 / $2.50 | 0.1x ($0.05 per MTok) |
| mid | Claude Sonnet 5.5 | $2 / $10 | 0.05x ($0.10 per MTok) |
| large | Claude Opus 5.5 | $4 / $20 | 0.05x ($0.20 per MTok) |
| frontier | Claude Fable 5.1 | $10 / $50 | 0.025x ($0.25 per MTok) |

Take the cache-read multiplier from the row of the model the step calls; it is the only cache price that differs by model. Models not listed use 0.1x. Haiku 5.5's price depends on prompt length: a step that carries long history can cross 100K tokens, so measure real prompt lengths and put such steps on `small_long`. Haiku 4.5 ($1 / $5) was still listed active on 2026-10-19, although its "not sooner than" retirement date had passed; check the provider's deprecations page before pricing a plan on it.

**Models not in this snapshot.** For a model from another provider, or an older model still offered somewhere (a model picker in the UI, a config default), add a tier to the spec's `prices` with that model's name, list price, the date you read it and the source. Check the provider's deprecation page too: a retired model still offered in a picker is itself a finding, since calls to it fail once it is switched off (F1, J2). When no price can be looked up (a retired model, a private contract, no web access), set the tier's `model` to "stand-in for <model>" with the nearest listed price, present dollar totals as order of magnitude only, and base the findings on shares, ratios and what-ifs, which depend less on the exact price. The report prints the model behind each tier it uses ("tiers:" line) and warns on a stand-in or a tier with no model name.

| Item | Value (USD) |
|---|---|
| Prompt cache write, 5-minute | 1.25x base input on every model (pays off after 1 read) |
| Prompt cache write, 1-hour | 2x base input on every model (pays off after 2 reads) |
| Batch API | 50% off input and output; stacks with prompt caching on Anthropic's API, but not every platform combines the two (check yours; on AWS see [aws-implementation-notes.md](aws-implementation-notes.md)); not with fast mode |
| US-only inference (`inference_geo: "us"`) | 1.1x on all token categories; cloud regional endpoints carry a 10% premium |
| Fast mode (research preview, Opus models) | premium price, e.g. Opus 5.5 $8 in / $40 out |
| Tool-use system prompt | about 290 to 680 extra input tokens per call that offers tools, by model, plus the tool definitions themselves |
| Web search (server tool) | $10 per 1,000 searches plus tokens |
| Tokenizer | Claude 4.7 and later (Haiku 5.5 included) produce about 30% more tokens for the same text than 4.6 and earlier (Haiku 4.5 included); re-measure token counts after a model-family switch |
| OpenAI flex processing | batch-rate pricing for synchronous calls; slower; may return `429 Resource Unavailable` (not billed); retry with backoff or fall back to the standard tier |

Older book figures for eval cost (mid-2026, see ci-gate.md) and GPU rental (early 2026) are dated; treat them as orders of magnitude.

## 4. Levers, in order

Work down the stack. The top three change how many units you buy and need only code; the bottom three discount each unit and need progressively more evaluation and infrastructure.

| # | Lever | What to do | Typical effect | Prove it with | Risk |
|---|---|---|---|---|---|
| 1 | **Bound the work** | Per-run caps on tokens, model calls, tool calls, retries, plan steps and cost per task type, ending in a partial result (below); per-session cost and turn fuse with handoff | Removes the tail; saves what capped sessions spend today (read it from traces) | max and p99 cost per session, stop-reason mix | Caps too tight cut success; set from the success-rate curve by step count |
| 2 | **Fewer calls** | Move routing, validation, formatting, permission checks and schema repair to code; merge classify + choose + fill into one structured call; drop reflection where evals show no gain | Proportional to calls removed | calls per request, task success | Merging steps on high-risk actions that need a separate check |
| 3 | **Fewer tokens per call** | Token ceiling per prompt section; 3 to 5 re-ranked chunks, not 10; trim tool results to the fields the next step needs; summarise old turns ("context janitor": keep system prompt and last turns, drop the middle with a note) | Large in loops, because every kept token is paid again on each later step; also cuts time to first token | input tokens per call by step | Dropping facts the next step needs; check with evals |
| 4 | **Reuse finished work** | Cache-stable prompt prefix (layout details: **agent-context-designer**); application caches for stable, non-personalised work; planner-decision memoisation | Prompt cache: input cost on cached share falls to 0.1x or less (0.05x on Sonnet and Opus 5.5, as of 2026-10; section 3); app caches skip whole calls | cache-read token share, hit rate per cache, correctness spot checks | App caches can serve stale or cross-user results (section 5) |
| 5 | **Cheaper model per step** | Small models for classify, extract, guard; strong model for planning and the answer; cascade where most inputs are easy (section 6). Shortlist with **agent-model-selector** | Real only on steps with a large share | cost per successful run, repair rate | Repairs and retries erase the saving |
| 6 | **Cheaper pricing tier** | Batch for evals, enrichment, backfills, nightly reports; flex for latency-tolerant synchronous work; regional pricing only when residency requires it | About 50% on the moved share | share of spend on batch or flex | Never for work a user waits for; check whether batch and prompt caching combine on your platform before counting both discounts |
| 7 | **Engine and hardware** | Self-host narrow, steady, high-volume steps; quantization, prefix caching, speculative decoding (section 9) | Step-shaped; wins only at high utilisation | cost per million tokens at measured utilisation | Ops burden, cold starts, quality loss from quantization |

**At a cap, stop cleanly.** A capped run drops to draft-only and returns a partial result with status `partial`: the work it finished, the work it did not, any receipts it holds, and the fewest questions someone must answer before the next step can go ahead [PRODGUIDE ch17 §Budget Guardrails and Context Discipline]. A cap that stops without saying so turns a cost control into a silent failure. How tight: the capped ceiling (section 2) sizes fuses; PLAYBOOK puts a run-level token cap at about three times expected use [PLAYBOOK ch6 §Token Cost Management], which bounds the tail far more tightly and ends some legitimate runs early, so it needs this fallback. Set each cap from the success-rate curve by step count. Caps are set per role: a router that answers with one word and a specialist that writes a report need different output caps. When several roles share one client object, a cap set on that client applies to all of them, so the fix names the split (a client per role, or the cap passed on each call). The checks themselves run before every model and tool call, with counters in checkpointed state (agent-harness-designer).

**Caps with no traces yet.** "Above the traced p99" needs traces. Until they exist, set provisional caps from a staging run on realistic inputs (or generous assumed values, such as twice the staging maximum), mark them provisional in the plan, and reset them from the traced p99 after one to two weeks of production traffic. A provisional cap that is too tight shows up as a rising share of `partial` stops; watch that share daily until the reset.

**Ship each lever like a release.** Canary on 1 to 5% of runs for at least 24 hours [EVALS ch10], with rollback triggers on success under the SLA, p95 latency, duplicate side effects and review minutes, and on a trigger, flip to draft-only or roll back [PRODGUIDE ch17 §Performance Tuning Without Breaking Reliability]. This skill adds cost per successful run as a fifth trigger.

Rule of thumb: when one step holds more than half the spend, levers 1 to 4 on that step come before anything else. A cheaper system that answers worse has been degraded rather than optimised, so compare variants on cost per successful run against the eval set (**agent-eval-designer**).

**No eval set yet: baseline before levers.** "Without hurting quality" needs a measured quality, so no lever that changes prompts, context, models or the number of calls ships before a baseline exists. Order the work:
1. Trace per-step tokens, calls and stop reasons (the cost model needs them anyway). If only final answers are logged, this comes first.
2. Build a minimal baseline: about 100 real requests sampled from traces, stratified by task type and including recent failures; a pass or fail rule per case (deterministic checks where possible, a rubric otherwise); three runs of the unchanged system to measure the noise band. Record a pass rate with its interval (100 cases resolve about ±7 points at an 85% pass rate) and the cost per successful run.
3. Apply levers one at a time, each measured against the baseline.

Safe to ship before the baseline: caps and fuses set above the traced p99, or provisional caps from a staging run when there are no traces yet (they stop runaway sessions without touching typical ones), and moving offline jobs to batch. A cache-layout change can also go first when it only moves volatile fields (timestamp, user name, request ID) below the cache point and leaves the wording unchanged. Run it in shadow on identical inputs with write tools stubbed, and compare tool choice and final decision pair by pair with production. Ship it only if the pairs disagree no more often than two runs of the unchanged system disagree on the same inputs. Any change to wording waits for the baseline. Dataset design, scorers and judge calibration belong to **agent-eval-designer**; hand it the sampled traces and the task types.

## 5. Caches

| Cache | Where | Saves | Correctness risk | Rules |
|---|---|---|---|---|
| KV cache | Inside one generation | Recomputing the prompt per token | None | Automatic |
| Prefix cache | Self-hosted engine (vLLM, SGLang, TGI) across requests | Prefill of shared prefixes | None; eviction under memory pressure shows as tail latency | Turn it on; stable prefix first |
| Provider prompt cache | Billed by the API | Input cost on cached share (read 0.1x on most models, per-model values in section 3; write 1.25x or 2x; as of 2026-10) and some latency | None; a changed prefix silently stops hits | Put stable content first; alert on cache-read share dropping and on the write-to-read ratio jumping after a deploy (cache churn, below) |
| Application caches (response, retrieval, embedding, tool result, planner decision) | Your code | Whole calls | Stale answers; one user's result served to another | Key by tenant, permission scope and the full decision context; TTL where the world changes; never store failed or invalid results; read-only tools only |

**Cache churn.** Monitor the cache write-to-read ratio, not only the read share. A write-dominant ratio after a deploy means the prefix changes per request: a timestamp, request ID, reordered tools or a changed setting placed before the cache point. Every call then pays the write premium and reads nothing back, which costs more than no cache (the `cost_model.py` churn what-if prices it). Routing one prompt across regions can also raise writes on some platforms, so check routing before blaming the prompt. Prompt layout belongs to **agent-context-designer**.

Planner-decision memoisation: key on the full planner context (task, facts gathered, tools available, tools that recently returned nothing new); look up exact, then normalised, then semantic above a high threshold with guards. A high hit rate with no new facts means the agent is looping; alert on it. Savings depend on how often your states repeat; one illustrative run avoided about half of planner calls, yours may avoid none.

Reasoning models and caching: early measurements found reasoning-model caches rarely hit; current APIs keep the cache across prior thinking blocks on newer models, so measure cache-read tokens rather than assume either way.

## 6. Routing and cascades

- **Task-based routing** (per step): small model classifies, extracts and guards; strong model plans and answers. Start with cheap heuristics (task type, keywords) before a trained router. Learned routers trained on preference data have reported more than halving cost at equal quality on public benchmarks (RouteLLM, 2024); verify on your own traffic.
- **Cascade** (per input): try the small model, escalate on low confidence. With per-request costs c_small and c_large and a share s that stops at the small model, the cascade costs c_small + (1 − s) × c_large. It beats large-only only when **s > c_small / c_large**, and only if the confidence signal is validated against labelled outcomes (agreement across reruns or a separate checker beats self-reported confidence).
- **Risk-based routing** (per case): routine cases get a cheap mode (short context, few sources, templated output); a risk trigger detected in code (a missing critical field, conflicting instructions, sensitive data, any irreversible action) moves the run to careful mode, with deeper retrieval, stricter verification and mandatory approval [PRODGUIDE ch17 §Performance Tuning Without Breaking Reliability]. Task-based routing picks the model per step; risk-based routing picks the effort per case. It pays only when the triggers are reliable; otherwise everyone ends up in careful mode.
- **Judge it on cost per successful run**: (expected cost + repair cost + review minutes × value per minute) / success rate. A cheap model that produces invalid tool arguments can cost more than it saves, and a cheap mode that needs longer review can too.

## 7. Resilience is also cost policy

- **Retries**: an agent that succeeds 60% of the time reaches about 99% after five independent attempts, at about five times the tokens. If reliability comes from retries, put the retry rate in the cost model. Retry only transient errors (timeouts, 429, 5xx) with jittered backoff and a max; fail fast on client errors.
- **Timeouts are soft by default; hard ones must be designed.** A timeout that leaves the generation or tool running keeps billing. Cancel downstream work on timeout. Set each timeout from the measured p99 of that call (decode time grows with output length), not from a round guess: a timeout below the tail turns slow successes into paid retries.
- **Three breakers**: per dependency (stop calling an unhealthy service for a while), per session (cost or turn fuse that halts and hands off; a provider's account-level cap is far too coarse), per output stream (pause a component after N unusable outputs in a window).
- **Fallback model**: decided at design time and tested through the whole pipeline in CI. Structured output in tiers: provider strict-schema mode, local validation with a bounded re-ask carrying the error, and last, canonicalising onto the product's enums with conservative defaults. Valid JSON is not consistent decisions: check action-triggering fields (priority, refund amount) across runs and models.

## 8. Latency

Decompose p95, not the mean, into: model time (prefill, felt as time to first token, grows with prompt length; decode, one token at a time, bound by memory bandwidth), retrieval, tools, orchestration, and loop iterations. Agents are slow mostly because of sequential calls and long contexts.

Read distributions, not averages: report p50 and p95 per phase, log tool latency apart from model latency, and watch jitter (the spread of completion times), because operators feel the p95. Slow or unpredictable runs also cause failures: people re-run them, and timeouts trigger retries that can duplicate side effects [PRODGUIDE ch17 §Performance Tuning Without Breaking Reliability].

| Symptom | Lever |
|---|---|
| p95 far above p50 | Loop iterations and retries in the tail: cap steps, add tool timeouts that cancel, check the stop-reason mix of slow traces |
| Time to first token high | Shorter prompt, stable cached prefix, fewer tools offered per call |
| Many sequential calls | Merge steps; run independent reads in parallel (raises downstream peak load; avoid speculative fan-out under load). Before running hops in parallel, confirm from the data flow that neither consumes the other's output, carry trace context into worker threads (observability.md §1), then rerun the quality gate. At the extreme, parallel sub-agents cut research time by up to 90% while using about 15 times the tokens of a chat (Anthropic, 2025-06) |
| Trace shows a staircase of identical child spans | N+1 lookups: use the tool's batch call (tool shape: **agent-tool-designer**) |
| Long answers | Stream tokens; show progress |
| Work over about 30 s | Async job with ID, status, cancel and streamed progress over SSE or WebSockets; common gateways cut REST calls at 30 s (job and stream design: agent-harness-designer) |
| Inline checks slow | Guardrail budget about 10 ms regex, 50 ms embedding, 100 ms total; LLM checks go asynchronous unless they guard an irreversible action |
| Bursts | Rate limits per user or tenant, concurrency capped when tools slow down, bounded queues, priorities, explicit rejection or degradation ("a queue that grows without limits is a delayed failure") |
| Speed matters for some users only | Premium fast tiers only on paths where users wait |

## 9. Where each agent runs

Place each agent, not the whole system: the data a step touches decides sensitivity; its traffic decides load shape. This section places agents and checks capacity; the serving design itself (three layers, no inference on the request event loop, streaming, deployment shape by trigger) is agent-harness-designer's, and the readiness review scores it (checklist J6, J7).

| | Bursty load | Steady, high volume |
|---|---|---|
| **Open data** | Managed API behind a gateway (default start) | Managed API; consider a self-hosted lane for a narrow, high-volume step a small open model handles at your quality bar |
| **Restricted data** | Dedicated endpoint with isolated tenancy, or a regional/residency option | Your weights in your VPC (or on-prem when required) |

- Start on managed APIs behind a gateway that makes provider and model a config value. Move one agent only with a named reason: data that cannot leave, or a steady step whose GPUs you can keep busy. API cost rises smoothly with traffic; self-hosted cost rises in steps because GPUs come whole.
- Partition by sensitivity: a supervisor routing by category need not run where a retrieval agent reads raw PII.
- Count data gravity: inference on one cloud and vectors on another can cost more in egress per retrieval step than in inference.
- Separate services per agent only when load, owners or permissions differ; each hop adds latency and failure modes.
- **Peak capacity check** before any scale-up, per model: peak requests/min = the busiest day's requests ÷ 1,440 × peak-hour factor; model calls/min = that × expected calls per request on that model; input tokens/min = calls/min × average input tokens; output tokens/min likewise. The peak-hour factor is the busiest hour's traffic over the average hour's. Default 3, which assumes all traffic falls in an 8-hour working day (24 ÷ 8); replace it with the ratio measured from gateway logs or traces, and label it assumed until then. Per-minute limits also see bursts inside the busiest hour, so once traffic is traced, size from the measured p99 calls per minute plus burst headroom rather than from an hourly factor. On current Claude models cache reads do not count toward the input-tokens-per-minute limit, while cache writes and uncached input do (as of 2026-10), so compare uncached input plus cache writes with that limit; other providers may count all input. Some platforms also reserve `max_tokens` when a request starts and weight output tokens by a per-model multiplier, so the token check needs the platform's quota formula, not the bill (on AWS Bedrock, see [aws-implementation-notes.md](aws-implementation-notes.md), "Quota accounting on Bedrock"). Compare each with the provider's requests-, input-token- and output-token-per-minute limits for your tier, keep headroom for retries, and request increases early. A second route to the same model (another region or cloud endpoint) adds capacity and doubles as a fallback; regional endpoints may carry a price premium.

**Host the loop where it can finish.** The host's maximum execution time must exceed the agent's capped latency ceiling (`cost_model.py` prints it) plus the async-job path. Otherwise runs die mid-loop, possibly right after a write. Serverless functions suit short, event-driven steps (hard timeout, cold starts). A container service suits long, steady agents: no time limit, health checks, autoscaling on queue depth or latency. A managed agent runtime gives session isolation and long sessions with consumption pricing. For an SLA, require health checks that replace unhealthy instances, autoscaling on an agent signal, and at least two availability zones (checklist J5).

**If you self-host** (sizing rules, as of 2026-10; measure on your hardware):
- Weights: parameters × (bits ÷ 8) × 1.2 for overhead; an 8B model at 16 bits is about 19 GB. Measured usage runs higher with cache and batch memory.
- KV cache bytes = sequence length × layers × KV heads × head dim × 2 × bytes per value. A 7B-class model with 28 layers, 4 KV heads of dim 128 at 16 bits holds about 56 KiB per token: one 32,000-token agent context is about 1.75 GiB. Size concurrency from this at real context lengths, not from parameter count.
- Cold start: a measured first request after deploy took about 125 s against 0.28 s warm. Keep weights on persistent storage and a warm minimum where latency matters. With adapters, pin the base model to an immutable revision, mirror it to your own storage and measure cold start with the base load included (adapter lifecycle: **agent-model-selector**).
- Prefix caching on. Expect a cache-invalidation tax when the system prompt changes or fresh context is injected early.
- Quantization saves 4 to 8 times memory with a task-dependent accuracy loss; 8-bit can be slower than 16-bit without kernel support. Evaluate the quantized checkpoint on your tasks; prefer the model developer's own quantized releases.
- Speculative decoding helps per-token latency on memory-bound servers at low to moderate load and shrinks as batches fill; a draft model untuned for your domain can make it slower. Measure acceptance rate on your traffic; another replica may be cheaper.
- vLLM, SGLang and TGI expose OpenAI-compatible APIs: keep the backend a config choice.
