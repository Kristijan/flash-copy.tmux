"""Tests for the tmux plugin loader and its key binding."""

import os
import subprocess
from pathlib import Path

import pytest


@pytest.fixture
def fake_tmux(tmp_path: Path) -> tuple[Path, Path]:
    """Create a tmux stand-in that records bind-key arguments."""
    executable = tmp_path / "tmux"
    log_file = tmp_path / "tmux-arguments"
    executable.write_text(
        """#!/usr/bin/env bash
if [[ "$1" == "show-option" ]]; then
    case "$3" in
        "@flash-copy-bind-key") printf '%s' "${TEST_BIND_KEY:-}" ;;
        "@flash-copy-bind-key-mode") printf '%s' "${TEST_BIND_KEY_MODE:-}" ;;
    esac
    exit 0
fi
printf '%s\n' "$@" > "${TEST_TMUX_LOG}"
"""
    )
    executable.chmod(0o755)
    return executable, log_file


def load_plugin(
    fake_tmux: tuple[Path, Path],
    *,
    bind_key: str = "",
    bind_key_mode: str = "",
) -> list[str]:
    """Load the plugin with configured options and return the bind-key arguments."""
    executable, log_file = fake_tmux
    project_root = Path(__file__).resolve().parents[1]
    environment = os.environ.copy()
    environment.update(
        {
            "PATH": f"{executable.parent}:{environment['PATH']}",
            "TEST_BIND_KEY": bind_key,
            "TEST_BIND_KEY_MODE": bind_key_mode,
            "TEST_TMUX_LOG": str(log_file),
        }
    )

    subprocess.run(
        ["bash", str(project_root / "tmux-flash-copy.tmux")],
        check=True,
        env=environment,
    )

    return log_file.read_text().splitlines()


@pytest.mark.parametrize(
    ("configured_mode", "expected_table"),
    [
        ("", "prefix"),
        ("prefix", "prefix"),
        ("root", "root"),
        ("invalid", "prefix"),
    ],
)
def test_bind_key_mode_selects_tmux_key_table(
    fake_tmux: tuple[Path, Path],
    configured_mode: str,
    expected_table: str,
):
    arguments = load_plugin(fake_tmux, bind_key_mode=configured_mode)

    assert arguments[:5] == ["bind-key", "-T", expected_table, "F", "run-shell"]


def test_custom_bind_key_preserves_runtime_context(fake_tmux: tuple[Path, Path]):
    arguments = load_plugin(fake_tmux, bind_key="C-f", bind_key_mode="root")
    project_root = Path(__file__).resolve().parents[1]

    assert arguments[:5] == ["bind-key", "-T", "root", "C-f", "run-shell"]
    assert arguments[5] == (
        f'"{project_root}/bin/tmux-flash-copy.py" '
        '--pane-id "#{pane_id}" --client-name "#{client_name}"'
    )
