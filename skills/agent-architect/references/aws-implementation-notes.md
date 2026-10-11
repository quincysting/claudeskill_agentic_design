# AWS implementation notes

AWS mapping for this skill's principles. As of 2026-10; services change, verify before use.

The principles live in the other reference files and stay vendor-neutral. This file says which AWS feature or setting carries each one and where hands-on labs tripped. Tags: **(docs)** confirmed against AWS documentation on 2026-10-11 (pages listed at the end); **(established)** long-standing documented behaviour the labs did not exercise; **(lab)** seen in practitioner labs only; **(unverified)** not confirmed, check before relying on it. Identity and policy enforcement on AWS: agent-threat-modeler's AWS notes. Hosting, tracing and runtime release mechanics: agent-ops-reviewer's.

## Mapping

| Principle (where in this skill) | AWS feature or setting | Gotcha |
|---|---|---|
| One writer per run (control-loop.md, "One writer per run") | DynamoDB conditional writes: `ConditionExpression` with `attribute_not_exists(<partition key>)` for create-once, `version = :read_version` plus an increment for updates; `TransactWriteItems` when several items change together (established) | `ConditionalCheckFailedException` means reload and decide again, not retry the same write (established). The labs used unconditional puts, so two processes resuming one request were last-writer-wins (lab) |
| Typed, versioned checkpoints (control-loop.md, "Typed, versioned checkpoints") | One DynamoDB item per run and step, carrying a state-schema version attribute; a TTL attribute for retention | The key schema can't change after the table is created, so a key change means a new table (established). Checkpoints stored as one JSON blob reloaded enums as plain strings; only a cross-process test caught it (lab) |
| Pin peer versions per run (control-loop.md, "State and checkpoints") | AgentCore Runtime versions and named endpoints | Every update creates a new version and moves the default endpoint to it, so a caller of the default endpoint changes peers mid-run (lab). Fix the version or named endpoint at run start (per-endpoint pinning unverified) |
| Ordered streams (control-loop.md, "Ordered streams") | Lambda event source mapping on Kinesis Data Streams: `MaximumRetryAttempts`, `MaximumRecordAgeInSeconds`, `BisectBatchOnFunctionError`, an on-failure destination on the mapping (SQS, SNS or S3) (docs); `ReportBatchItemFailures` returning the first failed sequence number (established) | With default settings a bad record can block its shard for up to one week (docs). The function's asynchronous-invocation destination never fired for stream failures (lab); see "The failure sink that never fired" |
| Durable exit sinks (control-loop.md, "Exit statuses") | SQS dead-letter queue through a redrive policy for queue-driven runs; the mapping's on-failure destination for stream-driven runs; a CloudWatch alarm on queue depth above zero | SQS and SNS failure records carry metadata about the failed batch, not the payload; an S3 destination also receives the invocation record (docs). In the lab the metadata was shard and sequence pointers (lab). Keep stream retention longer than triage time when the sink holds only pointers |
| Partitioning (multi-agent.md, "Partitioning") | Kinesis partition key; per-shard write limits on provisioned streams; on-demand capacity mode for spiky load | A low-cardinality key (one facility) piled records onto a few shards. Hash a sample of real keys offline to check the spread, and alarm on write throttling (lab) |
| Log retention for replay and audit (multi-agent.md, "Communication") | Amazon MSK topics with `cleanup.policy=delete` and `retention.ms` sized to the business lifecycle | `cleanup.policy=compact` keeps only the latest value per key and loses the history (established Kafka behaviour; lab) |
| Stream position on restart (control-loop.md, "Typed, versioned checkpoints") | Amazon Managed Service for Apache Flink snapshots and checkpoint interval | After a change to time semantics, old snapshots were incompatible and restoring one failed the job. It had to start without a snapshot from an explicit position; the default start position (latest) skips the backlog. Configuration updates replace whole property groups: read, merge, write (lab, unverified) |
| Per-agent credentials (multi-agent.md, "If you split") | One IAM execution role per agent runtime or tool server, scoped to that agent's own tables and indexes; the IAM policy simulator or a real call for the denial test | An inline policy with a harmless name granted cross-store access. Read the effective policy JSON, not policy names (lab) |
| Discovery (multi-agent.md, "Contracts between separately deployed agents") | A small DynamoDB table of agent cards; `GetAgentCard` to fetch the card of an agent on AgentCore Runtime (docs) | `Scan` reads the whole table and is eventually consistent by default: fine for a handful of agents; use a strongly consistent read when a just-registered card must be visible (established). The lab's registry entry had no address field, so callers compiled peer addresses in (lab) |
| A2A between agents (multi-agent.md, "Contracts between separately deployed agents") | AgentCore Runtime with the A2A protocol: a stateless HTTP server on `0.0.0.0:9000` at `/`, agent card at `/.well-known/agent-card.json`, ARM64 container (docs) | The runtime protocol defaults to HTTP; set A2A explicitly (lab). See "Deploying A2A agents" |
| Durable workflow engine (pattern-catalog.md, "Durable workflow engine") | AWS Step Functions with `Retry` and `Catch` per task; model calls inside task states | `States.ALL` must be the last entry in a retry list (established). EventBridge rules fire only for events after the rule exists, so existing items need a separate backfill (lab) |

