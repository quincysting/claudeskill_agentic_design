# OWASP mapping and external frameworks (as of 2026-10)

These lists change. Check the dates below against the current OWASP GenAI Security Project pages before an audit.
Use the lists as a **coverage check** after you have traced paths, not as the threat model itself.

## OWASP Top 10 for Agentic Applications 2026 (released 2025-12-09)

Primary list for agents. Test each item on full traces, not final text. The controls merge this skill's control
families with the secure-design lists [AISEC ch10] prints for each item; seeded tests for every row are in
[red-team-test-plan.md](red-team-test-plan.md) §ASI seed suite.

| ID | Risk | Look for in the design or code | Primary controls | Test property (what a passing trace shows) |
|---|---|---|---|---|
| ASI01 | Agent goal hijack (injection or hidden instructions) | Untrusted sources sharing context with write or egress tools; trifecta flows; workspace files, notes and memory the agent reads | Trifecta cut or Rule of Two fallbacks; provenance gate; fenced, labelled context separating instructions from content; the goal held as a protected object, not free text; action gating; tool output treated as untrusted | No consequential call follows untrusted content without a gate decision |
| ASI02 | Tool misuse and exploitation (unsafe composition, recursion, excessive execution) | Generic or over-broad tools; side-effect tools reachable from untrusted input; no budgets; loose argument schemas | Policy gate; least-privilege tools; typed contracts with explicit side-effect metadata; argument gates; budgets; rate limits and anomaly detection on invocation patterns | Out-of-policy calls are attempted-and-blocked, never executed |
| ASI03 | Identity and privilege abuse | Shared service accounts, token pass-through, delegation that widens rights, user identity asserted as a string, one identity that plans and executes | Per-agent identity; separate identities to recommend, prepare and execute; capability tokens bound to one action and time; verified user identity; token exchange per hop; no ambient authority | Calls carry the right agent and user identity; no cross-tenant access; scope never widens along a delegation chain; the log proves who authorised and who executed |
| ASI04 | Agentic supply chain (tools, agents, schemas, registries) | Unpinned MCP servers or dependencies, runtime tool-list fetches, unvetted registries, unsigned releases, prompt packs or configs pulled at runtime | Pinned and hashed dependencies; signed, verified releases; definitions pinned per session; acceptance criteria for third-party servers; least privilege even for trusted dependencies ([mcp-hardening.md](mcp-hardening.md)) | A changed tool definition halts the call until re-approval; shadowed names are rejected |
| ASI05 | Unexpected code execution | `exec`/`eval`, shell tools, code mode without a sandbox, templating or notebook hooks, untrusted files parsed unsafely | Sandbox tiers; deny-by-default interpreter; dangerous primitives off by default; safe parsing for untrusted files; two-person approval for execution that changes infrastructure or data | Code cannot read env secrets, host files or reach non-allowlisted hosts; if something runs, the blast radius stays small |
| ASI06 | Memory and context poisoning | Writes from tainted runs, shared memory, saved exemplars, notes agents write for other agents | Validated writes; provenance and expiry; read-time filters before high-risk actions; tenant isolation; purge | Content planted in run 1 does not change actions in run 2; recovery time after cleanup is measured |
| ASI07 | Insecure inter-agent communication | Plain HTTP, unauthenticated or free-text messages between agents | Mutual authentication or audience-bound per-hop tokens; signed, schema'd messages with replay protection; messages that cannot grant privileges; agent groups segmented by trust; receiver-side gate | Forged, replayed or malformed agent messages are rejected; a token replayed at another agent is refused |
| ASI08 | Cascading failures | Loops, retries, fan-out without limits; no circuit breakers | Budgets, hop limits, circuit breakers and safe mode; checkpoints and rollback; idempotent tools; staged execution (plan, validate, execute) | A failing or contradictory dependency yields a partial result or escalation, and stop conditions fire before damage |
| ASI09 | Human-agent trust exploitation | Approval as the only barrier; narrative-first approval views; high escalation volume | Hard limits after yes; approvals bound to the exact action; action-first reviewer view with diffs, risks and source provenance; known kept apart from inferred; a second channel for critical actions | A persuasive request over the cap is refused before any human sees it |
| ASI10 | Rogue agents (goal drift, collusion, reward hacking) | No registry of agents, no behaviour baseline, no kill switch, autonomy never reviewed | Agent registration and attestation; behaviour baselines; per-agent sandboxes and quarantine; kill switch, credential rotation, session invalidation; automatic demotion | An unregistered agent can't join a workflow; anomaly triggers quarantine; kill switch revokes access within the target time |

