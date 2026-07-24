# tmux-flash-copy Runtime Review

## Implementation status

This report is the local source of truth for implementation progress. Finding IDs remain stable;
completed work links to stable `jj` change IDs rather than mutable commit IDs. Update this table
whenever a finding changes state, and keep implementation changes isolated by finding where
practical.

Status vocabulary:

- **Implemented** — the accepted scope is complete and verified.
- **Accepted decision** — intentionally resolved without code, with the decision documented.
- **Partially implemented** — useful work landed, but material scope remains.
- **Won't fix** — deliberately left unchanged after implementation evidence or owner testing.
- **Not started** — no implementation work has been attributed to the finding.

Current overview:

| State                 | Count | Findings                                 |
| --------------------- | ----: | ---------------------------------------- |
| Implemented           |     7 | F-01, F-04, F-05, F-13–F-16               |
| Accepted decision     |     1 | F-02                                     |
| Partially implemented |     1 | F-06                                     |
| Won't fix             |     2 | F-03, F-19                               |
| Not started           |    13 | F-07–F-12, F-17, F-18, F-20–F-24           |

There are **13 findings with open implementation scope**, all not started.

| Finding | Implementation state  | `jj` change                                                                                 | Remaining scope                                                                     |
| ------- | --------------------- | ------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------- |
| F-01    | **Implemented**       | `tnrprnyowltzrtpnlmsnnpyqtuvszuol` — `fix: reject stale popup results`                      | None in the accepted P0 scope                                                       |
| F-02    | **Accepted decision** | `lrntorqpxsllpqvqkpoztuxrrytvoqyy` — `docs: require tmux 3.6b`                              | No runtime version guard or 3.6b CI gate is planned; the minimum is documented only |
| F-03    | **Won't fix**         | `vtnprqyurkmxrznwpyvwuxrlpukonqvq` and `utrwnrrkzynprtqwnsrkyvkxpnoktymy` abandoned after owner testing | Preserve established soft-wrapped label rendering |
| F-04    | **Implemented**       | `muztupsovnqpuvpwwuukzllnsvsxoqyv` — `fix: let interactive idle timeout own popup lifetime` | None in the accepted P0 scope                                                       |
| F-05    | **Implemented**       | `tnrprnyowltzrtpnlmsnnpyqtuvszuol`                                                          | None                                                                                |
| F-06    | **Partially implemented** | `pvrovzutwpkwzsnxwmszutunxntopllp` — `fix: bind actions to their launching tmux context` | Popup targeting was removed because it changed established placement behaviour |
| F-07    | **Not started**       | —                                                                                           | High-match search/render scaling work                                               |
| F-08    | **Not started**       | —                                                                                           | Literal separator regex handling                                                    |
| F-09    | **Not started**       | —                                                                                           | Unique representable label positions                                                |
| F-10    | **Not started**       | —                                                                                           | Unicode normalized-to-original offset mapping                                       |
| F-11    | **Not started**       | —                                                                                           | Grapheme and terminal-cell-width model                                              |
| F-12    | **Not started**       | —                                                                                           | Effective targeted `word-separators` lookup                                         |
| F-13    | **Implemented**       | `muztupsovnqpuvpwwuukzllnsvsxoqyv`                                                          | None                                                                                |
| F-14    | **Implemented**       | `tnrprnyowltzrtpnlmsnnpyqtuvszuol`                                                          | None                                                                                |
| F-15    | **Implemented**       | `nrzzlzzxsrxnyqkllypnsxuxopnvynuk` — `fix: preserve exact popup snapshots`                  | None                                                                                |
| F-16    | **Implemented**       | `smtyylxtvysukkqmlsosxvkqllwvkvnr` — `fix: report auto-paste failures`                      | None                                                                                |
| F-17    | **Not started**       | —                                                                                           | Explicit multiline/bracketed-paste policy                                           |
| F-18    | **Not started**       | —                                                                                           | Quoting-safe loader execution boundary                                              |
| F-19    | **Won't fix**         | `yrvpukxwmrtyqkmsouvlpsnslnuyxrzw` — `revert: preserve established popup positioning`       | Preserve the established popup positioning behaviour                               |
| F-20    | **Not started**       | —                                                                                           | Intentional runtime Python interpreter selection                                    |
| F-21    | **Not started**       | —                                                                                           | Client-targeted OSC52 diagnostics and delivery semantics                            |
| F-22    | **Not started**       | —                                                                                           | Report tmux-buffer fallback destination accurately                                  |
| F-23    | **Not started**       | —                                                                                           | Monotonic idle timing and session-scoped raw mode                                   |
| F-24    | **Not started**       | —                                                                                           | Structural terminal-control validation                                              |

