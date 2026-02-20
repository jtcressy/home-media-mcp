"""Tool-level tests for Sonarr tools.

Each test verifies:
1. The correct API class is instantiated (catches wrong class name bugs).
2. The correct method is called on that class (catches wrong method name bugs).
3. The tool returns a sensible result structure.
"""

from unittest.mock import MagicMock, patch

import pytest
from fastmcp.client import Client

from tests.test_tools.conftest import make_mock_model, make_mock_paged


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_series(**kwargs) -> MagicMock:
    defaults = dict(
        id=1,
        title="Test Series",
        year=2020,
        monitored=True,
        status="continuing",
        quality_profile_id=1,
        runtime=45,
        tvdb_id=12345,
    )
    defaults.update(kwargs)
    return make_mock_model(**defaults)


def _mock_episode(**kwargs) -> MagicMock:
    defaults = dict(
        id=10,
        series_id=1,
        season_number=1,
        episode_number=1,
        title="Pilot",
        monitored=True,
        has_file=True,
    )
    defaults.update(kwargs)
    return make_mock_model(**defaults)


def _mock_history_record(**kwargs) -> MagicMock:
    defaults = dict(id=100, series_id=1, episode_id=10, event_type="grabbed")
    defaults.update(kwargs)
    return make_mock_model(**defaults)


# ---------------------------------------------------------------------------
# System tools
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sonarr_get_system_status(patched_mcp):
    mock_status = make_mock_model(appName="Sonarr", version="4.0.0")
    mock_api = MagicMock()
    mock_api.get_system_status.return_value = mock_status

    with patch("sonarr.SystemApi", return_value=mock_api) as mock_cls:
        async with Client(patched_mcp) as client:
            result = await client.call_tool("sonarr_get_system_status", {})

    mock_cls.assert_called_once()
    mock_api.get_system_status.assert_called_once()
    assert result.data["appName"] == "Sonarr"


@pytest.mark.asyncio
async def test_sonarr_list_health_checks(patched_mcp):
    mock_item = make_mock_model(source="TestCheck", type="warning", message="ok")
    mock_api = MagicMock()
    mock_api.list_health.return_value = [mock_item]

    with patch("sonarr.HealthApi", return_value=mock_api):
        async with Client(patched_mcp) as client:
            result = await client.call_tool("sonarr_list_health_checks", {})

    mock_api.list_health.assert_called_once()
    assert result.data["summary"]["total"] == 1


@pytest.mark.asyncio
async def test_sonarr_get_disk_space(patched_mcp):
    mock_item = make_mock_model(path="/media", freeSpace=1000, totalSpace=2000)
    mock_api = MagicMock()
    mock_api.list_disk_space.return_value = [mock_item]

    with patch("sonarr.DiskSpaceApi", return_value=mock_api):
        async with Client(patched_mcp) as client:
            result = await client.call_tool("sonarr_get_disk_space", {})

    mock_api.list_disk_space.assert_called_once()
    assert result.data["summary"]["total"] == 1


# ---------------------------------------------------------------------------
# Series tools
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sonarr_list_series(patched_mcp):
    mock_api = MagicMock()
    mock_api.list_series.return_value = [_mock_series(), _mock_series(id=2)]

    with patch("sonarr.SeriesApi", return_value=mock_api):
        async with Client(patched_mcp) as client:
            result = await client.call_tool("sonarr_list_series", {})

    mock_api.list_series.assert_called_once()
    assert result.data["summary"]["total"] == 2


@pytest.mark.asyncio
async def test_sonarr_list_series_grep(patched_mcp):
    """grep filters the list before returning."""
    s1 = _mock_series(id=1, title="Breaking Bad")
    s1.to_dict.return_value["title"] = "Breaking Bad"
    s2 = _mock_series(id=2, title="Better Call Saul")
    s2.to_dict.return_value["title"] = "Better Call Saul"

    mock_api = MagicMock()
    mock_api.list_series.return_value = [s1, s2]

    # to_dict is used by grep_filter via _encoder.encode(item.to_dict())
    with patch("sonarr.SeriesApi", return_value=mock_api):
        async with Client(patched_mcp) as client:
            result = await client.call_tool("sonarr_list_series", {"grep": "Breaking"})

    assert result.data["summary"]["total"] == 1


