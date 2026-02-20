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

    Scans the folder and shows what Radarr detected.
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
        "List of import specifications from preview_manual_import.",
    ],
    client: radarr.ApiClient = Depends(get_radarr_client),
) -> dict[str, Any]:
    """Execute a manual import for the specified files.

    Use preview_manual_import first to see available files.
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
