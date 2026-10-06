# Tool specification: <agent or server name>

## Summary
- **Tools:** <N> tools, cut from <M> agent stories; <why this cut, in one line>.
- **Integration:** <native function calling | MCP over stdio | MCP over Streamable HTTP | CLI | Skill | A2A>, because <reason>.
- **Selection:** <load all | scoped by state/role | tool search with deferred loading | code mode | subagents>; definitions ≈ <tokens> tokens per call.
- **Riskiest tool:** `<name>`, controlled by <authorization, idempotency, approval>.
- **Build first:** <the first two or three tools and the eval>.

## Context
Model and API: <provider, model, strict mode yes/no, forced tool_choice yes/no>. Host: <own loop | framework | MCP hosts>; host controlled by us: <yes | no: list which levers are not ours>. Caller identity: <how authenticated, on whose behalf>. Consumers: <own agent | other teams | third parties>.

## Inventory

| Tool | Agent story | Kind (read / write / send / spend / destructive) | Permission or scope | Idempotency | Approval | Visible when |
|---|---|---|---|---|---|---|
| `svc_verb_object` | "The agent wants to …" | read | `orders:read` | n/a | no | always |

## Tool specs

### `svc_verb_object`

Definition (what the model sees). Use the target's key: `inputSchema` for MCP, `input_schema` for the Claude API, `parameters` for OpenAI. This skeleton shows MCP.

```json
{
  "name": "svc_verb_object",
  "description": "<what it does>. Use when <…>. Do not use for <…>; use <sibling> instead. <inputs, units, formats>. <preconditions>. Returns <shape>. <side effects, limits>. <failure behaviour>.",
  "inputSchema": {
    "type": "object",
    "properties": {},
    "required": [],
    "additionalProperties": false
  }
}
```

| Parameter | Type and constraints | Meaning, source of the value |
|---|---|---|

- **Injected by runtime (not in schema):** <caller identity, tenant, approval, idempotency key>
- **Validation:** schema, then business rules: <list>
- **Authorization:** <rule, decided from caller identity>
- **Result:** <fields; size bound; pagination or link for large data>
- **Errors:**

  | Condition | Route | Message |
  |---|---|---|

- **Side effects:** <what changes; idempotency key = hash(task_id, tool, args), or a business-object key when there is no task ID; state check that blocks a repeat; backend honours the key: yes/no>
- **Timeout and retries:** <timeout>; <retries with backoff for transient faults>; timeout message: "<may have completed; check with …>"
- **Approval:** <none | runtime gate | elicitation>, threshold <…> (basis: <human policy limit / accepted loss>); fallback when the client cannot ask: <propose-only tool>
- **Fallback if unavailable:** <backup or escalation> (critical tools only)

(repeat per tool)

## Mandatory steps
| Step | Enforced by (code pre-call / completion gate / exposure gate / forced tool_choice; in an MCP server: handler precondition check) |
|---|---|

## Protocol (if MCP or A2A)
- Primitives: <which capabilities are tools, resources, prompts, and why>
- Transport and deployment: <stdio | Streamable HTTP stateless, JSON responses>; <hosting>
- Auth: <OAuth resource server, scopes, audience check, no pass-through> or <env credentials for stdio>
- Human input: <elicitation form or URL mode for …>
- Long jobs: <Tasks extension | start/status pair>
- Client obligations: <namespacing, consent on list change, dedupe on resend, name translation>
- Distribution: <remote URL | registry entry | container | bundle>; version pinning

## Tool-choice eval
- Cases: <n> per tool, <n> per confusable pair (<pairs>), <n> ask / none / decline cases; held-out <n>.
- Runs: <k> per case, tool order shuffled; production model and prompt.
- Report: accuracy, per-tool precision and recall, confusion matrix, argument validity, calls and tokens per task.
- Ship bar: <e.g. no tool below 0.9 recall; zero wrong-tool calls on destructive tools>.
- Re-run on: tool, description, schema, server, model or prompt change.

## Assumptions and open questions
- <assumption> (**blocking** if a recommendation flips when it is wrong; how to check)

## Hand-offs
- <agent-threat-modeler for …>, <agent-eval-designer for …>, <agent-architect for …>
