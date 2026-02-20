"""Radarr movie file management tools."""

from typing import Annotated, Any

import radarr
from fastmcp.dependencies import Depends

from home_media_mcp.server import mcp
from home_media_mcp.services.radarr.server import (
    get_radarr_client,
    radarr_api_call,
)
from home_media_mcp.utils import full_detail, grep_filter, summarize_list


@mcp.tool(
    tags={"read"},
    annotations={"readOnlyHint": True},
)
async def radarr_list_movie_files(
    movie_id: Annotated[int, "The Radarr movie ID"],
    grep: Annotated[str | None, "Regex pattern to filter results"] = None,
    client: radarr.ApiClient = Depends(get_radarr_client),
) -> dict[str, Any]:
    """List all files for a movie. Use describe_movie_file for full details."""
    api = radarr.MovieFileApi(client)
    files = await radarr_api_call(api.list_movie_file, movie_id=[movie_id])
    filtered = grep_filter(files, grep)
    return summarize_list(filtered)


@mcp.tool(
    tags={"read"},
    annotations={"readOnlyHint": True},
)
async def radarr_describe_movie_file(
    id: Annotated[int, "The movie file ID"],
    client: radarr.ApiClient = Depends(get_radarr_client),
) -> dict[str, Any]:
    """Get full details for a specific movie file."""
    api = radarr.MovieFileApi(client)
    try:
        result = await radarr_api_call(api.get_movie_file_by_id, id=id)
    except radarr.exceptions.NotFoundException:
        return {"error": "not_found", "message": f"Movie file with ID {id} not found."}
    return full_detail(result)


@mcp.tool(
    tags={"write"},
    annotations={"destructiveHint": True, "readOnlyHint": False},
)
async def radarr_delete_movie_file(
    id: Annotated[int, "The movie file ID to delete"],
    client: radarr.ApiClient = Depends(get_radarr_client),
) -> dict[str, Any]:
    """Delete a movie file from disk permanently."""
    api = radarr.MovieFileApi(client)
    try:
        await radarr_api_call(api.delete_movie_file, id=id)
    except radarr.exceptions.NotFoundException:
        return {"error": "not_found", "message": f"Movie file with ID {id} not found."}
    return {"success": True, "message": f"Movie file {id} deleted from disk."}
