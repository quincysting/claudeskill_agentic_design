# Review method: scope, evidence, coverage and secrets

Use this in review mode (SKILL.md, Review mode) whenever the input is an existing agent's code, configuration or
documents. The evidence labels and the secrets rule are shared with the other review skills (agent-harness-designer,
agent-tool-designer, agent-ops-reviewer), so a label means the same thing in every review.

## 1. Scope: what is being judged

- **Reference code or product.** Record in the header whether the code is reference or demo code, or a product being
  offered (to whom, for what). Judge the verdict against that plan. "Block for offering it to employees as it stands"
  is more useful than an indictment of a demo that never claimed to be hardened.
- **Code-only review.** When the input is code with no logs, traces, dashboards or owners, say so in the header.
  Runtime facts (reachability, defaults in effect, whether a port is published beyond the host, whether a trace
  arrives) are then inferred and go under Confirm first.
- **Several variants of one system.** Name the one reviewed as the shipping candidate and rate that one. List the
  other variants' defects separately.
- **Parts that may not ship** (a second execution path, a demo runner, an optional extension or message channel):
  model them anyway, tag their findings "(if shipped)" at the priority of their consequence, and offer deleting the
  part as an alternative fix.

## 2. Evidence labels

Tag each fact a finding rests on:

| Label | Meaning | Cite |
|---|---|---|
| seen | Read in code, config or a document supplied for this review | file:line, config key or section |
| observed | Shown by logs, traces, metrics or a test run | the log line, trace or run |
| told | Stated by an owner or user and not checked | who said it |
| inferred | Follows from seen code plus a library, platform or language behaviour not checked here | the behaviour and the version it depends on |
| assumed | No evidence | the assumption |

- Severity follows the consequence if an inferred or assumed fact holds. The priority carries the weakest label it
  rests on, `P0 (inferred)` or `P0 (assumed)`, and blocks until the fact is checked (SKILL.md Step 8).
- Every inferred or assumed fact also goes under Confirm first, with the check that settles it and the findings that
  move if it turns out false.
- Don't use the older words "confirmed" and "stated". A sibling skill used "stated" to mean "told", so it misleads
  when applied to code you read.
- **What already works** needs the same evidence as a finding. Before writing "secrets come only from the config
  file", search for every way the code reads secrets, environment lookups included. A positive claim is as easy to get
  wrong as a negative one.

Generic example: "The execution service binds to all interfaces (seen, `<file>:<line>`), and none of its routes checks
authentication (seen, same file). Reachable from outside the host: inferred, depends on the ports the deployment
publishes; confirm first." With authentication seen absent the bind is a plain P0, and the reachability note makes
the verdict provisional.

## 3. Coverage before a verdict

- **Read the fix before recommending it.** Before calling a code path safe, or recommending it as the fix, read it,
  including the inherited and helper methods it delegates to. A subclass that quotes arguments for one action can
  still pass another action to its parent's unquoted code.
- **Search every file for each unsafe-call class.** Search the whole tree, not only the file with the first hit, and
  size the finding by all hits. Classes: shell strings (`shell=True`, `os.system`, a command built by string
  formatting), `eval` and `exec`, unsafe deserialisation, file paths built from model or user input, SQL built by
  string formatting, raw HTML rendering of model or page text, TLS verification turned off, and bind addresses.
- **Unread means unverified.** Files or line ranges you did not read go under Not verified, with the findings that
  could grow if they hold more hits. Never recommend code from them.
- **On a reading budget,** read every sink hit and every path you are about to recommend first, then list the rest as
  unread.

## 4. Secrets: cite, never reproduce

Cite a credential by file:line and kind (for example "messaging app secret literal"), never its value or any fragment
of it. The same holds for keys in URLs, logs and saved state. Public vendor defaults (a default admin user name, say)
may be named. An identifier designed to ship to clients (a public app key) is not a secret, but the secret paired with
it is. Before returning, search the draft for every credential literal found in the input and remove it. For a running
system the fix also names what to rotate (SKILL.md, Review mode).

## 5. Stubs and missing components

If tools are stubs (they return fixed values, print, or are placeholders) or a referenced component is absent:

- say so in the summary;
- ask what each becomes, or state the intended wiring from docstrings or the README as an assumption;
- review under that assumption, and say which findings or priorities change if it is false.

A stub that reports success it did not achieve is itself a finding. A feature with no real backend gets "remove" as a
fix option.

## 6. Dependencies without network access

Without network access, dependency age and known vulnerabilities are inferred: rate them P2 at most unless a known CVE
is cited from a dated source. What you can check offline is seen: pins and version ranges, the lock file and its
hashes, unpinned clones and third-party package repositories in build files, and modules imported but never declared.

## 7. Effort scale

S: under a day. M: up to two weeks. L: longer.
