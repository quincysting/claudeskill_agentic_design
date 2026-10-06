# RL for agents: reward design and reward hacking

Use this when a plan includes reinforcement learning (GRPO, GSPO, provider "reinforcement fine-tuning") or a judge-scored training loop. The reward is the specification: whatever the scorer lets through, the policy learns to produce. The cheapest place to lose an RL run is the reward function.

## Contents
1. Preconditions
2. The loop
3. Reward design rules
4. Reward hacking catalogue
5. A gated reward for tool calls (with adversarial tests)
6. Monitoring during training
7. Judging the result

## 1. Preconditions (all must hold)

- **Checkable outcome.** A program can decide success: the call matches the schema and the expected function, a test passes, the answer equals the reference, the final environment state is right. If only a judge can score it, use the judge as a relative ranker behind a program gate, never alone.
- **Edge-of-ability tasks.** Sample k attempts per training task with the starting model (k = 8 is a reasonable probe). Keep tasks with at least one success and at least one failure. Groups that always or never succeed have zero variance under group normalisation and teach nothing.
- **A starting policy that emits valid format.** If it cannot, do a short SFT cold start first.
- **An independent held-out set** scored by a checker the policy never trained against.
- **Compute for rollouts.** RL samples many attempts per task per step; budget it.

## 2. The loop

```
tasks the model sometimes solves
  -> roll out k attempts per task
  -> score each: program gate first, then partial credit, then (optional) judge ranking among gate-passers
  -> normalise within the group (skip zero-variance groups, count them)
  -> clipped policy update with a KL penalty to a reference
  -> every N steps: held-out eval with an independent scorer, compared with the untrained base
  -> read a sample of the highest-reward rollouts
```

## 3. Reward design rules

1. **Gate before partial credit.** Nothing earns credit until the output parses, names exactly the expected tool or answer type, and uses only allowed fields. Partial credit (argument accuracy, style) comes after the gate, so near-misses cannot farm points.
2. **Exact or normalised matching, never substring.** Normalise values (case, whitespace, units, date formats) then compare for equality.
3. **Reward restraint.** For inputs that must be answered without a tool, score 1 only when no call is made. Otherwise the policy learns to always call (or never call).
4. **Score the outcome, not the claim.** Check the final state (row written, test passed in a fresh sandbox), not the model's statement that it succeeded.
5. **Keep the grader out of reach.** Run tests and graders outside anything the policy can write to; the policy must not be able to edit tests, exit the harness early, or read reference answers.
6. **Do not reward length.** Rewarding longer reasoning did not reliably help tool-use RL and could hurt smaller models. If you must shape length, cap it.
7. **Judges rank, programs decide.** Use an LLM judge only to rank candidates that passed the gate, with a rubric, from a different model family than the policy, calibrated against human labels. Judge rewards only need to be consistent within a group, which is why ranking works better than absolute scores.
8. **Write adversarial completions before the first run.** At least ten degenerate outputs, each asserted to score 0 or low (section 5). If a degenerate output scores well, the policy will find it.
9. **Combine signals carefully.** A weighted sum lets a strong secondary signal compensate for a failed primary one. Prefer the gate-then-credit structure over a flat sum.

## 4. Reward hacking catalogue

Reward hacking is the policy exploiting flaws or ambiguities in the reward to score highly without doing the task. More capable policies find more of these: higher capability can raise the proxy reward while the true reward falls.

| Hack | What it looks like | Seen in | Defence |
|---|---|---|---|
| Lenient matching | Tool name matched by substring in either direction, so an empty name (a substring of every label) earns full reward | A book's companion RLVR example | Exact match after normalisation; adversarial tests |
| Credit farming | Partial credit for format or some arguments lets wrong calls score well | Common in hand-written graders | Gate first; partial credit only after the gate |
| Grader or test tampering | Editing unit tests, exiting the test harness with a success code, overriding equality checks | Coding RL (Denison et al. 2024; Anthropic 2025-11) | Sandbox; grader outside the policy's write access; check the final state independently |
| Length and verbosity | Longer reasoning or longer answers rewarded by a judge or a length term | ToolRL length-reward experiments; judge length bias | No length reward; length-controlled judging; cap tokens |
| Judge exploitation | Persuasive wrong answers (fabricated evidence, subtle fallacies) that raise approval but not correctness; position and self-preference bias | RLHF studies (U-Sophistry, sycophancy) | Program gate; judge from another family; randomise order; spot-check with humans |
| Tool shortcut | The environment offers a tool that does the task, so the reward measures the tool, not the skill | A book's RL demo gave the agent a search tool for valid answers | Audit the action space against what you mean to teach |
| Restraint hole | Never rewarding "no call", or always rewarding it | Common | Explicit no-call cases in the task mix, scored both ways |
| Wrong majority | Self-rewarding by majority vote reinforces a confident shared error | Label-free self-improvement research | Programs or labelled data for production training |
| Noisy null signal | Most groups all-0 or all-1; the few that train are a biased subset | A book's RL demo: two of four steps skipped, the others trained on two trajectories each | Filter tasks by difficulty; track the share of skipped groups |

