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
        "seriesId, episodeIds, path, quality, languages. "
        "Optional: downloadId, folderName, releaseGroup, indexerFlags, releaseType.",
    ],
    import_mode: Annotated[
        str,
        "Import mode: 'move' (move file), 'copy' (hardlink/copy), or 'auto' "
        "(let Sonarr decide based on download client settings). Default: 'auto'.",
    ] = "auto",
    client: sonarr.ApiClient = Depends(get_sonarr_client),
) -> dict[str, Any]:
    """Execute a manual import for the specified files.

    Triggers the actual file import via Sonarr's ManualImport command.
    This moves/copies the file into the series folder and registers it
    in Sonarr's database.

    REQUIRED FIELDS for each file dict:
    - seriesId: The Sonarr series ID to import into
    - episodeIds: Array of episode IDs this file contains
    - path: Full path to the file
    - quality: Quality object with nested 'quality' (from preview)
    - languages: Array of language objects (from preview)

    OPTIONAL FIELDS:
    - downloadId: The SABnzbd/NZBGet download ID (strongly recommended when
      importing from a completed download - lets Sonarr mark it as imported)
    - folderName: Folder name hint for scene release parsing
    - releaseGroup: Release group name
    - indexerFlags: Indexer flags integer (default 0)
    - releaseType: 'singleEpisode', 'multiEpisode', etc. (default 'unknown')

    EXAMPLE file dict:
    {
        \"seriesId\": 42,
        \"episodeIds\": [101, 102],
        \"path\": \"/downloads/complete/Series.2024/Series.S01E01-02.mkv\",
        \"quality\": {\"quality\": {\"id\": 6, \"name\": \"HDTV-1080p\"}},
        \"languages\": [{\"id\": 1, \"name\": \"English\"}],
        \"downloadId\": \"SABnzbd_nzo_xxx\"
    }

    Always call preview_manual_import first to get the path and quality details.
    """
    # Fields accepted by Sonarr's ManualImportFile (camelCase, matches JSON API)
    valid_file_fields = {
        "path",
        "folderName",
        "seriesId",
        "episodeIds",
        "episodeFileId",
        "quality",
        "languages",
        "releaseGroup",
        "indexerFlags",
        "releaseType",
        "downloadId",
    }
    clean_files = []
    for f in files:
        clean_files.append({k: v for k, v in f.items() if k in valid_file_fields})

    # POST to /api/v3/command with name="ManualImport" as a plain dict.
    # We bypass CommandResource (which doesn't have 'files'/'importMode' fields)
    # and use the client's param_serialize/call_api infrastructure directly so
    # that the plain dict body is passed through sanitize_for_serialization as-is.
    body = {
        "name": "ManualImport",
        "importMode": import_mode,
        "files": clean_files,
    }

    def _post_command():
        _param = client.param_serialize(
            method="POST",
            resource_path="/api/v3/command",
            header_params={
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            body=body,
            auth_settings=["apikey", "X-Api-Key"],
        )
        response_data = client.call_api(*_param)
        response_data.read()
        return client.response_deserialize(
            response_data=response_data,
            response_types_map={"2XX": "CommandResource"},
        ).data

    result = await sonarr_api_call(_post_command)
    return {
        "success": True,
        "message": f"ManualImport command queued for {len(files)} file(s).",
        "commandId": result.id if result else None,
        "status": result.status if result else None,
    }
