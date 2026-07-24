# Synthesize the Canonical Prioritized Review

Type: task
Status: resolved
Blocked by: 03, 04, 05, 06, 07, 08

## Question

What is the final prioritized, evidence-backed assessment of tmux-flash-copy's correctness,
security-adjacent runtime risks, performance, tmux 3.6b modernization opportunities, and
material Python 3.11/3.12 opportunities?

Produce the single canonical Markdown report described by the map. Deduplicate cross-cutting
findings, preserve confidence and evidence distinctions, include remediation direction and
regression-test needs, and propose an implementation sequence without making code changes.

## Answer

The canonical result is [tmux-flash-copy Runtime Review](../report.md).

It synthesizes 24 prioritized findings, led by stale-result acceptance, the false tmux 3.2
minimum, hidden selectable rows, timeout-policy conflict, shared IPC, implicit targets, and a
measured multi-second high-match scaling cliff. Confirmed defects are separated from probable
real-tmux/environment risks and low-priority hardening.

The report recommends raising and enforcing tmux 3.6b while explicitly documenting the loss of
otherwise-working 3.3–3.6a installations. It recommends retaining Python 3.10. It includes a
four-layer test strategy and six-phase implementation sequence, but no production fixes.
