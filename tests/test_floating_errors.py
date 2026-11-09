"""Failure outcomes and recovery through the real floating-search boundary."""

import shutil
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor

import pytest

from src.floating_pane import FloatingPane, supports_floating_panes
from src.popup_protocol import PopupExitCode
from tests.test_floating_pane import attached_tmux as attached_tmux


@pytest.mark.parametrize(
    ("version", "supported"),
    [
        ("3.7", False),
        ("3.7z", False),
        ("3.8", True),
        ("3.8a", True),
        ("3.8z", True),
        ("3.9", True),
        ("3.10", True),
        ("4.0", True),
        ("next-3.8", False),
        ("3.8-next", False),
        ("3.8-custom", False),
        ("3.8.1", False),
        ("3.8ab", False),
        ("", False),
    ],
)
def test_only_stable_supported_server_versions_enable_floating_panes(version, supported):
    assert supports_floating_panes(version) is supported


def pane_ids(tmux):
    return set(tmux("list-panes", "-a", "-F", "#{pane_id}").splitlines())


def assert_source_reusable(tmux, source, client, original_panes):
    """A fresh invocation must acquire the same source lock and finish normally."""
    with FloatingPane(source, client) as search:
        assert not search.reused
        assert search.run(["/bin/sh", "-c", "exit 7"]) == 7
    assert pane_ids(tmux) == original_panes
    assert "@flash-copy-" not in tmux("show-options", "-p", "-t", source)


@pytest.mark.parametrize("pane_id", ["", "0", "test:0.0", "%-1", "%1; kill-server", "%999999"])
def test_invalid_or_missing_source_does_not_touch_other_panes(attached_tmux, pane_id):
    tmux, source, client = attached_tmux
    original_panes = pane_ids(tmux)

    with (
        pytest.raises(RuntimeError, match="Source pane .* no longer exists"),
        FloatingPane(pane_id, client),
    ):
        pytest.fail("an invalid source must not enter the context")

    assert pane_ids(tmux) == original_panes
    assert_source_reusable(tmux, source, client, original_panes)


def test_missing_original_source_releases_its_lock_after_enter_failure(attached_tmux):
    tmux, source, client = attached_tmux
    original_panes = pane_ids(tmux)
    missing_source = tmux("new-window", "-d", "-P", "-F", "#{pane_id}", "sleep 30")
    orphan = tmux("new-pane", "-d", "-E", "-P", "-F", "#{pane_id}", "-t", source)
    tmux("set-option", "-p", "-t", orphan, "@flash-copy-source-pane", missing_source)
    tmux("kill-pane", "-t", missing_source)

    for _ in range(2):
        with (
            pytest.raises(
                RuntimeError, match=f"Original source pane {missing_source} no longer exists"
            ),
            FloatingPane(orphan, client),
        ):
            pytest.fail("an orphaned helper must not become a search source")

    assert pane_ids(tmux) == original_panes | {orphan}
    tmux("kill-pane", "-t", orphan)
    assert pane_ids(tmux) == original_panes
    assert_source_reusable(tmux, source, client, original_panes)


@pytest.mark.parametrize("stale_search", ["not-a-pane", "%999999"])
def test_stale_missing_search_reference_is_cleared_on_enter(attached_tmux, stale_search):
    tmux, source, client = attached_tmux
    original_panes = pane_ids(tmux)
    tmux("set-option", "-p", "-t", source, "@flash-copy-search-pane", stale_search)

    with FloatingPane(source, client) as search:
        assert not search.reused
        assert tmux("display-message", "-p", "-t", source, "#{@flash-copy-search-pane}") == ""
        assert search.run(["/bin/sh", "-c", "exit 0"]) == 0

    assert_source_reusable(tmux, source, client, original_panes)


@pytest.mark.parametrize("ownership", ["unowned", "foreign", "nonfloating"])
def test_stale_reference_never_kills_an_unrelated_pane(attached_tmux, ownership):
    tmux, source, client = attached_tmux
    command = "split-window" if ownership == "nonfloating" else "new-pane"
    unrelated = tmux(command, "-d", "-P", "-F", "#{pane_id}", "-t", source, "sleep 30")
    tmux("set-option", "-p", "-t", source, "@flash-copy-search-pane", unrelated)
    tmux(
        "set-option",
        "-p",
        "-t",
        unrelated,
        "@flash-copy-source-pane",
        "%999999" if ownership == "foreign" else source,
    )
    if ownership != "unowned":
        tmux("set-option", "-p", "-t", unrelated, "@flash-copy-owner", "abandoned-search")
    original_panes = pane_ids(tmux)

    with FloatingPane(source, client) as search:
        assert not search.reused
        assert unrelated in pane_ids(tmux)
        assert search.run(["/bin/sh", "-c", "exit 0"]) == 0

    assert_source_reusable(tmux, source, client, original_panes)


