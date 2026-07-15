"""Interaction tests for the two-stage range selection flow."""

import importlib.util
from pathlib import Path

import pytest

from src.ansi_utils import AnsiUtils
from src.config import FlashCopyConfig


def load_interactive_ui():
    script_path = Path(__file__).resolve().parents[1] / "bin" / "tmux-flash-copy-interactive.py"
    spec = importlib.util.spec_from_file_location("range_interactive_ui", str(script_path))
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Failed to load module spec for {script_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.InteractiveUI


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


def test_user_can_select_a_range_with_two_labelled_searches(monkeypatch):
    interactive_cls = load_interactive_ui()
    ui = interactive_cls("pane", "hello world", {}, FlashCopyConfig(reverse_search=False))

    selections = run_keys(monkeypatch, ui, ["h", ",", "a", "w", "s"])

    assert selections == [("hello world", False)]


def test_user_can_use_backslash_as_the_range_selection_key(monkeypatch):
    interactive_cls = load_interactive_ui()
    config = FlashCopyConfig(reverse_search=False, range_selection_key="\\")
    ui = interactive_cls("pane", "hello world", {}, config)

    selections = run_keys(monkeypatch, ui, ["h", "\\", "a", "w", "s"])

    assert selections == [("hello world", False)]


def test_user_can_select_a_precise_range_when_configured(monkeypatch):
    interactive_cls = load_interactive_ui()
    config = FlashCopyConfig(reverse_search=False, range_copy_mode="precise")
    ui = interactive_cls("pane", "hello world", {}, config)

    selections = run_keys(monkeypatch, ui, ["h", "e", ",", "a", "w", "s"])

    assert selections == [("ello w", False)]


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


def test_precise_range_highlights_the_first_character_that_will_be_copied(monkeypatch, capsys):
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
    assert "\033[30m\033[45me\033[0m" in rendered_line


def test_pinned_highlight_restores_the_pane_style_after_the_marked_span(monkeypatch):
    interactive_cls = load_interactive_ui()
    ui = interactive_cls("pane", "hello world", {}, FlashCopyConfig(reverse_search=False))
    monkeypatch.setattr(ui, "_display_content", lambda: None)
    ui._update_search("h")
    ui._begin_range(ui.current_matches[0])

    rendered_line = ui._overlay_pinned_endpoint("\033[31mhello world\033[0m", 0, "hello world")

    assert "\033[0m\033[31m world" in rendered_line
