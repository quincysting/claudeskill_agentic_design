# Agentic AI design skills for Claude

Eight [Claude skills](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview) that help you design,
build, evaluate and run AI agents. Each one turns Claude into a reviewer or designer for one part of an agent
system: architecture, tools and MCP, retrieval and memory, evals, operations and cost, security and human
oversight, model choice, and the business case.

The guidance was distilled from 11 books on agentic AI (listed below), cross-checked against current public
sources such as the MCP and A2A specifications, OWASP's 2026 lists and Anthropic's engineering posts, and then
tested: a fresh Claude instance that had never seen each skill ran it on a realistic scenario, and an independent
judge scored the result.

## The skills

| Skill | Use it to | Try asking |
|---|---|---|
| [`agent-architect`](skills/agent-architect/SKILL.md) | Decide workflow vs agent per step, pick patterns, design the control loop (budgets, stops, retries, checkpoints), choose single vs multi-agent | "Design an agent that prepares insurance claims for adjusters" |
| [`agent-tool-designer`](skills/agent-tool-designer/SKILL.md) | Design or review the tools an agent calls and the MCP servers that expose them; choose between function calling, MCP and A2A | "Review my support agent's tool definitions" |
| [`agent-context-designer`](skills/agent-context-designer/SKILL.md) | Design retrieval/RAG, agent memory and per-call context budgets, including cache-friendly prompt layout | "My agent forgets what it already tried after 40 turns" |
| [`agent-eval-designer`](skills/agent-eval-designer/SKILL.md) | Write an offline eval plan: task sets, scorers, LLM-judge calibration, pass^k, sample sizes, CI gates | "How many test cases do I need before launch?" |
| [`agent-ops-reviewer`](skills/agent-ops-reviewer/SKILL.md) | Review production readiness: tracing (OpenTelemetry GenAI), monitoring, online evals, cost and latency with a runnable cost model | "Is my agent production ready, and how do I halve its cost?" |
| [`agent-threat-modeler`](skills/agent-threat-modeler/SKILL.md) | Threat-model an agent and design its defences and human oversight: injection, tool governance, sandboxing, approval gates | "Threat-model an email assistant that can send replies" |
| [`agent-model-selector`](skills/agent-model-selector/SKILL.md) | Choose a model and reasoning effort per role, decide prompt vs RAG vs fine-tuning vs RL, run a fair bake-off | "Should we fine-tune our clause classifier?" |
| [`agentic-business-case`](skills/agentic-business-case/SKILL.md) | Pick use cases, build a business case with a runnable ROI model, plan the pilot, set up governance (incl. EU AI Act) | "Where should our bank start with AI agents?" |

The skills know about each other. Each one stays in its lane and points to the sibling that owns a related
question, so `agent-architect` hands tool design to `agent-tool-designer`, security to `agent-threat-modeler`,
and so on. Install all eight for the best results.

## Install

### Claude Code

Copy the skill folders into your personal skills directory (available in every project):

```bash
git clone https://github.com/quincysting/claudeskill_agentic_design.git
cp -r claudeskill_agentic_design/skills/* ~/.claude/skills/
```

On Windows (PowerShell):

```powershell
git clone https://github.com/quincysting/claudeskill_agentic_design.git
Copy-Item -Recurse claudeskill_agentic_design\skills\* $HOME\.claude\skills\
```

To share them with a team through one repository instead, copy them into that project's `.claude/skills/`
folder and commit it. Start a new Claude Code session afterwards; the skills load automatically and trigger when
your request matches their description. You can also call one by name, for example `/agent-architect`.

### Claude apps and the API

Each folder under `skills/` is a standard skill (a `SKILL.md` with YAML frontmatter plus supporting files). Where
your Claude product supports uploading custom skills, zip the individual skill folder and upload it.

## What's in a skill

