"""Sonarr series management tools."""

from typing import Annotated, Any

import sonarr
from fastmcp.dependencies import Depends

from home_media_mcp.server import mcp
from home_media_mcp.services.sonarr.server import (
    get_sonarr_client,
    sonarr_api_call,
)
from home_media_mcp.utils import (
    full_detail,
    grep_filter,
    resolve_quality_profile,
    resolve_root_folder,
    summarize_list,
)


@mcp.tool(
    tags={"read"},
    annotations={"readOnlyHint": True},
)
async def sonarr_list_series(
    grep: Annotated[str | None, "Regex pattern to filter results"] = None,
    client: sonarr.ApiClient = Depends(get_sonarr_client),
) -> dict[str, Any]:
    """List all series in Sonarr with summary info. Use describe_series for full details."""
    api = sonarr.SeriesApi(client)
    all_series = await sonarr_api_call(api.list_series)
    filtered = grep_filter(all_series, grep)
    return summarize_list(filtered, summary_fn=_sonarr_series_summary)


@mcp.tool(
    tags={"read"},
    annotations={"readOnlyHint": True},
)
async def sonarr_describe_series(
    id: Annotated[int, "The Sonarr series ID"],
    client: sonarr.ApiClient = Depends(get_sonarr_client),
) -> dict[str, Any]:
    """Get full details for a specific series by ID."""
    api = sonarr.SeriesApi(client)
    try:
        result = await sonarr_api_call(api.get_series_by_id, id=id)
    except sonarr.exceptions.NotFoundException:
        return {"error": "not_found", "message": f"Series with ID {id} not found."}
    return full_detail(result)


@mcp.tool(
    tags={"read"},
    annotations={"readOnlyHint": True},
)
async def sonarr_lookup_series(
    term: Annotated[str, "Search term (title, TVDB ID, or IMDB ID)"],
    client: sonarr.ApiClient = Depends(get_sonarr_client),
) -> dict[str, Any]:
    """Search TheTVDB for series to add. Use the tvdbId from results with add_series."""
    api = sonarr.SeriesLookupApi(client)
    results = await sonarr_api_call(api.list_series_lookup, term=term)
    return summarize_list(results, preserve_fields=["title", "tvdbId"])


@mcp.tool(
    tags={"write"},
    annotations={"destructiveHint": False, "readOnlyHint": False},
)
async def sonarr_add_series(
    tvdb_id: Annotated[int, "TVDB ID of the series to add (from lookup_series)"],
    quality_profile: Annotated[
        str | int,
        "Quality profile name or ID",
    ],
    root_folder: Annotated[
        str | int,
        "Root folder path or ID where the series will be stored",
    ],
    monitored: Annotated[bool, "Whether to monitor the series for new episodes"] = True,
    season_folder: Annotated[bool, "Whether to use season folders"] = True,
    search_for_missing: Annotated[
        bool, "Whether to search for missing episodes after adding"
    ] = True,
    client: sonarr.ApiClient = Depends(get_sonarr_client),
) -> dict[str, Any]:
    """Add a series to Sonarr by tvdbId. Use lookup_series, list_quality_profiles, and list_root_folders first."""
    api = sonarr.SeriesApi(client)

    # Resolve human-friendly names to IDs
    qp_api = sonarr.QualityProfileApi(client)
    profiles = await sonarr_api_call(qp_api.list_quality_profile)
    quality_profile_id = resolve_quality_profile(quality_profile, profiles)

    rf_api = sonarr.RootFolderApi(client)
    folders = await sonarr_api_call(rf_api.list_root_folder)
    root_folder_id = resolve_root_folder(root_folder, folders)
    root_folder_path = next(f.path for f in folders if f.id == root_folder_id)

    # Lookup series info from TVDB
    lookup_api = sonarr.SeriesLookupApi(client)
    lookup_results = await sonarr_api_call(
        lookup_api.list_series_lookup, term=f"tvdb:{tvdb_id}"
    )
    if not lookup_results:
        return {
            "error": "not_found",
            "message": f"No series found with TVDB ID {tvdb_id}.",
        }

    series_data = lookup_results[0]
    series_data.quality_profile_id = quality_profile_id
    series_data.root_folder_path = root_folder_path
    series_data.monitored = monitored
    series_data.season_folder = season_folder
    series_data.add_options = sonarr.AddSeriesOptions(
        search_for_missing_episodes=search_for_missing,
    )

    result = await sonarr_api_call(api.create_series, series_resource=series_data)
    return full_detail(result)


@mcp.tool(
    tags={"write"},
    annotations={"destructiveHint": False, "readOnlyHint": False},
)
async def sonarr_update_series(
    id: Annotated[int, "The Sonarr series ID to update"],
    monitored: Annotated[bool | None, "Set monitored status"] = None,
    quality_profile: Annotated[
        str | int | None, "New quality profile name or ID"
    ] = None,
    series_type: Annotated[
        str | None, "Series type: 'standard', 'daily', 'anime'"
    ] = None,
    season_folder: Annotated[bool | None, "Enable/disable season folders"] = None,
    path: Annotated[str | None, "New file path for the series"] = None,
    tags: Annotated[list[str | int] | None, "Set tags (names or IDs)"] = None,
    client: sonarr.ApiClient = Depends(get_sonarr_client),
) -> dict[str, Any]:
    """Update series-level settings. For per-season or per-episode monitoring, use update_season or update_episodes instead."""
    api = sonarr.SeriesApi(client)

    try:
        series = await sonarr_api_call(api.get_series_by_id, id=id)
    except sonarr.exceptions.NotFoundException:
        return {"error": "not_found", "message": f"Series with ID {id} not found."}

    if monitored is not None:
        series.monitored = monitored
    if quality_profile is not None:
        qp_api = sonarr.QualityProfileApi(client)
        profiles = await sonarr_api_call(qp_api.list_quality_profile)
        series.quality_profile_id = resolve_quality_profile(quality_profile, profiles)
    if series_type is not None:
        series.series_type = series_type
    if season_folder is not None:
        series.season_folder = season_folder
    if path is not None:
        series.path = path
    if tags is not None:
        tag_api = sonarr.TagApi(client)
        all_tags = await sonarr_api_call(tag_api.list_tag)
        from home_media_mcp.utils import resolve_tag

        series.tags = [resolve_tag(t, all_tags) for t in tags]

    result = await sonarr_api_call(
        api.update_series, id=str(id), series_resource=series
    )
    return full_detail(result)


@mcp.tool(
    tags={"write"},
    annotations={"destructiveHint": True, "readOnlyHint": False},
)
async def sonarr_delete_series(
    id: Annotated[int, "The Sonarr series ID to delete"],
    delete_files: Annotated[bool, "Also delete the series files from disk"] = False,
    client: sonarr.ApiClient = Depends(get_sonarr_client),
) -> dict[str, Any]:
    """Delete a series from Sonarr. If delete_files is True, media files are also removed from disk."""
    api = sonarr.SeriesApi(client)
    try:
        await sonarr_api_call(api.delete_series, id=id, delete_files=delete_files)
    except sonarr.exceptions.NotFoundException:
        return {"error": "not_found", "message": f"Series with ID {id} not found."}
    return {
        "success": True,
        "message": f"Series {id} deleted"
        + (" (files also deleted)" if delete_files else " (files preserved)"),
    }


def _sonarr_series_summary(items: list) -> dict[str, Any]:
    """Generate aggregate stats for series list summary."""
    monitored = sum(1 for s in items if getattr(s, "monitored", False))
    return {
        "monitored": monitored,
        "unmonitored": len(items) - monitored,
    }
