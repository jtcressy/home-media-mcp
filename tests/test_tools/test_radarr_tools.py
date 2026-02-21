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
    """Must use get_history (not list_history) on HistoryApi when movie_id is None."""
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
async def test_radarr_list_history_with_movie_id(patched_mcp):
    """When movie_id is provided, must use list_history_movie (not get_history)."""
    mock_api = MagicMock()
    mock_api.list_history_movie.return_value = [_mock_history_record()]

    with patch("radarr.HistoryApi", return_value=mock_api):
        async with Client(patched_mcp) as client:
            result = await client.call_tool("radarr_list_history", {"movie_id": 1})

    mock_api.list_history_movie.assert_called_once_with(movie_id=1)
    mock_api.get_history.assert_not_called()
    assert result.data["summary"]["total"] == 1


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


# ---------------------------------------------------------------------------
# Movie write tools
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_radarr_describe_movie_not_found(patched_mcp):
    from radarr.exceptions import NotFoundException

    mock_api = MagicMock()
    mock_api.get_movie_by_id.side_effect = NotFoundException()

    with patch("radarr.MovieApi", return_value=mock_api):
        async with Client(patched_mcp) as client:
            result = await client.call_tool("radarr_describe_movie", {"id": 999})

    assert result.data["error"] == "not_found"


@pytest.mark.asyncio
async def test_radarr_lookup_movie_by_term(patched_mcp):
    mock_api = MagicMock()
    mock_api.list_movie_lookup.return_value = [
        make_mock_model(id=1, title="The Matrix")
    ]

    with patch("radarr.MovieLookupApi", return_value=mock_api):
        async with Client(patched_mcp) as client:
            result = await client.call_tool("radarr_lookup_movie", {"term": "Matrix"})

    mock_api.list_movie_lookup.assert_called_once_with(term="Matrix")
    assert result.data["summary"]["total"] == 1


@pytest.mark.asyncio
async def test_radarr_lookup_movie_by_tmdb_id(patched_mcp):
    mock_api = MagicMock()
    mock_api.list_movie_lookup_tmdb.return_value = [
        make_mock_model(id=1, title="The Matrix")
    ]

    with patch("radarr.MovieLookupApi", return_value=mock_api):
        async with Client(patched_mcp) as client:
            result = await client.call_tool("radarr_lookup_movie", {"tmdb_id": 603})

    mock_api.list_movie_lookup_tmdb.assert_called_once_with(tmdb_id=603)
    assert result.data["summary"]["total"] == 1


@pytest.mark.asyncio
async def test_radarr_lookup_movie_invalid_params(patched_mcp):
    async with Client(patched_mcp) as client:
        result = await client.call_tool("radarr_lookup_movie", {})

    assert result.data["error"] == "invalid_params"


@pytest.mark.asyncio
async def test_radarr_add_movie_happy_path(patched_mcp):
    qp = MagicMock()
    qp.id = 8
    qp.name = "SQP-2"
    mock_qp_api = MagicMock()
    mock_qp_api.list_quality_profile.return_value = [qp]

    rf = MagicMock()
    rf.id = 2
    rf.path = "/media/movies"
    rf.to_dict.return_value = {"id": 2, "path": "/media/movies"}
    mock_rf_api = MagicMock()
    mock_rf_api.list_root_folder.return_value = [rf]

    mock_lookup_api = MagicMock()
    mock_lookup_api.list_movie_lookup.return_value = [MagicMock()]

    mock_movie_api = MagicMock()
    mock_movie_api.create_movie.return_value = make_mock_model(
        id=42, title="The Matrix"
    )

    with patch("radarr.QualityProfileApi", return_value=mock_qp_api):
        with patch("radarr.RootFolderApi", return_value=mock_rf_api):
            with patch("radarr.MovieLookupApi", return_value=mock_lookup_api):
                with patch("radarr.MovieApi", return_value=mock_movie_api):
                    async with Client(patched_mcp) as client:
                        result = await client.call_tool(
                            "radarr_add_movie",
                            {"tmdb_id": 603, "quality_profile": 8, "root_folder": 2},
                        )

    mock_movie_api.create_movie.assert_called_once()
    assert result.data["id"] == 42


