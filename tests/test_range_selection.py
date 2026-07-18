"""Tests for marker-to-marker range selection."""

import pytest

from src.range_selection import ActiveRange, RangeEndpoint
from src.search_interface import SearchInterface, SearchMatch


def make_match(
    *,
    text: str,
    start_pos: int,
    line: int,
    col: int,
    match_start: int,
    match_end: int,
    label: str = "a",
    copy_start_pos: int | None = None,
    copy_end_pos: int | None = None,
) -> SearchMatch:
    """Build a labelled search match for range tests."""
    match = SearchMatch(
        text=text,
        start_pos=start_pos,
        end_pos=start_pos + len(text),
        line=line,
        col=col,
        copy_start_pos=copy_start_pos,
        copy_end_pos=copy_end_pos,
    )
    match.match_start = match_start
    match.match_end = match_end
    match.label = label
    return match


def test_endpoint_uses_the_boundary_after_the_matched_query():
    match = make_match(
        text="hello", start_pos=10, line=2, col=4, match_start=1, match_end=3, label="q"
    )

    endpoint = RangeEndpoint.from_match(match)

    assert endpoint.offset == 13
    assert endpoint.line == 2
    assert endpoint.col == 7
    assert endpoint.label == "q"


def test_endpoint_requires_a_label_or_fallback():
    match = make_match(text="hello", start_pos=0, line=0, col=0, match_start=0, match_end=2)
    match.label = None

    with pytest.raises(ValueError, match="requires a labelled match"):
        RangeEndpoint.from_match(match)


def test_word_range_is_default_and_includes_both_endpoint_words_in_either_direction():
    content = "hello world"
    left = make_match(
        text="hello",
        start_pos=0,
        line=0,
        col=0,
        match_start=0,
        match_end=2,
        copy_start_pos=0,
        copy_end_pos=5,
    )
    right = make_match(
        text="world",
        start_pos=6,
        line=0,
        col=6,
        match_start=0,
        match_end=1,
        label="s",
        copy_start_pos=6,
        copy_end_pos=11,
    )

    assert ActiveRange.from_match(left).extract(content, right) == "hello world"
    assert ActiveRange.from_match(right).extract(content, left) == "hello world"


def test_word_range_uses_search_copy_boundaries_and_preserves_internal_separators():
    content = '"hello", [world]!'
    search = SearchInterface(
        content,
        reverse_search=False,
        word_separators=' " ,[]!',
    )
    left = search.search("he")[0]
    right = search.search("wo")[0]

    assert ActiveRange.from_match(left).extract(content, right) == 'hello", [world'


def test_distinct_endpoints_in_the_same_word_copy_the_whole_word():
    content = "hello"
    search = SearchInterface(content, reverse_search=False, word_separators=" ")
    left = search.search("he")[0]
    right = search.search("lo")[0]

    assert ActiveRange.from_match(left).extract(content, right) == "hello"


def test_precise_range_includes_final_match_character_in_either_direction():
    content = "hello world"
    left = make_match(text="hello", start_pos=0, line=0, col=0, match_start=0, match_end=2)
    right = make_match(
        text="world", start_pos=6, line=0, col=6, match_start=0, match_end=1, label="s"
    )

    assert ActiveRange.from_match(left).extract(content, right, copy_mode="precise") == "ello w"
    assert ActiveRange.from_match(right).extract(content, left, copy_mode="precise") == "ello w"


def test_extracts_continuous_multiline_text_and_preserves_whitespace():
    content = "one  \n  two\nthree"
    upper = make_match(text="one", start_pos=0, line=0, col=0, match_start=0, match_end=3)
    lower = make_match(
        text="three", start_pos=12, line=2, col=0, match_start=0, match_end=2, label="s"
    )

    assert (
        ActiveRange.from_match(lower).extract(content, upper, copy_mode="precise")
        == "e  \n  two\nth"
    )


def test_extracts_unicode_by_character_boundary():
    content = "αβγ hello 🌙"
    left = make_match(text="αβγ", start_pos=0, line=0, col=0, match_start=0, match_end=2)
    right = make_match(
        text="🌙", start_pos=10, line=0, col=10, match_start=0, match_end=1, label="s"
    )

    assert (
        ActiveRange.from_match(left).extract(content, right, copy_mode="precise") == "βγ hello 🌙"
    )


def test_identical_endpoint_is_not_eligible_and_cannot_be_extracted():
    match = make_match(text="hello", start_pos=0, line=0, col=0, match_start=0, match_end=2)
    active_range = ActiveRange.from_match(match)

    assert active_range.accepts(match) is False
    with pytest.raises(ValueError, match="different"):
        active_range.extract("hello", match)


def test_extract_rejects_an_unknown_copy_mode():
    content = "hello world"
    start = make_match(text="hello", start_pos=0, line=0, col=0, match_start=0, match_end=2)
    end = make_match(
        text="world", start_pos=6, line=0, col=6, match_start=0, match_end=1, label="s"
    )

    with pytest.raises(ValueError, match="Unknown range copy mode: invalid"):
        ActiveRange.from_match(start).extract(content, end, copy_mode="invalid")


def test_fallback_marker_allows_unlabelled_matches_for_enter_selection():
    start = make_match(text="hello", start_pos=0, line=0, col=0, match_start=0, match_end=2)
    start.label = None
    end = make_match(text="world", start_pos=6, line=0, col=6, match_start=0, match_end=1)
    end.label = None

    active_range = ActiveRange.from_match(start, fallback_label=",")

    assert active_range.start.label == ","
    assert active_range.extract("hello world", end, copy_mode="precise") == "ello w"


def test_search_excludes_offsets_and_reserves_labels_before_assignment():
    search = SearchInterface("hello hello", reverse_search=False, label_characters="asdf")
    initial_matches = search.search("he")
    pinned = initial_matches[0]
    assert pinned.label == "a"

    second_matches = search.search(
        "he",
        excluded_label_offsets={pinned.label_offset},
        reserved_labels={pinned.label},
    )

    assert [match.label_offset for match in second_matches] == [8]
    assert second_matches[0].label == "s"
