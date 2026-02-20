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
    movie_id: Annotated[int | None, "The Radarr movie ID"] = None,
    client: radarr.ApiClient = Depends(get_radarr_client),
) -> dict[str, Any]:
    """Get Radarr download/import history. When movie_id is provided, returns all history for that movie (unpaginated); otherwise returns paginated global history."""
    api = radarr.HistoryApi(client)
    if movie_id is not None:
        records = await radarr_api_call(api.list_history_movie, movie_id=movie_id)
        filtered = grep_filter(records, grep)
        return summarize_list(filtered)
    result = await radarr_api_call(api.get_history, page=page, page_size=page_size)
    records = result.records or []
    filtered = grep_filter(records, grep)
    return summarize_list(filtered)
