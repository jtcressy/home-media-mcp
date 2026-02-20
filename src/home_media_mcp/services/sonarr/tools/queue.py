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
    """List items currently in the Sonarr download queue.

    Shows what's being downloaded, their progress, and status.
    """
    api = sonarr.QueueDetailsApi(client)
    queue = await sonarr_api_call(api.list_queue_details)
    filtered = grep_filter(queue, grep)
    return summarize_list(filtered)


@mcp.tool(
    tags={"read"},
    annotations={"readOnlyHint": True},
)
async def sonarr_describe_queue_item(
    id: Annotated[int, "The queue item ID"],
    client: sonarr.ApiClient = Depends(get_sonarr_client),
) -> dict[str, Any]:
    """Get full details for a specific queue item.

    Includes download progress, status messages, quality, and indexer info.
    """
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
    """Force grab a pending queue item.

    This forces the download of an item that may be delayed or waiting.
    """
    api = sonarr.QueueApi(client)
    await sonarr_api_call(
        api.create_queue_grab_selected,
        queue_grab_bulk_resource=sonarr.QueueGrabBulkResource(ids=[id]),
    )
    return {"success": True, "message": f"Queue item {id} grabbed."}


@mcp.tool(
    tags={"write"},
    annotations={"destructiveHint": True, "readOnlyHint": False},
)
async def sonarr_remove_queue_item(
    id: Annotated[int, "The queue item ID to remove"],
    blocklist: Annotated[
        bool, "Add the release to the blocklist to prevent re-downloading"
    ] = False,
    remove_from_client: Annotated[
        bool, "Also remove the download from the download client"
    ] = True,
    client: sonarr.ApiClient = Depends(get_sonarr_client),
) -> dict[str, Any]:
    """Remove an item from the download queue.

    Optionally blocklist the release and/or remove it from the download client.
    """
    api = sonarr.QueueApi(client)
    await sonarr_api_call(
        api.delete_queue,
        id=id,
        blocklist=blocklist,
        remove_from_client=remove_from_client,
    )
    return {
        "success": True,
        "message": f"Queue item {id} removed"
        + (" and blocklisted" if blocklist else ""),
    }
