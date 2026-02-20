"""Radarr history tools."""

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
async def radarr_list_history(
    page: Annotated[int, "Page number"] = 1,
    page_size: Annotated[int, "Items per page"] = 20,
    grep: Annotated[str | None, "Regex pattern to filter results"] = None,
    client: radarr.ApiClient = Depends(get_radarr_client),
) -> dict[str, Any]:
    """Get Radarr download/import history.

    Returns paginated history of grabs, downloads, imports, and other events.
    """
    api = radarr.HistoryApi(client)
    result = await radarr_api_call(api.list_history, page=page, page_size=page_size)
    records = result.records or []
    filtered = grep_filter(records, grep)
    return summarize_list(filtered)


@mcp.tool(
    tags={"read"},
    annotations={"readOnlyHint": True},
)
async def radarr_list_movie_history(
    movie_id: Annotated[int, "The Radarr movie ID"],
    grep: Annotated[str | None, "Regex pattern to filter results"] = None,
    client: radarr.ApiClient = Depends(get_radarr_client),
) -> dict[str, Any]:
    """Get download/import history for a specific movie."""
    api = radarr.HistoryApi(client)
    result = await radarr_api_call(api.list_history, movie_id=movie_id)
    records = result.records or []
    filtered = grep_filter(records, grep)
    return summarize_list(filtered)
