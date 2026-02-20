"""Radarr manual import tools."""

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
async def radarr_preview_manual_import(
    folder: Annotated[str, "Path to folder to scan for importable files"],
    movie_id: Annotated[int | None, "Optionally filter to a specific movie"] = None,
    grep: Annotated[str | None, "Regex pattern to filter results"] = None,
    client: radarr.ApiClient = Depends(get_radarr_client),
) -> dict[str, Any]:
    """Preview files available for manual import from a folder.

    Scans the folder and shows what Radarr detected: matched movie,
    quality, languages, and any rejection reasons.

    IMPORTANT WORKFLOW:
    1. Call this WITHOUT movie_id first to see detected files
    2. Each file in the response has an 'id' field - note this
    3. For execute_manual_import, you must add these required fields:
       - movieId: The Radarr movie ID (from describe_movie or list_movies)
       - quality: Object with 'quality' nested (e.g., {quality: {id: 15, name: "WEBRip-1080p"}})
       - languages: Array of language objects (e.g., [{id: 1, name: "English"}])
    4. Copy other fields from preview (id, path, relativePath, size, etc.)

    WARNING: Passing movie_id may fail with 500 if the movie's destination
    folder doesn't exist yet (new movies). Use WITHOUT movie_id for new downloads.
    """
    api = radarr.ManualImportApi(client)
    kwargs: dict[str, Any] = {"folder": folder}
    if movie_id is not None:
        kwargs["movie_id"] = movie_id
    results = await radarr_api_call(api.list_manual_import, **kwargs)
    filtered = grep_filter(results, grep)
    return summarize_list(filtered)


@mcp.tool(
    tags={"write"},
    annotations={"destructiveHint": False, "readOnlyHint": False},
)
async def radarr_execute_manual_import(
    files: Annotated[
        list[dict],
        "List of import specifications. Each dict MUST include: "
        "id (from preview), movieId, path, relativePath, quality, languages, "
        "size, and other fields from preview_manual_import.",
    ],
    client: radarr.ApiClient = Depends(get_radarr_client),
) -> dict[str, Any]:
    """Execute a manual import for the specified files.

    REQUIRED FIELDS for each file dict:
    - id: The file ID from preview_manual_import
    - movieId: The Radarr movie ID to import into
    - path: Full path to the file
    - relativePath: Filename relative to folder
    - quality: Quality object with nested 'quality' (see example)
    - languages: Array of language objects
    - size: File size in bytes

    EXAMPLE file dict:
    {
        "id": 123456,
        "movieId": 42,
        "path": "/downloads/complete/Movie.2024/Movie.2024.mkv",
        "relativePath": "Movie.2024.mkv",
        "quality": {"quality": {"id": 15, "name": "WEBRip-1080p"}},
        "languages": [{"id": 1, "name": "English"}],
        "size": 8788663531
    }

    Always call preview_manual_import first to get file details.
    """
    api = radarr.ManualImportApi(client)
    resources = [radarr.ManualImportReprocessResource(**f) for f in files]
    await radarr_api_call(
        api.create_manual_import, manual_import_reprocess_resource=resources
    )
    return {
        "success": True,
        "message": f"Manual import started for {len(files)} file(s).",
    }
