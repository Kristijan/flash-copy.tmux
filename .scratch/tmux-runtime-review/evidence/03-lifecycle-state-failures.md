# Runtime Lifecycle, State, and Failure Audit

## Method

Traced every normal, cancellation, timeout, subprocess-error, child-error, and cleanup branch
across the loader, parent process, popup orchestration, child process, tmux IPC buffers, and
optional paste. Version semantics are taken from
[tmux 3.2–3.6b Runtime Semantics](02-tmux-3.2-to-3.6b.md). Focused mock probes exercised the
protocol without modifying production code.

## Findings

### LS-1 — Failed popup execution can copy a stale prior selection

- Classification: confirmed defect
- Severity: critical
- Confidence: high
- Versions: all supported tmux/Python versions
- Runtime path: popup result protocol

The result buffer is not deleted before a new invocation. After `display-popup` returns, the
parent reads the result buffer regardless of popup exit status. Any old buffer left by a prior
abnormal invocation is therefore accepted as the new selection if the popup is rejected or the
child exits before writing its own result.

A focused probe made `display-popup` return status 1 and `save-buffer` return
`STALE-SELECTION`; `_launch_popup()` returned `("STALE-SELECTION", False)`. The outer parent would
then copy that stale text.

This combines dangerously with the confirmed tmux 3.2 incompatibility: tmux 3.2 rejects `-B`,
and a stale result buffer can turn that rejection into an unintended copy.

Remediation direction: use an invocation-unique result channel, remove/initialize it before
launch, require an explicitly recognized child outcome, and reject result data on every other
exit. A single status bit plus buffer existence is not a sufficient transaction protocol.

Regression evidence needed:

- stale result plus popup rejection;
- child failure before result write;
- cancel, copy, auto-paste, and timeout as distinct outcomes;
- parent crash/restart between buffer creation and cleanup.

### LS-2 — Pane-derived and fixed buffer names are not invocation-safe

- Classification: probable correctness/concurrency defect
- Severity: high
- Confidence: high
- Versions: all supported tmux versions
- Runtime path: snapshot IPC, result IPC, and auto-paste

tmux paste buffers are server-global. Snapshot and result names contain only the pane id; the
auto-paste buffer is always `flash-paste`. Same-pane overlapping, nested, or reentrant
invocations therefore share mutable storage. One parent can overwrite or delete another
invocation's snapshot/result, and one auto-paste can replace another's payload.

The implementation comment says pane-specific names avoid concurrent conflicts, but they isolate
different panes only. tmux 3.6's behavior of modifying an existing popup when invoked inside a
popup increases the need to define reentrancy explicitly.

Remediation direction: assign a unique invocation id, include it in every transient buffer, pass
it explicitly to the child, and give one owner responsibility for cleanup. Avoid a named
auto-paste buffer where tmux can consume uniquely scoped data directly.

Regression evidence needed:

- two invocations from one pane/client;
- two clients invoking against one pane;
- nested/reentrant invocation;
- interleaved writes, reads, and cleanup with distinct selections.

### LS-3 — Configurable child lifetime conflicts with a fixed 35-second parent timeout

- Classification: confirmed defect
- Severity: high
- Confidence: high
- Versions: all supported versions
- Runtime path: popup wait and idle timeout

The child idle timeout is user-configurable with no upper bound. The parent always kills its
`tmux display-popup` client after 35 seconds. A valid configuration such as 60 seconds therefore
cannot work: the parent cancels the session well before the child contract says it should expire.
The source comment describes “35s vs 30s child timeout,” but the actual default child timeout is
15 seconds and the documented option permits other values.

Killing the local tmux CLI on timeout also does not establish, in this code, that the server-side
popup child has terminated before shared buffers are deleted.

Remediation direction: make one layer own timeout policy. Derive any parent watchdog from the
validated child configuration plus bounded shutdown grace, and explicitly terminate/confirm the
popup child before cleanup.

Regression evidence needed:

- idle timeouts below, equal to, and above 35 seconds;
- active input beyond 35 seconds;
- parent timeout with verification that no child/buffer survives;
- zero/negative/unreasonably large configuration validation.

### LS-4 — Source pane and clipboard client identity are resolved implicitly

- Classification: probable multi-client targeting defect
- Severity: high
- Confidence: medium-high
- Versions: all reviewed tmux versions; explicit targeting already exists in 3.2
- Runtime path: loader invocation, initial pane lookup, popup context, OSC52 target

The binding's `run-shell`, initial `display-message`, `display-popup`, and OSC52
`set-buffer -w` omit relevant explicit targets. Later capture and paste correctly use the pane id
obtained at startup, but the first pane and eventual terminal client are selected through tmux
“current/recent” rules.

This normally appears correct with one attached client, but it is not a guarantee that the pane
or terminal client which triggered the binding remains the implicit target across multiple tmux
CLI connections, clients, focus changes, or delayed work.

