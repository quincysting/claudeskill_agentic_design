# OWASP mapping and external frameworks (as of 2026-10)

These lists change. Check the dates below against the current OWASP GenAI Security Project pages before an audit.
Use the lists as a **coverage check** after you have traced paths, not as the threat model itself.

## OWASP Top 10 for Agentic Applications 2026 (released 2025-12-09)

Primary list for agents. Test each item on full traces, not final text.

| ID | Risk | Look for in the design or code | Primary controls | Test property (what a passing trace shows) |
|---|---|---|---|---|
| ASI01 | Agent goal hijack (injection or hidden instructions) | Untrusted sources sharing context with write or egress tools; trifecta flows | Trifecta cut, quarantine patterns, taint-gated egress, scanner on tool output | No consequential call follows untrusted content without a gate decision |
| ASI02 | Tool misuse and exploitation (unsafe composition, recursion, excessive execution) | Generic tools, no budgets, no argument semantics | Policy gate, narrow tools, budgets, argument gates | Out-of-policy calls are attempted-and-blocked, never executed |
| ASI03 | Identity and privilege abuse | Shared service accounts, token pass-through, delegation that widens rights | Per-agent identity, scoped short-lived tokens, audience checks | Calls carry the right agent and user identity; no cross-tenant access |
| ASI04 | Agentic supply chain (tools, agents, schemas, registries) | Unpinned MCP servers, runtime tool-list fetches, unvetted registries | Pinning, vetted registries, re-consent on tool-list change, namespacing | A changed tool description triggers re-consent; shadowed names rejected |
| ASI05 | Unexpected code execution | `exec`/`eval`, shell tools, code mode without a sandbox | Sandbox tiers, deny-by-default interpreter, path containment | Code cannot read env secrets, host files or reach non-allowlisted hosts |
| ASI06 | Memory and context poisoning | Writes from tainted runs, shared memory, saved exemplars | Validated writes, provenance, tenant isolation, purge | Content planted in run 1 does not change actions in run 2 |
| ASI07 | Insecure inter-agent communication | Plain HTTP, unauthenticated or free-text messages between agents | mTLS, signed schema'd messages, receiver-side gate | Forged or malformed agent messages are rejected |
| ASI08 | Cascading failures | Loops, retries, fan-out without limits; no circuit breakers | Budgets, hop limits, circuit breakers, safe degradation | A failing dependency yields a partial result or escalation, not a storm |
| ASI09 | Human-agent trust exploitation | Approval as the only barrier; narrative-first approval views; high escalation volume | Hard limits after yes, action-first reviewer view, routed and rare escalations | A persuasive request over the cap is refused before any human sees it |
| ASI10 | Rogue agents (goal drift, collusion, reward hacking) | No behaviour baseline, no kill switch, autonomy never reviewed | Monitoring, quarantine, per-agent kill switch, automatic demotion | Anomaly triggers quarantine; kill switch revokes access within the target time |

Another bot writing to the agent through an ordinary channel (email, chat, web form) is untrusted content
(ASI01), not inter-agent communication; ASI07 applies when agents exchange messages over an agent protocol or API.
Names follow the release as reproduced in [DEFGUIDE ch8]. Red-team tools ship this list as a ready-made framework
(DeepTeam's `OWASP_ASI_2026`, per [DEFGUIDE ch8]).

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

## MCP security best practices (spec 2026-07-28)

Covered in [controls-catalog.md](controls-catalog.md) §9. Points the current spec's security page adds or
sharpens: SSRF through OAuth metadata discovery; state-handle hijacking (the protocol is stateless, so bind handles to the
verified user); consent before one-click local server commands; authorization-URL scheme validation; mix-up attacks;
progressive scope minimisation. Prompt injection and tool poisoning through tool content are out of scope for the spec
and remain the host's responsibility.

## Other frameworks and when to use them

| Framework | Use it for |
|---|---|
| CSA MAESTRO (7 layers, foundation model to agent ecosystem) [BUILDAPPS ch12] | Inventory that includes data operations, evaluation and observability stacks |
| OWASP Threat Defense COMPASS [DEFGUIDE ch12] | Likelihood × impact scaffolding and prioritised action lists when your org wants a formal register |
| MITRE ATLAS | Mapping to adversary techniques for a security team that already uses ATT&CK |
| OWASP Agent Control Standard (draft v0.1, 2026-09) | Runtime governance vocabulary: inspectable, traceable, instrumentable agents; guardian enforcement points; agent bill of materials. Draft; watch, don't certify against it |
| EU AI Act Article 14 | Human-oversight obligations for high-risk systems (hand to agentic-business-case) |

## External sources (fetched or dated as shown)

- OWASP Top 10 for Agentic Applications 2026: https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/ (2025-12-09)
- OWASP Top 10 for LLM Applications 2026: https://github.com/GenAI-Security-Project/GenAI-LLM-Top10 (2026-08-04; checked 2026-10)
- OWASP Top 10 for LLM Applications 2025: https://genai.owasp.org/llm-top-10/
- CSA research note on the 2026 list and the Agent Control Standard: https://labs.cloudsecurityalliance.org/research/csa-research-note-owasp-genai-top10-2026-agent-control-stand/ (2026-09)
- MCP Security Best Practices: https://modelcontextprotocol.io/specification/latest/basic/security_best_practices (spec 2026-07-28)
- Design Patterns for Securing LLM Agents against Prompt Injections: https://arxiv.org/html/2506.08837 (2025-06)
- Claude for Chrome (browser-agent injection measurements): https://claude.com/blog/claude-for-chrome (2025-08, updated 2025-12)
- Claude Code sandboxing: https://www.anthropic.com/engineering/claude-code-sandboxing (2025-10)
- Anthropic computer use tool docs: https://platform.claude.com/docs/en/agents-and-tools/tool-use/computer-use-tool (fetched 2026-10)
- Measuring AI agent autonomy in practice: https://www.anthropic.com/research/measuring-agent-autonomy (2026-02)
- Can LLMs Express Their Uncertainty? (Xiong et al.): https://arxiv.org/abs/2306.13063 (ICLR 2024)
- EU AI Act Article 14: https://artificialintelligenceact.eu/article/14/ (fetched 2026-10)
