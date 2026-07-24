# Installation, Configuration, Clipboard, and Environment Audit

## Scope

Reviewed TPM/manual loading, executable discovery, configuration acquisition and validation,
effective tmux option scope, OSC52 and optional paste behavior, platform fallbacks, SSH/nesting,
packaging, CI, and documentation claims. Non-macOS fallbacks were inspected statically only, as
agreed.

tmux-version statements rely on
[tmux 3.2–3.6b Runtime Semantics](02-tmux-3.2-to-3.6b.md).

## Findings

### IE-1 — Advertised tmux 3.2 support is false

- Classification: confirmed compatibility defect
- Severity: high
- Confidence: high
- Environment: tmux 3.2 and 3.2a

The unconditional popup command uses `-B`, introduced in tmux 3.3. README and clipboard/debug
troubleshooting tell users that 3.2 is sufficient. On that version popup launch is rejected and
the parent normally presents it as cancellation; stale result state can make the outcome worse.

Remediation direction: either stop using `-B` for the old baseline or raise and enforce the
minimum. The proposed 3.6b floor makes the claim truthful and gains additional relevant fixes.

### IE-2 — Effective `word-separators` scope is not read from the source pane

- Classification: probable configuration correctness defect
- Severity: medium
- Confidence: medium-high
- Environment: multiple sessions or non-global `word-separators`

`word-separators` is a tmux session option in the reviewed versions. The plugin batch-reads the
global option defaults with `show-window-option -g`, not the effective value in the captured
pane's session. A user can therefore see tmux copy-mode and flash-copy disagree about word
boundaries despite the documentation saying the plugin honors tmux's setting by default.

Remediation direction: query the effective option against the stable source pane/session and
retain the explicit global `@flash-copy-word-separators` override policy.

Regression evidence needed: two sessions with different separator values, an explicit plugin
override, inherited defaults, and a source pane that is not in the most recently used session.

### IE-3 — Documented timeout validation is not implemented

- Classification: confirmed defect
- Severity: medium
- Confidence: high
- Environment: invalid or long timeout configuration

Configuration documentation says idle-timeout values below one are ignored. `get_int()` accepts
every integer, and `FlashCopyConfig` does not validate timeout or warning. Zero and negative
timeouts therefore cause immediate expiry rather than falling back. Large valid values conflict
with the separate fixed 35-second parent watchdog.

Remediation direction: validate the timeout pair once, define fallback/bounds explicitly, and
derive the parent watchdog from the validated result.

Regression evidence needed: non-integer, negative, zero, one, warning/timeout ordering, and long
timeouts.

### IE-4 — Invalid booleans silently become false, even when the default is true

- Classification: confirmed configuration robustness defect
- Severity: low to medium
- Confidence: high
- Environment: mistyped configuration

Any nonempty string outside the accepted true set is parsed as false. Thus a typo such as `onn`
silently disables default-on behavior including reverse search, auto-paste, or range selection
instead of using the declared default or reporting invalid configuration.

Remediation direction: parse explicit true and false sets and return “invalid” separately so the
loader can fall back and diagnose.

Regression evidence needed: documented true/false spellings, case variations, empty/unset, and
unknown values for both default-true and default-false options.

### IE-5 — Custom label configuration can produce labels the input loop cannot select

- Classification: confirmed defect
- Severity: medium
- Confidence: high
- Environment: custom `@flash-copy-label-characters`

Label characters receive no semantic validation. With auto-paste enabled, `;` and `:` are
intercepted as modifiers before label lookup, yet the search engine can assign them as labels.
Control/newline, zero-width, or multi-cell characters create further unselectable or
layout-corrupting labels described in the rendering audit.

A focused probe with label alphabet `;:` assigned `;` to a match even though that input can never
select it under default auto-paste behavior.

Remediation direction: validate a unique alphabet of exactly one-cell printable input symbols
and reserve all active control/modifier keys before assignment.

### IE-6 — The loader path is sensitive to plugin-directory shell syntax

- Classification: probable installation/security-adjacent defect
- Severity: medium
- Confidence: high for boundary; path-specific reproduction still needed
- Environment: manual/TPM path containing whitespace or shell metacharacters

The shell loader discovers its directory safely, but installs the absolute entrypoint as a
`run-shell` operand. `run-shell` subsequently executes through `/bin/sh`; tmux parsing/format
expansion and shell parsing are distinct layers. The parent-to-child popup uses argv operands and
does not share this weakness.

Remediation direction: preserve the path as data through tmux and shell quoting, or invoke it
through an execution form that does not reinterpret it. Test installed paths containing spaces,
single quotes, brackets, dollar signs, semicolons, and format-looking text.

### IE-7 — Runtime interpreter selection is independent of project installation

