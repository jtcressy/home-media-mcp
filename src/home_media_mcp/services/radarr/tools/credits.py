"""Radarr credits tools."""

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
async def radarr_list_credits(
    movie_id: Annotated[int, "The Radarr movie ID"],
    grep: Annotated[str | None, "Regex pattern to filter results"] = None,
    client: radarr.ApiClient = Depends(get_radarr_client),
) -> dict[str, Any]:
    """List cast and crew credits for a movie.

    Returns actors, directors, writers, and other crew members.
    """
    api = radarr.CreditApi(client)
    results = await radarr_api_call(api.list_credit, movie_id=movie_id)
    filtered = grep_filter(results, grep)
    return summarize_list(filtered)
