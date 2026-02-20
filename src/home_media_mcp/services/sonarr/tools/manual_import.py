"""Sonarr manual import tools."""

from typing import Annotated, Any

from pydantic import Field

import sonarr
from fastmcp.dependencies import Depends

from home_media_mcp.server import mcp
from home_media_mcp.services.sonarr.server import (
    get_sonarr_client,
    sonarr_api_call,
    sonarr_post_command,
)
from home_media_mcp.utils import grep_filter, summarize_list


@mcp.tool(
    tags={"read"},
    annotations={"readOnlyHint": True},
)
async def sonarr_preview_manual_import(
    folder: Annotated[str, "Path to folder to scan for importable files"],
    series_id: Annotated[
        int | None,
        Field(
            description="Optionally filter to a specific series. WARNING: may return 500 if the series folder doesn't exist yet. Omit for new downloads."
        ),
    ] = None,
    grep: Annotated[str | None, "Regex pattern to filter results"] = None,
    client: sonarr.ApiClient = Depends(get_sonarr_client),
) -> dict[str, Any]:
    """Scan a folder and preview what Sonarr would import."""
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
        Field(
            description="List of file dicts. Each requires: seriesId (int), episodeIds (list[int]), path (str), quality (object from preview), languages (list from preview). Optional: downloadId, folderName, releaseGroup, indexerFlags, releaseType."
        ),
    ],
    import_mode: Annotated[
        str,
        "Import mode: 'move' (move file), 'copy' (hardlink/copy), or 'auto' "
        "(let Sonarr decide based on download client settings). Default: 'auto'.",
    ] = "auto",
    client: sonarr.ApiClient = Depends(get_sonarr_client),
) -> dict[str, Any]:
    """Execute a manual import for files prepared via preview_manual_import."""
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

    result = await sonarr_post_command(client, body)
    return {
        "success": True,
        "message": f"ManualImport command queued for {len(files)} file(s).",
        "commandId": result.id if result else None,
        "status": result.status if result else None,
    }
