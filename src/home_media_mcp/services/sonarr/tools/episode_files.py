"""Sonarr episode file management tools."""

from typing import Annotated, Any

import sonarr
from fastmcp.dependencies import Depends

from home_media_mcp.server import mcp
from home_media_mcp.services.sonarr.server import (
    get_sonarr_client,
    sonarr_api_call,
)
from home_media_mcp.utils import full_detail, grep_filter, summarize_list


@mcp.tool(
    tags={"read"},
    annotations={"readOnlyHint": True},
)
async def sonarr_list_episode_files(
    series_id: Annotated[int, "The Sonarr series ID"],
    grep: Annotated[str | None, "Regex pattern to filter results"] = None,
    client: sonarr.ApiClient = Depends(get_sonarr_client),
) -> dict[str, Any]:
    """List all episode files for a series.

    Returns summary information about each file. Use describe_episode_file
    for full details including quality, media info, and file path.
    """
    api = sonarr.EpisodeFileApi(client)
    files = await sonarr_api_call(api.list_episode_file, series_id=series_id)
    filtered = grep_filter(files, grep)
    return summarize_list(filtered)


@mcp.tool(
    tags={"read"},
    annotations={"readOnlyHint": True},
)
async def sonarr_describe_episode_file(
    id: Annotated[int, "The Sonarr episode file ID"],
    client: sonarr.ApiClient = Depends(get_sonarr_client),
) -> dict[str, Any]:
    """Get full details for a specific episode file.

    Includes quality, media info, languages, path, size, and more.
    """
    api = sonarr.EpisodeFileApi(client)
    try:
        result = await sonarr_api_call(api.get_episode_file_by_id, id=id)
    except sonarr.NotFoundException:
        return {
            "error": "not_found",
            "message": f"Episode file with ID {id} not found.",
        }
    return full_detail(result)


@mcp.tool(
    tags={"write"},
    annotations={"destructiveHint": True, "readOnlyHint": False},
)
async def sonarr_delete_episode_file(
    id: Annotated[int, "The Sonarr episode file ID to delete"],
    client: sonarr.ApiClient = Depends(get_sonarr_client),
) -> dict[str, Any]:
    """Delete an episode file from disk.

    This permanently removes the file. The episode will show as missing
    in Sonarr. This action cannot be undone.
    """
    api = sonarr.EpisodeFileApi(client)
    try:
        await sonarr_api_call(api.delete_episode_file, id=id)
    except sonarr.NotFoundException:
        return {
            "error": "not_found",
            "message": f"Episode file with ID {id} not found.",
        }
    return {"success": True, "message": f"Episode file {id} deleted from disk."}
