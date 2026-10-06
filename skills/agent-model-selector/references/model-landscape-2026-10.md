# Model landscape snapshot, as of 2026-10

Everything in this file goes stale. Prices and model names were read from provider pages on 2026-10-06; experiment numbers come from books whose runs used mid-2025 to early-2026 models. Use this file to shortlist candidates and set expectations. Do not quote it to a user as current without re-checking, and put a date next to every number you hand back.

## How to refresh (do this before recommending a named model)

1. Open each candidate provider's model overview, pricing and deprecation pages. Record the model ID, input and output price per million tokens, cached-input price, context window, max output, thinking or effort controls, and retirement date.
2. Check whether the provider still offers fine-tuning for that model and which methods (SFT, DPO, RL). These menus change more than anything else (see below).
3. For open-weight candidates, check the licence text for use restrictions and terms on training with other models' outputs.
4. Replace the examples in your plan with the refreshed names. Keep the role classes ("small fast model", "frontier model") in the plan so it still reads correctly after the names change.

## Anthropic lineup (provider overview page, fetched 2026-10-06)

| Model | API ID | Input / output per MTok | Context | Max output | Thinking | Default effort | Retirement not before |
|---|---|---|---|---|---|---|---|
| Claude Fable 5.1 | `claude-fable-5-1` | $10 / $50 | 1M | 128K | Adaptive, always on | high | 2027-09-01 |
| Claude Opus 5.5 | `claude-opus-5-5` | $4 / $20 | 1M | 128K | Adaptive, always on | medium | 2027-09-22 |
| Claude Sonnet 5.5 | `claude-sonnet-5-5` | $2 / $10 | 1M | 128K | Adaptive | high | 2027-09-28 |
| Claude Haiku 4.5 | `claude-haiku-4-5-20251001` | $1 / $5 | 200K | 64K | Extended (manual budget) | effort not supported | not sooner than 2026-10-15 (active; no retirement notice as of 2026-10-06) |

Notes from the same page: batch requests are 50% off; cache reads cost 10% of base input (5% on Opus 5.5, 2.5% on Fable 5.1). The provider's own advice is to start with Opus 5.5 for most workloads and move to Fable 5.1 when evals at higher effort still fall short. That matches this skill's reference rule: with no incumbent, the provider's recommended general model (Opus 5.5 here) is the reference, and the top tier (Fable 5.1) is a probe for roles that miss their target. Haiku 4.5 is active; its retirement commitment is "not sooner than 2026-10-15" and no retirement notice had been issued on 2026-10-06. Check the deprecations page before building a long-lived plan on it. Data residency: the same page says Amazon Bedrock offers regional endpoints with guaranteed data routing (as well as global endpoints) for Claude Sonnet 4.5 and later, and Google Cloud offers regional and multi-region endpoints; cloud platforms set their own model lifecycle dates. Confirm region availability per model before promising residency.

## Where the savings come from when one vendor's tiers are close (2026-10)

On 2026-10-06 the current Anthropic lineup had no small tier with a long runway: Haiku 4.5 ($1/$5) was the only one, with a retirement commitment of "not sooner than 2026-10-15", and no successor was listed. Sonnet 5.5 is half Opus 5.5's list price, so a within-vendor step down saves at most about 50% per call before effort changes. Larger savings, roughly in order of effort:

1. **Effort.** Lower effort cuts reasoning and output tokens on the same model; often the biggest single lever for classification and tool calls.
2. **Batch and cache.** Batch requests were 50% off for roles that tolerate delay (offline classification, nightly summaries); cache reads cost 10% of base input or less.
3. **Another vendor's small tier.** On the same date OpenAI listed nano and low-cost tiers at $0.05 to $0.20 per million input tokens (table below). Check data-processing terms, regions and confidentiality constraints first; a second vendor is also a second dependency.
4. **Self-hosted open-weight models or encoders.** No per-token price; cost is GPU time plus operations, and data stays inside your boundary, which often settles confidentiality constraints. Classes and 2025 examples are listed below; refresh the names.
5. **Code.** Steps a rule can do cost nothing per call.

## Effort and thinking controls (Anthropic effort docs, fetched 2026-10-06)

- Levels: `low`, `medium`, `high`, `xhigh`, `max`, set per request. Not every model supports every level.
- Effort applies to all output tokens, not only thinking. Lower effort makes fewer and terser tool calls and may skip thinking on easy inputs; it is a behavioural signal, not a hard token cap.
- Fixed thinking budgets (`budget_tokens`) are deprecated on the 4.6 generation and not accepted on later models; adaptive thinking steered by effort replaces them. On Opus 5.5 thinking cannot be disabled. On Sonnet 5.5 the lowest setting is thinking only between tool calls.
- Changing top-level effort between requests invalidates the prompt cache. Newer models accept a per-message effort change (beta) that keeps the cache. Pick one level per conversation otherwise.
- The provider's documented advice for its newest models is to run an effort sweep on your own evals instead of carrying settings over from an earlier model, because levels are recalibrated between generations.
- Related API changes recorded in the study guide (2026-10): non-default `temperature`, `top_p` and `top_k` return errors on Claude Opus 4.7 and later, and the tokenizer introduced with Opus 4.7 uses roughly 1 to 1.35 times as many tokens for the same text. Re-measure token budgets after a generation change.