Verification for the implemented stack after removing explicit tmux-version enforcement:

- 306 tests pass on macOS/Python 3.14.6;
- reported `src` coverage is 96%;
- type checking, linting, formatting, and `git diff --check` pass;
- the working copy is clean above the implementation and rollback changes.

## Executive summary

The plugin's ordinary ASCII/Python paths are well unit-tested and fast, but the end-to-end tmux
runtime review identified several important defects that its original tests could not detect.
At discovery time, the review found:

- **12 confirmed correctness/compatibility defects** with high or medium priority;
- **7 probable runtime or environment defects/hazards** requiring focused real-tmux evidence;
- a **confirmed multi-second performance cliff** for supported large/high-match panes;
- a false compatibility claim: the code requires tmux 3.3 today despite advertising 3.2;
- a clear modernization direction: adopt tmux 3.6b while keeping Python 3.10.

The highest-priority issues are:

1. a failed popup can copy a stale result from an earlier invocation;
2. tmux 3.2/3.2a reject the unconditional `display-popup -B`;
3. the interactive UI searches a bottom row it deliberately hides, allowing invisible
   selection;
4. a fixed 35-second parent timeout overrides valid longer idle-timeout configuration;
5. invocation IPC is server-global and pane-scoped, so same-pane/reentrant uses can collide;
6. source pane and clipboard client identity remain partly implicit;
7. high-match redraws scale as rows × matches and reached 5.41 seconds in the local stress case.

