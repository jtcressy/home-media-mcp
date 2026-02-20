"""Radarr movie management tools."""

from typing import Annotated, Any

import radarr
from fastmcp.dependencies import Depends

from home_media_mcp.server import mcp
from home_media_mcp.services.radarr.server import (
    get_radarr_client,
    radarr_api_call,
)
from home_media_mcp.utils import (
    full_detail,
    grep_filter,
    resolve_quality_profile,
    resolve_root_folder,
    summarize_list,
)


@mcp.tool(
    tags={"read"},
    annotations={"readOnlyHint": True},
)
async def radarr_list_movies(
    grep: Annotated[str | None, "Regex pattern to filter results"] = None,
    client: radarr.ApiClient = Depends(get_radarr_client),
) -> dict[str, Any]:
    """List all movies in Radarr with summary information.

    Returns a summary of each movie (compact fields like id, title, year,
    status, monitored). Use describe_movie with an ID for full details.
    Use the grep parameter to filter by regex across all fields.
    """
    api = radarr.MovieApi(client)
    all_movies = await radarr_api_call(api.list_movie)
    filtered = grep_filter(all_movies, grep)
    return summarize_list(filtered, summary_fn=_radarr_movie_summary)


@mcp.tool(
    tags={"read"},
    annotations={"readOnlyHint": True},
)
async def radarr_describe_movie(
    id: Annotated[int, "The Radarr movie ID"],
    client: radarr.ApiClient = Depends(get_radarr_client),
) -> dict[str, Any]:
    """Get full details for a specific movie by ID.

    Returns the complete API response including all nested data like
    ratings, collection, images, file info, and more.
    """
    api = radarr.MovieApi(client)
    try:
        result = await radarr_api_call(api.get_movie_by_id, id=id)
    except radarr.exceptions.NotFoundException:
        return {"error": "not_found", "message": f"Movie with ID {id} not found."}
    return full_detail(result)


@mcp.tool(
    tags={"read"},
    annotations={"readOnlyHint": True},
)
async def radarr_lookup_movie(
    term: Annotated[str | None, "Search term (title)"] = None,
    tmdb_id: Annotated[int | None, "TMDB ID to look up"] = None,
    imdb_id: Annotated[str | None, "IMDB ID to look up (e.g., tt1234567)"] = None,
    client: radarr.ApiClient = Depends(get_radarr_client),
) -> dict[str, Any]:
    """Search for movies to add to Radarr.

    Provide exactly one of: term (title search), tmdb_id, or imdb_id.
    Returns matching movies from TMDB. Use the tmdbId from results
    when calling add_movie.
    """
    if sum(x is not None for x in (term, tmdb_id, imdb_id)) != 1:
        return {
            "error": "invalid_params",
            "message": "Provide exactly one of: term, tmdb_id, or imdb_id.",
        }

    api = radarr.MovieLookupApi(client)
    if term is not None:
        results = await radarr_api_call(api.list_movie_lookup, term=term)
    elif tmdb_id is not None:
        results = await radarr_api_call(api.list_movie_lookup_tmdb, tmdb_id=tmdb_id)
    else:
        results = await radarr_api_call(api.list_movie_lookup_imdb, imdb_id=imdb_id)

    return summarize_list(results, preserve_fields=["title", "tmdbId"])


@mcp.tool(
    tags={"write"},
    annotations={"destructiveHint": False, "readOnlyHint": False},
)
async def radarr_add_movie(
    tmdb_id: Annotated[int, "TMDB ID of the movie to add (from lookup_movie)"],
    quality_profile: Annotated[str | int, "Quality profile name or ID"],
    root_folder: Annotated[
        str | int,
        "Root folder path or ID where the movie will be stored",
    ],
    monitored: Annotated[bool, "Whether to monitor the movie"] = True,
    search_for_movie: Annotated[
        bool, "Whether to search for the movie after adding"
    ] = True,
    minimum_availability: Annotated[
        str,
        "When to consider the movie available: 'announced', 'inCinemas', 'released', 'preDB'",
    ] = "released",
    client: radarr.ApiClient = Depends(get_radarr_client),
) -> dict[str, Any]:
    """Add a new movie to Radarr.

    First use lookup_movie to find the TMDB ID. Use list_quality_profiles
    and list_root_folders to see available options.
    Accepts either names or numeric IDs for quality_profile and root_folder.
    """
    api = radarr.MovieApi(client)

    # Resolve human-friendly names to IDs
    qp_api = radarr.QualityProfileApi(client)
    profiles = await radarr_api_call(qp_api.list_quality_profile)
    quality_profile_id = resolve_quality_profile(quality_profile, profiles)

    rf_api = radarr.RootFolderApi(client)
    folders = await radarr_api_call(rf_api.list_root_folder)
    root_folder_id = resolve_root_folder(root_folder, folders)
    root_folder_path = next(f.path for f in folders if f.id == root_folder_id)

    # Lookup movie info from TMDB
    # Note: list_movie_lookup_tmdb returns a single MovieResource, not a list,
    # which causes deserialization errors. Use list_movie_lookup with tmdb: prefix.
    lookup_api = radarr.MovieLookupApi(client)
    lookup_results = await radarr_api_call(
        lookup_api.list_movie_lookup, term=f"tmdb:{tmdb_id}"
    )
    if not lookup_results:
        return {
            "error": "not_found",
            "message": f"No movie found with TMDB ID {tmdb_id}.",
        }

    movie_data = lookup_results[0]
    movie_data.quality_profile_id = quality_profile_id
    movie_data.root_folder_path = root_folder_path
    movie_data.monitored = monitored
    movie_data.minimum_availability = minimum_availability
    movie_data.add_options = radarr.AddMovieOptions(
        search_for_movie=search_for_movie,
    )

    result = await radarr_api_call(api.create_movie, movie_resource=movie_data)
    return full_detail(result)


