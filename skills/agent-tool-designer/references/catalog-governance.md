# Catalogue governance

Depth for step 13 of the procedure. Once several teams build tools, or agents reach more than a few servers, the tool set needs an owner for every entry, an inventory with nothing reachable outside it, a lifecycle that ends in retirement, and a written split of which decisions are made centrally. The contract each entry carries is in [tool-contracts.md](tool-contracts.md). Organisation-wide AI governance (operating model, review boards, funding) belongs to agentic-business-case; this file covers the catalogue. Citation keys are listed under Sources in SKILL.md.

## §1 Each tool or server is a product with an owner

APIMGMT's API-as-a-product argument covers internal APIs as well as public ones [APIMGMT ch3]. Its best-known example, the Bezos mandate, says teams expose functionality only through APIs and consume each other's only that way [APIMGMT ch3 §The Bezos Mandate]. The agent version: if the only path from an agent to a system is a catalogued tool behind a gateway, the catalogue is complete by construction. If ad hoc wrappers are allowed, every agent team writes its own, each with its own errors, scopes and retry behaviour.

An owner is a named team that answers for the contract, the version, incidents and retirement. APIMGMT's ten pillars are a fair checklist of what that team does: strategy, design, documentation, development, testing, deployment, security, monitoring, discovery and change management [APIMGMT ch4]. A tool nobody owns cannot be changed safely, so it never gets retired either.

## §2 Inventory: everything reachable is listed, nothing else is reachable

A catalogue entry holds the SYSTEMS registry fields (owner, contracts, risk class, permissions, approval rule, active version, log location) [SYSTEMS ch18 §18.5 Tool Platforms and Registries], plus:

| Extra field | Why |
|---|---|
| Namespace | Assigned by the catalogue, unique, used to resolve `server::name` (§3) |
| Lifecycle stage | Decides which rules apply (§4) |
| Calling agents | Who to tell before a change or a retirement |
| Reversible writes and their revert actions | MCP annotations cannot carry this (tool-contracts §6) |
| Release signature and disclosure contact | Whether you know what you run and who to report a flaw to |
| Deprecation date and replacement | Empty until §5 starts |
| Rate limits and quotas | Per principal, per client and per tool, lower for tools that create, spend, send or search expensively (tool-design-rules §7) |
| Upstream API and its version | Whose change can break the contract; the adapter absorbs renames (tool-contracts §8) |

**No shadow endpoints.** APIARCH's "improper assets management" example is a forgotten `/beta` endpoint, still public and still returning fields that newer versions removed; the defence is a catalogue of everything deployed and a gateway that knows what exists [APIARCH ch6]. The agent equivalents are an MCP server on a laptop, a tool defined inline in agent code, an old version still registered, and a fallback tool someone forgot. An agent uses whatever it holds: when Ng's research agent hit a rate limit on web search during a demo, it switched to a Wikipedia tool he had forgotten he had given it [NG Agentic Design Patterns Part 4, Planning, 2024-04-10]. That time the fallback helped, but a forgotten tool is an unreviewed path. List fallbacks, and tier them, like any other tool.

**Enforce the inventory.** Use a private subregistry of approved servers as the allowlist and a gateway as the enforcement point [MCP ch9 §MCP Registry], [MCP ch9 §Governance]. Reconcile regularly: compare what agents actually called (the call logs) with the catalogue, and treat a call to anything unlisted as an incident.

**Overlapping first-party servers.** When several teams publish servers that cover the same capability (two HR servers that both look up employees):
1. Inventory every server and tool across teams, from the subregistry and the call logs.
2. The catalogue owner names one authoritative server per capability and records it in the entry.
3. Namespaces are allocated centrally (§3), so no two servers can claim the same prefix.
4. The other servers' overlapping tools are retired through §5, with the authoritative tool as the replacement.
5. Until they are gone, hosts resolve every tool as `server::name` and pin definitions, and the consuming agents' tool-choice evals run with all the overlapping servers loaded, confusable pairs across servers included.

**Same name, different contract.** Count definitions, distinct names and servers separately. When two servers publish one tool name, compare their result shapes and behaviour (fields, units, side effects, errors). If they differ, what the model gets depends on which server answered. Record that as a finding even before a host connects both (P2 until a failure is shown), and resolve it through steps 2 to 4 above.

**Supply chain, contract side.** Each entry records whether releases are signed, the one supported install path, and a disclosure contact. HARDMCP's 2026 scan of nearly 11,700 servers found no signed releases and 86% with no disclosure channel (as of 2026-10) [HARDMCP ch10 §Recipe 3: Knowing and Trusting What We Run]. Dependency pinning, signature checks at launch and sandboxing are hardening work for agent-threat-modeler.

## §3 Names and permissions come from the catalogue