- Classification: environment compatibility hazard
- Severity: medium
- Confidence: high
- Environment: multiple Python installations or restricted tmux server PATH

The binding executes an executable script with `#!/usr/bin/env python3`. `uv sync` and editable
package installation do not cause that shebang to choose the project's virtual environment.
Runtime succeeds only when the tmux server's inherited PATH resolves `python3` 3.10+ with access
to the checked-out source tree.

The source tree deliberately inserts its repository root into `sys.path`, so no installed Python
package is required. That is coherent for TPM distribution but should be documented and tested
as the actual deployment model.

Remediation direction: document interpreter/PATH resolution clearly and provide an intentional
configuration or launcher strategy when users need a non-default Python.

Regression evidence needed: tmux server started before PATH changes, system Python below 3.10,
virtual environment present but inactive, and plugin paths on standard TPM/manual installs.

### IE-8 — OSC52 command success is only attempted-delivery success

- Classification: environment risk
- Severity: medium
- Confidence: high
- Environment: terminal without usable OSC52, multiple clients, SSH/nesting

`tmux set-buffer -w` returning zero proves tmux accepted the request, not that the outer terminal
changed its clipboard. Terminal capability advertisement, `set-clipboard`, client selection, and
terminal policy remain external. Because a zero status stops fallback processing, native tools
will not repair a silently ignored OSC52 sequence.

The command also omits explicit target-client identity, so multiple attached clients may direct
OSC52 toward a terminal other than the invoker.

Remediation direction: describe success as attempted delivery, target the launching client, add
capability diagnostics, and avoid promising observation the process cannot verify. A 3.6b
minimum improves OSC52 capability detection but cannot override terminal policy.

### IE-9 — tmux-buffer fallback is reported as copy success without a system clipboard

- Classification: documented semantic risk
- Severity: low to medium
- Confidence: high
- Environment: OSC52 and native fallbacks unavailable

The final fallback stores text only in tmux, returns true from `Clipboard.copy()`, and allows the
outer workflow to report success. The detailed clipboard guide discloses this, while top-level
feature language says the selection is copied to the system clipboard.

Remediation direction: represent delivery destination in the result (`system clipboard`,
`tmux-only`, or failure) and make diagnostics/user expectations explicit.

### IE-10 — Auto-paste behavior is unsafe for some multiline/interactive targets

- Classification: environment-specific behavioral risk
- Severity: medium
- Confidence: high
- Environment: shells, REPLs, editors, remote panes, bracketed-paste-aware applications

tmux `paste-buffer` converts LF to CR by default and only adds bracketed-paste markers with `-p`.
The plugin omits `-p` and `-r`. A multiline range can therefore be interpreted as multiple
submitted commands rather than one guarded paste, depending on the target application. This is
stable documented tmux behavior, not fixed merely by raising the minimum.

Remediation direction: define whether auto-paste means literal insertion, command-like paste, or
application-aware paste; choose tmux flags deliberately and document the security/behavior trade.

Regression evidence needed: multiline ranges into a shell, editor, and bracketed-paste-aware
application, with auto-paste clearly distinguished from copy.

### IE-11 — CI validates Python breadth but not the shipped tmux runtime

- Classification: confirmed evidence gap
- Severity: medium
- Confidence: high
- Environment: release qualification

CI runs type/lint/format checks and unit tests on Python 3.10–3.14 on Ubuntu. It does not install
or exercise tmux, source the shell loader, launch the executable entrypoints, validate popup
flags against the minimum version, or test macOS despite macOS clipboard support.

This explains how 97% `src` coverage coexists with a broken advertised tmux minimum.

Remediation direction: add a small real-tmux compatibility/integration matrix centered on the
declared minimum and 3.6b, while retaining Python 3.10 coverage. Detailed design belongs to the
test-evidence ticket.

## Static platform-fallback risks

These are reported without live cross-platform validation:

- `pbcopy` runs on the host where tmux/Python executes. In an SSH session to macOS, that is the
  remote Mac's clipboard, not necessarily the user's local terminal clipboard.
- `xclip` and `xsel` require X11 plus a usable `DISPLAY`; they do not cover native Wayland
  clipboards and may block/fail in headless or remote environments.
- No Windows/WSL-native clipboard command is attempted.
- The tmux-only buffer fallback is portable but does not fulfill a system-clipboard promise.

These fallbacks should remain secondary to OSC52, consistent with the agreed review scope.

## Packaging/install non-findings

- The loader and both Python entrypoints have executable mode in the repository.
- Direct source imports are intentional and make TPM checkout deployment independent of a PyPI
  package; release documentation correctly says the project is distributed through Git tags.
- Python 3.10–3.14 unit coverage in CI is useful and should be retained even if runtime
  integration coverage is added.
