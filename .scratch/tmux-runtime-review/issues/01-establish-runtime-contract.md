# Establish the Actual Runtime Contract

Type: task
Status: resolved
Blocked by: None

## Question

What is the plugin's actual end-to-end runtime topology—from TPM loading and key invocation
through pane capture, popup interaction, selection, clipboard delivery, and cleanup—and which
state, timing, compatibility, and trust-boundary invariants must hold for that path to work?

Record discrepancies between code, tests, configuration documentation, and user-facing support
claims as inputs to later investigations. Produce a linked local evidence note rather than
changing production files.

## Answer

The runtime contract is documented in
[Runtime Contract Evidence](../evidence/01-runtime-contract.md). The plugin is a two-process
Python system hosted by tmux: a parent captures and configures an immutable pane snapshot, a
popup child searches and renders it, and tmux buffers plus child exit status form the IPC
protocol. The original pane id anchors capture, placement, result ownership, and optional paste,
but also namespaces shared IPC state.

The contract identifies four state scopes, the complete success/cancellation path, content and
label invariants, timeout and cleanup obligations, and trust boundaries. It also records
unresolved reconciliation inputs for later tickets, notably pane-scoped concurrent IPC,
configurable timeout mismatch, snapshot fallback recapture, partial ANSI handling, geometry
drift, implicit target resolution, and the absence of a real-tmux end-to-end automated harness.

Baseline evidence: all 283 tests pass on Python 3.14.6 with 97% reported `src` coverage. Coverage
does not include the shell loader or either executable entrypoint, and tmux subprocess behavior
is predominantly mocked. No candidate hazard was promoted to a confirmed finding in this
contract-setting ticket.
