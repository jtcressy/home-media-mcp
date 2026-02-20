"""Sonarr reference data tools (read-only)."""

from typing import Annotated, Any

import sonarr
from fastmcp.dependencies import Depends

from home_media_mcp.server import mcp
from home_media_mcp.services.sonarr.server import (
    get_sonarr_client,
    sonarr_api_call,
)
from home_media_mcp.utils import full_detail, summarize_list


@mcp.tool(
    tags={"read"},
    annotations={"readOnlyHint": True},
)
async def sonarr_list_quality_profiles(
    client: sonarr.ApiClient = Depends(get_sonarr_client),
) -> dict[str, Any]:
    """List all quality profiles configured in Sonarr.

    Quality profiles define which qualities are acceptable and preferred
    for series. Needed when adding series.
    """
    api = sonarr.QualityProfileApi(client)
    results = await sonarr_api_call(api.list_quality_profile)
    return summarize_list(results)


@mcp.tool(
    tags={"read"},
    annotations={"readOnlyHint": True},
)
async def sonarr_describe_quality_profile(
    id: Annotated[int, "The quality profile ID"],
    client: sonarr.ApiClient = Depends(get_sonarr_client),
) -> dict[str, Any]:
    """Get full details for a quality profile.

    Shows allowed qualities, cutoff, and upgrade settings.
    """
    api = sonarr.QualityProfileApi(client)
    try:
        result = await sonarr_api_call(api.get_quality_profile_by_id, id=id)
    except sonarr.exceptions.NotFoundException:
        return {
            "error": "not_found",
            "message": f"Quality profile with ID {id} not found.",
        }
    return full_detail(result)


@mcp.tool(
    tags={"read"},
    annotations={"readOnlyHint": True},
)
async def sonarr_list_tags(
    client: sonarr.ApiClient = Depends(get_sonarr_client),
) -> dict[str, Any]:
    """List all tags in Sonarr.

    Tags are used to organize and link series with delay profiles,
    restrictions, and notifications.
    """
    api = sonarr.TagApi(client)
    results = await sonarr_api_call(api.list_tag)
    return summarize_list(results)


@mcp.tool(
    tags={"read"},
    annotations={"readOnlyHint": True},
)
async def sonarr_describe_tag(
    id: Annotated[int, "The tag ID"],
    client: sonarr.ApiClient = Depends(get_sonarr_client),
) -> dict[str, Any]:
    """Get full details for a tag including what it's applied to."""
    api = sonarr.TagDetailsApi(client)
    try:
        result = await sonarr_api_call(api.get_tag_detail_by_id, id=id)
    except sonarr.exceptions.NotFoundException:
        return {"error": "not_found", "message": f"Tag with ID {id} not found."}
    return full_detail(result)


@mcp.tool(
    tags={"read"},
    annotations={"readOnlyHint": True},
)
async def sonarr_list_root_folders(
    client: sonarr.ApiClient = Depends(get_sonarr_client),
) -> dict[str, Any]:
    """List all root folders configured in Sonarr.

    Root folders are the base directories where series are stored.
    Needed when adding new series.
    """
    api = sonarr.RootFolderApi(client)
    results = await sonarr_api_call(api.list_root_folder)
    return summarize_list(results)
