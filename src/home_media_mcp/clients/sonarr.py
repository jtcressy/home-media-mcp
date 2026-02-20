"""Sonarr API client factory."""

from __future__ import annotations

import logging

import sonarr

from home_media_mcp.config import ServiceConfig

logger = logging.getLogger(__name__)


def create_sonarr_client(config: ServiceConfig) -> sonarr.ApiClient:
    """Create a configured Sonarr API client.

    Args:
        config: Service connection configuration.

    Returns:
        A configured sonarr.ApiClient instance. The caller is responsible
        for closing it (use as context manager or call .close()).
    """
    configuration = sonarr.Configuration(
        host=config.url,
        api_key={"X-Api-Key": config.api_key},
    )
    return sonarr.ApiClient(configuration)


def health_check(client: sonarr.ApiClient) -> bool:
    """Check connectivity to Sonarr.

    Args:
        client: A configured Sonarr API client.

    Returns:
        True if Sonarr is reachable and responding, False otherwise.
    """
    try:
        api = sonarr.SystemApi(client)
        status = api.get_system_status()
        logger.info("Sonarr connected: version %s", status.version)
        return True
    except sonarr.ApiException as e:
        logger.error("Sonarr health check failed: %s %s", e.status, e.reason)
        return False
    except Exception as e:
        logger.error("Sonarr health check failed: %s", e)
        return False
