"""Interaction tests for the two-stage range selection flow."""

import importlib.util
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.ansi_utils import AnsiUtils
from src.config import FlashCopyConfig
from src.popup_protocol import PopupExitCode


def load_interactive_module():
    script_path = Path(__file__).resolve().parents[1] / "bin" / "tmux-flash-copy-interactive.py"
    spec = importlib.util.spec_from_file_location("range_interactive_ui", str(script_path))
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Failed to load module spec for {script_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_interactive_ui():
    return load_interactive_module().InteractiveUI


def run_keys(monkeypatch, ui, keys):
    """Run the public input loop with terminal and tmux output captured."""
    selections = []
    key_iter = iter(keys)
    monkeypatch.setattr(ui, "_get_single_char", lambda: next(key_iter))
    monkeypatch.setattr(ui, "_display_content", lambda: None)
    monkeypatch.setattr(ui, "_reset_terminal", lambda: None)
    monkeypatch.setattr(ui, "_clear_screen", lambda: None)

    def save_result(text, should_paste=False):
        selections.append((text, should_paste))
        raise SystemExit

    monkeypatch.setattr(ui, "_save_result", save_result)
    with pytest.raises(SystemExit):
        ui.run()
    return selections


def test_selection_is_written_to_the_parent_result_channel():
    interactive_cls = load_interactive_ui()
    result_buffer = "__tmux_flash_copy_result_invocation__"
    ui = interactive_cls(
        "pane",
        "hello world",
        {},
        FlashCopyConfig(),
        result_buffer=result_buffer,
    )

    with (
        patch("subprocess.run", return_value=MagicMock(returncode=0)) as mock_run,
        pytest.raises(SystemExit) as exit_info,
    ):
        ui._save_result("hello", should_paste=True)

    assert exit_info.value.code == 10
    mock_run.assert_called_once_with(
        ["tmux", "set-buffer", "-b", result_buffer, "hello"],
        check=True,
        capture_output=True,
    )


def test_cancel_exits_without_creating_a_result_buffer():
    interactive_cls = load_interactive_ui()
    ui = interactive_cls(
        "pane",
        "hello world",
        {},
        FlashCopyConfig(),
        result_buffer="__tmux_flash_copy_result_invocation__",
    )

    with (
        patch("subprocess.run") as mock_run,
        pytest.raises(SystemExit) as exit_info,
    ):
        ui._save_result("", should_paste=False)

    assert exit_info.value.code == PopupExitCode.CANCEL
    mock_run.assert_not_called()


def test_child_snapshot_read_failure_does_not_recapture_live_pane(monkeypatch):
    module = load_interactive_module()
    monkeypatch.setattr(
        "sys.argv",
        [
            "tmux-flash-copy-interactive.py",
            "--pane-id",
            "%1",
            "--pane-content-buffer",
            "__snapshot__",
            "--result-buffer",
            "__result__",
        ],
    )
    monkeypatch.setattr(
        module.subprocess,
        "run",
        MagicMock(side_effect=subprocess.CalledProcessError(1, ["tmux", "show-buffer"])),
    )
    capture_live_pane = MagicMock(return_value="newer live content")
    monkeypatch.setattr(module.PaneCapture, "capture_pane", capture_live_pane)
    monkeypatch.setattr(module.InteractiveUI, "run", MagicMock())

    with pytest.raises(SystemExit) as exit_info:
        module.main()

    assert exit_info.value.code == 1
    capture_live_pane.assert_not_called()


def test_user_can_select_a_range_with_two_labelled_searches(monkeypatch):
    interactive_cls = load_interactive_ui()
    ui = interactive_cls("pane", "hello world", {}, FlashCopyConfig(reverse_search=False))

    selections = run_keys(monkeypatch, ui, ["h", ",", "a", "w", "s"])

    assert selections == [("hello world", False)]


def test_user_can_use_backslash_as_the_range_selection_key(monkeypatch):
    interactive_cls = load_interactive_ui()
    config = FlashCopyConfig(reverse_search=False, mode_switch_key="\\")
    ui = interactive_cls("pane", "hello world", {}, config)

    selections = run_keys(monkeypatch, ui, ["h", "\\", "a", "w", "s"])

    assert selections == [("hello world", False)]


def test_range_default_selects_two_endpoints_without_mode_switch_key(monkeypatch):
    interactive_cls = load_interactive_ui()
    config = FlashCopyConfig(copy_mode="range", reverse_search=False)
    ui = interactive_cls("pane", "hello world", {}, config)

    selections = run_keys(monkeypatch, ui, ["h", "a", "w", "s"])

    assert selections == [("hello world", False)]


def test_range_default_enter_selects_both_endpoints(monkeypatch):
    interactive_cls = load_interactive_ui()
    config = FlashCopyConfig(copy_mode="range", reverse_search=False)
    ui = interactive_cls("pane", "hello world", {}, config)

    selections = run_keys(monkeypatch, ui, ["h", "\n", "w", "\n"])

    assert selections == [("hello world", False)]


def test_range_default_mode_switch_key_copies_a_word(monkeypatch):
    interactive_cls = load_interactive_ui()
    config = FlashCopyConfig(copy_mode="range", reverse_search=False)
    ui = interactive_cls("pane", "hello world", {}, config)

    selections = run_keys(monkeypatch, ui, ["h", ",", "a"])

    assert selections == [("hello", False)]


def test_range_default_mode_switch_key_and_enter_copy_a_word(monkeypatch):
    interactive_cls = load_interactive_ui()
    config = FlashCopyConfig(copy_mode="range", reverse_search=False)
    ui = interactive_cls("pane", "hello world", {}, config)

    selections = run_keys(monkeypatch, ui, ["h", ",", "\n"])

    assert selections == [("hello", False)]


@pytest.mark.parametrize("modifiers", [(";", ","), (",", ";")])
def test_range_default_mode_switch_key_can_combine_with_auto_paste(monkeypatch, modifiers):
    interactive_cls = load_interactive_ui()
    config = FlashCopyConfig(copy_mode="range", reverse_search=False)
    ui = interactive_cls("pane", "hello world", {}, config)

    selections = run_keys(monkeypatch, ui, ["h", *modifiers, "a"])

    assert selections == [("hello", True)]


def test_repeated_mode_switch_key_remains_armed(monkeypatch):
    interactive_cls = load_interactive_ui()
    config = FlashCopyConfig(copy_mode="range", reverse_search=False)
    ui = interactive_cls("pane", "hello world", {}, config)

    selections = run_keys(monkeypatch, ui, ["h", ",", ",", "a"])

    assert selections == [("hello", False)]


def test_backspace_clears_mode_switch_and_restores_range_default(monkeypatch):
    interactive_cls = load_interactive_ui()
    config = FlashCopyConfig(copy_mode="range", reverse_search=False)
    ui = interactive_cls("pane", "hello world", {}, config)

    selections = run_keys(monkeypatch, ui, ["h", ",", "\x7f", "h", "a", "w", "s"])

    assert selections == [("hello world", False)]


@pytest.mark.parametrize(
    ("initial_keys", "editing_key"),
    [(("h",), "\x15"), (("h", "e"), "\x17")],
)
def test_editing_commands_clear_mode_switch_and_restore_range_default(
    monkeypatch, initial_keys, editing_key
):
    interactive_cls = load_interactive_ui()
    config = FlashCopyConfig(copy_mode="range", reverse_search=False)
    ui = interactive_cls("pane", "hello world", {}, config)

    keys = [*initial_keys, ",", editing_key, "h", "a", "w", "s"]
    selections = run_keys(monkeypatch, ui, keys)

    assert selections == [("hello world", False)]


def test_range_default_launch_uses_normal_prompt_until_first_endpoint(monkeypatch):
    interactive_cls = load_interactive_ui()
    config = FlashCopyConfig(copy_mode="range", reverse_search=False)
    ui = interactive_cls("pane", "hello world", {}, config)
    monkeypatch.setattr(ui, "_display_content", lambda: None)

    initial_prompt = AnsiUtils.strip_ansi_codes(ui._build_search_bar_output())
    ui._update_search("h")
    ui._select_match(ui.current_matches[0])
    second_endpoint_prompt = AnsiUtils.strip_ansi_codes(ui._build_search_bar_output())

    assert initial_prompt.startswith("> search...")
    assert second_endpoint_prompt.startswith("range >")


def test_user_can_select_a_precise_range_when_configured(monkeypatch):
    interactive_cls = load_interactive_ui()
    config = FlashCopyConfig(reverse_search=False, range_copy_mode="precise")
    ui = interactive_cls("pane", "hello world", {}, config)

    selections = run_keys(monkeypatch, ui, ["h", "e", ",", "a", "w", "s"])

    assert selections == [("hello w", False)]


def test_second_endpoint_can_be_above_the_first_and_auto_paste_at_completion(monkeypatch):
    interactive_cls = load_interactive_ui()
    ui = interactive_cls("pane", "hello world", {}, FlashCopyConfig(reverse_search=False))

    selections = run_keys(monkeypatch, ui, ["w", ",", "a", "h", ";", "s"])

    assert selections == [("hello world", True)]


def test_auto_paste_armed_before_first_endpoint_does_not_carry_into_range(monkeypatch):
    interactive_cls = load_interactive_ui()
    ui = interactive_cls("pane", "hello world", {}, FlashCopyConfig(reverse_search=False))

    selections = run_keys(monkeypatch, ui, ["h", ";", ",", "a", "w", "s"])

    assert selections == [("hello world", False)]


def test_enter_selects_the_first_match_in_both_range_stages(monkeypatch):
    interactive_cls = load_interactive_ui()
    ui = interactive_cls("pane", "hello world", {}, FlashCopyConfig(reverse_search=False))

    selections = run_keys(monkeypatch, ui, ["h", ",", "\n", "w", "\n"])

    assert selections == [("hello world", False)]


def test_enter_can_select_unlabelled_matches_in_both_range_stages(monkeypatch):
    interactive_cls = load_interactive_ui()
    config = FlashCopyConfig(reverse_search=False, label_characters="a")
    ui = interactive_cls("pane", "alpha omega", {}, config)

    selections = run_keys(monkeypatch, ui, ["l", ",", "\n", "m", "\n"])

    assert selections == [("alpha omega", False)]
    assert ui.active_range is not None
    assert ui.active_range.start.label == "+"


def test_range_key_is_searchable_during_second_stage(monkeypatch):
    interactive_cls = load_interactive_ui()
    ui = interactive_cls("pane", "hello ,target", {}, FlashCopyConfig(reverse_search=False))

    selections = run_keys(monkeypatch, ui, ["h", ",", "a", ",", "s"])

    assert selections == [("hello ,target", False)]


def test_disabling_range_selection_restores_comma_as_search_input(monkeypatch):
    interactive_cls = load_interactive_ui()
    config = FlashCopyConfig(range_selection_enable=False, reverse_search=False)
    ui = interactive_cls("pane", "hello,world", {}, config)

    selections = run_keys(monkeypatch, ui, [",", "\x1b"])

    assert selections == [("", False)]
    assert ui.search_query == ","


def test_disabling_range_selection_forces_word_mode_and_makes_switch_key_searchable(monkeypatch):
    interactive_cls = load_interactive_ui()
    config = FlashCopyConfig(
        copy_mode="range",
        mode_switch_key="\\",
        range_selection_enable=False,
        reverse_search=False,
    )
    ui = interactive_cls("pane", r"hello\\world", {}, config)

    selections = run_keys(monkeypatch, ui, ["\\", "\x1b"])

    assert selections == [("", False)]
    assert config.copy_mode == "word"
    assert ui.active_range is None
    assert ui.search_query == "\\"


def test_escape_cancels_the_entire_plugin_while_range_mode_is_active(monkeypatch):
    interactive_cls = load_interactive_ui()
    ui = interactive_cls("pane", "hello world", {}, FlashCopyConfig(reverse_search=False))

    selections = run_keys(monkeypatch, ui, ["h", ",", "a", "\x1b"])

    assert selections == [("", False)]
    assert ui.active_range is not None


def test_word_range_highlights_the_entire_pinned_endpoint_word(monkeypatch, capsys):
    interactive_cls = load_interactive_ui()
    ui = interactive_cls("pane", "hello world", {}, FlashCopyConfig(reverse_search=False))
    monkeypatch.setattr(ui, "_display_content", lambda: None)
    ui._update_search("h")
    ui._begin_range(ui.current_matches[0])
    ui._update_search("e")

    ui._display_pane_content(["hello world"], ["hello world"], available_height=1)
    rendered_line = capsys.readouterr().err
    search_bar = ui._build_search_bar_output()

    assert AnsiUtils.strip_ansi_codes(rendered_line) == "hello world"
    assert "\033[30m\033[45mhello\033[0m" in rendered_line
    assert AnsiUtils.strip_ansi_codes(search_bar).startswith("range >")
    assert search_bar.startswith(f"{ui.config.prompt_colour}range")


def test_precise_range_highlights_the_complete_pinned_query(monkeypatch, capsys):
    interactive_cls = load_interactive_ui()
    config = FlashCopyConfig(reverse_search=False, range_copy_mode="precise")
    ui = interactive_cls("pane", "hello world", {}, config)
    monkeypatch.setattr(ui, "_display_content", lambda: None)
    ui._update_search("he")
    ui._begin_range(ui.current_matches[0])
    ui._update_search("h")

    ui._display_pane_content(["hello world"], ["hello world"], available_height=1)
    rendered_line = capsys.readouterr().err

    assert AnsiUtils.strip_ansi_codes(rendered_line) == "hello world"
    assert "\033[30m\033[45mhe\033[0m" in rendered_line


def test_pinned_highlight_restores_the_pane_style_after_the_marked_span(monkeypatch):
    interactive_cls = load_interactive_ui()
    ui = interactive_cls("pane", "hello world", {}, FlashCopyConfig(reverse_search=False))
    monkeypatch.setattr(ui, "_display_content", lambda: None)
    ui._update_search("h")
    ui._begin_range(ui.current_matches[0])

    rendered_line = ui._overlay_pinned_endpoint("\033[31mhello world\033[0m", 0, "hello world")

    assert "\033[0m\033[31m world" in rendered_line


def test_precise_pinned_highlight_restores_the_pane_style_after_the_query(monkeypatch):
    interactive_cls = load_interactive_ui()
    config = FlashCopyConfig(reverse_search=False, range_copy_mode="precise")
    ui = interactive_cls("pane", "hello world", {}, config)
    monkeypatch.setattr(ui, "_display_content", lambda: None)
    ui._update_search("he")
    ui._begin_range(ui.current_matches[0])

    rendered_line = ui._overlay_pinned_endpoint("\033[31mhello world\033[0m", 0, "hello world")

    assert "\033[0m\033[31mllo world" in rendered_line
