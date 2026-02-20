"""Radarr blocklist tools."""

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
async def radarr_list_blocklist(
    page: Annotated[int, "Page number"] = 1,
    page_size: Annotated[int, "Items per page"] = 20,
    grep: Annotated[str | None, "Regex pattern to filter results"] = None,
    client: radarr.ApiClient = Depends(get_radarr_client),
) -> dict[str, Any]:
    """List blocklisted releases in Radarr."""
    api = radarr.BlocklistApi(client)
    result = await radarr_api_call(api.get_blocklist, page=page, page_size=page_size)
    records = result.records or []
    filtered = grep_filter(records, grep)
    return summarize_list(filtered)


@mcp.tool(
    tags={"write"},
    annotations={"destructiveHint": True, "readOnlyHint": False},
)
async def radarr_remove_blocklist_item(
    id: Annotated[int, "The blocklist item ID to remove"],
    client: radarr.ApiClient = Depends(get_radarr_client),
) -> dict[str, Any]:
    """Remove an item from the blocklist to allow re-downloading."""
    api = radarr.BlocklistApi(client)
    await radarr_api_call(api.delete_blocklist, id=id)
    return {"success": True, "message": f"Blocklist item {id} removed."}
