"""Radarr wanted (missing/cutoff) tools."""

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
async def radarr_list_missing(
    page: Annotated[int, "Page number"] = 1,
    page_size: Annotated[int, "Items per page"] = 20,
    grep: Annotated[str | None, "Regex pattern to filter results"] = None,
    client: radarr.ApiClient = Depends(get_radarr_client),
) -> dict[str, Any]:
    """List movies that are monitored but missing (not downloaded).

    Returns paginated list of wanted movies.
    """
    api = radarr.WantedMissingApi(client)
    result = await radarr_api_call(
        api.list_wanted_missing, page=page, page_size=page_size
    )
    records = result.records or []
    filtered = grep_filter(records, grep)
    return summarize_list(filtered)


@mcp.tool(
    tags={"read"},
    annotations={"readOnlyHint": True},
)
async def radarr_list_cutoff_unmet(
    page: Annotated[int, "Page number"] = 1,
    page_size: Annotated[int, "Items per page"] = 20,
    grep: Annotated[str | None, "Regex pattern to filter results"] = None,
    client: radarr.ApiClient = Depends(get_radarr_client),
) -> dict[str, Any]:
    """List movies that don't meet their quality profile cutoff.

    These movies have been downloaded but in a quality below the cutoff.
    """
    api = radarr.CutoffApi(client)
    result = await radarr_api_call(
        api.list_wanted_cutoff, page=page, page_size=page_size
    )
    records = result.records or []
    filtered = grep_filter(records, grep)
    return summarize_list(filtered)
