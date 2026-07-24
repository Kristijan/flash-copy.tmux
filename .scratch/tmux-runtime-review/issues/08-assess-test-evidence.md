# Assess Regression Coverage and Evidence Gaps

Type: task
Status: resolved
Blocked by: 03, 04, 05, 06

## Question

How effectively do the existing automated tests and practical integration checks protect the
actual runtime contract and the candidate findings uncovered by the review?

Identify false confidence from mocks, missing boundary/integration cases, version-sensitive
blind spots, benchmark gaps, and the minimum regression evidence each substantive finding would
need. Do not add or modify tests.

## Answer

The assessment is recorded in
[Regression Coverage and Evidence Gaps](../evidence/08-test-evidence-gaps.md).

All 283 tests and all static quality checks pass. The suite is strong for isolated Python logic,
but 97% coverage applies only to `src`; the shell loader and roughly 1,121 lines of executable
scripts are outside the configured coverage target, and tmux behavior is predominantly mocked.
There is no real-tmux, minimum-version, multi-client, terminal-cell, concurrency, or performance
regression layer.

The note maps every substantive review finding to minimum regression evidence and proposes four
layers: pure contract/property tests, executable protocol tests with a fake tmux CLI, a small
real-tmux compatibility matrix, and limited environment smoke checks. No tests were added or
modified.
