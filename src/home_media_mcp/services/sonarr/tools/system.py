"""Sonarr system tools."""

from typing import Any

import sonarr
from fastmcp.dependencies import Depends

from home_media_mcp.server import mcp
from home_media_mcp.services.sonarr.server import (
    get_sonarr_client,
    sonarr_api_call,
)
from home_media_mcp.utils import full_detail, summarize_list


@mcp.tool(
    tags={"read"},
    annotations={"readOnlyHint": True},
)
async def sonarr_get_system_status(
    client: sonarr.ApiClient = Depends(get_sonarr_client),
) -> dict[str, Any]:
    """Get Sonarr system status information.

    Returns version, OS, runtime, startup time, and other system details.
    """
    api = sonarr.SystemApi(client)
    result = await sonarr_api_call(api.get_system_status)
    return full_detail(result)


@mcp.tool(
    tags={"read"},
    annotations={"readOnlyHint": True},
)
async def sonarr_list_health_checks(
    client: sonarr.ApiClient = Depends(get_sonarr_client),
) -> dict[str, Any]:
    """List Sonarr health check results.

    Shows warnings and errors about configuration issues, indexer problems,
    download client status, etc.
    """
    api = sonarr.HealthApi(client)
    results = await sonarr_api_call(api.list_health)
    return summarize_list(results)


@mcp.tool(
    tags={"read"},
    annotations={"readOnlyHint": True},
)
async def sonarr_get_disk_space(
    client: sonarr.ApiClient = Depends(get_sonarr_client),
) -> dict[str, Any]:
    """Get disk space information for Sonarr's configured paths.

    Shows free space, total space, and path for each monitored location.
    """
    api = sonarr.DiskSpaceApi(client)
    results = await sonarr_api_call(api.list_disk_space)
    return summarize_list(results)
