"""Shared fixtures for tool-level tests.

These tests verify that each tool calls the correct API class and method.
We patch the API classes (e.g. sonarr.SeriesApi) so no real HTTP calls are made,
and we swap the server's lifespan to inject mock clients into the context.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from typing import Any
from unittest.mock import MagicMock

import pytest
from fastmcp import FastMCP
from fastmcp.server.lifespan import lifespan


def make_mock_model(**kwargs: Any) -> MagicMock:
    """Create a mock devopsarr model with a to_dict() method."""
    m = MagicMock()
    m.to_dict.return_value = kwargs
    return m


def make_mock_paged(records: list, total: int | None = None) -> MagicMock:
    """Create a mock paged resource (.records, .total_records)."""
    m = MagicMock()
    m.records = records
    m.total_records = total if total is not None else len(records)
    return m


@pytest.fixture(autouse=True)
def _set_test_env(monkeypatch):
    """Ensure config sees both services as configured for all tool tests."""
    monkeypatch.setenv("SONARR_URL", "http://sonarr.test")
    monkeypatch.setenv("SONARR_API_KEY", "test-sonarr-key")
    monkeypatch.setenv("RADARR_URL", "http://radarr.test")
    monkeypatch.setenv("RADARR_API_KEY", "test-radarr-key")


@pytest.fixture
def mock_sonarr_client() -> MagicMock:
    return MagicMock(name="sonarr_client")


@pytest.fixture
def mock_radarr_client() -> MagicMock:
    return MagicMock(name="radarr_client")


@pytest.fixture
def patched_mcp(mock_sonarr_client, mock_radarr_client):
    """Return the shared mcp with both mock clients injected via a test lifespan."""
    # Import main to trigger tool registration (env vars are set by _set_test_env)
    import home_media_mcp.main  # noqa: F401
    from home_media_mcp.server import mcp

    @lifespan
    async def _test_lifespan(server: FastMCP) -> AsyncIterator[dict]:
        yield {
            "sonarr_client": mock_sonarr_client,
            "radarr_client": mock_radarr_client,
        }

    original_lifespan = mcp._lifespan
    mcp._lifespan = _test_lifespan
    yield mcp
    mcp._lifespan = original_lifespan
