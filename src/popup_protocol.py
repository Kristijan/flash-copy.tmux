"""Exit-status protocol shared by popup parent and interactive child."""

from enum import IntEnum


class PopupExitCode(IntEnum):
    """Observable outcomes returned by the interactive popup process."""

    COPY = 0
    PASTE = 10
    CANCEL = 20
