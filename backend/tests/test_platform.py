"""Tests for backend.platform env var resolution and backward compatibility."""

import os
from unittest.mock import patch

import pytest

# Reset adapter state between tests
import backend.platform as platform_mod


@pytest.fixture(autouse=True)
def reset_adapter():
    """Reset the cached adapter between tests."""
    platform_mod._adapter = None
    platform_mod._adapter_loaded = False
    yield
    platform_mod._adapter = None
    platform_mod._adapter_loaded = False


# ── get_llm_base_url ───────────────────────────────────────────────────────


class TestGetLLMBaseUrl:
    """Test env var priority for LLM URL."""

    def test_nebulus_llm_url_takes_priority(self):
        with patch.dict(os.environ, {
            "NEBULUS_LLM_URL": "http://new:5000",
            "TABBY_HOST": "http://old:5000",
        }):
            assert platform_mod.get_llm_base_url() == "http://new:5000"

    def test_tabby_host_backward_compat(self):
        with patch.dict(os.environ, {"TABBY_HOST": "http://tabby:5000"}, clear=False):
            env = os.environ.copy()
            env.pop("NEBULUS_LLM_URL", None)
            with patch.dict(os.environ, env, clear=True):
                assert platform_mod.get_llm_base_url() == "http://tabby:5000"

    def test_default_when_no_env(self):
        with patch.dict(os.environ, {}, clear=True):
            assert platform_mod.get_llm_base_url() == "http://localhost:5000"


# ── get_chroma_settings ────────────────────────────────────────────────────


class TestGetChromaSettings:
    """Test env var priority for ChromaDB settings."""

    def test_nebulus_chroma_url_takes_priority(self):
        with patch.dict(os.environ, {
            "NEBULUS_CHROMA_URL": "http://new-chroma:9000",
            "CHROMA_HOST": "http://old-chroma:8000",
        }):
            settings = platform_mod.get_chroma_settings()
            assert settings["host"] == "new-chroma"
            assert settings["port"] == 9000

    def test_chroma_host_backward_compat(self):
        with patch.dict(os.environ, {"CHROMA_HOST": "http://chromadb:8000"}, clear=False):
            env = os.environ.copy()
            env.pop("NEBULUS_CHROMA_URL", None)
            with patch.dict(os.environ, env, clear=True):
                settings = platform_mod.get_chroma_settings()
                assert settings["host"] == "chromadb"
                assert settings["port"] == 8000

    def test_default_when_no_env(self):
        with patch.dict(os.environ, {}, clear=True):
            settings = platform_mod.get_chroma_settings()
            assert settings == {"mode": "http", "host": "localhost", "port": 8001}


# ── get_platform_name ──────────────────────────────────────────────────────


class TestGetPlatformName:
    """Test get_platform_name helper."""

    def test_returns_unknown_without_adapter(self):
        assert platform_mod.get_platform_name() == "unknown"


# ── get_service_manager_type ───────────────────────────────────────────────


class TestGetServiceManagerType:
    """Test get_service_manager_type helper."""

    def test_returns_docker_when_available(self):
        import docker as docker_mod
        with patch.object(docker_mod, "from_env", return_value=object()):
            assert platform_mod.get_service_manager_type() == "docker"

    def test_returns_none_without_docker_or_adapter(self):
        import docker as docker_mod
        with patch.object(docker_mod, "from_env", side_effect=Exception("no docker")):
            assert platform_mod.get_service_manager_type() == "none"


# ── get_mcp_settings ──────────────────────────────────────────────────────


class TestGetMCPSettings:
    """Test get_mcp_settings helper."""

    def test_returns_none_without_adapter(self):
        assert platform_mod.get_mcp_settings() is None