Self-hosted open-weight reasoning models (Qwen3 family and similar) expose a thinking on/off switch in the chat template and can be budget-forced: cap reasoning tokens, then append an end-of-thinking marker so the model answers.

## OpenAI examples (pricing page, fetched 2026-10-06)

| Tier on the page | Example IDs | Input / output per MTok |
|---|---|---|
| Flagship | `gpt-6-astra` | $10 / $50 |
| Flagship | `gpt-6.1-sol` | $2 / $10 |
| Low-cost | `gpt-6-luna` | $0.10 / $0.50 |
| Mini | `gpt-5.4-mini`, `gpt-5-mini` | $0.75 / $4.50; $0.25 / $2.00 |
| Nano | `gpt-5.4-nano`, `gpt-5-nano` | $0.20 / $1.25; $0.05 / $0.40 |

**Hosted fine-tuning is shrinking.** The same page states that OpenAI is winding down its fine-tuning platform: it is closed to new users, existing users can create jobs "for the coming months", and tuned models stay available until their base models are deprecated. A plan that depends on vendor-hosted tuning of a closed model needs a fallback (open-weight model with LoRA, or another provider) and a migration date.

## Open-weight and small-model classes seen in the books (2025 to early 2026)

| Class | Examples the books used | Typical role | Note |
|---|---|---|---|
| Encoder, about 350M parameters | ModernBERT | Classification, filtering, scoring, embeddings | No generation loop; cheap, fast, gives class probabilities |
| Small or mid decoder | gpt-oss-20b, Qwen3 8B to 32B | Tool calling, extraction, routing | Many support thinking on/off |
| Mixture of experts | Qwen3-30B-A3B (30B loaded, about 3B active per token) | Throughput at mid capability | Memory sized by total parameters, speed by active ones |
| Large open | gpt-oss-120b, models above 200B | Near-frontier tasks, self-hosted | Self-hosting has real operations cost |

Price band quoted in one book (early 2026): up to $150 input and $600 output per million tokens for the most expensive closed reasoning model of the time, against about $0.30 and $3 for open models above 200B parameters on low-cost hosts. Use it only as an order-of-magnitude reminder that per-role choices can move cost by two orders of magnitude.

## Dated evidence worth knowing (numbers are not portable; the method is)

| Finding | Models and date | Use it for |
|---|---|---|
| Tool selection among 15 shuffled tools, roughly 60 to 75 one-line requests, 774 to 1,002 scored runs per setting: more reasoning never raised accuracy by more than a point, latency rose every time, gpt-oss models were worst at high effort (e.g. gpt-oss-120b 98.9% low, 96.6% high) | Claude Opus 4.1, Sonnet 4, Qwen3 32B, gpt-oss-20b/120b; mid-2025 | Default tool-caller effort to off or low; sweep before raising |
| Reasoning effort on 30 HLE questions and on MathQA: no consistent accuracy gain; on MathQA the best Claude model did best with reasoning off; median latency about 7.5 s off versus 12.5 to 15 s on | Claude Sonnet 4, Opus 4, o4-mini; mid-2025 | Effort is an experimental variable per task family |
| SWE-bench Verified, 4,018 trajectories: more "overthinking" correlated with fewer resolved issues; o1 high effort 29.1% for about $1,400 versus low effort 21.0% for about $400 | o1 and others; early 2025 (Cuadron et al.) | High effort can pay on hard agentic coding, at a steep price; measure |
| SQL generation bake-off, six models, one fixed prompt: best model 57.5% at a median cost 28 times the next most expensive; a 7B open model 18.9% | Gemini 2.5 Pro and others; mid-2025 | Template for a bake-off: accuracy, executes-at-all rate, latency, cost |
| Star-rating classification (about 173K training examples): fine-tuned GPT-4.1, GPT-4.1-Nano and ModernBERT all about 73%, well above prompted baselines; ModernBERT's calibration error 1.7 times lower; tuning cost about $122, $7.33 and about $1 of GPU time | 2025 | Fixed-label, high-volume classification favours a fine-tuned small model or encoder |
| Small models for agents: estimate that 40% to 70% of calls in three open-source agents could move to models under about 10B parameters; 10K to 100K examples per task as a tuning rule of thumb | NVIDIA position paper, 2025-06, revised 2026-09 | Upper bound on what stepping down might save; estimates, not measurements |
| LoRA matches full fine-tuning for small and medium SFT datasets and for policy-gradient RL even at rank 1; falls behind when data exceeds adapter capacity; best LoRA learning rate about 10 times the full-tuning one; apply to all layers, especially MLP | Thinking Machines, 2025-09 | Default to LoRA for SFT and RL on open models |
