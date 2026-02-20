"""Radarr import exclusion tools."""

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
async def radarr_list_exclusions(
    grep: Annotated[str | None, "Regex pattern to filter results"] = None,
    client: radarr.ApiClient = Depends(get_radarr_client),
) -> dict[str, Any]:
    """List import exclusions (movies that won't be auto-imported).

    Import exclusions prevent movies from being added by import lists.
    """
    api = radarr.ImportExclusionsApi(client)
    results = await radarr_api_call(api.list_exclusions)
    filtered = grep_filter(results, grep)
    return summarize_list(filtered)


@mcp.tool(
    tags={"write"},
    annotations={"destructiveHint": False, "readOnlyHint": False},
)
async def radarr_add_exclusion(
    tmdb_id: Annotated[int, "TMDB ID of the movie to exclude"],
    movie_title: Annotated[str, "Title of the movie (for display)"],
    movie_year: Annotated[int, "Release year of the movie"],
    client: radarr.ApiClient = Depends(get_radarr_client),
) -> dict[str, Any]:
    """Add a movie to the import exclusion list.

    This prevents the movie from being added by import lists.
    """
    api = radarr.ImportExclusionsApi(client)
    resource = radarr.ImportExclusionsResource(
        tmdb_id=tmdb_id,
        movie_title=movie_title,
        movie_year=movie_year,
    )
    result = await radarr_api_call(
        api.create_exclusions, import_exclusions_resource=resource
    )
    return {
        "success": True,
        "message": f"Added exclusion for '{movie_title}' ({movie_year}).",
    }


@mcp.tool(
    tags={"write"},
    annotations={"destructiveHint": True, "readOnlyHint": False},
)
async def radarr_remove_exclusion(
    id: Annotated[int, "The exclusion ID to remove"],
    client: radarr.ApiClient = Depends(get_radarr_client),
) -> dict[str, Any]:
    """Remove a movie from the import exclusion list.

    This allows import lists to add the movie again.
    """
    api = radarr.ImportExclusionsApi(client)
    await radarr_api_call(api.delete_exclusions, id=id)
    return {"success": True, "message": f"Exclusion {id} removed."}