@pytest.mark.asyncio
async def test_sonarr_describe_series(patched_mcp):
    mock_api = MagicMock()
    mock_api.get_series_by_id.return_value = _mock_series(id=42)

    with patch("sonarr.SeriesApi", return_value=mock_api):
        async with Client(patched_mcp) as client:
            result = await client.call_tool("sonarr_describe_series", {"id": 42})

    mock_api.get_series_by_id.assert_called_once_with(id=42)
    assert result.data["id"] == 42


# ---------------------------------------------------------------------------
# Episode tools
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sonarr_list_episodes(patched_mcp):
    mock_api = MagicMock()
    mock_api.list_episode.return_value = [_mock_episode(), _mock_episode(id=11)]

    with patch("sonarr.EpisodeApi", return_value=mock_api):
        async with Client(patched_mcp) as client:
            result = await client.call_tool("sonarr_list_episodes", {"series_id": 1})

    mock_api.list_episode.assert_called_once_with(series_id=1)
    assert result.data["summary"]["total"] == 2


# ---------------------------------------------------------------------------
# History tools
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sonarr_list_history_uses_get_history(patched_mcp):
    """Must use get_history (not list_history) on HistoryApi."""
    mock_api = MagicMock()
    mock_api.get_history.return_value = make_mock_paged([_mock_history_record()])

    with patch("sonarr.HistoryApi", return_value=mock_api) as mock_cls:
        async with Client(patched_mcp) as client:
            result = await client.call_tool("sonarr_list_history", {})

    mock_cls.assert_called_once()
    mock_api.get_history.assert_called_once()
    # Ensure list_history was NOT called (it doesn't exist)
    mock_api.list_history.assert_not_called()
    assert result.data["summary"]["total"] == 1


@pytest.mark.asyncio
async def test_sonarr_list_series_history_uses_list_history_series(patched_mcp):
    """Must use list_history_series (not list_history) for per-series history."""
    mock_api = MagicMock()
    mock_api.list_history_series.return_value = [_mock_history_record()]

    with patch("sonarr.HistoryApi", return_value=mock_api):
        async with Client(patched_mcp) as client:
            result = await client.call_tool(
                "sonarr_list_series_history", {"series_id": 1}
            )

    mock_api.list_history_series.assert_called_once_with(series_id=1)
    mock_api.list_history.assert_not_called()


# ---------------------------------------------------------------------------
# Queue tools
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sonarr_list_queue_uses_queue_details_api(patched_mcp):
    """Must use QueueDetailsApi.list_queue_details (not QueueApi.list_queue_details)."""
    mock_api = MagicMock()
    mock_api.list_queue_details.return_value = []

    with patch("sonarr.QueueDetailsApi", return_value=mock_api) as mock_cls:
        with patch("sonarr.QueueApi") as mock_wrong_cls:
            async with Client(patched_mcp) as client:
                result = await client.call_tool("sonarr_list_queue", {})

    mock_cls.assert_called_once()
    mock_api.list_queue_details.assert_called_once()
    mock_wrong_cls.assert_not_called()
    assert result.data["summary"]["total"] == 0


# ---------------------------------------------------------------------------
# Wanted tools
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sonarr_list_missing_uses_missing_api(patched_mcp):
    """Must use MissingApi.get_wanted_missing (not WantedMissingApi.list_wanted_missing)."""
    mock_api = MagicMock()
    mock_api.get_wanted_missing.return_value = make_mock_paged([])

    with patch("sonarr.MissingApi", return_value=mock_api) as mock_cls:
        async with Client(patched_mcp) as client:
            result = await client.call_tool("sonarr_list_missing", {})

    mock_cls.assert_called_once()
    mock_api.get_wanted_missing.assert_called_once()


@pytest.mark.asyncio
async def test_sonarr_list_cutoff_unmet_uses_cutoff_api(patched_mcp):
    """Must use CutoffApi.get_wanted_cutoff (not WantedCutoffApi.list_wanted_cutoff)."""
    mock_api = MagicMock()
    mock_api.get_wanted_cutoff.return_value = make_mock_paged([])

    with patch("sonarr.CutoffApi", return_value=mock_api) as mock_cls:
        async with Client(patched_mcp) as client:
            result = await client.call_tool("sonarr_list_cutoff_unmet", {})

    mock_cls.assert_called_once()
    mock_api.get_wanted_cutoff.assert_called_once()


