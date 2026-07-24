# Audit Installation, Configuration, Clipboard, and Environment Risks

Type: task
Status: resolved
Blocked by: 01, 02

## Question

Which loader, executable/path, packaging, configuration parsing, tmux option-scope, OSC52,
auto-paste, SSH/nesting, terminal-capability, and platform-fallback assumptions can break or
degrade the runtime path?

Use static analysis for non-macOS clipboard fallbacks, report environment-specific risks rather
than requiring cross-platform reproduction, and reconcile findings with documented support
claims.

## Answer

The results are recorded in
[Installation, Configuration, Clipboard, and Environment Audit](../evidence/06-integration-environment-risks.md).

Beyond the confirmed false tmux 3.2 claim, the audit finds effective `word-separators` scope,
missing timeout validation, invalid-boolean handling, and unselectable custom labels as
configuration defects. It documents loader path quoting and runtime Python/PATH selection as
installation hazards; distinguishes accepted OSC52 delivery from an observed clipboard change;
and identifies multiline auto-paste semantics as an environment-specific risk.

Non-macOS clipboard fallbacks were analyzed statically only. CI's broad Python matrix is a
strength, but the absence of real tmux, loader, entrypoint, minimum-version, and macOS runtime
coverage is a material evidence gap.
