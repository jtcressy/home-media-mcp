"""Sonarr release search tools."""

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
async def sonarr_search_releases(
    episode_id: Annotated[int, "The episode ID to search releases for"],
    grep: Annotated[str | None, "Regex pattern to filter results"] = None,
    client: sonarr.ApiClient = Depends(get_sonarr_client),
) -> dict[str, Any]:
    """Search indexers for available releases of a specific episode.

    Returns available downloads with their quality, size, indexer, and other details.
    Use download_release to download one.
    """
    api = sonarr.ReleaseApi(client)
    releases = await sonarr_api_call(api.list_release, episode_id=episode_id)
    filtered = grep_filter(releases, grep)
    return summarize_list(filtered)


@mcp.tool(
    tags={"write"},
    annotations={"destructiveHint": False, "readOnlyHint": False},
)
async def sonarr_download_release(
    guid: Annotated[str, "The release GUID from search_releases results"],
    indexer_id: Annotated[int, "The indexer ID from search_releases results"],
    client: sonarr.ApiClient = Depends(get_sonarr_client),
) -> dict[str, Any]:
    """Download a specific release found via search_releases.

    The guid and indexer_id come from the search_releases results.
    """
    api = sonarr.ReleaseApi(client)
    resource = sonarr.ReleaseResource(guid=guid, indexer_id=indexer_id)
    result = await sonarr_api_call(api.create_release, release_resource=resource)
    return full_detail(result)
