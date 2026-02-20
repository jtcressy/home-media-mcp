"""Tests for name-to-ID resolution utilities."""

import pytest
from fastmcp.exceptions import ToolError

from home_media_mcp.utils.resolution import (
    resolve_quality_profile,
    resolve_root_folder,
    resolve_tag,
)


class MockProfile:
    def __init__(self, id, name):
        self.id = id
        self.name = name


class MockFolder:
    def __init__(self, id, path):
        self.id = id
        self.path = path


class MockTag:
    def __init__(self, id, label):
        self.id = id
        self.label = label


@pytest.fixture
def profiles():
    return [
        MockProfile(1, "HD-1080p"),
        MockProfile(2, "Ultra-HD"),
        MockProfile(3, "Any"),
    ]


@pytest.fixture
def folders():
    return [
        MockFolder(1, "/tv"),
        MockFolder(2, "/movies"),
        MockFolder(3, "/media/4k"),
    ]


@pytest.fixture
def tag_list():
    return [MockTag(1, "favorite"), MockTag(2, "4k"), MockTag(3, "kids")]


class TestResolveQualityProfile:
    def test_resolve_by_int_id(self, profiles):
        assert resolve_quality_profile(1, profiles) == 1

    def test_resolve_by_string_id(self, profiles):
        assert resolve_quality_profile("2", profiles) == 2

    def test_resolve_by_name(self, profiles):
        assert resolve_quality_profile("HD-1080p", profiles) == 1

    def test_resolve_by_name_case_insensitive(self, profiles):
        assert resolve_quality_profile("hd-1080p", profiles) == 1

    def test_not_found_by_id(self, profiles):
        with pytest.raises(ToolError, match="not found"):
            resolve_quality_profile(99, profiles)

    def test_not_found_by_name(self, profiles):
        with pytest.raises(ToolError, match="No quality profile"):
            resolve_quality_profile("nonexistent", profiles)

    def test_shows_available_on_error(self, profiles):
        with pytest.raises(ToolError, match="HD-1080p"):
            resolve_quality_profile("nonexistent", profiles)


class TestResolveRootFolder:
    def test_resolve_by_int_id(self, folders):
        assert resolve_root_folder(1, folders) == 1

    def test_resolve_by_string_id(self, folders):
        assert resolve_root_folder("2", folders) == 2

    def test_resolve_by_exact_path(self, folders):
        assert resolve_root_folder("/tv", folders) == 1

    def test_resolve_by_path_substring(self, folders):
        assert resolve_root_folder("4k", folders) == 3

    def test_resolve_path_case_insensitive(self, folders):
        assert resolve_root_folder("/TV", folders) == 1

    def test_ambiguous_path(self, folders):
        # "/m" matches both "/movies" and "/media/4k"
        with pytest.raises(ToolError, match="Ambiguous"):
            resolve_root_folder("/m", folders)

    def test_not_found_by_id(self, folders):
        with pytest.raises(ToolError, match="not found"):
            resolve_root_folder(99, folders)

    def test_not_found_by_path(self, folders):
        with pytest.raises(ToolError, match="No root folder"):
            resolve_root_folder("/nonexistent", folders)


class TestResolveTag:
    def test_resolve_by_int_id(self, tag_list):
        assert resolve_tag(1, tag_list) == 1

    def test_resolve_by_string_id(self, tag_list):
        assert resolve_tag("2", tag_list) == 2

    def test_resolve_by_name(self, tag_list):
        assert resolve_tag("favorite", tag_list) == 1

    def test_resolve_by_name_case_insensitive(self, tag_list):
        assert resolve_tag("FAVORITE", tag_list) == 1

    def test_not_found_by_id(self, tag_list):
        with pytest.raises(ToolError, match="not found"):
            resolve_tag(99, tag_list)

    def test_not_found_by_name(self, tag_list):
        with pytest.raises(ToolError, match="No tag"):
            resolve_tag("nonexistent", tag_list)