## Gotchas the labs hit

### Last-writer-wins checkpoints
The checkpoint store wrote with an unconditional put. Two orchestrator processes resuming the same request could both write, and the later one silently replaced the earlier one. Use a version attribute and a condition on every update, or partition the trigger by case so one consumer owns each case. (lab)

### Enums that came back as strings
State went into the checkpoint as one JSON document. On reload, enum fields were plain strings, so a comparison with the enum value was false and the run took the wrong branch with no error. The in-memory store passed the same-process test. Only writing in one process and reading in another showed it. Rebuild state through the typed schema on load. (lab)

### The failure sink that never fired
A poison record in a Kinesis stream blocked its shard: the mapping retried until the record expired while the iterator age climbed. A failure destination had been configured on the function's asynchronous invocation, which looks like a dead-letter queue but never receives stream failures. The fix sat on the event source mapping: bounded retries, a maximum record age, batch bisection, an on-failure destination, and a handler that reports the first failed record and stops. Test it by injecting a malformed record and checking it lands in the sink. (lab; where the destination is configured: docs)

### Deploying A2A agents
- Each agent carried a hand-copied subset of the shared message types, because the deployment package couldn't import across the process boundary. A new response field meant editing every copy, and a missed copy failed as a type error deep in a log. Generate the types from one source. (lab)
- Peer addresses compiled into the caller forced callee-first deploys and a rebuild whenever a peer moved. Store the address with the registry entry or inject it at deploy time. (lab)
- Direct-code deploys installed no dependencies, so packages had to be vendored into the zip, built from inside the project folder. A health path at `/ping` was expected. (lab, unverified)
- An update replaced the whole runtime configuration and created a new version. Build updates from a fresh read of the current configuration. (lab)
- Runtime session IDs had to be 33 to 256 characters; derive them from the run ID. (lab, unverified)

### Hot shards from a low-cardinality key
Partitioning by facility sent most records to a few shards. Partitioning by device spread them. For agent runs, the case or session ID usually has the cardinality and gives per-case order. (lab)

## Checked against AWS documentation (2026-10-11)

- Lambda, retaining discarded batch records for a Kinesis event source: https://docs.aws.amazon.com/lambda/latest/dg/kinesis-on-failure-destination.html
- AgentCore Runtime, A2A server: https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-a2a.html
- AgentCore Runtime, A2A server container requirements: https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-a2a-protocol-contract.html
- AgentCore API reference, GetAgentCard: https://docs.aws.amazon.com/bedrock-agentcore/latest/APIReference/API_GetAgentCard.html
