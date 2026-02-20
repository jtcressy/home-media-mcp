"""Radarr reference data tools (read-only)."""

from typing import Annotated, Any

import radarr
from fastmcp.dependencies import Depends

from home_media_mcp.server import mcp
from home_media_mcp.services.radarr.server import (
    get_radarr_client,
    radarr_api_call,
)
from home_media_mcp.utils import full_detail, summarize_list


@mcp.tool(
    tags={"read"},
    annotations={"readOnlyHint": True},
)
async def radarr_list_quality_profiles(
    client: radarr.ApiClient = Depends(get_radarr_client),
) -> dict[str, Any]:
    """List all quality profiles configured in Radarr.

    Quality profiles define which qualities are acceptable for movies.
    Needed when adding movies.
    """
    api = radarr.QualityProfileApi(client)
    results = await radarr_api_call(api.list_quality_profile)
    return summarize_list(results)


@mcp.tool(
    tags={"read"},
    annotations={"readOnlyHint": True},
)
async def radarr_describe_quality_profile(
    id: Annotated[int, "The quality profile ID"],
    client: radarr.ApiClient = Depends(get_radarr_client),
) -> dict[str, Any]:
    """Get full details for a quality profile."""
    api = radarr.QualityProfileApi(client)
    try:
        result = await radarr_api_call(api.get_quality_profile_by_id, id=id)
    except radarr.NotFoundException:
        return {
            "error": "not_found",
            "message": f"Quality profile with ID {id} not found.",
        }
    return full_detail(result)


@mcp.tool(
    tags={"read"},
    annotations={"readOnlyHint": True},
)
async def radarr_list_tags(
    client: radarr.ApiClient = Depends(get_radarr_client),
) -> dict[str, Any]:
    """List all tags in Radarr."""
    api = radarr.TagApi(client)
    results = await radarr_api_call(api.list_tag)
    return summarize_list(results)


@mcp.tool(
    tags={"read"},
    annotations={"readOnlyHint": True},
)
async def radarr_describe_tag(
    id: Annotated[int, "The tag ID"],
    client: radarr.ApiClient = Depends(get_radarr_client),
) -> dict[str, Any]:
    """Get full details for a tag including what it's applied to."""
    api = radarr.TagDetailsApi(client)
    try:
        result = await radarr_api_call(api.get_tag_detail_by_id, id=id)
    except radarr.NotFoundException:
        return {"error": "not_found", "message": f"Tag with ID {id} not found."}
    return full_detail(result)


@mcp.tool(
    tags={"read"},
    annotations={"readOnlyHint": True},
)
async def radarr_list_root_folders(
    client: radarr.ApiClient = Depends(get_radarr_client),
) -> dict[str, Any]:
    """List all root folders configured in Radarr.

    Root folders are the base directories where movies are stored.
    Needed when adding new movies.
    """
    api = radarr.RootFolderApi(client)
    results = await radarr_api_call(api.list_root_folder)
    return summarize_list(results)
