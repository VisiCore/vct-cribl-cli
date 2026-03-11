"""Tests for OAuth2 token management (cloud and local auth)."""

from __future__ import annotations

import time
from unittest.mock import MagicMock

import httpx
import pytest

from cribl_cli.auth.oauth import clear_token_cache, get_access_token
from cribl_cli.config.types import CriblConfig


@pytest.fixture(autouse=True)
def _clear_cache():
    """Clear the token cache before each test."""
    clear_token_cache()
    yield
    clear_token_cache()


def _cloud_config() -> CriblConfig:
    return CriblConfig(
        profile="test",
        base_url="https://myorg.cribl.cloud",
        auth_type="cloud",
        client_id="test-cid",
        client_secret="test-csec",
    )


def _local_config() -> CriblConfig:
    return CriblConfig(
        profile="test",
        base_url="https://localhost:9000",
        auth_type="local",
        username="admin",
        password="secret",
    )


def _mock_token_response(token: str, expires_in: int = 3600, local: bool = False):
    """Build a mock httpx.Response for token endpoints."""
    resp = MagicMock(spec=httpx.Response)
    resp.raise_for_status.return_value = None
    if local:
        resp.json.return_value = {"token": token, "expiresIn": expires_in}
    else:
        resp.json.return_value = {"access_token": token, "expires_in": expires_in}
    return resp


# ---------------------------------------------------------------------------
# Cloud auth
# ---------------------------------------------------------------------------


def test_get_cloud_token(mocker):
    """Cloud auth posts to login.cribl.cloud and returns the access_token."""
    mock_post = mocker.patch("httpx.post", return_value=_mock_token_response("cloud-tok-123"))

    token = get_access_token(_cloud_config())

    assert token == "cloud-tok-123"
    mock_post.assert_called_once()
    call_kwargs = mock_post.call_args
    assert "login.cribl.cloud" in call_kwargs[0][0]
    assert call_kwargs[1]["json"]["audience"] == "https://api.cribl.cloud"
    assert call_kwargs[1]["json"]["grant_type"] == "client_credentials"


# ---------------------------------------------------------------------------
# Local auth
# ---------------------------------------------------------------------------


def test_get_local_token(mocker):
    """Local auth posts to {base_url}/api/v1/auth/login and returns the token."""
    mock_post = mocker.patch(
        "httpx.post",
        return_value=_mock_token_response("local-tok-456", local=True),
    )
    config = _local_config()

    token = get_access_token(config)

    assert token == "local-tok-456"
    mock_post.assert_called_once()
    call_url = mock_post.call_args[0][0]
    assert call_url == f"{config.base_url}/api/v1/auth/login"
    assert mock_post.call_args[1]["json"]["username"] == "admin"


# ---------------------------------------------------------------------------
# Caching
# ---------------------------------------------------------------------------


def test_token_caching(mocker):
    """Calling get_access_token twice uses the cached token (one HTTP call)."""
    mock_post = mocker.patch("httpx.post", return_value=_mock_token_response("cached-tok"))

    token1 = get_access_token(_cloud_config())
    token2 = get_access_token(_cloud_config())

    assert token1 == "cached-tok"
    assert token2 == "cached-tok"
    mock_post.assert_called_once()


def test_token_refresh_when_expired(mocker):
    """An expired token triggers a fresh HTTP call."""
    mock_post = mocker.patch("httpx.post")

    # First call: token that "expires" immediately (expires_in=0)
    mock_post.return_value = _mock_token_response("old-tok", expires_in=0)
    token1 = get_access_token(_cloud_config())
    assert token1 == "old-tok"

    # Manually expire the cache by patching time
    mocker.patch("cribl_cli.auth.oauth.time") \
        .time.return_value = time.time() + 99999

    mock_post.return_value = _mock_token_response("new-tok", expires_in=3600)
    token2 = get_access_token(_cloud_config())
    assert token2 == "new-tok"

    assert mock_post.call_count == 2
