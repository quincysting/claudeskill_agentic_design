# Governance and operating model for an agent estate

Load this for Mode B. One agent is a project. Fifty agents built by different teams on different stacks are an estate, and an estate raises questions no single agent's design answers. What exists? Who answers for each agent? What may it touch? How does a change get re-approved? How is an agent retired, and how do you leave a vendor?

## 1. The model: register, enforce, prove

- **Register.** Every agent that can run in production has a record: identity, owner, purpose, what it may touch, certification. MESH calls the registry the system of record for agents, policies, certifications and users [MESH ch9]. ENTERPRISE asks for a central repository of every agentic system with a live list of policies, audited while they run [ENTERPRISE ch6].
- **Enforce.** One control plane (orchestrator or gateway) reads those records and checks every call before it reaches a model, tool or another agent. The owner of an agentic system owns its orchestrator [ENTERPRISE ch7]. Domain agents get no direct route to models, systems or each other. That is why enforcement can be architectural rather than behavioural: people found workarounds to service catalogs, but agents can be forced by design to call governed services [ENTERPRISE ch8].
- **Prove.** The control plane writes a trace of plan, tool calls, approvals, version and owner into tamper-evident storage. The evidence goes back to owners and certifiers, who recertify, restrict or revoke [MESH ch12], [ENTERPRISE ch7].

Principles to open the operating model with: humans remain accountable; autonomy is earned, not given; logs are the source of truth [MESH ch13]. Policies "unless translated into machine-enforceable rules, are insufficient" [MESH ch13].

**When to start.** When the first agent writes to a system of record, or when a second team starts building agents. Aim for "directionally correct and incrementally improvable" [ENTERPRISE ch8], not the full apparatus on day one.

| Day-1 minimum | Add as the estate grows |
|---|---|
| Registry with owner, purpose, tier, tools, model version; deploy pipeline refuses unregistered agents | Certification workflow with expiry; configuration fingerprints |
| Model calls through one gateway; cost metered per agent | Governed action catalog shared across agents |
| Traces retained with agent version and owner | Tamper-evident audit store; tiered access to traces |
| Named business owner and safety owner per agent | Fleet managers; platform SLAs; certified templates |
| Kill switch and credential revocation per agent | Automated recertification triggers from drift and error budgets |

## 2. Four registries, not one

| Registry | Holds | Notes |
|---|---|---|
| Agent registry | One record per agent (schema below) | Marketplace or search UI sits on top [MESH ch7] |
| Action / tool catalog | Reusable business capabilities behind stable APIs: "create ticket", "update address" | Catalogue each action once. Otherwise three departments build three credit-risk agents that classify one applicant three ways [ENTERPRISE ch8]. For MCP servers, run a private subregistry of vetted servers behind a gateway [MCP ch9] |
| Model registry | Owner, version, certification, usage restrictions per model | No agent may reach an unapproved model [MESH ch15]. JPMorganChase registers every model and sends high-risk client-facing uses through independent validation [ENTERPRISE ch4] |
| Prompt / config registry | Prompts, tool definitions, model configs as versioned assets tied to eval suites | Needed for portability and recertification [ENTERPRISE ch8] |

Runtime traces live in the observability store, linked to the registry by agent ID and version.

