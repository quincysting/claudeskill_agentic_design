# Tool specification: <agent or server name>

## Summary
- **Tools:** <N> tools, cut from <M> agent stories; <why this cut, in one line>. (Recount every number in this summary from the body before returning.)
- **Integration:** <native function calling | MCP over stdio | MCP over Streamable HTTP | CLI | Skill | A2A>, because <reason>.
- **Selection:** <load all | scoped by state/role | tool search with deferred loading | code mode | subagents>; definitions ≈ <tokens> tokens per call.
- **Riskiest tool:** `<name>`, controlled by <authorization, idempotency, approval>.
- **Build first:** <the first two or three tools and the eval>.

## Context
Model and API: <provider, model, strict mode yes/no, forced tool_choice yes/no>. Host: <own loop | framework | MCP hosts>; host controlled by us: <yes | no: list which levers are not ours>. Caller identity: <how authenticated (verified token), on whose behalf>. Gateway or policy engine in front: <none | which; backends callable only from it: yes/no>. Consumers: <own agent | other teams | third parties>.

## Inventory

| Tool | Agent story | Kind (read / write / send / spend / destructive) | Tier (read-only / draft-only / approval / auto) | Scope | Idempotency | Reversible | Visible when |
|---|---|---|---|---|---|---|---|
| `svc_verb_object` | "The agent wants to …" | read | read-only | `orders:read` | n/a | n/a | always |

## Tool specs

### `svc_verb_object`

Definition (what the model sees). Use the target's key: `inputSchema` for MCP, `input_schema` for the Claude API, `parameters` for OpenAI. This skeleton shows MCP.

```json
{
  "name": "svc_verb_object",
  "title": "<Verb object, for people>",
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
- **Contract:** owner <team>, version <x.y.z>; operational constraints <when the tool may not be used>
- **Result:** <envelope fields; receipt for writes (ID, link, applied fields, status, key, contract version); size bound; opaque cursor (never a page number) or link for large data; next actions if state-dependent>
- **Errors:**

  | Condition | Category | Route | Message |
  |---|---|---|---|

  Wrapped backend: <how its HTTP status and error pages map to categories; a 5xx or timeout after a write was sent = outcome_unknown (tool-contracts §4a)>

- **Side effects:** <what changes; update as a guarded replacement, or idempotency key = run_id + action + target (+ plan step), recorded before the first attempt, or a business-object key when there is no run ID; state check that blocks a repeat; backend honours the key: yes/no; reversible: yes (revert action) / no>
- **Timeout and retries:** <timeout>; <retries with backoff for transient faults>; on a write timeout or a 5xx after sending, verify with <lookup tool by key, or a repeat that returns the existing record> before retrying with the same key; timeout message: "<may have completed; check with …>"
- **Rate limits:** <per principal / per client / per tool; quota per day; what the description tells the model>
- **Approval:** <none | runtime gate | elicitation | propose-only>, threshold <…> (basis: <human policy limit / accepted loss>); fallback when the client cannot ask: <propose-only tool>; approval page: <in the system of record, signed-in and entitled approver, decides on submit (POST), never on opening the link>
- **Fallback if unavailable:** <backup or escalation> (critical tools only)

(repeat per tool)

## Mandatory steps
| Step | Enforced by (code pre-call / completion gate / exposure gate / forced tool_choice; in an MCP server: handler precondition check) |
|---|---|

## Protocol (if MCP or A2A)
- Primitives: <which capabilities are tools, resources, prompts, and why>
- Transport and deployment: <stdio | Streamable HTTP stateless, JSON responses>; <hosting>
- Auth: <OAuth resource server, scopes, audience check, no pass-through: own credential or token exchange per backend> or <env credentials for stdio>
- Human input: <elicitation form or URL mode for …>
- Long jobs: <Tasks extension | start/status pair>
- Client obligations: <namespacing, consent on list change, dedupe on resend, name translation>
- Distribution: <remote URL | registry entry | container | bundle>; version pinning

## Tool-choice eval
- Cases: <n> per tool, <n> per confusable pair (<pairs>), <n> ask / none / decline cases; held-out <n>.
- Runs: <k> per case, tool order shuffled; production model and prompt.
- Report: accuracy, per-tool precision and recall, confusion matrix, argument validity, calls and tokens per task.
- Ship bar: <e.g. no tool below 0.9 recall; zero wrong-tool calls on destructive tools>.
- Re-run on: tool, description, schema, server, model or prompt change. Load definitions from the running server, not a hand-copied list.

## Change and catalogue (tools other teams or agents call)
- Catalogue entry: owner, namespace, lifecycle stage, calling agents.
- Change rule: additive changes only; a break ships as `<tool>_v2` beside the old tool; deprecation date and replacement.
- CI: schema diff (proved with a planted break), one contract test per tool and failure category through the real client, against a sandbox with test credentials (no production secrets in CI; `pull_request`, never `pull_request_target`).
- Upstream API: <name, version, owner>; the adapter absorbs renames; upstream spec diffed in CI; a change of meaning ships as v2.

## Assumptions and open questions
- <assumption> (**blocking** if a recommendation flips when it is wrong; how to check)

## Hand-offs
- <agent-threat-modeler for …>, <agent-eval-designer for …>, <agent-architect for …>
