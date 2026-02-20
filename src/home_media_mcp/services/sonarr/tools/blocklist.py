"""Sonarr blocklist tools."""

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
async def sonarr_list_blocklist(
    page: Annotated[int, "Page number"] = 1,
    page_size: Annotated[int, "Items per page"] = 20,
    grep: Annotated[str | None, "Regex pattern to filter results"] = None,
    client: sonarr.ApiClient = Depends(get_sonarr_client),
) -> dict[str, Any]:
    """List blocklisted releases in Sonarr."""
    api = sonarr.BlocklistApi(client)
    result = await sonarr_api_call(api.get_blocklist, page=page, page_size=page_size)
    records = result.records or []
    filtered = grep_filter(records, grep)
    return summarize_list(filtered)


@mcp.tool(
    tags={"write"},
    annotations={"destructiveHint": True, "readOnlyHint": False},
)
async def sonarr_remove_blocklist_item(
    id: Annotated[int, "The blocklist item ID to remove"],
    client: sonarr.ApiClient = Depends(get_sonarr_client),
) -> dict[str, Any]:
    """Remove an item from the blocklist to allow re-downloading."""
    api = sonarr.BlocklistApi(client)
    await sonarr_api_call(api.delete_blocklist, id=id)
    return {"success": True, "message": f"Blocklist item {id} removed."}