@mcp.tool(
    tags={"write"},
    annotations={"destructiveHint": False, "readOnlyHint": False},
)
async def radarr_update_movie(
    id: Annotated[int, "The Radarr movie ID to update"],
    monitored: Annotated[bool | None, "Set monitored status"] = None,
    quality_profile: Annotated[
        str | int | None, "New quality profile name or ID"
    ] = None,
    minimum_availability: Annotated[
        str | None,
        "When to consider available: 'announced', 'inCinemas', 'released', 'preDB'",
    ] = None,
    path: Annotated[str | None, "New file path for the movie"] = None,
    tags: Annotated[list[str | int] | None, "Set tags (names or IDs)"] = None,
    client: radarr.ApiClient = Depends(get_radarr_client),
) -> dict[str, Any]:
    """Update an existing movie in Radarr.

    Only provided fields are changed. Use describe_movie first to see
    current values.
    """
    api = radarr.MovieApi(client)

    try:
        movie = await radarr_api_call(api.get_movie_by_id, id=id)
    except radarr.exceptions.NotFoundException:
        return {"error": "not_found", "message": f"Movie with ID {id} not found."}

    if monitored is not None:
        movie.monitored = monitored
    if quality_profile is not None:
        qp_api = radarr.QualityProfileApi(client)
        profiles = await radarr_api_call(qp_api.list_quality_profile)
        movie.quality_profile_id = resolve_quality_profile(quality_profile, profiles)
    if minimum_availability is not None:
        movie.minimum_availability = minimum_availability
    if path is not None:
        movie.path = path
    if tags is not None:
        from home_media_mcp.utils import resolve_tag

        tag_api = radarr.TagApi(client)
        all_tags = await radarr_api_call(tag_api.list_tag)
        movie.tags = [resolve_tag(t, all_tags) for t in tags]

    result = await radarr_api_call(api.update_movie, id=str(id), movie_resource=movie)
    return full_detail(result)


@mcp.tool(
    tags={"write"},
    annotations={"destructiveHint": True, "readOnlyHint": False},
)
async def radarr_delete_movie(
    id: Annotated[int, "The Radarr movie ID to delete"],
    delete_files: Annotated[bool, "Also delete the movie files from disk"] = False,
    add_import_exclusion: Annotated[
        bool, "Add to import exclusion list to prevent re-adding"
    ] = False,
    client: radarr.ApiClient = Depends(get_radarr_client),
) -> dict[str, Any]:
    """Delete a movie from Radarr.

    This removes the movie from Radarr's database. If delete_files is True,
    the actual media files will also be removed from disk. This action cannot
    be undone.
    """
    api = radarr.MovieApi(client)
    try:
        await radarr_api_call(
            api.delete_movie,
            id=id,
            delete_files=delete_files,
            add_import_exclusion=add_import_exclusion,
        )
    except radarr.exceptions.NotFoundException:
        return {"error": "not_found", "message": f"Movie with ID {id} not found."}
    return {
        "success": True,
        "message": f"Movie {id} deleted"
        + (" (files also deleted)" if delete_files else " (files preserved)")
        + (" (added to import exclusion)" if add_import_exclusion else ""),
    }


def _radarr_movie_summary(items: list) -> dict[str, Any]:
    """Generate aggregate stats for movie list summary."""
    monitored = sum(1 for m in items if getattr(m, "monitored", False))
    has_file = sum(1 for m in items if getattr(m, "has_file", False))
    return {
        "monitored": monitored,
        "unmonitored": len(items) - monitored,
        "downloaded": has_file,
        "missing": len(items) - has_file,
    }
