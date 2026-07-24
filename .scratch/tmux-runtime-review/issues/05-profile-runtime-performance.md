# Profile User-Visible Runtime Performance

Type: task
Status: resolved
Blocked by: 01

## Question

Where are the material latency, CPU, memory, output-volume, and subprocess costs along startup,
pane capture, configuration loading, incremental search, label assignment, rendering, range
selection, and clipboard handoff?

Measure representative small, large, and pathological pane contents and high match counts.
Distinguish user-visible bottlenecks and scaling risks from inconsequential micro-optimizations,
and produce reproducible local benchmark evidence.

## Answer

The measurements and analysis are recorded in
[Runtime Performance Audit](../evidence/05-runtime-performance.md), with a reproducible
[benchmark harness](../benchmarks/search_render_profile.py).

Ordinary panes are fast, but supported high-match workloads show a severe scaling cliff. A
500,999-character/250,000-match case took 1.20 seconds to build, 0.83 seconds per search, and
5.41 seconds per redraw while peaking at 61.5 MiB during index construction. A rows × matches
lookup accounts for 2.92 seconds of that redraw.

The audit confirms excess occurrence materialization, per-row full-list scans, an unused parent
search index that the child rebuilds, and repeated ANSI-line rescanning as material costs. It
also records the roughly 14–15 synchronous tmux CLI boundaries on a normal success path and
per-poll terminal-mode churn as measurement targets. Ordinary-path micro-optimizations are
explicitly deprioritized.
