# Sandboxing code execution and computer use

Use when the agent writes or runs code, uses a shell, installs packages, edits files, drives a browser, or operates a
desktop. Approval decides *whether* something runs; isolation decides *what it can reach* when the approval was wrong.
For users who cannot read the command, isolation is the only control that works [ILLUSTRATED ch10].

## Three cumulative layers

[DEFGUIDE ch6] separates three kinds of sandboxing, each adding to the one below:

- **Runtime isolation** constrains *where* code runs: container, syscall sandbox, VM.
- **Ephemeral environments** constrain *how long* state persists: created per task, session or user, destroyed after.
- **Governed execution** constrains *who may run what, when*: execution sits behind a structured interface with
  policies, budgets, timeouts and approvals, outside the agent process.

A complete design names its choice in all three.

## Tier selection

| Tier | Isolates | Startup | Fits | Caveat |
|---|---|---|---|---|
| Capability-scoped interpreter (e.g. Monty) | Starts empty; only host functions you pass in are reachable | Microseconds | Code mode composing tools you already govern | Experimental; runs in your process, so an escape compromises the host. Nest it inside a container in production |
| Hardened container | Process and filesystem | Hundreds of ms | Internal tasks on trusted data; local MCP servers | Not a hard security boundary on its own [DEFGUIDE ch6] |
| Syscall sandbox (gVisor) or microVM (Firecracker) | Kernel surface or hardware boundary | Higher; both integrate with Kubernetes | Untrusted or user-supplied code, package installs, code influenced by untrusted content | Route only risky workloads through hardened nodes to control cost |
| Cloud sandbox (E2B, Daytona, Runloop and similar) | Ephemeral VM per run, off your infrastructure | Per-run provisioning | Dependency-heavy code, parallel runs | Code and data leave your environment; vendor dependency |

Quick pick:

| Situation | Minimum |
|---|---|
| Model composes your own governed tools, no file or network access | Capability-scoped interpreter, each host function through the policy gate |
| Model-written analysis code on internal, non-sensitive data, no untrusted input in the run | Hardened container, network off |
| Code shaped by untrusted content, user-uploaded code, or `pip install` at runtime | gVisor or microVM, or a cloud sandbox if data may leave |
| Regulated or customer data that must not leave | Self-hosted gVisor or microVM; never a third-party sandbox without a data agreement |
| Browser or desktop computer use | Dedicated VM or container with a separate browser profile (below) |
| Running model code with `exec`/`eval` on the host | Never acceptable, whatever the approval flow |

## Baseline hardening for any tier

- Non-root user; read-only root filesystem; exactly one writable work directory.
- No mounts of the home directory, SSH keys, cloud credentials or the Docker socket.
- CPU, memory, process-count, disk and wall-time limits; output size caps before results return to the model.
- Network off by default. If needed, egress through a proxy with a domain allowlist; block cloud metadata endpoints
  and private IP ranges.
- Fresh environment per user or session, destroyed afterwards; never share a sandbox between users
  [ILLUSTRATED ch10].
- Secrets absent unless a step needs one; then a short-lived, narrowly scoped token injected for that step.
- Logs of commands and file writes, kept outside the sandbox.
- Put agent execution in the locked-down container and the UI in a more permissive one, joined by a small internal
  API, rather than loosening the execution container to suit a UI framework [DEFGUIDE ch6].

## Paths: resolve first, then check

Containers don't stop traversal bugs inside the container. Blocking `..` misses encoded traversal, and a string-prefix
check lets `/home/kyle-evil` pass as `/home/kyle` [MCP ch7]. Decode, resolve, then test containment:

```python
from pathlib import Path
from urllib.parse import unquote

ROOT = Path("/workspace").resolve()

def safe_path(user_path: str) -> Path:
    p = (ROOT / unquote(user_path)).resolve()   # collapses .. and follows symlinks
    if not p.is_relative_to(ROOT):              # containment, not string prefix
        raise PermissionError(f"outside workspace: {user_path}")
    return p
```

## Code mode (programmatic tool calling)

Letting the model write one program that calls many tools saves tokens and round trips, but it turns a successful
injection from a misrouted tool call into code execution [DEFGUIDE ch6]. It is only cheap if the sandbox already exists.

- Run the program in a deny-by-default interpreter: no imports, no filesystem, environment or network; only the host
  functions you expose.
- Each exposed function still goes through the policy gate (allowlist, arguments, budget, approval). Approved calls
  run on the host, where credentials live; the program never holds them.
- Cap the number of host calls per program; return denials into the program as exceptions so it can handle them.
- Expose narrow functions. Injected code can still misuse anything you expose.

## Coding agents

| Capability | Default |
|---|---|
| Read, list, search files | Allowed, size-capped, inside the workspace |
| Write or edit files | Inside the workspace root only; auto inside a sandbox, approval if on a developer's machine |
| Run commands | Allowlist (test runner, linter, build); timeout; truncated output |
| Network | Off; allowlist package mirrors if installs are needed |
| `git push`, deploy, publish, change CI or secrets | Irreversible tier: goes out as a pull request for human review |

"Done" is decided by tests or a state check, not by the model's claim. Measured data point (external, 2025-10):
Anthropic reports that sandboxing Claude Code's filesystem and network access cut permission prompts by 84% internally,
which reduces approval fatigue as well as risk.

## Computer use and browser agents

A browser agent is a lethal trifecta by default: page text is untrusted, logged-in sessions are private data, and
typing, posting and buying are external channels. Measured residual (external, Anthropic, 2025): browser-agent attack
success fell from 23.6% to 11.2% with mitigations; one in nine is not acceptable for an agent holding real sessions.

- Dedicated VM or container per session; a separate browser profile with **no personal or production sessions**.
  Never attach the agent to someone's everyday browser.
- No credentials unless the task needs them; for logins, prefer a human step (or an out-of-band URL flow) so the
  password never passes through the model.
- Domain allowlist enforced by proxy, plus blocked site categories.
- Human confirmation before purchases, posting or sending, sharing personal data, accepting terms of service, and
  changing account settings.
- Treat everything on screen as untrusted content, including text in images.
- Prefer the most structured surface that exists: API or CLI, then DOM or accessibility tree, then pixels. An API call
  can be validated before it runs; a click can only be checked afterwards.
- Vendor guidance (as of 2026-10, Anthropic computer-use docs) repeats these points: dedicated VM or container, minimal
  credentials, domain allowlist, confirmation for consequential actions.

## Red flags in code review

- `exec(`, `eval(`, `subprocess` with `shell=True`, or `os.system` on model output outside a sandbox.
- A node, class or service called "sandbox" that runs code in-process.
- Docker socket mounted into the agent container; container running as root; `--privileged`.
- The whole host environment passed to a child process or MCP server.
- Path checks with `startswith` or a `".." in path` test.
- One long-lived sandbox shared across users or sessions.
- Agent attached to a real user's logged-in browser.
