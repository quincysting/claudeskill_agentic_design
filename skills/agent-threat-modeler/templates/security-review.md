# Security and oversight review: <agent name>

| | |
|---|---|
| Date / reviewer | <YYYY-MM-DD / name> |
| Scope reviewed | <repos, files, configs, environments; commit or version> |
| Not verified | <what you could not see or run, and how that limits the findings> |
| Assumptions | <conservative assumptions made where inputs were missing> |

## Verdict (Step 8)

**<Ship / Ship with conditions / Block>**: <one sentence why; Block while any P0 lacks an existing control (a planned control never lifts Block on a running system); a verdict that rests on (assumed) items is provisional either way>

Top fixes, in order (one fix may close several findings):
1. <P0 fix: one line>
2. <...>
3. <...>

## Worst outcomes (Step 2)

| # | Must never happen | Reachable today? |
|---|---|---|
| W1 | <...> | <yes, via F-0x / no> |

## Trust boundaries as built (Steps 3-4)

```mermaid
flowchart LR
  %% sources -> context -> model -> (where is enforcement?) -> tools / memory / egress
```

| Tool / action | Side-effect class | Permission tier today | Data reached | Credential | Brings untrusted content? | Gate today |
|---|---|---|---|---|---|---|

Untrusted inputs: <list every source that reaches the context>

Entry points: <every endpoint, alias and deployed version that can invoke the agent, read from the live config; the
authenticator on each; who can call each tool backend directly>

Rule of Two triage: <can one run hold (A) untrustworthy inputs, (B) access to sensitive systems or private data and (C) the ability to change state or communicate externally at once? Integrity case: can untrusted input change a sensitive system (merge, deploy, configuration, permissions, payments) even with no private data?>

Ambient capabilities: <environment variables and secrets, mounted sockets, inherited credentials and metadata endpoints, network position, repository paths that trigger CI>

## Trifecta check (Step 5)

| Flow | Private data | Untrusted content | External channel | Untrusted input can change a sensitive system? | Verdict and cut |
|---|---|---|---|---|---|

## Findings (Steps 6-9)

Order by priority, then by impact. One block per finding.

### F-01 [P0] <short title>

- **Evidence:** <stated / inferred / confirmed: file:line, config key, or observed behaviour; quote the minimum needed. An inferred finding keeps its consequence's priority, written P0 (assumed)>
- **Path and impact:** <untrusted source → plan → tool → effect; which worst outcome>
- **OWASP:** <ASI0x, LLM0x>
- **Fix:** <concrete change, where it goes; small snippet if it encodes the pattern; for a running system, also the clean-up of what the old design produced: secrets to rotate, links or tokens to revoke, stored data to purge, actions to review>
- **Effort:** <S / M / L>

## Guardrails as built (Step 9)

| Check | Layer | Applies to | Declared on error | Releases output before verdict? | Finding (F-ID) |
|---|---|---|---|---|---|

MCP hardening (if in scope): <server::name resolution, definition pinning per session, token pipeline and exchange,
front door and anonymous probe, consent, sampling/elicitation/roots, runtime defaults: what exists, what is missing>

## Oversight review (Step 10)

| Action | Current handling | Should be | Hard limit | Fix (F-ID) | Gap |
|---|---|---|---|---|---|

Approval mechanics: <side effects separated from interrupt? keyed execution? bound to a digest of the exact arguments,
an expiry and a nonce? deadline and silence rule? edits re-checked? payload preview and confirm question? reviewer view
order? approvals per day vs reviewer time? do approval links only open a view, with a signed-in, entitled approver
deciding?>
Sends: <who is the principal; draft-first or delayed send for messages to anyone else, incl. invites and notifications>
Autonomy ladder: <current rung per action class; promotion metric; demotion rule>
Stop control: <exists? server-side? remote? tested?>

## OWASP Agentic coverage (Step 7)

| ID | Status | Note |
|---|---|---|
| ASI01 | covered / partial / gap / N/A | |
| ... | | |
| ASI10 | | |

## Tests to add (Step 11)

| Test | Maps to | Technique class | Injection point | Expected trace property |
|---|---|---|---|---|

Include: <ASI seeds; same call under two identities; harness-level abuse tests (agent-harness-designer); MCP deploy
probes if in scope>.

Drills: <kill switch, secret rotation, memory purge and restore>. Hand-off: datasets and graders to agent-eval-designer.

## What already works

<2-4 bullets: controls that are sound and should be kept>

## Fix plan

| Order | Fix | Findings closed | Owner | Effort |
|---|---|---|---|---|

## Residual risk and re-review triggers (Step 12)

<what remains after the fix plan, who accepts it, and what change triggers another review>
