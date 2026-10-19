# AWS implementation notes

AWS mapping for this skill's principles. As of 2026-10; services change, verify before use.

Load this when the agent runs on AWS. The principles live in the other reference files; this file only says which AWS feature or setting carries each one and where the labs tripped. Items marked "(unverified)" were seen in practice labs or inferred, but not confirmed against current AWS documentation. The lab notes are anonymised observations from the author's own hands-on labs and contain no client data; treat a lab-only point as unverified until you have checked it against the documentation.

Steps below that act on a live account (sending a test request, updating a runtime's configuration) are for you to propose to the user and run only after they confirm, with the permissions they choose.

## Mapping

| Principle (skill section) | AWS feature or setting | Gotcha |
|---|---|---|
| One trace per request, spec names, custom `app.*` attributes (observability.md §1 to §2; checklist B1 to B6) | AWS Distro for OpenTelemetry (ADOT): the Lambda layer, or the auto-instrumentation launcher in containers; X-Ray and CloudWatch as the backend | ADOT sets up the provider, the exporter and AWS SDK child spans; you add only the custom spans and attributes. On AgentCore Runtime the runtime owns span delivery, so don't add your own OTLP exporter |
| Token counts in the spec's meaning (observability.md §2; cost-latency.md §2) | Bedrock Converse usage fields: `inputTokens`, `outputTokens`, `cacheReadInputTokens`, `cacheWriteInputTokens` | `inputTokens` excludes cached tokens. Set `gen_ai.usage.input_tokens` to the sum of the three input fields (see "Token fields on Bedrock") |
| Log inside the span; join logs on trace ID (observability.md §1) | One CloudWatch Logs Insights query across the agents' log groups, filtered on trace ID | A log line written after the span closed carries an empty trace ID and drops out of the join |
| Online scorers have no reference (observability.md §5; checklist E6) | AgentCore Evaluations: online (sampled live sessions), on-demand (named spans or traces), batch (curated sessions) | Ground truth (expected response, assertions, expected tool trajectory) works in batch and through the on-demand Evaluate API; online scoring of live sessions is reference-free. A trace sent without an expected response is scored in the evaluator's reference-free mode with no error, and fields an evaluator does not use come back in `ignoredReferenceInputFields`, so check which mode produced a score. The built-in LLM-judge evaluators are generic: calibrate before gating (agent-eval-designer) |
| Trace-based scoring needs the spans (observability.md §3, settings by environment) | AgentCore Observability writes spans to a dedicated stream in the runtime's log group | Online evaluators score only sessions whose spans arrived. Transaction Search indexing percentage is set separately from span ingestion (unverified); check what your evaluators read |
| Rate alarms with a floor, per segment, validated (observability.md §6; checklist D3) | CloudWatch metric filters on JSON log fields (numerator and denominator), metric math, `SEARCH` expressions for per-dimension graphs, "datapoints to alarm" | "Treat missing data as not breaching" stops alarms on zero traffic, not on low traffic. Add the `IF` floor and require two breaching datapoints |
| Cost attribution and reconciliation (cost-latency.md §2, "Attributing cost"; checklist I3) | Cost and Usage Report (prices each token type separately); a CloudWatch metric with low-cardinality dimensions; application inference profiles with cost-allocation tags for per-application or per-tenant cost (unverified) | Cross-region inference may increase cache writes |
| Cache churn (cost-latency.md §5; checklist I4) | Bedrock prompt caching (cache points); cache read and write token counts per call | Cache writes can be billed above the standard input rate, depending on the model. Cache multipliers for Amazon Nova models (unverified): never copy another model family's ratios into `cost_model.py` |
| Batch tier (cost-latency.md §3, §4 lever 6) | Bedrock batch inference | Prompt caching is not supported with batch inference, so the two discounts don't stack |
| Versioned prompts and configs (observability.md §7; checklist F1) | A config store with versions, such as Systems Manager Parameter Store (select by version number or label) | A prompt read as "latest" on every call can mix two versions inside one eval batch or canary. Pin the version and put it on the trace |
| Canary and rollback (observability.md §7; checklist G2, G3) | AgentCore Runtime versions and endpoints | Every update creates a new version, and the default endpoint moves to it automatically. For canary and rollback, use a named endpoint pinned to a version (per-endpoint pinning unverified) |
| Config survives a deploy; kill switch without a redeploy (checklist F1, G5, G6) | AgentCore Runtime update call | The update replaces the environment-variable map wholesale: read, merge, write, or variables such as model IDs disappear. Each update also creates a new runtime version, so a kill-switch flag kept in an environment variable flips only through a redeploy. Keep the draft-only and abort flags in a store the gate reads at every call, such as a parameter or a table (inferred from the versioning behaviour; unverified) |
| Model endpoint swap goes through a canary (SKILL.md release table; checklist F7) | SageMaker production variants with traffic weights, or deployment guardrails with canary or linear shifting and alarm rollback (unverified) | Editing one environment variable that points callers at a new endpoint is a hard cutover with no gate, shadow or canary |
| Smoke test per tool after deploy (observability.md §7; checklist G6) | AgentCore Gateway targets | A target wired to the wrong backend showed as ready and answered with another domain's data |
| Peak capacity check against provider limits (cost-latency.md §9, "Peak capacity check"; checklist J3) | Bedrock tokens-per-minute and tokens-per-day quotas; runtime metrics `InputTokenCount`, `CacheWriteInputTokenCount`, `CacheReadInputTokenCount`, `OutputTokenCount` | Quota use is not billed tokens. Bedrock reserves input plus `max_tokens` when a request starts and settles at `InputTokenCount + CacheWriteInputTokenCount + OutputTokenCount × burndown rate`; cache reads don't count. The burndown rate depends on the model (see "Quota accounting on Bedrock") |
| Host matches the run (cost-latency.md §9; checklist J5) | Lambda (hard 15-minute maximum per invocation); ECS on Fargate (no time limit, health checks, autoscaling); AgentCore Runtime (session isolation, long sessions, consumption pricing) | A loop whose capped latency ceiling exceeds 15 minutes cannot live in one Lambda invocation |
| Telemetry routes in private networks (observability.md §2, "confirm a span arrives") | VPC interface endpoints for CloudWatch Logs, X-Ray and the agent service | Without them, spans from a runtime in private subnets are dropped with no error |

## Token fields on Bedrock

The Converse API reports input in three parts. Normalise once, in the adapter:

```python
def otel_usage(usage):  # Bedrock Converse "usage" object -> OTel GenAI attributes
    read = usage.get("cacheReadInputTokens", 0)
    write = usage.get("cacheWriteInputTokens", 0)
    return {
        "gen_ai.usage.input_tokens": usage["inputTokens"] + read + write,  # spec: all input
        "gen_ai.usage.output_tokens": usage["outputTokens"],
        "gen_ai.usage.cache_read.input_tokens": read,
        "gen_ai.usage.cache_write.input_tokens": write,
    }
```

Cost then uses `inputTokens` as the uncached part, with reads and writes priced at their own multipliers. Test the adapter with a response that carries all three counts.

## Quota accounting on Bedrock

Bedrock counts quota differently from billing, so the peak capacity check (cost-latency.md §9) needs its own arithmetic.

- **When a request starts**, Bedrock deducts its input tokens plus `max_tokens` from the tokens-per-minute and tokens-per-day quotas, and throttles the request if that is more than what is left. In the docs' worked example this reservation counts uncached input and cache writes, not cache reads.
- **When it ends**, the request settles at `InputTokenCount + CacheWriteInputTokenCount + OutputTokenCount × burndown rate`, and the unused part of the reservation goes back to the quota. `CacheReadInputTokenCount` is not counted. Billing still uses the actual tokens.
- **The burndown rate depends on the model and model version.** The docs' Claude Sonnet 4 example uses 5, and the page lists higher rates for some newer models. Read the current rate for the exact model on the burndown page and date it; never carry one model's rate over to another. Models served only on the `bedrock-mantle` endpoint have separate input and output quotas, and burndown does not apply to them.
- **Peak check per model.** Settled use per minute = (uncached input + cache write) tokens/min + output tokens/min × burndown rate. Reserved use per minute, the admission check = (uncached input + cache write) tokens/min + calls/min × `max_tokens`. Neither is an upper bound on the other: settled use exceeds the reservation whenever output × burndown rate is larger than `max_tokens`. Size the quota on the larger of the two, with headroom for retries. At a rate of 5, for example, 350,000 output tokens a minute use 1.75M quota tokens a minute. If the settled figure fits and the reserved one does not, look at `max_tokens` before asking for a quota increase.
- **Set `max_tokens` above the observed maximum output** of each step (from `OutputTokenCount` or the traces), with a margin, not at the model's maximum and not at the p99: a cap at the p99 cuts off about one response in a hundred, tool-call JSON included. Treat a `max_tokens` stop as a failure in the trace and the alerts. Keep `max_tok_out` in `cost_model.py` equal to the `max_tokens` you set, so the capped ceiling and the quota check use the same cap.

## Instrumentation and span delivery

- On Lambda, use the ADOT layer; in containers, use the auto-instrumentation launcher. Both configure the exporter and AWS SDK spans.
- On AgentCore Runtime, the runtime ships spans. A unified-traces option routes spans into the agent's own runtime log group and needs a recent ADOT distro version (the lab used 0.18 or later; current minimum unverified).
- Runtime containers are linux/arm64 and serve the platform's invocation and health routes.
- Propose one test request (run it only after the user confirms) and check that the span lands in the expected log stream before building dashboards or online evaluators on it.

## Alarm math in CloudWatch

- Turn JSON log fields into two metrics with metric filters: bad turns and turns.
- Rate expression with a floor: `IF(turns >= N, 100 * bad / turns, 0)`, with N from the interval table (observability.md §5).
- Alarm on two of two breaching datapoints. Keep "missing data: not breaching" for zero-traffic periods; the floor handles low traffic.
- Graph cost per agent or tier with a `SEARCH` expression over the low-cardinality cost metric; never add session IDs as dimensions.

## Runtime releases

- Each AgentCore Runtime update creates a version, and the default endpoint follows it, so callers on the default endpoint get every update at once. Keep production callers on a named endpoint pinned to the released version, and point a canary share at a second endpoint on the candidate (whether the platform can weight traffic across endpoints natively is unverified; otherwise split in your gateway).
- An update must read the current configuration, merge the change and write the whole map back; a partial update drops the rest. Propose the merged configuration to the user and apply it only after they confirm.
- Release the prompt the same way when it lives in a parameter: new parameter version, then gate, then canary.

## Repo-only reviews of AWS-hosted agents

A repository shows the build spec and the code, not the console. In a code-only review (checklist, "Missing evidence"), tag what lives only in the account as inferred or list it in the discovery plan: environment variables set in the console, IAM policies attached outside the repo, log retention, and the hosting service's own timeouts.

- **Log retention.** A CloudWatch Logs log group created on first write keeps its data with no expiry until someone sets a retention period (as of 2026-10). A group that receives prompts, retrieved chunks or answers and has no retention in the repo's infrastructure code keeps customer text indefinitely (checklist C1, C4).
- **Execution timeout.** Managed web hosting that runs server-side routes has its own request timeout, often far shorter than Lambda's 15 minutes; read the current limit on the service's quota page and compare it with the capped latency ceiling (checklist J5; per-service limits unverified here).
- **Secrets at build time.** A build step that writes secrets into a `.env` file puts them into the build artifact. Read them at runtime from Secrets Manager or Parameter Store instead, and cite any found by file:line and kind only.

## Managed RAG services

- **Knowledge base ID from config.** The knowledge base or index ID passed to the retrieval call comes from server configuration, never from the request body (checklist K9). Scope the IAM policy to that knowledge base and the model ARNs the agent calls; a full-access managed policy turns a client-supplied ID into access to every knowledge base in the account.
- **Empty retrieval.** When retrieval returns nothing, report "no context found" so the answer path can refuse or hand off instead of answering ungrounded.
- **Cost.** Retrieved chunks are input tokens on the generating call; count them in `tok_in`. The vector store behind a managed knowledge base can carry a minimum hourly capacity charge that bills at zero traffic (unverified for current minimums; check the store's pricing page); count it as fixed cost, outside `cost_model.py`.
