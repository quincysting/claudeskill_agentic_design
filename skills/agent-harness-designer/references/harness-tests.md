# Harness tests and the run-record contract

Citation keys such as [PRODGUIDE ch16] point to the book list under Sources in SKILL.md.

These tests target the runtime, not the model. No book tests resume, stop, budget or cancel behaviour, and the companion repositories have none either; the tests below are the harness slice of the eval suite, and agent-eval-designer folds them into its plan. Each one forces a condition and checks the run record and the backend, never the reply text.

## 1. How to run them

- **Script the model.** Replace the planner with a list of canned proposals, so each test is deterministic and costs nothing.
- **Keep the store out of process.** A file or a real database, and a fresh process for every resume, so nothing passes on shared memory. A same-process resume test passes even with an in-memory checkpointer.
- **Assert on effects.** Count backend writes and receipts per key; read the exit status and stop reason from the record.
- **Make each test able to fail.** Remove the control it covers (the lookup, the guard, the digest check) once and confirm the test goes red. A test that cannot fail is decoration.
- **Run in CI on every harness change**, and before widening autonomy. They are part of the Prove gate.
- **Keep the tests out of the agent's reach.** Ng reports a coding agent that modified test code so it would pass more easily [NG Agentic Coding and Agentic Software Testing Go Together, 2025-09-17]. Derived rule (not Ng's): tests, eval data, scorers and judge prompts sit outside the agent's write scope, changes to them need human review, and the harness checks a hash of them before trusting a score.

## 2. The tests

| Test | How | Passes when |
|---|---|---|
| Resume after crash | Kill the worker between the intent save and the receipt save; resume the run ID in a fresh process | Exactly one write reaches the backend; one receipt per key |
| Kill while paused | Pause for approval, kill the process, load in a new one, approve | The approved action runs once, with the approved arguments |
| Approval digest | Change an argument after approval, then resume | Execution refused; a new approval requested |
| Approval expiry | Approve after the expiry | Nothing executed; status records the expiry |
| Approval link GET | Fetch the approval link with a plain GET, as a mail scanner or link preview would, with and without a session | Nothing is decided or executed; the approval stays `pending` |
| Link holder without a session | Submit a decision with only the link: no authenticated session, then a session of a user not entitled to approve | Refused both times; the approval stays `pending`; the attempt is logged |
| Forced stop status | Script the model never to finish; separately exhaust model calls, tool calls, tokens and wall time | Status `partial` with the reason, never `completed`; the output names what was not done |
| Budget grain | A turn that would make several tool calls with one call of budget left | Stops before the call that would exceed the budget; spend recorded |
| Parallel children at the limit | With the run's budget nearly spent, spawn several children in parallel | Total spend never exceeds the cap; a child refused a slice ends with a budget reason |
| Budget across restart | Spend most of a budget, restart the worker, continue | Counters survive the restart; the cap holds |
| Clock during waits | Leave an approval pending past the run's wall-time budget, then approve | The run is not stopped for time spent waiting |
| Cancel | Signal cancel mid-run, and during a long tool call | Status `cancelled`; the tool's cleanup ran; no call starts after the signal |
| Kill switch | Flip draft-only mid-run; then flip abort | Draft-only: previews, no writes. Abort: no further calls, run `cancelled` with reason `kill_switch`, restart refused without a new start approval |
| Safe-mode replay | Replay a recorded run with safe mode on | Zero side-effecting calls; unchanged components give the same previews |
| Duplicate delivery | Deliver one event twice, concurrently | One run, one set of writes |
| Lease, redelivery | Redeliver a run's message while its lease is live | No second worker starts; the redelivery is dropped |
| Lease, dead holder | Kill the lease holder after a redelivery was dropped | Once the lease expires the sweeper re-enqueues the run, and it resumes exactly once |
| Disconnect | Drop the client mid-stream, for an interactive run and for a background run | Interactive: cancelled and recorded. Background: continues; reconnect with the last event ID gets the gap |
| Output check before release | A slow output check and a fast model | No text reaches the client before the verdict |
| Declared labels | Register a tool labelled as needing approval with no approval policy wired | The harness refuses to start |
| Limit edge values | Set each limit (steps, sessions, calls, cost, time) to 0, to 1, and leave it unset | 0 stops before the first call or is refused at start; 1 allows exactly one; unset falls back to a declared default. None of them means unlimited |
| Completion claim | Script the model to mark every item done in a file it can write, while the harness's own check fails | The run does not end `completed`; the harness's check decides |
| Containment | From each process the agent can drive (shell, browser, MCP server), check whether it can reach the network beyond its allowlist and write a file the runtime later loads (settings, hooks, prompt files) | Each is blocked by a named boundary, or listed as an accepted risk in the design |
| Deletion | Clear a conversation, or let retention expire a run | Its state and checkpoints are gone from the store, not just hidden. One tutorial clears a conversation by writing an empty message list through an appending reducer, which likely deletes nothing (read, not run), so assert on the store [BUILDAGENTIC repo: sdr_multi_agent/flask_app/agent_builder.py] |
| Faults at the edge | Inject 50% HTTP 500s, then a fixed delay, at the network layer, in a test namespace or through a local proxy only, never on a shared or production mesh | Retries within budget, timeout fires, failures carry their category, no duplicate write |

