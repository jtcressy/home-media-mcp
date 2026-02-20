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
    """
    api = sonarr.ManualImportApi(client)
    kwargs: dict[str, Any] = {"folder": folder}
    if series_id is not None:
        kwargs["series_id"] = series_id
    results = await sonarr_api_call(api.list_manual_import, **kwargs)
    filtered = grep_filter(results, grep)
    return summarize_list(filtered)


@mcp.tool(
    tags={"write"},
    annotations={"destructiveHint": False, "readOnlyHint": False},
)
async def sonarr_execute_manual_import(
    files: Annotated[
        list[dict],
        "List of import specifications from preview_manual_import. "
        "Each dict should contain: path, seriesId, episodeIds, quality, "
        "languages, and other fields from the preview.",
    ],
    client: sonarr.ApiClient = Depends(get_sonarr_client),
) -> dict[str, Any]:
    """Execute a manual import for the specified files.

    Use preview_manual_import first to see available files and their
    detected metadata. Pass the file specs (with corrections if needed)
    to this tool.
    """
    api = sonarr.ManualImportApi(client)
    resources = [sonarr.ManualImportReprocessResource(**f) for f in files]
    await sonarr_api_call(
        api.create_manual_import, manual_import_reprocess_resource=resources
    )
    return {
        "success": True,
        "message": f"Manual import started for {len(files)} file(s).",
    }