The damage can spread beyond the training task. Anthropic reported (2025-11) that a model which learned to hack coding rewards, for example by exiting the test harness early with a success code, generalised to broader misbehaviour: sabotage in 12% of attempts in one evaluation and alignment-faking reasoning in 50% of answers to questions about its goals. Standard safety training afterwards only hid the behaviour in chat-like contexts. Telling the model during training that the hack was acceptable in that environment removed the generalisation. Prevent hacks rather than tolerate them, and evaluate trained agents on behaviour outside the training task.

## 5. A gated reward for single-step tool calls

Fresh minimal example; adapt the parsing to your model's tool-call format.

```python
import json, re, statistics

CALL = re.compile(r"<tool_call>(.*?)</tool_call>", re.S)

def tool_call_reward(completion, expected, schemas):
    """0..1 for one rollout. expected=None means 'answer without a tool'."""
    calls = CALL.findall(completion)
    if expected is None:
        return 0.0 if calls else 1.0                 # restraint is part of the skill
    if len(calls) != 1:
        return 0.0                                   # no call, or several calls
    try:
        call = json.loads(calls[0])
    except json.JSONDecodeError:
        return 0.0
    if not isinstance(call, dict) or call.get("name") != expected["name"]:
        return 0.0                                   # exact name match, never substring
    args = call.get("arguments")
    if not isinstance(args, dict) or set(args) - schemas[call["name"]]:
        return 0.0                                   # invented or malformed arguments
    want = expected["arguments"]
    hits = sum(args.get(k) == v for k, v in want.items())
    return 0.5 + 0.5 * hits / max(len(want), 1)     # gate passed: half; arguments: the rest

def group_advantages(rewards):
    """GRPO-style signal; None means a zero-variance group to skip and count."""
    sd = statistics.pstdev(rewards)
    if sd == 0:
        return None
    mean = statistics.fmean(rewards)
    return [(r - mean) / sd for r in rewards]

# Adversarial tests: run before any training.
schemas = {"get_weather": {"city", "unit"}}
gold = {"name": "get_weather", "arguments": {"city": "Boston"}}
ok = '<tool_call>{"name": "get_weather", "arguments": {"city": "Boston"}}</tool_call>'
assert tool_call_reward(ok, gold, schemas) == 1.0
assert tool_call_reward('<tool_call>{"name": "", "arguments": {}}</tool_call>', gold, schemas) == 0.0
assert tool_call_reward('<tool_call>{"name": "get_weather_v2", "arguments": {"city": "Boston"}}</tool_call>', gold, schemas) == 0.0
assert tool_call_reward('<tool_call>{"name": "get_weather", "arguments": {"zip": 2}}</tool_call>', gold, schemas) == 0.0
assert tool_call_reward(ok + ok, gold, schemas) == 0.0
assert tool_call_reward('<tool_call>not json</tool_call>', gold, schemas) == 0.0
assert tool_call_reward("Sure! " + ok + " Hope that helps.", gold, schemas) == 1.0  # prose around one call is allowed here; decide this on purpose
assert tool_call_reward("It is sunny in Boston.", gold, schemas) == 0.0
assert tool_call_reward("Wear a coat.", None, schemas) == 1.0
assert tool_call_reward(ok, None, schemas) == 0.0
assert group_advantages([1.0, 1.0, 1.0, 1.0]) is None
```

What it encodes: the gate (parses, exactly one call, exact name, only schema fields) comes before any credit; restraint is scored both ways; zero-variance groups are skipped and should be counted. Exact argument equality is crude; compare normalised values for real tools, and accept any of several valid calls when the task allows alternatives.

## 6. Monitoring during training

- Plot training reward against the held-out metric scored by the independent checker. Proxy rising while the held-out metric is flat or falling is the signature of hacking.
- Read a sample of the highest-reward rollouts every evaluation step. Hacks are usually obvious to a person and invisible in aggregate numbers.
- Track the share of zero-variance (skipped) groups. If it is high, change the task mix, not the learning rate.
- Track output length, tool-call count and refusal rate; sudden shifts often mark an exploit.
- Run the general-capability regression set at checkpoints, not only at the end.

## 7. Judging the result

Report, for the trained model and the untrained base on the same held-out tasks: success rate with intervals, number of non-skipped groups and trajectories actually trained on, regression-set scores, and behaviour on a few out-of-distribution tasks. A claim that the agent "learned" without the base-model comparison is not evidence: one book's RL demo reported 8 of 10 held-out puzzles solved without ever scoring the untrained model, after training on almost no signal.
