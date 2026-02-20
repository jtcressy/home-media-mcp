"""Radarr rename preview tools."""

from typing import Annotated, Any

import radarr
from fastmcp.dependencies import Depends

from home_media_mcp.server import mcp
from home_media_mcp.services.radarr.server import (
    get_radarr_client,
    radarr_api_call,
)
from home_media_mcp.utils import grep_filter, summarize_list


@mcp.tool(
    tags={"read"},
    annotations={"readOnlyHint": True},
)
async def radarr_preview_rename(
    movie_id: Annotated[int, "The Radarr movie ID"],
    grep: Annotated[str | None, "Regex pattern to filter results"] = None,
    client: radarr.ApiClient = Depends(get_radarr_client),
) -> dict[str, Any]:
    """Preview how movie files would be renamed based on Radarr's naming config."""
    api = radarr.RenameMovieApi(client)
    results = await radarr_api_call(api.list_rename, movie_id=movie_id)
    filtered = grep_filter(results, grep)
    return summarize_list(filtered)
