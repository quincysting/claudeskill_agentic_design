# AWS implementation notes

AWS mapping for this skill's principles. As of 2026-10; services change, verify before use.

The principles live in the other reference files and stay vendor-neutral. This file only says where each one lands on
AWS (Amazon Bedrock AgentCore Runtime, Gateway, Identity and Policy, plus IAM, CloudTrail and CloudWatch) and what went
wrong in practice. Tags: **(docs)** confirmed in AWS documentation on 2026-10-11; **(lab)** seen in hands-on practice
only; **(unverified)** neither, so check it before relying on it.

## Mapping

| Principle (skill section) | AWS feature or setting | Gotcha |
|---|---|---|
| Per-agent identity ([controls-catalog.md](controls-catalog.md) §3) | AgentCore Identity workload identities: created automatically for agents on AgentCore Runtime, created explicitly through the control-plane API for self-hosted agents (lab) | Scope the host's role so it can fetch tokens only for its own workload identity (lab) |
| Verified, not asserted, identity (§3) | Custom JWT inbound authorizer on Runtime and Gateway: discovery URL, allowed audiences, allowed clients, allowed scopes, custom claim matches (docs for the fields; claim-match syntax lab) | Invoke and token calls that take a user ID as a plain string are asserted identity. Remove the IAM permission for them and add an explicit deny (lab) |
| What a receiver checks (§3) | The authorizer checks audience, client, scope and custom claims before the request reaches agent code (docs) | The token itself reaches agent code only if `Authorization` is on the runtime's request-header allowlist (docs). Code that decodes claims without verifying is safe only while every runtime version and endpoint keeps the authorizer |
| Entry-point inventory (SKILL.md Step 3) | Inbound auth is configured per runtime version; named endpoints pin versions (lab) | An old version or a second endpoint can lack the authorizer. Scope invoke rights to the runtime and the named endpoint, not the runtime alone (lab) |
| Gateway inbound auth ([mcp-hardening.md](mcp-hardening.md) §3) | Types: JWT, IAM, or offloaded (authenticate only, or no authorization) (docs). The condition key `bedrock-agentcore:GatewayAuthorizerType` can forbid no-auth gateways across the organisation (docs) | Without inbound auth the policy engine has no principal: identity-aware rules are impossible and session limits are shared by every caller (docs). The lab found the type couldn't be changed after creation (lab; not confirmed for Gateway in docs) |
| Make the gate unavoidable (§2) | Runtime targets: restrict invocation to the gateway's workload with the authorizer's allowed-workload configuration or a resource policy (field confirmed in docs; using it to admit only the gateway is inferred, unverified). Lambda targets: grant invoke permission only to the gateway's role (unverified; standard Lambda practice, not lab-tested) | List every principal with invoke rights on each target, not just the gateway |
| Policy gate (§2) | Policy in AgentCore: a Cedar policy engine attached to a gateway. Default deny, forbid wins; principals from the JWT `sub` (claims as tags) or an IAM identity; schema generated from tool definitions (docs). Action named `<target>___<tool>`, resource is the gateway, arguments under `context.input` (lab) | Numbers are decimals, not floats; string patterns are wildcards only (lab). Policy evaluation covers MCP tools only: prompts and resources pass whatever the mode (docs) |
| Declarative engine semantics (§2) | Cedar skip-on-error: a policy whose condition errors is ignored (confirmed in the Cedar documentation, 2026-10-11) | A forbid that reads an optional argument the caller left out never fires. Mark such fields required in the tool schema or test for presence in the rule |
| Shipping a gate rule (§2) | Engine attachment mode `LOG_ONLY` / `ENFORCE` (docs); per-policy log-only or active state (lab); strict or permissive validation, natural-language authoring, automated analysis for always-allow and always-deny rules (docs) | Policy creation is asynchronous. Poll each policy to a terminal state; one can end `CREATE_FAILED` after the submit succeeded (lab) |
| Rule really in force (§2) | Gateway execution role and the role that manages policies (docs) | Without `GetPolicyEngine` on the gateway role, log-only evaluation fails silently; the role that creates policies needs `InvokeGateway` or creation fails (docs) |
| Protect the controls themselves (§10) | `bedrock-agentcore:UpdateGateway` (docs) | That one permission can switch enforcement from `ENFORCE` to `LOG_ONLY` or set the policy engine to null, and no condition key protects the mode field (docs). Hold it in a separate role and alarm on every `UpdateGateway` call in CloudTrail |
| Configuration drift (§10) | `update-agent-runtime` replaces the whole configuration and publishes a new version (lab) | Fields you don't resend (authorizer, header allowlist, environment) are dropped. Build updates from a fresh read of the current config and diff the security fields after deploy (lab) |
| Content checks on arguments ([guardrails.md](guardrails.md) §4) | Guardrail conditions inside policies (prompt attack, content filter, sensitive information) on tool input fields, and on output with a suppress-output effect (lab) | Not checked against docs (unverified). Tune thresholds in log-only mode first |
| Flow rules: order and session caps (§2 step 6) | Temporal policies over a policy session: call caps, "tool B only after tool A", no external calls after a sensitive read (docs) | Per-caller isolation needs an authenticated gateway; sessions expire after 24 hours idle; the caller identity chain propagates Gateway → Runtime → Gateway within one account and Region (docs). The caller generates the policy session ID and sends it in a header, so a per-session cap bounds one session, not a customer or principal (docs). Limits per customer, per order or per day are aggregates; enforce them in the handler against the system of record |
| Tool visibility | `tools/list` shows a tool if any circumstance could permit the call (docs) | A listed tool can still be denied. The list is not an authorization result |
| Delegation chains (§3) | Either agent code performs the RFC 8693 exchange against the identity provider (lab), or the AgentCore Identity OAuth credential provider brokers on-behalf-of exchange (RFC 8693 or RFC 7523), so code never handles the inbound token or the client secret (docs) | A JWT pass-through outbound option appears in docs search results (unverified). Treat it as token pass-through ([threat-catalog.md](threat-catalog.md) T8) unless the receiver is your own audience-checking runtime |
| Broker, outbound SaaS (§3) | OAuth2 credential provider with a token vault and a user-consent flow from the SDK (SDK names unverified) | Ask for read scopes where the task allows |
| Credential issuance audit (§10) | CloudTrail data events for workload-identity token calls, selected with advanced event selectors (lab) | A trail whose selectors ask only for data events stops logging management events (lab). The JWT subject is written to CloudTrail, so keep PII out of `sub` (docs) |
| Identity alerts (§10) | Identity metrics in the AgentCore CloudWatch namespace, including `WorkloadAccessTokenFetchFailures` (docs); log metric filters with a default value of 0 (lab) | Without the zero default the alarm sits in "insufficient data" instead of OK |
| Browser session audit ([sandboxing.md](sandboxing.md)) | Session recording to S3 from a custom browser tool (unverified) | Add Object Lock to the bucket and keep CloudTrail for who started each session |
| Calling a JWT-protected runtime | The AWS SDK signs every request with SigV4 (lab) | Bearer-token callers use plain HTTPS with an `Authorization` header and a session-ID header (lab) |
| Denials return a reason (§2) | AWS docs show a policy denial as a tool result with `isError` set and the reason in text (docs) | The lab saw a JSON-RPC protocol error over HTTP 400 instead (lab). Check what your client passes to the model, and parse 4xx bodies in smoke tests |

