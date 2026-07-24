# Audit Search, Selection, Rendering, and Terminal Safety

Type: task
Status: resolved
Blocked by: 01

## Question

Which pane-content, Unicode, ANSI/control-sequence, wrapping, resize, word-boundary, label,
range-selection, input, and rendering cases can produce incorrect selection, incorrect copied
text, display corruption, unsafe terminal behavior, or an unusable interactive session?

Exercise ordinary and adversarial content, including large captures and high match counts, and
record finding evidence and missing regression tests without changing production code.

## Answer

The audit is recorded in
[Search, Rendering, and Terminal-Safety Audit](../evidence/04-search-render-terminal-safety.md).
It confirmed five defects: selectable hidden bottom-row matches, colliding overlays for
end-of-token occurrences, incorrect regex range semantics for literal hyphen separators,
Unicode lowercase expansion corrupting original offsets, and failure to preserve terminal cell
width for labels and cursor calculations.

It also identified structural validation of user-configurable terminal strings as a
low-severity hardening gap. Each finding includes severity, confidence, affected versions,
focused reproduction evidence, remediation direction, and regression-test requirements. No
production or test files were changed.
