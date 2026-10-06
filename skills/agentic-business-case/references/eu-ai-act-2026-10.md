# EU AI Act and agents: dates and duties (as of 2026-10)

Status: checked 2026-10-06 against the AI Act Explorer timeline (page updated 2026-08-31) and Orrick's summary of the Digital Omnibus amendments, published in the Official Journal on 29 July 2026. Dates in the books predate the Omnibus; use these. This is a screening aid, not legal advice. Confirm classification and duties with counsel, and re-check the timeline before relying on a date.

## 1. Timeline

| Date | What applies |
|---|---|
| 1 Aug 2024 | Act in force; no duties yet |
| 2 Feb 2025 | Prohibited practices (Art. 5) and AI-literacy duty (Art. 4) |
| 2 Aug 2025 | General-purpose AI (GPAI) model obligations, governance, penalties regime. GPAI models already on the market before this date have until 2 Aug 2027 |
| 29 Jul 2026 | Digital Omnibus amendments published; they moved the high-risk dates below |
| 2 Aug 2026 | The rest of the Act applies generally, including Art. 50 transparency. Synthetic-content systems already on the market have until 2 Dec 2026 for the Art. 50(2) marking duty |
| 2 Dec 2026 | New prohibitions: generating non-consensual intimate imagery and child sexual abuse material |
| 2 Aug 2027 | Pre-Aug-2025 GPAI models must comply |
| **2 Dec 2027** | **High-risk requirements for Annex III (stand-alone) systems.** Systems placed on the market or put into service before this date are caught only if substantially modified afterwards |
| 2 Aug 2028 | High-risk requirements for Annex I systems (AI in products under EU harmonisation law, e.g. machinery, medical devices) |
| 31 Dec 2030 | Large-scale EU IT systems (Annex X) |

Penalties: up to EUR 35M or 7% of worldwide turnover for prohibited practices; up to EUR 15M or 3% for most other breaches; up to EUR 7.5M or 1% for supplying incorrect information.

## 2. Classification is by use, not by technology

The Act doesn't name agents. ENTERPRISE notes it treats many agentic uses as high-risk when they affect safety, fundamental rights, finance or employment [ENTERPRISE ch7]. An agent is classified by its intended purpose. The same orchestration code can be minimal-risk in one deployment and high-risk in another.

**Annex III areas** (abridged):
1. Biometrics: remote identification, categorisation by sensitive attributes, emotion recognition.
2. Critical infrastructure: safety components in digital infrastructure, traffic, water, gas, heating, electricity.
3. Education: admission, assessing learning outcomes, steering learning, proctoring.
4. **Employment and workers' management**: recruitment and candidate screening or ranking; decisions on terms, promotion or termination; allocating tasks based on behaviour or traits; monitoring and evaluating performance.
5. **Essential private and public services**: eligibility for public benefits; **creditworthiness and credit scoring** (fraud detection excluded); **risk assessment and pricing for life and health insurance**; emergency-call triage.
6. Law enforcement. 7. Migration, asylum, border control. 8. Administration of justice and democratic processes.

**Art. 6(3) derogation.** An Annex III system is not high-risk if it poses no significant risk and only (a) performs a narrow procedural task, (b) improves the result of a completed human activity, (c) detects patterns or deviations from prior decisions without replacing or influencing the human assessment without proper review, or (d) performs a preparatory task. **It never applies if the system profiles natural persons.** A provider relying on it must document the assessment before placing the system on the market and register it (Art. 6(4)).

Agent examples:
- An agent that ranks job applicants is high-risk (Annex III 4, profiling).
- An agent that only extracts CV fields into a form a recruiter fills in may fall under 6(3)(d). Document why.
- An agent that sets credit limits for consumers is high-risk. A fraud-signal agent is excluded from 5(b). B2B credit for companies is outside 5(b), which concerns natural persons.
- A customer-service agent answering order questions is not high-risk, but Art. 50 transparency applies.

## 3. Provider or deployer?

- **Provider**: develops an AI system and places it on the market or puts it into service under its own name. **An organisation that builds a high-risk agent for its own use is its provider.**
- **Deployer**: uses an AI system under its authority.
- A deployer becomes a provider (Art. 25) if it puts its name on a high-risk system, substantially modifies one, or changes the intended purpose of a system so that it becomes high-risk. Example: repurposing a general assistant platform to screen applicants.
- GPAI model duties sit with the model provider. Substantially modifying or fine-tuning a GPAI model can make you a provider of the modified model; check with counsel.

## 4. Duties that land on an agent estate

