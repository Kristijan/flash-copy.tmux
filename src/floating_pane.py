"""Non-modal, source-sized search panes on stable tmux 3.8 and newer."""

import os
import re
import selectors
import subprocess
import time
import uuid
from dataclasses import dataclass
from types import TracebackType

from .popup_protocol import PopupExitCode
from .utils import PaneDimensions, SubprocessUtils

_SOURCE_OPTION = "@flash-copy-source-pane"
_SEARCH_OPTION = "@flash-copy-search-pane"
_OWNER_OPTION = "@flash-copy-owner"
_PANE_ID = re.compile(r"%[0-9]+")
_TIMEOUT = SubprocessUtils.DEFAULT_TIMEOUT
_POLL_INTERVAL = 0.2


def supports_floating_panes(version: str) -> bool:
    """Accept stable numeric server versions, including one patch-release letter."""
    match = re.fullmatch(r"([0-9]+)\.([0-9]+)[a-z]?", version)
    return match is not None and tuple(map(int, match.groups())) >= (3, 8)


def _tmux(*arguments: str) -> str:
    # Unlike the forgiving utility wrappers, launch failures must reach the caller.
    return subprocess.run(
        ["tmux", *arguments], capture_output=True, text=True, check=True, timeout=_TIMEOUT
    ).stdout.rstrip("\n")


@dataclass
class _PaneState:
    dimensions: PaneDimensions
    client_name: str
    source: str
    search: str
    owner: str
    dead: bool
    floating: bool
    result: str
    title: str