@pytest.mark.asyncio
async def test_radarr_add_movie_tmdb_not_found(patched_mcp):
    qp = MagicMock()
    qp.id = 8
    qp.name = "SQP-2"
    mock_qp_api = MagicMock()
    mock_qp_api.list_quality_profile.return_value = [qp]

    rf = MagicMock()
    rf.id = 2
    rf.path = "/media/movies"
    rf.to_dict.return_value = {"id": 2, "path": "/media/movies"}
    mock_rf_api = MagicMock()
    mock_rf_api.list_root_folder.return_value = [rf]

    mock_lookup_api = MagicMock()
    mock_lookup_api.list_movie_lookup.return_value = []

    mock_movie_api = MagicMock()

    with patch("radarr.QualityProfileApi", return_value=mock_qp_api):
        with patch("radarr.RootFolderApi", return_value=mock_rf_api):
            with patch("radarr.MovieLookupApi", return_value=mock_lookup_api):
                with patch("radarr.MovieApi", return_value=mock_movie_api):
                    async with Client(patched_mcp) as client:
                        result = await client.call_tool(
                            "radarr_add_movie",
                            {"tmdb_id": 603, "quality_profile": 8, "root_folder": 2},
                        )

    assert result.data["error"] == "not_found"


@pytest.mark.asyncio
async def test_radarr_update_movie_happy_path(patched_mcp):
    mock_api = MagicMock()
    mock_api.get_movie_by_id.return_value = MagicMock()
    mock_api.update_movie.return_value = make_mock_model(id=5, title="Updated")

    with patch("radarr.MovieApi", return_value=mock_api):
        async with Client(patched_mcp) as client:
            result = await client.call_tool(
                "radarr_update_movie", {"id": 5, "monitored": False}
            )

    mock_api.update_movie.assert_called_once()
    assert result.data["id"] == 5


@pytest.mark.asyncio
async def test_radarr_update_movie_not_found(patched_mcp):
    from radarr.exceptions import NotFoundException

    mock_api = MagicMock()
    mock_api.get_movie_by_id.side_effect = NotFoundException()

    with patch("radarr.MovieApi", return_value=mock_api):
        async with Client(patched_mcp) as client:
            result = await client.call_tool(
                "radarr_update_movie", {"id": 999, "monitored": False}
            )

    assert result.data["error"] == "not_found"


@pytest.mark.asyncio
async def test_radarr_delete_movie_happy_path(patched_mcp):
    mock_api = MagicMock()
    mock_api.delete_movie.return_value = None

    with patch("radarr.MovieApi", return_value=mock_api):
        async with Client(patched_mcp) as client:
            result = await client.call_tool("radarr_delete_movie", {"id": 7})

    mock_api.delete_movie.assert_called_once_with(
        id=7, delete_files=False, add_import_exclusion=False
    )
    assert result.data["success"] is True


@pytest.mark.asyncio
async def test_radarr_delete_movie_with_files(patched_mcp):
    mock_api = MagicMock()
    mock_api.delete_movie.return_value = None

    with patch("radarr.MovieApi", return_value=mock_api):
        async with Client(patched_mcp) as client:
            result = await client.call_tool(
                "radarr_delete_movie", {"id": 7, "delete_files": True}
            )

    assert "files also deleted" in result.data["message"]


@pytest.mark.asyncio
async def test_radarr_delete_movie_with_exclusion(patched_mcp):
    mock_api = MagicMock()
    mock_api.delete_movie.return_value = None

    with patch("radarr.MovieApi", return_value=mock_api):
        async with Client(patched_mcp) as client:
            result = await client.call_tool(
                "radarr_delete_movie", {"id": 7, "add_import_exclusion": True}
            )

    assert "import exclusion" in result.data["message"]


@pytest.mark.asyncio
async def test_radarr_delete_movie_not_found(patched_mcp):
    from radarr.exceptions import NotFoundException

    mock_api = MagicMock()
    mock_api.delete_movie.side_effect = NotFoundException()

    with patch("radarr.MovieApi", return_value=mock_api):
        async with Client(patched_mcp) as client:
            result = await client.call_tool("radarr_delete_movie", {"id": 999})

    assert result.data["error"] == "not_found"


# ---------------------------------------------------------------------------
# Movie file write tools
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_radarr_describe_movie_file_happy_path(patched_mcp):
    mock_api = MagicMock()
    mock_api.get_movie_file_by_id.return_value = make_mock_model(id=526)

    with patch("radarr.MovieFileApi", return_value=mock_api):
        async with Client(patched_mcp) as client:
            result = await client.call_tool("radarr_describe_movie_file", {"id": 526})

    assert result.data["id"] == 526