```
skills/agent-eval-designer/
  SKILL.md        the procedure Claude follows: inputs to gather, steps, decision tables, output shape, quality bar
  references/     depth loaded only when needed: pattern catalogues, checklists, statistics, dated facts
  templates/      skeletons for the deliverable (eval plan, threat model, design doc, business case)
  scripts/        small runnable helpers (two skills have one)
```

Two skills include Python helpers that need only the standard library:

- `agent-ops-reviewer/scripts/cost_model.py`: expected, likely-high and capped worst-case cost and latency per
  request, monthly cost at peak, and what-ifs. Run it with `--selftest` to check it, or pass your own JSON spec.
- `agentic-business-case/scripts/roi_model.py`: monthly ROI, payback, breakeven containment, sensitivity and a
  fundable / pilot-only / not-fundable verdict. Running it with no arguments runs its self-check.

## How these skills were built

1. Eleven books were converted to text and each was read in full, chapter by chapter, to produce a per-book digest.
2. All 137 chapters were mapped onto 18 topics, down to section level, and the books' disagreements were listed.
3. An 18-chapter reference guide (about 135,000 words) was written from those chapters plus companion code and
   current public sources, with citations checked and 38 claims spot-checked against the books.
4. The skills were distilled from the guide: decisions, defaults, thresholds and checklists rather than summaries.
5. Each skill was dry-run by its author, then tested cold by a separate Claude instance on a held-out scenario.
   An independent judge scored the outputs (all eight passed, 4.0 to 4.8 out of 5 on followed-the-procedure,
   specific, correct, actionable and well-scoped), and the testers' notes were fixed in the published versions.

Citations such as `[DEFGUIDE ch5]` in the reference files point to the books below; each skill's Sources section
maps the keys to titles. You do not need the books to use the skills.

## Sources

| Key | Book |
|---|---|
| DEFGUIDE | *AI Agents: The Definitive Guide*, Nicole Koenigstein (O'Reilly) |
| MCP | *AI Agents with MCP*, Kyle Stratis (O'Reilly) |
| EVALS | *AI Evals in Practice*, Caio Incau (Packt) |
| AGENTICAI | *Agentic Artificial Intelligence*, Pascal Bornet et al. |
| MESH | *Agentic Mesh*, Eric Broda and Davis Broda (O'Reilly) |
| ILLUSTRATED | *An Illustrated Guide to AI Agents*, Maarten Grootendorst and Jay Alammar (O'Reilly) |
| BUILDAGENTIC | *Building Agentic AI*, Sinan Ozdemir (Pearson) |
| BUILDAPPS | *Building Applications with AI Agents*, Michael Albada (O'Reilly) |
| DLLMA | *Designing Large Language Model Applications*, Suhas Pai (O'Reilly) |
| SYSTEMS | *Systems Thinking for Agentic AI* |
| ENTERPRISE | *The Agentic Enterprise*, Babak Hodjat et al. (O'Reilly) |

The skills paraphrase and synthesize; they contain no book text beyond short attributed phrases. This project is
not affiliated with the authors or publishers. If you find the guidance useful, the books are worth reading.

## Limits

- Fast-moving facts (model names, prices, MCP and A2A versions, OWASP lists, EU AI Act dates) are dated
  October 2026 and kept in clearly named files such as `references/current-facts-2026-10.md`,
  `references/model-landscape-2026-10.md` and `references/eu-ai-act-2026-10.md`. Check them before relying on
  them, and send a pull request when they change.
- The skills give design and review guidance. They do not replace testing your own system, and the regulatory
  material in `agentic-business-case` is not legal advice.
- The skills are written for Claude. Other agents that read `SKILL.md` files may use them, but they were only
  tested with Claude.

## Contributing

Issues and pull requests are welcome, especially updates to the dated reference files and reports of scenarios
where a skill gave weak or wrong advice. Please keep `SKILL.md` under 500 lines and put depth in `references/`.

## License

[MIT](LICENSE)
