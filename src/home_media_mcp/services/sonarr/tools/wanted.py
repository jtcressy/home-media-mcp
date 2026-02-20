"""Sonarr wanted (missing/cutoff) tools."""

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
async def sonarr_list_missing(
    page: Annotated[int, "Page number"] = 1,
    page_size: Annotated[int, "Items per page"] = 20,
    grep: Annotated[str | None, "Regex pattern to filter results"] = None,
    client: sonarr.ApiClient = Depends(get_sonarr_client),
) -> dict[str, Any]:
    """List episodes that are monitored but missing (not downloaded).

    Returns paginated list of wanted episodes.
    """
    api = sonarr.MissingApi(client)
    result = await sonarr_api_call(
        api.get_wanted_missing, page=page, page_size=page_size
    )
    records = result.records or []
    filtered = grep_filter(records, grep)
    return summarize_list(filtered)


@mcp.tool(
    tags={"read"},
    annotations={"readOnlyHint": True},
)
async def sonarr_list_cutoff_unmet(
    page: Annotated[int, "Page number"] = 1,
    page_size: Annotated[int, "Items per page"] = 20,
    grep: Annotated[str | None, "Regex pattern to filter results"] = None,
    client: sonarr.ApiClient = Depends(get_sonarr_client),
) -> dict[str, Any]:
    """List episodes that don't meet their quality profile cutoff.

    These episodes have been downloaded but in a quality below the cutoff
    defined in their quality profile.
    """
    api = sonarr.CutoffApi(client)
    result = await sonarr_api_call(
        api.get_wanted_cutoff, page=page, page_size=page_size
    )
    records = result.records or []
    filtered = grep_filter(records, grep)
    return summarize_list(filtered)
