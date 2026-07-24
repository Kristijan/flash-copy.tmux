# Evaluate tmux and Python Baseline Modernization

Type: research
Status: resolved
Blocked by: 02, 05

## Question

Which concrete correctness, robustness, simplification, or performance improvements become
available if the minimum tmux version moves from 3.2 to 3.6b, and what compatibility cost does
each carry?

Separately, do Python 3.11 or 3.12 offer any credible, material benefit on the measured runtime
path that could justify reconsidering Python 3.10? Exclude style-only syntax upgrades,
unsupported assumptions about tmux after 3.6b, and negligible interpreter microbenchmarks.

## Answer

The primary-source comparison is recorded in
[tmux and Python Baseline Modernization](../evidence/07-version-modernization.md).

Recommendation: raise and enforce the tmux minimum at 3.6b. This corrects an already-false 3.2
claim, establishes a robust popup/capture/OSC52 floor, and makes multi-operand popup argv behavior
a documented public contract. The cost is excluding otherwise-working tmux 3.3–3.6a
installations. Most targeting, IPC, lifecycle, and performance defects still require plugin work
and should not be attributed to the baseline change.

Keep Python 3.10. Official Python 3.11 improvements provide credible directional startup and
pure-Python benefits, but no measured material end-to-end case justifies dropping 3.10. Python
3.12 adds no workload-specific advantage that changes the decision. Algorithmic fixes and fewer
runtime boundaries dominate interpreter-version gains.