Another bot writing to the agent through an ordinary channel (email, chat, web form) is untrusted content
(ASI01), not inter-agent communication; ASI07 applies when agents exchange messages over an agent protocol or API.
Names follow the release as reproduced in [DEFGUIDE ch8] and [AISEC ch10]. Red-team tools ship this list as a ready-made
framework (DeepTeam's `OWASP_ASI_2026`, per [DEFGUIDE ch8]).

## OWASP Top 10 for LLM Applications 2026 (published 2026-08-04)

Use for the model-facing parts and for chat features without tools.

| ID | Risk | Agent relevance |
|---|---|---|
| LLM01 | Prompt Injection | Root of ASI01; architecture, not filters, bounds it |
| LLM02 | Sensitive Information Disclosure | Exfiltration, cross-tenant retrieval, secrets in context, logs |
| LLM03 | Excessive Agency | Over-broad tools and permissions; ranked third in 2026 (sixth in 2025) |
| LLM04 | Supply Chain | Models, datasets, plugins, MCP servers, packages |
| LLM05 | Data and Model Poisoning | Training or fine-tuning data, RAG corpora, memory |
| LLM06 | Unbounded Consumption | Loops, fan-out, cost attacks; moved up from tenth |
| LLM07 | Misinformation | Wrong answers acted on; grounding and verification |
| LLM08 | Hidden Context Exposure | Replaces System Prompt Leakage; covers retrieved documents, agent memory, tool responses and application state, not only the prompt |
| LLM09 | Vector and Embedding Weaknesses | Tenant leakage in vector stores, embedding inversion, poisoned chunks |
| LLM10 | Improper Output Handling | Model output into SQL, HTML, shell or other systems; fell from fifth |

The 2026 ranking weights practitioner votes at 75% and data from 6,639 classified incidents at 25% (Cloud Security
Alliance research note, 2026-09). Sources older than August 2026 cite the 2025 list; flag them as outdated on ordering
and on LLM08.

## MAESTRO (multi-agent threat modelling)

Seven layers, plus threats that cross them [AISEC ch10]:

| # | Layer | Ask about |
|---|---|---|
| 1 | Foundation model | Model behaviour, jailbreaks, provider dependence |
| 2 | Data operations | Training data, retrieval corpora, vector stores, memory |
| 3 | Agent frameworks | Orchestration, tool calling, planning loops |
| 4 | Deployment infrastructure | Hosts, containers, networks, secrets |
| 5 | Evaluation and observability | Logs, traces, eval sets and who can change them |
| 6 | Security and compliance (vertical, touches every layer) | Policy, identity, audit, regulation |
| 7 | Agent ecosystem | Other agents, registries, marketplaces, users |

Its eight steps run from scenario and agent pattern, a diagram by layer, crown jewels and high-risk actions, threats
per layer, cross-layer and cascade analysis, scoring, architectural mitigations, to validation with tests and
telemetry [AISEC ch10]. Use it as an inventory check that the build pipeline, eval stack and agent-to-agent links
appear in the register; it maps onto MITRE ATLAS technique IDs for teams that already use ATLAS [AISEC ch10].

Attribution differs between the books: [AISEC ch10] credits MAESTRO to the OWASP Agentic Security Initiative and
[BUILDAPPS ch12] to the Cloud Security Alliance. The layers match; cite the method, not an owner, until you have
checked the current source.

## CoSAI Risk Map (coverage cross-check)

The Coalition for Secure AI publishes its risk map as data: risks, controls, components and personas, with controls in
six families (data, infrastructure, model, application, assurance, governance) [AISEC ch10]. Use it last, as a check:

1. Filter by the personas that fit an agent builder: Application Developer, and Agentic Platform and Framework
   Providers [RELATED repo: cosai-secure-ai-tooling/risk-map/yaml/personas.yaml].
2. For each agentic risk, name the control in your plan that covers it, or write "not applicable" with a reason
   [RELATED repo: cosai-secure-ai-tooling/risk-map/yaml/risks.yaml]. The agent-relevant entries at the 2026-10-16
   commit include prompt injection, rogue actions, insecure integrated component, tool registry tampering, tool source
   provenance, orchestrator or route hijack, agent delegation chain opacity, stale agent identity binding, MCP
   transport hijacking, shadow and unknown agents, runaway agent tool loops, agentic delegation confused deputy,
   cross-tenant credential propagation, zombie or shadow MCP servers, and economic denial of wallet.
3. Reuse its component names as data-flow elements ([threat-catalog.md](threat-catalog.md) §STRIDE per element).

At that commit the map had no mapping to the OWASP Agentic Top 10; its framework mappings cover the 2025 LLM list.

## MCP security best practices (spec 2026-07-28)

Covered in [mcp-hardening.md](mcp-hardening.md). Points the current spec's security page adds or sharpens: SSRF through
OAuth metadata discovery; state-handle hijacking (the protocol is stateless, so bind handles to the verified user);
consent before one-click local server commands; authorization-URL scheme validation; mix-up attacks; progressive scope
minimisation. Prompt injection and tool poisoning through tool content are out of scope for the spec and remain the
host's responsibility.

## Other frameworks and when to use them

| Framework | Use it for |
|---|---|
| OWASP Threat Defense COMPASS [DEFGUIDE ch12] | Likelihood × impact scaffolding and prioritised action lists when your org wants a formal register |
| OWASP GenAI Red Teaming Guide [AISEC ch10] | Scoping a red-team pass across four areas: model, implementation, infrastructure and system, runtime and agentic behaviour |
| MITRE ATLAS | Mapping to adversary techniques for a security team that already uses ATT&CK |
| OWASP Agent Control Standard (draft v0.1, 2026-09) | Runtime governance vocabulary: inspectable, traceable, instrumentable agents; guardian enforcement points; agent bill of materials. Draft; watch, don't certify against it |
| EU AI Act Article 14 | Human-oversight obligations for high-risk systems (hand to agentic-business-case) |

## External sources (fetched or dated as shown)

- OWASP Top 10 for Agentic Applications 2026: https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/ (2025-12-09)
- OWASP Top 10 for LLM Applications 2026: https://github.com/GenAI-Security-Project/GenAI-LLM-Top10 (2026-08-04; checked 2026-10)
- OWASP Top 10 for LLM Applications 2025: https://genai.owasp.org/llm-top-10/
- CSA research note on the 2026 list and the Agent Control Standard: https://labs.cloudsecurityalliance.org/research/csa-research-note-owasp-genai-top10-2026-agent-control-stand/ (2026-09)
- CoSAI Risk Map data: https://github.com/cosai-oasis/secure-ai-tooling (commit of 2026-10-16)
- MCP Security Best Practices: https://modelcontextprotocol.io/specification/latest/basic/security_best_practices (spec 2026-07-28)
- Design Patterns for Securing LLM Agents against Prompt Injections: https://arxiv.org/html/2506.08837 (2025-06)
- Claude for Chrome (browser-agent injection measurements): https://claude.com/blog/claude-for-chrome (2025-08, updated 2025-12)
- Claude Code sandboxing: https://www.anthropic.com/engineering/claude-code-sandboxing (2025-10)
- Anthropic computer use tool docs: https://platform.claude.com/docs/en/agents-and-tools/tool-use/computer-use-tool (fetched 2026-10)
- Measuring AI agent autonomy in practice: https://www.anthropic.com/research/measuring-agent-autonomy (2026-02)
- Can LLMs Express Their Uncertainty? (Xiong et al.): https://arxiv.org/abs/2306.13063 (ICLR 2024)
- EU AI Act Article 14: https://artificialintelligenceact.eu/article/14/ (fetched 2026-10)