Since the discovery review, F-01, F-03, and F-04 have been implemented. F-02 was resolved by an
owner decision to document tmux 3.6b as the supported minimum without runtime enforcement or a
version-specific CI gate. See [Implementation status](#implementation-status) for the live
ledger; the evidence and counts below describe the original review baseline.

## Scope and evidence

Reviewed:

- TPM/manual shell loading and key binding;
- both Python executable entrypoints;
- every module under `src`;
- pane capture, popup placement/lifecycle, tmux-buffer IPC, configuration, search, labels,
  rendering, range selection, OSC52, fallbacks, and auto-paste;
- tests, CI, packaging, installation, and support documentation;
- official tmux behavior from 3.2 through 3.6b;
- material Python 3.11/3.12 opportunities while retaining 3.10 as the expected baseline.

Evidence:

- 283 tests pass on macOS/Python 3.14.6;
- reported `src` coverage is 97%;
- type, lint, and format checks pass;
- focused read-only probes reproduced stale-result acceptance, false auto-paste diagnostics,
  separator-regex corruption, overlapping-label loss, Unicode offset corruption, and cell-width
  violations;
- a reproducible benchmark measured ordinary, large, very large, and dense-match panes;
- version claims use official tmux source/manual/release history and official Python documents.

Limitations:

- the available local tmux is 3.7b and the reviewing shell was not inside tmux;
- no live 3.2 or 3.6b popup session was installed for this discovery review;
- non-macOS clipboard fallbacks were assessed statically;
- real terminal rendering, multi-client targeting, popup geometry, and concurrent invocation
  hazards are marked probable where code/source evidence is strong but live confirmation remains
  necessary.

Supporting evidence:

- [Runtime contract](evidence/01-runtime-contract.md)
- [tmux 3.2–3.6b semantics](evidence/02-tmux-3.2-to-3.6b.md)
- [Lifecycle and state](evidence/03-lifecycle-state-failures.md)
- [Search/render/terminal safety](evidence/04-search-render-terminal-safety.md)
- [Performance](evidence/05-runtime-performance.md)
- [Integration/environment](evidence/06-integration-environment-risks.md)
- [Version modernization](evidence/07-version-modernization.md)
- [Test evidence](evidence/08-test-evidence-gaps.md)

## Prioritized findings

### P0 — Release-blocking correctness and support

#### F-01 — Failed popup execution can copy a stale prior selection

- Discovery status: confirmed defect
- Implementation: **implemented** in `jj` change `tnrprnyowltzrtpnlmsnnpyqtuvszuol`
- Severity: high
- Confidence: high
- Affected: all supported versions

The result buffer is neither uniquely named per invocation nor cleared before popup launch. The
parent reads it after `display-popup` returns regardless of popup exit status. A focused probe
made the popup fail with status 1 while an old buffer contained `STALE-SELECTION`; the popup layer
returned that old text as the new result.

Impact: an operational failure can silently replace the user's clipboard with unrelated text.
The confirmed tmux 3.2 `-B` rejection is one direct trigger.

Direction:

- use an invocation-unique result channel;
- initialize/clear state before launch;
- define explicit cancel/copy/paste/error outcomes;
- accept result data only after the matching successful child transaction;
- clean all state in an idempotent `finally`.

Required regression evidence: stale result plus rejected popup, child crash before write, every
outcome state, and crash between creation/read/cleanup.

#### F-02 — The advertised tmux 3.2 minimum is false

- Discovery status: confirmed compatibility defect
- Implementation: **accepted decision** in `jj` change
  `lrntorqpxsllpqvqkpoztuxrrytvoqyy`
- Severity: high
- Confidence: high
- Affected: tmux 3.2 and 3.2a

The popup always includes `-B`. Official tmux source and change history show `display-popup -B`
arrived in 3.3. tmux 3.2 rejects the shipped command, while the plugin generally converts that
failure to cancellation.

Decision: document tmux 3.6b as the supported floor throughout the project, but do not add a
runtime semantic-version check or version-specific CI gate. Compatibility below 3.6b is not
claimed; if it is later desired, it requires an explicit product decision and conditional
command behavior.

#### F-03 — Hidden bottom-row matches remain selectable

- Discovery status: confirmed defect
- Implementation: **won't fix**; attempted `jj` changes
  `vtnprqyurkmxrznwpyvwuxrlpukonqvq` and `utrwnrrkzynprtqwnsrkyvkxpnoktymy`
  were abandoned
- Severity: high
- Confidence: high
- Affected: all supported versions

The child indexes the full snapshot, then redraw removes the final remaining line because it
assumes it is a shell prompt. Matches are not filtered to rendered rows. Under default reverse
search, an invisible match can become the Enter-selected first result; it also consumes labels
and changes visible assignments.

Impact: incorrect invisible copy, missing application content, and disagreement between display
and selection.

Direction: define prompt allocation without assuming the bottom row's semantics, and make the
searchable/selectable row set identical to the rendered row set.

Resolution: preserve the established soft-wrapped label behaviour. The hidden-row correction
stopped labels continuing across pane-boundary wraps, and the follow-up terminal-row budgeting
did not restore the owner's runtime behaviour. Both changes were dropped; F-03 remains unfixed.

#### F-04 — Fixed parent timeout overrides valid child configuration

- Discovery status: confirmed defect
- Implementation: **implemented** in `jj` change `muztupsovnqpuvpwwuukzllnsvsxoqyv`
- Severity: high
- Confidence: high
- Affected: all supported versions

The child timeout is configurable; the parent always times out its popup command after 35
seconds. A 60-second configuration is therefore impossible, and active use beyond 35 seconds is
cancelled despite resetting the child timer.

Direction: give one layer ownership of timeout policy, validate timeout bounds, derive any outer
watchdog from that policy plus shutdown grace, and confirm the popup child has ended before
cleanup.

### P1 — Runtime identity, isolation, and scaling

#### F-05 — Server-global IPC is not isolated per invocation

- Discovery status: probable correctness/concurrency defect
- Implementation: **implemented** in `jj` change
  `tnrprnyowltzrtpnlmsnnpyqtuvszuol`
- Severity: high
- Confidence: high from tmux semantics; live interleaving still required
- Affected: all supported tmux versions

Snapshot/result buffers are named only by pane id, and auto-paste always uses `flash-paste`.
tmux buffers are server-global. Same-pane overlap, nested invocation, reentrancy, or multiple
clients can overwrite/read/delete one another's state.

Resolution: snapshot, result, and auto-paste buffers now use invocation identities with
centralized cleanup ownership.

#### F-06 — Launching pane and clipboard client identity are partly implicit

- Discovery status: probable multi-client targeting defect
- Implementation: **partially implemented** in `jj` change
  `pvrovzutwpkwzsnxwmszutunxntopllp`
- Severity: high
- Confidence: medium-high
- Affected: all reviewed tmux versions

The loader's `run-shell`, initial pane-id query, popup command, and OSC52 request omit explicit
targets. Later capture/paste correctly use a stable pane id, but it was resolved through tmux
current/recent context; OSC52 is client-specific.

Direction: capture pane and client identity in the binding context and explicitly forward/use
both throughout. tmux already supported the required targeting forms in 3.2; this does not
require 3.6b.

Resolution: the binding captures the source pane and launching client while handling the key
event. Pane capture and auto-paste use the explicit source pane, and OSC52 delivery targets the
launching client. Explicit `display-popup` targeting was removed after owner testing showed it
changed established popup placement; that remaining scope is intentionally tied to F-19.

#### F-07 — Large/high-match panes hit a multi-second algorithmic cliff

- Status: confirmed performance defect
- Severity: high for supported stress scenarios
- Confidence: high
- Affected: all supported Python versions

Benchmark results:

| Scenario         |    Shape | Characters | Matches |       Build |    Search |      Render | Build peak |
| ---------------- | -------: | ---------: | ------: | ----------: | --------: | ----------: | ---------: |
| Ordinary         |   24×120 |      2,903 |      96 |     2.15 ms |   0.34 ms |     0.51 ms |   0.14 MiB |
| Large            |  200×240 |     48,199 |   1,600 |    37.11 ms |   4.99 ms |     7.71 ms |   2.19 MiB |
| Very large       | 1000×500 |    500,999 |  17,000 |   387.06 ms |  58.35 ms |   341.32 ms |  23.88 MiB |
| Dense very large | 1000×500 |    500,999 | 250,000 | 1,198.85 ms | 832.58 ms | 5,411.62 ms |  61.50 MiB |

The primary causes are:

- `get_matches_at_line()` scans every match for every row, often twice: rows × matches;
- all overlapping occurrences are allocated, sorted, and processed even though only a finite
  label alphabet is selectable;
- the parent builds/retains an index that the child rebuilds;
- overlay rendering repeatedly scans and reconstructs ANSI-decorated lines.

Direction:

1. decide product behavior beyond label capacity and stop materializing useless selectable
   objects;
2. group matches by row once per query;
3. remove the unused parent index;
4. emit overlays in one immutable-coordinate pass;
5. measure real-tmux process/terminal cost after algorithmic correction.

Python 3.11/3.12 cannot cure these complexity problems.

### P2 — Search, rendering, and configuration correctness

#### F-08 — Literal hyphen separators can become regex ranges

- Status: confirmed defect
- Severity: medium
- Confidence: high

Configured separator characters are inserted into a negated regex class without escaping
hyphen. Example: separators `a-z` treat the entire lowercase range as separators; searching
`foo` in `foo-bar` produced `-` as the copied word.

Direction: use a correct literal character-class strategy and property-test every regex-special
separator position.

#### F-09 — End-of-token occurrences can overwrite visible labels

- Status: confirmed defect
- Severity: medium
- Confidence: high

Overlapping matches receive unique labels, but multiple logical endpoints can fall back to the
same final-character replacement position. With content `aa` and query `a`, two labels are
assigned but only the later one remains visible; the hidden label is still accepted.

Direction: determine unique representable overlay positions before assigning labels, or omit
colliding occurrences. Assert one visible label for every selectable label.

#### F-10 — Unicode lowercase expansion corrupts original offsets

- Status: confirmed defect
- Severity: medium
- Confidence: high

Case-insensitive search computes offsets in lowercased strings and reuses them against original
text. Lowercase mappings may expand. Searching `İ` in `İX` recorded a two-code-point original
match (`İX`), moving highlight, label, and precise range endpoint.

Direction: maintain a normalized-to-original boundary map or adopt another explicit
normalization model that preserves original coordinates.

#### F-11 — Rendering uses code points as terminal cells

- Status: confirmed defect
- Severity: medium
- Confidence: high

Labels, cursor placement, right alignment, and pinned markers use Python indices/`len()`.
CJK/emoji can occupy two cells; combining marks can occupy zero; custom labels can do either.
Replacing one code point therefore changes row width/wrapping and violates the plugin's explicit
fixed-width label invariant.

tmux 3.6's tab-preserving capture strengthens fidelity but adds another variable-width case.

Direction: define grapheme/cell-width handling, restrict labels to one printable cell, and
calculate overlays/cursors in terminal cells.

#### F-12 — Effective tmux `word-separators` may come from the wrong scope

- Status: probable configuration defect
- Severity: medium
- Confidence: medium-high

The plugin reads the global default for a session option rather than the effective value for the
captured pane's session. tmux copy mode and flash-copy can disagree in multi-session setups.

Direction: query the effective option using the explicit source target, while retaining the
documented global plugin override.

#### F-13 — Configuration validation contradicts documentation

- Discovery status: confirmed defect
- Implementation: **implemented** in `jj` change
  `muztupsovnqpuvpwwuukzllnsvsxoqyv`
- Severity: medium
- Confidence: high

Examples:

- documentation says idle timeout below one is ignored; code accepts zero/negative values and
  expires immediately;
- an unknown boolean becomes false instead of using the declared default or reporting invalid;
- custom labels can include `;`/`:` while those keys are intercepted as auto-paste modifiers;
- zero-cell, multi-cell, duplicate, and structural-control labels are not rejected.

Resolution: invalid idle bounds receive safe fallbacks; unknown booleans honor their declared
defaults; and custom labels fall back unless they are unique visible ASCII characters disjoint
from active input keys. Broader Unicode label width remains part of F-11.

### P2 — Failure handling and integration

#### F-14 — Failure branches leak state and mask operational errors

- Discovery status: confirmed robustness defect
- Implementation: **implemented** in `jj` change
  `tnrprnyowltzrtpnlmsnnpyqtuvszuol`
- Severity: medium
- Confidence: high

Result-read failure skips snapshot cleanup; timeout/general exception do not necessarily clean a
result; child top-level exceptions print but can exit apparently successfully; snapshot-buffer
write failure silently changes behavior to a later recapture; popup error and deliberate cancel
usually collapse to the same parent result.

Resolution: result acceptance is transaction-scoped, top-level child failures are nonzero,
cleanup is centralized and idempotent, snapshot initialization fails closed, and operational
popup/transport failures propagate distinctly from deliberate cancellation.

#### F-15 — Child snapshot transport uses display-oriented `show-buffer`

- Discovery status: probable version-sensitive correctness defect
- Implementation: **implemented** in `jj` change
  `nrzzlzzxsrxnyqkllypnsxuxopnvynuk`
- Severity: medium
- Confidence: medium-high

tmux 3.4 changed `show-buffer` to process escape sequences. The child uses it for exact
ANSI-preserving snapshot transport, while the parent already uses serialization-oriented
`save-buffer ... -` for results.

Direction: use an exact-data serialization primitive consistently and round-trip SGR,
whitespace, tabs, newlines, and escapes across relevant tmux versions.

Resolution: the child now reads the immutable snapshot with `save-buffer ... -`, matching the
serialization-oriented result transport. Regression coverage preserves trailing spaces and
multiple trailing newlines without recapturing live pane content on failure.

#### F-16 — Auto-paste reports success after failed operations

- Discovery status: confirmed defect
- Implementation: **implemented** in `jj` change `smtyylxtvysukkqmlsosxvkqllwvkvnr`
- Severity: medium
- Confidence: high

The subprocess helper returns false on command failure. Auto-paste ignores both buffer-write and
paste booleans, logs success unconditionally, and still returns copy success. A failed first
write can be followed by pasting stale fixed-buffer content.

Resolution: the requested operation returns success only when copy, transient-buffer write, and
paste all succeed. A failed buffer write prevents paste, cleanup failure prevents a success
result, every failure is logged truthfully, and the entrypoint propagates failure as a nonzero
exit.

#### F-17 — Multiline auto-paste omits bracketed-paste protection

- Status: documented environment-specific risk
- Severity: medium
- Confidence: high

tmux `paste-buffer` converts LF to CR by default and adds bracketed-paste markers only with `-p`.
The plugin uses neither `-p` nor `-r`. A multiline copied range can become multiple submitted
commands in a shell rather than guarded pasted text.

Direction: define intended semantics explicitly and select/document tmux flags based on the
security/UX trade-off.

#### F-18 — Loader execution remains a quoting-sensitive shell boundary

- Status: probable installation/security-adjacent defect
- Severity: medium
- Confidence: high for boundary, path-specific live confirmation pending

The popup child is launched with a safe multi-operand argv contract. The loader instead installs
an absolute path as `run-shell` input, which crosses tmux parsing/format expansion and `/bin/sh`.
Paths with whitespace/metacharacters may be reinterpreted.

Direction: preserve the path as data across both parsers or avoid the shell boundary. Test
hostile-but-valid installation paths.

#### F-19 — Popup geometry/resize policy lacks real-runtime validation

- Discovery status: probable defect
- Implementation: **won't fix** after owner testing of `jj` change
  `klmwsqszzslvvqqrupxnrpwmrvktzlnn`; reverted in
  `yrvpukxwmrtyqkmsouvlpsnslnuyxrzw`
- Severity: medium
- Confidence: medium-high

For non-top panes, y is calculated as `pane_bottom + 1` while popup height remains the pane
height; official coordinates are client-relative, making this look like a bottom coordinate used
as a top. Current tests merely encode the formula. Capture, geometry, popup size, and rendering
also occur at different times; resize can desynchronize them, and fallback recapture changes the
snapshot silently.

Direction: verify real top/bottom/left/right pane overlays, then define immutable snapshot and
resize behavior.

Resolution: preserve the established popup positioning and fallback behaviour. The attempted
coordinate and explicit-target changes placed pane C's popup over pane B in the owner's tested
stacked layout, so they were rolled back. Further geometry work is marked won't fix until a
real-tmux harness can protect the layouts already known to work.

#### F-20 — Runtime Python selection may ignore the project environment

- Status: environment compatibility hazard
- Severity: medium
- Confidence: high

The binding executes `#!/usr/bin/env python3`. `uv sync` does not make tmux's inherited PATH use
the virtual environment. The runtime can select an older system Python even when a valid project
environment exists.

Direction: document the source-checkout/shebang deployment model and offer an intentional
interpreter/launcher configuration if needed.

### P3 — Hardening and observability

#### F-21 — OSC52 success is attempted delivery, not observed clipboard success

- Status: environment risk
- Severity: low to medium
- Confidence: high

A zero result from `set-buffer -w` means tmux accepted the operation. Terminal capability,
policy, nesting, and target-client choice can still prevent the intended clipboard change.
Native fallback will not run after accepted-but-ignored OSC52.

Direction: target the launching client, improve diagnostics, and describe delivery honestly.
tmux 3.6b capability detection helps but cannot verify terminal policy.

#### F-22 — tmux-only fallback is reported as generic copy success

- Status: documented semantic risk
- Severity: low
- Confidence: high

The final fallback writes only a tmux buffer but satisfies the boolean “copy” contract. Detailed
clipboard docs disclose this; top-level product language promises the system clipboard.

Direction: report delivery destination, not just success/failure.

#### F-23 — Elapsed idle timing uses an adjustable wall clock

- Status: hardening opportunity
- Severity: low
- Confidence: high

`time.time()` can move during an interaction. Use monotonic elapsed time, ideally while moving
raw terminal mode ownership from each 100 ms poll to one exception-safe session boundary.

#### F-24 — Rendering configuration accepts structural terminal controls

- Status: hardening opportunity
- Severity: low
- Confidence: high that validation is absent

Prompt/label strings and color controls are emitted directly. Malformed user configuration can
move the cursor, erase content, insert rows, or make selection impossible. This is trusted-user
configuration, not a remote pane-content exploit.

Direction: validate printable single-line text separately from an explicitly supported SGR
subset.

## tmux 3.6b modernization decision

Current decision: **document tmux 3.6b as the minimum, without runtime enforcement**.

Benefits that become universal:

- current `-B` popup invocation is supported;
- popup survives resize and source panes continue redrawing (since 3.3);
- accumulated extended-key, Unicode, paste, and clipboard fixes;
- focus enter/leave events for popups (3.6);
- tab-preserving capture/copy (3.6);
- OSC52 capability detection through terminal device attributes (3.6);
- multi-operand popup argv execution is publicly documented in 3.6.

Compatibility cost:

- excludes tmux 3.3–3.6a installations which may run the current feature set;
- no repository telemetry exists to quantify affected users;
- 3.2 users are not newly losing a working popup path because `-B` already breaks it.

Important caveat: raising the minimum does **not** fix stale results, shared IPC, implicit targets,
option scope, loader quoting, multiline paste policy, Unicode/cell rendering, or Python
complexity. Most required tmux primitives for those fixes already existed in 3.2.

If explicit enforcement is reconsidered later, it would require:

- semantic comparison of lettered tmux versions (`3.6`, `3.6a`, `3.6b`, `3.10`, suffixes);
- actionable load/invocation error;
- real tmux 3.6b release evidence;
- documentation of dropped 3.3–3.6a compatibility.

## Python baseline decision

Recommendation: **keep Python 3.10**.

Python 3.11 has credible directional benefit:

- official documentation reports faster startup, relevant because two short-lived interpreters
  run per invocation;
- general pure-Python execution improvements may reduce search/render constants.

That is not enough to raise the floor:

- no matched 3.10/3.11 plugin benchmark exists;
- ordinary Python work is already fast;
- supported stress failures are algorithmic and remain multi-second under a faster interpreter;
- roughly 14–15 synchronous tmux CLI boundaries and terminal I/O are unaffected.

Python 3.12's comprehension/object optimizations do not map materially to the dominant
rows × matches scan, occurrence objects, duplicate index, or overlay rescans.

Reconsider only after correctness/algorithmic work, using identical end-to-end
launch-to-first-frame and query-to-frame benchmarks on 3.10 and 3.11.

## Test strategy

Current tests are valuable but insufficient for this runtime:

- 283 tests pass;
- 97% coverage applies only to `src`;
- the shell loader and executable scripts are outside the configured coverage target;
- no real tmux version, popup, client, buffer, or terminal contract is tested.

Recommended layers:

1. **Pure contract/property tests**
   - Unicode normalized/original boundaries;
   - literal separator properties;
   - assigned-to-rendered label bijection;
   - terminal cell/grapheme fixtures;
   - explicit popup result state machine;
   - semantic configuration validation;
   - deterministic scaling counters.
2. **Executable protocol tests with a fake `tmux` CLI**
   - run both entrypoints as processes;
   - record argv, exact text, exit status, cleanup, and injected failures.
3. **Small real-tmux integration matrix**
   - declared minimum 3.6b;
   - loader/binding, popup, copy/range/cancel, resize, multi-client target, concurrency, option
     scope, and exact buffer round trips.
4. **Limited environment smoke checks**
   - macOS OSC52/pbcopy diagnostics;
   - one SSH/nested path;
   - Linux fallback only on an appropriate runner;
   - selected real-terminal cell rendering.

Report unit coverage and runtime-contract scenarios separately; one percentage cannot represent
both.

## Proposed implementation sequence

This was the discovery sequence. Use the implementation ledger above for current state; completed
and partial work should be skipped or narrowed to the remaining scope recorded there.

### Phase 1 — Make result handling transactional

**Status: complete.**

Address F-01, F-05, F-14, and F-16 together:

- invocation identity;
- explicit outcome protocol;
- preflight initialization;
- idempotent cleanup;
- truthful copy/paste outcomes;
- failure-injection tests.

This removes the most dangerous stale/cross-invocation behavior before other changes.

### Phase 2 — Bind runtime identity and lifetime

**Status: closed with popup positioning marked won't fix.**

Address F-04, F-06, F-15, and F-19:

- explicit source pane/client;
- exact snapshot serialization;
- one timeout owner;
- immutable snapshot/resize policy;
- verified popup geometry.

Use real tmux evidence here; mocks cannot settle these contracts.

### Phase 3 — Correct selection/render coordinates

Address F-03 and F-08 through F-13:

- same searchable/rendered row set;
- literal separator handling;
- collision-free label planning;
- normalized-to-original offsets;
- grapheme/cell-width model;
- effective option scope and configuration validation.

These changes share coordinate/input invariants and should be designed together.

### Phase 4 — Remove the scaling cliff

Address F-07 after selectable-match semantics are fixed:

- cap/separate selectable and nonselectable occurrence representations;
- direct matches-by-row index;
- one search index;
- single-pass overlay emission;
- ordinary/large/dense performance budgets.

This order avoids optimizing the current incorrect label/row model.

### Phase 5 — Harden loading, paste, and delivery semantics

Address F-17, F-18, F-20 through F-24:

- loader quoting and runtime interpreter policy;
- explicit multiline paste behavior;
- OSC52 client targeting/diagnostics;
- delivery destination result;
- monotonic timing and rendering-option validation.

### Phase 6 — Adopt the 3.6b support floor

The documentation correction is complete. Runtime enforcement and a version-specific release
gate were considered and intentionally omitted. If that decision changes, the work would include:

- semantic version guard;
- 3.6b real-integration gate;
- release note for dropping 3.3–3.6a;
- tab-aware rendering evidence;
- updated troubleshooting and clipboard claims.

Keep Python 3.10 and its CI job.

## Final assessment

The plugin has a solid unit-tested core for ordinary ASCII use, but its most consequential risks
sit at boundaries omitted by current coverage: tmux version semantics, process outcome/IPC,
client targeting, terminal coordinates, and stress-case data structures. The absence of reported
bugs should not be treated as evidence that these paths are safe; several defects were
deterministically reproduced.

The recommended strategy is not a broad rewrite. Invocation/result state and the visible-row
contract now have their first corrections; next establish real tmux contract tests, finish the
remaining identity/failure work, correct the broader coordinate model, and only then optimize
the high-match path. Document tmux 3.6b as the support floor and keep Python 3.10 because
version-based speedups are secondary to correctness and algorithmic improvements.