@pytest.mark.asyncio
async def test_radarr_describe_movie_file_not_found(patched_mcp):
    from radarr.exceptions import NotFoundException

    mock_api = MagicMock()
    mock_api.get_movie_file_by_id.side_effect = NotFoundException()

    with patch("radarr.MovieFileApi", return_value=mock_api):
        async with Client(patched_mcp) as client:
            result = await client.call_tool("radarr_describe_movie_file", {"id": 999})

    assert result.data["error"] == "not_found"


@pytest.mark.asyncio
async def test_radarr_delete_movie_file_happy_path(patched_mcp):
    mock_api = MagicMock()
    mock_api.delete_movie_file.return_value = None

    with patch("radarr.MovieFileApi", return_value=mock_api):
        async with Client(patched_mcp) as client:
            result = await client.call_tool("radarr_delete_movie_file", {"id": 526})

    mock_api.delete_movie_file.assert_called_once_with(id=526)
    assert result.data["success"] is True


@pytest.mark.asyncio
async def test_radarr_delete_movie_file_not_found(patched_mcp):
    from radarr.exceptions import NotFoundException

    mock_api = MagicMock()
    mock_api.delete_movie_file.side_effect = NotFoundException()

    with patch("radarr.MovieFileApi", return_value=mock_api):
        async with Client(patched_mcp) as client:
            result = await client.call_tool("radarr_delete_movie_file", {"id": 999})

    assert result.data["error"] == "not_found"


# ---------------------------------------------------------------------------
# Exclusion write tools
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_radarr_add_exclusion_happy_path(patched_mcp):
    mock_api = MagicMock()
    mock_api.create_exclusions.return_value = MagicMock()

    with patch("radarr.ImportListExclusionApi", return_value=mock_api):
        async with Client(patched_mcp) as client:
            result = await client.call_tool(
                "radarr_add_exclusion",
                {"tmdb_id": 603, "movie_title": "The Matrix", "movie_year": 1999},
            )

    mock_api.create_exclusions.assert_called_once()
    assert result.data["success"] is True


@pytest.mark.asyncio
async def test_radarr_remove_exclusion_happy_path(patched_mcp):
    mock_api = MagicMock()
    mock_api.delete_exclusions.return_value = None

    with patch("radarr.ImportListExclusionApi", return_value=mock_api):
        async with Client(patched_mcp) as client:
            result = await client.call_tool("radarr_remove_exclusion", {"id": 5})

    mock_api.delete_exclusions.assert_called_once_with(id=5)
    assert result.data["success"] is True


# ---------------------------------------------------------------------------
# Blocklist write tools
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_radarr_remove_blocklist_item_happy_path(patched_mcp):
    mock_api = MagicMock()
    mock_api.delete_blocklist.return_value = None

    with patch("radarr.BlocklistApi", return_value=mock_api):
        async with Client(patched_mcp) as client:
            result = await client.call_tool("radarr_remove_blocklist_item", {"id": 42})

    mock_api.delete_blocklist.assert_called_once_with(id=42)
    assert result.data["success"] is True


# ---------------------------------------------------------------------------
# Calendar tools
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_radarr_get_calendar_no_dates(patched_mcp):
    mock_api = MagicMock()
    mock_api.list_calendar.return_value = [
        make_mock_model(id=1, title="Movie Premiere")
    ]

    with patch("radarr.CalendarApi", return_value=mock_api):
        async with Client(patched_mcp) as client:
            result = await client.call_tool("radarr_get_calendar", {})

    mock_api.list_calendar.assert_called_once()
    assert result.data["summary"]["total"] == 1


@pytest.mark.asyncio
async def test_radarr_get_calendar_with_dates(patched_mcp):
    mock_api = MagicMock()
    mock_api.list_calendar.return_value = [
        make_mock_model(id=1, title="Movie Premiere")
    ]

    with patch("radarr.CalendarApi", return_value=mock_api):
        async with Client(patched_mcp) as client:
            result = await client.call_tool(
                "radarr_get_calendar", {"start": "2024-02-01", "end": "2024-02-28"}
            )

    mock_api.list_calendar.assert_called_once_with(start="2024-02-01", end="2024-02-28")


