"""Sonarr queue management tools."""

from typing import Annotated, Any

import sonarr
from fastmcp.dependencies import Depends

from home_media_mcp.server import mcp
from home_media_mcp.services.sonarr.server import (
    get_sonarr_client,
    sonarr_api_call,
)
from home_media_mcp.utils import full_detail, grep_filter, summarize_list


@mcp.tool(
    tags={"read"},
    annotations={"readOnlyHint": True},
)
async def sonarr_list_queue(
    grep: Annotated[str | None, "Regex pattern to filter results"] = None,
    client: sonarr.ApiClient = Depends(get_sonarr_client),
) -> dict[str, Any]:
    """List items currently in the Sonarr download queue."""
    api = sonarr.QueueDetailsApi(client)
    queue = await sonarr_api_call(api.list_queue_details)
    filtered = grep_filter(queue, grep)
    return summarize_list(
        filtered,
        preserve_fields=[
            "title",
            "status",
            "downloadId",
            "downloadClient",
            "outputPath",
            "indexer",
            "timeleft",
            "errorMessage",
        ],
    )


@mcp.tool(
    tags={"read"},
    annotations={"readOnlyHint": True},
)
async def sonarr_describe_queue_item(
    id: Annotated[int, "The queue item ID"],
    client: sonarr.ApiClient = Depends(get_sonarr_client),
) -> dict[str, Any]:
    """Get full details for a specific queue item."""
    api = sonarr.QueueDetailsApi(client)
    # Queue details returns all items; find the one we want
    items = await sonarr_api_call(api.list_queue_details)
    for item in items:
        if item.id == id:
            return full_detail(item)
    return {"error": "not_found", "message": f"Queue item with ID {id} not found."}


@mcp.tool(
    tags={"write"},
    annotations={"destructiveHint": False, "readOnlyHint": False},
)
async def sonarr_grab_queue_item(
    id: Annotated[int, "The queue item ID to grab/force download"],
    client: sonarr.ApiClient = Depends(get_sonarr_client),
) -> dict[str, Any]:
    """Force grab a pending queue item."""
    api = sonarr.QueueActionApi(client)
    await sonarr_api_call(
        api.create_queue_grab_bulk,
        queue_bulk_resource=sonarr.QueueBulkResource(ids=[id]),
    )
    return {"success": True, "message": f"Queue item {id} grabbed."}


@mcp.tool(
    tags={"write"},
    annotations={"destructiveHint": True, "readOnlyHint": False},
)
async def sonarr_remove_queue_items(
    ids: Annotated[list[int], "List of queue item IDs to remove"],
    blocklist: Annotated[
        bool, "Add the releases to the blocklist to prevent re-downloading"
    ] = False,
    remove_from_client: Annotated[
        bool, "Also remove the downloads from the download client"
    ] = True,
    client: sonarr.ApiClient = Depends(get_sonarr_client),
) -> dict[str, Any]:
    """Remove multiple items from the download queue in a single request."""
    api = sonarr.QueueApi(client)
    await sonarr_api_call(
        api.delete_queue_bulk,
        blocklist=blocklist,
        remove_from_client=remove_from_client,
        queue_bulk_resource=sonarr.QueueBulkResource(ids=ids),
    )
    return {
        "success": True,
        "message": f"Removed {len(ids)} queue items"
        + (" and blocklisted" if blocklist else ""),
    }
