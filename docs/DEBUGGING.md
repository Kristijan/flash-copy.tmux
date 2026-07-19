# Debugging guide

This document explains how to enable and use the debugging features in tmux-flash-copy to troubleshoot issues.

## Table of contents

- [Enabling or disabling debug mode](#enabling-or-disabling-debug-mode)
  - [Enable debug mode](#enable-debug-mode)
  - [Disable debug mode](#disable-debug-mode)
- [Debug log location](#debug-log-location)
- [Visual debug indicator](#visual-debug-indicator)
- [Idle timeout](#idle-timeout)
- [What gets logged](#what-gets-logged)
  - [1. Session header](#1-session-header)
  - [2. Configuration settings](#2-configuration-settings)
  - [3. tmux environment](#3-tmux-environment)
  - [4. Pane layout (ASCII art)](#4-pane-layout-ascii-art)
  - [5. Search activity](#5-search-activity)
  - [6. User actions](#6-user-actions)
- [Common issues and what to look for](#common-issues-and-what-to-look-for)
  - [Issue: Clipboard not working](#issue-clipboard-not-working)
  - [Issue: No matches found](#issue-no-matches-found)
  - [Issue: Popup not appearing or mispositioned](#issue-popup-not-appearing-or-mispositioned)
  - [Issue: Labels not appearing](#issue-labels-not-appearing)
  - [Issue: Performance problems](#issue-performance-problems)
- [Reporting issues](#reporting-issues)
- [Related documentation](#related-documentation)

## Enabling or disabling debug mode

### Enable debug mode

Add the following to your `~/.tmux.conf`:

```bash
# Enable debug logging
set -g @flash-copy-debug "on"
```

After adding this, reload your tmux configuration:

```bash
tmux source ~/.tmux.conf
```

Or restart tmux entirely.

### Disable debug mode

```bash
# Disable debug logging
set -g @flash-copy-debug "off"
```

Then reload:

```bash
tmux source ~/.tmux.conf
```

Or restart tmux entirely.

## Debug log location

- **Path**: `~/.tmux-flash-copy-debug.log`
- **Max size**: 5 MB per file
- **Rotation**: Keeps 2 backup files (`.log`, `.log.1`, `.log.2`)
- **Total storage**: ~15 MB maximum

The log automatically rotates when it reaches 5MB, ensuring it doesn't consume excessive disk space.

- `~/.tmux-flash-copy-debug.log` - Current log
- `~/.tmux-flash-copy-debug.log.1` - Previous log (after rotation)
- `~/.tmux-flash-copy-debug.log.2` - Older log (after second rotation)

## Visual debug indicator

When debug mode is active, you'll see a persistent indicator on the right side of the search prompt:

```text
───────────────────────────────────────────────────
> search...                          !! DEBUG ON !!
```

This serves as a visual reminder that debug logging is enabled.

## Idle timeout

To prevent the popup from blocking indefinitely if left open, tmux-flash-copy includes an **automatic idle timeout**:

### Behaviour

- **Timeout duration**: 15 seconds of inactivity (configurable via `@flash-copy-idle-timeout`)
- **Warning**: Appears 5 seconds before timeout (at 10 seconds elapsed, configurable via `@flash-copy-idle-warning`)
- **Auto-exit**: At 15 seconds, the popup closes automatically (same as pressing ESC)

The `@flash-copy-idle-warning` value specifies how many seconds before the timeout the warning appears. With the defaults (`timeout=15`, `warning=5`), it appears after 10 seconds.

### Warning Message

When the warning appears, you'll see a yellow countdown message:

```text
───────────────────────────────────────────────────
> search...              Idle, terminating in 5s...
```

The warning takes priority over the debug indicator when both would be displayed.

### Why This Exists

The timeout serves as a safety mechanism to:

1. **Prevent indefinite blocking**: If the popup is left open accidentally, it won't block tmux forever
2. **Free resources**: Closes the popup if you walk away from your computer
3. **Handle edge cases**: Catches rare bugs that might cause the UI to hang

### Timeout Coordination

The implementation uses two coordinated timeouts:

- **Child process (interactive UI)**: Configurable self-timeout (default: 15 seconds) with configurable warning (default: 5 seconds before timeout, appearing at 10 seconds elapsed)
- **Parent process**: Child timeout + 5 seconds safety margin to catch unexpected hangs

The child process always exits gracefully at the configured timeout. The parent's timeout is a backup that should never be reached under normal circumstances.

**Note**: The warning value is relative to the timeout, not an absolute time. If `@flash-copy-idle-warning` is equal to or greater than `@flash-copy-idle-timeout`, no warning is displayed.

### Debug Logging

When debug mode is enabled, timeout events are logged:

```text
[2026-01-08T11:28:10.123] Showing idle timeout warning
[2026-01-08T11:28:15.456] Idle timeout (15s) - auto-exiting
```

### User Control

You can always exit before the timeout by:

- Pressing **ESC** to cancel
- Pressing **Ctrl+C** to cancel
- Selecting text with a label key

### Configuration

Customise the idle timeout with these tmux options:

```bash
# Set idle timeout to 30 seconds (default: 15)
set -g @flash-copy-idle-timeout "30"

# Show warning 10 seconds before timeout (default: 5)
set -g @flash-copy-idle-warning "10"
```

See [Configuration options](CONFIGURATION.md#configuration-options) for more details.

## What gets logged

The debug log captures information about each tmux-flash-copy session:

### 1. Session header

```text
[2026-01-05T10:30:45.123] ================================================================================
[2026-01-05T10:30:45.123]   TMUX-FLASH-COPY DEBUG SESSION STARTED
[2026-01-05T10:30:45.123] ================================================================================
[2026-01-05T10:30:45.124] Python: 3.14.2 (final) (/usr/local/bin/python3)
[2026-01-05T10:30:45.125] Tmux: tmux 3.6a
[2026-01-05T10:30:45.125] Pane ID: %0
[2026-01-05T10:30:45.125] Log file: /Users/username/.tmux-flash-copy-debug.log
```

### 2. Configuration settings

```text
[2026-01-05T10:30:45.126] ================================================================================
[2026-01-05T10:30:45.126]   Configuration Settings
[2026-01-05T10:30:45.126] ================================================================================
[2026-01-05T10:30:45.126] reverse_search: True
[2026-01-05T10:30:45.126] case_sensitive: False
[2026-01-05T10:30:45.126] word_separators: ' -_.,;:!?/\()[]{}
<>~!@#$%^&*|+=[]{}?\'"'
[2026-01-05T10:30:45.126] prompt_placeholder_text: search...
[2026-01-05T10:30:45.126] highlight_colour: \033[1;33m
[2026-01-05T10:30:45.126] label_colour: \033[1;32m
[2026-01-05T10:30:45.126] prompt_position: bottom
[2026-01-05T10:30:45.126] prompt_indicator: >
[2026-01-05T10:30:45.126] prompt_colour: \033[1m
```

### 3. tmux environment

```text
[2026-01-05T10:30:45.130] ================================================================================
[2026-01-05T10:30:45.130]   Tmux Environment
[2026-01-05T10:30:45.130] ================================================================================
[2026-01-05T10:30:45.131] Sessions (1):
[2026-01-05T10:30:45.131]   - main (5 windows) ← ACTIVE
[2026-01-05T10:30:45.132] Windows (3):
[2026-01-05T10:30:45.132]   - [0] zsh (1 panes)
[2026-01-05T10:30:45.133]   - [1] vim (2 panes) ← ACTIVE
[2026-01-05T10:30:45.134] Panes (2):
[2026-01-05T10:30:45.134]   - %0: 80x24 (vim) ← ACTIVE
[2026-01-05T10:30:45.135]   - %1: 80x24 (zsh)
```

### 4. Pane layout (ASCII art)

```text
[2026-01-05T10:30:45.136] ================================================================================
[2026-01-05T10:30:45.136]   Pane Layout (ASCII)
[2026-01-05T10:30:45.136] ================================================================================
[2026-01-05T10:30:45.137] ┌────────────────────────────────┬───────────────────────────────┐
[2026-01-05T10:30:45.137] │                                │                               │
[2026-01-05T10:30:45.137] │        %0 80x24                │        %1 80x24               │
[2026-01-05T10:30:45.137] │                                │                               │
[2026-01-05T10:30:45.137] └────────────────────────────────┴───────────────────────────────┘
```

### 5. Search activity

```text
[2026-01-05T10:30:47.456] Search query: 'test' -> 12 matches
[2026-01-05T10:30:47.457]   [a] line 5, col 10: 'testing'
[2026-01-05T10:30:47.457]   [s] line 8, col 23: 'test'
[2026-01-05T10:30:47.457]   [d] line 10, col 5: 'tests'
[2026-01-05T10:30:47.458]   [f] line 12, col 15: 'test-case'
[2026-01-05T10:30:47.458]   ... (first 10 matches shown)
```

### 6. User actions

```text
[2026-01-05T10:30:49.123] User selected label 'a': 'testing'
[2026-01-05T10:30:49.125] Clipboard: Success via tmux OSC52
```

## Common issues and what to look for

### Issue: Clipboard not working

**What to check**:

```bash
grep -i clipboard ~/.tmux-flash-copy-debug.log | tail -5
```

**Expected output**:

- `Clipboard: Success via tmux OSC52` (best case)
- `Clipboard: Success via pbcopy (macOS)` (macOS fallback)
- `Clipboard: Success via xclip (Linux)` (Linux fallback)
- `Clipboard: Success via tmux buffer (tmux-only)` (last resort)

**Problem indicators**:

- `Clipboard: Failed - not in tmux` - tmux environment not detected
- No clipboard messages at all - clipboard code may not be running

**Solution**: See [Clipboard implementation](CLIPBOARD.md) for detailed troubleshooting.

### Issue: No matches found

**What to check**:

```bash
grep "Search query" ~/.tmux-flash-copy-debug.log | tail -5
```

**Expected output**:

```text
Search query: 'test' -> 12 matches
```

**Problem indicators**:

- `Search query: 'test' -> 0 matches` - no words matched your search

**Possible causes**:

- Search query doesn't match any visible text
- Word separators configuration doesn't match your content
- Case-sensitive search enabled when it should be off

**Solution**:

1. Check `word_separators` in the configuration section of the log
2. Try adjusting `@flash-copy-word-separators` in your `~/.tmux.conf`
3. Toggle `@flash-copy-case-sensitive` setting

### Issue: Popup not appearing or mispositioned

**What to check**:

```bash
grep -A 20 "Pane Layout" ~/.tmux-flash-copy-debug.log | tail -25
```

Look for pane dimensions and positions.

**Problem indicators**:

- Incorrect pane dimensions
- Unusual pane positions

**Solution**:

1. Check tmux version: `tmux -V` (should be 3.2+)
2. Verify pane dimensions match your expectations

### Issue: Labels not appearing

**What to check**:

```bash
grep "Search query" ~/.tmux-flash-copy-debug.log | tail -20
```

**Expected output**:

```text
[a] line 5, col 10: 'testing'
[s] line 8, col 23: 'test'
```

**Problem indicators**:

- No labels in brackets: `[ ] line 5, col 10: 'testing'`
- Very few labels when many matches exist

**Possible causes**:

- Label characters exhausted (too many matches)
- Label characters conflict with search query or matched words

**Solution**:

1. Refine your search query to reduce matches
2. Customise label characters in `src/search_interface.py`

### Issue: Performance problems

**What to check**:
Look at timestamps between actions:

```bash
grep "\[" ~/.tmux-flash-copy-debug.log | tail -20
```

**Problem indicators**:

- Large time gaps between search updates
- Slow response to user input

**Possible causes**:

- Very large pane content
- Complex word separator patterns
- Many matches

**Solution**:

1. Use more specific search queries
2. Simplify custom word separators

## Reporting issues

[Report issues via GitHub](https://github.com/Kristijan/flash-copy.tmux/issues)

## Related documentation

- [README](../README.md)
- [Configuration](CONFIGURATION.md)
- [Clipboard implementation](CLIPBOARD.md)
- [Testing guide](TESTING.md)
- [Release guide](RELEASING.md)
