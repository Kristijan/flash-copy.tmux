"""Runtime entrypoint outcome tests."""

import importlib.util
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.config import FlashCopyConfig


def load_entrypoint_module():
    script_path = Path(__file__).resolve().parents[1] / "bin" / "tmux-flash-copy.py"
    spec = importlib.util.spec_from_file_location("tmux_flash_copy_entrypoint", script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Failed to load module spec for {script_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_entrypoint_propagates_copy_or_paste_failure(monkeypatch, capsys):
    module = load_entrypoint_module()
    monkeypatch.setattr(module.ConfigLoader, "load_all_flash_copy_config", FlashCopyConfig)

    capture = MagicMock()
    capture.capture_pane.return_value = "visible text"
    monkeypatch.setattr(module, "PaneCapture", MagicMock(return_value=capture))

    popup = MagicMock()
    popup.run.return_value = ("visible", True)
    monkeypatch.setattr(module, "PopupUI", MagicMock(return_value=popup))

    clipboard = MagicMock()
    clipboard.copy_and_paste.return_value = False
    monkeypatch.setattr(module, "Clipboard", MagicMock(return_value=clipboard))

    with pytest.raises(SystemExit) as exit_info:
        module.main("%1", "client-1")

    assert exit_info.value.code == 1
    assert "Clipboard copy/paste operation failed" in capsys.readouterr().err
    module.PopupUI.assert_called_once()
    assert module.PopupUI.call_args.kwargs["client_name"] == "client-1"
    clipboard.copy_and_paste.assert_called_once_with(
        "visible",
        pane_id="%1",
        client_name="client-1",
        auto_paste=True,
        logger=None,
    )
