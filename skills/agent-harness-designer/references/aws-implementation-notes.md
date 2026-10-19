# AWS implementation notes

AWS mapping for this skill's principles. As of 2026-10; services change, verify before use.

The (lab) rows are anonymised observations from the author's own hands-on labs, with no client data; treat them as unverified unless they are also tagged (docs).

The principles live in the other reference files and stay vendor-neutral. This file says which AWS feature or setting carries each one and where hands-on labs tripped. Tags: **(docs)** confirmed against AWS documentation (2026-10-11 for rows moved from agent-architect, 2026-10-19 for the rest; pages listed at the end); **(established)** long-standing documented behaviour the labs did not exercise; **(lab)** found in practitioner labs only; **(unverified)** not confirmed, check before relying on it. Identity and policy enforcement on AWS: agent-threat-modeler's AWS notes. Hosting choice, tracing and runtime release mechanics (versions, endpoints, canary): agent-ops-reviewer's. Peer version pinning, partitioning and A2A deployment: agent-architect's.

## Mapping

| Principle (where in this skill) | AWS feature or setting | Gotcha |
|---|---|---|
| One writer per run (control-loop.md, "One writer per run") | DynamoDB conditional writes: `ConditionExpression` with `attribute_not_exists(<partition key>)` for create-once, `version = :read_version` plus an increment for updates; `TransactWriteItems` when several items change together (established) | `ConditionalCheckFailedException` means reload and decide again, not retry the same write (established). The labs used unconditional puts, so two processes resuming one request were last-writer-wins (lab) |
| Typed, versioned checkpoints (control-loop.md, "Typed, versioned checkpoints") | One DynamoDB item per run and step, carrying a state-schema version attribute; a TTL attribute for retention | The key schema can't change after the table is created, so a key change means a new table (established). Checkpoints stored as one JSON blob reloaded enums as plain strings; only a cross-process test caught it (lab) |
| Durable state, not compute memory (harness-components.md §1, row 3) | AgentCore Runtime sessions: one microVM per session; memory and disk last only for that compute's lifecycle; session storage persists a mounted directory across stop and resume (docs) | A session stops after 15 minutes idle or 8 hours of compute lifetime by default (configurable up to 8 hours on microVMs, 14 days on Instances), and the next invoke gets a new compute for the same session ID: anything held only in memory is gone (docs). Keep the run record and checkpoints in an external store |
| Run identity (harness-components.md §2) | `runtimeSessionId` on `InvokeAgentRuntime` and `StopRuntimeSession`: 33 to 256 characters (docs) | AgentCore does not enforce session-to-user mappings; your backend keeps them and limits sessions per user (docs). Derive the session ID from the run ID and check the caller owns it before every invoke |
| Background work in a session (serving-and-deployment.md §5) | The agent's ping reports `HealthyBusy` while background tasks run (docs) | Without it a session doing background work looks idle and can be stopped at the idle timeout (docs) |
| Cancel and abort (serving-and-deployment.md §4; harness-components.md §4) | `StopRuntimeSession` stops a session's compute; it takes a `clientToken` for idempotent retries (docs) | Stopping is not aborting: the next invoke for that session provisions new compute (docs). The abort flag in the harness and revoked credentials must still hold. A stop or invoke during provisioning can return a retryable 409; back off and retry (docs) |
| Kill-switch flags read at every call (harness-components.md §4) | AWS AppConfig feature flags, read through the AppConfig Agent Lambda extension or agent | The agent polls every 45 seconds by default and serves cached data when a poll times out (docs), so a flip reaches running workers within the poll interval, not instantly. Set the interval to what draft-only needs; for abort, also revoke IAM permissions on the execution role so the stop does not depend on propagation (established) |
| Durable workflow engine (serving-and-deployment.md §7) | AWS Step Functions with `Retry` and `Catch` per task; model calls inside task states | `States.ALL` must be the last entry in a retry list (established). EventBridge rules fire only for events after the rule exists, so existing items need a separate backfill (lab) |
| Durable execution in code (serving-and-deployment.md §7) | Lambda durable functions: steps and waits, checkpoint and replay; executions up to one year; waits incur no compute charge (docs) | Replay runs the code from the beginning and skips completed checkpoints, so model and tool calls belong in steps (docs). Steps are at-least-once: a step interrupted before it completes can run again, so key the write inside it (docs) |
| Run ID from the trigger (serving-and-deployment.md §6) | Durable function execution names act as idempotency keys: the same name and payload returns the existing execution (docs) | Event source mappings do not deduplicate durable executions: every invocation, retries included, starts a new one. Invoke through a small dispatcher that sets the execution name from the event's source and ID (docs) |
| Approval pause in a workflow (harness-components.md §3) | Step Functions `.waitForTaskToken`; the approval service calls `SendTaskSuccess` or `SendTaskFailure` with the token; `StopExecution` to cancel (established) | The token proves which paused task resumes, not what was approved. Keep the digest, expiry and nonce in your own approval record and recheck them in the task that executes (this skill's rule) |
| Ordered streams (control-loop.md, "Ordered streams") | Lambda event source mapping on Kinesis Data Streams: `MaximumRetryAttempts`, `MaximumRecordAgeInSeconds`, `BisectBatchOnFunctionError`, an on-failure destination on the mapping (SQS, SNS or S3) (docs); `ReportBatchItemFailures` returning the first failed sequence number (established) | With default settings a bad record can block its shard for up to one week (docs). The function's asynchronous-invocation destination never fired for stream failures (lab); see "The failure sink that never fired" |
| Durable exit sinks (control-loop.md, "Exit statuses") | SQS dead-letter queue through a redrive policy for queue-driven runs; the mapping's on-failure destination for stream-driven runs; a CloudWatch alarm on queue depth above zero | SQS and SNS failure records carry metadata about the failed batch, not the payload; an S3 destination also receives the invocation record (docs). In the lab the metadata was shard and sequence pointers (lab). Keep stream retention longer than triage time when the sink holds only pointers |
| Stream position on restart (control-loop.md, "Typed, versioned checkpoints") | Amazon Managed Service for Apache Flink snapshots and checkpoint interval | After a change to time semantics, old snapshots were incompatible and restoring one failed the job. It had to start without a snapshot from an explicit position; the default start position (latest) skips the backlog. Configuration updates replace whole property groups: read, merge, write (lab, unverified) |

## Gotchas the labs hit

### Last-writer-wins checkpoints
The checkpoint store wrote with an unconditional put. Two orchestrator processes resuming the same request could both write, and the later one silently replaced the earlier one. Use a version attribute and a condition on every update, or partition the trigger by case so one consumer owns each case. (lab)

### Enums that came back as strings
State went into the checkpoint as one JSON document. On reload, enum fields were plain strings, so a comparison with the enum value was false and the run took the wrong branch with no error. The in-memory store passed the same-process test. Only writing in one process and reading in another showed it. Rebuild state through the typed schema on load. (lab)

### The failure sink that never fired
A poison record in a Kinesis stream blocked its shard: the mapping retried until the record expired while the iterator age climbed. A failure destination had been configured on the function's asynchronous invocation, which looks like a dead-letter queue but never receives stream failures. The fix sat on the event source mapping: bounded retries, a maximum record age, batch bisection, an on-failure destination, and a handler that reports the first failed record and stops. Test it by injecting a malformed record and checking it lands in the sink. (lab; where the destination is configured: docs)

### Session IDs that were too short
Runtime session IDs had to be 33 to 256 characters (lab; length confirmed in the API reference, docs). Derive them from the run ID, padded or hashed to length, rather than using a short ticket number.

## Checked against AWS documentation

2026-10-11:
- Lambda, retaining discarded batch records for a Kinesis event source: https://docs.aws.amazon.com/lambda/latest/dg/kinesis-on-failure-destination.html

2026-10-19:
- AgentCore Runtime, isolated sessions and session lifecycle: https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-sessions.html
- AgentCore Runtime, lifecycle settings: https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-lifecycle-settings.html
- AgentCore API reference, StopRuntimeSession: https://docs.aws.amazon.com/bedrock-agentcore/latest/APIReference/API_StopRuntimeSession.html
- Lambda durable functions: https://docs.aws.amazon.com/lambda/latest/dg/durable-functions.html
- Lambda durable functions, idempotency: https://docs.aws.amazon.com/lambda/latest/dg/durable-execution-idempotency.html
- AppConfig Agent Lambda extension configuration: https://docs.aws.amazon.com/appconfig/latest/userguide/appconfig-integration-lambda-extensions-config.html
