"""Tests for PopupUI module."""

import subprocess
from unittest.mock import MagicMock, patch

import pytest

from src.clipboard import Clipboard
from src.config import FlashCopyConfig
from src.popup_protocol import PopupExitCode
from src.popup_ui import PopupExecutionError, PopupUI
from src.search_interface import SearchInterface


class TestPopupUIAutoPaste:
    """Test auto-paste argument passing in PopupUI."""

    @patch("src.popup_ui.subprocess.run")
    @patch("src.popup_ui.TmuxPaneUtils.get_pane_dimensions")
    @patch("src.popup_ui.TmuxPaneUtils.calculate_popup_position")
    @patch("src.popup_ui.DebugLogger.get_instance")
    def test_popup_targets_launching_client(
        self, mock_get_instance, mock_calc_pos, mock_get_dims, mock_subprocess
    ):
        mock_get_instance.return_value = MagicMock(enabled=False, log_file="")
        mock_get_dims.return_value = MagicMock()
        mock_calc_pos.return_value = {"x": 0, "y": 0, "width": 100, "height": 20}
        mock_subprocess.return_value = MagicMock(returncode=0, stdout="")
        search_interface = MagicMock(spec=SearchInterface)
        search_interface.reverse_search = True
        search_interface.word_separators = ""
        popup_ui = PopupUI(
            pane_content="text",
            search_interface=search_interface,
            clipboard=MagicMock(spec=Clipboard),
            pane_id="%1",
            config=FlashCopyConfig(),
            client_name="client-1",
        )

        popup_ui.run()

        popup_command = next(
            call.args[0]
            for call in mock_subprocess.call_args_list
            if "display-popup" in call.args[0]
        )
        assert popup_command[:7] == [
            "tmux",
            "display-popup",
            "-c",
            "client-1",
            "-t",
            "%1",
            "-E",
        ]

    @patch("src.popup_ui.subprocess.run")
    @patch("src.popup_ui.TmuxPaneUtils.get_pane_dimensions")
    @patch("src.popup_ui.TmuxPaneUtils.calculate_popup_position")
    @patch("src.popup_ui.DebugLogger.get_instance")
    def test_hyphen_leading_custom_labels_are_passed_as_attached_option(
        self, mock_get_instance, mock_calc_pos, mock_get_dims, mock_subprocess
    ):
        mock_get_instance.return_value = MagicMock(enabled=False, log_file="")
        mock_get_dims.return_value = MagicMock()
        mock_calc_pos.return_value = {"x": 0, "y": 0, "width": 100, "height": 20}

        def subprocess_side_effect(cmd, **kwargs):
            if "save-buffer" in cmd:
                return MagicMock(returncode=0, stdout="")
            return MagicMock(returncode=0, stdout="")

        mock_subprocess.side_effect = subprocess_side_effect
        search_interface = MagicMock(spec=SearchInterface)
        search_interface.reverse_search = True
        search_interface.word_separators = ""
        popup_ui = PopupUI(
            pane_content="text",
            search_interface=search_interface,
            clipboard=MagicMock(spec=Clipboard),
            pane_id="test_pane",
            config=FlashCopyConfig(label_characters="-a"),
        )

        popup_ui.run()

        popup_command = next(
            call.args[0]
            for call in mock_subprocess.call_args_list
            if "display-popup" in call.args[0]
        )
        assert "--label-characters=-a" in popup_command

    @patch("src.popup_ui.subprocess.run")
    @patch("src.popup_ui.TmuxPaneUtils.get_pane_dimensions")
    @patch("src.popup_ui.TmuxPaneUtils.calculate_popup_position")
    @patch("src.popup_ui.DebugLogger.get_instance")
    def test_popup_ui_passes_auto_paste_enabled_argument(
        self, mock_get_instance, mock_calc_pos, mock_get_dims, mock_subprocess
    ):
        """Test that PopupUI passes --auto-paste true when auto_paste_enable is True."""
        # Setup mocks
        mock_logger = MagicMock()
        mock_logger.log_file = ""
        mock_get_instance.return_value = mock_logger

        mock_get_dims.return_value = {
            "pane_x": 0,
            "pane_y": 0,
            "pane_width": 100,
            "pane_height": 20,
            "terminal_width": 200,
            "terminal_height": 50,
        }

        mock_calc_pos.return_value = {
            "x": 0,
            "y": 0,
            "width": 100,
            "height": 20,
        }

        # Mock subprocess.run to handle different commands
        def subprocess_side_effect(cmd, **kwargs):
            result = MagicMock()
            result.returncode = 0
            if "save-buffer" in cmd:
                result.stdout = "  test result  \n"
            else:
                result.stdout = ""
            return result

        mock_subprocess.side_effect = subprocess_side_effect

        # Create config with auto_paste_enable=True
        config = FlashCopyConfig(
            auto_paste_enable=True,
            range_marker_fg_colour="\033[31m",
            range_marker_bg_colour="\033[46m",
        )

        # Create PopupUI
        clipboard = MagicMock(spec=Clipboard)
        search_interface = MagicMock(spec=SearchInterface)
        search_interface.reverse_search = True
        search_interface.word_separators = ""
        search_interface.case_sensitive = False
        popup_ui = PopupUI(
            pane_content="test content",
            search_interface=search_interface,
            clipboard=clipboard,
            pane_id="test_pane",
            config=config,
        )

        selected = popup_ui._launch_popup()

        # Verify subprocess.run was called
        assert mock_subprocess.called
        # Get the display-popup call (skip buffer write at index 0)
        popup_call = None
        for call in mock_subprocess.call_args_list:
            call_args = call[0][0]
            if "display-popup" in call_args:
                popup_call = call_args
                break

        assert popup_call is not None, "display-popup call not found"

        # Check that --auto-paste true is in the arguments
        assert "--auto-paste" in popup_call
        auto_paste_index = popup_call.index("--auto-paste")
        assert popup_call[auto_paste_index + 1] == "true"
        assert popup_call[popup_call.index("--range-selection") + 1] == "true"
        assert popup_call[popup_call.index("--copy-mode") + 1] == "word"
        assert popup_call[popup_call.index("--mode-switch-key") + 1] == ","
        assert popup_call[popup_call.index("--range-copy-mode") + 1] == "word"
        assert popup_call[popup_call.index("--range-marker-fg-colour") + 1] == "\033[31m"
        assert popup_call[popup_call.index("--range-marker-bg-colour") + 1] == "\033[46m"
        assert selected == ("  test result  \n", False)

    @patch("src.popup_ui.subprocess.run")
    @patch("src.popup_ui.TmuxPaneUtils.get_pane_dimensions")
    @patch("src.popup_ui.TmuxPaneUtils.calculate_popup_position")
    @patch("src.popup_ui.DebugLogger.get_instance")
    def test_popup_ui_passes_auto_paste_disabled_argument(
        self, mock_get_instance, mock_calc_pos, mock_get_dims, mock_subprocess
    ):
        """Test that PopupUI passes --auto-paste false when auto_paste_enable is False."""
        # Setup mocks
        mock_logger = MagicMock()
        mock_logger.log_file = ""
        mock_get_instance.return_value = mock_logger

        mock_get_dims.return_value = {
            "pane_x": 0,
            "pane_y": 0,
            "pane_width": 100,
            "pane_height": 20,
            "terminal_width": 200,
            "terminal_height": 50,
        }

        mock_calc_pos.return_value = {
            "x": 0,
            "y": 0,
            "width": 100,
            "height": 20,
        }

        # Mock subprocess.run to handle different commands
        def subprocess_side_effect(cmd, **kwargs):
            result = MagicMock()
            result.returncode = 0
            if "save-buffer" in cmd:
                result.stdout = "test result"
            else:
                result.stdout = ""
            return result

        mock_subprocess.side_effect = subprocess_side_effect

        # Create config with auto_paste_enable=False
        config = FlashCopyConfig(auto_paste_enable=False)

        # Create PopupUI
        clipboard = MagicMock(spec=Clipboard)
        search_interface = MagicMock(spec=SearchInterface)
        search_interface.reverse_search = True
        search_interface.word_separators = ""
        search_interface.case_sensitive = False
        popup_ui = PopupUI(
            pane_content="test content",
            search_interface=search_interface,
            clipboard=clipboard,
            pane_id="test_pane",
            config=config,
        )

        popup_ui._launch_popup()

        # Verify subprocess.run was called
        assert mock_subprocess.called
        # Get the display-popup call (skip buffer write at index 0)
        popup_call = None
        for call in mock_subprocess.call_args_list:
            call_args = call[0][0]
            if "display-popup" in call_args:
                popup_call = call_args
                break

        assert popup_call is not None, "display-popup call not found"

        # Check that --auto-paste false is in the arguments
        assert "--auto-paste" in popup_call
        auto_paste_index = popup_call.index("--auto-paste")
        assert popup_call[auto_paste_index + 1] == "false"


