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


# ---------------------------------------------------------------------------
# Series write tools
# ---------------------------------------------------------------------------

from sonarr.exceptions import NotFoundException as _SonarrNotFoundException  # noqa: E402


def _make_qp_mock(id: int = 1, name: str = "Any") -> MagicMock:
    """Create a quality profile mock with real .id and .name attributes."""
    m = make_mock_model(id=id, name=name)
    m.id = id
    m.name = name
    return m


def _make_rf_mock(id: int = 1, path: str = "/tv") -> MagicMock:
    """Create a root folder mock with real .id and .path attributes."""
    m = make_mock_model(id=id, path=path)
    m.id = id
    m.path = path
    return m


@pytest.mark.asyncio
async def test_sonarr_describe_series_not_found(patched_mcp):
    mock_api = MagicMock()
    mock_api.get_series_by_id.side_effect = _SonarrNotFoundException()

    with patch("sonarr.SeriesApi", return_value=mock_api):
        async with Client(patched_mcp) as client:
            result = await client.call_tool("sonarr_describe_series", {"id": 999})

    assert result.data["error"] == "not_found"


@pytest.mark.asyncio
async def test_sonarr_add_series_happy_path(patched_mcp):
    qp_mock_api = MagicMock()
    qp_mock_api.list_quality_profile.return_value = [_make_qp_mock(id=1, name="Any")]

    rf_mock_api = MagicMock()
    rf_mock_api.list_root_folder.return_value = [_make_rf_mock(id=1, path="/tv")]

    series_data_mock = MagicMock()
    series_lookup_mock_api = MagicMock()
    series_lookup_mock_api.list_series_lookup.return_value = [series_data_mock]

    series_mock_api = MagicMock()
    series_mock_api.create_series.return_value = make_mock_model(id=10, title="Test")

    with patch("sonarr.QualityProfileApi", return_value=qp_mock_api):
        with patch("sonarr.RootFolderApi", return_value=rf_mock_api):
            with patch("sonarr.SeriesLookupApi", return_value=series_lookup_mock_api):
                with patch("sonarr.SeriesApi", return_value=series_mock_api):
                    async with Client(patched_mcp) as client:
                        result = await client.call_tool(
                            "sonarr_add_series",
                            {"tvdb_id": 12345, "quality_profile": 1, "root_folder": 1},
                        )

    series_mock_api.create_series.assert_called_once()
    assert result.data["id"] == 10


@pytest.mark.asyncio
async def test_sonarr_add_series_tvdb_not_found(patched_mcp):
    qp_mock_api = MagicMock()
    qp_mock_api.list_quality_profile.return_value = [_make_qp_mock(id=1, name="Any")]

    rf_mock_api = MagicMock()
    rf_mock_api.list_root_folder.return_value = [_make_rf_mock(id=1, path="/tv")]

    series_lookup_mock_api = MagicMock()
    series_lookup_mock_api.list_series_lookup.return_value = []

    with patch("sonarr.QualityProfileApi", return_value=qp_mock_api):
        with patch("sonarr.RootFolderApi", return_value=rf_mock_api):
            with patch("sonarr.SeriesLookupApi", return_value=series_lookup_mock_api):
                async with Client(patched_mcp) as client:
                    result = await client.call_tool(
                        "sonarr_add_series",
                        {"tvdb_id": 99999, "quality_profile": 1, "root_folder": 1},
                    )

    assert result.data["error"] == "not_found"


@pytest.mark.asyncio
async def test_sonarr_update_series_happy_path(patched_mcp):
    existing_series = MagicMock()
    updated_series = make_mock_model(id=5)

    mock_api = MagicMock()
    mock_api.get_series_by_id.return_value = existing_series
    mock_api.update_series.return_value = updated_series

    with patch("sonarr.SeriesApi", return_value=mock_api):
        async with Client(patched_mcp) as client:
            result = await client.call_tool(
                "sonarr_update_series", {"id": 5, "monitored": False}
            )

    mock_api.update_series.assert_called_once()
    assert result.data["id"] == 5


@pytest.mark.asyncio
async def test_sonarr_update_series_not_found(patched_mcp):
    mock_api = MagicMock()
    mock_api.get_series_by_id.side_effect = _SonarrNotFoundException()

    with patch("sonarr.SeriesApi", return_value=mock_api):
        async with Client(patched_mcp) as client:
            result = await client.call_tool(
                "sonarr_update_series", {"id": 999, "monitored": False}
            )

    assert result.data["error"] == "not_found"


