# Use-case discovery, fit gates and scoring

Load this for steps 1-5 of Mode A: framing the unit, inventorying tasks, the pass/fail fit gate, the 35-point scorecard and the readiness check.

## 1. The unit you evaluate

Evaluate tasks or workflow slices, never job roles or technologies. A role is a bundle of linked tasks that no agent takes over whole [AGENTICAI ch8]. Start from workflows rather than the org chart, because the same people act in different processes with different colleagues [ENTERPRISE ch5].

A use case is a bounded slice with defined inputs, defined outputs or actions, and a success test. Scope check [BUILDAPPS ch2]:

| Scope smell | Example | Fix |
|---|---|---|
| Too narrow | "only cancellations" | Include the neighbouring high-volume requests that share data and actions |
| Too broad | "automate every support inquiry" | Cut to the 3-5 request types that make up most of the volume |
| Too vague | "improve customer satisfaction" | Name the KPI and the threshold that counts as success |

If the user arrives with one agent in mind, list the neighbouring tasks anyway. In AGENTICAI's engagements nearly half of the requested agents were not the client's best opportunity; one client asked for social-media posting when lead qualification would have returned about five times as much [AGENTICAI ch8].

## 2. Inventory

**Small team (work can be listed in an hour): two-hour workshop.** Ask [AGENTICAI ch8]:
- What do you repeat every week?
- What keeps you from the work you were hired for?
- Where do things queue or wait?
- Which routine tasks need the most checking or rework?

For each task record frequency, minutes per instance, people involved, systems touched, how the data is reached (API, UI, export, paper), whether a document describes the process, and who owns it. The tasks people complain about are usually the high-impact ones.

**Large department: workload mapping.** Interview and observe; don't rely on survey estimates. AGENTICAI's insurer engagement embedded for six weeks with more than 50 staff, built workload maps per department, then applied a 20/80 rule: the 20% of activities taking 80% of the time became the targets [AGENTICAI ch11]. Measured time per activity becomes the business-case baseline later, so record the source and the period.

## 3. Fit gate (pass/fail, before any score)

Two questions decide fit:
1. **What does a wrong result cost if nobody catches it?**
2. **Can a wrong result be caught cheaply before it takes effect?**

AGENTICAI's own feasibility circle includes "manageable consequences if something goes wrong" and the "ability to verify results before they impact operations" [AGENTICAI ch8]. Its 35-point score then leaves both out, which is why this gate sits in front of the score.

| | Errors cheap | Errors costly |
|---|---|---|
| **Checkable before effect** | Automate end to end, with monitoring | Automate behind a coded check or human approval before the effect |
| **Hard to check before effect** | Assist: agent drafts, people sample-review | Keep with people; at most an assist agent that gathers checkable evidence |

Place each task, not the whole process. One process often splits across cells:
- Compliance: monitoring rule changes and flagging gaps is cheap-error and checkable (a false flag costs a reviewer minutes); acting on an interpretation of a rule is costly. ENTERPRISE lists compliance as a good fit and misreading a compliance rule as a bad one [ENTERPRISE ch2]. Both statements hold because they describe different tasks.
- Fraud: detecting the same damaged-parcel photo reused across refund claims is a checkable signal [AGENTICAI ch12]; deciding whether a given customer is lying is not.

**When the check is the expensive step.** "Checkable before effect" only helps if checking is cheaper than doing. If an analyst must re-read every document to approve the agent's work (KYC files, contract clauses), the saving disappears. Model it with approvals on every item (`qa_share` 1.0, `qa_min` = review minutes). If review takes half the manual time or more, treat the task as assist at best. Then make the check cheaper: the agent cites the exact source passage, highlights only fields that differ from the system of record, or a coded check replaces the person. Rubber-stamping is the other risk. People approve without looking once the agent is usually right, so audit a sample of approved items.