## Gotchas the labs hit

### Default deny breaks reads first

Turning enforcement on with only the rules for risky tools blocked every read tool too. Give each tool an explicit
permit before switching the attachment to enforce, and keep an allow case per tool in the smoke test.

### Log-only looks like a working gate

In log-only mode the decision logs still show "would have denied", so dashboards look healthy while nothing is
enforced. Alarm on the mode itself, not only on denials. The same permission that edits the gateway can switch the
mode or detach the engine.

### Created is not active

A policy submission can succeed and the policy still end in a failed state, for example when its action names a tool
the gateway doesn't expose. Treat deploys as done only when every policy reports active and appears in decision logs.

### Asserted identity in invoke and token calls

Calls that accept "act for user ID X" trust whoever holds the IAM permission. Replace them with the JWT authorizer, then
add an explicit IAM deny on the old calls so a later broad allow can't reopen them.

### Full-replace updates

Updating a runtime with only the fields you meant to change silently removed the rest, including the authorizer and the
header allowlist, and the result became a new version. Read the current config, change it, send all of it, then diff.

### Data events and management events on one trail

Adding data-event selectors for token issuance can switch off management events on that trail if the selector set
names only data events. Check both categories after the change.

## Sources

AWS documentation pages confirmed on 2026-10-11:

- Policy enforcement modes: https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/policy-enforcement-modes.html
- Policy core concepts: https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/policy-core-concepts.html
- Policy sessions and identity propagation: https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/policy-session-based-temporal.html
- Use a gateway with Policy: https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/use-gateway-with-policy.html
- Gateway and Policy IAM permissions: https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/policy-permissions.html
- Gateway inbound authorization: https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/gateway-inbound-auth.html
- Runtime inbound and outbound auth: https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-oauth.html
- Runtime custom headers: https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-header-allowlist.html
- On-behalf-of token exchange: https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/on-behalf-of-token-exchange.html
- Identity observability metrics: https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/observability-identity-metrics.html
