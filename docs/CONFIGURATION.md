# Configuration

This document lists the tmux-flash-copy configuration options and common ANSI colour codes.

## Table of contents

- [Configuration options](#configuration-options)
  - [General options](#general-options)
  - [Prompt](#prompt)
  - [Matched text and labels](#matched-text-and-labels)
- [ANSI colour codes](#ansi-colour-codes)
- [Related documentation](#related-documentation)

## Configuration options

The following configuration options are supported. Default values are listed, with overrides to be added to your tmux configuration (`~/.tmux.conf`).

### General options

| Option                                                                    | Description                                  |
| ------------------------------------------------------------------------- | -------------------------------------------- |
| [`@flash-copy-bind-key`](#flash-copy-bind-key-default-f)                  | Key binding to activate tmux-flash-copy      |
| [`@flash-copy-bind-key-mode`](#flash-copy-bind-key-mode-default-prefix)   | Key table for the activation binding         |
| [`@flash-copy-word-separators`](#flash-copy-word-separators)              | Characters that define word boundaries       |
| [`@flash-copy-case-sensitive`](#flash-copy-case-sensitive-default-off)    | Case-sensitive searching                     |
| [`@flash-copy-reverse-search`](#flash-copy-reverse-search-default-on)     | Direction of label assignment when searching |
| [`@flash-copy-auto-paste`](#flash-copy-auto-paste-default-on)             | Enable auto-paste modifier functionality     |
| [`@flash-copy-mode`](#flash-copy-mode-default-word)                       | Choose the default copy mode                 |
| [`@flash-copy-range-selection`](#flash-copy-range-selection-default-on)   | Enable two-endpoint range selection          |
| [`@flash-copy-mode-switch-key`](#flash-copy-mode-switch-key-default-)     | Temporarily use the other copy mode          |
| [`@flash-copy-range-copy-mode`](#flash-copy-range-copy-mode-default-word) | Choose word or precise range boundaries      |
| [`@flash-copy-debug`](DEBUGGING.md#enabling-or-disabling-debug-mode)      | Enable debug logging                         |

### Prompt

| Option                                                                                      | Description                                                |
| ------------------------------------------------------------------------------------------- | ---------------------------------------------------------- |
| [`@flash-copy-prompt-position`](#flash-copy-prompt-position-default-bottom)                 | Controls where the prompt is positioned in the pane window |
| [`@flash-copy-prompt-indicator`](#flash-copy-prompt-indicator-default-)                     | Customises the prompt indicator                            |
| [`@flash-copy-prompt-colour`](#flash-copy-prompt-colour-default-0331m---bold)               | Customises the prompt indicator colour                     |
| [`@flash-copy-prompt-placeholder-text`](#flash-copy-prompt-placeholder-text-default-search) | Customises prompt placeholder text                         |
| [`@flash-copy-idle-timeout`](#flash-copy-idle-timeout-default-15)                           | Idle timeout in seconds before auto-exit                   |
| [`@flash-copy-idle-warning`](#flash-copy-idle-warning-default-5)                            | Seconds before timeout to show warning in prompt           |

### Matched text and labels

| Option                                                                                                                      | Description                                                                           |
| --------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------- |
| [`@flash-copy-label-characters`](#flash-copy-label-characters-default-asdfghjklqwertyuiopzxcvbnmasdfghjklqwertyuiopzxcvbnm) | Customise the characters that can be used as labels                                   |
| [`@flash-copy-highlight-colour`](#flash-copy-highlight-colour-default-033133m---bold-yellow)                                | Customises the colour used to highlight the matched portion of text in search results |
| [`@flash-copy-label-colour`](#flash-copy-label-colour-default-033132m---bold-green)                                         | Customises the colour used for match labels                                           |
| [`@flash-copy-range-marker-fg-colour`](#flash-copy-range-marker-fg-colour-default-03330m---black)                           | Customises the foreground of the pinned first range endpoint                          |
| [`@flash-copy-range-marker-bg-colour`](#flash-copy-range-marker-bg-colour-default-03345m---magenta)                         | Customises the background of the pinned first range endpoint                          |

---

### `@flash-copy-bind-key` (default: `F`)

Customise the key binding to activate tmux-flash-copy.

The default option value is `F`, which tmux displays as Shift+F. Combined with your tmux prefix, the default key sequence is `<prefix> F`.

```bash
# Change the key binding to Ctrl+F
set -g @flash-copy-bind-key "C-f"

# Or use Alt+F
set -g @flash-copy-bind-key "M-f"
```

### `@flash-copy-bind-key-mode` (default: `prefix`)

Controls which tmux key table contains the activation binding:

- `prefix`: Activate the plugin with `<prefix>` followed by `@flash-copy-bind-key`.
- `root`: Activate the plugin by pressing `@flash-copy-bind-key` directly, without the tmux prefix.

Values other than `prefix` or `root` fall back to `prefix`. A root-table binding takes precedence over the same key being sent to applications running inside tmux.

```bash
# Launch tmux-flash-copy without pressing the tmux prefix first
set -g @flash-copy-bind-key-mode "root"
```

### `@flash-copy-word-separators`

Customise the characters that define word boundaries.

The plugin determines word separators in this order:

1. Use `@flash-copy-word-separators` when it is configured.
2. Otherwise, use tmux's built-in `word-separators` window option.

This allows you to control what constitutes a "word" for the plugin. This is particularly useful when working with configuration strings like `#{@variable_name}` where you want `@` and `}` to be word boundaries.

```bash
# Use custom word separators (overrides tmux's word-separators)
set -g @flash-copy-word-separators ' ()":,;<>~!@#$%^&*|+=[]{}?`'

# To add single quote to the separators
set -ag @flash-copy-word-separators "'"
```

### `@flash-copy-case-sensitive` (default: `off`)

Controls whether search is case-sensitive or case-insensitive.

- `on` or `true`: Search is case-sensitive (e.g., `Test` will not match `test`)
- `off` or `false`: Search is case-insensitive, ignoring case differences (default behaviour)

```bash
# Enable case-sensitive search
set -g @flash-copy-case-sensitive "on"
```

### `@flash-copy-reverse-search` (default: `on`)

Controls the direction of label assignment when searching:

- `on` or `true`: Labels are assigned from bottom to top
- `off` or `false`: Labels are assigned from top to bottom

Setting to `off` is useful if you have your `@flash-copy-prompt-position` at the top of the screen. This means matches are assigned closer to your prompt.

```bash
# Switch to top-to-bottom search
set -g @flash-copy-reverse-search "off"
```

### `@flash-copy-auto-paste` (default: `on`)

Controls whether the auto-paste modifier (semicolon and colon keys) is enabled.

- `on` or `true`: Auto-paste modifier is enabled (default). Pressing `;` (semicolon) or `:` (colon) activates the auto-paste mode, allowing you to copy and automatically paste selected text.
- `off` or `false`: Auto-paste modifier is disabled. The `;` (semicolon) and `:` (colon) keys work as regular characters in search queries instead of being reserved for the modifier.

```bash
# Disable auto-paste modifier (semicolon and colon work in searches)
set -g @flash-copy-auto-paste "off"
```

### `@flash-copy-range-selection` (default: `on`)

Controls whether range copying and copy-mode switching are enabled.

- `on` or `true`: Range copying and the configured mode-switch key are available.
- `off` or `false`: Range copying is disabled, word mode is used, and the mode-switch key is available for normal searches.

```bash
# Disable range selection and make comma searchable in the first search
set -g @flash-copy-range-selection "off"
```

### `@flash-copy-mode` (default: `word`)

Chooses the copy mode used when the plugin launches.

- `word`: Selecting a match copies its word. Use the mode-switch key before selecting to start a range.
- `range`: The first selection pins a range endpoint. Use the mode-switch key before selecting to perform a one-off word copy.

```bash
# Start in range mode
set -g @flash-copy-mode "range"
```

### `@flash-copy-mode-switch-key` (default: `,`)

Sets the single printable character that makes the first selection use the copy mode opposite to `@flash-copy-mode`. The key cannot be `;` or `:` while auto-paste is enabled. Invalid values fall back to comma.

The key is reserved before the first selection. Once the first range endpoint is pinned, it becomes searchable during the second search.

```bash
# Use backslash as the mode-switch key
set -g @flash-copy-mode-switch-key "\\"
```

### `@flash-copy-range-copy-mode` (default: `word`)

Controls how the two range endpoints are expanded when copying.

- `word`: Include the separator-defined word at each endpoint and everything between them.
- `precise`: Include the complete search query at each endpoint and everything between them.

```bash
# Use matched query boundaries instead of whole endpoint words
set -g @flash-copy-range-copy-mode "precise"
```

### `@flash-copy-prompt-position` (default: `bottom`)

Controls where the prompt is positioned in the pane window.

- `bottom`: Prompt is displayed at the bottom (default)
- `top`: Prompt is displayed at the top

This is independent of the `@flash-copy-reverse-search` setting, allowing you to combine any desired configuration.

```bash
# Place prompt at the top of the popup
set -g @flash-copy-prompt-position "top"
```

### `@flash-copy-prompt-indicator` (default: `>`)

Customises the prompt indicator or string displayed before the search input.

- Default: A single `>` character
- Can be set to any string (e.g., `>>>`, `❯`, `$`, `λ`)

```bash
# Use a different prompt character
set -g @flash-copy-prompt-indicator "❯"

# Use multiple characters as prompt
set -g @flash-copy-prompt-indicator ">>>"
```

### `@flash-copy-prompt-colour` (default: `\033[1m` - bold)

Customises the ANSI colour code applied to the prompt indicator. This allows you to style the prompt with different colours and formatting (bold, dim, etc.).

- Default: `\033[1m` (bold)
- Accepts any valid ANSI colour code (see [ANSI colour codes](#ansi-colour-codes) section below)
- The colour applies only to the prompt indicator, not the search input

```bash
# Use bold red for the prompt
set -g @flash-copy-prompt-colour "\033[1;31m"

# Use bold cyan for the prompt
set -g @flash-copy-prompt-colour "\033[1;36m"

# Use non-bold yellow for the prompt
set -g @flash-copy-prompt-colour "\033[0;33m"
```

### `@flash-copy-prompt-placeholder-text` (default: `search...`)

Customises the ghost text that appears in the prompt input when it's empty.

- If set to any string: Shows that string as dimmed placeholder text
- If set to empty string (`""`): Disables placeholder text entirely

The placeholder text automatically disappears when you start typing.

```bash
# Use custom placeholder
set -g @flash-copy-prompt-placeholder-text "Type to search..."

# Disable placeholder text
set -g @flash-copy-prompt-placeholder-text ""
```

### `@flash-copy-idle-timeout` (default: `15`)

Controls the idle timeout in seconds before the popup automatically exits.

- Default: `15` seconds
- Minimum: `1` second (values less than 1 are ignored)
- Set to a higher value if you need more time to make your selection

When no user input is detected for the specified duration, tmux-flash-copy will automatically exit to prevent indefinitely blocking the terminal.

```bash
# Extend idle timeout to 30 seconds
set -g @flash-copy-idle-timeout "30"
```

### `@flash-copy-idle-warning` (default: `5`)

Controls when the idle timeout warning appears, measured in seconds before the timeout.

- Default: `5` seconds (warning appears 5 seconds before timeout)
- Minimum: `0` seconds (negative values are treated as `0`)
- Must be less than `@flash-copy-idle-timeout` for a warning to appear
- If set equal to or greater than `@flash-copy-idle-timeout`, no warning will be displayed

```bash
# Show warning 10 seconds before timeout (at 20s if timeout=30s)
set -g @flash-copy-idle-timeout "30"
set -g @flash-copy-idle-warning "10"

# Show warning very late, only 2 seconds before timeout
set -g @flash-copy-idle-warning "2"

# Disable warning by setting equal to timeout
set -g @flash-copy-idle-timeout "15"
set -g @flash-copy-idle-warning "15"  # No warning will appear
```

**Note**: Any keypress resets the idle timer back to zero, so actively searching or typing will prevent timeout.

### `@flash-copy-label-characters` (default: `asdfghjklqwertyuiopzxcvbnmASDFGHJKLQWERTYUIOPZXCVBNM`)

Customises the ordered list of characters used as match labels. Provide a string of characters in the order you want them to be assigned. If left unset the plugin uses the default label set inspired by [flash.nvim](https://github.com/folke/flash.nvim).

Labels are guaranteed not to exist as a continuation of the search pattern.
Each custom label must be a unique visible ASCII character and must not conflict with the
configured mode-switch or auto-paste keys. This guarantees one terminal cell per label across
supported environments. If any label is invalid, the entire custom set is ignored and the
default labels are used.

Examples:

```bash
# Use only lower-case letters as labels
set -g @flash-copy-label-characters "asdfghjklqwertyuiopzxcvbnm"

# Custom order: prioritise hjkl then asdf
set -g @flash-copy-label-characters "hjklasdf..."
```

### `@flash-copy-highlight-colour` (default: `\033[1;33m` - bold yellow)

Customises the ANSI colour code used to highlight the matched portion of text in search results.

- Default: `\033[1;33m` (bold yellow)
- Accepts any valid ANSI colour code (see [ANSI colour codes](#ansi-colour-codes) section below)

```bash
# Use bold red for highlighting
set -g @flash-copy-highlight-colour "\033[1;31m"
```

### `@flash-copy-label-colour` (default: `\033[1;32m` - bold green)

Customises the ANSI colour code used for match labels (the keyboard shortcut indicator).

- Default: `\033[1;32m` (bold green)
- Accepts any valid ANSI colour code (see [ANSI colour codes](#ansi-colour-codes) section below)

```bash
# Use bold cyan for labels
set -g @flash-copy-label-colour "\033[1;36m"
```

### `@flash-copy-range-marker-fg-colour` (default: `\033[30m` - black)

Customises the ANSI foreground colour used for the pinned first range endpoint.

```bash
# Use white text for the pinned range marker
set -g @flash-copy-range-marker-fg-colour "\033[37m"
```

### `@flash-copy-range-marker-bg-colour` (default: `\033[45m` - magenta)

Customises the ANSI background colour used for the pinned first range endpoint. The range-mode prompt cue uses the normal prompt colour.

```bash
# Use a cyan background for the pinned range marker
set -g @flash-copy-range-marker-bg-colour "\033[46m"
```

## ANSI colour codes

Common ANSI colour codes.

- `\033[1;31m` - Bold red
- `\033[1;32m` - Bold green
- `\033[1;33m` - Bold yellow
- `\033[1;34m` - Bold blue
- `\033[1;35m` - Bold magenta
- `\033[1;36m` - Bold cyan
- `\033[1;37m` - Bold white
- `\033[0;31m` - Red (non-bold)
- `\033[0;32m` - Green (non-bold)

## Related documentation

- [README](../README.md)
- [Clipboard implementation](CLIPBOARD.md)
- [Debugging guide](DEBUGGING.md)
- [Testing guide](TESTING.md)
- [Release guide](RELEASING.md)
