# Security and oversight review: <agent name>

| | |
|---|---|
| Date / reviewer | <YYYY-MM-DD / name> |
| Scope reviewed | <repos, files, configs, environments; commit or version; when several variants exist, the one reviewed as the shipping candidate> |
| What it is | <reference or demo code / a product being offered, to whom and for what; the verdict is judged against this plan> |
| Evidence available | <code only / config / logs and traces / owners. A code-only review says so here; its runtime facts (reachability, defaults in effect) are inferred> |
| Stubs and missing parts | <tools that return fixed values, print or are placeholders; components referenced but absent; the wiring assumed for each, or "none"> |
| Not verified | <what you could not see or run, including files or line ranges not read (nothing in them is recommended), and how that limits the findings> |
| Assumptions | <conservative assumptions made where inputs were missing> |

## Verdict (Step 8)

**<Ship / Ship with conditions / Block>**: <one sentence why; Block while any P0 lacks an existing control (a planned control never lifts Block on a running system); a verdict that rests on (inferred) or (assumed) items is provisional either way>

Top fixes, in order (one fix may close several findings):
1. <P0 fix: one line>
2. <...>
3. <...>

## Confirm first

Every inferred or assumed fact a finding rests on, and the check that settles it.

| Fact | Label (inferred / assumed) | Check that settles it | Findings that change if it is false |
|---|---|---|---|

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

Ambient capabilities: <environment variables and secrets, mounted sockets, inherited credentials and metadata endpoints, network position, repository paths that trigger CI; every bind mount with its mode (a writable host mount is a finding: the agent can write to the host and persist there); paths the agent can write that the app or a later session loads as code, configuration or prompts; local listeners and how each authenticates>

## Trifecta check (Step 5)

| Flow | Private data | Untrusted content | External channel | Untrusted input can change a sensitive system? | Verdict and cut |
|---|---|---|---|---|---|

## Findings (Steps 6-9)

Order by priority, then by impact. One block per finding.

### F-01 [P0] <short title>

- **Evidence:** <label each fact: seen (file:line, config key or document section) / observed (logs, traces, a test run) / told (owner, unchecked) / inferred (name the behaviour and the version it depends on) / assumed. Quote the minimum needed; cite a credential by file:line and kind, never its value. Priority follows the consequence, written P0 (inferred) or P0 (assumed) when it rests on such a fact, which also goes under Confirm first>
- **Path and impact:** <untrusted source → plan → tool → effect; which worst outcome>
- **OWASP:** <ASI0x, LLM0x>
- **Fix:** <control C-ID; concrete change, where it goes; small snippet if it encodes the pattern; for a part that may not ship, deleting it is an option; for a running system, also the clean-up of what the old design produced: secrets to rotate, links or tokens to revoke, stored data to purge, actions to review>
- **Effort:** <S (under a day) / M (up to two weeks) / L (longer)>

Findings in parts that may not ship go after the main register, tagged (if shipped), at their consequence priority.

## Controls plan (Step 9)

Every C-ID cited anywhere in the review is defined here.

| ID | Control | Status (existing / planned) | Stops (F-IDs) | Lives in | Model can bypass? | Who can switch it off? | Cost | Priority |
|---|---|---|---|---|---|---|---|---|
| C-01 | <...> | | <F-01, F-03> | <service, file> | <no> | <role; alarm> | <latency, utility, operator time> | <P0> |

## Guardrails as built (Step 9)

| Check | Layer | Applies to | Declared on error | Releases output before verdict? | Finding (F-ID) |
|---|---|---|---|---|---|

MCP hardening (if in scope): <server::name resolution, definition pinning per session, token pipeline and exchange,
front door and anonymous probe, consent, sampling/elicitation/roots, runtime defaults: what exists, what is missing>

## Oversight review (Step 10)

| Action | Current handling | Should be | Hard limit | Control (C-ID) and finding (F-ID) | Gap |
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
| ASI01 | covered (built) / covered (planned) / gap / N/A with reason | |
| ... | | |
| ASI10 | | |

## Tests to add (Step 11)

| Test | Maps to (F-ID, C-ID) | Technique class | Injection point | Expected trace property |
|---|---|---|---|---|

Include: <ASI seeds; same call under two identities; harness-level abuse tests (agent-harness-designer); MCP deploy
probes if in scope>.

Drills: <kill switch, secret rotation, memory purge and restore>. Hand-off: datasets and graders to agent-eval-designer.

## What already works

<2-4 bullets: controls that are sound and should be kept, each with its evidence label and file:line, checked as hard as a finding>

## Fix plan

| Order | Fix (C-IDs) | Findings closed | Owner | Effort |
|---|---|---|---|---|

## Residual risk and re-review triggers (Step 12)

<what remains after the fix plan, who accepts it, and what change triggers another review>