**Everyone (from 2 Aug 2026), Art. 50**: people interacting directly with an AI system must be told so, unless it's obvious. Synthetic audio, image, video or text output must be machine-detectably marked (providers). Deepfakes, and AI-generated text published to inform the public, must be disclosed (deployers; the text duty lapses where a human reviews and takes editorial responsibility).

**High-risk providers (Annex III from 2 Dec 2027)**: risk management (Art. 9), data governance (Art. 10), technical documentation (Art. 11), automatic event logging over the system's lifetime so risks, substantial modifications and operation can be traced (Art. 12), instructions for deployers (Art. 13), human-oversight design (Art. 14), accuracy, robustness, cybersecurity (Art. 15), quality management system (Art. 17), conformity assessment (internal control for most Annex III areas), EU database registration (Art. 49), post-market monitoring and serious-incident reporting.

**High-risk deployers (Art. 26)**:
- use per the provider's instructions;
- assign human oversight to people with the competence, training and authority for it, and support them;
- ensure input data under their control is relevant and sufficiently representative;
- monitor operation; report risks and serious incidents to the provider and authorities;
- keep automatically generated logs for a period appropriate to the purpose, **at least six months** unless other EU or national law says otherwise;
- **before using a high-risk system at work, inform workers' representatives and affected workers**;
- inform people subject to decisions made or assisted by the system that it is being used.

**Fundamental rights impact assessment (Art. 27)**, before first use: deployers that are public bodies or private entities providing public services, and deployers of credit-scoring or life/health-insurance pricing systems.

**Right to explanation (Art. 86)**: people affected by a decision based on a high-risk Annex III system's output, with legal or similarly significant effects, can ask the deployer for a clear explanation of the system's role.

## 5. Mapping duties to governance controls

| Duty | Control in the estate (governance-operating-model.md) |
|---|---|
| Classify each use (Annex III, 6(3), Art. 50) | Registry field "EU AI Act class", set at intake and re-checked when purpose changes |
| Logging and traceability (Art. 12, 26) | Control-plane trace of plan, tool calls, approvals, version, owner; tamper-evident storage; retention ≥ 6 months, or longer where sector law requires. Traceability is met at orchestrator and workflow level, since model internals can't be replayed [ENTERPRISE ch7] |
| Human oversight with authority (Art. 14, 26) | Named safety owner; T3 tier; approvers with authority to override and stop; training records |
| Substantial modification | Recertification trigger on model, prompt or tool change; a change log tied to the configuration fingerprint |
| Inform workers before workplace use (Art. 26) | Step in the workforce-transition plan, before the pilot, not after |
| Inform affected persons; explanation (Art. 26, 86) | Notice in the customer or applicant flow; decision trace good enough to explain the agent's role |
| Monitoring and incident reporting | Agent SRE on-call, incident runbook with a regulatory-notification step |
| AI literacy (Art. 4) | Training for builders, approvers and users of agents |
| Transparency to users (Art. 50) | "You are talking to an AI agent" disclosure in customer-facing channels |

## 6. Other regimes to check alongside

- **GDPR Art. 22**: solely automated decisions with legal or similarly significant effects on a person need a legal basis (contract necessity, law, or explicit consent) plus safeguards: human intervention, the chance to contest. Data protection impact assessment (Art. 35) for high-risk processing.
- Sector rules: EU financial services in §7; insurance conduct rules; employment and works-council law (some EU countries require works-council agreement before monitoring tools).
- Voluntary frameworks used as evidence of good practice: NIST AI RMF, ISO/IEC 42001 (AI management systems).

## 7. EU financial services: check these too (as of 2026-10-06)

A screening list for banks, lenders, payment and e-money institutions, investment firms and insurers. It names the regimes and why an agent touches them; it doesn't say what they require of a given system. Not legal advice: the compliance function and counsel confirm scope. Mark each line "applies now" or "from <date>" against today's date.

