# Runtime Performance Audit

## Method and limits

The benchmark harness is
[search_render_profile.py](../benchmarks/search_render_profile.py). It uses the production search
and rendering code without modifying it, records median wall time, and uses `tracemalloc` for
search-index construction peak memory. Runs were performed on the available macOS host with
Python 3.14.6.

These measurements compare workload scaling on one machine; they are not cross-version Python
claims. tmux subprocess latency was analyzed structurally because the reviewing shell was not
inside tmux and a real popup round trip was unavailable.

## Measurements

| Scenario | Shape | Characters | Matches | Build ms | Search ms | Render ms | Match lookup sweep ms | Build peak MiB |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| ordinary | 24x120 | 2,903 | 96 | 2.15 | 0.34 | 0.51 | 0.02 | 0.14 |
| large | 200x240 | 48,199 | 1,600 | 37.11 | 4.99 | 7.71 | 3.02 | 2.19 |
| very large | 1000x500 | 500,999 | 17,000 | 387.06 | 58.35 | 341.32 | 166.12 | 23.88 |
| dense matches | 200x240 | 48,199 | 24,000 | 99.57 | 70.01 | 97.83 | 47.83 | 5.54 |
| dense very large | 1000x500 | 500,999 | 250,000 | 1,198.85 | 832.58 | 5,411.62 | 2,924.49 | 61.50 |

The ordinary visible-pane case is fast. The supported large/high-match scenarios have a clear
responsiveness cliff: one redraw can exceed five seconds, and construction plus the first search
adds roughly another two seconds before process/IPC/terminal output costs.

## Findings

### PF-1 — Per-row match lookup creates an rows × matches redraw cost

- Classification: confirmed performance defect
- Severity: high for large/high-match panes
- Confidence: high
- Versions: all supported Python and tmux versions

`get_matches_at_line()` scans the entire current match list. The renderer calls it for every
displayed row, then calls it again inside the line-overlay function for rows that contain
matches. This makes match grouping roughly O(rows × matches) per redraw.

In the dense 1000×500 case, a lookup-only sweep consumed 2.92 seconds of the 5.41-second render.
No ANSI output construction or terminal I/O is included in that lookup figure.

Remediation direction: group matches by line once per search update and make row lookup direct.
Regression/performance evidence: benchmark redraw scaling while independently increasing rows
and matches; assert that lookup time grows approximately with rows + matches.

### PF-2 — The search materializes far more matches than the UI can expose

- Classification: confirmed performance defect
- Severity: high for high-match panes
- Confidence: high
- Versions: all supported Python and tmux versions

Search creates a new object for every overlapping occurrence, deduplicates and sorts the full
list, and runs label assignment across it. The UI has a finite label alphabet (52 by default);
unlabelled matches are not highlighted by the overlay loop and cannot be selected by label.
Only the first match has an additional Enter-selection role.

The dense 1000×500 case materialized 250,000 matches:

- index build: 1.20 seconds and 61.5 MiB peak traced allocation;
- each search: 0.83 seconds;
- each redraw: 5.41 seconds.

This work repeats after every input edit.

Remediation direction: define the exact product behavior for matches beyond label capacity, then
avoid allocating/sorting/render-indexing occurrences the UI cannot expose. If all occurrences
must affect dimming, represent that separately from selectable labeled matches.
Regression/performance evidence: high-frequency tokens, overlapping occurrences, custom small
label alphabets, and stable first-match ordering in both search directions.

### PF-3 — The parent builds and retains a search index that the child rebuilds

- Classification: confirmed performance opportunity
- Severity: medium for large panes
- Confidence: high
- Versions: all supported Python and tmux versions

The parent constructs `SearchInterface` over ANSI-preserving captured content. `PopupUI` only
uses that object to forward `reverse_search` and `word_separators`; it performs no parent-side
search. The child then strips ANSI and constructs the real search index again.

At the benchmark's 500,999-character scale, one construction costs 0.39–1.20 seconds and
23.9–61.5 MiB peak depending on token density. During the popup, the parent retains its pane
content and index while the child owns another snapshot and index, multiplying live memory.

