# tmux and Python Baseline Modernization

## Decision

Raise the documented and enforced tmux minimum to **3.6b** if the project is willing to stop
supporting tmux 3.3–3.5. This is primarily a correctness and support-policy decision, with useful
robustness and fidelity benefits; it is **not** a remedy for the plugin's own major correctness or
performance defects.

Keep the Python minimum at **3.10**. Python 3.11 should make this pure-Python, short-lived program
somewhat faster without code changes, but the available evidence does not show a material enough
end-to-end gain to justify excluding Python 3.10. Python 3.12 adds no workload-specific improvement
that changes that conclusion.

## Evidence boundary

Version claims below use only primary official sources:

- [tmux 3.2 manual](https://github.com/tmux/tmux/blob/3.2/tmux.1)
- [tmux 3.2 popup implementation](https://github.com/tmux/tmux/blob/3.2/cmd-display-menu.c#L49-L58)
- [tmux 3.6b manual](https://github.com/tmux/tmux/blob/3.6b/tmux.1)
- [tmux changes through 3.6b](https://github.com/tmux/tmux/blob/3.6b/CHANGES)
- [Python 3.11 “What’s New” performance notes](https://docs.python.org/3.11/whatsnew/3.11.html#faster-cpython)
- [Python 3.12 “What’s New” optimization notes](https://docs.python.org/3.12/whatsnew/3.12.html#optimizations)
- [PEP 709: inlined comprehensions in Python 3.12](https://peps.python.org/pep-0709/)

The local performance profile was run with Python 3.14.6, not as a cross-version benchmark.
Accordingly, this note does not assign invented 3.10/3.11/3.12 speedup percentages to the plugin.

## tmux 3.6b

### The immediate correctness benefit: make the support claim true

The plugin always passes `-B` to `display-popup`. The option is absent from both the tmux 3.2
popup synopsis and its accepted option template; the official change history records `-B` as
added after 3.2a for 3.3. Therefore:

- the advertised 3.2 baseline is already false;
- the executable's present effective minimum is 3.3;
- selecting 3.6b makes every currently used popup flag part of the supported baseline.

This is the strongest reason to change the baseline. If retaining 3.2 mattered, removing or
conditionally supplying `-B` would be the alternative, but that is a different product choice.

The compatibility cost is real but cannot be quantified from repository evidence: an enforced
3.6b minimum excludes tmux 3.3, 3.3a, 3.4, 3.5 and 3.6/3.6a installations that can run all or
most of the current plugin. It does not newly exclude a functioning 3.2 population, because the
unconditional `-B` already prevents that population from using the popup path. No installation
telemetry is available, so the review should not claim how many users are affected.

### Concrete robustness and fidelity benefits

The following official changes become universal assumptions at a 3.6b floor:

| Available by | Official behavior/fix | Concrete plugin benefit | Required plugin work |
| --- | --- | --- | --- |
| 3.3 | Popups are adjusted rather than closed on resize | Fewer abrupt cancellations during an interaction | Still define how the immutable capture and overlays react to geometry changes |
| 3.3 | Panes continue to redraw behind a popup | Source applications no longer appear frozen merely because flash-copy is open | Treat the capture as an explicit snapshot; never silently recapture after losing IPC state |
| 3.5 | Multiple extended-key fixes and mode-2 handling | More consistent modified-key input at the popup terminal boundary | Add real-tmux input tests; the child still decodes raw bytes itself |
| 3.5 | Clipboard escape-sequence terminator sizing fixed | More robust OSC52 delivery through tmux | Terminal capability and policy can still prevent delivery |
| 3.6 | Focus events are sent on entering and leaving a popup | Better focus semantics for applications in the source pane | Expect focus-triggered redraws behind the immutable snapshot |
| 3.6 | Tabs are preserved in capture/copy | Better copied-text fidelity | Renderer/search must become tab-cell-aware; otherwise this exposes existing coordinate defects |
| 3.6 | Pasted input is copied without key interpretation | More literal auto-paste transport | The plugin must still choose `paste-buffer -p` if it wants bracketed-paste protection |
| 3.6 | OSC52 support can be detected through terminal device attributes | Less manual terminal-feature setup on terminals that report support | A successful tmux command still cannot prove the outer clipboard changed |

These items are summarized from the official
[3.6b change history](https://github.com/tmux/tmux/blob/3.6b/CHANGES). The exact capture,
popup, buffer and paste interfaces are documented in the
[3.6b manual](https://github.com/tmux/tmux/blob/3.6b/tmux.1).

There is also a supportability benefit: tmux 3.6b finally documents the popup form as accepting
`shell-command [argument ...]`. The implementation accepted multiple operands earlier, including
3.2, but a 3.6b floor lets the plugin rely on a documented argv-preserving public interface
instead of a source-derived contract. The current multi-operand invocation should be retained
because it avoids interpolating configuration and pane data into a shell string.

### What raising the minimum does not fix

Most high-value remedies found by this review do not need tmux 3.6b:

- explicitly carry and use the source pane and client targets;
- read effective pane/session options rather than global defaults;
- serialize snapshot bytes with `save-buffer -` instead of display-oriented `show-buffer`;
- use invocation-unique IPC names or an ownership protocol;
- make result consumption atomic and reject missing/stale results;
- use `paste-buffer -p` where bracketed paste is intended;
- quote or avoid the loader's `run-shell` shell boundary.

The required targeting, named-buffer, `save-buffer`, popup, and clipboard forms existed in 3.2.
A baseline bump must not be presented as fixing these plugin defects.

Nor does 3.6b solve the measured scaling cliff. Search-index duplication, all-occurrence
materialization, rows-by-matches lookup, and repeated overlay scans are Python/data-structure
costs. The tmux upgrade may improve upstream behavior, but it does not change those algorithms or
meaningfully reduce the roughly 14–15 synchronous tmux client processes in a normal invocation.

### Recommended baseline policy

If adopted, make the minimum executable rather than documentary:

1. check `tmux -V` at load or invocation and emit one actionable error below 3.6b;
2. test the loader and a real popup against 3.6b in CI or a release gate;
3. keep all tmux recommendations capped at interfaces documented by 3.6b;
4. document the loss of 3.3–3.5 compatibility as the migration cost.

Version strings include lettered patch releases, so a guard must compare tmux versions
semantically rather than lexicographically and must have tests for `3.6`, `3.6a`, `3.6b`,
`3.10`, and nonstandard suffixes. The official source has a `-V` command, but the parsing and
policy are the plugin's responsibility.

## Python 3.10 versus 3.11 and 3.12

### Python 3.11 has a credible benefit, but not a baseline-changing one

The runtime has two properties that align with official Python 3.11 improvements:

- it starts two short-lived Python processes per invocation, and Python 3.11 reports interpreter
  startup about 10–15% faster due to frozen core modules;
- its pathological cases spend seconds in pure-Python calls, loops, sorting, object creation, and
  string processing, and Python 3.11 reports an average 25% improvement over 3.10 on
  `pyperformance`, while warning that results vary by workload and I/O-bound programs may see
  little benefit.

Those are credible directional benefits from the official
[Faster CPython notes](https://docs.python.org/3.11/whatsnew/3.11.html#faster-cpython), not measured
plugin results. They do not justify a baseline change:

- ordinary search/render work is already sub-millisecond to low-millisecond locally;
- launch time also contains many synchronous tmux processes and popup/terminal I/O, which an
  interpreter upgrade cannot accelerate;
- the multi-second supported stress cases are dominated by avoidable algorithmic complexity.
  Even a substantial constant-factor interpreter improvement would leave them unresponsive;
- the project has no matched 3.10-versus-3.11 end-to-end measurement on the same machine.

Python 3.11 is therefore worth recommending as an optional runtime for users who already have it,
not requiring from everyone. Before reconsidering the baseline, measure launch-to-first-frame and
query-to-frame on 3.10 and 3.11 after the algorithmic fixes, using identical content and builds.

### Python 3.12 does not add a material workload-specific case

Python 3.12's relevant general change is PEP 709 comprehension inlining, which removes the nested
frame for list/dict/set comprehensions and reports faster comprehension execution. The
[PEP](https://peps.python.org/pep-0709/) estimates up to roughly twofold improvement for an
isolated comprehension and about 11% in a comprehension-heavy synthetic benchmark. The official
[3.12 optimization list](https://docs.python.org/3.12/whatsnew/3.12.html#optimizations) also
includes smaller object and selected-library improvements.

None maps to the dominant runtime costs strongly enough to justify excluding 3.10 or 3.11:

- this plugin is not `asyncio`, `tokenize`, `inspect`, or regex-substitution heavy;
- comprehension call-frame overhead is not the rows × matches scan, excess match
  materialization, duplicate index, or repeated overlay construction;
- removing `wstr` saves 8 or 16 bytes per Unicode object, but the measured tens of MiB are largely
  caused by retaining hundreds of thousands of application-level match/index objects.

Python 3.12 may provide another modest constant-factor improvement, but the evidence is less
direct than for 3.11 and is not material to the product decision.

### Compatibility and maintenance costs

Raising the Python floor would:

- reject otherwise compatible Python installations even though the code and locked metadata
  currently declare `>=3.10`;
- reduce the CI/runtime matrix without eliminating a compatibility branch used in production
  code—the runtime has no identified 3.10-specific workaround to remove;
- provide no correctness simplification required by the reviewed runtime path.

The only concrete maintenance simplification visible in the dependency lock is removal of some
conditional backports on newer interpreters, but those are development/test dependencies and do
not improve the installed plugin's user-visible runtime. Syntax, typing, and traceback
improvements are intentionally outside this performance/correctness decision.

## Final recommendation

| Baseline decision | Recommendation | Why |
| --- | --- | --- |
| tmux 3.2 → 3.6b | **Adopt, with an enforced version check and 3.6b integration evidence** | Corrects an already-false support claim, makes the documented argv contract available, and establishes a materially more robust popup/capture/OSC52 floor |
| Python 3.10 → 3.11 | **Do not require** | Credible startup and pure-Python speed benefit, but no matched plugin measurement and no cure for the dominant algorithmic/process costs |
| Python 3.10 → 3.12 | **Do not require** | No additional workload-specific material benefit beyond modest constant-factor optimization |

The implementation order should be: fix the plugin's correctness and scaling defects, establish
real 3.6b integration coverage, enforce/document the tmux baseline, then benchmark Python versions
only if interpreter time remains material. Raising Python should not be used as a substitute for
the algorithmic fixes.