The fault rows need no change to tool code: the APIARCH companion repository injects 500s on half the calls, or a fixed delay, with service-mesh rules [APIARCH repo: operations/istio/half-broken-gateway.yaml] [APIARCH repo: operations/istio/delayed-gateway.yaml]. A local proxy does the same in a laptop setup. Apply such rules only in a test namespace or a local proxy, never on a shared or production mesh.

## 3. A minimal resume test

The shape of the first test, against the loop skeleton in control-loop.md. The store writes JSON files and dies on the save chosen by the test.

```python
import json

class DyingStore:
    def __init__(self, path, die_on=None):
        self.path, self.saves, self.die_on = path, 0, die_on
    def save(self, st):
        self.saves += 1
        if self.saves == self.die_on:
            raise SystemExit("worker died")          # this save never lands
        with open(self.path, "w") as f:
            json.dump(st, f)
    def load(self):
        with open(self.path) as f:
            return json.load(f)

def test_resume_after_crash(tmp_path, tools, backend, new_state):
    p = tmp_path / "run.json"
    st = new_state("run-1")
    plan = iter([{"tool": "send", "args": {"to": "v", "text": "hi"}}, {"final": "done"}])
    try:                                             # save 1 = intent, save 2 = receipt
        run(st, lambda ev: next(plan), tools, DyingStore(p, die_on=2), {}, lambda: False, None)
    except SystemExit:
        pass
    resumed = DyingStore(p).load()                   # in CI, do this part in a fresh process
    assert run(resumed, lambda ev: next(plan), tools, DyingStore(p), {}, lambda: False, None) == "completed"
    assert len(backend) == 1
    assert sum(e["type"] == "receipt" for e in DyingStore(p).load()["events"]) == 1
```

The other rows follow the same pattern: set the flag or the budget, run, reload, assert on the record and the backend.

## 4. The run-record contract (shared with agent-eval-designer)

Scorers read only fields the harness writes. Without a contract they read fields nothing fills: one eval kit's trajectory scorers read tools, iterations and tool errors from case metadata that nothing in its repository produces, and its cost-capped runner averages the cases it reached with only a printed warning [EVALS repo: project/cap08/evalkit/scorers/agent.py] [EVALS repo: project/cap11/evalkit/runners/cost_aware.py]. Per trial the harness writes:

| Field | Content |
|---|---|
| `run_id` | The run's ID, also on every trace span |
| `versions` | Agent, prompt, policy, model, tool-schema and dataset versions |
| `tool_calls[]` | Tool, arguments, `mode` (`rejected` by the gate, `preview` only, or `executed`), result, error category (agent-fixable or infrastructure), idempotency key, receipt |
| `approvals[]` | Approval ID, requested action, digest, decision, approver, requested and decided times, `expires_at`, `used` |
| `usage` | Model calls, tool calls, steps, tokens, cost, active time, wall time |
| `status` | One of `completed`, `partial`, `awaiting_approval`, `handed_off`, `escalated`, `failed`, `cancelled` |
| `stop_reason` | From the fixed list below; empty for `completed` and `awaiting_approval` |
| `final` | The output, or what was not done for a non-completed status |

**Stop reasons: one fixed list.** This table is the only place status and stop-reason names are defined. agent-eval-designer links to it instead of restating it, and a new reason is added here first, with its status.