Remediation direction: capture launching pane and client identity in the binding/run-shell
context and forward them explicitly through popup, OSC52, and paste operations.

Regression evidence needed: two clients on distinct terminals, rapid focus changes, and
invocation from nonstandard command contexts.

### LS-5 — Failure paths leak state and collapse errors into cancellation

- Classification: confirmed robustness defect
- Severity: medium
- Confidence: high
- Versions: all supported versions
- Runtime path: child main, popup orchestration, cleanup

Specific branches:

- if parent result-buffer read fails, snapshot-buffer cleanup is skipped because both deletions
  live after the successful read inside the same `try`;
- general popup exceptions and timeout clean only the snapshot buffer, not a possible result
  buffer;
- child top-level exceptions print a traceback but fall through without an explicit nonzero exit,
  so `-E` closes the popup with apparent status 0;
- the parent converts most popup failures to `(None, False)`, indistinguishable from deliberate
  cancellation;
- buffer write failure is suppressed and silently changes the snapshot contract from captured
  data to a later child recapture.

These paths create the stale state required by LS-1 and make field diagnosis difficult.

Remediation direction: model outcomes explicitly, centralize idempotent cleanup in `finally`,
return nonzero for child failure, and distinguish cancel from operational error in logs and
parent behavior.

Regression evidence needed: failure injection at every tmux subprocess boundary with buffer
inventory and explicit outcome assertions afterward.

### LS-6 — Auto-paste reports success without checking either paste operation

- Classification: confirmed defect
- Severity: medium
- Confidence: high
- Versions: all supported versions
- Runtime path: optional paste

`run_command_quiet()` returns `False` on a nonzero status; it does not raise. `copy_and_paste()`
ignores both returned booleans and logs `Success` unconditionally. A focused probe made both
commands return `False`; the function returned `True` and emitted
`Auto-paste to pane %1: Success`.

The public return value intentionally represents copy success, so it may remain true, but the
diagnostic and internal paste outcome are false. Failure of the initial named-buffer write also
does not prevent a subsequent paste attempt against potentially stale `flash-paste` data.

Remediation direction: gate paste on successful buffer write, record paste status truthfully,
and keep copy success distinct from paste success.

Regression evidence needed: first command failure, second command failure, dead target pane,
stale fixed buffer, and successful copy with failed paste.

### LS-7 — Non-top pane popup positioning appears to use the pane bottom as its top

- Classification: probable positioning defect
- Severity: medium
- Confidence: medium-high
- Versions: all supported versions
- Runtime path: popup geometry

For a top pane, the calculated popup y-coordinate is `pane_top`. For every other pane it is
`pane_bottom + 1`, while width and height remain the pane's full dimensions. Official tmux
semantics make literal popup coordinates client-relative; they do not define y as a bottom
anchor. A bottom pane beginning at row 20 and ending at row 39 is therefore requested at row 40
with its full height rather than at row 20.

Current unit tests encode this calculation rather than validating real overlay geometry. Live
attached-client confirmation is still needed before promoting confidence to “confirmed.”

Remediation direction: derive coordinates from one documented tmux coordinate system and test
real top/bottom/left/right panes, status-line positions, and fallback geometry.

### LS-8 — Resizes and fallback recapture can break snapshot consistency

- Classification: probable compatibility defect
- Severity: medium
- Confidence: high for race, environment-dependent impact
- Versions: especially relevant from tmux 3.3 onward when popups survive resize and panes redraw
- Runtime path: capture, geometry, child fallback, rendering

Capture, geometry query, popup launch, child terminal-size query, and rendering occur at different
times. The source pane can resize or redraw between them. If snapshot IPC fails, the child
recaptures still later while configuration/geometry came from the earlier invocation.

Remediation direction: choose and document immutable-snapshot behavior, make handoff failure an
error rather than implicit semantic change, and define resize handling (reflow, recapture, or
graceful cancel).

Regression evidence needed: resize and source output before launch, during popup, and during
range selection.

### LS-9 — Idle timing uses an adjustable wall clock

- Classification: speculative hardening/performance opportunity
- Severity: low
- Confidence: high
- Versions: all supported Python versions

Idle elapsed time uses `time.time()`. Wall-clock corrections can delay or accelerate expiry.
`time.monotonic()` is the contract-appropriate source for elapsed duration. This should be
addressed together with single-session raw-mode ownership, not as an isolated optimization.

## Lifecycle priorities

1. Prevent stale-result acceptance (LS-1).
2. Give every invocation isolated state and cleanup ownership (LS-2, LS-5).
3. unify timeout ownership (LS-3).
4. bind pane/client identity explicitly (LS-4).
5. make paste outcome truthful and safe (LS-6).
6. verify geometry and resize behavior in a real tmux client (LS-7, LS-8).
7. adopt monotonic elapsed time (LS-9).