| Regime | Status on 2026-10-06 | Why an agent touches it |
|---|---|---|
| **DORA**, Regulation (EU) 2022/2554 | Applies since 17 Jan 2025 | The model vendor, hosted agent platform and tool APIs are ICT third-party services: contract terms, an entry in the register of information (submitted to the supervisor every year), an exit strategy. Agent failures fall under ICT risk management and major-incident classification and reporting. The ESAs designated the first 19 critical ICT third-party providers on 18 Nov 2025, large cloud providers among them; the firm stays responsible for its own use of them |
| **EBA Guidelines on outsourcing arrangements** (EBA/GL/2019/02) | Apply now | Outsourcing of functions, including a bought service with an agent inside. The EBA published replacement Guidelines on third-party risk for non-ICT services (EBA/GL/2026/09) on 18 Sep 2026; they repeal the 2019 Guidelines from an application date not yet set, with two years to bring existing critical or important arrangements in line. ICT arrangements sit under DORA |
| **Model risk management** | Applies now | No single EU rulebook covers every model. For credit, the EBA Guidelines on loan origination and monitoring (EBA/GL/2020/06, since 30 Jun 2021, section 4.3.4) expect institutions using automated models in creditworthiness assessment and credit decisions to understand the model's method, data and limits, control bias and data quality, keep decisions traceable and auditable, and govern model risk. Most banks also run an internal model-risk policy: put any agent that scores, ranks or recommends in the model inventory and ask whether it needs independent validation (tier T3) |
| **AML/CFT** | National laws under the AML Directives apply now; AMLA operational since 1 Jul 2025; **AMLR**, Regulation (EU) 2024/1624, from 10 Jul 2027 | KYC, due-diligence and alert-triage agents work inside these duties. Under AMLR Art. 76(5), decisions from automated processes or AI systems on entering or refusing a business relationship, executing a transaction or changing the level of due diligence need meaningful human intervention, and the customer can get an explanation and challenge the decision (not for suspicious-transaction reports). Cost that review in the model |
| **Consumer Credit Directive 2** (CCD2), Directive (EU) 2023/2225 | National rules from 20 Nov 2026 | Where the creditworthiness assessment uses automated processing, the consumer can ask the creditor for human intervention, get an explanation of the assessment and its main variables and logic, give their view and ask for a review of the assessment and the decision (Art. 18) |
| **GDPR Art. 22** (with Art. 35 DPIA) | Applies now | Solely automated decisions with legal or similarly significant effects need a legal basis and safeguards. The CJEU held in *SCHUFA* (C-634/21, 7 Dec 2023) that a credit score can itself be such a decision when the lender draws strongly on it. A person who rubber-stamps an agent's recommendation may not take the decision outside Art. 22; counsel to confirm |
| **Insurers**: EIOPA Opinion on AI governance and risk management | Published 6 Aug 2025 | Supervisory reading of Solvency II, IDD, DORA and GDPR for AI systems: risk-based, proportionate governance, heavier for systems that affect customers or use sensitive data. Life and health risk assessment and pricing are also Annex III high-risk (§2) |

Each line adds a cost line, lead time or a control to the case: contract and register work, model validation, human review of the decisions these rules cover, explanation and appeal flows. Tie the controls to registry fields and traces as in §5.

Sources: [AI Act implementation timeline](https://artificialintelligenceact.eu/implementation-timeline/) (updated 2026-08-31), [Orrick: Digital Omnibus finalised](https://www.orrick.com/en/Insights/2026/07/EU-AI-Act-Update-Digital-Omnibus-Finalizes-8-Compliance-Changes) (2026-07), [Article 6](https://artificialintelligenceact.eu/article/6/), [Annex III](https://artificialintelligenceact.eu/annex/3/), [Article 12](https://artificialintelligenceact.eu/article/12/), [Article 26](https://artificialintelligenceact.eu/article/26/), all fetched 2026-10. Financial services (§7), fetched 2026-10-06: [DORA, EUR-Lex](https://eur-lex.europa.eu/eli/reg/2022/2554/oj/eng), [ESAs list of critical ICT third-party providers (Morgan Lewis, 2025-11)](https://www.morganlewis.com/blogs/sourcingatmorganlewis/2025/11/dora-eu-regulators-announce-list-of-critical-ict-third-party-providers), [EBA press release on third-party risk Guidelines, 2026-09-18](https://www.eba.europa.eu/publications-and-media/press-releases/eba-publishes-its-final-guidelines-management-third-party-risk-delivering-more-proportionate-and), [EBA/GL/2020/06 final report](https://www.eba.europa.eu/sites/default/files/document_library/Publications/Guidelines/2020/Guidelines%20on%20loan%20origination%20and%20monitoring/884283/EBA%20GL%202020%2006%20Final%20Report%20on%20GL%20on%20loan%20origination%20and%20monitoring.pdf), [AMLR, EUR-Lex](https://eur-lex.europa.eu/eli/reg/2024/1624/oj/eng), [AMLR Art. 76](https://anti-money-laundering.eu/article-76-amlr/), [CCD2, EUR-Lex](https://eur-lex.europa.eu/eli/dir/2023/2225/oj/eng), [SCHUFA C-634/21 (Hunton summary)](https://www.hunton.com/privacy-and-cybersecurity-law-blog/cjeu-rules-that-gdpr-prohibition-on-automated-decision-making-applies-to-credit-scoring), [EIOPA Opinion on AI governance](https://www.eiopa.europa.eu/publications/opinion-artificial-intelligence-governance-and-risk-management_en).
