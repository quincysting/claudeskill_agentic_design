# AWS implementation notes

AWS mapping for this skill's principles. As of 2026-10; services change, verify before use.

The (lab) rows are anonymised observations from the author's own hands-on labs, with no client data; treat them as unverified unless they are also tagged (docs).

The principles live in the other reference files and stay vendor-neutral. This file says which AWS feature or setting carries each one and where hands-on labs tripped. Tags: **(docs)** confirmed against AWS documentation on 2026-10-11 (pages listed at the end); **(established)** long-standing documented behaviour the labs did not exercise; **(lab)** found in practitioner labs only; **(unverified)** not confirmed, check before relying on it. Identity and policy enforcement on AWS: agent-threat-modeler's AWS notes. Hosting, tracing and runtime release mechanics: agent-ops-reviewer's. Runtime rows (one writer per run, typed checkpoints, ordered streams and stream position, durable exit sinks, durable workflow engines, AgentCore Runtime sessions, kill-switch flags) moved with the control loop to the agent-harness-designer skill's AWS notes.

## Mapping

| Principle (where in this skill) | AWS feature or setting | Gotcha |
|---|---|---|
| Pin peer versions per run (multi-agent.md, "Pin peer versions per run") | AgentCore Runtime versions and named endpoints | Every update creates a new version and moves the default endpoint to it, so a caller of the default endpoint changes peers mid-run (lab). Fix the version or named endpoint at run start (per-endpoint pinning unverified) |
| Partitioning (multi-agent.md, "Partitioning") | Kinesis partition key; per-shard write limits on provisioned streams; on-demand capacity mode for spiky load | A low-cardinality key (one facility) piled records onto a few shards. Hash a sample of real keys offline to check the spread, and alarm on write throttling (lab) |
| Log retention for replay and audit (multi-agent.md, "Communication") | Amazon MSK topics with `cleanup.policy=delete` and `retention.ms` sized to the business lifecycle | `cleanup.policy=compact` keeps only the latest value per key and loses the history (established Kafka behaviour; lab) |
| Per-agent credentials (multi-agent.md, "If you split") | One IAM execution role per agent runtime or tool server, scoped to that agent's own tables and indexes; the IAM policy simulator or a real call for the denial test | An inline policy with a harmless name granted cross-store access. Read the effective policy JSON, not policy names (lab) |
| Discovery (multi-agent.md, "Contracts between separately deployed agents") | A small DynamoDB table of agent cards; `GetAgentCard` to fetch the card of an agent on AgentCore Runtime (docs) | `Scan` reads the whole table and is eventually consistent by default: fine for a handful of agents; use a strongly consistent read when a just-registered card must be visible (established). The lab's registry entry had no address field, so callers compiled peer addresses in (lab) |
| A2A between agents (multi-agent.md, "Contracts between separately deployed agents") | AgentCore Runtime with the A2A protocol: a stateless HTTP server on `0.0.0.0:9000` at `/`, agent card at `/.well-known/agent-card.json`, ARM64 container (docs). That bind is for inside the managed runtime's container only; never expose the port directly | The runtime protocol defaults to HTTP; set A2A explicitly (lab). See "Deploying A2A agents" |

## Gotchas the labs hit

### Deploying A2A agents
- Each agent carried a hand-copied subset of the shared message types, because the deployment package couldn't import across the process boundary. A new response field meant editing every copy, and a missed copy failed as a type error deep in a log. Generate the types from one source. (lab)
- Peer addresses compiled into the caller forced callee-first deploys and a rebuild whenever a peer moved. Store the address with the registry entry or inject it at deploy time. (lab)
- Direct-code deploys installed no dependencies, so packages had to be vendored into the zip, built from inside the project folder. A health path at `/ping` was expected. (lab, unverified)
- An update replaced the whole runtime configuration and created a new version. Build updates from a fresh read of the current configuration. (lab)

### Hot shards from a low-cardinality key
Partitioning by facility sent most records to a few shards. Partitioning by device spread them. For agent runs, the case or session ID usually has the cardinality and gives per-case order. (lab)

## Checked against AWS documentation (2026-10-11)

- AgentCore Runtime, A2A server: https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-a2a.html
- AgentCore Runtime, A2A server container requirements: https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-a2a-protocol-contract.html
- AgentCore API reference, GetAgentCard: https://docs.aws.amazon.com/bedrock-agentcore/latest/APIReference/API_GetAgentCard.html
