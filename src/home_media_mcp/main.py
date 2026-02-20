"""Main entry point for the home-media-mcp server."""

from __future__ import annotations

import logging
import sys

from home_media_mcp.config import Config
from home_media_mcp.server import mcp

logger = logging.getLogger(__name__)


def _register_tools() -> None:
    """Import service modules to trigger tool registration on the shared server."""
    config = Config.from_env()

    if config.sonarr is not None:
        import home_media_mcp.services.sonarr  # noqa: F401

        logger.info("Sonarr tools registered.")

    if config.radarr is not None:
        import home_media_mcp.services.radarr  # noqa: F401

        logger.info("Radarr tools registered.")

    # Apply read-only mode
    if config.read_only:
        mcp.disable(tags={"write"})
        logger.info("Read-only mode enabled. Write tools are disabled.")


# Register tools at import time so they exist before the server starts
_register_tools()


def run() -> None:
    """Run the MCP server (entry point for 'home-media-mcp' command)."""
    config = Config.from_env()
    logging.basicConfig(
        level=getattr(logging, config.log_level, logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stderr,
    )
    mcp.run()


if __name__ == "__main__":
    run()
