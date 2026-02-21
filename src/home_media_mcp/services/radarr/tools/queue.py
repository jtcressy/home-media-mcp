"""Radarr queue management tools."""

import asyncio
from typing import Annotated, Any

import radarr
from fastmcp.dependencies import Depends

from home_media_mcp.server import mcp
from home_media_mcp.services.radarr.server import (
    get_radarr_client,
    radarr_api_call,
)
from home_media_mcp.utils import full_detail, grep_filter, summarize_list


@mcp.tool(
    tags={"read"},
    annotations={"readOnlyHint": True},
)
async def radarr_list_queue(
    grep: Annotated[str | None, "Regex pattern to filter results"] = None,
    client: radarr.ApiClient = Depends(get_radarr_client),
) -> dict[str, Any]:
    """List items currently in the Radarr download queue."""
    api = radarr.QueueDetailsApi(client)
    queue = await radarr_api_call(api.list_queue_details)
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
async def radarr_describe_queue_item(
    id: Annotated[int, "The queue item ID"],
    client: radarr.ApiClient = Depends(get_radarr_client),
) -> dict[str, Any]:
    """Get full details for a specific queue item."""
    api = radarr.QueueDetailsApi(client)
    items = await radarr_api_call(api.list_queue_details)
    for item in items:
        if item.id == id:
            return full_detail(item)
    return {"error": "not_found", "message": f"Queue item with ID {id} not found."}


@mcp.tool(
    tags={"write"},
    annotations={"destructiveHint": False, "readOnlyHint": False},
)
async def radarr_grab_queue_item(
    id: Annotated[int, "The queue item ID to grab/force download"],
    client: radarr.ApiClient = Depends(get_radarr_client),
) -> dict[str, Any]:
    """Force grab a pending queue item."""
    api = radarr.QueueActionApi(client)
    await radarr_api_call(
        api.create_queue_grab_bulk,
        queue_bulk_resource=radarr.QueueBulkResource(ids=[id]),
    )
    return {"success": True, "message": f"Queue item {id} grabbed."}


@mcp.tool(
    tags={"write"},
    annotations={"destructiveHint": True, "readOnlyHint": False},
)
async def radarr_remove_queue_items(
    ids: Annotated[list[int], "List of queue item IDs to remove"],
    blocklist: Annotated[
        bool, "Add the releases to the blocklist to prevent re-downloading"
    ] = False,
    remove_from_client: Annotated[
        bool, "Also remove the downloads from the download client"
    ] = True,
    client: radarr.ApiClient = Depends(get_radarr_client),
) -> dict[str, Any]:
    """Remove multiple items from the download queue in a single request."""
    if not ids:
        return {"success": False, "error": "No queue item IDs provided."}

    details_api = radarr.QueueDetailsApi(client)
    queue_items = await radarr_api_call(details_api.list_queue_details)
    queue_by_id = {item.id: item for item in queue_items}

    tracked_ids = []
    pending_ids = []
    unknown_ids = []

    for queue_id in ids:
        item = queue_by_id.get(queue_id)
        if item is None:
            unknown_ids.append(queue_id)
        elif getattr(item, "download_id", None):
            tracked_ids.append(queue_id)
        else:
            pending_ids.append(queue_id)

    api = radarr.QueueApi(client)
    tasks = []

    if tracked_ids:
        tasks.append(
            radarr_api_call(
                api.delete_queue_bulk,
                blocklist=blocklist,
                remove_from_client=remove_from_client,
                queue_bulk_resource=radarr.QueueBulkResource(ids=tracked_ids),
            )
        )
    if pending_ids:
        tasks.append(
            radarr_api_call(
                api.delete_queue_bulk,
                blocklist=blocklist,
                remove_from_client=False,
                queue_bulk_resource=radarr.QueueBulkResource(ids=pending_ids),
            )
        )

    errors = []
    if tasks:
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                which = "tracked" if i == 0 and tracked_ids else "pending"
                errors.append(f"Failed to remove {which} items: {result}")

    if unknown_ids:
        errors.append(f"IDs not found in queue: {unknown_ids}")

    removed_count = len(tracked_ids) + len(pending_ids)
    return {
        "success": removed_count > 0,
        "message": f"Removed {removed_count} queue items"
        + (" and blocklisted" if blocklist else ""),
        "tracked_removed": len(tracked_ids),
        "pending_removed": len(pending_ids),
        "errors": errors or None,
    }
