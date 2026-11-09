"""Fault injection at process/command boundaries, retaining real tmux pane effects."""

import os
import subprocess
import threading

import pytest

import src.floating_pane as floating_module
from src.floating_pane import FloatingPane
from tests.test_floating_errors import assert_source_reusable, pane_ids
from tests.test_floating_pane import attached_tmux as attached_tmux


@pytest.mark.parametrize("fault", ["truncated", "malformed", "lost"])
def test_failed_identity_transport_does_not_strand_an_empty_pane(attached_tmux, monkeypatch, fault):
    tmux, source, client = attached_tmux
    original_panes = pane_ids(tmux)
    real_popen = subprocess.Popen
    bridges = []

    class BrokenIdentityTransport(real_popen):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            native_output = self.stdout
            assert native_output is not None
            read_fd, write_fd = os.pipe()
            self.stdout = os.fdopen(read_fd, "rb", buffering=0)
            self.transport_closed = threading.Event()

            def bridge():
                try:
                    # The real pane is already created. Lose or corrupt only its
                    # identity reply, so recovery must locate the orphan safely.
                    native_output.readline()
                    if fault == "malformed":
                        os.write(write_fd, b"invalid-pane-id\n")
                    elif fault == "truncated":
                        super(BrokenIdentityTransport, self).terminate()
                    else:
                        self.transport_closed.wait(5)
                finally:
                    native_output.close()
                    os.close(write_fd)

            thread = threading.Thread(target=bridge, daemon=True)
            bridges.append((self.transport_closed, thread))
            thread.start()

        def terminate(self):
            self.transport_closed.set()
            super().terminate()

    def corrupt_launch_only(command, *args, **kwargs):
        process_type = BrokenIdentityTransport if "new-pane" in command else real_popen
        return process_type(command, *args, **kwargs)

    try:
        with monkeypatch.context() as failure:
            failure.setattr(subprocess, "Popen", corrupt_launch_only)
            failure.setattr(floating_module, "_TIMEOUT", 0.5)
            expected = {
                "truncated": subprocess.CalledProcessError,
                "malformed": RuntimeError,
                "lost": subprocess.TimeoutExpired,
            }[fault]
            with pytest.raises(expected), FloatingPane(source, client) as search:
                search.run(["/bin/sh", "-c", "exit 0"])
    finally:
        for closed, bridge_thread in bridges:
            closed.set()
            bridge_thread.join(timeout=5)

    assert pane_ids(tmux) == original_panes
    assert_source_reusable(tmux, source, client, original_panes)


def test_malformed_pane_information_fails_without_modifying_existing_panes(
    attached_tmux, monkeypatch
):
    tmux, source, client = attached_tmux
    original_panes = pane_ids(tmux)
    real_run = subprocess.run

    def corrupt_information(command, **kwargs):
        response = real_run(command, **kwargs)
        if "display-message" in command:
            response.stdout = f"{source}\ttruncated\n"
        return response

    with monkeypatch.context() as failure:
        failure.setattr(subprocess, "run", corrupt_information)
        with pytest.raises(RuntimeError), FloatingPane(source, client):
            pytest.fail("malformed pane information must not be accepted")

    assert pane_ids(tmux) == original_panes
    assert_source_reusable(tmux, source, client, original_panes)


def test_rejected_focus_is_reported_and_the_search_is_removed(attached_tmux, monkeypatch):
    tmux, source, client = attached_tmux
    original_panes = pane_ids(tmux)
    real_run = subprocess.run

    def reject_focus(command, **kwargs):
        if "select-pane" in command:
            raise subprocess.CalledProcessError(1, command, stderr="focus rejected")
        return real_run(command, **kwargs)

    with monkeypatch.context() as failure:
        failure.setattr(subprocess, "run", reject_focus)
        with pytest.raises(subprocess.CalledProcessError), FloatingPane(source, client) as search:
            search.run(["/bin/sleep", "30"])

    assert pane_ids(tmux) == original_panes
    assert_source_reusable(tmux, source, client, original_panes)


@pytest.mark.parametrize("already_closed", [False, True], ids=["rejected", "close-race"])
def test_cleanup_handles_close_races_but_reports_a_rejected_kill(
    attached_tmux, monkeypatch, already_closed
):
    tmux, source, client = attached_tmux
    original_panes = pane_ids(tmux)
    real_run = subprocess.run

    def fail_setup_and_close(command, **kwargs):
        if "set-option" in command and "synchronize-panes" in command:
            raise subprocess.CalledProcessError(1, command)
        if "kill-pane" in command:
            if already_closed:
                real_run(command, **kwargs)
            raise subprocess.CalledProcessError(73, command, stderr="close rejected")
        return real_run(command, **kwargs)

    with monkeypatch.context() as failure:
        failure.setattr(subprocess, "run", fail_setup_and_close)
        failure.setattr(floating_module, "_TIMEOUT", 1)
        expected = subprocess.CalledProcessError if already_closed else subprocess.TimeoutExpired
        with (
            pytest.raises(expected) as error,
            FloatingPane(source, client) as search,
        ):
            search.run(["/bin/sh", "-c", "exit 0"])

    # A close race preserves the original setup error. A rejected kill leaves
    # the empty pane alive, so the worker must stop waiting and report a timeout.
    if already_closed:
        assert isinstance(error.value, subprocess.CalledProcessError)
        assert error.value.returncode == 1
    leftovers = pane_ids(tmux) - original_panes
    assert bool(leftovers) is not already_closed
    for helper in leftovers:
        tmux("kill-pane", "-t", helper)
    assert_source_reusable(tmux, source, client, original_panes)


def test_owner_disappearing_before_launch_cancels_without_creating_a_pane(attached_tmux):
    tmux, source, client = attached_tmux
    original_panes = pane_ids(tmux)
    with FloatingPane(source, client) as search:
        tmux("detach-client", "-t", client)
        assert search.run(["/bin/sleep", "30"]) == 20
    assert pane_ids(tmux) == original_panes
    assert "@flash-copy-" not in tmux("show-options", "-p", "-t", source)


def test_misaligned_helper_is_never_exposed_as_a_search(attached_tmux, monkeypatch):
    tmux, source, client = attached_tmux
    original_panes = pane_ids(tmux)
    real_run = subprocess.run

    def resize_during_launch(command, **kwargs):
        response = real_run(command, **kwargs)
        if "respawn-pane" in command:
            helper = command[command.index("-t") + 1]
            real_run(["tmux", "resize-pane", "-t", helper, "-x", "20"], check=True)
        return response

    with monkeypatch.context() as failure:
        failure.setattr(subprocess, "run", resize_during_launch)
        failure.setattr(floating_module, "_TIMEOUT", 0.5)
        with pytest.raises(RuntimeError), FloatingPane(source, client) as search:
            search.run(["/bin/sleep", "30"])

    assert pane_ids(tmux) == original_panes
    assert_source_reusable(tmux, source, client, original_panes)
