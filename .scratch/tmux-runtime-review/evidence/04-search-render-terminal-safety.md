# Search, Rendering, and Terminal-Safety Audit

## Method

Reviewed the immutable-snapshot search/index, label assignment, range extraction, ANSI mapping,
interactive input loop, and redraw pipeline. Existing unit tests were reconciled with focused
read-only probes using the repository's virtual environment. No production or test files were
changed.

The full baseline suite passes (283 tests), but the cases below are absent from it.

## Findings

### SR-1 — Hidden bottom-line matches can be selected

- Classification: confirmed defect
- Severity: high
- Confidence: high
- Versions: all supported Python and tmux versions; not fixed by raising either baseline
- Runtime path: child snapshot display and selection

The search index is built over the entire plain snapshot. During every redraw,
`_display_content()` strips trailing newlines and then unconditionally removes the final
remaining line on the assumption that it is a shell prompt. The current matches are not filtered
to displayed lines.

Consequences:

- the bottom visible line is unavailable in the overlay even when it is application content, not
  a prompt;
- reverse search (the default) can make an invisible bottom-line match the first match;
- pressing Enter can copy that invisible match;
- label assignment consumes labels for hidden matches and can therefore change labels shown
  elsewhere.

This violates the documented promise to search visible pane content and the invariant that every
selectable match has a visible overlay.

Remediation direction: define display rows from actual popup capacity without assuming semantic
knowledge of a shell prompt. Search and label exactly the rows rendered, or render the whole
captured pane with an explicitly allocated prompt row and a documented clipping rule.

Regression evidence needed:

- bottom row with ordinary application content;
- reverse and forward search with matches on the bottom row;
- Enter and label selection never choose a non-rendered match;
- trailing blank rows and a genuine shell-prompt row.

### SR-2 — End-of-token occurrences can overwrite each other's labels

- Classification: confirmed defect
- Severity: medium
- Confidence: high
- Versions: all supported Python and tmux versions
- Runtime path: multi-occurrence search and label overlay

Every overlapping occurrence in a non-whitespace sequence becomes a separate `SearchMatch`.
Labels are unique, but label placement falls back from the logical end boundary to the final
character when an occurrence ends at end-of-line/token. Two occurrences can therefore replace
the same character.

Reproduction:

```text
content: "aa"
query:   "a"
matches: (0..1, label q, label column 1), (1..2, label w, label column 2)
render:  only w remains visible at the final character
```

The first label is still accepted by input despite no longer being visible. Longer overlapping
patterns can create the same collision.

Remediation direction: make label placement positions unique and representable before labels are
assigned, or collapse/omit occurrences whose fixed-width overlay position collides. Label
assignment and rendering must share the same placement model.

Regression evidence needed:

- repeated characters with one-character queries;
- overlapping multi-character queries at end-of-line;
- assertion that every assigned label occurs exactly once in rendered output.

### SR-3 — Literal separators can accidentally become regex ranges

- Classification: confirmed defect
- Severity: medium
- Confidence: high
- Versions: all supported Python and tmux versions
- Runtime path: copied-word boundary extraction

Configured word separators are interpolated into a negated regular-expression character class.
The escaping helper handles backslash, closing bracket, and a leading caret, but not hyphen.
A hyphen between characters is interpreted as a range rather than a literal separator.

Focused reproduction:

```text
content:    "foo-bar baz"
separators: "a-z"
query:      "foo"
copy_text:  "-"
```

The user intended `a`, `-`, and `z` as separators; the pattern instead excludes the entire
lowercase alphabet. Other separator orderings can silently broaden ranges.

Remediation direction: use correct character-class escaping (for example, a proven regex escape
strategy with placement rules) and treat every configured code point literally.

Regression evidence needed:

- hyphen at the start, middle, and end of separator strings;
- combinations with `]`, backslash, and caret;
- the documented shell/configuration separator example.

### SR-4 — Expanding lowercase mappings corrupt match boundaries

- Classification: confirmed defect
- Severity: medium
- Confidence: high
- Versions: all supported Python versions
- Runtime path: case-insensitive Unicode search, highlight, label, and precise range offsets

