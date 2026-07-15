# Testing guide

This document explains how to set up your local development environment and run tests for tmux-flash-copy.

## Table of contents

- [Prerequisites](#prerequisites)
  - [Required tools](#required-tools)
- [Setting up the development environment](#setting-up-the-development-environment)
  - [1. Clone the repository](#1-clone-the-repository)
  - [2. Create a virtual environment](#2-create-a-virtual-environment)
  - [3. Activate the virtual environment](#3-activate-the-virtual-environment)
  - [4. Install dependencies](#4-install-dependencies)
  - [5. Verify the installation](#5-verify-the-installation)
- [Running tests](#running-tests)
  - [Run all tests](#run-all-tests)
  - [Run tests with a coverage report](#run-tests-with-a-coverage-report)
  - [Run specific test files](#run-specific-test-files)
  - [Run specific test classes](#run-specific-test-classes)
  - [Run specific test functions](#run-specific-test-functions)
- [Code-quality checks](#code-quality-checks)
  - [1. Type checking with `ty`](#1-type-checking-with-ty)
  - [2. Linting with `ruff`](#2-linting-with-ruff)
  - [3. Formatting with `ruff`](#3-formatting-with-ruff)
- [Test structure](#test-structure)
- [Continuous integration (CI)](#continuous-integration-ci)
  - [GitHub Actions workflow](#github-actions-workflow)
  - [Running CI checks locally](#running-ci-checks-locally)
- [Related documentation](#related-documentation)

## Prerequisites

### Required tools

1. **Python 3.9+**

   ```bash
   python3 --version
   # Should be 3.9 or higher
   ```

2. **uv**

   Development commands use `uv` to manage the virtual environment, install dependencies, and run `pytest`, `ty`, and `ruff`.

3. **Git**

   ```bash
   git --version
   ```

## Setting up the development environment

### 1. Clone the repository

```bash
git clone https://github.com/Kristijan/flash-copy.tmux.git
cd flash-copy.tmux
```

### 2. Create a virtual environment

```bash
# Create a new virtual environment
uv venv

# This creates a .venv directory in the project root
```

### 3. Activate the virtual environment

```bash
source .venv/bin/activate
```

### 4. Install dependencies

Install dependencies:

```bash
uv sync --locked --all-extras --dev
```

This installs:

- The `tmux-flash-copy` package in editable mode
- Test dependencies:
  - `pytest-cov`
  - `pytest`
  - `ruff`
  - `ty`

### 5. Verify the installation

```bash
# Check that pytest is available
uv run pytest --version

# Check Python can import the package
uv run python -c "from src.clipboard import Clipboard; print('Success!')"
```

## Running tests

### Run all tests

```bash
uv run pytest
```

Pytest displays each test name as it runs and generates terminal and HTML coverage reports using the settings in `pyproject.toml`.

### Run tests with a coverage report

```bash
# Terminal report
uv run pytest --cov=src --cov-report=term-missing
```

The HTML report is written to `htmlcov/`.

### Run specific test files

```bash
# Run only clipboard tests
uv run pytest tests/test_clipboard.py
```

### Run specific test classes

```bash
# Run all tests in TestClipboard class
uv run pytest tests/test_clipboard.py::TestClipboard -v
```

### Run specific test functions

```bash
# Run a single test
uv run pytest tests/test_clipboard.py::TestClipboard::test_copy_success_with_osc52 -v

# Run multiple specific tests
uv run pytest tests/test_clipboard.py::TestClipboard::test_copy_success_with_osc52 \
              tests/test_clipboard.py::TestClipboard::test_copy_fallback_to_pbcopy_on_macos -v
```

## Code-quality checks

Use these tools to check code quality:

### 1. Type checking with `ty`

```bash
uv run ty check
```

### 2. Linting with `ruff`

```bash
uv run ruff check
```

### 3. Formatting with `ruff`

```bash
uv run ruff format --check
```

## Test structure

Tests live under `tests/` and follow pytest's `test_*.py` naming convention.

| Test file                   | Focus                                                     |
| --------------------------- | --------------------------------------------------------- |
| `test_ansi_utils.py`        | ANSI styles, control characters, and position mapping     |
| `test_auto_paste.py`        | Auto-paste configuration and interaction                  |
| `test_clipboard.py`         | OSC52 and platform clipboard fallbacks                    |
| `test_config.py`            | Configuration defaults, parsing, and tmux option loading  |
| `test_debug_logger.py`      | Debug logging, environment details, and log rotation      |
| `test_idle_timeout.py`      | Timeout warnings, exits, resets, and logging              |
| `test_label_placement.py`   | Width-preserving label placement                          |
| `test_pane_capture.py`      | Pane capture and dimensions                               |
| `test_popup_ui.py`          | Popup arguments, errors, timeouts, and cleanup            |
| `test_range_interactive.py` | Two-stage range-selection interaction                     |
| `test_range_selection.py`   | Range boundaries, extraction, and endpoint rules          |
| `test_search_interface.py`  | Search matching and label assignment                      |
| `test_utils.py`             | Subprocess and tmux utility functions                     |

## Continuous integration (CI)

### GitHub Actions workflow

Tests run automatically on every pull request to `main`.

**Workflow**: `.github/workflows/plugin-testing.yml`

**What it runs**:

1. Tests against Python 3.9, 3.10, 3.11, 3.12, 3.13, and 3.14
2. Type checking: `uv run ty check --output-format=github`
3. Linting: `uv run ruff check --output-format=github`
4. Formatting: `uv run ruff format --check`
5. Tests with coverage: `uv run pytest --cov=src --cov-report=term-missing --cov-report=xml`
6. Uploads coverage to Codecov (Python 3.14 only)

### Running CI checks locally

Simulate CI environment locally:

```bash
# Create a fresh virtual environment
rm -rf .venv
uv venv
source .venv/bin/activate

# Install the project
uv sync --locked --all-extras --dev

# Run all CI checks
uv run ty check --output-format=github
uv run ruff check --output-format=github
uv run ruff format --check
uv run pytest --cov=src --cov-report=term-missing --cov-report=xml

# If all checks pass, your PR is ready.
```

## Related documentation

- [README](../README.md)
- [Configuration](CONFIGURATION.md)
- [Clipboard implementation](CLIPBOARD.md)
- [Debugging guide](DEBUGGING.md)
- [Release guide](RELEASING.md)
- **pytest**: [https://docs.pytest.org/](https://docs.pytest.org/)
- **ruff**: [https://docs.astral.sh/ruff/](https://docs.astral.sh/ruff/)
- **ty**: [https://docs.astral.sh/ty/](https://docs.astral.sh/ty/)
- **uv**: [https://docs.astral.sh/uv](https://docs.astral.sh/uv)
