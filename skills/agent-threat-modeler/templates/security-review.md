# Security and oversight review: <agent name>

| | |
|---|---|
| Date / reviewer | <YYYY-MM-DD / name> |
| Scope reviewed | <repos, files, configs, environments; commit or version> |
| Not verified | <what you could not see or run, and how that limits the findings> |
| Assumptions | <conservative assumptions made where inputs were missing> |

## Verdict (Step 8)

**<Ship / Ship with conditions / Block>**: <one sentence why>

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

| Tool / action | Side-effect class | Data reached | Credential | Brings untrusted content? | Gate today |
|---|---|---|---|---|---|

Untrusted inputs: <list every source that reaches the context>

## Trifecta check (Step 5)

| Flow | Private data | Untrusted content | External channel | Verdict and cut |
|---|---|---|---|---|

## Findings (Steps 6-9)

Order by priority, then by impact. One block per finding.

### F-01 [P0] <short title>

- **Evidence:** <file:line, config key, or observed behaviour; quote the minimum needed>
- **Path and impact:** <untrusted source → plan → tool → effect; which worst outcome>
- **OWASP:** <ASI0x, LLM0x>
- **Fix:** <concrete change, where it goes; small snippet if it encodes the pattern>
- **Effort:** <S / M / L>

## Oversight review (Step 10)

| Action | Current handling | Should be | Hard limit | Fix (F-ID) | Gap |
|---|---|---|---|---|---|

Approval mechanics: <side effects separated from interrupt? keyed execution? deadline and silence rule? edits re-checked?
reviewer view order? approvals per day vs reviewer time?>
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

Drills: <kill switch, secret rotation, memory purge and restore>. Hand-off: datasets and graders to agent-eval-designer.

## What already works

<2-4 bullets: controls that are sound and should be kept>

## Fix plan

| Order | Fix | Findings closed | Owner | Effort |
|---|---|---|---|---|

## Residual risk and re-review triggers (Step 12)

<what remains after the fix plan, who accepts it, and what change triggers another review>