@pytest.mark.asyncio
async def test_sonarr_delete_series_happy_path(patched_mcp):
    mock_api = MagicMock()
    mock_api.delete_series.return_value = None

    with patch("sonarr.SeriesApi", return_value=mock_api):
        async with Client(patched_mcp) as client:
            result = await client.call_tool("sonarr_delete_series", {"id": 7})

    mock_api.delete_series.assert_called_once_with(id=7, delete_files=False)
    assert result.data["success"] is True


@pytest.mark.asyncio
async def test_sonarr_delete_series_with_files(patched_mcp):
    mock_api = MagicMock()
    mock_api.delete_series.return_value = None

    with patch("sonarr.SeriesApi", return_value=mock_api):
        async with Client(patched_mcp) as client:
            result = await client.call_tool(
                "sonarr_delete_series", {"id": 7, "delete_files": True}
            )

    mock_api.delete_series.assert_called_once_with(id=7, delete_files=True)
    assert result.data["success"] is True
    assert "files also deleted" in result.data["message"]


@pytest.mark.asyncio
async def test_sonarr_delete_series_not_found(patched_mcp):
    mock_api = MagicMock()
    mock_api.delete_series.side_effect = _SonarrNotFoundException()

    with patch("sonarr.SeriesApi", return_value=mock_api):
        async with Client(patched_mcp) as client:
            result = await client.call_tool("sonarr_delete_series", {"id": 999})

    assert result.data["error"] == "not_found"


# ---------------------------------------------------------------------------
# Episode write tools
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sonarr_describe_episode_happy_path(patched_mcp):
    mock_api = MagicMock()
    mock_api.get_episode_by_id.return_value = make_mock_model(id=20, title="Ep1")

    with patch("sonarr.EpisodeApi", return_value=mock_api):
        async with Client(patched_mcp) as client:
            result = await client.call_tool("sonarr_describe_episode", {"id": 20})

    assert result.data["id"] == 20


@pytest.mark.asyncio
async def test_sonarr_describe_episode_not_found(patched_mcp):
    mock_api = MagicMock()
    mock_api.get_episode_by_id.side_effect = _SonarrNotFoundException()

    with patch("sonarr.EpisodeApi", return_value=mock_api):
        async with Client(patched_mcp) as client:
            result = await client.call_tool("sonarr_describe_episode", {"id": 999})

    assert result.data["error"] == "not_found"


@pytest.mark.asyncio
async def test_sonarr_monitor_episodes_happy_path(patched_mcp):
    mock_api = MagicMock()
    mock_api.put_episode_monitor.return_value = None

    with patch("sonarr.EpisodeApi", return_value=mock_api):
        async with Client(patched_mcp) as client:
            result = await client.call_tool(
                "sonarr_monitor_episodes",
                {"episode_ids": [1, 2, 3], "monitored": True},
            )

    mock_api.put_episode_monitor.assert_called_once()
    assert result.data["success"] is True


# ---------------------------------------------------------------------------
# Episode file tools
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sonarr_list_episode_files_happy_path(patched_mcp):
    mock_api = MagicMock()
    mock_api.list_episode_file.return_value = [make_mock_model(id=100, seriesId=1)]

    with patch("sonarr.EpisodeFileApi", return_value=mock_api):
        async with Client(patched_mcp) as client:
            result = await client.call_tool(
                "sonarr_list_episode_files", {"series_id": 1}
            )

    mock_api.list_episode_file.assert_called_once_with(series_id=1)
    assert result.data["summary"]["total"] == 1


@pytest.mark.asyncio
async def test_sonarr_describe_episode_file_happy_path(patched_mcp):
    mock_api = MagicMock()
    mock_api.get_episode_file_by_id.return_value = make_mock_model(id=100)

    with patch("sonarr.EpisodeFileApi", return_value=mock_api):
        async with Client(patched_mcp) as client:
            result = await client.call_tool("sonarr_describe_episode_file", {"id": 100})

    assert result.data["id"] == 100


