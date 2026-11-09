"""Search lifecycles observed through real tmux panes and attached clients."""

import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager

import pytest

from src.floating_pane import FloatingPane
from tests.test_floating_pane import attached_tmux as attached_tmux

_READY = "floating-child-ready"
_COMMAND = ["/bin/sh", "-c", f"printf '{_READY}\\n'; IFS= read -r status; exit \"$status\""]
_GEOMETRY = "#{pane_left},#{pane_top},#{pane_width},#{pane_height}"


def _eventually(probe):
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        result = probe()
        if result:
            return result
        time.sleep(0.02)
    pytest.fail("timed out waiting for observable tmux state")


def _helpers(tmux, source):
    rows = tmux("list-panes", "-a", "-F", "#{pane_id}\t#{@flash-copy-source-pane}", check=False)
    return [
        pane
        for row in rows.splitlines()
        for pane, separator, original in [row.partition("\t")]
        if separator and original == source
    ]


@contextmanager
def _running_search(tmux, source, client, command=None):
    def run():
        with FloatingPane(source, client) as search:
            return search.run(_COMMAND if command is None else command)

    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(run)
        try:
            yield future
        finally:
            # Stop the real blocking child before joining its owner, including
            # when an assertion or readiness wait fails in the inspecting thread.
            for helper in _helpers(tmux, source):
                tmux("kill-pane", "-t", helper, check=False)
            future.result(timeout=8)


def _ready_search(tmux, source, client, future):
    def ready():
        if future.done():
            pytest.fail(f"search finished before becoming interactive: {future.result()}")
        for helper in _helpers(tmux, source):
            content = tmux("capture-pane", "-p", "-t", helper)
            active = tmux("display-message", "-p", "-c", client, "-t", helper, "#{pane_active}")
            if _READY in content and active == "1":
                return helper
        return None

    return _eventually(ready)


def _assert_clean(tmux, source, helper):
    assert helper not in tmux("list-panes", "-a", "-F", "#{pane_id}").splitlines()
    assert "@flash-copy-" not in tmux("show-options", "-p", "-t", source)


def test_source_and_helper_reentry_reuse_the_original_owner(attached_tmux):
    tmux, source, client = attached_tmux
    with _running_search(tmux, source, client) as future:
        helper = _ready_search(tmux, source, client, future)
        owner = tmux("display-message", "-p", "-t", helper, "#{@flash-copy-owner}")
        assert owner
        for entrypoint in (source, helper):
            tmux("select-pane", "-t", source)
            with FloatingPane(entrypoint, client) as reused:
                assert reused.reused
                assert reused.pane_id == source
                assert tmux("display-message", "-p", "-c", client, "#{pane_id}") == helper
            assert _helpers(tmux, source) == [helper]
            assert tmux("display-message", "-p", "-t", helper, "#{@flash-copy-owner}") == owner
            assert not future.done()
        tmux("send-keys", "-t", helper, "10", "Enter")
        assert future.result(timeout=8) == 10
    _assert_clean(tmux, source, helper)


def test_independent_sources_keep_separate_live_searches(attached_tmux):
    tmux, source, client = attached_tmux
    other = tmux("split-window", "-h", "-t", source, "-P", "-F", "#{pane_id}", "sleep 30")
    with _running_search(tmux, source, client) as first:
        first_helper = _ready_search(tmux, source, client, first)
        with _running_search(tmux, other, client) as second:
            second_helper = _ready_search(tmux, other, client, second)
            assert first_helper != second_helper
            assert _helpers(tmux, source) == [first_helper]
            assert _helpers(tmux, other) == [second_helper]
            assert tmux(
                "display-message", "-p", "-t", first_helper, "#{@flash-copy-owner}"
            ) != tmux("display-message", "-p", "-t", second_helper, "#{@flash-copy-owner}")
            tmux("send-keys", "-t", first_helper, "10", "Enter")
            assert first.result(timeout=8) == 10
            _assert_clean(tmux, source, first_helper)
            assert not second.done()
            assert _helpers(tmux, other) == [second_helper]
            tmux("send-keys", "-t", second_helper, "20", "Enter")
            assert second.result(timeout=8) == 20
        _assert_clean(tmux, other, second_helper)


