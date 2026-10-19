# Sandboxing code execution and computer use

Use when the agent writes or runs code, uses a shell, installs packages, edits files, drives a browser, or operates a
desktop. Approval decides *whether* something runs; isolation decides *what it can reach* when the approval was wrong.
For users who cannot read the command, isolation is the only control that works [ILLUSTRATED ch10]. Put the effort
here rather than in the model's refusals: Ng names buggy sandboxing and monitoring as key to enabling a 2026 agent
breach, and holds the people who build and use agents responsible, not the agent
[NG Who's Responsible for Irresponsible AI?, 2026-09-18].

## What earns the name "sandbox"

Call it a sandbox only if it bounds files, network, time and memory, and you have checked each. A container is useful
isolation, not proof of it: verify network paths, mounts, identities and host-escape protections independently
[AISEC repo: part8_multi-agent_harness_spec/safety-governance.md]. Three shapes that look like sandboxes and aren't:

- **`exec` called a sandbox.** A graph node named `sandbox` sends model code, with no timeout, to a local service that
  runs it with `exec` [BUILDAGENTIC repo: codeact_browser/create_codeact.py]. The name changes nothing about what the
  code can reach.
- **An unauthenticated execution service.** That same service listens on every interface with no authentication
  [BUILDAGENTIC repo: codeact_browser/browser_service.py], so anything on the network can run code on it. An
  execution service is an endpoint like any other: private network or loopback only, authenticated callers, a time
  and memory limit per call, fresh state per call.
- **A path jail that one tool skips.** File tools check paths by string prefix while a code tool runs a subprocess
  that can open any path [ILLUSTRATED repo: src/illustrated_agents/toolbox.py]. Confinement has to hold for every
  tool that touches the filesystem, at the process level.

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
| Hosted browser or desktop (a third-party cloud browser service) | Browser session on the vendor's infrastructure | Per-session provisioning | Browser agents without running your own fleet | The vendor is a data processor holding logged-in sessions: cover the data agreement, residency, isolation between the vendor's customers, who can see session recordings, and how cookies and credentials are stored and deleted. Its API key belongs to the broker, never to the agent's context or URLs |

Quick pick:

| Situation | Minimum |
|---|---|
| Model composes your own governed tools, no file or network access | Capability-scoped interpreter, each host function through the policy gate |
| Model-written analysis code on internal, non-sensitive data, no untrusted input in the run | Hardened container, network off |
| Code shaped by untrusted content, user-uploaded code, or `pip install` at runtime | gVisor or microVM, or a cloud sandbox if data may leave |
| Regulated or customer data that must not leave | Self-hosted gVisor or microVM; never a third-party sandbox or hosted browser without a data agreement |
| Browser or desktop computer use | Dedicated VM or container with a separate browser profile (below) |
| Running model code with `exec`/`eval` on the host | Never acceptable, whatever the approval flow |

## Baseline hardening for any tier

- Non-root user; read-only root filesystem; exactly one writable work directory.
- No host mounts by default, and never the home directory, SSH keys, cloud credentials or the Docker socket. Check
  every bind mount's mode: a writable mount of a host path lets the agent write to the host and persist there, for
  example through credential configs whose helper commands the host runs later, shell start-up files, or prompt and
  config files that later sessions reload. If a host path must be shared, mount it read-only; credential and config
  folders are better not mounted at all, with the broker injecting what a step needs.
- Nothing the agent can write is later loaded by a more privileged component as code, configuration or instructions:
  the app's own source when its framework reloads on change, hooks, project settings, prompt files. Keep those paths
  outside the agent's write path, or record each one as a finding rated by what it reaches.
- CPU, memory, process-count, disk and wall-time limits; output size caps before results return to the model.
- A command timeout kills the whole process group (or the container), not only the shell. A timed-out command that
  keeps running is a finding.
- Network off by default. If needed, egress through a proxy with a domain allowlist; block cloud metadata endpoints
  and private IP ranges.
- Egress isolation is deny by default and covers the quiet routes: public DNS resolution, arbitrary package installs,
  production routes, corporate identity endpoints and shared mounts are unreachable unless a documented need names
  them [AISEC repo: part8_multi-agent_harness_spec/safety-governance.md]. Test from inside the sandbox that each
  is refused.
- Fresh environment per user or session, destroyed afterwards; never share a sandbox between users
  [ILLUSTRATED ch10].
- Secrets absent unless a step needs one; then a short-lived, narrowly scoped token injected for that step.
- Logs of commands and file writes, kept outside the sandbox.
- Put agent execution in the locked-down container and the UI in a more permissive one, joined by a small internal
  API, rather than loosening the execution container to suit a UI framework [DEFGUIDE ch6].

## Local listeners: loopback is not authentication

Binding a listener to loopback keeps other hosts out, not the user's own browser. A page open in any tab can reach
`localhost` through a cross-site WebSocket connection or DNS rebinding, so an unauthenticated local listener answers
any site the user visits. Every local HTTP or WebSocket listener (a VNC or remote-desktop proxy, the agent's web UI, a
development server, an MCP server over HTTP, a code-execution service):

- authenticates every request and every WebSocket upgrade with a token the page must present, not with an ambient
  cookie alone;
- checks Origin against an allowlist on every request and upgrade, and refuses unknown Host headers;
- for VNC and remote-desktop servers, keeps its own password or token even behind a proxy;
- for debug and development servers (auto-reload, interactive debugger consoles), is never reachable from the network
  and is off in anything shipped.

A proxy with single sign-on in front of the desktop must apply the Origin check on the WebSocket upgrade too. Test with
the exposure probes in [red-team-test-plan.md](red-team-test-plan.md) §Exposure probes. MCP specifics:
[mcp-hardening.md](mcp-hardening.md) §7.

## Paths: resolve first, then check

Containers don't stop traversal bugs inside the container. Blocking `..` misses encoded traversal, and a string-prefix
check lets `/srv/app-evil` pass as `/srv/app` [MCP ch7]. Decode, resolve, then test containment:

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
| Run commands | Allowlist (test runner, linter, build); timeout; truncated output. The allowlist limits what starts, not what runs: a test runner, build tool or package manager executes repository and dependency code, and allowed interpreters (`node -e`, `python -c`), package scripts and scripts the agent wrote run anything by name. It is a convenience, not a control, so contain the run itself (below) |
| Network | Off; allowlist package mirrors if installs are needed |
| `git push`, deploy, publish, change CI or secrets | Irreversible tier: goes out as a pull request for human review |

**Containment for a coding agent's runs.** Treat every command as arbitrary code. Use a tier for untrusted code (gVisor
or microVM), with no secrets in the environment, no Docker or other host sockets, the cloud metadata endpoint blocked,
and the network off apart from a package mirror. Tests that need containers run rootless inside the VM, never through a
mounted host socket.

