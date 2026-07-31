"""
Popup UI module for the interactive search interface.

This module creates a tmux popup window that displays the pane content
with a search interface, labels for matches, and handles user input.
"""

import contextlib
import subprocess
import uuid
from pathlib import Path

from src.clipboard import Clipboard
from src.config import FlashCopyConfig
from src.debug_logger import DebugLogger
from src.popup_protocol import PopupExitCode
from src.search_interface import SearchInterface, SearchMatch
from src.utils import TmuxPaneUtils


class PopupExecutionError(RuntimeError):
    """Raised when popup transport or execution fails rather than being cancelled."""


class PopupUI:
    """Manages the interactive popup UI for searching and selecting."""

    def __init__(
        self,
        pane_content: str,
        search_interface: SearchInterface,
        clipboard: Clipboard,
        pane_id: str,
        config: FlashCopyConfig,
        client_name: str | None = None,
    ):
        """
        Initialise the popup UI.

        Args:
            pane_content: The captured pane content
            search_interface: SearchInterface instance for searching
            clipboard: Clipboard instance for copying
            pane_id: The tmux pane ID
            config: FlashCopyConfig with all configuration options
            client_name: The tmux client that launched the popup
        """
        self.pane_content = pane_content
        self.search_interface = search_interface
        self.clipboard = clipboard
        self.pane_id = pane_id
        self.client_name = client_name
        self.config = config
        self.search_query = ""
        self.current_matches: list[SearchMatch] = []

    def run(self) -> tuple[str | None, bool]:
        """
        Run the interactive popup UI.

        Returns:
            Tuple of (text, should_paste) where text is the copied text if selection
            was made (None if cancelled) and should_paste is True if auto-paste is enabled
        """
        # Launch the popup
        result = self._launch_popup()

        return result

    @staticmethod
    def _delete_buffer(buffer_name: str) -> None:
        """Delete a transient tmux buffer if it exists."""
        with contextlib.suppress(subprocess.SubprocessError, OSError):
            subprocess.run(
                ["tmux", "delete-buffer", "-b", buffer_name],
                capture_output=True,
                check=False,
                timeout=5,
            )

    def _launch_popup(self) -> tuple[str | None, bool]:
        """
        Launch the tmux popup window.

        Returns:
            Tuple of (text, should_paste) where text is the copied text if selection
            was made (None if cancelled) and should_paste is True if auto-paste is enabled
        """
        # Get pane dimensions for seamless overlay positioning
        pane_dimensions = TmuxPaneUtils.get_pane_dimensions(self.pane_id)

        if pane_dimensions:
            # Calculate popup position to perfectly overlay the pane
            popup_pos = TmuxPaneUtils.calculate_popup_position(pane_dimensions)
            popup_x = popup_pos["x"]
            popup_y = popup_pos["y"]
            popup_width = popup_pos["width"]
            popup_height = popup_pos["height"]
        else:
            # Fallback: Get window dimensions if pane dimensions unavailable
            try:
                result = subprocess.run(
                    ["tmux", "display-message", "-p", "#{window_width},#{window_height}"],
                    capture_output=True,
                    text=True,
                    check=True,
                )
                popup_width, popup_height = map(int, result.stdout.strip().split(","))
                popup_x = 0
                popup_y = 0
            except (subprocess.SubprocessError, ValueError):
                popup_width = 160
                popup_height = 40
                popup_x = 0
                popup_y = 0

        # Create a command that will be executed in the popup
        # We'll use a custom Python script for better control
        plugin_dir = Path(__file__).parent.parent
        interactive_script = plugin_dir / "bin" / "tmux-flash-copy-interactive.py"

        # Write pane content to an invocation-specific buffer for the child.
        invocation_id = uuid.uuid4().hex
        pane_content_buffer = f"__tmux_flash_copy_pane_content_{invocation_id}__"
        result_buffer = f"__tmux_flash_copy_result_{invocation_id}__"

        # Launch tmux popup with the interactive UI
        # -E: close popup on exit
        # -B: no border for seamless look
        # Position and size to seamlessly overlay the calling pane
        popup_cmd = [
            "tmux",
            "display-popup",
            "-E",
            "-B",
            "-x",
            str(popup_x),
            "-y",
            str(popup_y),
            "-w",
            str(popup_width),
            "-h",
            str(popup_height),
            str(interactive_script),
            "--pane-id",
            self.pane_id,
            "--pane-content-buffer",
            pane_content_buffer,
            "--result-buffer",
            result_buffer,
            "--reverse-search",
            str(self.search_interface.reverse_search),
            "--word-separators",
            self.search_interface.word_separators or "",
            "--case-sensitive",
            str(self.config.case_sensitive),
            "--prompt-placeholder-text",
            self.config.prompt_placeholder_text,
            "--highlight-colour",
            self.config.highlight_colour,
            "--label-colour",
            self.config.label_colour,
            "--prompt-position",
            self.config.prompt_position,
            "--prompt-indicator",
            self.config.prompt_indicator,
            "--prompt-colour",
            self.config.prompt_colour,
            "--debug-enabled",
            "true" if self.config.debug_enabled else "false",
            "--debug-log-file",
            DebugLogger.get_instance().log_file if self.config.debug_enabled else "",
            f"--label-characters={self.config.label_characters or ''}",
            "--auto-paste",
            "true" if self.config.auto_paste_enable else "false",
            "--idle-timeout",
            str(self.config.idle_timeout),
            "--idle-warning",
            str(self.config.idle_warning),
            "--range-selection",
            "true" if self.config.range_selection_enable else "false",
            "--copy-mode",
            self.config.copy_mode,
            "--mode-switch-key",
            self.config.mode_switch_key,
            "--range-copy-mode",
            self.config.range_copy_mode,
            "--range-marker-fg-colour",
            self.config.range_marker_fg_colour,
            "--range-marker-bg-colour",
            self.config.range_marker_bg_colour,
        ]
        if self.client_name:
            popup_cmd[2:2] = ["-t", self.client_name]

        logger = DebugLogger.get_instance()

        try:
            self._delete_buffer(result_buffer)
            try:
                subprocess.run(
                    ["tmux", "set-buffer", "-b", pane_content_buffer, self.pane_content],
                    check=True,
                    timeout=5,
                )
            except (subprocess.SubprocessError, OSError) as error:
                raise PopupExecutionError(
                    "Could not initialize popup snapshot transport"
                ) from error

            # The interactive child owns idle expiry because user input resets its
            # timer. A fixed parent timeout would cancel otherwise-active sessions.
            result = subprocess.run(
                popup_cmd,
                check=False,
            )

            if logger.enabled:
                logger.log(f"Popup closed with exit code: {result.returncode}")

            if result.returncode == PopupExitCode.CANCEL:
                if logger.enabled:
                    logger.log("Popup cancelled")
                return (None, False)

            if result.returncode not in (PopupExitCode.COPY, PopupExitCode.PASTE):
                if logger.enabled:
                    logger.log(f"Popup failed with exit code: {result.returncode}")
                raise PopupExecutionError(f"Popup failed with exit code {result.returncode}")

            should_paste = result.returncode == PopupExitCode.PASTE

            # Read result from tmux buffer (written by child process)
            # Using pane-specific buffer names to avoid conflicts
            try:
                if logger.enabled:
                    logger.log("Reading result from tmux buffer...")

                buffer_result = subprocess.run(
                    ["tmux", "save-buffer", "-b", result_buffer, "-"],
                    capture_output=True,
                    text=True,
                    check=True,
                )
                result_text = buffer_result.stdout if buffer_result.stdout is not None else None

                if logger.enabled:
                    if result_text:
                        logger.log(f"Buffer read successful (length: {len(result_text)})")
                    else:
                        logger.log("Buffer read returned empty string")

            except subprocess.CalledProcessError as e:
                if logger.enabled:
                    logger.log(f"Buffer read FAILED: {e}")
                raise PopupExecutionError("Could not read popup result transport") from e

            # Empty string means cancelled (ESC/Ctrl+C)
            # None means no output or buffer not found
            if result_text is not None and result_text != "":
                if logger.enabled:
                    logger.log(
                        f"Returning result to parent: '{result_text[:50]}...' (paste={should_paste})"
                    )
                # Return tuple of (text, should_paste)
                return (result_text, should_paste)

            # Return tuple of (None, False) for cancelled or no output
            if logger.enabled:
                logger.log("No result to return (cancelled or empty)")
            return (None, False)

        except PopupExecutionError:
            raise
        except subprocess.TimeoutExpired as error:
            if logger.enabled:
                logger.log("Popup timeout expired")
            raise PopupExecutionError("Popup execution timed out") from error
        except Exception as e:
            if logger.enabled:
                logger.log(f"Exception in _launch_popup: {e}")
            raise PopupExecutionError("Unexpected popup execution failure") from e
        finally:
            self._delete_buffer(result_buffer)
            self._delete_buffer(pane_content_buffer)
