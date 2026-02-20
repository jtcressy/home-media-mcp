"""Radarr system tools."""

from typing import Annotated, Any

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


@mcp.tool(
    tags={"read"},
    annotations={"readOnlyHint": True},
)
async def radarr_list_logs(
    page: Annotated[int, "Page number"] = 1,
    page_size: Annotated[int, "Items per page"] = 50,
    level: Annotated[str | None, "Log level filter: info, warn, error, debug"] = None,
    grep: Annotated[str | None, "Regex pattern to filter log messages"] = None,
    client: radarr.ApiClient = Depends(get_radarr_client),
) -> dict[str, Any]:
    """Get Radarr log entries."""
    api = radarr.LogApi(client)
    kwargs: dict[str, Any] = {"page": page, "page_size": page_size}
    if level is not None:
        kwargs["level"] = level
    result = await radarr_api_call(api.get_log, **kwargs)
    if hasattr(result, "records"):
        records = result.records
    elif isinstance(result, list):
        records = result
    else:
        records = []
    if grep:
        import re

        pattern = re.compile(grep, re.IGNORECASE)
        records = [r for r in records if pattern.search(str(r.to_dict()))]
    return summarize_list(
        records,
        preserve_fields=["id", "time", "level", "logger", "message", "exception"],
    )