"Done" is decided by tests or a state check, not by the model's claim. Measured data point (external, 2025-10):
Anthropic reports that sandboxing Claude Code's filesystem and network access cut permission prompts by 84% internally,
which reduces approval fatigue as well as risk.

### Forge and CI

A coding agent is judged by the checks and reviewers around it, so both sit outside its reach.
- The agent never merges and never approves. A code owner reviews the latest commit, and a new push dismisses earlier
  approvals ([human-oversight.md](human-oversight.md) §3, "When the platform already binds the approval").
- The checks that judge the agent's change come from a protected source (the base branch or a protected
  configuration), and tests and policy files are protected too ([controls-catalog.md](controls-catalog.md) §10).
- The pull request's code never runs in a privileged context: a job that holds a write token or secrets must not check
  out and run the change.
- Release and deploy secrets live only in protected environments used by a separate release that a person triggers,
  preferably with OIDC or trusted publishing instead of stored tokens. No agent run, and no job that runs the agent's
  code, can reach them. If a secret was ever reachable from an agent run, rotate it now.
- The agent's identity is a dedicated app or bot for one repository with the narrowest permissions it needs, and
  without permission to edit workflow files.

Platform notes (GitHub, checked 2026-10-19; verify against current documentation): a `pull_request_target` workflow
runs in the context of the base repository's default branch, and GitHub warns that running untrusted pull-request code
there can grant unintended access to write privileges or secrets; avoid it when the job must build or run the change.
Workflows triggered by `pull_request` from a fork receive no secrets and a read-only `GITHUB_TOKEN`
(https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows). Not re-checked on
that date: a GitHub App needs the `workflows` permission to change files under `.github/workflows/`, and rulesets can
require code-owner review and dismiss stale approvals on new pushes.

## Computer use and browser agents

A browser agent is a lethal trifecta by default: page text is untrusted, logged-in sessions are private data, and
typing, posting and buying are external channels. Measured residual (external, Anthropic's Claude for Chrome post,
2025-08, updated 2025-12): browser-agent attack success fell from 23.6% to 11.2% with mitigations; one in nine is not
acceptable for an agent holding real sessions. Figures like this date quickly: quote the date and source, and use the
vendor's latest measurement when there is one. Every screenshot also goes to the model provider (threat-catalog.md T6).

- Dedicated VM or container per session; a separate browser profile with **no personal or production sessions**.
  Never attach the agent to someone's everyday browser.
- No credentials unless the task needs them; for logins, prefer a human step (or an out-of-band URL flow) so the
  password never passes through the model. Act as a dedicated agent account with a narrow role, not as the employee
  ([controls-catalog.md](controls-catalog.md) §3, "Logged-in web apps").
- Gate pixel actions as well as tool calls ([controls-catalog.md](controls-catalog.md) §2, "Computer use").
- Domain allowlist enforced by proxy, plus blocked site categories.
- Human confirmation before purchases, posting or sending, sharing personal data, accepting terms of service, and
  changing account settings.
- Treat everything on screen as untrusted content, including text in images.
- Record sessions for audit to storage the agent can't reach or alter (write-once retention), and keep control-plane
  logs (who started which session, as whom) beside the recordings. Together with a least-privilege execution role,
  the recordings tie each action to a session and each session to a caller.
- Prefer the most structured surface that exists: API or CLI, then DOM or accessibility tree, then pixels. An API call
  can be validated before it runs; a click can only be checked afterwards.
- Vendor guidance (as of 2026-10, Anthropic computer-use docs) repeats these points: dedicated VM or container, minimal
  credentials, domain allowlist, confirmation for consequential actions.

## Red flags in code review

- `exec(`, `eval(`, `subprocess` with `shell=True`, or `os.system` on model output outside a sandbox.
- A node, class or service called "sandbox" that runs code in-process, or hands it to an `exec` service.
- A code-execution service listening on all interfaces, without authentication or a per-call timeout.
- A path check in the file tools that a code or shell tool can bypass.
- Docker socket mounted into the agent container; container running as root; `--privileged`.
- A writable bind mount of a host path, above all a home, credential or config folder.
- A local listener (VNC proxy, web UI, development or debug server) with no token or Origin check, on loopback too.
- An app that reloads its own code or config on change, where the agent can write that code or config.
- A command timeout that kills the shell but not the processes it started.
- The whole host environment passed to a child process or MCP server.
- Path checks with `startswith` or a `".." in path` test.
- One long-lived sandbox shared across users or sessions.
- Agent attached to a real user's logged-in browser.
