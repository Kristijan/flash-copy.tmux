# Thorough tmux Runtime Review

Label: wayfinder:map

## Destination

Produce a canonical, evidence-backed review of tmux-flash-copy's entire runtime path,
prioritising latent bugs, security-adjacent correctness risks, and user-visible performance.
The review will also identify improvements available through a tmux 3.6b minimum and material
Python 3.11/3.12 opportunities, without implementing fixes.

## Notes

- Work is discovery-only. Do not modify production code or implement fixes.
- Keep the map, tickets, evidence notes, benchmarks, and final report under this directory.
- Review the shell loader, Python entry points and modules, tmux subprocess interactions,
  configuration, packaging, tests, documentation claims, and complete user runtime path.
- Treat tmux 3.2 as the existing baseline and tmux 3.6b as the modernization ceiling. Do not
  recommend or rely on behavior introduced after 3.6b. The locally installed tmux 3.7b may
  provide supporting evidence only when the tested behavior also exists in 3.6b.
- Keep Python 3.10 as the expected baseline. Discuss 3.11 or 3.12 only where a credible,
  material runtime benefit exists.
- OSC52 remains in the normal review scope. Analyze platform clipboard fallbacks statically and
  report environment-specific risks; do not require live cross-platform validation.
- Treat unusually large pane captures and high match counts as supported scenarios.
- Include focused security-adjacent correctness analysis for shell quoting, tmux format
  expansion, command injection surfaces, temporary/shared state, terminal escape handling, and
  untrusted pane content. This is not a broad security audit.
- Classify findings as confirmed defects, probable defects/compatibility hazards, measured or
  clearly supported performance opportunities, or speculative hardening. Keep speculative
  hardening in a low-priority appendix.
- Each substantive finding must state evidence, affected runtime path, severity, confidence,
  relevant tmux/Python versions, remediation direction, and regression-test needs.
- Use official tmux and Python primary sources for version-specific claims.
- The final artifact is one Markdown report, supported by smaller local evidence notes.

## Decisions so far

- [Establish the Actual Runtime Contract](issues/01-establish-runtime-contract.md) — Defined the
  two-process tmux-hosted lifecycle, state ownership, IPC, snapshot, selection, clipboard, and
  trust-boundary invariants that later audits must test.
- [Audit Search, Selection, Rendering, and Terminal Safety](issues/04-audit-search-render-and-terminal-safety.md)
  — Confirmed hidden selectable rows, label collisions, separator-regex errors, Unicode offset
  corruption, and terminal-cell-width violations, plus a configuration hardening gap.
- [Research tmux 3.2–3.6b Runtime Semantics](issues/02-research-tmux-3.2-to-3.6b.md) — Established
  that `display-popup -B` makes the advertised 3.2 minimum false and identified targeting, IPC,
  quoting, option-scope, capture, OSC52, and safe 3.6b modernization implications.
- [Profile User-Visible Runtime Performance](issues/05-profile-runtime-performance.md) — Measured
  a multi-second high-match scaling cliff driven by rows × matches lookup, excess occurrence
  materialization, duplicate indexing, and repeated overlay scans; ordinary panes remain fast.
- [Audit Runtime Lifecycle, State, and Failure Handling](issues/03-audit-lifecycle-and-state.md) —
  Confirmed critical stale-selection acceptance plus timeout conflict, cleanup/error masking, and
  false paste-success diagnostics; mapped concurrency, targeting, geometry, and resize hazards.
- [Audit Installation, Configuration, Clipboard, and Environment Risks](issues/06-audit-integration-and-environment-risks.md)
  — Reconciled support claims and found option-scope/validation/label defects, loader and Python
  path hazards, OSC52/auto-paste risks, fallback limits, and missing real-tmux CI evidence.
- [Assess Regression Coverage and Evidence Gaps](issues/08-assess-test-evidence.md) — Confirmed
  the fast Python suite is healthy but cannot validate loader/entrypoint/tmux/terminal contracts;
  mapped every finding to minimum evidence and a four-layer regression strategy.
- [Evaluate tmux and Python Baseline Modernization](issues/07-evaluate-version-modernization.md) —
  Recommends enforcing tmux 3.6b with an explicit 3.3–3.6a compatibility cost, while retaining
  Python 3.10 because 3.11/3.12 gains are not material enough to justify exclusion.
- [Synthesize the Canonical Prioritized Review](issues/09-synthesize-prioritized-review.md) —
  Consolidated 24 findings, modernization decisions, regression evidence, and implementation
  sequencing into the canonical discovery report without implementing fixes.

## Not yet specified

None. The discovery route is complete; focused reproduction and implementation work are
specified in the canonical report's regression strategy and proposed implementation sequence.

## Out of scope

- Implementing, refactoring, or formatting production code.
- Publishing discovery work to GitHub Issues.
- A general readability or style review unless readability directly creates correctness risk.
- Live validation of non-macOS clipboard fallback tools or a cross-platform test matrix.
- Recommendations that require tmux behavior introduced after 3.6b.
- Raising Python beyond 3.12 as a practical baseline recommendation.
- A broad security audit unrelated to the plugin's runtime and trust boundaries.
