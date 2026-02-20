"""Sonarr command tools."""

from typing import Annotated, Any

from pydantic import Field

import sonarr
from fastmcp.dependencies import Depends

from home_media_mcp.server import mcp
from home_media_mcp.services.sonarr.server import (
    get_sonarr_client,
    sonarr_api_call,
    sonarr_post_command,
)
from home_media_mcp.utils import full_detail, summarize_list


@mcp.tool(
    tags={"write"},
    annotations={"destructiveHint": False, "readOnlyHint": False},
)
async def sonarr_run_command(
    name: Annotated[
        str,
        Field(
            description="Command name: RefreshSeries, RescanSeries, EpisodeSearch, SeasonSearch, SeriesSearch, RssSync, RenameFiles, RenameSeries, Backup, MissingEpisodeSearch, CutoffUnmetEpisodeSearch"
        ),
    ],
    series_id: Annotated[int | None, "Series ID (for series-specific commands)"] = None,
    season_number: Annotated[int | None, "Season number (for SeasonSearch)"] = None,
    episode_ids: Annotated[list[int] | None, "Episode IDs (for EpisodeSearch)"] = None,
    client: sonarr.ApiClient = Depends(get_sonarr_client),
) -> dict[str, Any]:
    """Execute a Sonarr background command."""
    body: dict[str, Any] = {"name": name}
    if series_id is not None:
        body["seriesId"] = series_id
    if season_number is not None:
        body["seasonNumber"] = season_number
    if episode_ids is not None:
        body["episodeIds"] = episode_ids

    result = await sonarr_post_command(client, body)
    return full_detail(result)


@mcp.tool(
    tags={"read"},
    annotations={"readOnlyHint": True},
)
async def sonarr_list_commands(
    client: sonarr.ApiClient = Depends(get_sonarr_client),
) -> dict[str, Any]:
    """List recent and currently running Sonarr commands."""
    api = sonarr.CommandApi(client)
    results = await sonarr_api_call(api.list_command)
    return summarize_list(results)


@mcp.tool(
    tags={"read"},
    annotations={"readOnlyHint": True},
)
async def sonarr_describe_command(
    id: Annotated[int, "The command ID"],
    client: sonarr.ApiClient = Depends(get_sonarr_client),
) -> dict[str, Any]:
    """Get the status of a specific command."""
    api = sonarr.CommandApi(client)
    try:
        result = await sonarr_api_call(api.get_command_by_id, id=id)
    except sonarr.exceptions.NotFoundException:
        return {"error": "not_found", "message": f"Command with ID {id} not found."}
    return full_detail(result)
