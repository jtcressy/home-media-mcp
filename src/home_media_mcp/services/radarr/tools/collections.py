"""Radarr collection management tools."""

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
async def radarr_list_collections(
    grep: Annotated[str | None, "Regex pattern to filter results"] = None,
    client: radarr.ApiClient = Depends(get_radarr_client),
) -> dict[str, Any]:
    """List all movie collections in Radarr."""
    api = radarr.CollectionApi(client)
    results = await radarr_api_call(api.list_collection)
    filtered = grep_filter(results, grep)
    return summarize_list(filtered)


@mcp.tool(
    tags={"read"},
    annotations={"readOnlyHint": True},
)
async def radarr_describe_collection(
    id: Annotated[int, "The collection ID"],
    client: radarr.ApiClient = Depends(get_radarr_client),
) -> dict[str, Any]:
    """Get full details for a movie collection."""
    api = radarr.CollectionApi(client)
    try:
        result = await radarr_api_call(api.get_collection_by_id, id=id)
    except radarr.exceptions.NotFoundException:
        return {"error": "not_found", "message": f"Collection with ID {id} not found."}
    return full_detail(result)


@mcp.tool(
    tags={"write"},
    annotations={"destructiveHint": False, "readOnlyHint": False},
)
async def radarr_update_collection(
    id: Annotated[int, "The collection ID to update"],
    monitored: Annotated[
        bool | None, "Set monitored status for all movies in collection"
    ] = None,
    quality_profile: Annotated[str | int | None, "Quality profile name or ID"] = None,
    root_folder: Annotated[str | int | None, "Root folder path or ID"] = None,
    minimum_availability: Annotated[
        str | None,
        "When to consider available: 'announced', 'inCinemas', 'released', 'preDB'",
    ] = None,
    client: radarr.ApiClient = Depends(get_radarr_client),
) -> dict[str, Any]:
    """Update a movie collection's settings. Changes apply to all movies in the collection."""
    api = radarr.CollectionApi(client)

    try:
        collection = await radarr_api_call(api.get_collection_by_id, id=id)
    except radarr.exceptions.NotFoundException:
        return {"error": "not_found", "message": f"Collection with ID {id} not found."}

    if monitored is not None:
        collection.monitored = monitored
    if quality_profile is not None:
        from home_media_mcp.utils import resolve_quality_profile

        qp_api = radarr.QualityProfileApi(client)
        profiles = await radarr_api_call(qp_api.list_quality_profile)
        collection.quality_profile_id = resolve_quality_profile(
            quality_profile, profiles
        )
    if root_folder is not None:
        from home_media_mcp.utils import resolve_root_folder

        rf_api = radarr.RootFolderApi(client)
        folders = await radarr_api_call(rf_api.list_root_folder)
        folder_id = resolve_root_folder(root_folder, folders)
        collection.root_folder_path = next(f.path for f in folders if f.id == folder_id)
    if minimum_availability is not None:
        collection.minimum_availability = minimum_availability

    result = await radarr_api_call(
        api.update_collection, id=str(id), collection_resource=collection
    )
    return full_detail(result)