@pytest.mark.asyncio
async def test_sonarr_describe_episode_file_not_found(patched_mcp):
    mock_api = MagicMock()
    mock_api.get_episode_file_by_id.side_effect = _SonarrNotFoundException()

    with patch("sonarr.EpisodeFileApi", return_value=mock_api):
        async with Client(patched_mcp) as client:
            result = await client.call_tool("sonarr_describe_episode_file", {"id": 999})

    assert result.data["error"] == "not_found"


@pytest.mark.asyncio
async def test_sonarr_delete_episode_file_happy_path(patched_mcp):
    mock_api = MagicMock()
    mock_api.delete_episode_file.return_value = None

    with patch("sonarr.EpisodeFileApi", return_value=mock_api):
        async with Client(patched_mcp) as client:
            result = await client.call_tool("sonarr_delete_episode_file", {"id": 55})

    mock_api.delete_episode_file.assert_called_once_with(id=55)
    assert result.data["success"] is True


@pytest.mark.asyncio
async def test_sonarr_delete_episode_file_not_found(patched_mcp):
    mock_api = MagicMock()
    mock_api.delete_episode_file.side_effect = _SonarrNotFoundException()

    with patch("sonarr.EpisodeFileApi", return_value=mock_api):
        async with Client(patched_mcp) as client:
            result = await client.call_tool("sonarr_delete_episode_file", {"id": 999})

    assert result.data["error"] == "not_found"


# ---------------------------------------------------------------------------
# Blocklist write tools
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sonarr_remove_blocklist_item_happy_path(patched_mcp):
    mock_api = MagicMock()
    mock_api.delete_blocklist.return_value = None

    with patch("sonarr.BlocklistApi", return_value=mock_api):
        async with Client(patched_mcp) as client:
            result = await client.call_tool("sonarr_remove_blocklist_item", {"id": 42})

    mock_api.delete_blocklist.assert_called_once_with(id=42)
    assert result.data["success"] is True


# ---------------------------------------------------------------------------
# Calendar tools
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sonarr_get_calendar_no_dates(patched_mcp):
    mock_api = MagicMock()
    mock_api.list_calendar.return_value = [make_mock_model(id=1, title="S01E01")]

    with patch("sonarr.CalendarApi", return_value=mock_api):
        async with Client(patched_mcp) as client:
            result = await client.call_tool("sonarr_get_calendar", {})

    mock_api.list_calendar.assert_called_once_with()
    assert result.data["summary"]["total"] == 1


@pytest.mark.asyncio
async def test_sonarr_get_calendar_with_dates(patched_mcp):
    mock_api = MagicMock()
    mock_api.list_calendar.return_value = [make_mock_model(id=1, title="S01E01")]

    with patch("sonarr.CalendarApi", return_value=mock_api):
        async with Client(patched_mcp) as client:
            result = await client.call_tool(
                "sonarr_get_calendar", {"start": "2024-01-01", "end": "2024-01-31"}
            )

    mock_api.list_calendar.assert_called_once_with(start="2024-01-01", end="2024-01-31")


# ---------------------------------------------------------------------------
# Commands tools
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sonarr_list_commands_happy_path(patched_mcp):
    mock_api = MagicMock()
    mock_api.list_command.return_value = [
        make_mock_model(id=1, name="RssSync", status="completed")
    ]

    with patch("sonarr.CommandApi", return_value=mock_api):
        async with Client(patched_mcp) as client:
            result = await client.call_tool("sonarr_list_commands", {})

    mock_api.list_command.assert_called_once()
    assert result.data["summary"]["total"] == 1


@pytest.mark.asyncio
async def test_sonarr_describe_command_happy_path(patched_mcp):
    mock_api = MagicMock()
    mock_api.get_command_by_id.return_value = make_mock_model(
        id=5, name="RefreshSeries"
    )

    with patch("sonarr.CommandApi", return_value=mock_api):
        async with Client(patched_mcp) as client:
            result = await client.call_tool("sonarr_describe_command", {"id": 5})

    mock_api.get_command_by_id.assert_called_once_with(id=5)
    assert result.data["id"] == 5


@pytest.mark.asyncio
async def test_sonarr_describe_command_not_found(patched_mcp):
    from sonarr.exceptions import NotFoundException

    mock_api = MagicMock()
    mock_api.get_command_by_id.side_effect = NotFoundException()

    with patch("sonarr.CommandApi", return_value=mock_api):
        async with Client(patched_mcp) as client:
            result = await client.call_tool("sonarr_describe_command", {"id": 999})

    assert result.data["error"] == "not_found"