# ---------------------------------------------------------------------------
# Commands tools
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_radarr_list_commands_happy_path(patched_mcp):
    mock_api = MagicMock()
    mock_api.list_command.return_value = [
        make_mock_model(id=1, name="RssSync", status="completed")
    ]

    with patch("radarr.CommandApi", return_value=mock_api):
        async with Client(patched_mcp) as client:
            result = await client.call_tool("radarr_list_commands", {})

    mock_api.list_command.assert_called_once()
    assert result.data["summary"]["total"] == 1


@pytest.mark.asyncio
async def test_radarr_describe_command_happy_path(patched_mcp):
    mock_api = MagicMock()
    mock_api.get_command_by_id.return_value = make_mock_model(id=5, name="RefreshMovie")

    with patch("radarr.CommandApi", return_value=mock_api):
        async with Client(patched_mcp) as client:
            result = await client.call_tool("radarr_describe_command", {"id": 5})

    mock_api.get_command_by_id.assert_called_once_with(id=5)
    assert result.data["id"] == 5


@pytest.mark.asyncio
async def test_radarr_describe_command_not_found(patched_mcp):
    from radarr.exceptions import NotFoundException

    mock_api = MagicMock()
    mock_api.get_command_by_id.side_effect = NotFoundException()

    with patch("radarr.CommandApi", return_value=mock_api):
        async with Client(patched_mcp) as client:
            result = await client.call_tool("radarr_describe_command", {"id": 999})

    assert isinstance(result.data, dict)
    assert result.data.get("error") == "not_found"


@pytest.mark.asyncio
async def test_radarr_run_command_basic(patched_mcp, mock_radarr_client):
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

    mock_radarr_client.__aenter__ = AsyncMock(return_value=mock_radarr_client)
    mock_radarr_client.__aexit__ = AsyncMock(return_value=None)
    mock_radarr_client.param_serialize = MagicMock(
        return_value=("POST", "/api/v3/command", {}, {}, {}, None, None, None, None)
    )
    mock_radarr_client.call_api = MagicMock(return_value=mock_response_data)
    mock_radarr_client.response_deserialize = MagicMock(return_value=mock_deser_result)

    async with Client(patched_mcp) as client:
        result = await client.call_tool("radarr_run_command", {"name": "RssSync"})

    mock_radarr_client.param_serialize.assert_called_once()
    assert result.data["id"] == 10


@pytest.mark.asyncio
async def test_radarr_run_command_with_movie_ids(patched_mcp, mock_radarr_client):
    from unittest.mock import AsyncMock

    mock_command = MagicMock()
    mock_command.id = 10
    mock_command.name = "MoviesSearch"
    mock_command.status = "queued"
    mock_command.to_dict.return_value = {
        "id": 10,
        "name": "MoviesSearch",
        "status": "queued",
    }

    mock_deser_result = MagicMock()
    mock_deser_result.data = mock_command

    mock_response_data = MagicMock()
    mock_response_data.read.return_value = None

    mock_radarr_client.__aenter__ = AsyncMock(return_value=mock_radarr_client)
    mock_radarr_client.__aexit__ = AsyncMock(return_value=None)
    mock_radarr_client.param_serialize = MagicMock(
        return_value=("POST", "/api/v3/command", {}, {}, {}, None, None, None, None)
    )
    mock_radarr_client.call_api = MagicMock(return_value=mock_response_data)
    mock_radarr_client.response_deserialize = MagicMock(return_value=mock_deser_result)

    async with Client(patched_mcp) as client:
        result = await client.call_tool(
            "radarr_run_command", {"name": "MoviesSearch", "movie_ids": [1, 2]}
        )

    mock_radarr_client.param_serialize.assert_called_once()
    call_body = mock_radarr_client.param_serialize.call_args[1]["body"]
    assert call_body["movieIds"] == [1, 2]


# ---------------------------------------------------------------------------
# Manual import tools
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_radarr_preview_manual_import_basic(patched_mcp):
    mock_api = MagicMock()
    mock_api.list_manual_import.return_value = [
        make_mock_model(id=1, path="/dl/movie.mkv")
    ]

    with patch("radarr.ManualImportApi", return_value=mock_api):
        async with Client(patched_mcp) as client:
            result = await client.call_tool(
                "radarr_preview_manual_import", {"folder": "/dl"}
            )

    mock_api.list_manual_import.assert_called_once_with(folder="/dl")
    assert result.data["summary"]["total"] == 1