- **Unambiguous names.** Tool names are unique only within one server. The catalogue gives each server a unique namespace, and the host or gateway resolves every tool as `server::name` from that namespace, never from the server's self-reported name [HARDMCP ch9 §Recipe 1: Tool Shadowing] (current facts). The shadowing threat and definition pinning are agent-threat-modeler's.
- **Permissions keyed by contract ID.** One project's generated access map named an action `CreateNewTask` where its profile said `doCreateTask` [RELATED repo: ai-apis-design-with-alps/06-rbac-security-profile/2025-06-15-rbac-map.json]. Key policy entries and tests by contract ID, and lint for one policy entry and one tagged test per action.
- **Scopes per tool.** The catalogue lists the scope each tool requires; the tool checks it on every call (tool-design-rules §7). Per-call authorization as granted scope intersected with the user's own entitlements [APIARCH ch7] is agent-threat-modeler's.

## §4 Lifecycle

APIMGMT's five stages map onto tools [APIMGMT ch7]:

| Stage | What it means for a tool | Before it moves on |
|---|---|---|
| Create | Contract, tier and owner set; not callable by production agents | Contract reviewed; tool-choice eval passes |
| Publish | Registered; changes are cheap but cost trust | Schema diff and contract tests in CI (tool-contracts §9) |
| Realize | Agents depend on it; never-break rules apply; usage counted per version | Any break ships as a new name (tool-contracts §8) |
| Maintain | Fixes and compliance only | A large change goes back to Publish as a new version |
| Retire | Announced date and replacement; then removed | §5 |

## §5 Deprecation and retirement

1. **Announce** a date and a replacement, and tell the calling agents' owners.
2. **Flag it where machines look.** Put a `deprecated` field (date and replacement) in the result envelope and the registry entry, so harnesses and owners see it. APIMGMT warns in documentation and even in responses [APIMGMT ch7 §Methodology: Retiring APIs without breaking applications using API metrics].
3. **Count callers.** Log the tool name and version on every call, find who still calls the old version, and talk to them.
4. **Re-run evals without it.** Each consuming agent's tool-choice eval runs against the tool list it will have after retirement.
5. **Remove the instance**, not only the documentation, and close the registry entry. A retired version that still answers is a shadow endpoint (§2).

Set a deprecation window and publish it. The MCP specification keeps deprecated features working for at least twelve months, a usable precedent (current facts). Some companies, Stripe and Salesforce among them, keep every version live instead [APIMGMT ch7], at a support cost most teams cannot carry.

## §6 Decision-based governance

APIMGMT argues that what you can govern is the decisions people make, and splits each decision into six elements: inception, choice generation, selection, authorization, implementation and challenge [APIMGMT ch2 §The Elements of a Decision]. Centralize an element when a bad local choice could do irreversible harm to the system, or when consistency matters more than local fit; otherwise leave it to teams. Enforce the centralized decisions and incentivize the decentralized ones, for example by making the preferred path the cheapest [APIMGMT ch2 §Designing Your Governance System].

A starting decision map for a tool catalogue:

| Decision | Centralized | Left to teams | Enforce or incentivize |
|---|---|---|---|
| Error format and failure categories | Choice, selection, challenge | Implementation | Enforce: lint in CI |
| Naming and namespaces | Convention, namespace allocation | Names within the namespace | Enforce: the registry rejects collisions |
| Permission tier of a write | The tier list; authorizing a tier | Proposing it | Enforce: review before Publish |
| Which tools a team builds | Only the catalogue check | Everything else | Incentivize: templates and scaffolds |
| Retiring a version | Authorization and the date | Migration plans | Enforce the date; reward early moves |

APIMGMT describes three governance patterns: a design authority that can stop releases, centralized experts embedded in teams, and influenced self-governance steered by a recommended "golden path" [APIMGMT ch2 §Governance Pattern #1: Design Authority], [APIMGMT ch2 §Governance Pattern #3: Influenced Self-Governance]. A small platform team usually starts with the third and adds a design authority for write tools.

PRODGUIDE treats its deny list as non-negotiable [PRODGUIDE ch7], while APIMGMT says neither enforcement nor incentives work alone [APIMGMT ch2]. Both hold: enforce the fields that guard side effects (tier, idempotency rule, reversibility, failure categories) and incentivize the rest.

## §7 Catalogue review checklist

1. Does every reachable tool and server version have a catalogue entry with an owner, a unique namespace, a lifecycle stage and its calling agents, and does each capability have one authoritative server?
2. Is the catalogued path the only path (subregistry allowlist plus gateway), and do call logs get reconciled against the catalogue?
3. Are fallback tools listed and tiered like primary ones?
4. Are permissions and tests keyed by contract ID, with one policy entry and one tagged test per action?
5. Does each entry record release signing, the install path and a disclosure contact?
6. Is each deprecation dated, flagged in results and in the registry, measured by per-version usage, and finished by removing the instance?
7. Is there a written decision map of what is centralized, and is each centralized rule enforced in CI or at registration?
8. Are definitions, distinct names and servers counted separately, and does any name appear on two servers with a different result shape or behaviour?
