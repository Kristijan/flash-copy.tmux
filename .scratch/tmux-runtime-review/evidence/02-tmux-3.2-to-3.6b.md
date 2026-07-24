# tmux 3.2–3.6b Runtime Semantics

## Scope and sources

This note compares the plugin's tmux-facing runtime with the official tmux manuals, source, and
release history from 3.2 through 3.6b. It does not use behavior introduced after 3.6b. Local tmux
3.7b behavior is deliberately not used as version evidence.

Primary sources:

- [tmux 3.2 manual](https://github.com/tmux/tmux/blob/3.2/tmux.1)
- [tmux 3.2 command source](https://github.com/tmux/tmux/tree/3.2)
- [tmux 3.6b manual](https://github.com/tmux/tmux/blob/3.6b/tmux.1)
- [tmux 3.6b command source](https://github.com/tmux/tmux/tree/3.6b)
- [tmux CHANGES through 3.6b](https://github.com/tmux/tmux/blob/3.6b/CHANGES)
- [official tmux clipboard guide](https://github.com/tmux/tmux/wiki/Clipboard)

The plugin operations assessed here are:

```text
bind-key ... run-shell <entrypoint>
display-message -p <format>
capture-pane -p -e -J -t <pane-id>
show-options / show-window-options
set-buffer / show-buffer / save-buffer / delete-buffer
display-popup -E -B ... <program> <argv...>
set-buffer -w
paste-buffer -b <name> -t <pane-id>
```

## High-confidence conclusions

### 1. The implementation does not actually run on tmux 3.2

The popup command always includes `-B`. The tmux 3.2 `display-popup` synopsis accepts only
`-C`, `-E`, `-c`, `-d`, `-h`, `-t`, `-w`, `-x`, and `-y`; its command source likewise has no
`B` in the accepted option template. `display-popup -B` (no border) was added in the changes
from 3.2a to 3.3. See the [3.2 popup command source](https://github.com/tmux/tmux/blob/3.2/cmd-display-menu.c#L49-L58)
and the [3.3 change entry](https://github.com/tmux/tmux/blob/3.6b/CHANGES).

Consequently, the current advertised tmux 3.2 minimum is a confirmed compatibility defect:
invocation reaches `display-popup`, tmux rejects `-B`, and the plugin converts the nonzero popup
result into cancellation. tmux 3.3 is the first release compatible with the command as presently
constructed. Raising the minimum to 3.6b makes the implementation and support claim agree; it
does not itself fix users on the currently claimed 3.2 baseline.

Although manuals before 3.6 describe only one `shell-command` operand, the source accepts an
unlimited operand count and passes multiple operands as an argv vector. This is true in the
[3.2 source](https://github.com/tmux/tmux/blob/3.2/cmd-display-menu.c#L49-L58) as well as
[3.6b](https://github.com/tmux/tmux/blob/3.6b/cmd-display-menu.c#L53-L67). The manual finally
documents `shell-command [argument ...]` in 3.6b. The plugin's multi-argument popup invocation is
therefore not another 3.2 incompatibility.

### 2. Stable pane IDs are appropriate, but the initial target is resolved implicitly

Both manuals state that `%` pane IDs are unique and unchanged for the life of a pane in a tmux
server, and that the pane ID is placed in `TMUX_PANE` for a pane's child process. Once the plugin
has obtained `%N`, explicitly targeting capture, geometry, and paste with it is correct.

The weak point is earlier: the binding executes `run-shell` without `-t`, and the parent then
runs `display-message -p '#{pane_id}'` without `-t`. tmux's general target rules choose a current
target when one is available, otherwise a recent target. `run-shell` itself supports `-t` in
both 3.2 and 3.6b and uses that pane as the format/output context. The plugin should not need a
3.6b minimum to bind and forward an explicit source pane identity; the relevant targeting
facilities already exist in 3.2.

This is a compatibility hazard rather than a version-specific confirmed defect: with one normal
attached client it will usually resolve as intended, but implicit "current" state is needlessly
sensitive to multiple clients, focus changes, delayed execution, and invocation without an
ordinary attached-client context. The official [3.2 target rules](https://github.com/tmux/tmux/blob/3.2/tmux.1#L709-L925)
and [3.6b target rules](https://github.com/tmux/tmux/blob/3.6b/tmux.1) do not guarantee that a
later standalone tmux client invocation means "the pane whose binding launched this shell."

### 3. Popup execution is argv-safe, but the loader remains a shell-command boundary

The Python popup call supplies more than one operand. tmux source handles this case as an argv
vector; only a zero- or one-operand popup is treated as a shell command. In current code,
configuration values such as prompt text, separators, labels, and colour escape sequences are
therefore passed as child arguments, not interpolated into one shell string. This materially
reduces shell-injection and quoting risk at the parent-to-child boundary.

By contrast, the loader installs `run-shell <absolute-entrypoint>` as a tmux command argument.
`run-shell` expands formats and executes its operand with a shell. Official documentation also
warns that commands may undergo both tmux parsing and shell parsing. A repository path containing
shell metacharacters or whitespace is thus still a quoting-sensitive input. tmux 3.6b documents
that `run-shell` uses `/bin/sh`; 3.5 briefly changed related shell selection and 3.5a restored
`/bin/sh` for `run-shell` and `if-shell`, retaining `default-shell` only for popups. See the
[3.6b `run-shell` manual](https://github.com/tmux/tmux/blob/3.6b/tmux.1#L7414-L7440) and
[3.5/3.5a release entries](https://github.com/tmux/tmux/blob/3.6b/CHANGES).

Raising the minimum does not remove this boundary. A remediation must quote or avoid the loader's
shell command explicitly. The plugin's current multi-operand popup approach should be preserved.

## Command-by-command semantics

### Popup lifecycle, geometry, focus, resize, and input

tmux 3.2 introduced popups, including:

- `-E` to close automatically when the command exits;
- `-EE` to close only on successful exit;
- explicit client, target pane, directory, dimensions, and position;
- a blocking command-queue lifetime while the popup is open.

The plugin uses single `-E`, so the popup closes for success, cancellation, auto-paste status 10,
or an unhandled child failure. That is intentional for UI cleanup, but means child exit status and
result-buffer state must distinguish all outcomes.

Relevant changes after the original baseline are:

| Release | Official change | Plugin relevance |
| --- | --- | --- |
| 3.3 | `display-popup -B` added | Required by current code; establishes actual minimum 3.3. |
| 3.3 | Popup no longer closes on resize; it is adjusted to fit | Reduces abrupt cancellation, but the plugin's captured snapshot and separately queried geometry can still become stale. |
| 3.3 | Panes continue to redraw while a popup is open | Source pane may change behind the immutable snapshot. This makes loss of the handoff buffer followed by recapture semantically more dangerous. |
| 3.3 | Popup environment (`-e`), title/style/border controls added | Available modernization tools, but not necessary merely to pass the existing argv. |
| 3.5 | Extended-key handling substantially changed | The child reads terminal input itself, so modifier/key behavior can vary at this boundary; targeted integration tests are warranted. |
| 3.6 | Focus events are sent when entering and leaving a popup | Better application focus semantics, but may cause the source application to redraw after the snapshot was taken. |
| 3.6 | A popup invoked inside a popup modifies the existing popup | Nested invocation no longer creates an independent overlay. Current buffer names and result protocol are also pane-scoped, so nested/reentrant use remains unsafe. |
| 3.6 | `-k` allows any key to dismiss after command exit | Not useful for this live interactive UI. |

The 3.6b manual still contains the sentence that panes are not updated while a popup is present,
but the official 3.3 release history explicitly says output is no longer frozen and panes continue
to redraw. For this review, the later, specific change entry and implementation history should
govern. This documentation inconsistency should not be turned into a plugin guarantee.

Popup `-x` and `-y` are relative to the target client, while pane geometry comes from pane format
variables. Explicitly supplying `-t <pane-id>` to `display-popup` is the safest way to bind the
format/target context; the current popup command omits it even though it already has the stable
pane ID. This facility exists at 3.2 and is not a 3.6-only opportunity.

The source changes from 3.4 to 3.5 substantially revise extended-key handling and always request
extended-key mode 2 from the parent terminal. The plugin reads bytes with termios/select rather
than using tmux key bindings, so tmux, outer-terminal, and popup-terminal encoding all matter.
No release note supports assuming identical modified-key byte streams across 3.2–3.6b.

### Pane capture

The plugin uses:

```text
capture-pane -p -e -J -t %N
```

Across both endpoints:

- `-p` writes to stdout;
- `-e` includes escape sequences for text and background attributes;
- `-J` joins wrapped lines and preserves trailing spaces;
- no `-S` or `-E` means visible content only;
- explicit `-t %N` is stable for the lifetime of the pane.

This captures tmux's parsed grid, not the application's original byte stream. `-e` re-emits
style-related escapes; it does not promise lossless recovery of arbitrary OSC, DCS, or other
application control sequences. Therefore the pane is not a transparent source of arbitrary
terminal-control bytes, but its emitted SGR sequences and all printable/control characters
returned by capture still need safe handling.

Version changes relevant to exact text fidelity:

- tmux 3.3 adds `capture-pane -T` and makes its old behavior the default except when `-J` is used;
  `-J` therefore carries trimming/joining semantics that must be tested explicitly.
- tmux 3.3 expands appropriate `capture-pane` arguments. Values provided to those arguments may
  undergo format expansion; the plugin supplies only a server-generated pane ID.
- tmux 3.6 adds `-M` for the copy-mode screen, which the plugin does not use. Capturing a pane in
  copy or another mode still means capturing the normal pane grid, not necessarily what the user
  visibly sees in that mode.
- tmux 3.6 preserves tabs in copying and `capture-pane`. This is a real 3.6b-minimum benefit for
  copy fidelity, but changes width/index assumptions if the renderer treats a tab as one Python
  character while the terminal expands it across columns.

The official command descriptions are in the
[3.2 manual](https://github.com/tmux/tmux/blob/3.2/tmux.1#L1937-L1977) and
[3.6b manual](https://github.com/tmux/tmux/blob/3.6b/tmux.1#L2576-L2625).

### Paste buffers and IPC

tmux paste buffers are server-global. Explicitly named buffers are not subject to `buffer-limit`
and remain until deleted. The manuals make no ownership or atomic-claim guarantee for a name.
Thus the plugin's pane-derived handoff/result names and fixed `flash-paste` name are shared mutable
server state, not invocation-local IPC. A higher tmux minimum does not change this.

The exact-data path should prefer `save-buffer -b NAME -` over `show-buffer`:

- `save-buffer ... -` writes the buffer to stdout and has been available throughout the relevant
  range;
- tmux 3.4 explicitly changed `show-buffer` to process escape sequences;
- the parent already uses `save-buffer`, while the child reads its snapshot with `show-buffer`.

Using `show-buffer` for ANSI-preserving captured pane data therefore has version-sensitive display
semantics and is a probable compatibility/correctness hazard. `save-buffer -` is the documented
serialization operation and avoids asking tmux to display buffer content. See the
[3.2 buffer commands](https://github.com/tmux/tmux/blob/3.2/tmux.1#L5769-L5874),
[3.6b buffer commands](https://github.com/tmux/tmux/blob/3.6b/tmux.1#L7243-L7370), and the
[3.4 change entry](https://github.com/tmux/tmux/blob/3.6b/CHANGES).

The plugin passes buffer data as a subprocess argv operand, not a tmux command string, so shell
metacharacters in captured or selected text are data at these call sites. Buffer names are made
from `%N` plus fixed text and are not attacker-controlled command fragments.

`paste-buffer` replaces LF with CR by default and only wraps bracketed-paste markers when `-p` is
used. The plugin's optional auto-paste omits both `-r` and `-p`, so multiline selections become
carriage-return-delimited input and applications that requested bracketed paste do not receive
paste guards. This is stable documented behavior across 3.2–3.6b, not a modernization change.
tmux 3.6 fixes pasting so input is copied without key interpretation, but that does not add
bracketed paste to callers that omit `-p`.

### OSC52 and clipboard targeting

`set-buffer -w` exists in tmux 3.2. It stores the buffer and asks tmux to send it to the clipboard
of a target client using the terminal `Ms` capability. This is not raw OSC52 passthrough from the
pane and does not require `allow-passthrough`.

Successful operation requires:

1. `set-clipboard` to be `on` or `external` (`external` is the default);
2. the outer client terminal to advertise or be configured with the clipboard/`Ms` capability;
3. the terminal itself to permit OSC52.

The official [clipboard guide](https://github.com/tmux/tmux/wiki/Clipboard) notes inconsistent
terminal support and configuration. A zero exit from `set-buffer -w` only means tmux accepted the
operation; it cannot prove the outer terminal changed its clipboard. This supports treating the
plugin's transport "success" as attempted delivery rather than observed clipboard success.

The plugin omits `-t target-client` from `set-buffer -w`. With multiple clients, clipboard delivery
is inherently client-specific, so the client that launched the popup should be captured and
targeted explicitly. The target-client flag already exists in tmux 3.2. Raising the minimum is
not required.

Version-relevant changes:

- tmux 3.2 introduced named `terminal-features`, including `clipboard`, which makes OSC52 setup
  easier than raw terminfo overrides.
- tmux 3.3 introduced `allow-passthrough`, default off; from 3.3 onward raw passthrough needs this
  enabled. It is irrelevant to this plugin's `set-buffer -w` transport.
- tmux 3.3 passes the first OSC52 argument through when applications emit OSC52; again, this is
  separate from `set-buffer -w`.
- tmux 3.5 fixed clipboard escape-sequence terminator sizing.
- tmux 3.6 added device-attribute detection of OSC52 support. A 3.6b baseline should reduce manual
  capability setup on supporting terminals, but terminal policy remains external to tmux.

`set-clipboard=on` also lets applications inside panes create tmux buffers through OSC52, whereas
`external` permits tmux-to-terminal copying but blocks that application-to-tmux mutation. The
official guide recommends understanding this distinction; `external` is the narrower posture and
is sufficient for the plugin.

### Formats, options, and quoting

`display-message -p '#{pane_id}'` and geometry format queries are stable facilities. Format
expansion is intentional at those sites because the strings are fixed by the plugin.

The loader is different: tmux parsing, format expansion in `run-shell`, and `/bin/sh` parsing may
all occur. Passing a Python subprocess argv list prevents a *local Python shell* but does not
retroactively make the installed `run-shell` string safe. tmux's parsing section explicitly notes
that some arguments are parsed twice and that shell invocation adds a separate quoting layer.

tmux 3.4 added `display-message -l` to disable format expansion, but it does not help the plugin's
fixed format queries and is not a general way to quote `run-shell`.

Configuration scope is also stable across the range:

- user `@flash-copy-*` options read with `show-options -g` are global/server configuration by the
  plugin's own design;
- `word-separators` is a session option in these versions, but the plugin batch-reads global
  window/session defaults with `show-window-options -g` rather than the effective option for the
  captured pane's session.

If per-session `word-separators` is expected, reading only the global default is a correctness
hazard. Explicit `-t <pane-id>` option lookup is available without raising the tmux minimum.

## Safe opportunities with a tmux 3.6b minimum

These are genuine benefits available by making 3.6b the supported floor:

1. **Make the documented minimum truthful without removing `-B`.** The existing runtime already
   requires at least 3.3; 3.6b is compatible with every flag currently used.
2. **Depend on popup survival across resize and continued pane redraw.** This is available since
   3.3, but a 3.6b floor makes it universal. The application still needs a deliberate snapshot
   policy and resize behavior.
3. **Depend on focus enter/leave delivery for popups.** This arrives in 3.6 and gives source
   applications consistent focus transitions.
4. **Depend on tab-preserving capture.** This arrives in 3.6 and improves exact-text fidelity,
   provided search/render column logic is made tab-aware.
5. **Benefit from tmux's OSC52 capability detection.** 3.6 can detect OSC52 via terminal device
   attributes, reducing configuration friction where terminals respond accurately.
6. **Use the now-documented popup argv contract.** Multi-operand execution existed earlier, but
   3.6's manual explicitly exposes `shell-command [argument ...]`, making the plugin's no-shell
   child invocation a supported public contract rather than a source-derived one.
7. **Rely on accumulated popup, key, Unicode, capture, and paste fixes.** The changes through 3.6b
   include resize, extended-key, Unicode/invalid UTF-8, clipboard terminator, tab, and literal-paste
   corrections relevant to this UI.

Capabilities that are useful but **not** reasons to require 3.6b include explicit `-t` targeting,
`set-buffer -w -t`, `save-buffer -`, named buffers, `wait-for`, popup `-E`, and format quoting
tools; the necessary forms already existed at or before 3.2.

## Version matrix

| Behavior | 3.2 | 3.3 | 3.4 | 3.5 | 3.6/3.6b |
| --- | --- | --- | --- | --- | --- |
| Popup base feature and `-E` | Yes | Yes | Yes | Yes | Yes |
| Borderless popup `-B` | **No** | Yes | Yes | Yes | Yes |
| Popup argv vector in source | Yes, undocumented | Yes, undocumented | Yes, undocumented | Yes, undocumented | Yes, documented |
| Popup survives resize | No guarantee; closed in old behavior | Yes | Yes | Yes | Yes |
| Pane continues redraw behind popup | No | Yes | Yes | Yes | Yes |
| Popup focus enter/leave events | No | No | No | No | Yes |
| `capture-pane` preserves tabs | No | No | No | No | Yes |
| `capture-pane -M` mode screen | No | No | No | No | Yes |
| `show-buffer` processes escapes | Old behavior | Old behavior | Yes | Yes | Yes |
| `set-buffer -w` OSC52 path | Yes | Yes | Yes | Yes | Yes |
| `allow-passthrough` | No | Yes | Yes (`all` added) | Yes | Yes |
| OSC52 capability auto-detection via DA | No | No | No | No | Yes |
| Substantial extended-key mode-2 revision | No | No | No | Yes | Yes |

## Findings to carry into synthesis

| Candidate | Classification | Confidence | Version relevance |
| --- | --- | --- | --- |
| `display-popup -B` makes the claimed tmux 3.2 minimum false | Confirmed defect | High | Fails 3.2/3.2a; works 3.3+ |
| Source pane and target client are initially/partly implicit | Compatibility hazard | High | All reviewed versions; explicit targeting already available |
| Pane-derived and fixed buffer names permit same-pane/reentrant collisions | Probable correctness hazard | High | All reviewed versions |
| Child uses display-oriented `show-buffer` for exact snapshot transport | Probable version-sensitive correctness hazard | Medium-high | Semantics changed in 3.4 |
| Loader path crosses unquoted tmux + shell parsing | Security-adjacent compatibility hazard | High | All reviewed versions |
| Auto-paste omits bracketed-paste guards and transforms LF to CR | Documented behavioral risk | High | All reviewed versions; literal-paste fix in 3.6 does not change omitted `-p` |
| Effective `word-separators` may differ from global default read by plugin | Probable configuration-scope defect | Medium-high | All reviewed versions |
| 3.6 tab-preserving capture can invalidate character-index/column assumptions | Modernization regression risk | High | New when adopting 3.6 baseline |
| OSC52 command success does not prove clipboard observation | Environment risk | High | All reviewed versions |

## Regression evidence needed

- Run the actual popup command against tmux 3.2/3.2a and assert rejection of `-B`; run against
  3.3 and 3.6b and assert launch.
- Exercise invocation from two attached clients and rapid focus changes; verify capture, popup,
  clipboard target, and optional paste all remain bound to the launching client/pane.
- Compare `show-buffer` and `save-buffer -` round trips on 3.2, 3.4, and 3.6b with SGR, ESC,
  newlines, tabs, invalid UTF-8, and leading/trailing whitespace.
- Resize the client/source pane while the popup is active on 3.6b and verify snapshot/label
  alignment and cleanup.
- Test tabs on tmux 3.6b at multiple tab stops and after `-J` joins.
- Trigger two same-pane invocations and a nested popup invocation; check buffer ownership,
  selection isolation, and cleanup.
- Test auto-paste with multiline text into applications with and without bracketed paste mode.
- Test OSC52 selection with two clients attached to terminals having different clipboard
  capabilities.

