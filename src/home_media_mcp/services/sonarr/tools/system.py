"""Sonarr system tools."""

from typing import Annotated, Any

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
    """Get Sonarr system status information."""
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
    """List Sonarr health check results."""
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
    """Get disk space information for Sonarr's configured paths."""
    api = sonarr.DiskSpaceApi(client)
    results = await sonarr_api_call(api.list_disk_space)
    return summarize_list(results)


@mcp.tool(
    tags={"read"},
    annotations={"readOnlyHint": True},
)
async def sonarr_list_logs(
    page: Annotated[int, "Page number"] = 1,
    page_size: Annotated[int, "Items per page"] = 50,
    level: Annotated[str | None, "Log level filter: info, warn, error, debug"] = None,
    grep: Annotated[str | None, "Regex pattern to filter log messages"] = None,
    client: sonarr.ApiClient = Depends(get_sonarr_client),
) -> dict[str, Any]:
    """Get Sonarr log entries."""
    api = sonarr.LogApi(client)
    kwargs: dict[str, Any] = {"page": page, "page_size": page_size}
    if level is not None:
        kwargs["level"] = level
    result = await sonarr_api_call(api.get_log, **kwargs)
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
