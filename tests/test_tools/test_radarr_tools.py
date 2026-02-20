"""Tool-level tests for Radarr tools.

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


def _mock_movie(**kwargs) -> MagicMock:
    defaults = dict(
        id=1,
        title="Test Movie",
        year=2020,
        monitored=True,
        status="released",
        quality_profile_id=8,
        tmdb_id=99999,
        has_file=True,
    )
    defaults.update(kwargs)
    return make_mock_model(**defaults)


def _mock_history_record(**kwargs) -> MagicMock:
    defaults = dict(id=200, movie_id=1, event_type="grabbed")
    defaults.update(kwargs)
    return make_mock_model(**defaults)


# ---------------------------------------------------------------------------
# System tools
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_radarr_get_system_status(patched_mcp):
    mock_status = make_mock_model(appName="Radarr", version="6.0.0")
    mock_api = MagicMock()
    mock_api.get_system_status.return_value = mock_status

    with patch("radarr.SystemApi", return_value=mock_api) as mock_cls:
        async with Client(patched_mcp) as client:
            result = await client.call_tool("radarr_get_system_status", {})

    mock_cls.assert_called_once()
    mock_api.get_system_status.assert_called_once()
    assert result.data["appName"] == "Radarr"


@pytest.mark.asyncio
async def test_radarr_list_health_checks(patched_mcp):
    mock_api = MagicMock()
    mock_api.list_health.return_value = [
        make_mock_model(
            source="UpdateCheck", type="warning", message="Update available"
        )
    ]

    with patch("radarr.HealthApi", return_value=mock_api):
        async with Client(patched_mcp) as client:
            result = await client.call_tool("radarr_list_health_checks", {})

    mock_api.list_health.assert_called_once()
    assert result.data["summary"]["total"] == 1


@pytest.mark.asyncio
async def test_radarr_get_disk_space(patched_mcp):
    mock_api = MagicMock()
    mock_api.list_disk_space.return_value = [
        make_mock_model(path="/media/movies", freeSpace=5000, totalSpace=10000)
    ]

    with patch("radarr.DiskSpaceApi", return_value=mock_api):
        async with Client(patched_mcp) as client:
            result = await client.call_tool("radarr_get_disk_space", {})

    mock_api.list_disk_space.assert_called_once()
    assert result.data["summary"]["total"] == 1


# ---------------------------------------------------------------------------
# Movie tools
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_radarr_list_movies(patched_mcp):
    mock_api = MagicMock()
    mock_api.list_movie.return_value = [_mock_movie(), _mock_movie(id=2)]

    with patch("radarr.MovieApi", return_value=mock_api):
        async with Client(patched_mcp) as client:
            result = await client.call_tool("radarr_list_movies", {})

    mock_api.list_movie.assert_called_once()
    assert result.data["summary"]["total"] == 2


@pytest.mark.asyncio
async def test_radarr_describe_movie(patched_mcp):
    mock_api = MagicMock()
    mock_api.get_movie_by_id.return_value = _mock_movie(id=42)

    with patch("radarr.MovieApi", return_value=mock_api):
        async with Client(patched_mcp) as client:
            result = await client.call_tool("radarr_describe_movie", {"id": 42})

    mock_api.get_movie_by_id.assert_called_once_with(id=42)
    assert result.data["id"] == 42


# ---------------------------------------------------------------------------
# History tools
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_radarr_list_history_uses_get_history(patched_mcp):
    """Must use get_history (not list_history) on HistoryApi."""
    mock_api = MagicMock()
    mock_api.get_history.return_value = make_mock_paged([_mock_history_record()])

    with patch("radarr.HistoryApi", return_value=mock_api) as mock_cls:
        async with Client(patched_mcp) as client:
            result = await client.call_tool("radarr_list_history", {})

    mock_cls.assert_called_once()
    mock_api.get_history.assert_called_once()
    mock_api.list_history.assert_not_called()
    assert result.data["summary"]["total"] == 1


@pytest.mark.asyncio
async def test_radarr_list_movie_history_uses_list_history_movie(patched_mcp):
    """Must use list_history_movie (not list_history) for per-movie history."""
    mock_api = MagicMock()
    mock_api.list_history_movie.return_value = [_mock_history_record()]

    with patch("radarr.HistoryApi", return_value=mock_api):
        async with Client(patched_mcp) as client:
            result = await client.call_tool(
                "radarr_list_movie_history", {"movie_id": 1}
            )

    mock_api.list_history_movie.assert_called_once_with(movie_id=1)
    mock_api.list_history.assert_not_called()


# ---------------------------------------------------------------------------
# Queue tools
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_radarr_list_queue_uses_queue_details_api(patched_mcp):
    """Must use QueueDetailsApi.list_queue_details (not QueueApi.list_queue_details)."""
    mock_api = MagicMock()
    mock_api.list_queue_details.return_value = []

    with patch("radarr.QueueDetailsApi", return_value=mock_api) as mock_cls:
        with patch("radarr.QueueApi") as mock_wrong_cls:
            async with Client(patched_mcp) as client:
                result = await client.call_tool("radarr_list_queue", {})

    mock_cls.assert_called_once()
    mock_api.list_queue_details.assert_called_once()
    mock_wrong_cls.assert_not_called()


# ---------------------------------------------------------------------------
# Wanted tools
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_radarr_list_missing_uses_missing_api(patched_mcp):
    """Must use MissingApi.get_wanted_missing (not WantedMissingApi.list_wanted_missing)."""
    mock_api = MagicMock()
    mock_api.get_wanted_missing.return_value = make_mock_paged([])

    with patch("radarr.MissingApi", return_value=mock_api) as mock_cls:
        async with Client(patched_mcp) as client:
            result = await client.call_tool("radarr_list_missing", {})

    mock_cls.assert_called_once()
    mock_api.get_wanted_missing.assert_called_once()


@pytest.mark.asyncio
async def test_radarr_list_cutoff_unmet_uses_cutoff_api(patched_mcp):
    """Must use CutoffApi.get_wanted_cutoff (not WantedCutoffApi.list_wanted_cutoff)."""
    mock_api = MagicMock()
    mock_api.get_wanted_cutoff.return_value = make_mock_paged([])

    with patch("radarr.CutoffApi", return_value=mock_api) as mock_cls:
        async with Client(patched_mcp) as client:
            result = await client.call_tool("radarr_list_cutoff_unmet", {})

    mock_cls.assert_called_once()
    mock_api.get_wanted_cutoff.assert_called_once()


# ---------------------------------------------------------------------------
# Blocklist tools
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_radarr_list_blocklist_uses_get_blocklist(patched_mcp):
    """Must use BlocklistApi.get_blocklist (not list_blocklist)."""
    mock_api = MagicMock()
    mock_api.get_blocklist.return_value = make_mock_paged([])

    with patch("radarr.BlocklistApi", return_value=mock_api) as mock_cls:
        async with Client(patched_mcp) as client:
            result = await client.call_tool("radarr_list_blocklist", {})

    mock_cls.assert_called_once()
    mock_api.get_blocklist.assert_called_once()
    mock_api.list_blocklist.assert_not_called()


# ---------------------------------------------------------------------------
# Rename tools
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_radarr_preview_rename_uses_rename_movie_api(patched_mcp):
    """Must use RenameMovieApi.list_rename (not RenameApi.list_rename)."""
    mock_rename = make_mock_model(movieId=1, existingPath="old.mkv", newPath="new.mkv")
    mock_api = MagicMock()
    mock_api.list_rename.return_value = [mock_rename]

    with patch("radarr.RenameMovieApi", return_value=mock_api) as mock_cls:
        async with Client(patched_mcp) as client:
            result = await client.call_tool("radarr_preview_rename", {"movie_id": 1})

    mock_cls.assert_called_once()
    mock_api.list_rename.assert_called_once_with(movie_id=1)


# ---------------------------------------------------------------------------
# Collections tools
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_radarr_list_collections(patched_mcp):
    mock_api = MagicMock()
    mock_api.list_collection.return_value = [
        make_mock_model(id=10, title="The Matrix Collection", tmdbId=2344)
    ]

    with patch("radarr.CollectionApi", return_value=mock_api):
        async with Client(patched_mcp) as client:
            result = await client.call_tool("radarr_list_collections", {})

    mock_api.list_collection.assert_called_once()
    assert result.data["summary"]["total"] == 1


@pytest.mark.asyncio
async def test_radarr_describe_collection(patched_mcp):
    mock_api = MagicMock()
    mock_api.get_collection_by_id.return_value = make_mock_model(
        id=10, title="The Matrix Collection"
    )

    with patch("radarr.CollectionApi", return_value=mock_api):
        async with Client(patched_mcp) as client:
            result = await client.call_tool("radarr_describe_collection", {"id": 10})

    mock_api.get_collection_by_id.assert_called_once_with(id=10)


# ---------------------------------------------------------------------------
# Credits tools
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_radarr_list_credits_uses_get_credit(patched_mcp):
    """Must use CreditApi.get_credit (not list_credit) with movie_id."""
    mock_api = MagicMock()
    mock_api.get_credit.return_value = [
        make_mock_model(id=1, name="Keanu Reeves", character="Neo")
    ]

    with patch("radarr.CreditApi", return_value=mock_api) as mock_cls:
        async with Client(patched_mcp) as client:
            result = await client.call_tool("radarr_list_credits", {"movie_id": 142})

    mock_cls.assert_called_once()
    mock_api.get_credit.assert_called_once_with(movie_id=142)
    mock_api.list_credit.assert_not_called()


# ---------------------------------------------------------------------------
# Alternative titles tools
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_radarr_list_alternative_titles(patched_mcp):
    mock_api = MagicMock()
    mock_api.list_alttitle.return_value = [
        make_mock_model(id=1, title="Le Titre Alternatif", sourceType="tmdb")
    ]

    with patch("radarr.AlternativeTitleApi", return_value=mock_api) as mock_cls:
        async with Client(patched_mcp) as client:
            result = await client.call_tool(
                "radarr_list_alternative_titles", {"movie_id": 142}
            )

    mock_cls.assert_called_once()
    mock_api.list_alttitle.assert_called_once_with(movie_id=142)


# ---------------------------------------------------------------------------
# Exclusions tools
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_radarr_list_exclusions_uses_import_list_exclusion_api(patched_mcp):
    """Must use ImportListExclusionApi (not ImportExclusionsApi)."""
    mock_api = MagicMock()
    mock_api.list_exclusions.return_value = [
        make_mock_model(id=1, tmdbId=603, movieTitle="The Matrix", movieYear=1999)
    ]

    with patch("radarr.ImportListExclusionApi", return_value=mock_api) as mock_cls:
        async with Client(patched_mcp) as client:
            result = await client.call_tool("radarr_list_exclusions", {})

    mock_cls.assert_called_once()
    mock_api.list_exclusions.assert_called_once()
    assert result.data["summary"]["total"] == 1


# ---------------------------------------------------------------------------
# Movie files tools
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_radarr_list_movie_files_passes_list(patched_mcp):
    """movie_id must be passed as a list to list_movie_file."""
    mock_api = MagicMock()
    mock_api.list_movie_file.return_value = [
        make_mock_model(id=526, movieId=142, size=55000000)
    ]
    with patch("radarr.MovieFileApi", return_value=mock_api):
        async with Client(patched_mcp) as client:
            result = await client.call_tool(
                "radarr_list_movie_files", {"movie_id": 142}
            )
    mock_api.list_movie_file.assert_called_once_with(movie_id=[142])
    assert result.data["summary"]["total"] == 1


@pytest.mark.asyncio
async def test_radarr_list_credits_handles_none_result(patched_mcp):
    """get_credit may return None — must not raise."""
    mock_api = MagicMock()
    mock_api.get_credit.return_value = None
    with patch("radarr.CreditApi", return_value=mock_api):
        async with Client(patched_mcp) as client:
            result = await client.call_tool("radarr_list_credits", {"movie_id": 999})
    assert result.data["summary"]["total"] == 0


@pytest.mark.asyncio
async def test_radarr_list_credits_returns_results(patched_mcp):
    """When get_credit returns data, it should be summarized normally."""
    mock_api = MagicMock()
    mock_api.get_credit.return_value = [
        make_mock_model(id=1, name="Keanu Reeves", character="Neo", type="cast")
    ]
    with patch("radarr.CreditApi", return_value=mock_api):
        async with Client(patched_mcp) as client:
            result = await client.call_tool("radarr_list_credits", {"movie_id": 142})
    mock_api.get_credit.assert_called_once_with(movie_id=142)
    assert result.data["summary"]["total"] == 1


# ---------------------------------------------------------------------------
# Reference tools
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_radarr_list_quality_profiles(patched_mcp):
    mock_api = MagicMock()
    mock_api.list_quality_profile.return_value = [
        make_mock_model(id=8, name="SQP-2"),
        make_mock_model(id=41, name="SQP-1 (2160p)"),
    ]

    with patch("radarr.QualityProfileApi", return_value=mock_api):
        async with Client(patched_mcp) as client:
            result = await client.call_tool("radarr_list_quality_profiles", {})

    mock_api.list_quality_profile.assert_called_once()
    assert result.data["summary"]["total"] == 2


@pytest.mark.asyncio
async def test_radarr_list_root_folders(patched_mcp):
    mock_api = MagicMock()
    mock_api.list_root_folder.return_value = [
        make_mock_model(id=2, path="/media/movies", freeSpace=37000000000)
    ]

    with patch("radarr.RootFolderApi", return_value=mock_api):
        async with Client(patched_mcp) as client:
            result = await client.call_tool("radarr_list_root_folders", {})

    mock_api.list_root_folder.assert_called_once()
    assert result.data["summary"]["total"] == 1


@pytest.mark.asyncio
async def test_radarr_list_tags(patched_mcp):
    mock_api = MagicMock()
    mock_api.list_tag.return_value = [make_mock_model(id=1, label="4k")]

    with patch("radarr.TagApi", return_value=mock_api):
        async with Client(patched_mcp) as client:
            result = await client.call_tool("radarr_list_tags", {})

    mock_api.list_tag.assert_called_once()
    assert result.data["summary"]["total"] == 1