Case-insensitive search lowercases the sequence and query, then treats offsets and lengths in the
lowercased string as offsets into the original string. Unicode lowercase mappings are not always
length-preserving.

Focused reproduction:

```text
content: "İX"
query:   "İ"
lowered query length: 2
recorded original match: 0..2 ("İX"), rather than only "İ"
```

The label boundary, highlighted substring, and precise-range endpoint move one code point too
far. Similar problems exist for any multi-code-point case mapping.

Remediation direction: preserve an explicit mapping from normalized search positions to original
grapheme/code-point boundaries, or constrain and document a normalization model that cannot
silently reuse incompatible offsets.

Regression evidence needed:

- Turkish dotted capital I in content and query;
- multiple expanding mappings in one token;
- highlight, copied word, and precise range endpoints against original content.

### SR-5 — Code-point replacement does not preserve terminal cell width

- Classification: confirmed defect
- Severity: medium
- Confidence: high
- Versions: all supported Python and tmux versions; interpreter upgrades do not solve it
- Runtime path: label overlays, pinned markers, prompt placement, and cursor positioning

The renderer equates Python `len()`/string indices with terminal columns. Replacing one code point
does not necessarily replace one terminal cell:

- a CJK or many emoji code points occupy two cells, so a default one-cell label shrinks the line;
- a combining mark occupies zero cells, so replacing it adds a cell;
- a custom label may itself occupy zero or two cells;
- prompt/query cursor calculations and right-aligned indicators use code-point length.

Focused probes confirmed that a custom `界` label replaces a one-cell character with a two-cell
glyph, and the same inverse mismatch occurs when a normal label replaces a wide pane glyph.
This violates the explicit no-wrap/no-movement label invariant and can misplace the cursor or
change wrapping.

Remediation direction: establish a terminal-cell-width model (including grapheme clusters and
ambiguous-width policy), restrict labels to exactly one printable cell, and calculate overlay and
cursor positions in cells rather than code points.

Regression evidence needed:

- CJK, emoji, variation selectors, combining sequences, and zero-width joiner sequences;
- invalid custom labels (zero-cell, two-cell, duplicate, control/newline);
- wide prompt indicators and queries;
- rendered cell width exactly equals source row width.

### SR-6 — User-configurable terminal strings are structurally unvalidated

- Classification: probable compatibility/safety hazard
- Severity: low
- Confidence: high that validation is absent; impact depends on configuration
- Versions: all supported Python and tmux versions
- Runtime path: prompt, color, marker, and label rendering

Color options intentionally accept ANSI SGR sequences, while prompt text, indicator, and label
characters are emitted directly. There is no distinction between trusted style sequences and
structural terminal controls such as cursor movement, erase, newline, carriage return, or OSC.
A malformed or copied configuration value can corrupt the popup layout or make labels
unselectable.

This is configuration-originated rather than pane-originated and is therefore best treated as
hardening, not an untrusted remote-code issue.

Remediation direction: validate each option by semantic type: single-cell labels, printable
single-line prompt text, and a deliberately supported SGR subset for colors.

Regression evidence needed:

- newline/carriage-return prompt values;
- cursor/erase controls in non-color options;
- non-SGR escape sequences in color options;
- safe fallback and useful diagnostics.

## Lower-priority observations

- Arrow/function-key escape sequences are effectively treated as Escape cancellation rather than
  parsed as multi-byte keys. This matches the documented key set but should remain explicit.
- ANSI mapping recognizes SGR sequences only. tmux's exact `capture-pane -e` output contract must
  be established by the tmux-semantics ticket before broader pane-originated escape handling is
  classified as a defect.
- Label exhaustion intentionally leaves later matches unlabeled. The final report should
  distinguish this capacity rule from the label-collision defect above.

## Test-evidence assessment for this area

Existing tests are strong for ordinary ASCII matching, separator-aware copies, range extraction,
basic SGR mapping, modifier state, and mocked interactive branches. They do not currently assert:

- that searchable matches and rendered rows are the same set;
- one rendered label per assigned match;
- literal semantics for every regex-special separator;
- Unicode normalization/case-mapping position preservation;
- terminal cell-width preservation;
- semantic validation of rendering configuration.
