# AWS implementation notes

AWS mapping for this skill's principles. As of 2026-10; services change, verify before use.

The principles live in the other reference files and stay vendor-neutral. This file only says where each one lands on
AWS (Amazon Bedrock AgentCore Gateway, Policy, Runtime and Identity, plus IAM, Lambda, DynamoDB and Neptune) and what
went wrong in practice. Tags: **(docs)** confirmed in AWS documentation on 2026-10-11; **(lab)** seen in hands-on
practice only; **(unverified)** neither, so check it before relying on it.

## Mapping

| Principle (skill section) | AWS feature or setting | Gotcha |
|---|---|---|
| Names fit the final budget ([tool-design-rules.md](tool-design-rules.md) §2) | AgentCore Gateway exposes each tool as `<target>___<tool>` (three underscores) (lab) | The prefix counts toward the 64-character budget, and Policy actions use the same prefixed name (lab). Keep target names short |
| Protocol version ([current-facts-2026-10.md](current-facts-2026-10.md), "Managed MCP gateways") | The gateway's supported MCP versions setting (lab) | The lab gateway negotiated an older MCP revision by default, and a client helper failed although auth worked (lab; default not confirmed in docs). Set the versions explicitly |
| Refusals as tool errors (tool-design-rules §5) | A Policy denial: AWS docs show a tool result with `isError: true` and the reason in text (docs) | The lab saw a JSON-RPC error over HTTP 400 instead (lab). Check what your client passes to the model, and parse 4xx bodies in smoke tests. Don't treat the lab's error code as standard |
| A gateway adds a layer; handlers keep state checks (tool-design-rules §7) | Policy in AgentCore: a Cedar policy engine attached to a gateway; default deny, forbid wins (docs). Action is the prefixed tool name, resource is the gateway, arguments are under `context.input` (lab) | A permit conditioned on a status argument the model supplies is advisory. The Lambda or runtime behind the tool still reads the record and checks it (lab practice the skill flags) |
| The schema is the policy contract (tool-design-rules §3) | The Policy schema is generated from the gateway's tool definitions (docs); argument types follow each tool's JSON schema (lab) | Numbers are decimals, not floats; string patterns are wildcards only (lab). A rule that reads an optional argument the call left out may not apply, so mark fields that rules read as required (unverified; follows from Cedar's skip-on-error semantics) |
| Make the gate the only route (tool-design-rules §7) | Lambda targets: grant invoke permission only to the gateway's service role (unverified; standard Lambda practice, not lab-tested). Runtime targets: the authorizer's allowed-workload configuration or a resource policy (field confirmed in docs; using it to admit only the gateway is unverified) | List every principal with invoke rights on each target function or runtime, not just the gateway |
| Authentication on every request ([mcp-and-protocols.md](mcp-and-protocols.md) §3, §6) | Gateway inbound auth types: JWT, IAM, or offloaded (authenticate only, or no authorization) (docs). The IAM condition key `bedrock-agentcore:GatewayAuthorizerType` can forbid no-auth gateways across an organisation (docs) | With no inbound auth the policy engine has no principal: identity-aware rules are impossible and session limits are shared by every caller (docs). The lab found the type couldn't be changed after creation (lab; not confirmed for Gateway in docs) |
| Receiver checklist (mcp-and-protocols §5) | Custom JWT authorizer on Gateway and Runtime: discovery URL, allowed audiences, allowed clients, allowed scopes, custom claim matches (docs for the fields; claim-match syntax lab) | Add a custom-claim match on the provider's token-use claim so ID tokens signed by the same keys are refused (lab). On Runtime, the token reaches your code only if `Authorization` is on the request-header allowlist (docs) |
| Verified, not asserted, identity (mcp-and-protocols §5) | The JWT authorizer above | Invoke and token calls that take a user ID as a plain string trust whoever holds the IAM permission. Remove that permission and add an explicit deny (lab) |
| Opaque subject IDs (mcp-and-protocols §5) | The JWT subject is written to CloudTrail (docs) | Keep emails and other PII out of `sub` |
| Delegation across hops (mcp-and-protocols §5) | Either agent code performs the RFC 8693 exchange against the identity provider (lab), or the AgentCore Identity OAuth credential provider brokers on-behalf-of exchange (RFC 8693 or RFC 7523), so code never handles the inbound token or the client secret (docs) | A JWT pass-through outbound option appears in docs search results (unverified). Treat it as token pass-through unless the receiver is your own audience-checking runtime. Full chain rules: agent-threat-modeler |
| No token pass-through; the server holds its own downstream credentials (mcp-and-protocols §3) | AgentCore Identity OAuth2 credential provider with a token vault and a user-consent flow from the SDK (SDK names unverified) | Ask for read scopes where the task allows |
| Session rules for order (tool-design-rules §8) | Policy temporal rules over a policy session: call caps, "tool B only after tool A", no external calls after a sensitive read; sessions expire after 24 hours idle; caller identity propagates Gateway → Runtime → Gateway within one account and Region (docs) | Per-caller isolation needs an authenticated gateway (docs). The handler's state check stays |
| Listed is not permitted (current facts) | With Policy attached, `tools/list` shows a tool if any circumstance could permit the call (docs) | A listed tool can still be denied at call time |
| Read-only enforced by the database (tool-design-rules §7) | Neptune IAM data-access actions separate `neptune-db:ReadDataViaQuery` from `WriteDataViaQuery` and `DeleteDataViaQuery`; the `neptune-db:QueryLanguage` condition key limits the query language (docs) | Granting only the read action is a database-enforced read-only boundary; a driver's read access mode is not (lab). openCypher `SET` needs all three actions (docs) |
| Test under the agent's own identity (tool-design-rules §7) | Connect database MCP servers and test clients as the same database user the agent's tools use, for example a Secrets Manager secret per privilege level with the RDS Data API (lab) | An admin credential hid exactly the permission errors being debugged (lab) |
| One definition for schema and handler (tool-design-rules §3) | A Lambda-backed tool server whose tool catalog was written by hand beside the function (lab); Gateway Lambda targets likewise take a tool schema supplied separately from the function code (unverified) | The catalog and the function drifted on a field name and a type (lab). After a change, test with `tools/list` and then a `tools/call` using the schema's own example |
| State check, not upsert (tool-design-rules §6) | DynamoDB `UpdateItem` creates the item when the key doesn't exist (well-established DynamoDB behaviour) | A refund handler built on it created a record for an order that didn't exist (lab). Add a condition such as `attribute_exists` on the key, or read the record first and refuse when it is missing |

## Gotchas the labs hit

### Rule-free tools behind a policy gateway

The lab put every business limit in the gateway policy and none in the tool functions. One rule permitted a
cancellation when the status argument the model supplied wasn't "shipped". A steered or confused model can pass any
status, so that rule only filters honest mistakes. Keep the gateway rules for coarse limits (amount caps, tenant,
identity), and have the function read the order and check its real status.

### A no-auth gateway

The lab gateway had no inbound authentication, so anyone with its URL could call the tools. Beyond the obvious
exposure, the policy engine then has no principal to reason about, and session limits apply to all callers together.
Pick JWT or IAM inbound auth at creation; the lab could not switch it later.

### Denial shape differed from the docs

A policy denial came back to the lab's client as a JSON-RPC error with HTTP 400, while current docs show an `isError`
tool result. The cause (negotiated protocol revision or a service change) is unknown. Smoke tests should read the
error body on a 4xx and assert on the reason, whichever shape arrives.

### Older protocol version by default

The gateway negotiated an older MCP revision until its supported versions were set explicitly. The symptom was a
client helper failing after authentication had succeeded, so it looked like an auth problem when it wasn't one.

### "Read-only" graph tool

A free-form Cypher tool ran in the driver's read access mode and was then patched with a keyword filter. The driver
mode blocks writes but not procedure calls; the filter blocked harmless queries and could miss others. The fix that
holds is a role granted only `neptune-db:ReadDataViaQuery`, plus named traversals for the two or three lookups the
agent actually needs.

### Hand-maintained tool catalog

The hand-written tool catalog named a field differently from what the function read, and declared a string where the
function checked for an integer. Every call failed validation inside the function. Generate the
schema from the handler's own types where you can, and keep one contract test per tool.

### Upsert in a refund handler

The refund function used an update that creates missing items, had no check against the order total or earlier
refunds, had no idempotency key, and returned failures as a normal result with an error field. Each of these is a
rule in tool-design-rules §5 and §6. Don't reuse such handlers as templates.

## Sources

AWS documentation pages confirmed on 2026-10-11:

- Gateway inbound authorization: https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/gateway-inbound-auth.html
- Use a gateway with Policy: https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/use-gateway-with-policy.html
- Policy core concepts: https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/policy-core-concepts.html
- Policy sessions and identity propagation: https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/policy-session-based-temporal.html
- Runtime inbound and outbound auth: https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-oauth.html
- Runtime custom headers: https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-header-allowlist.html
- On-behalf-of token exchange: https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/on-behalf-of-token-exchange.html

The Neptune IAM data-access actions were checked against the Neptune user guide on 2026-10-11.