@pytest.mark.asyncio
async def test_radarr_preview_manual_import_with_movie_id(patched_mcp):
    mock_api = MagicMock()
    mock_api.list_manual_import.return_value = [
        make_mock_model(id=1, path="/dl/movie.mkv")
    ]

    with patch("radarr.ManualImportApi", return_value=mock_api):
        async with Client(patched_mcp) as client:
            result = await client.call_tool(
                "radarr_preview_manual_import", {"folder": "/dl", "movie_id": 42}
            )

    mock_api.list_manual_import.assert_called_once_with(folder="/dl", movie_id=42)


@pytest.mark.asyncio
async def test_radarr_execute_manual_import_happy_path(patched_mcp, mock_radarr_client):
    # The new implementation bypasses ManualImportApi and POSTs directly via the
    # ApiClient's low-level methods: param_serialize -> call_api -> response_deserialize.
    # FastMCP's Depends injects the client via an async context manager (__aenter__),
    # so we must configure __aenter__ to return the mock itself (not a new AsyncMock).
    from unittest.mock import AsyncMock

    mock_response_data = MagicMock()
    mock_response_data.read.return_value = None

    mock_command = MagicMock()
    mock_command.id = 88
    mock_command.status = "queued"

    mock_deser_result = MagicMock()
    mock_deser_result.data = mock_command

    # Make the async context manager return the mock itself
    mock_radarr_client.__aenter__ = AsyncMock(return_value=mock_radarr_client)
    mock_radarr_client.__aexit__ = AsyncMock(return_value=None)

    # Use plain MagicMock for synchronous methods so *_param unpacking gets a real tuple
    param_tuple = ("POST", "/api/v3/command", {}, {}, {}, None, None, None, None)
    mock_radarr_client.param_serialize = MagicMock(return_value=param_tuple)
    mock_radarr_client.call_api = MagicMock(return_value=mock_response_data)
    mock_radarr_client.response_deserialize = MagicMock(return_value=mock_deser_result)

    async with Client(patched_mcp) as client:
        result = await client.call_tool(
            "radarr_execute_manual_import",
            {"files": [{"path": "/dl/movie.mkv", "movieId": 42}]},
        )

    mock_radarr_client.param_serialize.assert_called_once()
    mock_radarr_client.call_api.assert_called_once()
    assert result.data.get("success") is True
    assert result.data.get("commandId") == 88


# ---------------------------------------------------------------------------
# Search / download tools
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_radarr_search_releases_happy_path(patched_mcp):
    mock_api = MagicMock()
    mock_api.list_release.return_value = [
        make_mock_model(id=1, title="The.Matrix.2160p", indexerId=3)
    ]

    with patch("radarr.ReleaseApi", return_value=mock_api):
        async with Client(patched_mcp) as client:
            result = await client.call_tool("radarr_search_releases", {"movie_id": 42})

    mock_api.list_release.assert_called_once_with(movie_id=42)
    assert result.data["summary"]["total"] == 1


@pytest.mark.asyncio
async def test_radarr_download_release_happy_path(patched_mcp):
    mock_api = MagicMock()
    mock_api.create_release.return_value = make_mock_model(id=1, guid="xyz-789")

    with patch("radarr.ReleaseApi", return_value=mock_api):
        async with Client(patched_mcp) as client:
            result = await client.call_tool(
                "radarr_download_release", {"guid": "xyz-789", "indexer_id": 3}
            )

    mock_api.create_release.assert_called_once()
    assert result.data["guid"] == "xyz-789"


# ---------------------------------------------------------------------------
# Queue read tools
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_radarr_describe_queue_item_found(patched_mcp):
    item = MagicMock()
    item.id = 77
    item.to_dict.return_value = {"id": 77, "title": "The Matrix"}

    mock_api = MagicMock()
    mock_api.list_queue_details.return_value = [item]

    with patch("radarr.QueueDetailsApi", return_value=mock_api):
        async with Client(patched_mcp) as client:
            result = await client.call_tool("radarr_describe_queue_item", {"id": 77})

    assert result.data["id"] == 77


@pytest.mark.asyncio
async def test_radarr_describe_queue_item_not_found(patched_mcp):
    mock_api = MagicMock()
    mock_api.list_queue_details.return_value = []

    with patch("radarr.QueueDetailsApi", return_value=mock_api):
        async with Client(patched_mcp) as client:
            result = await client.call_tool("radarr_describe_queue_item", {"id": 99})

    assert result.data.get("error") == "not_found"