**Borderline cells.** If you can't say whether errors are cheap or checkable, place the task in the more cautious cell and name the evidence that would move it (an error-cost estimate from finance, a sample showing checks take under a minute). Revisit after the pilot.

**High-risk by law is not a blocker by itself.** A use in an EU AI Act Annex III area (hiring, consumer credit, life and health insurance pricing) or under sector rules on automated decisions can still pass the gate. It sets risk tier T3, adds compliance cost lines and lead time, and needs a human with authority over each decision. It fails the gate only through the blockers below: no legal authority, uncheckable costly errors, tacit knowledge.

**Hard blockers. Any one of these fails the task, whatever its score:**

| Blocker | Source of the rule | Result |
|---|---|---|
| Knowledge is tacit, fragmented or in people's heads rather than systems of record (M&A negotiation, credit on opaque counterparties, crisis management) | [ENTERPRISE ch2] | Not scored; keep with people |
| Judgment is subjective and individual, or needs creativity/empathy as the core output | [ENTERPRISE ch2], [AGENTICAI ch8] | Keep with people or assist |
| One mistake costs more than the operational benefit and can't be caught before effect | [ENTERPRISE ch2] | Keep with people |
| No legal or regulatory authority for the agent (or its operator) to make the decision | [AGENTICAI ch8] | Not scored |
| Process not proven manually, or known to be flawed | [AGENTICAI ch8] | Redesign first. "If you automate a flawed process, it will just result in flawed automation." |
| Too many unique scenarios to specify success | [AGENTICAI ch8] | Narrow the scope or drop |
| No data or system access the agent could use | this skill | Fix access first or drop |
| No named process owner who will accept the result | this skill | Find one or drop |

**Agent, workflow or plain code?** Fit for automation is not fit for an agent. If inputs are structured and the rules fully specifiable, a deterministic workflow, RPA or plain code is cheaper and repeatable. If language understanding is needed on a fixed path, an LLM workflow is enough. Use an agent only where the steps can't be fixed in advance. Agents trade latency and cost for task performance, and a single well-built model call is often enough ([Building effective agents](https://www.anthropic.com/engineering/building-effective-agents), external, 2024-12). Pets at Home found running agents could cost more than standard automation [AGENTICAI ch12]. Price the agent against the best non-agent option, not only against the manual baseline. Hand architecture questions to agent-architect.

## 4. Scorecard (survivors only)

AGENTICAI's Three Circles: impact (will it matter), feasibility (can it be done), effort (is it worth it) [AGENTICAI ch8]. Before scoring, write down what the team means by "feasibility" and "effort"; the books use the words differently (standardisation plus data access in AGENTICAI's scorecard; architecture, tool and model readiness in MESH ch15).

**Impact, 4 criteria x 1-5 = max 20**

| Criterion | 1 | 3 | 5 |
|---|---|---|---|
| Time saved | under 1 hour a week | several hours a week | multiple hours a day |
| Strategic value of the freed time | limited alternative use | moderate | high-value work currently blocked |
| Error-reduction potential | few errors | occasional significant errors | frequent or costly errors |
| Scalability | one-off task | moderately repeatable | scales across the organisation at little extra cost |