@pytest.mark.parametrize("change", ["resize", "remove"])
def test_source_geometry_change_or_removal_cancels_live_search(attached_tmux, change):
    tmux, source, client = attached_tmux
    survivor = tmux("split-window", "-h", "-t", source, "-P", "-F", "#{pane_id}", "sleep 30")
    with _running_search(tmux, source, client) as future:
        helper = _ready_search(tmux, source, client, future)
        if change == "resize":
            before = tmux("display-message", "-p", "-t", source, _GEOMETRY)
            tmux("resize-pane", "-t", source, "-R", "5")
            assert tmux("display-message", "-p", "-t", source, _GEOMETRY) != before
        else:
            tmux("kill-pane", "-t", source)
        assert future.result(timeout=8) == 20
    _assert_clean(tmux, source if change == "resize" else survivor, helper)


def test_owner_disconnection_cancels_live_search(attached_tmux):
    tmux, source, client = attached_tmux
    with _running_search(tmux, source, client) as future:
        helper = _ready_search(tmux, source, client, future)
        tmux("detach-client", "-t", client)
        assert client not in tmux("list-clients", "-F", "#{client_name}").splitlines()
        assert future.result(timeout=8) == 20
    _assert_clean(tmux, source, helper)


def test_owner_session_switch_preserves_live_search(attached_tmux):
    tmux, source, client = attached_tmux
    tmux("new-session", "-d", "-s", "away", "sleep 30")
    with _running_search(tmux, source, client) as future:
        helper = _ready_search(tmux, source, client, future)
        tmux("switch-client", "-c", client, "-t", "away")
        assert (
            f"{client}\taway"
            in tmux("list-clients", "-F", "#{client_name}\t#{session_name}").splitlines()
        )
        # Allow more than one lifecycle poll: changing sessions is not detaching.
        time.sleep(0.5)
        assert not future.done()
        assert _helpers(tmux, source) == [helper]
        tmux("send-keys", "-t", helper, "10", "Enter")
        assert future.result(timeout=8) == 10
    _assert_clean(tmux, source, helper)


def test_external_helper_kill_cancels_and_allows_a_fresh_search(attached_tmux):
    tmux, source, client = attached_tmux
    with _running_search(tmux, source, client) as first:
        helper = _ready_search(tmux, source, client, first)
        owner = tmux("display-message", "-p", "-t", helper, "#{@flash-copy-owner}")
        tmux("kill-pane", "-t", helper)
        assert first.result(timeout=8) == 20
    _assert_clean(tmux, source, helper)

    with _running_search(tmux, source, client) as second:
        replacement = _ready_search(tmux, source, client, second)
        assert replacement != helper
        assert tmux("display-message", "-p", "-t", replacement, "#{@flash-copy-owner}") != owner
        tmux("send-keys", "-t", replacement, "0", "Enter")
        assert second.result(timeout=8) == 0
    _assert_clean(tmux, source, replacement)


def test_synchronized_source_input_and_search_input_are_isolated(attached_tmux):
    tmux, source, client = attached_tmux
    sibling = tmux("split-window", "-h", "-t", source, "-P", "-F", "#{pane_id}", "sleep 30")
    tmux("set-option", "-w", "-t", source, "synchronize-panes", "on")
    tmux("select-pane", "-t", source)
    # -K goes through the attached client's real input/key-table path, rather
    # than injecting directly into a pane and bypassing synchronization.
    tmux("send-keys", "-K", "-c", client, "before-search")
    for pane in (source, sibling):
        _eventually(lambda pane=pane: "before-search" in tmux("capture-pane", "-p", "-t", pane))

    command = [
        "/bin/sh",
        "-c",
        f"printf '{_READY}\\n'; IFS= read -r answer; "
        'printf \'accepted:%s\\n\' "$answer"; IFS= read -r status; exit "$status"',
    ]
    with _running_search(tmux, source, client, command) as future:
        helper = _ready_search(tmux, source, client, future)
        tmux("select-pane", "-t", source)
        tmux("send-keys", "-K", "-c", client, "source-after-search")
        for pane in (source, sibling):
            _eventually(
                lambda pane=pane: "source-after-search" in tmux("capture-pane", "-p", "-t", pane)
            )
        assert "source-after-search" not in tmux("capture-pane", "-p", "-t", helper)

        tmux("select-pane", "-t", helper)
        tmux("send-keys", "-K", "-c", client, "search-private-input", "Enter")
        _eventually(
            lambda: "accepted:search-private-input" in tmux("capture-pane", "-p", "-t", helper)
        )
        for pane in (source, sibling):
            assert "search-private-input" not in tmux("capture-pane", "-p", "-t", pane)
        assert tmux("show-options", "-wv", "-t", source, "synchronize-panes") == "on"
        tmux("send-keys", "-K", "-c", client, "10", "Enter")
        assert future.result(timeout=8) == 10
    _assert_clean(tmux, source, helper)
    assert tmux("show-options", "-wv", "-t", source, "synchronize-panes") == "on"
