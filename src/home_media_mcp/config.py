"""Configuration management for home-media-mcp."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ServiceConfig:
    """Connection configuration for a single service."""

    url: str
    api_key: str


@dataclass(frozen=True)
class Config:
    """Application configuration loaded from environment variables."""

    sonarr: ServiceConfig | None
    radarr: ServiceConfig | None
    read_only: bool
    log_level: str
    list_summary_max_fields: int

    @classmethod
    def from_env(cls) -> Config:
        """Load configuration from environment variables.

        Environment variables:
            SONARR_URL: Base URL for Sonarr (e.g., http://localhost:8989)
            SONARR_API_KEY: API key for Sonarr
            RADARR_URL: Base URL for Radarr (e.g., http://localhost:7878)
            RADARR_API_KEY: API key for Radarr
            MCP_READ_ONLY: Set to '1', 'true', or 'yes' to disable write tools
            MCP_LOG_LEVEL: Logging level (default: INFO)
            MCP_LIST_SUMMARY_MAX_FIELDS: Max scalar fields in list summaries (default: 10)
        """
        sonarr = _load_service_config("SONARR")
        radarr = _load_service_config("RADARR")

        read_only = os.environ.get("MCP_READ_ONLY", "").lower() in (
            "1",
            "true",
            "yes",
        )
        log_level = os.environ.get("MCP_LOG_LEVEL", "INFO").upper()
        list_summary_max_fields = int(
            os.environ.get("MCP_LIST_SUMMARY_MAX_FIELDS", "10")
        )

        return cls(
            sonarr=sonarr,
            radarr=radarr,
            read_only=read_only,
            log_level=log_level,
            list_summary_max_fields=list_summary_max_fields,
        )


def _load_service_config(prefix: str) -> ServiceConfig | None:
    """Load a service configuration from environment variables.

    Returns None if either URL or API key is missing.
    """
    url = os.environ.get(f"{prefix}_URL", "").strip()
    api_key = os.environ.get(f"{prefix}_API_KEY", "").strip()

    if not url or not api_key:
        if url or api_key:
            logger.warning(
                "%s partially configured (need both %s_URL and %s_API_KEY)",
                prefix,
                prefix,
                prefix,
            )
        return None

    # Normalize URL: strip trailing slash
    url = url.rstrip("/")

    return ServiceConfig(url=url, api_key=api_key)