Optional money backing (AGENTICAI's formulas): time = hours per instance x instances per month x hourly cost; errors = error rate x cost per error x volume. In large operations, time saved hits 5 for nearly every candidate. Two fixes: (1) record addressable money per month (volume x minutes x rate) for every candidate and break ties on it, not on more points; (2) score time saved relative to the candidate set. Rank candidates by hours per month and give 5 to the top fifth, 4 to the next, down to 1 for the bottom fifth. Say which scaling you used.

**Feasibility, 2 criteria x 1-5 = max 10**

| Criterion | 1 | 3 | 5 |
|---|---|---|---|
| Process standardisation | ad hoc, no standard approach | basic documentation, relies on experience | fully documented: steps, decision rules, exceptions. A newcomer could follow it from the documents alone. |
| Data and system access | locked in legacy systems or paper | available but needs significant preparation | structured, behind modern APIs |

**Effort, 1-5 reverse-scored = max 5**: 5 standard tools, little or no customisation; 4 some customisation on common technology; 3 significant custom development; 2 complex integration or new technology; 1 research and development.

**Matrix.** Impact on one axis; on the other, what the book calls complexity, combining feasibility and effort [AGENTICAI ch8]. Both scores rise as the task gets easier, so this skill calls the sum **ease** (feasibility + effort, out of 15) to avoid reading it backwards. Quadrants: quick wins (high impact, high ease), strategic projects (high impact, low ease), low priority (low impact, high ease), avoid (low impact, low ease). The book gives no cut-offs. This skill's default: high impact is 14 or more out of 20; high ease is 11 or more out of 15; a score exactly at a cut-off counts as high. Say that these cut-offs are a convention. A task within one point of either cut-off is **borderline**: show it as such and decide on the fit result and the money figure, not on the quadrant label.

**Known weaknesses: why the gate comes first**
- Additive: a task with data access 1 can still score 31/35, so a fatal blocker gets averaged away.
- Risk is not in the score. Show it in its own column (risk tier, regulated yes/no) and don't fold it into the points.
- Impact carries 20 of 35 points, which pushes high-volume, high-stakes tasks up the ranking. The fit gate pulls them back.

**Choosing the pilot.** Pick one quick win whose errors are checkable and whose unit metric the business already tracks, plus one or two next in line. MESH also weighs "demonstration potential" to win sponsors for a platform [MESH ch15]. Use it only to break ties, never to outrank value.

## 5. Readiness (once per organisation, not per use case)

Rate each dimension red (behind), amber (progressing) or green (on top of it) [ENTERPRISE ch2]:

| Dimension | Questions to ask |
|---|---|
| Leadership alignment | Do leaders understand agents as opportunity and threat? Are pain points named? Are autonomy vs human-intervention boundaries defined? |
| Technical infrastructure | Data, MLOps and APIs in place? Which gaps are non-negotiable and which can we work around? |
| Governance and risk | Documented principles on autonomy vs augmentation? How enforced and monitored? Which committee oversees, and who is accountable when an agent acts? |
| Architecture | Modular systems and orchestration that work with legacy systems? Which systems get modernised first? |
| Technical resources | In-house skills to design, learn from feedback and iterate? |
| Change management | Talent, cultural agility, risk appetite; readiness to change roles and manage humans and agents as one workforce |

Each red item becomes a cost line or a named risk in every business case. Readiness red on governance means the governance plan (Mode B) starts before or alongside the first pilot.

## 6. Worked example (illustrative scores)

Online retailer, support and finance teams, six candidates. Gate first, then score.

| Candidate | Fit | Impact | Feas. | Effort | Total | Decision |
|---|---|---|---|---|---|---|
| A. Order changes by email (refund, cancel, address) for unshipped orders | Checkable against order state; refunds above a cap go to a person | 15 | 10 | 4 | 29 | Pilot |
| B. Weekly trading report for category managers | Numbers recomputable; narrative needs sampling | 13 | 8 | 4 | 25 | Next in line |
| C. Supplier invoice disputes with ERP write-back | Costly but checkable; process ad hoc | 14 | 4 | 2 | 20 | Redesign process first |
| D. Brand social posts | Cheap errors, hard to check | 8 | 8 | 5 | 21 | Low priority |
| E. Approve/deny high-value refund fraud | Costly; ground truth arrives weeks later | 17 | 7 | 3 | 27 | Assist only: agent gathers evidence, a person decides |
| F. Credit terms for new wholesale customers | Tacit knowledge, opaque counterparties | - | - | - | - | Fails gate; not scored |

E ranks second on points and still fails the gate as an autonomous agent. That is the reason the gate runs first.