# ---------------------------------------------------------------------------
# Blocklist tools
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sonarr_list_blocklist_uses_get_blocklist(patched_mcp):
    """Must use BlocklistApi.get_blocklist (not list_blocklist)."""
    mock_api = MagicMock()
    mock_api.get_blocklist.return_value = make_mock_paged([])

    with patch("sonarr.BlocklistApi", return_value=mock_api) as mock_cls:
        async with Client(patched_mcp) as client:
            result = await client.call_tool("sonarr_list_blocklist", {})

    mock_cls.assert_called_once()
    mock_api.get_blocklist.assert_called_once()
    mock_api.list_blocklist.assert_not_called()


# ---------------------------------------------------------------------------
# Rename tools
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sonarr_preview_rename_uses_rename_episode_api(patched_mcp):
    """Must use RenameEpisodeApi.list_rename (not RenameApi.list_rename)."""
    mock_rename = make_mock_model(seriesId=1, seasonNumber=1, episodeNumbers=[1])
    mock_api = MagicMock()
    mock_api.list_rename.return_value = [mock_rename]

    with patch("sonarr.RenameEpisodeApi", return_value=mock_api) as mock_cls:
        async with Client(patched_mcp) as client:
            result = await client.call_tool("sonarr_preview_rename", {"series_id": 1})

    mock_cls.assert_called_once()
    mock_api.list_rename.assert_called_once_with(series_id=1)


# ---------------------------------------------------------------------------
# Lookup tools
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sonarr_lookup_series_uses_series_lookup_api(patched_mcp):
    """Must use SeriesLookupApi.list_series_lookup (not SeriesApi.list_series_lookup)."""
    mock_api = MagicMock()
    mock_api.list_series_lookup.return_value = [_mock_series(id=99, title="Severance")]
    with patch("sonarr.SeriesLookupApi", return_value=mock_api) as mock_cls:
        with patch("sonarr.SeriesApi") as mock_wrong_cls:
            async with Client(patched_mcp) as client:
                result = await client.call_tool(
                    "sonarr_lookup_series", {"term": "Severance"}
                )
    mock_cls.assert_called_once()
    mock_api.list_series_lookup.assert_called_once_with(term="Severance")
    mock_wrong_cls.assert_not_called()
    assert result.data["summary"]["total"] == 1


# ---------------------------------------------------------------------------
# Reference tools
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sonarr_list_quality_profiles(patched_mcp):
    mock_api = MagicMock()
    mock_api.list_quality_profile.return_value = [
        make_mock_model(id=1, name="Any"),
        make_mock_model(id=7, name="WEB-2160p"),
    ]

    with patch("sonarr.QualityProfileApi", return_value=mock_api):
        async with Client(patched_mcp) as client:
            result = await client.call_tool("sonarr_list_quality_profiles", {})

    mock_api.list_quality_profile.assert_called_once()
    assert result.data["summary"]["total"] == 2


@pytest.mark.asyncio
async def test_sonarr_list_root_folders(patched_mcp):
    mock_api = MagicMock()
    mock_api.list_root_folder.return_value = [
        make_mock_model(id=1, path="/media/tv", freeSpace=100000),
    ]

    with patch("sonarr.RootFolderApi", return_value=mock_api):
        async with Client(patched_mcp) as client:
            result = await client.call_tool("sonarr_list_root_folders", {})

    mock_api.list_root_folder.assert_called_once()
    assert result.data["summary"]["total"] == 1


@pytest.mark.asyncio
async def test_sonarr_list_tags(patched_mcp):
    mock_api = MagicMock()
    mock_api.list_tag.return_value = [make_mock_model(id=1, label="hd")]

    with patch("sonarr.TagApi", return_value=mock_api):
        async with Client(patched_mcp) as client:
            result = await client.call_tool("sonarr_list_tags", {})

    mock_api.list_tag.assert_called_once()
    assert result.data["summary"]["total"] == 1
