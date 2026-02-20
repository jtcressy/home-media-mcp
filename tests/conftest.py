"""Shared test fixtures for home-media-mcp."""

import json
import os
from pathlib import Path
from unittest.mock import MagicMock

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def load_fixture(service: str, name: str) -> dict | list:
    """Load a JSON fixture file."""
    path = FIXTURES_DIR / service / f"{name}.json"
    with open(path) as f:
        return json.load(f)


@pytest.fixture
def sonarr_series_list():
    """List of Sonarr series as raw dicts."""
    return load_fixture("sonarr", "series_list")


@pytest.fixture
def sonarr_series_detail():
    """Single Sonarr series as raw dict."""
    return load_fixture("sonarr", "series_detail")


@pytest.fixture
def sonarr_episodes_list():
    """List of Sonarr episodes as raw dicts."""
    return load_fixture("sonarr", "episodes_list")


@pytest.fixture
def radarr_movie_list():
    """List of Radarr movies as raw dicts."""
    return load_fixture("radarr", "movie_list")


@pytest.fixture
def radarr_movie_detail():
    """Single Radarr movie as raw dict."""
    return load_fixture("radarr", "movie_detail")


@pytest.fixture
def quality_profiles():
    """Quality profiles as raw dicts (shared format for both services)."""
    return load_fixture("shared", "quality_profiles")


@pytest.fixture
def root_folders():
    """Root folders as raw dicts (shared format for both services)."""
    return load_fixture("shared", "root_folders")


@pytest.fixture
def tags():
    """Tags as raw dicts (shared format for both services)."""
    return load_fixture("shared", "tags")
