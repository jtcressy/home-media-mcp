"""Shared FastMCP server instance with composed lifespans.

All service tool modules import `mcp` from here and register their
tools on it. This avoids circular imports with main.py.
"""

from __future__ import annotations

import asyncio
import logging

from fastmcp import FastMCP
from fastmcp.server.lifespan import lifespan

from home_media_mcp.config import Config

logger = logging.getLogger(__name__)


@lifespan
async def sonarr_lifespan(server: FastMCP):
    """Create and manage the Sonarr API client lifecycle."""
    from home_media_mcp.clients.sonarr import create_sonarr_client, health_check

    config = Config.from_env()

    if config.sonarr is None:
        logger.info("Sonarr not configured (set SONARR_URL and SONARR_API_KEY).")
        yield {}
        return

    logger.info("Connecting to Sonarr at %s...", config.sonarr.url)
    client = create_sonarr_client(config.sonarr)
    healthy = await asyncio.to_thread(health_check, client)

    if not healthy:
        logger.warning(
            "Sonarr at %s is not reachable. Sonarr tools will not work.",
            config.sonarr.url,
        )
        yield {}
        return

    logger.info("Sonarr connected successfully.")
    yield {"sonarr_client": client}
    logger.info("Sonarr client shut down.")


@lifespan
async def radarr_lifespan(server: FastMCP):
    """Create and manage the Radarr API client lifecycle."""
    from home_media_mcp.clients.radarr import create_radarr_client, health_check

    config = Config.from_env()

    if config.radarr is None:
        logger.info("Radarr not configured (set RADARR_URL and RADARR_API_KEY).")
        yield {}
        return

    logger.info("Connecting to Radarr at %s...", config.radarr.url)
    client = create_radarr_client(config.radarr)
    healthy = await asyncio.to_thread(health_check, client)

    if not healthy:
        logger.warning(
            "Radarr at %s is not reachable. Radarr tools will not work.",
            config.radarr.url,
        )
        yield {}
        return

    logger.info("Radarr connected successfully.")
    yield {"radarr_client": client}
    logger.info("Radarr client shut down.")


mcp = FastMCP(
    "home-media-mcp",
    instructions=(
        "This server provides tools for managing a home media library "
        "through Sonarr (TV shows) and Radarr (movies). Use list_* tools "
        "to browse content with optional grep filtering, and describe_* "
        "tools to get full details by ID. Write operations like add, "
        "update, and delete are available when not in read-only mode."
    ),
    lifespan=sonarr_lifespan | radarr_lifespan,
)
