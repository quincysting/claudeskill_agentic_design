# Guardrails: layers, checks, release and failure modes

Three words for checks at different points: a **guardrail** is synchronous and can block, modify or replace content
before it is used; a **verifier** checks quality so the agent can retry or self-correct [DLLMA ch10]; an **online
eval** runs after delivery on a sample and changes nothing for the user [EVALS ch10]. Guardrails cut the volume of
bad traffic. Architecture bounds the damage of whatever gets through, so no guardrail is the only control on a P0 or
P1 path.

Risk sits in the application, not the model: the same model is harmless or dangerous depending on what the
application lets it do [NG Blenders Versus Bombs, or Why California's Proposed AI Law is Bad for Everyone, 2024-06-05].
That decides where guardrails go: around the model, in code you own and test.

## 1. Three layers, and what each can carry

| Layer | What it is | Catches | Why it fails | Counts as the control for a P0/P1 path? |
|---|---|---|---|---|
| Prompt (model layer) | Role, rules and forbidden actions in the instructions | Most normal use | It lives in the same reasoning space as the attack; it can be truncated, summarised away or argued around | Never |
| Screening | Input and output checks between user, agent and systems | Known patterns | Misses new phrasing; detectors vary widely | No: detection only |
| Hard limits in code and infrastructure | API restrictions, rate limits, access controls, filesystem permissions, the policy gate | Anything outside the bounds, whatever the model was told | Narrow in scope | Yes |

[PLAYBOOK ch9] requires all three and says plainly that a prompt instruction is not a guardrail: if the agent may
not delete records, the restriction exists in the system. The model can't enforce a boundary that injection works by
confusing [HARDMCP ch6].

**Provider safety is not a control.** A hosted model's refusals are someone else's policy, which you neither control
nor test. In 2026 they blocked defensive work (analysing logs of an attack, reviewing a team's own code) and did not
stop an agent whose sandbox and monitoring failed [NG When Guardrails Go Wrong, 2026-07-24],
[NG Open Models, Open Harnesses, Open Security, 2026-07-31], [NG Who's Responsible for Irresponsible AI?, 2026-09-18].
[AISEC ch10] gives providers robustness, alignment and baseline guardrails, and application owners validation,
filtering and monitoring; take the application half as yours in full. Count provider safety as a bonus, and keep an
in-house or open-weight model path for forensic work on sensitive logs.

## 2. What to check, and where

### Input guardrails

| Check | Looks for | Applies to |
|---|---|---|
| Topical | Off-topic or sensitive subjects the product doesn't serve | User input |
| Injection, direct and indirect | Override attempts; hidden characters, encoded payloads or prompt overrides in uploads, pages and transcripts | User input, retrieved content, tool results, tool descriptions |
| Moderation | Brand, legal and policy rules: profanity, competitor mentions, personal data, self-harm | User input |
| Attribute | Length, file size, allowed choices, ranges, format and structure | Every input |

Taxonomy after [FASTGENAI ch9], which adds the rule that matters most: don't give the model secrets or sensitive
configuration in the first place.

### Tool output, before it reaches the model

- Every tool result is untrusted input: validate it against the tool's output schema, cap its size, scan it for
  injection and exfiltration markers with higher sensitivity than authenticated user input [DEFGUIDE ch12], mark it
  as data and set the taint flag if it carries outside content.
- A gateway check is the last line, not the only one: the service behind the gateway still validates its own input
  and output [APIARCH ch6].
- Results never trigger calls on their own (section 3).

### Output guardrails

| Check | Looks for | On fail |
|---|---|---|
| Grounding and fact checks | Claims unsupported by the retrieved sources | Canned "I don't know", or drop the claim |
| Moderation | Toxicity, brand and policy rules | Filter or rewrite |
| Syntax and schema | Output structure; function-call arguments; tool or agent selection in agent workflows | Retry, or handle the exception before it reaches a downstream system |
| Proposed-call arguments | Injection markers in free-text arguments (reasons, notes, message bodies) | Deny or route to a person (section 4) |
| Destination encoding | Model output headed for HTML, SQL, a shell or a template | Escape, parameterise, never `shell=True` |

The first three rows follow [FASTGENAI ch9]; the destination rule is OWASP's improper output handling (LLM10).

## 3. Provenance gate, fenced context, egress allowlist

Three controls that hold without asking the model to judge intent [HARDMCP ch6]:

- **Provenance gate.** Tag every tool output with its origin and refuse any tool call whose trigger traces to tool
  content rather than the user's request: a tool result may inform, never command. Google DeepMind's CaMeL applies
  the same principle, granting permissions from the data's source rather than its content [PLAYBOOK ch9]. A "trigger"
  is hard to trace in a free-running model, so implement it as taint (once untrusted content has entered the run,
  consequential calls need approval or are denied) or per value with the dual-LLM pattern
  ([controls-catalog.md](controls-catalog.md) §5).
- **Fenced, labelled context.** Each source sits in a bounded block whose trust label is attached on entry, so
  low-trust text can't pose as a system instruction ([mcp-hardening.md](mcp-hardening.md) §1).
- **Egress allowlist.** A short list of named destinations; everything else is refused. Every exfiltration ends with
  data leaving, so one rule on the exit covers attacks whose earlier stages you never saw. Implement it in an egress
  proxy ([controls-catalog.md](controls-catalog.md) §4).

## 4. Tiers and latency

| Tier | What | Where | Latency |
|---|---|---|---|
| 1 Deterministic | Unicode normalisation, invisible-character flags, regex families (injection markers, exfiltration patterns such as URLs with encoded data), schema checks, allow/deny lists, PII patterns | Inline, every request and every tool result | Microseconds [EVALS ch10] |
| 2 Small model or classifier | Injection/jailbreak classifier, topic classifier | Inline only on the uncertain band of tier-1 scores, with a cache | Tens to hundreds of ms |
| 3 LLM judge | Policy or alignment check on the plan or output | Uncertain band only, or in parallel with generation (section 5) | Hundreds of ms or more [EVALS ch10] |
| 4 Online eval | Quality and safety sampled after delivery | Async, sampled | None for the user |

Design rules:
- Weight by trust context: tool output gets higher injection and exfiltration sensitivity than authenticated staff
  input [DEFGUIDE ch12].
- Map the score to allow / human review / block, and invoke the judge only between two thresholds (the book's scanner
  uses 0.2 and 0.8 [DEFGUIDE ch12]; tune yours on a labelled set). Before enforcing, run the check in shadow
  (log-only) mode and set thresholds on the observed score distribution.
- Scan the free-text **arguments of proposed calls** (reasons, notes, message bodies) as well as inputs and results.
  Injection markers in an argument mean the plan was steered upstream: deny or route to a human, as a forbid no allow
  can override. It is still detection, not the control for a P0 path. Test each such rule with a paired call
  ([red-team-test-plan.md](red-team-test-plan.md) §Gate rule tests).
- Choose the on-fail action per validator: fix or redact (deliver the rest), re-ask, filter one field, refrain, log only,
  raise [DLLMA ch10]. Prefer modification to blocking; a guardrail that blocks good answers can be worse than none [EVALS ch10].
- Start from untrusted defaults, measure a bypass baseline with an automated red-team harness, tune only the categories
  that fail [DEFGUIDE ch12].
- Detector quality varies widely: on the vendor-run PINT benchmark one commercial detector scored 92.5% and Llama Prompt
  Guard 61.4% [BUILDAPPS ch12]. A joint study by OpenAI, Anthropic and Google DeepMind bypassed most published
  defences at attack success rates above 90% (a 2025 snapshot, in [PLAYBOOK ch9]). Whatever you deploy leaves a
  residue the architecture must absorb.

Guardrail products named in the books (NeMo Guardrails, Guardrails AI, LlamaFirewall, LLM-Guard) are examples as of
2026-10, not endorsements; check their current state.

## 5. Release discipline: no output before its verdict

- **Hold release for every verdict.** Running a check in parallel with generation is fine; releasing before it
  finishes is not. One listing cancels generation when the input check fails
  [FASTGENAI repo: examples/ch09/9-3.py]; the next returns the answer whenever generation finishes first, skipping the
  input verdict [FASTGENAI repo: examples/ch09/9-5.py].
- **Streaming.** With server-sent events a whole-answer output check can't run before tokens leave. Buffer, or check in
  windows and stop the stream on a fail [FASTGENAI ch6], [FASTGENAI ch9]. Streaming and cancellation mechanics belong
  to agent-harness-designer.
- **A guard returns a decision and blocks by default.** A pipeline that hands back the output together with a failed
  result has a guard that blocks only in its report [EVALS repo: project/cap10/evalkit/production/pipeline.py]. The same
  code's substring profanity check also blocks "hello", which is why false blocks need measuring.
- **Labels are not enforcement.** A tool marked "requires approval" or given a risk level blocks nothing unless a
  policy reads the label [RELATED repo: aisuite/aisuite/toolkits/shell.py]. Refuse to start when an approval-labelled
  tool has no approval policy wired, so the gap fails closed. Startup checks of this kind: agent-harness-designer.

Test: a deliberately slow guardrail and a fast model; the output must wait for the verdict.

## 6. Fail open or fail closed, declared per check

Every check errors sometimes: a timeout, a classifier that is down, a policy engine out of reach. Declare per check
what happens then, and test it by making the check fail [APIARCH ch6].

| The check guards | On error | Why |
|---|---|---|
| A side effect: policy gate, token validation, egress, approvals, hard limits | Fail closed | An error must never become a permit |
| Input screening in a run that can reach write or egress tools | Fail closed, or route to a person | The run's tools set the stakes, not the check |
| Quality of a read-only answer | May fail open if every miss is logged and sampled | Blocking a good answer can be worse than no guardrail [EVALS ch10] |
| Rate limits | Fail closed wherever cost or abuse matters | [APIARCH ch6] counts a rate limit left to fail open as a misconfiguration |

[PRODGUIDE ch12] and [PLAYBOOK ch9] default to deny; [EVALS ch10]'s after-delivery checks amount to failing open,
which is right only for the last row. Write the declared mode next to each check in the controls plan.

## 7. The enforcement point itself

The gate is a guardrail too, and the companion governor shows the usual weak spots
[DEFGUIDE repo: ch06/ch06_A2A_MCP_Governed.ipynb]:

- Anchor allowlist patterns. A first-match, unanchored pattern written for one tool also matches longer names that
  contain it.
- Argument validation fails closed for a tool that has no rule.
- The approval record stores the approver and a digest of the exact arguments, with an expiry and a nonce
  ([human-oversight.md](human-oversight.md) §3).
- The gate fails closed when it errors, and its mode and rules are protected ([controls-catalog.md](controls-catalog.md) §10).

## 8. Measuring guardrails

Measure both error rates for each check, and repeat after every model, prompt or tool change:
- **False-pass rate**: share of red-team cases per technique class that the check lets through
  ([red-team-test-plan.md](red-team-test-plan.md)).
- **False-block rate**: share of a benign set blocked, including legitimate traffic that looks risky (developer
  requests, security staff, quoted attacks in support tickets).

## Common mistakes

| Mistake | Fix |
|---|---|
| Defending injection with a better system prompt | The prompt layer lives where the attack lives. Keep the instruction as documentation; put the rule in the gate, the egress allowlist or the provenance gate |
| Leaving safety to provider refusals | Refusals are untested third-party policy. Own the three layers; keep an in-house model path for sensitive forensics |
| A guardrail that releases output before its verdict | Parallel checks are fine; release waits for every verdict. Buffer or window streamed output |
| A guard that blocks only in its report | Return a decision that blocks by default; test that a failed check stops delivery |
| No declared failure mode | Write fail open or fail closed per check; side-effect checks fail closed |
| Screening user input only | Screen tool results, tool descriptions and proposed-call arguments as well |
| Blocking whole answers where redaction would do | Pick the on-fail action per validator; redact and deliver the rest |
| An LLM judge on every request | Deterministic inline, small model on the uncertain band, judge only there or in parallel |
| Approval labels with no policy behind them | Refuse to start until a policy enforces the label |
