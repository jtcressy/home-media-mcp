"""Radarr service helpers and tool registration."""

import asyncio
from typing import Any

import radarr
from fastmcp import Context
from fastmcp.dependencies import CurrentContext, Depends

from home_media_mcp.server import mcp


def get_radarr_client(ctx: Context = CurrentContext()) -> radarr.ApiClient:
    """Dependency that provides the Radarr API client from lifespan context."""
    client = ctx.lifespan_context.get("radarr_client")
    if client is None:
        raise RuntimeError("Radarr client not available")
    return client


async def radarr_api_call(func, *args, **kwargs) -> Any:
    """Execute a synchronous radarr-py API call in a thread."""
    return await asyncio.to_thread(func, *args, **kwargs)


# Import tool modules to register tools on the shared mcp instance
from home_media_mcp.services.radarr.tools import (  # noqa: E402, F401
    alt_titles,
    blocklist,
    calendar,
    collections,
    commands,
    credits,
    exclusions,
    history,
    manual_import,
    movie_files,
    movies,
    queue,
    reference,
    rename,
    search,
    system,
    wanted,
)
