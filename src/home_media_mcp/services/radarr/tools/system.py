"""Radarr system tools."""

from typing import Any

import radarr
from fastmcp.dependencies import Depends

from home_media_mcp.server import mcp
from home_media_mcp.services.radarr.server import (
    get_radarr_client,
    radarr_api_call,
)
from home_media_mcp.utils import full_detail, summarize_list


@mcp.tool(
    tags={"read"},
    annotations={"readOnlyHint": True},
)
async def radarr_get_system_status(
    client: radarr.ApiClient = Depends(get_radarr_client),
) -> dict[str, Any]:
    """Get Radarr system status information."""
    api = radarr.SystemApi(client)
    result = await radarr_api_call(api.get_system_status)
    return full_detail(result)


@mcp.tool(
    tags={"read"},
    annotations={"readOnlyHint": True},
)
async def radarr_list_health_checks(
    client: radarr.ApiClient = Depends(get_radarr_client),
) -> dict[str, Any]:
    """List Radarr health check results."""
    api = radarr.HealthApi(client)
    results = await radarr_api_call(api.list_health)
    return summarize_list(results)


@mcp.tool(
    tags={"read"},
    annotations={"readOnlyHint": True},
)
async def radarr_get_disk_space(
    client: radarr.ApiClient = Depends(get_radarr_client),
) -> dict[str, Any]:
    """Get disk space information for Radarr's configured paths."""
    api = radarr.DiskSpaceApi(client)
    results = await radarr_api_call(api.list_disk_space)
    return summarize_list(results)
