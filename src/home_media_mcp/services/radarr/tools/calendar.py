"""Radarr calendar tools."""

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
async def radarr_get_calendar(
    start: Annotated[str | None, "Start date (ISO 8601, e.g., 2024-01-01)"] = None,
    end: Annotated[str | None, "End date (ISO 8601, e.g., 2024-01-31)"] = None,
    grep: Annotated[str | None, "Regex pattern to filter results"] = None,
    client: radarr.ApiClient = Depends(get_radarr_client),
) -> dict[str, Any]:
    """Get upcoming movie releases from the Radarr calendar."""
    api = radarr.CalendarApi(client)
    kwargs: dict[str, Any] = {}
    if start is not None:
        kwargs["start"] = start
    if end is not None:
        kwargs["end"] = end
    movies = await radarr_api_call(api.list_calendar, **kwargs)
    filtered = grep_filter(movies, grep)
    return summarize_list(filtered)
