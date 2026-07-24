# Runtime Contract Evidence

## Scope and baseline

This note establishes the runtime topology and invariants that later review tickets must test. It
does not decide whether a suspicious implementation detail is a defect.

Observed local baseline:

- macOS with tmux 3.7b installed.
- `TMUX` was not present in the reviewing shell, so no live in-session popup invocation was
  performed for this ticket.
- `uv run pytest -q` completed on Python 3.14.6: 283 tests passed.
- Reported coverage was 97% across `src` (856 statements, 28 missed). That measurement omits the
  shell loader and both executable scripts as coverage targets.

User-facing support claims:

- tmux 3.2 or newer.
- Python 3.10 or newer.
- Search and copy of visible pane content, optional range selection, OSC52-first clipboard
  delivery, and optional paste back into the originating pane.

## Runtime topology

### 1. Plugin loading and invocation

`tmux-flash-copy.tmux` is sourced by TPM or `run-shell`. It:

1. Resolves its own directory through `BASH_SOURCE`.
2. reads global `@flash-copy-bind-key`, defaulting to `F`;
3. installs a tmux key binding whose action is `run-shell <absolute plugin path>/bin/tmux-flash-copy.py`.

Contract:

- Bash, `tmux`, and an executable Python entrypoint must be available in the tmux server's
  execution environment.
- The plugin path must remain valid after the binding is installed.
- The key binding must invoke the process in a tmux command context that resolves the intended
  source pane.

### 2. Parent Python process

`bin/tmux-flash-copy.py` is the orchestration process. It:

1. obtains a pane id with `tmux display-message -p "#{pane_id}"`;
2. captures that pane with `capture-pane -p -e -J -t <pane>`;
3. loads global and window tmux configuration;
4. optionally performs extensive debug-only tmux queries;
5. constructs search, clipboard, and popup helpers;
6. synchronously launches the popup;
7. receives selected text plus an auto-paste flag;
8. copies through the OSC52-first clipboard chain and optionally pastes to the captured pane.

Contract:

- The pane id selected at startup is the stable identity for capture, popup placement, result
  ownership, and optional paste.
- The captured snapshot, not later pane output, is the selection source.
- Configuration is a per-invocation snapshot and must survive losslessly when forwarded to the
  child.
- Parent failure before popup launch is visible on stderr with exit status 1. Popup-layer errors
  are generally converted to cancellation.

### 3. Parent-to-child handoff and popup

`PopupUI`:

1. queries the source pane's geometry;
2. writes captured content to a named tmux buffer;
3. invokes `tmux display-popup -E -B` synchronously, sized and positioned over the source pane;
4. passes configuration as child command-line arguments;
5. waits up to 35 seconds;
6. derives auto-paste from child exit status 10;
7. reads selected text from a second named tmux buffer;
8. deletes IPC buffers on the main success path and selected failure paths.

The IPC names are derived only from the pane id:

- `__tmux_flash_copy_pane_content_<pane-id>__`
- `__tmux_flash_copy_result_<pane-id>__`

Contract:

- Only one invocation may own a given pair of pane-derived buffer names at a time unless the
  implementation provides additional isolation.
- Buffer contents must preserve exact captured/selected text, including newlines and non-ASCII
  characters.
- Popup exit status and result-buffer existence jointly form the result protocol:
  status 10 means paste requested; status 0 means copy/cancel; a non-empty result buffer means a
  selection exists.
- Cleanup must not delete another invocation's state.
- The parent's 35-second timeout must exceed every legitimate child lifetime or cancellation is
  expected.

### 4. Interactive child process

`bin/tmux-flash-copy-interactive.py`:

1. parses the forwarded configuration;
2. reads the pane snapshot buffer, falling back to a fresh capture when unavailable;
3. separately queries pane dimensions;
4. strips recognized ANSI SGR sequences to form the search/copy representation;
5. indexes non-whitespace sequences once;
6. redraws the snapshot and protected prompt after each search edit;
7. manages idle timeout, modifiers, word/range selection, and cancellation;
8. writes selected text to the result buffer and exits 0 (copy) or 10 (copy-and-paste).

Contract:

- The colored snapshot and plain snapshot must have identical line structure and logical visible
  character positions after supported ANSI sequences are removed.
- Search matches, displayed labels, selected words, and range offsets must refer to the same
  immutable snapshot.
- Search considers complete non-whitespace sequences. Configured word separators affect copied
  word boundaries, not which sequences can match.
- A label visually replaces an existing character or following space; rendering must not change
  line width or wrapping.