**Agent registry minimum schema** (MESH ch9's entity model plus the governance fields spread across MESH and ENTERPRISE):

| Field | Why |
|---|---|
| namespace:name, SemVer version | Identity; a fork or rename never inherits permissions [MESH ch12] |
| Business owner, safety owner (named people) | Accountability for value and for risk [MESH ch13] |
| Purpose (specific), non-responsibilities | A breach becomes a verifiable event. "Drafts replies to customer emails using ticket history" is a purpose; "optimise user experience" is not [MESH ch12], [ENTERPRISE ch6] |
| Policies attached | Constraints such as "never send directly to customers" |
| Risk tier | Sets certification depth and what the control plane passes |
| Allowed tools / actions, allowed collaborators, pinned model versions | Default deny |
| Decision rights: autonomous / pre-approval / post-review per action class | MESH's "digital employee" framing [MESH ch13] |
| Certification record: issuer, date, version, policies covered, state, expiry | [MESH ch8] |
| Configuration fingerprint (hash of prompts, tools, model version) | Proves the running config is the certified one [ENTERPRISE ch6] |
| Lifecycle state, dependants, cost ceiling | Retirement, impact analysis, spend control |
| Regulatory flags: personal data, EU AI Act class, log retention | Drives the audit and oversight duties |

MESH lists what a production registry still needs: schema evolution, change events, immutable access logs, concurrency control, soft delete and archival, staged approvals with rollback, identity-provider integration, encryption, scale, usage analytics, disaster recovery [MESH ch9]. Treat it as the build backlog.

**Standards status (as of 2026-10).** No standard agent registry exists, so keep the schema your own. The official MCP Registry is in preview, holds metadata only, and recommends running a private registry on its OpenAPI spec ([MCP Registry](https://modelcontextprotocol.io/registry/about), external). A2A publishes Agent Cards but "does not prescribe a standard API for curated registries" ([A2A agent discovery](https://a2a-protocol.org/latest/topics/agent-discovery/), external). NIST's NCCoE concept paper on agent identity (Feb 2026) drew comments that mostly favour composing existing standards: OAuth 2.0, token exchange, SPIFFE/SPIRE, WIMSE, MCP, A2A, Verifiable Credentials ([NIST NCCoE](https://csrc.nist.gov/pubs/other/2026/02/05/accelerating-the-adoption-of-software-and-ai-agent/ipd), external).

## 3. Risk tiers and certification weight

How heavy governance should be is disputed. MESH is heaviest: seven trust layers and UL-style certification [MESH ch12], [MESH ch5]. BUILDAPPS wants it "lightweight and flexible" [BUILDAPPS ch1]. **Verdict: tier it.** No book measures what its process costs or prevents. Use capability tiers [ENTERPRISE ch8], which MESH itself allows for low-risk agents [MESH ch5]. The classes below merge ENTERPRISE ch8, SYSTEMS ch18 (read-only; drafting for approval; executing low-risk tasks; blocked from sensitive systems) and MESH ch13's policy catalog.

| Tier | Agent does | Before production | Recertify | Runtime |
|---|---|---|---|---|
| T0 Read-only | Reads, summarises, drafts for the person who asked | Register; automated checks in pipeline | On model/prompt/tool change; 12-month expiry | Logs; cost ceiling |
| T1 Drafts for approval | Proposes actions a person approves before effect | Register; eval suite passes; platform review | On change; 12 months | Approval UI; approval and override rates tracked |
| T2 Acts within limits | Writes to systems of record within coded caps; customer-facing | Full certification: evals, red team, policy tests; business and safety owner; error budget; kill switch | On change; 6-12 months; on budget breach | Caps in code; sampled audits; autonomy reduced automatically on breach |
| T3 High-risk | Decisions about people (hiring, credit, insurance, benefits), safety, large money, or EU AI Act high-risk | T2 plus independent validation and risk/legal sign-off; regulatory duties mapped | On change; 6 months | Human oversight with authority; logs kept to legal minimum |

Error-budget autonomy: value SLOs (completion, cycle time, cost to serve, satisfaction) and safety SLOs (escalations, overrides, hallucination incidents, privacy violations). If an agent exceeds its budget, autonomy is cut or paused automatically [MESH ch13]. Per-action approval routing belongs to agent-threat-modeler.

**Certification.**
- Evidence: the eval suite (agent-eval-designer), red-team results, production logs. Evaluators stress edge cases, ambiguous prompts, conflicting constraints and adversarial inputs [MESH ch12].
- Record: a signed statement of which version passed which suite against which policies, with issuer, date, state (provisional, approved, expired, revoked) [MESH ch8].
- Triggers: any meaningful change (model swap, prompt rewrite, new tool) [MESH ch13], expiry, drift or error-budget alerts [MESH ch12]. Pin model versions: behind a floating alias the provider can change the model with no change on your side.
- Don't certify after one audit and move on. Keep sampling transactions [ENTERPRISE ch6].
- At scale, certification has to be the automated outcome of pipeline tests, or it "would grind the system to a halt" [MESH ch15]. A certificate is then only as good as its suite.
- Certified templates: if a template restricts what may change (e.g. only the data source), certify it once [MESH ch14]. A shared SDK update changes every agent built on it, so run the template's regression suite first.

**Admission check at the control plane** (a sketch of the registry side; workload identity and per-action policy come from agent-threat-modeler):

```python
import hashlib, json, time

def fingerprint(prompts: dict, tools: list, model_version: str) -> str:
    blob = json.dumps({"p": prompts, "t": sorted(tools), "m": model_version}, sort_keys=True)
    return hashlib.sha256(blob.encode()).hexdigest()

def admit(rec: dict, running_hash: str, tool: str) -> tuple[bool, dict]:
    checks = {
        "registered": rec is not None,
        "certified": bool(rec) and rec["cert_expires"] > time.time() and (
            rec["cert_state"] == "approved"
            or (rec["cert_state"] == "provisional" and rec["tier"] == "T0")),
        "unchanged": bool(rec) and running_hash == rec["certified_hash"],  # certified == deployed
        "tool_allowed": bool(rec) and tool in rec["tools"],                 # default deny
    }
    return all(checks.values()), checks  # write checks + agent@version + owner to the audit log
```

A failed `unchanged` check opens a recertification task for the named owner.

## 4. Accountability and liability

Four areas, each with a named owner [ENTERPRISE ch7]: business purpose and outcomes; model, data and agent competence; policy, ethics and legal compliance; operations, incidents and change.

**Second layer of RACI.** A classic RACI governs a fixed artifact. With agents you approve a space of behaviours, so someone must own [ENTERPRISE ch7]:
1. the scope of judgment the agent may exercise;
2. thresholds that force escalation regardless of the agent's confidence;
3. data and authority boundaries;
4. how conflicts between goals or instructions are handled;
5. the minimum trace needed to reconstruct a decision.

All five are enforced as hard rules in orchestration and tools, not left to the model. Natural-language policy is not a control: ENTERPRISE reports an agent that deleted over two hundred emails after context compression likely dropped its "wait for approval" instruction [ENTERPRISE ch7]. Write policies in plain language for people and tests; enforce them in code.

Liability stays with the deploying organisation, its decision-makers and vendors. Agents are tools, not legal persons. Use contracts that allocate responsibility, documented oversight, audit logs and insurance [ENTERPRISE ch4].

## 5. Operating model

MESH's five pillars [MESH ch13]: **structure** (owners, decision rights), **process** (lifecycle from intake to retirement), **technology** (registry, policy decision point, immutable logs, regression pipelines, identity), **policy** (enforced at runtime), **metrics** (value and safety SLOs).

**Central platform, federated builders** [ENTERPRISE ch8], [MESH ch13]:

| Who | Owns | Answers for |
|---|---|---|
| Central platform team | Agent platform, gateway, registry, evaluation framework, cross-cutting agents (e.g. enterprise search), paved-road templates | Platform reliability, security posture, policy enforcement |
| Business-unit agent teams | Domain agents, prompts, workflows, KPIs | Each agent's value and safety |
| Enabling teams: governance, architecture, red team, security, training | Standards, reviews, certification support | Quality of the gates |
| Legal, risk, compliance | Consulted on T2/T3 | Regulatory interpretation |

The platform needs an owner and service levels too. EVALS gives a shared eval library a named owner, light SLAs (a 100-case judged suite in five minutes, bugs triaged within a business day), semantic versioning and two-to-four-week migration windows [EVALS ch15].

**Agent team roles** (roles, not necessarily people) [MESH ch13]: agent owner (purpose, value, risk, autonomy boundaries); agent engineers (prompts, tool contracts, retrieval, guardrails, unit economics); agent SREs (SLOs, error budgets, incidents, kill switches); governance and certification lead (policy turned into tests, tiers, certification); evaluation and human-in-the-loop supervisor (golden suite, regressions, escalation and override rates as drift signals); policy and ethics liaison; release manager (canaries, rollback, evidence before release). Above several teams: a fleet manager per mission-aligned fleet [MESH ch13].

**Governance bodies.** In mature organisations, extend the existing chief AI, data and risk roles and committees: approve high-risk use cases, set logging standards, review incidents, report to the board [ENTERPRISE ch7]. Without them, AGENTICAI's global bank used three tiers: a steering committee, a centre of excellence that standardised and checked compliance, AI champions per department, plus an ethics board reviewing major implementations early enough to change them [AGENTICAI ch10]. A committee decision must end as a registry field the control plane reads. Otherwise approvals happen in meetings while the agent runs with whatever access its developer gave it.

**Timing**: encourage experiments early, avoid premature standardisation on one framework, standardise per large group once patterns emerge [BUILDAPPS ch1]. A paved road makes the governed path the fast one.

**What unit to own**: give one owner the end-to-end outcome (a mission-aligned fleet [MESH ch13]) built from shared governed actions. That avoids both department-shaped silos and duplicated capabilities [AGENTICAI ch10], [ENTERPRISE ch8].

## 6. Lifecycle

```
intake -> define (purpose, owner, tier) -> build & test -> certify & register -> staged rollout -> operate
operate --model/prompt/tool change or expiry--> recertify --pass--> operate
operate --error budget breached--> suspended --fix recertified--> operate
any gate fails --> rejected
operate --> retire: revoke credentials, archive record and logs, notify users, name a replacement
```

At intake, reject tasks a plain program does better, such as anything needing exactly repeatable output [MESH ch14]. At retirement, a retired agent that still holds credentials is a "zombie" [MESH ch12]. Reconcile live credentials against the registry on a schedule.

## 7. Lock-in and portability

- **Neutral model access layer**: one internal API over several providers. Grab's gateway routes to several clouds and in-house models and normalises prompts, safety controls, auth and observability [ENTERPRISE ch8]. Only approved models are reachable [MESH ch15].
- **Prompts don't port for free.** They degrade silently on another model. Separate intent from model-specific wording and run the eval suite per target model before switching [ENTERPRISE ch8].
- **Data and tools** in formats and accounts you control; tool contracts on open protocols (MCP) behind your gateway.
- **Evaluation assets export**: datasets, annotations with provenance, per-case results, scorer configs, without the vendor's tool [EVALS ch12].
- Orchestration vendors all want to be "the layer your agents cannot do without" [ENTERPRISE ch8]. Apply the same scrutiny there.
- Test: could you move one agent to another provider within a sprint, prompts and evals included?
- Cost of neutrality: a gateway adds milliseconds and some tokens. That's small for most workflows and a hard constraint for real-time scoring, so measure it [ENTERPRISE ch8]. Keep inline checks deterministic and write traces asynchronously.

## 8. Migrating an existing estate [ENTERPRISE ch8]

1. Audit which agents moved from experiment to core workflow (include low-code agents: they multiply, and so do their bills [AGENTICAI ch12]).
2. Put the gateway and catalog in front without touching business logic. That buys observability and policy enforcement at once.
3. Migrate tools, prompts and data access to governed, portable formats one agent at a time, highest risk first.
4. Retire point-to-point integrations as governed services appear.

## 9. Cost governance

Runtime cost limits per agent and unit economics per task [MESH ch13]; cost ceilings per workflow or business unit enforced by orchestration, because costs compound as agents call agents [ENTERPRISE ch8]. Mechanics: agent-ops-reviewer.

## 10. Workforce transition

BUILDAPPS cites Klarna replacing roughly 700 customer-service roles with a chatbot in 2024 and rehiring by mid-2025 after complaints rose [BUILDAPPS ch13]. MESH's transition practices [MESH ch13]:
- augmentation first;
- human review and appeal for any agent decision affecting a worker's role, pay or career, with audit logs;
- advance notice, coaching, redeployment paths;
- role-specific reskilling (e.g. admin staff to supervise agents and handle exceptions);
- transition councils with HR, legal, ethics, operations, tech and employee representatives;
- staged autonomy;
- metrics on engagement and retention alongside value.

In the EU, deployers of high-risk systems at work must inform workers' representatives and affected workers before use (see eu-ai-act-2026-10.md).