Remediation direction: pass configuration directly to popup orchestration and build exactly one
search index in the process that searches. Regression evidence should show identical child argv
and behavior with no parent index.

### PF-4 — Overlay construction repeatedly rescans and rebuilds decorated lines

- Classification: confirmed scaling opportunity
- Severity: medium
- Confidence: high
- Versions: all supported Python and tmux versions

For every labeled match, rendering maps plain positions to ANSI positions by scanning the line
and then reconstructs strings with new style sequences. The cache is invalidated after each
mutation. Multiple occurrences in one long row therefore cause repeated scans and allocations;
the full pane is rebuilt and written after every accepted query edit.

The benchmark isolates the larger PF-1 component, but the remaining ~2.5 seconds in the dense
very-large render is still Python overlay/output-string work with stderr redirected to memory.

Remediation direction: plan overlays in immutable plain/cell coordinates, emit each row in one
left-to-right pass, and write the completed frame in coarse chunks. Reuse row data unaffected by
the query where practical. This redesign must also solve the correctness findings around
colliding labels and terminal-cell width.

Regression/performance evidence: many labeled occurrences on one long row, ANSI-heavy rows,
Unicode cell widths, and output equivalence for ordinary ASCII cases.

### PF-5 — Normal invocation crosses many synchronous tmux process boundaries

- Classification: probable performance opportunity
- Severity: low to medium
- Confidence: high for count, unmeasured for local latency
- Versions: all supported tmux versions

A successful ordinary copy typically performs approximately:

1. pane-id query;
2. pane capture;
3. two batched option queries (and sometimes a separate separator query);
4. pane geometry query;
5. snapshot-buffer write;
6. popup process;
7. child snapshot-buffer read;
8. child pane-dimensions query;
9. child result-buffer write;
10. parent result-buffer read;
11. two buffer deletions;
12. OSC52 buffer write.

That is roughly 14–15 synchronous tmux CLI invocations, excluding native fallback, auto-paste,
or debug-only environment queries. Configuration batching is already a useful optimization.

Remediation direction: first remove redundant queries/state identified by lifecycle review;
consider obtaining stable pane/client identity through invocation arguments and avoid the child's
dimension query if it is not used. Do not trade exact IPC semantics for fewer commands without
integration evidence.

Regression/performance evidence: real-tmux launch-to-first-frame and selection-to-return timing,
with subprocess count, normal/debug, copy/paste, and buffer-fallback variants.

### PF-6 — Raw terminal mode is entered and restored on every 100 ms poll

- Classification: probable performance/responsiveness opportunity
- Severity: low
- Confidence: high from control flow
- Versions: all supported Python/tmux versions

When stdin is a TTY, every idle loop calls `tcgetattr`, enters raw mode, waits up to 100 ms, and
restores terminal settings. With no input this repeats around ten times per second. It adds
system-call churn and creates repeated terminal-mode transition windows.

Remediation direction: own raw mode for the interactive session with one exception-safe
enter/restore boundary, while retaining periodic timeout checks. Use a monotonic clock as part of
the lifecycle correction.

Regression/performance evidence: idle CPU/syscall sampling, input latency, cancellation, signals,
and guaranteed restoration after exceptions.

## Non-findings and prioritization

- Ordinary pane search/render latency is already sub-millisecond to low-millisecond in this
  harness; micro-optimizing simple ASCII cases is not warranted.
- Regex compilation and small Python syntax-level changes are immaterial beside match
  materialization, row scans, duplicate indexing, and process boundaries.
- Debug mode intentionally runs several additional tmux queries and logs match samples. Optimize
  it only if it interferes with diagnosis, not at the expense of useful evidence.
- Clipboard transport itself is one subprocess on the successful OSC52 path. Fallback latency is
  environment-specific and outside the live-validation requirement.

## Recommended performance order

1. Establish selectable-match capacity/behavior and eliminate PF-2 excess materialization.
2. Index matches by row to eliminate PF-1.
3. Remove the unused parent search index (PF-3).
4. Redesign overlay emission together with terminal-cell correctness (PF-4).
5. Measure a real tmux session before deciding whether subprocess consolidation (PF-5) is worth
   complexity.
6. Move raw-mode ownership to the session boundary (PF-6).
