# Regression Coverage and Evidence Gaps

## Current baseline

Local verification on macOS/Python 3.14.6:

- `uv run pytest -q`: 283 passed in 3.48 seconds.
- configured `src` coverage: 97% (856 statements, 28 missed).
- `ty check`: passed.
- `ruff check`: passed after the local scratch benchmark was marked as an intentional import-path
  harness.
- `ruff format --check`: passed.

CI strengths:

- unit tests run on Python 3.10, 3.11, 3.12, 3.13, and 3.14;
- type, lint, and format checks run on a current Python;
- subprocess success, error, exception, and timeout branches in `src` have broad mock coverage;
- ASCII search, ranges, modifiers, configuration parsing, clipboard fallback order, ANSI SGR
  helpers, and popup argument construction are well covered in isolation.

## Why 97% does not represent runtime confidence

Coverage is configured only for `src`. It excludes:

- the 24-line shell loader;
- the 190-line parent executable;
- the 931-line interactive executable as a process and its top-level `main()`.

Some interactive classes are dynamically imported and unit-tested, but coverage reporting does
not include that script and the actual argparse/buffer/exit protocol is not exercised
end-to-end. No test:

- sources the plugin loader in tmux;
- invokes a real key binding or `run-shell`;
- launches a real popup;
- runs against tmux 3.2, 3.3, or 3.6b;
- attaches multiple clients;
- observes real tmux buffer ownership/cleanup;
- validates a real terminal cell layout;
- measures performance regressions.

Nearly all tmux behavior is replaced with mocks returning the shape the implementation expects.
This tests Python branching well but cannot detect unsupported tmux flags, command parsing,
target rules, buffer display semantics, popup coordinates, terminal behavior, or version drift.

## Tests that encode implementation rather than contract

These are not intrinsically bad tests, but they can protect defects:

- `test_get_int_negative` asserts that `-5` is returned, while user documentation says
  idle-timeout values below one are ignored.
- popup-position unit tests assert the current bottom+1 formula without real tmux evidence that
  it overlays a non-top pane.
- popup buffer-read failure asserts cancellation but not snapshot-buffer cleanup.
- popup timeout asserts a fixed 35-second timeout outcome without relating it to configured child
  lifetime.
- clipboard paste-failure tests use an exception; the production helper normally reports failure
  as `False`, which the caller ignores while logging success.
- label-placement tests use code-point `len()` and ASCII, so “without adding width” does not mean
  terminal-cell width.

Contract-level assertions should sit above these implementation tests.

## Minimum evidence by finding

| Finding area | Minimum regression evidence |
| --- | --- |
| False tmux 3.2 minimum | Run the shipped popup command on 3.2/3.2a (expected rejection before policy change) and supported minimum/3.6b (expected launch); assert declared-version gate or flags. |
| Stale result acceptance | Seed an old result, fail/reject child before write, and assert no copy; distinguish cancel/copy/paste/error outcomes and inventory buffers after each. |
| Shared buffer concurrency | Interleave two same-pane invocations and two-client invocations; selections, paste data, and cleanup must remain isolated. |
| Configurable timeout | Run below/equal/above old 35-second boundary with active input; one owner controls expiry and no child/buffer survives. |
| Implicit pane/client targeting | Two attached clients focused on different panes/terminals; capture, popup, OSC52 target, and paste remain bound to invoker. |
| Popup geometry and resize | Real tmux top/bottom/left/right panes, status line top/bottom, resize during word/range stages, and pixel/cell overlay assertions or stable screenshots. |
| Hidden bottom row | Render and search the same snapshot rows; reverse Enter/labels cannot select anything absent from output. |
| Label collision | Repeated/overlapping occurrences; every assigned selectable label is rendered exactly once. |
| Separator regex | Property/parameter tests treating every configured regex-special character literally, especially hyphen positions and documented defaults. |
| Unicode offsets | Dotted I and other expanding mappings; original highlight, copied word, and precise range offsets remain aligned. |
| Terminal cell width | CJK, emoji, combining and ZWJ graphemes, tabs on 3.6b, custom labels, wide prompts; frame width and cursor cells stay stable. |
| Effective option scope | Two sessions with different `word-separators`, plus explicit plugin override; source pane determines inherited value. |
| Invalid config | Unknown booleans, noninteger/zero/negative/large timeout pairs, reserved/custom labels, structural terminal controls; assert fallback and diagnostics. |
| Child buffer serialization | Round-trip exact bytes/text through the chosen tmux primitive on affected versions with SGR, whitespace, tabs, newlines, and escapes. |
| Loader quoting/Python PATH | Install paths with spaces/metacharacters and tmux-server PATH resolving supported/unsupported Python interpreters. |
| Auto-paste truth/semantics | False return from each subprocess, stale/missing paste buffer, multiline input with and without bracketed-paste-aware target; copy and paste outcomes remain separate. |
| OSC52 environment | Two target clients with different capabilities; assert selected target and diagnostic state, not unverifiable system clipboard observation in headless CI. |
| Performance | Fixed ordinary/large/dense fixtures with budgets for construction, incremental search, match grouping, render planning, peak memory, output size, and subprocess count. |

## Recommended layered test strategy

### Layer 1 — Pure contract/property tests

Keep the fast current suite and add:

- normalization-to-original offset properties;
- literal separator properties;
- assigned-label/rendered-label bijection;
- cell-width and grapheme fixtures;
- configuration semantic validation;
- explicit popup result state-machine tests;
- deterministic performance counters/complexity guards where wall time would be flaky.

### Layer 2 — Executable protocol tests with a fake tmux CLI

Put a recording fake `tmux` first on PATH and execute both shipped scripts as processes. This can
verify:

- argv, stdout/stderr, and exit codes;
- snapshot/result protocol and exact text;
- cleanup after injected failures;
- timeout propagation;
- Python interpreter/entrypoint behavior;
- parent handling of cancel/copy/paste/error.

It will cover the executable scripts without requiring a terminal server, while remaining honest
that tmux semantics are not validated.

### Layer 3 — Real tmux compatibility integration

Run a small matrix at the declared minimum and 3.6b:

- source the loader and inspect the binding;
- launch popup in a PTY/control-capable client;
- exercise one word copy, range copy, cancel, resize, multi-client target, and concurrency;
- inspect buffers and child processes after every run;
- round-trip capture/buffer content and option scope.

If the project immediately raises its floor to 3.6b, retain a one-time 3.2/3.3 compatibility test
or documented probe as evidence for the migration decision rather than an ongoing supported
matrix.

### Layer 4 — Environment smoke checks

Keep these small and mostly manual:

- macOS OSC52 and `pbcopy` fallback diagnostics;
- one SSH/nested tmux OSC52 path;
- Linux X11 fallback only when an appropriate runner exists;
- terminal-specific cell rendering where headless emulation is insufficient.

Do not make broad fallback live validation a release gate under the agreed scope.

## Coverage reporting recommendation

Report two separate signals:

1. Python unit coverage over `src` plus executable-script modules;
2. runtime contract scenarios completed against real tmux versions.

A single statement percentage cannot represent shell/tmux/terminal integration confidence. The
confirmed `display-popup -B` baseline mismatch is the clearest proof: every current test passes
while the advertised minimum rejects the shipped command.