@pytest.mark.asyncio
async def test_sonarr_run_command_basic(patched_mcp, mock_sonarr_client):
    from unittest.mock import AsyncMock

    mock_command = MagicMock()
    mock_command.id = 10
    mock_command.name = "RssSync"
    mock_command.status = "queued"
    mock_command.to_dict.return_value = {
        "id": 10,
        "name": "RssSync",
        "status": "queued",
    }

    mock_deser_result = MagicMock()
    mock_deser_result.data = mock_command

    mock_response_data = MagicMock()
    mock_response_data.read.return_value = None

    mock_sonarr_client.__aenter__ = AsyncMock(return_value=mock_sonarr_client)
    mock_sonarr_client.__aexit__ = AsyncMock(return_value=None)
    mock_sonarr_client.param_serialize = MagicMock(
        return_value=("POST", "/api/v3/command", {}, {}, {}, None, None, None, None)
    )
    mock_sonarr_client.call_api = MagicMock(return_value=mock_response_data)
    mock_sonarr_client.response_deserialize = MagicMock(return_value=mock_deser_result)

    async with Client(patched_mcp) as client:
        result = await client.call_tool("sonarr_run_command", {"name": "RssSync"})

    mock_sonarr_client.param_serialize.assert_called_once()
    assert result.data["id"] == 10


@pytest.mark.asyncio
async def test_sonarr_run_command_with_series_and_episodes(
    patched_mcp, mock_sonarr_client
):
    from unittest.mock import AsyncMock

    mock_command = MagicMock()
    mock_command.id = 10
    mock_command.name = "EpisodeSearch"
    mock_command.status = "queued"
    mock_command.to_dict.return_value = {
        "id": 10,
        "name": "EpisodeSearch",
        "status": "queued",
    }

    mock_deser_result = MagicMock()
    mock_deser_result.data = mock_command

    mock_response_data = MagicMock()
    mock_response_data.read.return_value = None

    mock_sonarr_client.__aenter__ = AsyncMock(return_value=mock_sonarr_client)
    mock_sonarr_client.__aexit__ = AsyncMock(return_value=None)
    mock_sonarr_client.param_serialize = MagicMock(
        return_value=("POST", "/api/v3/command", {}, {}, {}, None, None, None, None)
    )
    mock_sonarr_client.call_api = MagicMock(return_value=mock_response_data)
    mock_sonarr_client.response_deserialize = MagicMock(return_value=mock_deser_result)

    async with Client(patched_mcp) as client:
        result = await client.call_tool(
            "sonarr_run_command",
            {"name": "EpisodeSearch", "series_id": 1, "episode_ids": [10, 11]},
        )

    mock_sonarr_client.param_serialize.assert_called_once()
    call_body = mock_sonarr_client.param_serialize.call_args[1]["body"]
    assert call_body["seriesId"] == 1
    assert call_body["episodeIds"] == [10, 11]


# ---------------------------------------------------------------------------
# Episodes read tools
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sonarr_list_episodes_with_season_number(patched_mcp):
    mock_api = MagicMock()
    mock_api.list_episode.return_value = [make_mock_model(id=10)]

    with patch("sonarr.EpisodeApi", return_value=mock_api):
        async with Client(patched_mcp) as client:
            result = await client.call_tool(
                "sonarr_list_episodes", {"series_id": 1, "season_number": 2}
            )

    mock_api.list_episode.assert_called_once_with(series_id=1, season_number=2)


# ---------------------------------------------------------------------------
# Manual import tools
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sonarr_preview_manual_import_basic(patched_mcp):
    mock_api = MagicMock()
    mock_api.list_manual_import.return_value = [
        make_mock_model(id=1, path="/dl/file.mkv")
    ]

    with patch("sonarr.ManualImportApi", return_value=mock_api):
        async with Client(patched_mcp) as client:
            result = await client.call_tool(
                "sonarr_preview_manual_import", {"folder": "/dl"}
            )

    mock_api.list_manual_import.assert_called_once_with(folder="/dl")
    assert result.data["summary"]["total"] == 1


