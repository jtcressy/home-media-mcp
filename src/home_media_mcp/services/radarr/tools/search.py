"""Radarr release search tools."""

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
async def radarr_search_releases(
    movie_id: Annotated[int, "The movie ID to search releases for"],
    grep: Annotated[str | None, "Regex pattern to filter results"] = None,
    client: radarr.ApiClient = Depends(get_radarr_client),
) -> dict[str, Any]:
    """Search indexers for releases of a movie. Use download_release with the guid and indexerId from results."""
    api = radarr.ReleaseApi(client)
    releases = await radarr_api_call(api.list_release, movie_id=movie_id)
    filtered = grep_filter(releases, grep)
    return summarize_list(
        filtered, preserve_fields=["guid", "indexerId", "title", "size", "approved"]
    )


@mcp.tool(
    tags={"write"},
    annotations={"destructiveHint": False, "readOnlyHint": False},
)
async def radarr_download_release(
    guid: Annotated[str, "The release GUID from search_releases results"],
    indexer_id: Annotated[int, "The indexer ID from search_releases results"],
    client: radarr.ApiClient = Depends(get_radarr_client),
) -> dict[str, Any]:
    """Download a specific release found via search_releases."""
    api = radarr.ReleaseApi(client)
    resource = radarr.ReleaseResource(guid=guid, indexer_id=indexer_id)
    result = await radarr_api_call(api.create_release, release_resource=resource)
    if result is None:
        return {"success": True, "message": "Release added to download queue."}
    return full_detail(result)