@pytest.mark.parametrize("stale_state", ["resized", "dead"])
def test_abandoned_owned_floating_pane_is_removed_before_replacement(attached_tmux, stale_state):
    tmux, source, client = attached_tmux
    original_panes = pane_ids(tmux)
    helper = tmux(
        "new-pane", "-d", "-E", "-P", "-F", "#{pane_id}", "-t", source, "-x", "20", "-y", "5"
    )
    tmux("set-option", "-p", "-t", helper, "@flash-copy-source-pane", source)
    tmux("set-option", "-p", "-t", helper, "@flash-copy-owner", "abandoned-search")
    tmux("set-option", "-p", "-t", source, "@flash-copy-search-pane", helper)
    if stale_state == "dead":
        tmux("set-option", "-p", "-t", helper, "remain-on-exit", "on")
        tmux("respawn-pane", "-t", helper, "/bin/sh", "-c", "exit 0")
        deadline = time.monotonic() + 3
        while tmux("display-message", "-p", "-t", helper, "#{pane_dead}") != "1":
            assert time.monotonic() < deadline, "abandoned command did not exit"
            time.sleep(0.02)

    with FloatingPane(source, client) as search:
        assert not search.reused
        assert helper not in pane_ids(tmux)
        assert search.run(["/bin/sh", "-c", "exit 0"]) == 0

    assert_source_reusable(tmux, source, client, original_panes)


@pytest.mark.parametrize(
    ("command", "expected"),
    [
        (["/bin/sh", "-c", "exit 129"], 129),
        (["/flash-copy-test/no-such-command"], 127),
    ],
)
def test_child_execution_errors_are_not_converted_to_cancellation(attached_tmux, command, expected):
    tmux, source, client = attached_tmux
    original_panes = pane_ids(tmux)

    with FloatingPane(source, client) as search:
        assert search.run(command) == expected

    assert_source_reusable(tmux, source, client, original_panes)


def test_external_search_pane_kill_is_cancellation_not_child_exit_129(attached_tmux):
    tmux, source, client = attached_tmux
    original_panes = pane_ids(tmux)

    def close_search():
        tmux("wait-for", "floating-errors-child-ready")
        helper = tmux("display-message", "-p", "-t", source, "#{@flash-copy-search-pane}")
        assert helper and helper != source
        tmux("kill-pane", "-t", helper)

    with ThreadPoolExecutor(max_workers=1) as executor:
        closing = executor.submit(close_search)
        with FloatingPane(source, client) as search:
            status = search.run(
                ["/bin/sh", "-c", "tmux wait-for -S floating-errors-child-ready; exec sleep 30"]
            )
        closing.result(timeout=5)

    assert status == PopupExitCode.CANCEL
    assert_source_reusable(tmux, source, client, original_panes)


def test_helper_configuration_failure_preserves_panes_and_unlocks_source(
    attached_tmux, monkeypatch
):
    tmux, source, client = attached_tmux
    original_panes = pane_ids(tmux)
    real_run = subprocess.run

    def reject_configuration(command, **kwargs):
        if "set-option" in command and "synchronize-panes" in command:
            raise subprocess.CalledProcessError(1, command, stderr="configuration rejected")
        return real_run(command, **kwargs)

    # Inject a command failure, not fabricated successful tmux responses. The
    # helper is real and must be removed even though configuration never finished.
    with monkeypatch.context() as failure:
        failure.setattr(subprocess, "run", reject_configuration)
        with pytest.raises(subprocess.CalledProcessError), FloatingPane(source, client) as search:
            search.run(["/bin/sh", "-c", "exit 0"])

    assert pane_ids(tmux) == original_panes
    assert_source_reusable(tmux, source, client, original_panes)


def test_missing_configured_launcher_preserves_failure_and_releases_source(
    attached_tmux, tmp_path, monkeypatch
):
    tmux, source, client = attached_tmux
    original_panes = pane_ids(tmux)
    binary = shutil.which("tmux")
    assert binary is not None
    (tmp_path / "tmux").symlink_to(binary)
    # The real tmux client is still available, but its execution PATH cannot
    # resolve the wrapper's `sh`. tmux forwards this PATH to the respawned child.
    with monkeypatch.context() as environment:
        environment.setenv("PATH", str(tmp_path))
        with (
            pytest.raises(subprocess.CalledProcessError) as failure,
            FloatingPane(source, client) as search,
        ):
            search.run(["/bin/sh", "-c", "exit 0"])
        assert failure.value.returncode == 1

    assert pane_ids(tmux) == original_panes
    assert_source_reusable(tmux, source, client, original_panes)


def test_run_requires_an_entered_context(attached_tmux):
    tmux, source, client = attached_tmux
    original_panes = pane_ids(tmux)

    with pytest.raises(RuntimeError, match="requires a new, entered source context"):
        FloatingPane(source, client).run(["/bin/sh", "-c", "exit 0"])

    assert pane_ids(tmux) == original_panes


def test_empty_command_releases_the_entered_source_lock(attached_tmux):
    tmux, source, client = attached_tmux
    original_panes = pane_ids(tmux)

    with (
        pytest.raises(ValueError, match="must not be empty"),
        FloatingPane(source, client) as search,
    ):
        search.run([])

    assert_source_reusable(tmux, source, client, original_panes)