@pytest.mark.asyncio
async def test_sonarr_preview_manual_import_with_series_id(patched_mcp):
    mock_api = MagicMock()
    mock_api.list_manual_import.return_value = [
        make_mock_model(id=1, path="/dl/file.mkv")
    ]

    with patch("sonarr.ManualImportApi", return_value=mock_api):
        async with Client(patched_mcp) as client:
            result = await client.call_tool(
                "sonarr_preview_manual_import", {"folder": "/dl", "series_id": 3}
            )

    mock_api.list_manual_import.assert_called_once_with(folder="/dl", series_id=3)


@pytest.mark.asyncio
async def test_sonarr_execute_manual_import_happy_path(patched_mcp, mock_sonarr_client):
    # The new implementation bypasses ManualImportApi and POSTs directly via the
    # ApiClient's low-level methods: param_serialize -> call_api -> response_deserialize.
    # FastMCP's Depends injects the client via an async context manager (__aenter__),
    # so we must configure __aenter__ to return the mock itself (not a new AsyncMock).
    from unittest.mock import AsyncMock

    mock_response_data = MagicMock()
    mock_response_data.read.return_value = None

    mock_command = MagicMock()
    mock_command.id = 99
    mock_command.status = "queued"

    mock_deser_result = MagicMock()
    mock_deser_result.data = mock_command

    # Make the async context manager return the mock itself
    mock_sonarr_client.__aenter__ = AsyncMock(return_value=mock_sonarr_client)
    mock_sonarr_client.__aexit__ = AsyncMock(return_value=None)

    # Use plain MagicMock for synchronous methods so *_param unpacking gets a real tuple
    param_tuple = ("POST", "/api/v3/command", {}, {}, {}, None, None, None, None)
    mock_sonarr_client.param_serialize = MagicMock(return_value=param_tuple)
    mock_sonarr_client.call_api = MagicMock(return_value=mock_response_data)
    mock_sonarr_client.response_deserialize = MagicMock(return_value=mock_deser_result)

    async with Client(patched_mcp) as client:
        result = await client.call_tool(
            "sonarr_execute_manual_import",
            {"files": [{"path": "/dl/ep.mkv", "seriesId": 1, "episodeIds": [10]}]},
        )

    mock_sonarr_client.param_serialize.assert_called_once()
    mock_sonarr_client.call_api.assert_called_once()
    assert result.data["success"] is True
    assert result.data["commandId"] == 99


# ---------------------------------------------------------------------------
# Search / download tools
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sonarr_search_releases_happy_path(patched_mcp):
    mock_api = MagicMock()
    mock_api.list_release.return_value = [
        make_mock_model(id=1, title="Release.X264", indexerId=2)
    ]

    with patch("sonarr.ReleaseApi", return_value=mock_api):
        async with Client(patched_mcp) as client:
            result = await client.call_tool(
                "sonarr_search_releases", {"episode_id": 10}
            )

    mock_api.list_release.assert_called_once_with(episode_id=10)
    assert result.data["summary"]["total"] == 1


@pytest.mark.asyncio
async def test_sonarr_download_release_happy_path(patched_mcp):
    mock_api = MagicMock()
    mock_api.create_release.return_value = make_mock_model(id=1, guid="abc-123")

    with patch("sonarr.ReleaseApi", return_value=mock_api):
        async with Client(patched_mcp) as client:
            result = await client.call_tool(
                "sonarr_download_release", {"guid": "abc-123", "indexer_id": 2}
            )

    mock_api.create_release.assert_called_once()
    assert result.data["guid"] == "abc-123"


# ---------------------------------------------------------------------------
# Queue read tools
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sonarr_describe_queue_item_found(patched_mcp):
    item = MagicMock()
    item.id = 77
    item.to_dict.return_value = {"id": 77, "title": "Some Episode"}

    mock_api = MagicMock()
    mock_api.list_queue_details.return_value = [item]

    with patch("sonarr.QueueDetailsApi", return_value=mock_api):
        async with Client(patched_mcp) as client:
            result = await client.call_tool("sonarr_describe_queue_item", {"id": 77})

    assert result.data["id"] == 77


@pytest.mark.asyncio
async def test_sonarr_describe_queue_item_not_found(patched_mcp):
    mock_api = MagicMock()
    mock_api.list_queue_details.return_value = []

    with patch("sonarr.QueueDetailsApi", return_value=mock_api):
        async with Client(patched_mcp) as client:
            result = await client.call_tool("sonarr_describe_queue_item", {"id": 99})

    assert result.data["error"] == "not_found"


