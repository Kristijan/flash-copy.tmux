"""Tests for PopupUI module."""

import subprocess
from unittest.mock import MagicMock, patch

from src.clipboard import Clipboard
from src.config import FlashCopyConfig
from src.popup_ui import PopupUI
from src.search_interface import SearchInterface


class TestPopupUIAutoPaste:
    """Test auto-paste argument passing in PopupUI."""

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

        mock_subprocess.return_value = MagicMock()

        # Create config with auto_paste_enable=True
        config = FlashCopyConfig(auto_paste_enable=True)

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

        # Mock the file operations
        with (
            patch("builtins.open", create=True),
            patch("os.path.join", side_effect=lambda *args: "/".join(args)),
            patch("os.path.exists") as mock_exists,
        ):
            mock_exists.return_value = False
            popup_ui._launch_popup()

        # Verify subprocess.run was called
        assert mock_subprocess.called
        call_args = mock_subprocess.call_args[0][0]

        # Check that --auto-paste true is in the arguments
        assert "--auto-paste" in call_args
        auto_paste_index = call_args.index("--auto-paste")
        assert call_args[auto_paste_index + 1] == "true"

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

        mock_subprocess.return_value = MagicMock()

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

        # Mock the file operations
        with (
            patch("builtins.open", create=True),
            patch("os.path.join", side_effect=lambda *args: "/".join(args)),
            patch("os.path.exists") as mock_exists,
        ):
            mock_exists.return_value = False
            popup_ui._launch_popup()

        # Verify subprocess.run was called
        assert mock_subprocess.called
        call_args = mock_subprocess.call_args[0][0]

        # Check that --auto-paste false is in the arguments
        assert "--auto-paste" in call_args
        auto_paste_index = call_args.index("--auto-paste")
        assert call_args[auto_paste_index + 1] == "false"