- A label is unique among current matches and cannot be mistaken for continuation of the query.
- Reverse search changes match/label priority, not the text that a given match copies.
- The first range endpoint remains tied to its original plain-text offsets while the second query
  is performed.
- Every user input resets the idle timer. Cancellation produces no clipboard action.
- Terminal scrolling regions and screen state must be restored on every normal Python exit path.

### 5. Clipboard and optional paste

After the popup closes, the parent attempts:

1. `tmux set-buffer -w -- <text>` for OSC52;
2. a platform clipboard command when OSC52 reports failure;
3. a plain tmux buffer as last resort.

If auto-paste was requested and copy reported success, it writes a fixed buffer named
`flash-paste` and invokes `paste-buffer` against the original pane id.

Contract:

- Clipboard success is defined as the selected transport command returning zero; it does not
  prove that a system clipboard observed the text.
- Clipboard data must be passed as data rather than evaluated as shell/tmux command syntax.
- Auto-paste must target the pane captured at invocation, regardless of later focus changes.
- A paste failure must not negate a successful copy, though diagnostics should describe reality.
- Shared clipboard/paste buffers must not allow concurrent invocations to exchange or delete each
  other's data.

## State and ownership model

The runtime uses four distinct state scopes:

| State | Owner/lifetime | Representation |
| --- | --- | --- |
| Binding configuration | tmux server, until rebound | tmux option and key table |
| Invocation configuration | parent then child, one invocation | dataclass forwarded as argv |
| Pane snapshot and selection | parent/child invocation | strings plus tmux IPC buffers |
| Clipboard/paste result | tmux server/terminal/source pane | tmux buffer and OSC52 side effect |

The pane id is currently both the target identifier and the namespace for invocation IPC. It is
not a unique invocation id.

## Trust boundaries

Later tickets should treat these inputs as untrusted or externally mutable:

- pane text, including terminal control sequences and Unicode;
- tmux user options, including colors, labels, prompt strings, separators, timeouts, and bind key;
- pane/window geometry and focus, which can change during invocation;
- tmux buffer namespace, shared by clients attached to the same server;
- executable paths and environment inherited by the tmux server;
- terminal OSC52 policy and nested/remote tmux behavior.

Arguments are generally passed to Python `subprocess.run` as lists, which avoids a local shell at
those call sites. That alone does not settle tmux command parsing, format expansion, terminal
escape interpretation, or the shell command installed by the loader.

## Evidence boundaries and reconciliation inputs

The documentation and implementation agree on the broad feature flow, the current tmux/Python
minimum claims, dynamic search, separator semantics, range behavior, timeout intent, and
OSC52-first clipboard order.

The following are not resolved here and must be carried into later tickets:

- The loader and parent resolve target context implicitly at invocation, while all later
  operations assume the returned pane id is the intended source pane.
- IPC names are pane-specific rather than invocation-specific; the code comment says this avoids
  concurrent conflicts, but it only separates different panes.
- The child may fall back to recapturing a pane, which changes the immutable-snapshot premise if
  the handoff buffer is missing.
- Popup timeout is fixed at 35 seconds while the user-configurable child idle timeout has no
  corresponding upper bound in the parent.
- Popup errors are commonly returned as ordinary cancellation, and the interactive script's
  top-level exception handler prints an error but does not explicitly return a failure status.
- ANSI handling recognizes SGR (`CSI ... m`) sequences only, whereas captured pane text and
  configurable rendering inputs may contain a broader terminal/control vocabulary.
- Pane dimensions are queried at multiple times; the snapshot, geometry, popup terminal size,
  and live pane can diverge after resize.
- The fixed `flash-paste` buffer and pane-derived IPC buffers have tmux-server-wide visibility.
- The high unit-test coverage is principally mock-based around tmux subprocess behavior. The
  coverage configuration excludes both executable entrypoints, and no automated real-tmux
  end-to-end harness was found.
- The parent constructs a `SearchInterface` from ANSI-preserving content, but the actual child
  reconstructs its own interface from stripped content; the parent instance mainly transports
  configuration into `PopupUI`.
- Configuration is read globally for custom options and from global window options for
  `word-separators`; whether this matches the active pane/window contract requires targeted
  option-scope review.

These are candidate hazards or evidence gaps, not findings. “Audit Runtime Lifecycle, State, and
Failure Handling,” “Audit Search, Selection, Rendering, and Terminal Safety,” “Audit
Installation, Configuration, Clipboard, and Environment Risks,” and “Assess Regression Coverage
and Evidence Gaps” own their resolution.
