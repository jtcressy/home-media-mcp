"""Tests for response formatting utilities."""

import json
from unittest.mock import MagicMock

import pytest
from pydantic import BaseModel

from home_media_mcp.utils.formatting import full_detail, summarize_item, summarize_list


class SampleModel(BaseModel):
    """A test model that mimics devopsarr model behavior."""

    id: int | None = None
    title: str | None = None
    year: int | None = None
    status: str | None = None
    monitored: bool | None = None
    path: str | None = None
    overview: str | None = None
    added: str | None = None
    sort_title: str | None = None
    tags: list[int] | None = None
    statistics: dict | None = None
    images: list[dict] | None = None

    def to_dict(self):
        """Mimic devopsarr model to_dict (returns camelCase keys)."""
        result = {}
        for key, value in self.__dict__.items():
            if value is not None:
                result[key] = value
        return result

    def to_json(self):
        """Mimic devopsarr model to_json."""
        return json.dumps(self.to_dict())


class SmallModel(BaseModel):
    """A model with fewer than 10 scalar fields."""

    id: int | None = None
    name: str | None = None
    active: bool | None = None

    def to_dict(self):
        result = {}
        for key, value in self.__dict__.items():
            if value is not None:
                result[key] = value
        return result

    def to_json(self):
        return json.dumps(self.to_dict())


class TestSummarizeItem:
    """Tests for summarize_item."""

    def test_returns_dict(self):
        item = SampleModel(id=1, title="Test", year=2024)
        result = summarize_item(item)
        assert isinstance(result, dict)

    def test_id_always_included(self):
        item = SampleModel(
            id=1,
            title="Test",
            year=2024,
            status="ended",
            monitored=True,
            path="/a/very/long/path/to/something",
            overview="A" * 500,
            added="2024-01-01T00:00:00Z",
            sort_title="test",
        )
        result = summarize_item(item, max_fields=3)
        assert "id" in result

    def test_excludes_non_scalar_fields(self):
        item = SampleModel(
            id=1,
            title="Test",
            tags=[1, 2, 3],
            statistics={"count": 5},
            images=[{"url": "http://example.com"}],
        )
        result = summarize_item(item)
        assert "tags" not in result
        assert "statistics" not in result
        assert "images" not in result

    def test_sorts_by_size_ascending(self):
        item = SampleModel(
            id=1,
            title="Short",
            overview="A" * 500,  # very long
            year=2024,
            status="ok",
            monitored=True,
        )
        result = summarize_item(item, max_fields=4)
        # overview is the longest, should be excluded with max_fields=4
        # (id + 3 smallest scalars)
        assert "overview" not in result
        assert "id" in result

    def test_respects_max_fields(self):
        item = SampleModel(
            id=1,
            title="Test",
            year=2024,
            status="ended",
            monitored=True,
            path="/tv/Test",
            overview="Some overview text",
            added="2024-01-01T00:00:00Z",
            sort_title="test",
        )
        result = summarize_item(item, max_fields=5)
        assert len(result) <= 5

    def test_fewer_fields_than_max(self):
        item = SmallModel(id=1, name="Test", active=True)
        result = summarize_item(item, max_fields=10)
        # Should include all 3 fields
        assert len(result) == 3
        assert result["id"] == 1
        assert result["name"] == "Test"
        assert result["active"] is True

    def test_handles_none_values(self):
        item = SampleModel(id=1, title=None, year=2024)
        result = summarize_item(item)
        # None values are scalar and should be included
        assert "id" in result

    def test_no_id_field(self):
        item = SmallModel(name="Test", active=True)
        result = summarize_item(item, max_fields=10)
        assert "id" not in result
        assert "name" in result


class TestSummarizeList:
    """Tests for summarize_list."""

    def test_returns_summary_and_items(self):
        items = [SampleModel(id=1, title="A"), SampleModel(id=2, title="B")]
        result = summarize_list(items)
        assert "summary" in result
        assert "items" in result
        assert result["summary"]["total"] == 2
        assert len(result["items"]) == 2

    def test_empty_list(self):
        result = summarize_list([])
        assert result["summary"]["total"] == 0
        assert result["items"] == []

    def test_summary_fn_called(self):
        items = [
            SampleModel(id=1, monitored=True),
            SampleModel(id=2, monitored=False),
        ]

        def my_summary(items):
            monitored = sum(1 for i in items if i.monitored)
            return {"monitored": monitored}

        result = summarize_list(items, summary_fn=my_summary)
        assert result["summary"]["total"] == 2
        assert result["summary"]["monitored"] == 1

    def test_summary_fn_none(self):
        items = [SampleModel(id=1)]
        result = summarize_list(items, summary_fn=None)
        assert result["summary"] == {"total": 1}

    def test_max_fields_passed_through(self):
        items = [
            SampleModel(
                id=1,
                title="Test",
                year=2024,
                status="ok",
                monitored=True,
                path="/long/path",
                overview="x" * 200,
                added="2024-01-01",
                sort_title="test",
            )
        ]
        result = summarize_list(items, max_fields=3)
        assert len(result["items"][0]) <= 3


class TestFullDetail:
    """Tests for full_detail."""

    def test_returns_complete_dict(self):
        item = SampleModel(
            id=1,
            title="Test",
            tags=[1, 2],
            statistics={"count": 5},
        )
        result = full_detail(item)
        assert result["id"] == 1
        assert result["title"] == "Test"
        assert result["tags"] == [1, 2]
        assert result["statistics"] == {"count": 5}

    def test_includes_nested_objects(self):
        item = SampleModel(
            id=1,
            images=[{"coverType": "poster", "url": "http://example.com"}],
        )
        result = full_detail(item)
        assert "images" in result
        assert len(result["images"]) == 1