| Status | Stop reasons | When |
|---|---|---|
| `completed` | none | Goal met and output validated, including a draft or pack delivered to a person's queue (control-loop.md, "Exit statuses") |
| `awaiting_approval` | none | A pause, not an exit; the pending approval record says what the run waits for |
| `partial` | `max_steps`, `no_progress`, `budget:<name>` for any budget the design declares (`budget:model_calls`, `budget:tool_calls`, `budget:tokens`, `budget:cost`, or another such as `budget:sessions` for an outer loop over sessions), `wall_time` | A forced stop before the goal; a framework's recursion or turn-limit error also maps to `max_steps` |
| `cancelled` | `caller_cancel`, `kill_switch` | Stopped by the caller, or by the abort level of the kill switch |
| `handed_off` | `draft_only`, `external_decision` | Draft-only or safe mode recorded a preview and executed nothing; or a pending action went to another system that decides on its own timeline |
| `escalated` | `approval_expired`, `approval_denied`, `outcome_unknown`, `retries_exhausted`, `invalid_output`, `needs_human` | A person must act: an approval lapsed or was refused and the run cannot go on without it; a write's outcome is still unknown after the lookup; retries ran out; closed-vocabulary output stayed invalid after one re-ask; low confidence or a blocked path |
| `failed` | `error:<category>`, `unreadable_state` | A required check or dependency failed; a checkpoint the code cannot read |

Rules for both sides:
- An eval case's `expected_exit` holds a status, optionally with a reason as `status:stop_reason` (`partial:max_steps`). Scorers compare it with `status`, and with `stop_reason` when the case gives one.
- Short names such as `budget_exhausted` or `killed` may appear in reports as display labels only. The record has no `exit` field, and no scorer reads one.
- A stop reason written as free text is a finding.
- A scorer fails when a field it needs is missing; truncated or capped runs are flagged and never silently averaged; a trial whose status is not `completed` fails the task check unless the case expects that exit (a case can correctly expect `escalated` or `awaiting_approval`). Who designs the scorers and the statistics: agent-eval-designer.

## 5. Harness bake-off

The bake-off protocol belongs to the agent-model-selector skill (its bakeoff-protocol.md, sections 4 and 5): hold the model fixed and vary only the harness, with the same tasks and budgets, several trials per task, pass rate with intervals by task family, and cost per solved task. This skill supplies what goes into it when choosing between harnesses (a framework against your own loop, a vendor harness against a neutral one):
- **The harness variants**, each fully specified: loop, tool dispatch, state store, stop rules, prompt version, provider layer and its effective request parameters. All run under the same budgets, so the comparison measures the harness, not the spend.
- **The harness tests** (section 2). Each variant passes them before it enters the bake-off; a variant that duplicates a write or resumes wrongly is out, whatever its pass rate.

When the harnesses differ in human review time, compare agent-ops-reviewer's cost per successful run instead of cost per solved task. The evidence on how much the harness matters is thin. Public coding leaderboards rank a model and a harness as one entry, and entries also differ in prompts, budgets and versions, so gaps between rows are observational. The one controlled comparison found so far is a single-author preprint (80 private tasks, two frontier models). It found no reliable average difference, a gap that varied by task family, and a neutral harness that cost 1.2 to 1.6 times as much per solved task (Arjmandi, arXiv 2609.11987, 2026-09: https://arxiv.org/abs/2609.11987). Its cost ratio comes from observed usage rather than billed cost, and its task-family split was chosen after seeing the data. So the harness may matter as much as a model upgrade on some of your tasks, or not at all, and it can change cost; measure both on your own tasks. A provider-swap layer also changes behaviour: one injects a default output-token limit and maps unknown stop reasons, a refusal among them, onto an ordinary stop [RELATED repo: aisuite/aisuite/providers/anthropic_provider.py]. Log the effective request parameters and the provider's own stop reason, and rerun the full suite after any swap.

## 6. Scaffolding review at each model upgrade

Hard-coded steps that helped a weaker model can hold a stronger one back. Ng's signal for removing them: error analysis shows each step performing well while the chain as a whole trails what a person would do, which suggests the workflow is too rigid [NG Improve Agentic Performance with Evals and Error Analysis, Part 2, 2025-10-22]. The counterweight is his own recipe: a bare model with tools and a turn cap is highly autonomous, moderately capable and highly unreliable [NG Build an Autonomous Agent Using This Simple Recipe!, 2025-12-10]. So at each model upgrade, rerun the existing eval set with and without the scaffolding in question and decide on the result, not by default. The runtime controls (record, budgets, stops, approvals, kill switch) are not scaffolding and never come out.
