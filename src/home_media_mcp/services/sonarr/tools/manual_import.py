"""Sonarr manual import tools."""

from typing import Annotated, Any

import sonarr
from fastmcp.dependencies import Depends

from home_media_mcp.server import mcp
from home_media_mcp.services.sonarr.server import (
    get_sonarr_client,
    sonarr_api_call,
)
from home_media_mcp.utils import grep_filter, summarize_list


@mcp.tool(
    tags={"read"},
    annotations={"readOnlyHint": True},
)
async def sonarr_preview_manual_import(
    folder: Annotated[str, "Path to folder to scan for importable files"],
    series_id: Annotated[int | None, "Optionally filter to a specific series"] = None,
    grep: Annotated[str | None, "Regex pattern to filter results"] = None,
    client: sonarr.ApiClient = Depends(get_sonarr_client),
) -> dict[str, Any]:
    """Preview files available for manual import from a folder.

    Scans the folder and shows what Sonarr detected: matched series,
    episodes, quality, and any rejection reasons.

    IMPORTANT WORKFLOW:
    1. Call this WITHOUT series_id first to see detected files
    2. Each file in the response has an 'id' field - note this
    3. For execute_manual_import, copy ALL fields from preview and ADD:
       - seriesId: The Sonarr series ID
       - episodeIds: Array of episode IDs this file matches
    4. The path, quality, languages, and other fields come from preview

    WARNING: Passing series_id may fail with 500 if the series' destination
    folder doesn't exist yet. Use WITHOUT series_id for new downloads.
    """
    api = sonarr.ManualImportApi(client)
    kwargs: dict[str, Any] = {"folder": folder}
    if series_id is not None:
        kwargs["series_id"] = series_id
    results = await sonarr_api_call(api.list_manual_import, **kwargs)
    filtered = grep_filter(results, grep)
    return summarize_list(
        filtered,
        preserve_fields=[
            "id",
            "path",
            "relativePath",
            "folderName",
            "name",
            "size",
            "quality",
            "languages",
            "seriesId",
            "seasonNumber",
            "episodes",
            "episodeIds",
            "releaseGroup",
            "downloadId",
            "customFormats",
            "customFormatScore",
            "indexerFlags",
            "rejections",
        ],
    )


@mcp.tool(
    tags={"write"},
    annotations={"destructiveHint": False, "readOnlyHint": False},
)
async def sonarr_execute_manual_import(
    files: Annotated[
        list[dict],
        "List of import specifications. Each dict MUST include: "
        "id (from preview), seriesId, episodeIds, path, quality, languages. "
        "Optional: downloadId, customFormats, customFormatScore, indexerFlags, releaseGroup.",
    ],
    client: sonarr.ApiClient = Depends(get_sonarr_client),
) -> dict[str, Any]:
    """Execute a manual import for the specified files.

    REQUIRED FIELDS for each file dict:
    - id: The file ID from preview_manual_import
    - seriesId: The Sonarr series ID to import into
    - episodeIds: Array of episode IDs this file contains
    - path: Full path to the file
    - quality: Quality object with nested 'quality' (from preview)
    - languages: Array of language objects (from preview)

    OPTIONAL FIELDS (from preview):
    - downloadId: The download ID if importing from a completed download
    - customFormats: Array of custom format objects
    - customFormatScore: Custom format score
    - indexerFlags: Indexer flags
    - releaseGroup: Release group name

    EXAMPLE file dict:
    {
        \"id\": 123456,
        \"seriesId\": 42,
        \"episodeIds\": [101, 102],
        \"path\": \"/downloads/complete/Series.2024/Series.S01E01-02.mkv\",
        \"quality\": {\"quality\": {\"id\": 6, \"name\": \"HDTV-1080p\"}},
        \"languages\": [{\"id\": 1, \"name\": \"English\"}],
        \"downloadId\": \"SABnzbd_nzo_xxx\"
    }

    Always call preview_manual_import first to get file details.
    Copy the id and other relevant fields from the preview response.
    """
    api = sonarr.ManualImportApi(client)
    valid_fields = {
        "id",
        "path",
        "seriesId",
        "series_id",
        "episodeIds",
        "episode_ids",
        "quality",
        "languages",
        "releaseGroup",
        "release_group",
        "downloadId",
        "download_id",
        "customFormats",
        "custom_formats",
        "customFormatScore",
        "custom_format_score",
        "indexerFlags",
        "indexer_flags",
    }
    filtered_files = []
    for f in files:
        filtered = {k: v for k, v in f.items() if k in valid_fields}
        filtered_files.append(filtered)
    resources = [sonarr.ManualImportReprocessResource(**f) for f in filtered_files]
    await sonarr_api_call(
        api.create_manual_import, manual_import_reprocess_resource=resources
    )
    return {
        "success": True,
        "message": f"Manual import started for {len(files)} file(s).",
    }
