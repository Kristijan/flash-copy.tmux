# tmux-flash-copy Optimization Plan

**Date**: 2026-01-08
**Current Test Coverage**: 93%
**Target Coverage**: 95%+

This document outlines recommended changes to improve performance, simplify code, and increase test coverage for the tmux-flash-copy plugin.

---

## Table of Contents

1. [Quick Wins (High Impact, Low Effort)](#quick-wins)
2. [Performance Improvements](#performance-improvements)
3. [Code Simplification](#code-simplification)
4. [Test Coverage Improvements](#test-coverage-improvements)
5. [Implementation Priority](#implementation-priority)

---

## Quick Wins

These changes provide high value with minimal effort and risk.

### QW-1: Remove Duplicate `escape_for_char_class()` Function
**File**: `src/search_interface.py`
**Lines**: 99-104 and 130-135
**Effort**: 5 minutes
**Impact**: High (removes code duplication in hot path)

**Issue**: The same function is defined twice as a nested function within `SearchInterface` class methods.

**Solution**: Extract as a private class method or module-level function:
```python
@staticmethod
def _escape_for_char_class(s: str) -> str:
    """Escape special characters for use in regex character class."""
    s = s.replace("\\", "\\\\")
    s = s.replace("]", "\\]")
    if s.startswith("^"):
        s = "^" + s[1:].replace("^", "\\^")
    return s
```

Then use `self._escape_for_char_class()` in both places (lines 104 and 135).

**Lines Saved**: 6 lines

---

### QW-2: Reuse `ConfigLoader.parse_bool()` in Interactive Script
**File**: `bin/tmux-flash-copy-interactive.py`
**Lines**: 758-761, 767
**Effort**: 10 minutes
**Impact**: Medium (DRY principle, consistency)

**Issue**: Boolean parsing logic is duplicated 4 times:
```python
args.reverse_search.lower() in ("true", "1", "yes", "on")
args.case_sensitive.lower() in ("true", "1", "yes", "on")
args.debug_enabled.lower() in ("true", "1", "yes", "on")
args.auto_paste.lower() in ("true", "1", "yes", "on")
```

**Solution**: Import and reuse the existing function:
```python
from src.config import ConfigLoader

config = FlashCopyConfig(
    reverse_search=ConfigLoader.parse_bool(args.reverse_search),
    case_sensitive=ConfigLoader.parse_bool(args.case_sensitive),
    # ... etc
    debug_enabled=ConfigLoader.parse_bool(args.debug_enabled),
    auto_paste_enable=ConfigLoader.parse_bool(args.auto_paste),
)
```

**Lines Saved**: 4 expressions replaced with reusable function calls

---

### QW-3: Fix Unused `_line_plain` Parameter
**File**: `bin/tmux-flash-copy-interactive.py`
**Line**: 381
**Effort**: 5 minutes
**Impact**: Low (code clarity)

**Issue**: Variable is unpacked but immediately discarded:
```python
for line_idx, (line, _line_plain) in enumerate(zip(lines, lines_plain)):
    # ... later at line 406
    plain_line = lines_plain[line_idx]  # Re-indexed instead of using _line_plain
```

**Solution**: Either use the unpacked value consistently, or remove it:
```python
# Option 1: Use the unpacked value
for line_idx, (line, line_plain) in enumerate(zip(lines, lines_plain)):
    # ... use line_plain directly instead of lines_plain[line_idx]

# Option 2: Don't unpack it
for line_idx, line in enumerate(lines):
    plain_line = lines_plain[line_idx]
```

**Recommendation**: Option 1 (use unpacked value) for clarity.

---

### QW-4: Add Error Path Tests for `popup_ui.py`
**File**: `tests/test_popup_ui.py`
**Effort**: 30 minutes
**Impact**: High (increases coverage from 76% → ~90%)

**Issue**: Three exception paths are not covered:
- Line 190, 198-202: `subprocess.CalledProcessError` when reading tmux buffer
- Lines 219-221: `subprocess.TimeoutExpired` when popup times out
- Lines 223-226: Generic `Exception` handling

**Solution**: Add three new test methods:
```python
def test_popup_ui_buffer_read_failure(self):
    """Test handling of failed buffer read."""
    # Mock subprocess.run to succeed for popup but fail for buffer read

def test_popup_ui_timeout_expired(self):
    """Test handling of popup timeout."""
    # Mock subprocess.run to raise TimeoutExpired

def test_popup_ui_generic_exception(self):
    """Test handling of unexpected exceptions."""
    # Mock subprocess.run to raise generic Exception
```

**Coverage Increase**: 76% → 90%+

---

### QW-5: Add Fallback Path Tests for `clipboard.py`
**File**: `tests/test_clipboard.py`
**Effort**: 30 minutes
**Impact**: Medium (increases coverage from 92% → 98%+)

**Issue**: Missing coverage for:
- Lines 80, 84, 90, 94: Platform-specific fallback success paths with logging
- Line 127: Auto-paste exception handling

**Solution**: Add tests for each fallback method with logger enabled:
```python
def test_copy_pbcopy_success_with_logging(self):
    """Test pbcopy fallback with debug logging."""

def test_copy_xclip_success_with_logging(self):
    """Test xclip fallback with debug logging."""

def test_copy_xsel_success_with_logging(self):
    """Test xsel fallback with debug logging."""

def test_copy_all_methods_fail_with_logging(self):
    """Test all clipboard methods failing with debug logging."""

def test_auto_paste_exception_handling(self):
    """Test auto-paste failure is caught silently."""
```

**Coverage Increase**: 92% → 98%+

---

## Performance Improvements

### PERF-1: Batch Configuration Reads
**File**: `src/config.py`
**Lines**: 49-60, 75-86, 241-273
**Effort**: 2 hours
**Impact**: High (reduces startup time by ~500ms-1s)

**Issue**: Each configuration option spawns a separate `tmux show-option` subprocess (~13 calls total). This adds significant startup latency.

**Current Behavior**:
```python
# Each line spawns a subprocess:
reverse_search = ConfigLoader.get_bool("@flash-copy-reverse-search", default=True)
case_sensitive = ConfigLoader.get_bool("@flash-copy-case-sensitive", default=False)
word_separators = ConfigLoader.get_word_separators()
# ... 10 more calls
```

**Solution Option A**: Batch read all options in a single tmux call:
```python
@staticmethod
def _read_all_options() -> dict[str, str]:
    """Read all flash-copy options in a single subprocess call."""
    result = subprocess.run(
        [
            "tmux", "show-options", "-g",
            "-t", "global",
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=5,
    )

    options = {}
    if result.returncode == 0:
        for line in result.stdout.splitlines():
            if line.startswith("@flash-copy-"):
                parts = line.split(" ", 1)
                if len(parts) == 2:
                    key = parts[0]
                    value = parts[1].strip('"')
                    options[key] = value
    return options
```

**Solution Option B**: Add caching with `functools.lru_cache`:
```python
@staticmethod
@lru_cache(maxsize=128)
def _read_tmux_option_cached(option_name: str, default: str = "") -> str:
    # ... existing implementation
```

**Recommendation**: Implement Option A for maximum performance gain.

**Time Saved**: ~500ms-1s per plugin invocation

---

### PERF-2: Eliminate Redundant Pane Capture
**Files**: `bin/tmux-flash-copy.py`, `bin/tmux-flash-copy-interactive.py`
**Lines**: tmux-flash-copy.py:61, tmux-flash-copy-interactive.py:750-751
**Effort**: 1 hour
**Impact**: Medium (saves ~50-100ms per invocation)

**Issue**: Pane content is captured twice:
1. Parent process: `PaneCapture(pane_id).capture_pane()`
2. Child process: `PaneCapture(args.pane_id).capture_pane()`

**Solution**: Pass pane content via tmux buffer instead of re-capturing:
```python
# In parent (tmux-flash-copy.py):
capture = PaneCapture(pane_id)
pane_content = capture.capture_pane()

# Write to temporary buffer
subprocess.run(
    ["tmux", "set-buffer", "-b", "__tmux_flash_copy_pane_content__", pane_content],
    check=True,
)

# In child (tmux-flash-copy-interactive.py):
# Read from buffer instead of re-capturing
result = subprocess.run(
    ["tmux", "show-buffer", "-b", "__tmux_flash_copy_pane_content__"],
    capture_output=True,
    text=True,
    check=True,
)
pane_content = result.stdout

# Clean up buffer
subprocess.run(
    ["tmux", "delete-buffer", "-b", "__tmux_flash_copy_pane_content__"],
    check=False,
)
```

**Alternative**: Pass via stdin to child process (more complex but avoids buffer).

**Time Saved**: ~50-100ms per invocation

---

### PERF-3: Optimize String Operations in Display Loop
**File**: `bin/tmux-flash-copy-interactive.py`
**Lines**: 204-210 (_dim_coloured_line)
**Effort**: 1 hour
**Impact**: Low-Medium (improves rendering by ~5-10%)

**Issue**: Multiple string replace operations and concatenations in hot path (called for every non-matching line).

**Current Code**:
```python
def _dim_coloured_line(self, line: str) -> str:
    dimmed = line.replace(AnsiStyles.RESET, AnsiStyles.RESET + AnsiStyles.DIM)
    if not dimmed.startswith(AnsiStyles.DIM):
        dimmed = AnsiStyles.DIM + dimmed
    if not dimmed.endswith(AnsiStyles.RESET):
        dimmed = dimmed + AnsiStyles.RESET
    return dimmed
```

**Solution**: Use list accumulation and join:
```python
def _dim_coloured_line(self, line: str) -> str:
    """Apply dim style to a line, preserving existing ANSI codes."""
    parts = []

    if not line.startswith(AnsiStyles.DIM):
        parts.append(AnsiStyles.DIM)

    # Replace RESET with RESET+DIM to maintain dimming through the line
    parts.append(line.replace(AnsiStyles.RESET, AnsiStyles.RESET + AnsiStyles.DIM))

    if not line.endswith(AnsiStyles.RESET):
        parts.append(AnsiStyles.RESET)

    return "".join(parts)
```

**Rendering Improvement**: ~5-10% for 40-line panes

---

### PERF-4: Cache ANSI Position Calculations
**File**: `bin/tmux-flash-copy-interactive.py`
**Lines**: 304-358 (_display_line_with_matches)
**Effort**: 2 hours
**Impact**: Medium (reduces render time by ~2-3%)

**Issue**: `AnsiUtils.map_position_to_coloured()` is called multiple times for the same positions within the same line.

**Solution**: Pre-calculate all position mappings once per line:
```python
def _display_line_with_matches(self, line_idx: int, display_line: str) -> str:
    # ... existing setup ...

    # Build position mapping cache for this line
    position_cache = {}

    def get_coloured_pos(plain_pos: int) -> int:
        if plain_pos not in position_cache:
            position_cache[plain_pos] = AnsiUtils.map_position_to_coloured(
                display_line, plain_pos
            )
        return position_cache[plain_pos]

    # Use get_coloured_pos() instead of AnsiUtils.map_position_to_coloured()
    # throughout the function
```

**Render Improvement**: ~2-3% for lines with multiple matches

---

### PERF-5: Consolidate Subprocess Helper Methods
**File**: `src/config.py`
**Lines**: 37-60, 63-86
**Effort**: 30 minutes
**Impact**: Low (code quality, slight perf improvement)

**Issue**: `_read_tmux_option()` and `_read_tmux_window_option()` have duplicated subprocess logic.

**Solution**: Extract common pattern:
```python
@staticmethod
def _run_tmux_command(args: list[str], default: str = "") -> str:
    """Run a tmux command and return stdout or default on error."""
    try:
        result = subprocess.run(
            args,
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
        return default
    except (subprocess.SubprocessError, OSError):
        return default

@staticmethod
def _read_tmux_option(option_name: str, default: str = "") -> str:
    return ConfigLoader._run_tmux_command(
        ["tmux", "show-option", "-gv", option_name],
        default,
    )

@staticmethod
def _read_tmux_window_option(option_name: str, default: str = "") -> str:
    return ConfigLoader._run_tmux_command(
        ["tmux", "show-option", "-gwv", option_name],
        default,
    )
```

**Lines Saved**: ~20 lines of duplicated code

---

## Code Simplification

### SIMP-1: Move Debug Utilities to Separate Module
**File**: `src/debug_logger.py`
**Lines**: 153-395 (helper functions)
**Effort**: 1 hour
**Impact**: Low (code organization)

**Issue**: Debug-only helper functions (~140 lines) are mixed with the DebugLogger class, bloating the file.

**Solution**: Create `src/debug_utils.py` and move these functions:
- `get_python_version()`
- `get_tmux_version()`
- `get_current_session_name()`
- `get_current_window_index()`
- `get_tmux_sessions()`
- `get_tmux_windows()`
- `get_tmux_panes()`
- `get_tmux_panes_with_positions()`
- `draw_pane_layout()`

Update `bin/tmux-flash-copy.py` to import from new module.

**Benefit**: Better separation of concerns, smaller debug_logger.py

---

### SIMP-2: Split Complex `_display_line_with_matches()` Function
**File**: `bin/tmux-flash-copy-interactive.py`
**Lines**: 271-367 (97 lines, 4+ levels of nesting)
**Effort**: 2 hours
**Impact**: High (maintainability, testability)

**Issue**: This function does too much:
1. Get matches for the line
2. Process matches right-to-left
3. Calculate ANSI positions
4. Handle label insertion/replacement
5. Apply highlighting
6. Handle edge cases

**Solution**: Split into smaller methods:
```python
def _display_line_with_matches(self, line_idx: int, display_line: str) -> str:
    """Display a line with highlighted matches and labels."""
    matches = self._get_matches_for_line(line_idx)
    if not matches:
        return display_line

    # Process matches right-to-left to maintain positions
    for match in reversed(matches):
        display_line = self._insert_match_on_line(display_line, match, line_idx)

    return display_line

def _insert_match_on_line(
    self, line: str, match: SearchMatch, line_idx: int
) -> str:
    """Insert a single match (label + highlight) into a line."""
    word_start, word_end = self._get_word_boundaries(match, line_idx)
    coloured_start = AnsiUtils.map_position_to_coloured(line, word_start)

    if match.label:
        line = self._insert_or_replace_label(line, match, word_start, coloured_start)

    line = self._apply_highlight_to_match(line, match, word_start)

    return line

def _insert_or_replace_label(
    self, line: str, match: SearchMatch, word_start: int, coloured_start: int
) -> str:
    """Insert label before match or replace following character."""
    # Label insertion logic (currently lines 304-358)
    pass

def _apply_highlight_to_match(
    self, line: str, match: SearchMatch, word_start: int
) -> str:
    """Apply highlighting to the matched portion."""
    # Highlighting logic
    pass
```

**Benefit**: Each function is <30 lines, single responsibility, easier to test

---

### SIMP-3: Avoid Configuration Duplication
**Files**: `src/config.py`, `bin/tmux-flash-copy-interactive.py`
**Effort**: 3 hours
**Impact**: Medium (maintenance, consistency)

**Issue**: Configuration is loaded in parent process, then reconstructed in child process from command-line arguments. Adding new config options requires updating both places.

**Current Flow**:
1. Parent: `config = ConfigLoader.load_all_flash_copy_config()` (src/config.py:241-273)
2. Parent: Serialize to command-line args (src/popup_ui.py:106-152)
3. Child: Parse args (bin/tmux-flash-copy-interactive.py:684-730)
4. Child: Reconstruct config (bin/tmux-flash-copy-interactive.py:757-772)

**Solution Option A**: Serialize config to JSON and pass as single argument:
```python
# In parent (popup_ui.py):
import json
config_json = json.dumps(asdict(self.config))

popup_cmd = [
    "tmux", "display-popup",
    # ...
    str(interactive_script),
    "--config", config_json,
]

# In child (tmux-flash-copy-interactive.py):
import json
from dataclasses import asdict
config_dict = json.loads(args.config)
config = FlashCopyConfig(**config_dict)
```

**Solution Option B**: Pass via tmux buffer (similar to PERF-2).

**Benefit**: Single source of truth, easier to add new config options

---

### SIMP-4: Simplify Empty String to None Conversion
**File**: `src/config.py`
**Line**: 268-270
**Effort**: 5 minutes
**Impact**: Low (code clarity)

**Issue**: Implicit type conversion via `or`:
```python
label_characters=(
    ConfigLoader.get_string("@flash-copy-label-characters", default="") or None
),
```

**Solution**: Make it explicit:
```python
label_characters=ConfigLoader.get_string(
    "@flash-copy-label-characters", default=""
) if ConfigLoader.get_string("@flash-copy-label-characters", default="") else None,
```

Or better, create a dedicated method:
```python
@staticmethod
def get_optional_string(option_name: str) -> Optional[str]:
    """Get string option, returning None if empty or not set."""
    value = ConfigLoader.get_string(option_name, default="")
    return value if value else None

# Usage:
label_characters=ConfigLoader.get_optional_string("@flash-copy-label-characters"),
```

---

## Test Coverage Improvements

### TEST-1: Add Error Path Tests for `popup_ui.py`
**See QW-4 above** (Quick Win)

---

### TEST-2: Add Clipboard Fallback Tests
**See QW-5 above** (Quick Win)

---

### TEST-3: Test Malformed ANSI Sequences
**File**: `tests/test_ansi_utils.py`
**Effort**: 15 minutes
**Impact**: Low (edge case coverage)

**Missing Coverage**: Line 90 in `ansi_utils.py` (malformed escape sequence)

**Solution**: Add test:
```python
def test_map_position_to_coloured_malformed_ansi():
    """Test position mapping with malformed ANSI sequence (no 'm' terminator)."""
    # "\x1b[31" is missing the 'm' terminator
    coloured_text = "\x1b[31Hello"
    result = AnsiUtils.map_position_to_coloured(coloured_text, 3)
    # Should handle gracefully without crashing
    assert isinstance(result, int)
```

**Coverage Increase**: 98% → 100% for ansi_utils.py

---

### TEST-4: Test Word Separator Edge Cases
**File**: `tests/test_config.py`
**Effort**: 20 minutes
**Impact**: Low (error handling coverage)

**Missing Coverage**: Lines 232-236 in `config.py` (exception handling in word separator parsing)

**Solution**: Add tests:
```python
def test_get_word_separators_invalid_escape_sequence():
    """Test handling of invalid escape sequences in word-separators."""
    # Mock invalid escape sequence that causes ValueError
    with patch.object(
        ConfigLoader, "_read_tmux_window_option", return_value='"\\x999"'
    ):
        result = ConfigLoader.get_word_separators()
        # Should fall back to extracting between quotes
        assert result == "\\x999"

def test_get_word_separators_malformed_syntax():
    """Test handling of malformed quotes in word-separators."""
    with patch.object(
        ConfigLoader, "_read_tmux_window_option", return_value='invalid syntax'
    ):
        result = ConfigLoader.get_word_separators()
        # Should return default
        assert result == ConfigLoader.DEFAULT_WORD_SEPARATORS
```

**Coverage Increase**: 94% → 96% for config.py

---

### TEST-5: Test Label Assignment Exhaustion
**File**: `tests/test_search_interface.py`
**Effort**: 30 minutes
**Impact**: Medium (edge case coverage)

**Missing Coverage**: Behavior when all 52 labels are exhausted (more than 52 matches)

**Solution**: Add test:
```python
def test_label_assignment_exhaustion():
    """Test label assignment when there are more matches than available labels."""
    # Create content with 60 words
    content = " ".join([f"word{i}" for i in range(60)])
    interface = SearchInterface(content, case_sensitive=False)

    # Search for "word" - should match all 60 words
    matches = interface.search("word")

    # First 52 should have labels
    labeled_matches = [m for m in matches if m.label]
    assert len(labeled_matches) == 52

    # Remaining 8 should have no labels
    unlabeled_matches = [m for m in matches if not m.label]
    assert len(unlabeled_matches) == 8
```

---

### TEST-6: Test Empty Pane Content in InteractiveUI
**File**: `tests/test_idle_timeout.py` (or new test file)
**Effort**: 20 minutes
**Impact**: Low (edge case coverage)

**Missing Coverage**: Interactive UI behavior with empty pane

**Solution**: Add test:
```python
def test_interactive_ui_with_empty_pane():
    """Test that UI handles empty pane content gracefully."""
    pane_content = ""
    dimensions = {"width": 80, "height": 24}
    config = FlashCopyConfig()

    ui = InteractiveUI(
        pane_id="%0",
        pane_content=pane_content,
        dimensions=dimensions,
        config=config,
    )

    # Should not crash, should show empty display
    output = ui._build_search_bar_output()
    assert isinstance(output, str)

    # Search should return no matches
    ui.search_query = "test"
    matches = ui.search_interface.search(ui.search_query)
    assert len(matches) == 0
```

---

### TEST-7: Test Idle Timeout During Active Search
**File**: `tests/test_idle_timeout.py`
**Effort**: 30 minutes
**Impact**: Medium (integration scenario)

**Missing Coverage**: Timeout behavior while search is active

**Solution**: Add test:
```python
def test_search_functionality_during_timeout_warning():
    """Test that search still works while timeout warning is displayed."""
    # Mock UI with timeout warning active
    mock_ui.start_time = 0.0
    mock_ui.timeout_warning_shown = True
    mock_time.return_value = 11.0  # Warning active (15-11=4s remaining)

    # User types search query
    mock_ui.search_query = "test"
    matches = mock_ui.search_interface.search(mock_ui.search_query)

    # Search should still work
    assert len(matches) > 0

    # Warning should still be displayed
    output = mock_ui._build_search_bar_output()
    assert "Idle, terminating in" in output
```

---

### TEST-8: Test Complex ANSI Scenarios
**File**: `tests/test_label_placement.py` (or new integration test)
**Effort**: 45 minutes
**Impact**: Medium (integration scenario)

**Missing Coverage**: Lines with multiple interleaved ANSI codes

**Solution**: Add integration test:
```python
def test_label_placement_with_complex_ansi():
    """Test label placement on line with multiple ANSI codes."""
    # Line with multiple colors and styles
    pane_content = (
        "\x1b[1;31mRed\x1b[0m normal \x1b[1;32mGreen\x1b[0m "
        "\x1b[4munderline\x1b[0m text"
    )

    interface = SearchInterface(pane_content, case_sensitive=False)
    matches = interface.search("text")

    assert len(matches) == 1
    assert matches[0].label is not None

    # Verify label can be inserted without breaking ANSI codes
    # (Integration test would verify rendering)
```

---

### TEST-9: Extract InteractiveUI to src/ for Direct Testing
**Files**: `bin/tmux-flash-copy-interactive.py` → `src/interactive_ui.py`
**Effort**: 4 hours
**Impact**: High (enables direct unit testing)

**Issue**: `InteractiveUI` class is defined in `bin/` script and can't be easily unit tested.

**Solution**:
1. Move `InteractiveUI` class to `src/interactive_ui.py`
2. Keep `bin/tmux-flash-copy-interactive.py` as thin entry point
3. Add comprehensive unit tests for InteractiveUI methods

**Benefit**: Can test display logic, input handling, and state management directly without subprocess mocking.

---

## Implementation Priority

### Phase 1: Quick Wins (1-2 days)
High impact, low effort changes that can be done immediately.

1. ✅ **QW-1**: Remove duplicate `escape_for_char_class()` (5 min)
2. ✅ **QW-2**: Reuse `ConfigLoader.parse_bool()` (10 min)
3. ✅ **QW-3**: Fix unused `_line_plain` parameter (5 min)
4. ✅ **QW-4**: Add error path tests for `popup_ui.py` (30 min)
5. ✅ **QW-5**: Add fallback tests for `clipboard.py` (30 min)
6. ✅ **TEST-3**: Test malformed ANSI sequences (15 min)
7. ✅ **TEST-4**: Test word separator edge cases (20 min)
8. ✅ **PERF-5**: Consolidate subprocess helpers (30 min)
9. ✅ **SIMP-4**: Simplify empty string conversion (5 min)

**Total Time**: ~3 hours
**Coverage Improvement**: 93% → 95%+
**Code Reduction**: ~30 lines

---

### Phase 2: Performance Optimizations (3-5 days)
Measurable performance improvements with moderate effort.

1. ✅ **PERF-1**: Batch configuration reads (2 hrs) - **Saves 500ms-1s startup time**
2. ✅ **PERF-2**: Eliminate redundant pane capture (1 hr) - **Saves 50-100ms**
3. ✅ **PERF-3**: Optimize display loop string ops (1 hr) - **5-10% render improvement**
4. ✅ **PERF-4**: Cache ANSI position calculations (2 hrs) - **2-3% render improvement**

**Total Time**: ~6 hours
**Performance Improvement**: ~600ms faster startup, ~7-13% faster rendering

---

### Phase 3: Code Quality (5-7 days)
Larger refactoring for better maintainability.

1. ✅ **SIMP-1**: Move debug utilities to separate module (1 hr)
2. ✅ **SIMP-2**: Split complex `_display_line_with_matches()` (2 hrs)
3. ✅ **SIMP-3**: Avoid configuration duplication (3 hrs)
4. ✅ **TEST-9**: Extract InteractiveUI to src/ (4 hrs)

**Total Time**: ~10 hours
**Code Quality**: Better separation of concerns, easier to test

---

### Phase 4: Additional Test Coverage (2-3 days)
Complete test coverage for edge cases.

1. ✅ **TEST-5**: Label assignment exhaustion (30 min)
2. ✅ **TEST-6**: Empty pane content (20 min)
3. ✅ **TEST-7**: Timeout during search (30 min)
4. ✅ **TEST-8**: Complex ANSI scenarios (45 min)

**Total Time**: ~2 hours
**Coverage Improvement**: 95% → 97%+

---

## Testing Requirements

After each change, run:
```bash
uv run ty check && uv run ruff check && uv run ruff format --check
uv run pytest --cov=src --cov-report=term-missing
```

**Success Criteria**:
- ✅ All tests pass
- ✅ Coverage maintained or improved (never goes down)
- ✅ No type errors
- ✅ No linting errors
- ✅ Code formatted correctly

---

## Estimated Total Impact

**Time Investment**: ~21 hours across 4 phases
**Performance Gains**:
- 600ms faster startup time (PERF-1, PERF-2)
- 7-13% faster rendering (PERF-3, PERF-4)

**Code Quality**:
- ~50 lines removed (duplication eliminated)
- Better separation of concerns
- Easier to test and maintain

**Test Coverage**:
- 93% → 97%+ total coverage
- All error paths covered
- Edge cases tested

---

## Notes

- Each phase can be implemented independently
- Phase 1 (Quick Wins) should be done first for immediate improvements
- Phase 2 (Performance) has the highest user-visible impact
- Phase 3 (Code Quality) pays long-term maintenance dividends
- Phase 4 (Testing) ensures robustness

**Recommendation**: Start with Phase 1 (Quick Wins) to get familiar with the changes, then proceed to Phase 2 (Performance) for maximum user benefit.
