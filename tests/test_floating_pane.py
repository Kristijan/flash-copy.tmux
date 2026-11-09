"""Native tmux behavior that cannot be represented by subprocess response mocks."""

import contextlib
import os
import pty
import shutil
import signal
import subprocess
import tempfile
import time

import pytest

from src.floating_pane import FloatingPane, supports_floating_panes


@pytest.fixture
def attached_tmux(monkeypatch):
    """Attach a real terminal to a disposable server, never the user's socket."""
    binary = shutil.which("tmux")
    if binary is None:
        if os.environ.get("FLASH_COPY_REQUIRE_TMUX") == "1":
            pytest.fail("CI requires tmux 3.8+; native tests must not be skipped")
        pytest.skip("tmux is not installed")
    environment = os.environ.copy()
    environment.pop("TMUX", None)
    environment.pop("TMUX_PANE", None)
    environment["TERM"] = "xterm-256color"
    with tempfile.TemporaryDirectory(prefix="fc-test-", dir="/tmp") as directory:
        prefix = [binary, "-S", f"{directory}/socket", "-f", "/dev/null"]

        def tmux(*arguments, check=True):
            return subprocess.run(
                [*prefix, *arguments],
                env=environment,
                capture_output=True,
                text=True,
                check=check,
                timeout=5,
            ).stdout.strip()

        client_pid = None
        terminal = None
        try:
            source = tmux(
                "new-session",
                "-d",
                "-s",
                "test",
                "-x",
                "100",
                "-y",
                "30",
                "-P",
                "-F",
                "#{pane_id}",
                "sleep 30",
            )
            if not supports_floating_panes(tmux("display-message", "-p", "#{version}")):
                if os.environ.get("FLASH_COPY_REQUIRE_TMUX") == "1":
                    pytest.fail("CI requires stable tmux 3.8+; check the native runtime setup")
                pytest.skip("native floating search requires stable tmux 3.8+")
            tmux("set-option", "-g", "default-shell", "/bin/sh")
            monkeypatch.setenv("TMUX", tmux("display-message", "-p", "#{socket_path},#{pid},0"))
            client_pid, terminal = pty.fork()
            if client_pid == 0:
                os.execvpe(binary, [*prefix, "attach-session", "-t", "test"], environment)
            deadline = time.monotonic() + 5
            client = ""
            while time.monotonic() < deadline:
                clients = tmux("list-clients", "-F", "#{client_pid}\t#{client_name}")
                client = next(
                    (
                        row.split("\t", 1)[1]
                        for row in clients.splitlines()
                        if row.startswith(f"{client_pid}\t")
                    ),
                    "",
                )
                if client:
                    break
                time.sleep(0.02)
            assert client, "attached terminal did not connect"
            yield tmux, source, client
        finally:
            tmux("kill-server", check=False)
            if terminal is not None:
                os.close(terminal)
            if client_pid:
                deadline = time.monotonic() + 3
                while time.monotonic() < deadline:
                    if os.waitpid(client_pid, os.WNOHANG)[0]:
                        break
                    time.sleep(0.02)
                else:
                    with contextlib.suppress(ProcessLookupError):
                        os.kill(client_pid, signal.SIGKILL)
                    os.waitpid(client_pid, 0)


def test_search_preserves_source_scrollbars_and_content_geometry(attached_tmux):
    tmux, source, client = attached_tmux
    tmux("set-option", "-w", "-t", source, "pane-scrollbars", "on")
    tmux("set-option", "-w", "-t", source, "pane-border-status", "top")
    geometry_format = "#{pane_left},#{pane_top},#{pane_width},#{pane_height}"
    original_geometry = tmux("display-message", "-p", "-t", source, geometry_format)

    with FloatingPane(source, client) as search:
        # A short real command distinguishes normal completion from the erroneous
        # geometry-change cancellation caused by mutating the window's scrollbars.
        status = search.run(["/bin/sh", "-c", "sleep 0.1; exit 7"])

    assert status == 7
    assert tmux("show-options", "-wv", "-t", source, "pane-scrollbars") == "on"
    assert tmux("display-message", "-p", "-t", source, geometry_format) == original_geometry
