"""Sonarr rename preview tools."""

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
async def sonarr_preview_rename(
    series_id: Annotated[int, "The Sonarr series ID"],
    season_number: Annotated[
        int | None, "Optionally limit to a specific season"
    ] = None,
    grep: Annotated[str | None, "Regex pattern to filter results"] = None,
    client: sonarr.ApiClient = Depends(get_sonarr_client),
) -> dict[str, Any]:
    """Preview how episode files would be renamed.

    Shows the current filename and the new filename based on Sonarr's
    naming configuration. Use run_command with 'RenameFiles' to execute.
    """
    api = sonarr.RenameEpisodeApi(client)
    kwargs: dict[str, Any] = {"series_id": series_id}
    if season_number is not None:
        kwargs["season_number"] = season_number
    results = await sonarr_api_call(api.list_rename, **kwargs)
    filtered = grep_filter(results, grep)
    return summarize_list(filtered)