@pytest.mark.asyncio
async def test_sonarr_grab_queue_item_happy_path(patched_mcp):
    mock_api = MagicMock()
    mock_api.create_queue_grab_selected.return_value = None

    with patch("sonarr.QueueApi", return_value=mock_api):
        async with Client(patched_mcp) as client:
            result = await client.call_tool("sonarr_grab_queue_item", {"id": 88})

    mock_api.create_queue_grab_selected.assert_called_once()
    assert result.data["success"] is True


@pytest.mark.asyncio
async def test_sonarr_remove_queue_item_happy_path(patched_mcp):
    mock_api = MagicMock()
    mock_api.delete_queue.return_value = None

    with patch("sonarr.QueueApi", return_value=mock_api):
        async with Client(patched_mcp) as client:
            result = await client.call_tool("sonarr_remove_queue_item", {"id": 88})

    mock_api.delete_queue.assert_called_once_with(
        id=88, blocklist=False, remove_from_client=True
    )
    assert result.data["success"] is True


@pytest.mark.asyncio
async def test_sonarr_remove_queue_item_with_blocklist(patched_mcp):
    mock_api = MagicMock()
    mock_api.delete_queue.return_value = None

    with patch("sonarr.QueueApi", return_value=mock_api):
        async with Client(patched_mcp) as client:
            result = await client.call_tool(
                "sonarr_remove_queue_item", {"id": 88, "blocklist": True}
            )

    assert "blocklisted" in result.data["message"]


# ---------------------------------------------------------------------------
# Reference describe tools
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sonarr_describe_quality_profile_happy_path(patched_mcp):
    mock_api = MagicMock()
    mock_api.get_quality_profile_by_id.return_value = make_mock_model(id=1, name="Any")

    with patch("sonarr.QualityProfileApi", return_value=mock_api):
        async with Client(patched_mcp) as client:
            result = await client.call_tool(
                "sonarr_describe_quality_profile", {"id": 1}
            )

    mock_api.get_quality_profile_by_id.assert_called_once_with(id=1)
    assert result.data["id"] == 1


@pytest.mark.asyncio
async def test_sonarr_describe_quality_profile_not_found(patched_mcp):
    from sonarr.exceptions import NotFoundException

    mock_api = MagicMock()
    mock_api.get_quality_profile_by_id.side_effect = NotFoundException()

    with patch("sonarr.QualityProfileApi", return_value=mock_api):
        async with Client(patched_mcp) as client:
            result = await client.call_tool(
                "sonarr_describe_quality_profile", {"id": 999}
            )

    assert result.data["error"] == "not_found"


@pytest.mark.asyncio
async def test_sonarr_describe_tag_happy_path(patched_mcp):
    mock_api = MagicMock()
    mock_api.get_tag_detail_by_id.return_value = make_mock_model(id=3, label="hd")

    with patch("sonarr.TagDetailsApi", return_value=mock_api):
        async with Client(patched_mcp) as client:
            result = await client.call_tool("sonarr_describe_tag", {"id": 3})

    mock_api.get_tag_detail_by_id.assert_called_once_with(id=3)
    assert result.data["id"] == 3


@pytest.mark.asyncio
async def test_sonarr_describe_tag_not_found(patched_mcp):
    from sonarr.exceptions import NotFoundException

    mock_api = MagicMock()
    mock_api.get_tag_detail_by_id.side_effect = NotFoundException()

    with patch("sonarr.TagDetailsApi", return_value=mock_api):
        async with Client(patched_mcp) as client:
            result = await client.call_tool("sonarr_describe_tag", {"id": 999})

    assert result.data["error"] == "not_found"


# ---------------------------------------------------------------------------
# Rename with season_number
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sonarr_preview_rename_with_season_number(patched_mcp):
    mock_api = MagicMock()
    mock_api.list_rename.return_value = [make_mock_model(seriesId=1)]

    with patch("sonarr.RenameEpisodeApi", return_value=mock_api):
        async with Client(patched_mcp) as client:
            result = await client.call_tool(
                "sonarr_preview_rename", {"series_id": 1, "season_number": 2}
            )

    mock_api.list_rename.assert_called_once_with(series_id=1, season_number=2)
