"""Sonarr service helpers and tool registration."""

import asyncio
from typing import Any

import sonarr
from fastmcp import Context
from fastmcp.dependencies import CurrentContext, Depends

from home_media_mcp.server import mcp


def get_sonarr_client(ctx: Context = CurrentContext()) -> sonarr.ApiClient:
    """Dependency that provides the Sonarr API client from lifespan context."""
    client = ctx.lifespan_context.get("sonarr_client")
    if client is None:
        raise RuntimeError("Sonarr client not available")
    return client


async def sonarr_api_call(func, *args, **kwargs) -> Any:
    """Execute a synchronous sonarr-py API call in a thread."""
    return await asyncio.to_thread(func, *args, **kwargs)


async def sonarr_post_command(client: sonarr.ApiClient, body: dict) -> Any:
    """POST a plain-dict body to /api/v3/command, bypassing CommandResource."""

    def _call():
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

    return await sonarr_api_call(_call)


# Import tool modules to register tools on the shared mcp instance
from home_media_mcp.services.sonarr.tools import (  # noqa: E402, F401
    blocklist,
    calendar,
    commands,
    episode_files,
    episodes,
    history,
    manual_import,
    queue,
    reference,
    rename,
    search,
    series,
    system,
    wanted,
)
