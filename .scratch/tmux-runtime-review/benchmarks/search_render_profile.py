"""Read-only benchmark harness for the tmux-flash-copy discovery review."""

# ruff: noqa: E402, I001

from __future__ import annotations

import importlib.util
import io
import statistics
import sys
import time
import tracemalloc
from contextlib import redirect_stderr
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.config import FlashCopyConfig
from src.search_interface import SearchInterface


INTERACTIVE_PATH = ROOT / "bin" / "tmux-flash-copy-interactive.py"
SPEC = importlib.util.spec_from_file_location("flash_copy_interactive_benchmark", INTERACTIVE_PATH)
assert SPEC and SPEC.loader
INTERACTIVE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(INTERACTIVE)


def timed(function, repetitions: int = 5) -> tuple[float, float]:
    samples = []
    for _ in range(repetitions):
        started = time.perf_counter()
        function()
        samples.append((time.perf_counter() - started) * 1000)
    return statistics.median(samples), max(samples)


def scenario(name: str, lines: int, columns: int, query: str, dense: bool = False) -> None:
    if dense:
        unit = "a "
        line = (unit * (columns // len(unit) + 1))[:columns]
    else:
        unit = "alpha beta gamma delta epsilon "
        line = (unit * (columns // len(unit) + 1))[:columns]
    content = "\n".join(line for _ in range(lines))

    tracemalloc.start()
    started = time.perf_counter()
    search = SearchInterface(content, reverse_search=False)
    build_ms = (time.perf_counter() - started) * 1000
    _current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    search_median, search_max = timed(lambda: search.search(query))
    matches = search.search(query)

    config = FlashCopyConfig(range_selection_enable=False)
    ui = INTERACTIVE.InteractiveUI("%1", content, {}, config)
    ui.search_query = query
    ui.current_matches = ui.search_interface.search(query)
    rows = content.splitlines()

    def render() -> None:
        with redirect_stderr(io.StringIO()):
            ui._display_pane_content(rows, rows, lines)

    render_median, render_max = timed(render, repetitions=3)

    def lookup_sweep() -> None:
        for line_number in range(lines):
            search.get_matches_at_line(line_number)

    lookup_median, lookup_max = timed(lookup_sweep)

    print(
        "| "
        + " | ".join(
            [
                name,
                f"{lines}x{columns}",
                str(len(content)),
                str(len(matches)),
                f"{build_ms:.2f}",
                f"{search_median:.2f}",
                f"{render_median:.2f}",
                f"{lookup_median:.2f}",
                f"{peak / 1024 / 1024:.2f}",
            ]
        )
        + " |"
    )


if __name__ == "__main__":
    print(
        "| Scenario | Shape | Characters | Matches | Build ms | Search ms | "
        "Render ms | Match lookup sweep ms | Build peak MiB |"
    )
    print("| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
    scenario("ordinary", 24, 120, "alp")
    scenario("large", 200, 240, "alp")
    scenario("very large", 1_000, 500, "alp")
    scenario("dense matches", 200, 240, "a", dense=True)
    scenario("dense very large", 1_000, 500, "a", dense=True)
