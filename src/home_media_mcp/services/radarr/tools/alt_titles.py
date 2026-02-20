"""Radarr alternative titles tools."""

from typing import Annotated, Any

import radarr
from fastmcp.dependencies import Depends

from home_media_mcp.server import mcp
from home_media_mcp.services.radarr.server import (
    get_radarr_client,
    radarr_api_call,
)
from home_media_mcp.utils import summarize_list


@mcp.tool(
    tags={"read"},
    annotations={"readOnlyHint": True},
)
async def radarr_list_alternative_titles(
    movie_id: Annotated[int, "The Radarr movie ID"],
    client: radarr.ApiClient = Depends(get_radarr_client),
) -> dict[str, Any]:
    """List alternative titles for a movie.

    Shows international titles, alternate names, and other known titles.
    """
    api = radarr.AlternativeTitleApi(client)
    results = await radarr_api_call(api.list_alttitle, movie_id=movie_id)
    return summarize_list(results)
