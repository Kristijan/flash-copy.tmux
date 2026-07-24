# Research tmux 3.2–3.6b Runtime Semantics

Type: research
Status: resolved
Blocked by: None

## Question

Across official tmux documentation, source/release history, and command semantics from 3.2
through 3.6b, which behaviors affect this plugin's popup lifecycle, target resolution, pane
capture, buffers, OSC52, formats, quoting, input, and process execution?

Identify compatibility traps at the current 3.2 baseline and capabilities that become safely
available with a 3.6b minimum. Keep any observation derived from local tmux 3.7b clearly
separated from evidence applicable to 3.6b. Produce a linked local research note.

## Answer

The official-source research is recorded in
[tmux 3.2–3.6b Runtime Semantics](../evidence/02-tmux-3.2-to-3.6b.md).

The most important confirmed result is that the implementation is not compatible with its
advertised tmux 3.2 minimum: it unconditionally invokes `display-popup -B`, and `-B` was added in
tmux 3.3. The research also establishes that multi-operand popup execution was argv-based in
source from 3.2 and became formally documented in 3.6, while loader quoting remains a separate
tmux-plus-shell boundary.

Other high-confidence inputs include implicit pane/client targeting, server-global IPC buffer
ownership, version-sensitive `show-buffer` semantics from 3.4, auto-paste newline/bracketed-paste
behavior, global-versus-effective `word-separators` scope, and 3.6b opportunities for
tab-preserving capture, popup focus events, OSC52 capability detection, and accumulated
popup/input/capture fixes. All claims use official tmux manuals, source, release history, or the
official clipboard guide, with no reliance on post-3.6b behavior.