@pytest.mark.asyncio
async def test_radarr_grab_queue_item_happy_path(patched_mcp):
    mock_api = MagicMock()
    mock_api.create_queue_grab_bulk.return_value = None

    with patch("radarr.QueueActionApi", return_value=mock_api):
        async with Client(patched_mcp) as client:
            result = await client.call_tool("radarr_grab_queue_item", {"id": 88})

    mock_api.create_queue_grab_bulk.assert_called_once()
    assert result.data.get("success") is True


@pytest.mark.asyncio
async def test_radarr_remove_queue_items_happy_path(patched_mcp):
    tracked_item = MagicMock()
    tracked_item.id = 1
    tracked_item.download_id = "SABnzbd_nzo_abc123"
    tracked_item.to_dict.return_value = {"id": 1, "downloadId": "SABnzbd_nzo_abc123"}

    tracked_item2 = MagicMock()
    tracked_item2.id = 2
    tracked_item2.download_id = "SABnzbd_nzo_def456"
    tracked_item2.to_dict.return_value = {"id": 2, "downloadId": "SABnzbd_nzo_def456"}

    mock_details_api = MagicMock()
    mock_details_api.list_queue_details.return_value = [tracked_item, tracked_item2]

    mock_queue_api = MagicMock()
    mock_queue_api.delete_queue_bulk.return_value = None

    with (
        patch("radarr.QueueDetailsApi", return_value=mock_details_api),
        patch("radarr.QueueApi", return_value=mock_queue_api),
    ):
        async with Client(patched_mcp) as client:
            result = await client.call_tool(
                "radarr_remove_queue_items", {"ids": [1, 2]}
            )

    mock_queue_api.delete_queue_bulk.assert_called_once()
    call_kwargs = mock_queue_api.delete_queue_bulk.call_args.kwargs
    assert call_kwargs["blocklist"] is False
    assert call_kwargs["remove_from_client"] is True
    assert call_kwargs["queue_bulk_resource"].ids == [1, 2]
    assert result.data["success"] is True


@pytest.mark.asyncio
async def test_radarr_remove_queue_items_with_blocklist(patched_mcp):
    tracked_item = MagicMock()
    tracked_item.id = 88
    tracked_item.download_id = "SABnzbd_nzo_xyz789"
    tracked_item.to_dict.return_value = {"id": 88, "downloadId": "SABnzbd_nzo_xyz789"}

    mock_details_api = MagicMock()
    mock_details_api.list_queue_details.return_value = [tracked_item]

    mock_queue_api = MagicMock()
    mock_queue_api.delete_queue_bulk.return_value = None

    with (
        patch("radarr.QueueDetailsApi", return_value=mock_details_api),
        patch("radarr.QueueApi", return_value=mock_queue_api),
    ):
        async with Client(patched_mcp) as client:
            result = await client.call_tool(
                "radarr_remove_queue_items", {"ids": [88], "blocklist": True}
            )

    call_kwargs = mock_queue_api.delete_queue_bulk.call_args.kwargs
    assert call_kwargs["blocklist"] is True
    assert "blocklisted" in result.data["message"].lower()


@pytest.mark.asyncio
async def test_radarr_list_queue_preserve_fields(patched_mcp):
    item = MagicMock()
    item.id = 1
    item.to_dict.return_value = {
        "id": 1,
        "title": "Some Movie",
        "status": "downloading",
        "downloadId": None,
        "downloadClient": None,
        "outputPath": None,
        "indexer": None,
        "timeleft": None,
        "errorMessage": None,
    }

    mock_api = MagicMock()
    mock_api.list_queue_details.return_value = [item]

    with patch("radarr.QueueDetailsApi", return_value=mock_api):
        async with Client(patched_mcp) as client:
            result = await client.call_tool("radarr_list_queue", {})

    for field in [
        "title",
        "status",
        "downloadId",
        "downloadClient",
        "outputPath",
        "indexer",
        "timeleft",
        "errorMessage",
    ]:
        assert field in result.data["items"][0], f"Field {field} should be present"


@pytest.mark.asyncio
async def test_radarr_remove_queue_items_empty_list(patched_mcp):
    async with Client(patched_mcp) as client:
        result = await client.call_tool("radarr_remove_queue_items", {"ids": []})

    assert result.data["success"] is False
    assert "error" in result.data


