"""Radarr API client factory."""

from __future__ import annotations

import logging

import radarr

from home_media_mcp.config import ServiceConfig

logger = logging.getLogger(__name__)


def create_radarr_client(config: ServiceConfig) -> radarr.ApiClient:
    """Create a configured Radarr API client.

    Args:
        config: Service connection configuration.

    Returns:
        A configured radarr.ApiClient instance. The caller is responsible
        for closing it (use as context manager or call .close()).
    """
    configuration = radarr.Configuration(
        host=config.url,
        api_key={"X-Api-Key": config.api_key},
    )
    return radarr.ApiClient(configuration)


def health_check(client: radarr.ApiClient) -> bool:
    """Check connectivity to Radarr.

    Args:
        client: A configured Radarr API client.

    Returns:
        True if Radarr is reachable and responding, False otherwise.
    """
    try:
        api = radarr.SystemApi(client)
        status = api.get_system_status()
        logger.info("Radarr connected: version %s", status.version)
        return True
    except radarr.ApiException as e:
        logger.error("Radarr health check failed: %s %s", e.status, e.reason)
        return False
    except Exception as e:
        logger.error("Radarr health check failed: %s", e)
        return False
