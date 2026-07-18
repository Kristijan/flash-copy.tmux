"""Marker-to-marker range selection over captured pane text."""

from dataclasses import dataclass

from src.search_interface import SearchMatch


@dataclass(frozen=True)
class RangeEndpoint:
    """A character boundary selected from an overlaid search label."""

    offset: int
    line: int
    col: int
    label: str
    copy_start_pos: int
    copy_end_pos: int
    copy_start_col: int
    copy_end_col: int

    @classmethod
    def from_match(cls, match: SearchMatch, fallback_label: str | None = None) -> "RangeEndpoint":
        """Create an endpoint at the boundary where a match label is rendered."""
        label = match.label or fallback_label
        if label is None:
            raise ValueError("A range endpoint requires a labelled match")
        return cls(
            offset=match.label_offset,
            line=match.line,
            col=match.label_col,
            label=label,
            copy_start_pos=match.copy_start_pos,
            copy_end_pos=match.copy_end_pos,
            copy_start_col=match.col + match.copy_start_pos - match.start_pos,
            copy_end_col=match.col + match.copy_end_pos - match.start_pos,
        )


@dataclass(frozen=True)
class ActiveRange:
    """A range with a fixed first endpoint awaiting its second endpoint."""

    start: RangeEndpoint

    @classmethod
    def from_match(cls, match: SearchMatch, fallback_label: str | None = None) -> "ActiveRange":
        """Start a range from a labelled match."""
        return cls(start=RangeEndpoint.from_match(match, fallback_label=fallback_label))

    def accepts(self, match: SearchMatch) -> bool:
        """Return whether a match can complete this range."""
        return match.label_offset != self.start.offset

    def extract(self, pane_content: str, end_match: SearchMatch, copy_mode: str = "word") -> str:
        """Extract text between endpoints using the configured copy mode."""
        end_offset = end_match.label_offset
        if end_offset == self.start.offset:
            raise ValueError("Range endpoints must be different")

        if copy_mode == "word":
            if self.start.offset < end_offset:
                lower = self.start.copy_start_pos
                upper = end_match.copy_end_pos
            else:
                lower = end_match.copy_start_pos
                upper = self.start.copy_end_pos
            return pane_content[lower:upper]

        if copy_mode != "precise":
            raise ValueError(f"Unknown range copy mode: {copy_mode}")
        lower, upper = sorted((self.start.offset, end_offset))
        return pane_content[max(0, lower - 1) : upper]
