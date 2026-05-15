"""Tests for the shared ``ProviderConfig`` dataclass."""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from meta_data_mcp.provider_config import ProviderConfig


def test_defaults_are_sane():
    """Unset optional fields should default to safe, documented values."""
    cfg = ProviderConfig(base_url="https://example.test/api")

    assert cfg.base_url == "https://example.test/api"
    assert cfg.auth_env_var is None
    assert cfg.contact_required is False
    assert cfg.default_accept == "application/json"
    assert cfg.rate_limit_per_minute is None


def test_auth_headers_empty_when_no_env_var_configured():
    """No ``auth_env_var`` means ``auth_headers()`` must return ``{}``."""
    cfg = ProviderConfig(base_url="https://example.test/api")
    assert cfg.auth_headers() == {}


def test_auth_headers_empty_when_env_var_unset(monkeypatch):
    """If the configured env var is not set, return ``{}``."""
    monkeypatch.delenv("MY_PROVIDER_TOKEN", raising=False)
    cfg = ProviderConfig(
        base_url="https://example.test/api", auth_env_var="MY_PROVIDER_TOKEN"
    )
    assert cfg.auth_headers() == {}


def test_auth_headers_present_when_env_var_set(monkeypatch):
    """When the env var is set, return a ``Token``-style Authorization header."""
    monkeypatch.setenv("MY_PROVIDER_TOKEN", "secret-xyz")
    cfg = ProviderConfig(
        base_url="https://example.test/api", auth_env_var="MY_PROVIDER_TOKEN"
    )
    assert cfg.auth_headers() == {"Authorization": "Token secret-xyz"}


def test_dataclass_is_frozen():
    """``ProviderConfig`` is immutable; reassignment must raise."""
    cfg = ProviderConfig(base_url="https://example.test/api")
    with pytest.raises(FrozenInstanceError):
        cfg.base_url = "https://other.test/api"  # type: ignore[misc]
