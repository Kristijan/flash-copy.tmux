# Audit Runtime Lifecycle, State, and Failure Handling

Type: task
Status: resolved
Blocked by: 01, 02

## Question

Where can invocation targeting, popup/window lifecycle, inter-process communication, shared tmux
buffers, concurrent invocations, cancellation, timeouts, partial failures, or cleanup violate the
runtime contract?

Determine which candidates are confirmed defects versus probable hazards, using focused
reproduction where practical, and capture evidence plus required regression tests without
implementing fixes.

## Answer

The results are recorded in
[Runtime Lifecycle, State, and Failure Audit](../evidence/03-lifecycle-state-failures.md).

The highest-severity confirmed defect is stale-result acceptance: the parent neither clears the
result buffer before launch nor rejects data after popup failure. A focused probe showed a failed
popup returning a prior `STALE-SELECTION`, which the outer process would copy. The audit also
confirms the fixed 35-second parent timeout conflicts with configurable child lifetime, failure
paths leak buffers and mask errors, and auto-paste reports success after failed commands.

High-confidence hazards include server-global pane-derived/fixed buffer collisions, implicit
pane/client targeting, resize/fallback-recapture snapshot drift, and likely incorrect y
positioning for non-top panes. Findings include remediation direction and precise regression
evidence; no fixes were implemented.
