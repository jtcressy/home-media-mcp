"""Sonarr history tools."""

from typing import Annotated, Any

import sonarr
from fastmcp.dependencies import Depends

from home_media_mcp.server import mcp
from home_media_mcp.services.sonarr.server import (
    get_sonarr_client,
    sonarr_api_call,
)
from home_media_mcp.utils import grep_filter, summarize_list


@mcp.tool(
    tags={"read"},
    annotations={"readOnlyHint": True},
)
async def sonarr_list_history(
    page: Annotated[int, "Page number"] = 1,
    page_size: Annotated[int, "Items per page"] = 20,
    grep: Annotated[str | None, "Regex pattern to filter results"] = None,
    client: sonarr.ApiClient = Depends(get_sonarr_client),
) -> dict[str, Any]:
    """Get Sonarr download/import history.

    Returns paginated history of grabs, downloads, imports, and other events.
    """
    api = sonarr.HistoryApi(client)
    result = await sonarr_api_call(api.list_history, page=page, page_size=page_size)
    records = result.records or []
    filtered = grep_filter(records, grep)
    return summarize_list(filtered)


@mcp.tool(
    tags={"read"},
    annotations={"readOnlyHint": True},
)
async def sonarr_list_series_history(
    series_id: Annotated[int, "The Sonarr series ID"],
    grep: Annotated[str | None, "Regex pattern to filter results"] = None,
    client: sonarr.ApiClient = Depends(get_sonarr_client),
) -> dict[str, Any]:
    """Get download/import history for a specific series."""
    api = sonarr.HistoryApi(client)
    result = await sonarr_api_call(api.list_history, series_id=series_id)
    records = result.records or []
    filtered = grep_filter(records, grep)
    return summarize_list(filtered)
