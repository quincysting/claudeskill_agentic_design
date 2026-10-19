# Sizing: estimating at volume and reliability arithmetic

Citation keys such as [DEFGUIDE ch5] point to the book list under Sources in SKILL.md.

Sizing is a design decision. It shows whether a shape is affordable before anyone builds it: model calls per path decide between workflow and agent, tokens per case decide whether a split into several agents still fits the budget, and run duration against the latency target decides sync or async. The results fill section 8 of the design doc. Runtime capacity (workers, streams, per-client limits) is in the agent-harness-designer skill's serving-and-deployment.md; production tuning belongs to agent-ops-reviewer. Put assumptions next to every figure.

## Estimating at volume

1. **Tokens per path.** For each model call: input (system prompt + tool definitions + assembled context + documents) and output (including reasoning tokens, billed as output). Multiply per-document calls by documents per case. Report typical and worst case.
2. **Peak load.** Daily volume → peak arrivals per minute. Measure the peak hour from history; if unknown, assume arrivals within business hours with a 2× peak-hour factor and label it (this skill's convention). The factor applies to interactive traffic; batch work is smoothed over its window, so size it by volume over that window.
3. **Concurrency.** Runs in flight ≈ arrival rate × average run duration (Little's law). Size workers and connection pools from it.
4. **Rate limits.** Required requests per minute = peak arrivals × calls per case; required tokens per minute = peak arrivals × tokens per case. Compare with the provider tier's limits (check current values). A queue absorbs bursts; expected wait ≈ backlog ÷ throughput, which must fit the SLA.
5. **Caching.** Put stable content (system prompt, tool definitions, policy text) first so the provider's prompt cache can reuse it; cached input is cheaper and faster (check current pricing). Changing tools or thinking settings between calls invalidates the cache.
6. **Cost.** Tokens × current prices per model role. If prices are unknown, stop at tokens and calls and say so.
7. **External limits.** Some limits are not yours to raise quickly: sender reputation and domain warm-up for outbound email, third-party API quotas and pricing tiers, vendor onboarding. They often cap volume below what the design could run. Size the ramp from them and list them with their lead times.
8. **Against the incumbent.** For human labour, compare per case: today's handling minutes × loaded hourly rate, against model and infrastructure cost plus the review and approval minutes the design still needs. Compare error and rework rates too. The business case itself goes to agentic-business-case.

## Reliability arithmetic (direction, not prediction)

Chain of n steps, each succeeding independently with probability p: success = p^n. At p = 0.98, ten steps ≈ 0.82 [DEFGUIDE ch5].

A gate catching fraction v of failures and allowing recovery raises effective per-step success to p + (1 − p)·v. At p = 0.98, v = 0.9: 0.998 per step, ≈ 0.98 over ten steps [DEFGUIDE ch5].

Real errors are not independent (they cluster on hard decisions), so use the numbers for direction. What survives: adding steps without checks makes things worse; the gain comes from catching errors at boundaries; a step moved into code does not compound. The same arithmetic for chains of agents is in multi-agent.md, "Reliability arithmetic for chains of agents".