@pytest.mark.asyncio
async def test_radarr_remove_queue_items_all_tracked(patched_mcp):
    tracked_item = MagicMock()
    tracked_item.id = 1
    tracked_item.download_id = "SABnzbd_nzo_abc123"
    tracked_item.to_dict.return_value = {"id": 1, "downloadId": "SABnzbd_nzo_abc123"}

    tracked_item2 = MagicMock()
    tracked_item2.id = 2
    tracked_item2.download_id = "SABnzbd_nzo_def456"
    tracked_item2.to_dict.return_value = {"id": 2, "downloadId": "SABnzbd_nzo_def456"}

    mock_details_api = MagicMock()
    mock_details_api.list_queue_details.return_value = [tracked_item, tracked_item2]

    mock_queue_api = MagicMock()
    mock_queue_api.delete_queue_bulk.return_value = None

    with (
        patch("radarr.QueueDetailsApi", return_value=mock_details_api),
        patch("radarr.QueueApi", return_value=mock_queue_api),
    ):
        async with Client(patched_mcp) as client:
            result = await client.call_tool(
                "radarr_remove_queue_items", {"ids": [1, 2]}
            )

    mock_queue_api.delete_queue_bulk.assert_called_once()
    assert result.data["success"] is True
    assert result.data["tracked_removed"] == 2
    assert result.data["pending_removed"] == 0


@pytest.mark.asyncio
async def test_radarr_remove_queue_items_all_pending(patched_mcp):
    pending_item = MagicMock()
    pending_item.id = 10
    pending_item.download_id = None
    pending_item.to_dict.return_value = {"id": 10, "downloadId": None}

    pending_item2 = MagicMock()
    pending_item2.id = 11
    pending_item2.download_id = None
    pending_item2.to_dict.return_value = {"id": 11, "downloadId": None}

    mock_details_api = MagicMock()
    mock_details_api.list_queue_details.return_value = [pending_item, pending_item2]

    mock_queue_api = MagicMock()
    mock_queue_api.delete_queue_bulk.return_value = None

    with (
        patch("radarr.QueueDetailsApi", return_value=mock_details_api),
        patch("radarr.QueueApi", return_value=mock_queue_api),
    ):
        async with Client(patched_mcp) as client:
            result = await client.call_tool(
                "radarr_remove_queue_items", {"ids": [10, 11]}
            )

    mock_queue_api.delete_queue_bulk.assert_called_once()
    call_kwargs = mock_queue_api.delete_queue_bulk.call_args.kwargs
    assert call_kwargs["remove_from_client"] is False  # pending items
    assert result.data["pending_removed"] == 2
    assert result.data["tracked_removed"] == 0


@pytest.mark.asyncio
async def test_radarr_remove_queue_items_mixed_types(patched_mcp):
    tracked_item = MagicMock()
    tracked_item.id = 1
    tracked_item.download_id = "SABnzbd_nzo_abc123"
    tracked_item.to_dict.return_value = {"id": 1, "downloadId": "SABnzbd_nzo_abc123"}

    pending_item = MagicMock()
    pending_item.id = 10
    pending_item.download_id = None
    pending_item.to_dict.return_value = {"id": 10, "downloadId": None}

    mock_details_api = MagicMock()
    mock_details_api.list_queue_details.return_value = [tracked_item, pending_item]

    mock_queue_api = MagicMock()
    mock_queue_api.delete_queue_bulk.return_value = None

    with (
        patch("radarr.QueueDetailsApi", return_value=mock_details_api),
        patch("radarr.QueueApi", return_value=mock_queue_api),
    ):
        async with Client(patched_mcp) as client:
            result = await client.call_tool(
                "radarr_remove_queue_items", {"ids": [1, 10]}
            )

    # Should be called twice - once for tracked, once for pending
    assert mock_queue_api.delete_queue_bulk.call_count == 2
    assert result.data["tracked_removed"] == 1
    assert result.data["pending_removed"] == 1