class FloatingPane:
    """Serialize source capture/setup, then own one native search until completion."""

    def __init__(self, pane_id: str, client_name: str):
        self.pane_id = pane_id
        self.client_name = client_name
        self.reused = False
        self.dimensions: PaneDimensions
        self._token = uuid.uuid4().hex
        self._title = f"flash-copy-{self._token}"
        self._result_option = f"@flash-copy-result-{self._token}"
        self._lock = ""
        self._locked = False
        self._helper: str | None = None
        self._waiter: subprocess.Popen | None = None

    def _state(self, pane_id: str, *, client: bool = False) -> _PaneState | None:
        if not _PANE_ID.fullmatch(pane_id):
            return None
        fields = [
            "#{pane_id}",
            "#{pane_left}",
            "#{pane_top}",
            "#{pane_right}",
            "#{pane_bottom}",
            "#{pane_width}",
            "#{pane_height}",
            "#{client_name}",
            f"#{{{_SOURCE_OPTION}}}",
            f"#{{{_SEARCH_OPTION}}}",
            f"#{{{_OWNER_OPTION}}}",
            "#{pane_dead}",
            "#{pane_floating_flag}",
            f"#{{{self._result_option}}}",
            "#{pane_title}",
        ]
        arguments = ["display-message", "-p", "-t", pane_id]
        if client:
            arguments.extend(["-c", self.client_name])
        output = _tmux(*arguments, "\t".join(fields))
        parts = output.split("\t", len(fields) - 1)
        # display-message permits failed targets and may silently use another pane.
        if not parts or parts[0] != pane_id:
            return None
        if len(parts) != len(fields):
            raise RuntimeError(f"Malformed tmux pane information for {pane_id}: {output!r}")
        dimensions = PaneDimensions(pane_id, *(int(value) for value in parts[1:7]))
        return _PaneState(
            dimensions,
            parts[7],
            parts[8],
            parts[9],
            parts[10],
            parts[11] == "1",
            parts[12] == "1",
            parts[13],
            parts[14],
        )

    def _acquire(self) -> None:
        _tmux("wait-for", "-L", self._lock)
        self._locked = True

    def _release(self) -> None:
        if self._locked:
            _tmux("wait-for", "-U", self._lock)
            self._locked = False

    def __enter__(self) -> "FloatingPane":
        try:
            state = self._state(self.pane_id)
            if state is None:
                raise RuntimeError(f"Source pane {self.pane_id} no longer exists")
            if state.source:
                self.pane_id = state.source
            # wait-for channels already belong to the current tmux server. Pane IDs
            # do not repeat within a server, so unrelated sources never contend.
            self._lock = f"flash-copy-source-{self.pane_id}"
            self._acquire()
            state = self._state(self.pane_id)
            if state is None or state.source:
                raise RuntimeError(f"Original source pane {self.pane_id} no longer exists")
            self.dimensions = state.dimensions
            if state.search:
                helper = self._state(state.search)
                if (
                    helper is not None
                    and helper.source == self.pane_id
                    and helper.owner
                    and helper.floating
                    and not helper.dead
                    and self._same_geometry(helper.dimensions, self.dimensions)
                ):
                    if self._focus(state.search):
                        self.reused = True
                        self._release()
                        return self
                elif (
                    helper is not None
                    and helper.source == self.pane_id
                    and helper.owner
                    and helper.floating
                ):
                    self._kill(state.search)
                _tmux("set-option", "-pu", "-t", self.pane_id, _SEARCH_OPTION)
            return self
        except BaseException:
            self._release()
            raise

    @staticmethod
    def _same_geometry(left: PaneDimensions, right: PaneDimensions) -> bool:
        return (left.left, left.top, left.width, left.height) == (
            right.left,
            right.top,
            right.width,
            right.height,
        )

    def _source_valid(self) -> bool:
        state = self._state(self.pane_id, client=True)
        if state is None or not self._same_geometry(state.dimensions, self.dimensions):
            return False
        if state.client_name == self.client_name:
            return True
        # display-message substitutes a source-session client when the requested
        # client switches sessions. Check presence, not its current session/window.
        return self.client_name in _tmux("list-clients", "-F", "#{client_name}").splitlines()

    def _focus(self, pane_id: str) -> bool:
        try:
            _tmux("select-pane", "-t", pane_id)
            return True
        except subprocess.CalledProcessError:
            if self._state(pane_id) is not None:
                raise
            return False

    def _kill(self, pane_id: str) -> None:
        try:
            _tmux("kill-pane", "-t", pane_id)
        except subprocess.CalledProcessError:
            if self._state(pane_id) is not None:
                raise

    def _create(self) -> None:
        dimensions = self.dimensions
        arguments = [
            "tmux",
            "new-pane",
            "-d",
            "-E",
            "-A",
            "-B",
            "none",
            "-W",
            "-P",
            "-F",
            "#{pane_id}",
            "-t",
            self.pane_id,
            "-T",
            self._title,
            "-x",
            str(dimensions.width),
            "-y",
            str(dimensions.height),
            "-X",
            str(dimensions.left),
            "-Y",
            str(dimensions.top),
        ]
        self._waiter = subprocess.Popen(arguments, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        assert self._waiter.stdout is not None
        deadline = time.monotonic() + _TIMEOUT
        output = b""
        with selectors.DefaultSelector() as selector:
            selector.register(self._waiter.stdout, selectors.EVENT_READ)
            while b"\n" not in output:
                remaining = deadline - time.monotonic()
                if remaining <= 0 or not selector.select(remaining):
                    raise subprocess.TimeoutExpired(arguments, _TIMEOUT, output=output)
                chunk = os.read(self._waiter.stdout.fileno(), 4096)
                if not chunk:
                    _, stderr = self._waiter.communicate(timeout=_TIMEOUT)
                    raise subprocess.CalledProcessError(
                        self._waiter.returncode or 1, arguments, output=output, stderr=stderr
                    )
                output += chunk
        pane_id = output.decode().strip()
        if not _PANE_ID.fullmatch(pane_id):
            raise RuntimeError(f"Malformed tmux helper pane ID: {pane_id!r}")
        self._helper = pane_id
        # An empty detached pane has no pty: synchronization cannot leak keys
        # before these per-pane overrides have been installed.
        for option, value in (
            ("synchronize-panes", "off"),
            ("remain-on-exit", "off"),
            ("alternate-screen", "on"),
            (_OWNER_OPTION, self._token),
            (_SOURCE_OPTION, self.pane_id),
        ):
            _tmux("set-option", "-p", "-t", pane_id, option, value)
        _tmux("set-option", "-p", "-t", self.pane_id, _SEARCH_OPTION, pane_id)

    def run(self, command: list[str]) -> int:
        """Start the interactive argv only after safe setup, and wait without an idle limit."""
        if self.reused or not self._locked:
            raise RuntimeError("FloatingPane.run requires a new, entered source context")
        if not command:
            raise ValueError("The floating search command must not be empty")
        if not self._source_valid():
            return int(PopupExitCode.CANCEL)
        self._create()
        assert self._helper is not None and self._waiter is not None
        # A killed pane and a genuine exit 129 have the same -W status. Record
        # normal child completion separately so launch/execution errors survive.
        wrapper = (
            'printf "\\033[?1049h"; source=$1; result=$2; shift 2; "$@"; status=$?; '
            'tmux set-option -p -t "$source" "$result" "$status" || exit $?; exit "$status"'
        )
        _tmux(
            "respawn-pane",
            "-t",
            self._helper,
            "sh",
            "-c",
            wrapper,
            "flash-copy",
            self.pane_id,
            self._result_option,
            *command,
        )
        # Scrollbar visibility is window-scoped, so never disable it with -p:
        # tmux would modify the user's window. An alternate screen suppresses
        # helper scrollbars without changing source geometry. Wait for tmux to
        # process that terminal transition before exposing the helper to input.
        deadline = time.monotonic() + _TIMEOUT
        while self._waiter.poll() is None:
            helper = self._state(self._helper)
            if helper is None or self._same_geometry(helper.dimensions, self.dimensions):
                break
            if time.monotonic() >= deadline:
                raise RuntimeError(
                    "Floating search pane does not match the source content geometry"
                )
            time.sleep(0.02)
        cancelled = not self._source_valid()
        if not cancelled:
            self._focus(self._helper)
        self._release()
        while not cancelled:
            try:
                self._waiter.wait(timeout=_POLL_INTERVAL)
                break
            except subprocess.TimeoutExpired:
                cancelled = not self._source_valid()
        if cancelled:
            self._kill(self._helper)
        _, stderr = self._waiter.communicate(timeout=_TIMEOUT)
        cancelled = cancelled or not self._source_valid()
        if cancelled:
            return int(PopupExitCode.CANCEL)
        source = self._state(self.pane_id)
        if source is not None and source.result:
            return int(source.result)
        if self._waiter.returncode == 129 and self._state(self._helper) is None:
            return int(PopupExitCode.CANCEL)
        if self._waiter.returncode:
            # Preserve diagnostics as well as the actual waiting command status.
            raise subprocess.CalledProcessError(
                self._waiter.returncode, self._waiter.args, stderr=stderr
            )
        return self._waiter.returncode

    def _cleanup_helper(self) -> None:
        if self._waiter is None:
            return
        if self._helper is None:
            # A failed ID handshake must not strand an empty pane. The title is
            # an invocation UUID installed atomically by new-pane itself.
            if self._waiter.poll() is None:
                self._waiter.terminate()
                self._waiter.communicate(timeout=_TIMEOUT)
            for line in _tmux("list-panes", "-a", "-F", "#{pane_id}\t#{pane_title}").splitlines():
                pane_id, separator, title = line.partition("\t")
                if separator and title == self._title:
                    self._helper = pane_id
                    break
        if self._helper is not None:
            helper = self._state(self._helper)
            if helper is not None and (helper.owner == self._token or helper.title == self._title):
                self._kill(self._helper)

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        try:
            self._cleanup_helper()
        finally:
            try:
                if self._waiter is not None:
                    if not self._locked:
                        self._acquire()
                    state = self._state(self.pane_id)
                    if state is not None:
                        if state.search == self._helper:
                            _tmux("set-option", "-pu", "-t", self.pane_id, _SEARCH_OPTION)
                        if state.result:
                            _tmux("set-option", "-pu", "-t", self.pane_id, self._result_option)
            finally:
                try:
                    self._release()
                finally:
                    if self._waiter is not None:
                        try:
                            self._waiter.communicate(timeout=_TIMEOUT)
                        except subprocess.TimeoutExpired:
                            self._waiter.kill()
                            self._waiter.communicate(timeout=_TIMEOUT)
                            raise