class TestPopupUIErrorHandling:
    """Test error handling paths in PopupUI."""

    @patch("src.popup_ui.subprocess.run")
    @patch("src.popup_ui.TmuxPaneUtils.get_pane_dimensions")
    @patch("src.popup_ui.TmuxPaneUtils.calculate_popup_position")
    @patch("src.popup_ui.DebugLogger.get_instance")
    def test_snapshot_transport_failure_aborts_before_popup_launch(
        self, mock_get_instance, mock_calc_pos, mock_get_dims, mock_subprocess
    ):
        mock_get_instance.return_value = MagicMock(enabled=False, log_file="")
        mock_get_dims.return_value = MagicMock()
        mock_calc_pos.return_value = {"x": 0, "y": 0, "width": 100, "height": 20}

        def subprocess_side_effect(cmd, **kwargs):
            if "set-buffer" in cmd:
                raise subprocess.CalledProcessError(1, cmd)
            return MagicMock(returncode=0, stdout="")

        mock_subprocess.side_effect = subprocess_side_effect
        search_interface = MagicMock(spec=SearchInterface)
        search_interface.reverse_search = True
        search_interface.word_separators = ""
        popup_ui = PopupUI(
            pane_content="snapshot",
            search_interface=search_interface,
            clipboard=MagicMock(spec=Clipboard),
            pane_id="test_pane",
            config=FlashCopyConfig(),
        )

        with pytest.raises(PopupExecutionError, match="snapshot transport"):
            popup_ui.run()

        assert not any("display-popup" in call.args[0] for call in mock_subprocess.call_args_list)

    @patch("src.popup_ui.subprocess.run")
    @patch("src.popup_ui.TmuxPaneUtils.get_pane_dimensions")
    @patch("src.popup_ui.TmuxPaneUtils.calculate_popup_position")
    @patch("src.popup_ui.DebugLogger.get_instance")
    def test_failed_popup_does_not_return_a_stale_selection(
        self, mock_get_instance, mock_calc_pos, mock_get_dims, mock_subprocess
    ):
        """A failed popup must not consume result data left by an earlier invocation."""
        mock_logger = MagicMock()
        mock_logger.enabled = True
        mock_logger.log_file = ""
        mock_get_instance.return_value = mock_logger
        mock_get_dims.return_value = MagicMock()
        mock_calc_pos.return_value = {"x": 0, "y": 0, "width": 100, "height": 20}

        def subprocess_side_effect(cmd, **kwargs):
            result = MagicMock()
            if "display-popup" in cmd:
                result.returncode = 1
            elif "save-buffer" in cmd:
                result.returncode = 0
                result.stdout = "stale selection"
            else:
                result.returncode = 0
                result.stdout = ""
            return result

        mock_subprocess.side_effect = subprocess_side_effect

        config = FlashCopyConfig()
        search_interface = MagicMock(spec=SearchInterface)
        search_interface.reverse_search = True
        search_interface.word_separators = ""
        popup_ui = PopupUI(
            pane_content="test content",
            search_interface=search_interface,
            clipboard=MagicMock(spec=Clipboard),
            pane_id="test_pane",
            config=config,
        )

        with pytest.raises(PopupExecutionError, match="exit code 1"):
            popup_ui.run()

        save_calls = [
            call for call in mock_subprocess.call_args_list if "save-buffer" in call.args[0]
        ]
        assert save_calls == []

    @patch("src.popup_ui.subprocess.run")
    @patch("src.popup_ui.TmuxPaneUtils.get_pane_dimensions")
    @patch("src.popup_ui.TmuxPaneUtils.calculate_popup_position")
    @patch("src.popup_ui.DebugLogger.get_instance")
    def test_each_popup_uses_a_unique_result_channel(
        self, mock_get_instance, mock_calc_pos, mock_get_dims, mock_subprocess
    ):
        mock_logger = MagicMock()
        mock_logger.enabled = False
        mock_logger.log_file = ""
        mock_get_instance.return_value = mock_logger
        mock_get_dims.return_value = MagicMock()
        mock_calc_pos.return_value = {"x": 0, "y": 0, "width": 100, "height": 20}

        def subprocess_side_effect(cmd, **kwargs):
            return MagicMock(returncode=0, stdout="")

        mock_subprocess.side_effect = subprocess_side_effect

        search_interface = MagicMock(spec=SearchInterface)
        search_interface.reverse_search = True
        search_interface.word_separators = ""
        popup_ui = PopupUI(
            pane_content="test content",
            search_interface=search_interface,
            clipboard=MagicMock(spec=Clipboard),
            pane_id="test_pane",
            config=FlashCopyConfig(),
        )

        assert popup_ui.run() == (None, False)
        assert popup_ui.run() == (None, False)

        result_buffers = []
        pane_buffers = []
        for call in mock_subprocess.call_args_list:
            command = call.args[0]
            if "display-popup" not in command:
                continue
            result_buffers.append(command[command.index("--result-buffer") + 1])
            pane_buffers.append(command[command.index("--pane-content-buffer") + 1])

        assert len(result_buffers) == 2
        assert len(set(result_buffers)) == 2
        assert len(set(pane_buffers)) == 2
        assert all(
            result.rsplit("_", 1)[-1] == pane.rsplit("_", 1)[-1]
            for result, pane in zip(result_buffers, pane_buffers, strict=True)
        )

    @patch("src.popup_ui.subprocess.run")
    @patch("src.popup_ui.TmuxPaneUtils.get_pane_dimensions")
    @patch("src.popup_ui.TmuxPaneUtils.calculate_popup_position")
    @patch("src.popup_ui.DebugLogger.get_instance")
    def test_cancel_outcome_does_not_read_a_result_buffer(
        self, mock_get_instance, mock_calc_pos, mock_get_dims, mock_subprocess
    ):
        mock_get_instance.return_value = MagicMock(enabled=False, log_file="")
        mock_get_dims.return_value = MagicMock()
        mock_calc_pos.return_value = {"x": 0, "y": 0, "width": 100, "height": 20}

        def subprocess_side_effect(cmd, **kwargs):
            if "display-popup" in cmd:
                return MagicMock(returncode=PopupExitCode.CANCEL, stdout="")
            return MagicMock(returncode=0, stdout="")

        mock_subprocess.side_effect = subprocess_side_effect
        search_interface = MagicMock(spec=SearchInterface)
        search_interface.reverse_search = True
        search_interface.word_separators = ""
        popup_ui = PopupUI(
            pane_content="text",
            search_interface=search_interface,
            clipboard=MagicMock(spec=Clipboard),
            pane_id="test_pane",
            config=FlashCopyConfig(),
        )

        assert popup_ui.run() == (None, False)
        assert not any("save-buffer" in call.args[0] for call in mock_subprocess.call_args_list)

    @patch("src.popup_ui.subprocess.run")
    @patch("src.popup_ui.TmuxPaneUtils.get_pane_dimensions")
    @patch("src.popup_ui.TmuxPaneUtils.calculate_popup_position")
    @patch("src.popup_ui.DebugLogger.get_instance")
    def test_successful_paste_reads_only_its_transaction_result(
        self, mock_get_instance, mock_calc_pos, mock_get_dims, mock_subprocess
    ):
        mock_get_instance.return_value = MagicMock(enabled=False, log_file="")
        mock_get_dims.return_value = MagicMock()
        mock_calc_pos.return_value = {"x": 0, "y": 0, "width": 100, "height": 20}

        def subprocess_side_effect(cmd, **kwargs):
            if "display-popup" in cmd:
                return MagicMock(returncode=10, stdout="")
            if "save-buffer" in cmd:
                return MagicMock(returncode=0, stdout="selected text")
            return MagicMock(returncode=0, stdout="")

        mock_subprocess.side_effect = subprocess_side_effect
        search_interface = MagicMock(spec=SearchInterface)
        search_interface.reverse_search = True
        search_interface.word_separators = ""
        popup_ui = PopupUI(
            pane_content="selected text",
            search_interface=search_interface,
            clipboard=MagicMock(spec=Clipboard),
            pane_id="test_pane",
            config=FlashCopyConfig(),
        )

        assert popup_ui.run() == ("selected text", True)

        popup_command = next(
            call.args[0]
            for call in mock_subprocess.call_args_list
            if "display-popup" in call.args[0]
        )
        result_buffer = popup_command[popup_command.index("--result-buffer") + 1]
        save_command = next(
            call.args[0] for call in mock_subprocess.call_args_list if "save-buffer" in call.args[0]
        )
        assert save_command[save_command.index("-b") + 1] == result_buffer

    @patch("src.popup_ui.subprocess.run")
    @patch("src.popup_ui.TmuxPaneUtils.get_pane_dimensions")
    @patch("src.popup_ui.TmuxPaneUtils.calculate_popup_position")
    @patch("src.popup_ui.DebugLogger.get_instance")
    def test_cleanup_failure_does_not_mask_the_completed_transaction(
        self, mock_get_instance, mock_calc_pos, mock_get_dims, mock_subprocess
    ):
        mock_get_instance.return_value = MagicMock(enabled=False, log_file="")
        mock_get_dims.return_value = MagicMock()
        mock_calc_pos.return_value = {"x": 0, "y": 0, "width": 100, "height": 20}

        def subprocess_side_effect(cmd, **kwargs):
            if "delete-buffer" in cmd:
                raise subprocess.CalledProcessError(1, cmd)
            if "save-buffer" in cmd:
                return MagicMock(returncode=0, stdout="selected text")
            return MagicMock(returncode=0, stdout="")

        mock_subprocess.side_effect = subprocess_side_effect
        search_interface = MagicMock(spec=SearchInterface)
        search_interface.reverse_search = True
        search_interface.word_separators = ""
        popup_ui = PopupUI(
            pane_content="selected text",
            search_interface=search_interface,
            clipboard=MagicMock(spec=Clipboard),
            pane_id="test_pane",
            config=FlashCopyConfig(),
        )

        assert popup_ui.run() == ("selected text", False)

    @patch("src.popup_ui.subprocess.run")
    @patch("src.popup_ui.TmuxPaneUtils.get_pane_dimensions")
    @patch("src.popup_ui.DebugLogger.get_instance")
    def test_popup_aborts_when_targeted_pane_geometry_is_unavailable(
        self, mock_get_instance, mock_get_dims, mock_subprocess
    ):
        mock_logger = MagicMock()
        mock_logger.log_file = ""
        mock_get_instance.return_value = mock_logger
        mock_get_dims.return_value = None
        search_interface = MagicMock(spec=SearchInterface)
        search_interface.reverse_search = True
        search_interface.word_separators = ""
        popup_ui = PopupUI(
            pane_content="test content",
            search_interface=search_interface,
            clipboard=MagicMock(spec=Clipboard),
            pane_id="test_pane",
            config=FlashCopyConfig(),
        )

        with pytest.raises(PopupExecutionError, match="geometry for pane test_pane"):
            popup_ui._launch_popup()

        mock_subprocess.assert_not_called()

    @patch("src.popup_ui.subprocess.run")
    @patch("src.popup_ui.TmuxPaneUtils.get_pane_dimensions")
    @patch("src.popup_ui.TmuxPaneUtils.calculate_popup_position")
    @patch("src.popup_ui.DebugLogger.get_instance")
    def test_popup_buffer_read_failure(
        self, mock_get_instance, mock_calc_pos, mock_get_dims, mock_subprocess
    ):
        """Test handling of failed buffer read (CalledProcessError)."""
        mock_logger = MagicMock()
        mock_logger.enabled = True
        mock_logger.log_file = ""
        mock_get_instance.return_value = mock_logger

        mock_get_dims.return_value = {
            "pane_x": 0,
            "pane_y": 0,
            "pane_width": 100,
            "pane_height": 20,
            "terminal_width": 200,
            "terminal_height": 50,
        }

        mock_calc_pos.return_value = {
            "x": 0,
            "y": 0,
            "width": 100,
            "height": 20,
        }

        # Mock subprocess: popup succeeds, buffer read fails
        def subprocess_side_effect(cmd, **kwargs):
            result = MagicMock()
            if "save-buffer" in cmd:
                raise subprocess.CalledProcessError(1, cmd)
            result.returncode = 0
            result.stdout = ""
            return result

        mock_subprocess.side_effect = subprocess_side_effect

        config = FlashCopyConfig()
        clipboard = MagicMock(spec=Clipboard)
        search_interface = MagicMock(spec=SearchInterface)
        search_interface.reverse_search = True
        search_interface.word_separators = ""
        search_interface.case_sensitive = False

        popup_ui = PopupUI(
            pane_content="test content",
            search_interface=search_interface,
            clipboard=clipboard,
            pane_id="test_pane",
            config=config,
        )

        with pytest.raises(PopupExecutionError, match="result transport"):
            popup_ui._launch_popup()
        failure_log = next(
            call.args[0]
            for call in mock_logger.log.call_args_list
            if call.args[0].startswith("Buffer read FAILED:")
        )
        assert "__tmux_flash_copy_result_" in failure_log

        popup_call = next(
            call for call in mock_subprocess.call_args_list if "display-popup" in call.args[0]
        )
        popup_command = popup_call.args[0]
        result_buffer = popup_command[popup_command.index("--result-buffer") + 1]
        pane_buffer = popup_command[popup_command.index("--pane-content-buffer") + 1]
        deleted_buffers = {
            call.args[0][3]
            for call in mock_subprocess.call_args_list
            if "delete-buffer" in call.args[0]
        }
        assert result_buffer in deleted_buffers
        assert pane_buffer in deleted_buffers

    @patch("src.popup_ui.subprocess.run")
    @patch("src.popup_ui.TmuxPaneUtils.get_pane_dimensions")
    @patch("src.popup_ui.TmuxPaneUtils.calculate_popup_position")
    @patch("src.popup_ui.DebugLogger.get_instance")
    def test_interactive_idle_timeout_owns_popup_lifetime(
        self, mock_get_instance, mock_calc_pos, mock_get_dims, mock_subprocess
    ):
        """Active input may extend the child session beyond its configured idle timeout."""
        mock_logger = MagicMock()
        mock_logger.enabled = False
        mock_logger.log_file = ""
        mock_get_instance.return_value = mock_logger
        mock_get_dims.return_value = MagicMock()
        mock_calc_pos.return_value = {"x": 0, "y": 0, "width": 100, "height": 20}

        def subprocess_side_effect(cmd, **kwargs):
            result = MagicMock(returncode=0, stdout="")
            return result

        mock_subprocess.side_effect = subprocess_side_effect

        search_interface = MagicMock(spec=SearchInterface)
        search_interface.reverse_search = True
        search_interface.word_separators = ""
        popup_ui = PopupUI(
            pane_content="test content",
            search_interface=search_interface,
            clipboard=MagicMock(spec=Clipboard),
            pane_id="test_pane",
            config=FlashCopyConfig(idle_timeout=60),
        )

        assert popup_ui.run() == (None, False)

        popup_call = next(
            call for call in mock_subprocess.call_args_list if "display-popup" in call.args[0]
        )
        assert "timeout" not in popup_call.kwargs

    @patch("src.popup_ui.subprocess.run")
    @patch("src.popup_ui.TmuxPaneUtils.get_pane_dimensions")
    @patch("src.popup_ui.TmuxPaneUtils.calculate_popup_position")
    @patch("src.popup_ui.DebugLogger.get_instance")
    def test_external_popup_timeout_is_handled(
        self, mock_get_instance, mock_calc_pos, mock_get_dims, mock_subprocess
    ):
        """A caller- or platform-imposed subprocess timeout is still handled safely."""
        mock_logger = MagicMock()
        mock_logger.enabled = True
        mock_logger.log_file = ""
        mock_get_instance.return_value = mock_logger

        mock_get_dims.return_value = {
            "pane_x": 0,
            "pane_y": 0,
            "pane_width": 100,
            "pane_height": 20,
            "terminal_width": 200,
            "terminal_height": 50,
        }

        mock_calc_pos.return_value = {
            "x": 0,
            "y": 0,
            "width": 100,
            "height": 20,
        }

        # Mock subprocess to succeed for buffer operations, timeout for popup command
        def subprocess_side_effect(cmd, **kwargs):
            if "set-buffer" in cmd or "delete-buffer" in cmd:
                # Buffer operations succeed
                result = MagicMock()
                result.returncode = 0
                return result
            # Popup command times out
            raise subprocess.TimeoutExpired("tmux", 60.0)

        mock_subprocess.side_effect = subprocess_side_effect

        config = FlashCopyConfig()
        clipboard = MagicMock(spec=Clipboard)
        search_interface = MagicMock(spec=SearchInterface)
        search_interface.reverse_search = True
        search_interface.word_separators = ""
        search_interface.case_sensitive = False

        popup_ui = PopupUI(
            pane_content="test content",
            search_interface=search_interface,
            clipboard=clipboard,
            pane_id="test_pane",
            config=config,
        )

        with pytest.raises(PopupExecutionError, match="timed out"):
            popup_ui._launch_popup()
        # Should log the timeout
        mock_logger.log.assert_any_call("Popup timeout expired")

    @patch("src.popup_ui.subprocess.run")
    @patch("src.popup_ui.TmuxPaneUtils.get_pane_dimensions")
    @patch("src.popup_ui.TmuxPaneUtils.calculate_popup_position")
    @patch("src.popup_ui.DebugLogger.get_instance")
    def test_popup_generic_exception(
        self, mock_get_instance, mock_calc_pos, mock_get_dims, mock_subprocess
    ):
        """Test handling of unexpected exceptions."""
        mock_logger = MagicMock()
        mock_logger.enabled = True
        mock_logger.log_file = ""
        mock_get_instance.return_value = mock_logger

        mock_get_dims.return_value = {
            "pane_x": 0,
            "pane_y": 0,
            "pane_width": 100,
            "pane_height": 20,
            "terminal_width": 200,
            "terminal_height": 50,
        }

        mock_calc_pos.return_value = {
            "x": 0,
            "y": 0,
            "width": 100,
            "height": 20,
        }

        # Mock subprocess to succeed for buffer operations, fail for popup command
        def subprocess_side_effect(cmd, **kwargs):
            if "set-buffer" in cmd or "delete-buffer" in cmd:
                # Buffer operations succeed
                result = MagicMock()
                result.returncode = 0
                return result
            # Popup command raises generic exception
            raise RuntimeError("Unexpected error")

        mock_subprocess.side_effect = subprocess_side_effect

        config = FlashCopyConfig()
        clipboard = MagicMock(spec=Clipboard)
        search_interface = MagicMock(spec=SearchInterface)
        search_interface.reverse_search = True
        search_interface.word_separators = ""
        search_interface.case_sensitive = False

        popup_ui = PopupUI(
            pane_content="test content",
            search_interface=search_interface,
            clipboard=clipboard,
            pane_id="test_pane",
            config=config,
        )

        with pytest.raises(PopupExecutionError, match="Unexpected popup"):
            popup_ui._launch_popup()
        # Should log the exception
        mock_logger.log.assert_any_call("Exception in _launch_popup: Unexpected error")