class TestPopupUIErrorHandling:
    """Test error handling paths in PopupUI."""

    @patch("src.popup_ui.subprocess.run")
    @patch("src.popup_ui.TmuxPaneUtils.get_pane_dimensions")
    @patch("src.popup_ui.TmuxPaneUtils.calculate_popup_position")
    @patch("src.popup_ui.DebugLogger.get_instance")
    @patch("src.popup_ui.FileUtils.cleanup_dir")
    def test_pane_content_write_oserror(
        self, mock_cleanup, mock_get_instance, mock_calc_pos, mock_get_dims, mock_subprocess
    ):
        """Test that OSError when writing pane content is handled gracefully."""
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

        mock_subprocess.return_value = MagicMock()

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

        # Mock file open to raise OSError
        with (
            patch("builtins.open", side_effect=OSError("Permission denied")),
            patch("os.path.join", side_effect=lambda *args: "/".join(args)),
            patch("os.path.exists") as mock_exists,
        ):
            mock_exists.return_value = False
            # Should not raise exception, should continue
            popup_ui._launch_popup()

        # Verify subprocess was still called (fallback behavior)
        assert mock_subprocess.called

    @patch("src.popup_ui.subprocess.run")
    @patch("src.popup_ui.TmuxPaneUtils.get_pane_dimensions")
    @patch("src.popup_ui.DebugLogger.get_instance")
    @patch("src.popup_ui.FileUtils.cleanup_dir")
    def test_popup_dimensions_fallback_on_none(
        self, mock_cleanup, mock_get_instance, mock_get_dims, mock_subprocess
    ):
        """Test fallback to tmux window dimensions when pane dimensions unavailable."""
        mock_logger = MagicMock()
        mock_logger.log_file = ""
        mock_get_instance.return_value = mock_logger

        # Return None to trigger fallback
        mock_get_dims.return_value = None

        tmux_output = "200,50"
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = tmux_output

        mock_subprocess.side_effect = [
            mock_result,
            MagicMock(),
        ]  # First for tmux query, second for popup

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

        with (
            patch("builtins.open", create=True),
            patch("os.path.join", side_effect=lambda *args: "/".join(args)),
            patch("os.path.exists") as mock_exists,
        ):
            mock_exists.return_value = False
            popup_ui._launch_popup()

        # Verify subprocess was called for tmux query
        assert mock_subprocess.called
        first_call = mock_subprocess.call_args_list[0][0][0]
        assert "display-message" in first_call

    @patch("src.popup_ui.subprocess.run")
    @patch("src.popup_ui.TmuxPaneUtils.get_pane_dimensions")
    @patch("src.popup_ui.DebugLogger.get_instance")
    @patch("src.popup_ui.FileUtils.cleanup_dir")
    def test_popup_dimensions_fallback_on_subprocess_error(
        self, mock_cleanup, mock_get_instance, mock_get_dims, mock_subprocess
    ):
        """Test fallback to hardcoded dimensions on subprocess error."""
        mock_logger = MagicMock()
        mock_logger.log_file = ""
        mock_get_instance.return_value = mock_logger

        mock_get_dims.return_value = None

        # First subprocess call raises error (for tmux query), second is popup
        error_result = MagicMock()
        error_result.returncode = 1
        error_result.stdout = ""

        popup_result = MagicMock()
        mock_subprocess.side_effect = [
            subprocess.CalledProcessError(1, "tmux"),
            popup_result,
        ]

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

        with (
            patch("builtins.open", create=True),
            patch("os.path.join", side_effect=lambda *args: "/".join(args)),
            patch("os.path.exists") as mock_exists,
        ):
            mock_exists.return_value = False
            popup_ui._launch_popup()

        # Should still call popup command with fallback dimensions
        assert mock_subprocess.call_count >= 1

    def test_wait_for_result_file_timeout(self):
        """Test that _wait_for_result_file returns None on timeout."""
        config = FlashCopyConfig()
        clipboard = MagicMock(spec=Clipboard)
        search_interface = MagicMock(spec=SearchInterface)

        popup_ui = PopupUI(
            pane_content="test",
            search_interface=search_interface,
            clipboard=clipboard,
            pane_id="test_pane",
            config=config,
        )

        with patch("os.path.exists", return_value=False):
            result = popup_ui._wait_for_result_file("/nonexistent/file.txt", timeout=0.05)

        assert result is None

    def test_wait_for_result_file_success(self):
        """Test that _wait_for_result_file returns content when file exists."""
        config = FlashCopyConfig()
        clipboard = MagicMock(spec=Clipboard)
        search_interface = MagicMock(spec=SearchInterface)

        popup_ui = PopupUI(
            pane_content="test",
            search_interface=search_interface,
            clipboard=clipboard,
            pane_id="test_pane",
            config=config,
        )

        with (
            patch("os.path.exists", return_value=True),
            patch(
                "builtins.open",
                create=True,
            ) as mock_open,
        ):
            mock_open.return_value.__enter__.return_value.read.return_value = "selected text"
            result = popup_ui._wait_for_result_file("/some/file.txt", timeout=1.0)

        assert result == "selected text"

    def test_wait_for_result_file_oserror(self):
        """Test that _wait_for_result_file handles OSError when reading."""
        config = FlashCopyConfig()
        clipboard = MagicMock(spec=Clipboard)
        search_interface = MagicMock(spec=SearchInterface)

        popup_ui = PopupUI(
            pane_content="test",
            search_interface=search_interface,
            clipboard=clipboard,
            pane_id="test_pane",
            config=config,
        )

        call_count = 0

        def exists_side_effect(path):
            nonlocal call_count
            call_count += 1
            return call_count > 5  # Return True after a few calls

        with (
            patch("os.path.exists", side_effect=exists_side_effect),
            patch("builtins.open", side_effect=OSError("Permission denied")),
            patch("time.sleep"),  # Skip actual sleep
        ):
            result = popup_ui._wait_for_result_file("/some/file.txt", timeout=1.0)

        # Eventually returns None on timeout
        assert result is None

    def test_read_paste_flag_missing_file(self):
        """Test that _read_paste_flag handles missing file."""
        config = FlashCopyConfig()
        clipboard = MagicMock(spec=Clipboard)
        search_interface = MagicMock(spec=SearchInterface)

        popup_ui = PopupUI(
            pane_content="test",
            search_interface=search_interface,
            clipboard=clipboard,
            pane_id="test_pane",
            config=config,
        )

        with patch("os.path.exists", return_value=False):
            result = popup_ui._read_paste_flag("/nonexistent/file.txt")

        # Should return False for missing file
        assert result is False

    def test_read_paste_flag_true(self):
        """Test that _read_paste_flag correctly parses true value."""
        config = FlashCopyConfig()
        clipboard = MagicMock(spec=Clipboard)
        search_interface = MagicMock(spec=SearchInterface)

        popup_ui = PopupUI(
            pane_content="test",
            search_interface=search_interface,
            clipboard=clipboard,
            pane_id="test_pane",
            config=config,
        )

        with (
            patch("os.path.exists", return_value=True),
            patch("builtins.open", create=True) as mock_open,
        ):
            mock_open.return_value.__enter__.return_value.read.return_value = "true"
            result = popup_ui._read_paste_flag("/some/file.txt")

        assert result is True

    def test_read_paste_flag_false(self):
        """Test that _read_paste_flag correctly parses false value."""
        config = FlashCopyConfig()
        clipboard = MagicMock(spec=Clipboard)
        search_interface = MagicMock(spec=SearchInterface)

        popup_ui = PopupUI(
            pane_content="test",
            search_interface=search_interface,
            clipboard=clipboard,
            pane_id="test_pane",
            config=config,
        )

        with (
            patch("os.path.exists", return_value=True),
            patch("builtins.open", create=True) as mock_open,
        ):
            mock_open.return_value.__enter__.return_value.read.return_value = "false"
            result = popup_ui._read_paste_flag("/some/file.txt")

        assert result is False

    @patch("src.popup_ui.subprocess.run")
    @patch("src.popup_ui.TmuxPaneUtils.get_pane_dimensions")
    @patch("src.popup_ui.DebugLogger.get_instance")
    @patch("src.popup_ui.FileUtils.cleanup_dir")
    def test_run_exception_cleanup(
        self, mock_cleanup, mock_get_instance, mock_get_dims, mock_subprocess
    ):
        """Test that cleanup is called even when exception occurs."""
        mock_logger = MagicMock()
        mock_logger.log_file = ""
        mock_get_instance.return_value = mock_logger

        mock_get_dims.return_value = None

        # First call succeeds (window dimensions), second fails (popup)
        success_result = MagicMock()
        success_result.returncode = 0
        success_result.stdout = "200,50"

        mock_subprocess.side_effect = [
            success_result,  # First call for window dimensions
            RuntimeError("Subprocess failed"),  # Second call for popup fails
        ]

        config = FlashCopyConfig()
        clipboard = MagicMock(spec=Clipboard)
        search_interface = MagicMock(spec=SearchInterface)
        search_interface.reverse_search = True
        search_interface.word_separators = ""
        search_interface.case_sensitive = False

        popup_ui = PopupUI(
            pane_content="test",
            search_interface=search_interface,
            clipboard=clipboard,
            pane_id="test_pane",
            config=config,
        )

        with (
            patch("os.path.join", side_effect=lambda *args: "/".join(args)),
            patch("builtins.open", create=True),
        ):
            result = popup_ui.run()

        # Should return (None, False) on error
        assert result == (None, False)
        # Cleanup should still be called
        assert mock_cleanup.called
