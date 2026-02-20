"""Radarr command tools."""

from typing import Annotated, Any

import radarr
from fastmcp.dependencies import Depends

from home_media_mcp.server import mcp
from home_media_mcp.services.radarr.server import (
    get_radarr_client,
    radarr_api_call,
)
from home_media_mcp.utils import full_detail, summarize_list


@mcp.tool(
    tags={"write"},
    annotations={"destructiveHint": False, "readOnlyHint": False},
)
async def radarr_run_command(
    name: Annotated[
        str,
        "Command name: RefreshMovie, RescanMovie, MoviesSearch, "
        "RssSync, RenameFiles, RenameMovie, Backup, "
        "MissingMoviesSearch, CutoffUnmetMoviesSearch, "
        "RefreshCollections, RefreshMonitoredDownloads",
    ],
    movie_ids: Annotated[
        list[int] | None, "Movie IDs (for movie-specific commands)"
    ] = None,
    client: radarr.ApiClient = Depends(get_radarr_client),
) -> dict[str, Any]:
    """Execute a Radarr command.

    Triggers background tasks like movie refresh, RSS sync, search, etc.
    Returns the command status (use describe_command to check progress).
    """
    api = radarr.CommandApi(client)

    body: dict[str, Any] = {"name": name}
    if movie_ids is not None:
        body["movieIds"] = movie_ids

    resource = radarr.CommandResource(**body)
    result = await radarr_api_call(api.create_command, command_resource=resource)
    return full_detail(result)


@mcp.tool(
    tags={"read"},
    annotations={"readOnlyHint": True},
)
async def radarr_list_commands(
    client: radarr.ApiClient = Depends(get_radarr_client),
) -> dict[str, Any]:
    """List recent and currently running Radarr commands."""
    api = radarr.CommandApi(client)
    results = await radarr_api_call(api.list_command)
    return summarize_list(results)


@mcp.tool(
    tags={"read"},
    annotations={"readOnlyHint": True},
)
async def radarr_describe_command(
    id: Annotated[int, "The command ID"],
    client: radarr.ApiClient = Depends(get_radarr_client),
) -> dict[str, Any]:
    """Get the status of a specific command."""
    api = radarr.CommandApi(client)
    try:
        result = await radarr_api_call(api.get_command_by_id, id=id)
    except radarr.exceptions.NotFoundException:
        return {"error": "not_found", "message": f"Command with ID {id} not found."}
    return full_detail(result)
