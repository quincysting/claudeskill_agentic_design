# Agent governance and operating-model plan: <organisation>

Date: <YYYY-MM-DD> · Owner of this plan: <name> · Scope: <business units, agent count, stacks>

## 1. Current estate

| Agent | Team | Stack | Reads / writes | Systems of record | Personal data | In production? | Owner today | Proposed tier | EU AI Act class |
|---|---|---|---|---|---|---|---|---|---|

Trigger for governance: <first agent writing to a system of record / second team building / regulated use>
Main gaps: <unregistered agents, direct vendor API keys, no traces, no owners, ...>

## 2. Register

- Agent registry: <tool/location>; schema = minimum fields (name@version, business + safety owner, purpose, non-responsibilities, policies, tier, allowed tools/collaborators/models, decision rights, certification record, config fingerprint, lifecycle state, cost ceiling, regulatory flags)
- Action catalog: <first shared actions to catalogue>
- Model registry: <approved models, pinned versions>
- Prompt/config registry: <where, tied to eval suites>
- Registration enforced by: <deploy pipeline step + control-plane refusal>

## 3. Tiers and certification

| Tier | Definition here | Before production | Recertify on | Approver |
|---|---|---|---|---|
| T0 | | | | |
| T1 | | | | |
| T2 | | | | |
| T3 | | | | |

Certification evidence: <eval suite owner, red team, log sampling> · Certificate binds: version + config fingerprint + policies

## 4. Enforce and prove

- Control plane / gateway: <what it checks on each call; who owns it>
- Cost ceilings: <per agent / workflow / BU>
- Audit trail: <fields, storage, retention (≥6 months for EU high-risk deployers), who may read traces>
- Kill switch and suspension: <per agent / fleet; who can pull it>

## 5. Accountability

| Area | Owner |
|---|---|
| Business purpose and outcomes | |
| Model, data and agent competence | |
| Policy, ethics and legal compliance | |
| Operations, incidents and change | |

Second-layer RACI per T2/T3 agent: scope of judgment · forced-escalation thresholds · data and authority boundaries · conflict handling · minimum trace. Each enforced in code at: <...>
Liability: <contract clauses with vendors, insurance, documented oversight>

## 6. Operating model

| Unit | Owns | Answers for |
|---|---|---|
| Central platform team | | |
| BU agent teams | | |
| Enabling teams | | |
| Legal / risk / compliance | | |

Governance body: <existing committee extended / new council: steering, CoE, champions, ethics review>; every decision ends as a registry field.
Roles to staff first: <agent owner, governance/certification lead, agent SRE, eval supervisor, ...>
Platform service levels: <...>

## 7. Lifecycle

Intake check (reject tasks a plain program does better) → define → build/test → certify/register → staged rollout → operate → recertify / suspend → retire (revoke credentials, archive, notify users). Credential-vs-registry reconciliation every <period>.

## 8. Portability

- Model access layer: <gateway; providers reachable>
- Prompt portability: <intent vs model-specific wording; eval per target model>
- Eval assets export: <yes/no per tool>
- Sprint test: could <agent> move provider within a sprint? <yes/no, gap>

## 9. Regulation (not legal advice)

| Use case | Annex III? | 6(3) derogation? (never with profiling) | Role (provider/deployer) | Duties | Applies from |
|---|---|---|---|---|---|

Art. 50 disclosures: <channels> · Worker information: <when, to whom> · FRIA/DPIA: <needed?> · GDPR Art. 22: <...> · Counsel review by: <date>

## 10. Workforce transition

Augmentation-first principle · notice and redeployment · appeal path for agent decisions on roles or pay · reskilling plan · transition council membership.

## 11. Sequence

| Phase | Window | Deliverables | Exit check |
|---|---|---|---|
| 0 Inventory and stop the bleeding | <weeks> | estate list, owners named, keys rotated into gateway | every production agent registered |
| 1 Day-1 minimum | | registry + gateway + traces + kill switch | control plane refuses unregistered agents |
| 2 Tiers and certification | | tier per agent, T2/T3 certified | no T2/T3 agent without a valid certificate |
| 3 Scale | | action catalog, templates, automated recertification | time from idea to production, reuse rate tracked |
