"""Tests for configuration management."""

import os

import pytest

from home_media_mcp.config import Config, ServiceConfig, _load_service_config


class TestServiceConfig:
    def test_frozen(self):
        config = ServiceConfig(url="http://localhost", api_key="test")
        with pytest.raises(AttributeError):
            config.url = "other"


class TestLoadServiceConfig:
    def test_both_present(self, monkeypatch):
        monkeypatch.setenv("TEST_URL", "http://localhost:8989")
        monkeypatch.setenv("TEST_API_KEY", "abc123")
        result = _load_service_config("TEST")
        assert result is not None
        assert result.url == "http://localhost:8989"
        assert result.api_key == "abc123"

    def test_url_only_returns_none(self, monkeypatch):
        monkeypatch.setenv("TEST_URL", "http://localhost:8989")
        monkeypatch.delenv("TEST_API_KEY", raising=False)
        result = _load_service_config("TEST")
        assert result is None

    def test_api_key_only_returns_none(self, monkeypatch):
        monkeypatch.delenv("TEST_URL", raising=False)
        monkeypatch.setenv("TEST_API_KEY", "abc123")
        result = _load_service_config("TEST")
        assert result is None

    def test_neither_present_returns_none(self, monkeypatch):
        monkeypatch.delenv("TEST_URL", raising=False)
        monkeypatch.delenv("TEST_API_KEY", raising=False)
        result = _load_service_config("TEST")
        assert result is None

    def test_strips_whitespace(self, monkeypatch):
        monkeypatch.setenv("TEST_URL", "  http://localhost:8989  ")
        monkeypatch.setenv("TEST_API_KEY", "  abc123  ")
        result = _load_service_config("TEST")
        assert result.url == "http://localhost:8989"
        assert result.api_key == "abc123"

    def test_strips_trailing_slash(self, monkeypatch):
        monkeypatch.setenv("TEST_URL", "http://localhost:8989/")
        monkeypatch.setenv("TEST_API_KEY", "abc123")
        result = _load_service_config("TEST")
        assert result.url == "http://localhost:8989"

    def test_empty_string_treated_as_missing(self, monkeypatch):
        monkeypatch.setenv("TEST_URL", "")
        monkeypatch.setenv("TEST_API_KEY", "abc123")
        result = _load_service_config("TEST")
        assert result is None


class TestConfig:
    def test_from_env_defaults(self, monkeypatch):
        # Clear all relevant env vars
        for key in [
            "SONARR_URL",
            "SONARR_API_KEY",
            "RADARR_URL",
            "RADARR_API_KEY",
            "MCP_READ_ONLY",
            "MCP_LOG_LEVEL",
            "MCP_LIST_SUMMARY_MAX_FIELDS",
        ]:
            monkeypatch.delenv(key, raising=False)

        config = Config.from_env()
        assert config.sonarr is None
        assert config.radarr is None
        assert config.read_only is False
        assert config.log_level == "INFO"
        assert config.list_summary_max_fields == 10

    def test_from_env_full(self, monkeypatch):
        monkeypatch.setenv("SONARR_URL", "http://sonarr:8989")
        monkeypatch.setenv("SONARR_API_KEY", "sonarr_key")
        monkeypatch.setenv("RADARR_URL", "http://radarr:7878")
        monkeypatch.setenv("RADARR_API_KEY", "radarr_key")
        monkeypatch.setenv("MCP_READ_ONLY", "true")
        monkeypatch.setenv("MCP_LOG_LEVEL", "DEBUG")
        monkeypatch.setenv("MCP_LIST_SUMMARY_MAX_FIELDS", "5")

        config = Config.from_env()
        assert config.sonarr.url == "http://sonarr:8989"
        assert config.sonarr.api_key == "sonarr_key"
        assert config.radarr.url == "http://radarr:7878"
        assert config.radarr.api_key == "radarr_key"
        assert config.read_only is True
        assert config.log_level == "DEBUG"
        assert config.list_summary_max_fields == 5

    def test_read_only_variations(self, monkeypatch):
        for val in ("1", "true", "yes", "TRUE", "Yes"):
            monkeypatch.setenv("MCP_READ_ONLY", val)
            for key in ["SONARR_URL", "SONARR_API_KEY", "RADARR_URL", "RADARR_API_KEY"]:
                monkeypatch.delenv(key, raising=False)
            config = Config.from_env()
            assert config.read_only is True, f"Failed for '{val}'"

        for val in ("0", "false", "no", ""):
            monkeypatch.setenv("MCP_READ_ONLY", val)
            config = Config.from_env()
            assert config.read_only is False, f"Failed for '{val}'"
