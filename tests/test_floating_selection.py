"""Search results through the real floating terminal and snapshot transport."""

import time
from concurrent.futures import ThreadPoolExecutor

from src.clipboard import Clipboard
from src.config import FlashCopyConfig
from src.floating_pane import FloatingPane
from src.popup_ui import PopupUI
from src.search_interface import SearchInterface
from tests.test_floating_pane import attached_tmux as attached_tmux


def test_floating_selection_survives_popup_idle_timeout(attached_tmux):
    tmux, source, client = attached_tmux
    snapshot = "hello world\n"

    def search():
        with FloatingPane(source, client) as floating:
            return PopupUI(
                pane_content=snapshot,
                search_interface=SearchInterface(snapshot),
                clipboard=Clipboard(),
                pane_id=source,
                config=FlashCopyConfig(idle_timeout=1, idle_warning=0),
                client_name=client,
                floating=floating,
            ).run()

    with ThreadPoolExecutor(max_workers=1) as executor:
        result = executor.submit(search)
        helper = ""
        try:
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline:
                helper = tmux("display-message", "-p", "-t", source, "#{@flash-copy-search-pane}")
                if helper and "search..." in tmux("capture-pane", "-p", "-t", helper, check=False):
                    break
                if result.done():
                    raise AssertionError(f"Search ended before input: {result.result()}")
                time.sleep(0.02)
            else:
                raise AssertionError("Floating search did not render its prompt")
            tmux("send-keys", "-t", helper, "-l", "he")
            time.sleep(1.2)
            rendered = tmux("capture-pane", "-p", "-t", helper)
            assert "> he" in rendered
            assert "Idle, terminating" not in rendered
            tmux("send-keys", "-t", helper, "Enter")
            assert result.result(timeout=5) == ("hello", False)
        finally:
            if not result.done() and helper:
                tmux("kill-pane", "-t", helper, check=False)
            result.result(timeout=10)

    assert not tmux("display-message", "-p", "-t", source, "#{@flash-copy-search-pane}")
    assert "__tmux_flash_copy_" not in tmux("list-buffers", "-F", "#{buffer_name}")
