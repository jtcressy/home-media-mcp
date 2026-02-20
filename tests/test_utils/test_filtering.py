"""Tests for grep filtering utility."""

import json

import pytest
from fastmcp.exceptions import ToolError
from pydantic import BaseModel

from home_media_mcp.utils.filtering import grep_filter


class MockItem(BaseModel):
    id: int
    title: str
    status: str | None = None
    year: int | None = None

    def to_dict(self):
        return {k: v for k, v in self.__dict__.items() if v is not None}

    def to_json(self):
        return json.dumps(self.to_dict())


@pytest.fixture
def sample_items():
    return [
        MockItem(id=1, title="Breaking Bad", status="ended", year=2008),
        MockItem(id=2, title="The Office", status="ended", year=2005),
        MockItem(id=3, title="Stranger Things", status="continuing", year=2016),
    ]


class TestGrepFilter:
    def test_none_pattern_returns_all(self, sample_items):
        result = grep_filter(sample_items, None)
        assert len(result) == 3

    def test_simple_string_match(self, sample_items):
        result = grep_filter(sample_items, "Breaking")
        assert len(result) == 1
        assert result[0].id == 1

    def test_case_insensitive(self, sample_items):
        result = grep_filter(sample_items, "breaking")
        assert len(result) == 1
        assert result[0].id == 1

    def test_regex_pattern(self, sample_items):
        result = grep_filter(sample_items, r"^.*Office.*$")
        assert len(result) == 1
        assert result[0].id == 2

    def test_matches_any_field(self, sample_items):
        # Match on status field
        result = grep_filter(sample_items, "continuing")
        assert len(result) == 1
        assert result[0].id == 3

    def test_matches_numeric_field(self, sample_items):
        result = grep_filter(sample_items, "2008")
        assert len(result) == 1
        assert result[0].id == 1

    def test_no_matches_returns_empty(self, sample_items):
        result = grep_filter(sample_items, "nonexistent")
        assert len(result) == 0

    def test_multiple_matches(self, sample_items):
        result = grep_filter(sample_items, "ended")
        assert len(result) == 2

    def test_invalid_regex_raises_tool_error(self, sample_items):
        with pytest.raises(ToolError, match="Invalid grep pattern"):
            grep_filter(sample_items, "[invalid")

    def test_empty_list(self):
        result = grep_filter([], "test")
        assert result == []

    def test_regex_special_chars(self, sample_items):
        # Dot matches any character
        result = grep_filter(sample_items, "Th.")
        assert len(result) >= 1