@pytest.mark.asyncio
async def test_radarr_remove_queue_items_with_unknown(patched_mcp):
    tracked_item = MagicMock()
    tracked_item.id = 1
    tracked_item.download_id = "SABnzbd_nzo_abc123"
    tracked_item.to_dict.return_value = {"id": 1, "downloadId": "SABnzbd_nzo_abc123"}

    mock_details_api = MagicMock()
    mock_details_api.list_queue_details.return_value = [tracked_item]

    mock_queue_api = MagicMock()
    mock_queue_api.delete_queue_bulk.return_value = None

    with (
        patch("radarr.QueueDetailsApi", return_value=mock_details_api),
        patch("radarr.QueueApi", return_value=mock_queue_api),
    ):
        async with Client(patched_mcp) as client:
            result = await client.call_tool(
                "radarr_remove_queue_items", {"ids": [1, 999]}
            )

    assert result.data["success"] is True
    assert result.data["tracked_removed"] == 1
    assert result.data["errors"] is not None
    assert "999" in str(result.data["errors"])


# ---------------------------------------------------------------------------
# Reference describe tools
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_radarr_describe_quality_profile_happy_path(patched_mcp):
    mock_api = MagicMock()
    mock_api.get_quality_profile_by_id.return_value = make_mock_model(
        id=8, name="SQP-2"
    )

    with patch("radarr.QualityProfileApi", return_value=mock_api):
        async with Client(patched_mcp) as client:
            result = await client.call_tool(
                "radarr_describe_quality_profile", {"id": 8}
            )

    assert result.data["id"] == 8


@pytest.mark.asyncio
async def test_radarr_describe_quality_profile_not_found(patched_mcp):
    from radarr.exceptions import NotFoundException

    mock_api = MagicMock()
    mock_api.get_quality_profile_by_id.side_effect = NotFoundException()

    with patch("radarr.QualityProfileApi", return_value=mock_api):
        async with Client(patched_mcp) as client:
            result = await client.call_tool(
                "radarr_describe_quality_profile", {"id": 999}
            )

    assert isinstance(result.data, dict)
    assert result.data.get("error") == "not_found"


@pytest.mark.asyncio
async def test_radarr_describe_tag_happy_path(patched_mcp):
    mock_api = MagicMock()
    mock_api.get_tag_detail_by_id.return_value = make_mock_model(id=2, label="4k")

    with patch("radarr.TagDetailsApi", return_value=mock_api):
        async with Client(patched_mcp) as client:
            result = await client.call_tool("radarr_describe_tag", {"id": 2})

    assert result.data["id"] == 2


@pytest.mark.asyncio
async def test_radarr_describe_tag_not_found(patched_mcp):
    from radarr.exceptions import NotFoundException

    mock_api = MagicMock()
    mock_api.get_tag_detail_by_id.side_effect = NotFoundException()

    with patch("radarr.TagDetailsApi", return_value=mock_api):
        async with Client(patched_mcp) as client:
            result = await client.call_tool("radarr_describe_tag", {"id": 999})

    assert isinstance(result.data, dict)
    assert result.data.get("error") == "not_found"


# ---------------------------------------------------------------------------
# Collections write tools
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_radarr_describe_collection_not_found(patched_mcp):
    from radarr.exceptions import NotFoundException

    mock_api = MagicMock()
    mock_api.get_collection_by_id.side_effect = NotFoundException()

    with patch("radarr.CollectionApi", return_value=mock_api):
        async with Client(patched_mcp) as client:
            result = await client.call_tool("radarr_describe_collection", {"id": 999})

    assert result.data.get("error") == "not_found"


@pytest.mark.asyncio
async def test_radarr_update_collection_happy_path(patched_mcp):
    mock_api = MagicMock()
    mock_api.get_collection_by_id.return_value = MagicMock()
    mock_api.update_collection.return_value = make_mock_model(
        id=10, title="Matrix Collection"
    )

    with patch("radarr.CollectionApi", return_value=mock_api):
        async with Client(patched_mcp) as client:
            result = await client.call_tool(
                "radarr_update_collection", {"id": 10, "monitored": True}
            )

    mock_api.update_collection.assert_called_once()
    assert result.data["id"] == 10


@pytest.mark.asyncio
async def test_radarr_update_collection_not_found(patched_mcp):
    from radarr.exceptions import NotFoundException

    mock_api = MagicMock()
    mock_api.get_collection_by_id.side_effect = NotFoundException()

    with patch("radarr.CollectionApi", return_value=mock_api):
        async with Client(patched_mcp) as client:
            result = await client.call_tool(
                "radarr_update_collection", {"id": 999, "monitored": True}
            )

    assert isinstance(result.data, dict)
    assert result.data.get("error") == "not_found"
