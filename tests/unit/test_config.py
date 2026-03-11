"""Tests for config loading cascades: CLI > env > saved profiles."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from cribl_cli.config.loader import load_config, load_rc, save_rc
from cribl_cli.config.types import CriblRc, ProfileConfig


# ---------------------------------------------------------------------------
# load_rc
# ---------------------------------------------------------------------------


def test_load_rc_returns_default_when_file_missing(mocker):
    """When ~/.criblrc does not exist, load_rc returns empty CriblRc defaults."""
    mock_path = MagicMock(spec=Path)
    mock_path.read_text.side_effect = FileNotFoundError

    rc = load_rc(path=mock_path)

    assert rc.profiles == {}
    assert rc.active_profile == "default"


def test_load_rc_parses_valid_file(mocker):
    """A valid .criblrc JSON is correctly parsed into profiles."""
    rc_data = {
        "profiles": {
            "prod": {
                "baseUrl": "https://cribl.example.com",
                "authType": "cloud",
                "clientId": "cid123",
                "clientSecret": "csec456",
            },
            "local": {
                "baseUrl": "https://localhost:9000",
                "authType": "local",
                "username": "admin",
                "password": "secret",
            },
        },
        "activeProfile": "prod",
    }
    mock_path = MagicMock(spec=Path)
    mock_path.read_text.return_value = json.dumps(rc_data)

    rc = load_rc(path=mock_path)

    assert "prod" in rc.profiles
    assert "local" in rc.profiles
    assert rc.active_profile == "prod"
    assert rc.profiles["prod"].client_id == "cid123"
    assert rc.profiles["prod"].client_secret == "csec456"
    assert rc.profiles["local"].username == "admin"
    assert rc.profiles["local"].auth_type == "local"


# ---------------------------------------------------------------------------
# save_rc
# ---------------------------------------------------------------------------


def test_save_rc_writes_json(mocker):
    """save_rc writes JSON to the file and sets 0o600 permissions."""
    mock_path = MagicMock(spec=Path)

    rc = CriblRc(
        profiles={
            "default": ProfileConfig(
                base_url="https://cribl.example.com",
                auth_type="cloud",
                client_id="cid",
                client_secret="csec",
            )
        },
        active_profile="default",
    )

    save_rc(rc, path=mock_path)

    # Verify write_text was called with valid JSON
    written = mock_path.write_text.call_args[0][0]
    parsed = json.loads(written)
    assert parsed["activeProfile"] == "default"
    assert parsed["profiles"]["default"]["baseUrl"] == "https://cribl.example.com"
    assert parsed["profiles"]["default"]["clientId"] == "cid"
    assert parsed["profiles"]["default"]["clientSecret"] == "csec"

    # Verify chmod 0o600
    mock_path.chmod.assert_called_once_with(0o600)


# ---------------------------------------------------------------------------
# load_config — priority cascades
# ---------------------------------------------------------------------------


def test_load_config_cli_overrides_env(monkeypatch, mocker):
    """CLI arguments take priority over environment variables."""
    monkeypatch.setenv("CRIBL_BASE_URL", "https://env.example.com")
    monkeypatch.setenv("CRIBL_CLIENT_ID", "env_cid")
    monkeypatch.setenv("CRIBL_CLIENT_SECRET", "env_csec")

    # Stub load_rc so it doesn't read the real file
    mocker.patch(
        "cribl_cli.config.loader.load_rc",
        return_value=CriblRc(),
    )

    cfg = load_config(
        base_url="https://cli.example.com",
        client_id="cli_cid",
        client_secret="cli_csec",
    )

    assert cfg.base_url == "https://cli.example.com"
    assert cfg.client_id == "cli_cid"
    assert cfg.client_secret == "cli_csec"


def test_load_config_env_overrides_saved(monkeypatch, mocker):
    """Environment variables override saved profile values."""
    saved_profile = ProfileConfig(
        base_url="https://saved.example.com",
        auth_type="cloud",
        client_id="saved_cid",
        client_secret="saved_csec",
    )
    mocker.patch(
        "cribl_cli.config.loader.load_rc",
        return_value=CriblRc(profiles={"default": saved_profile}, active_profile="default"),
    )

    monkeypatch.setenv("CRIBL_BASE_URL", "https://env.example.com")
    monkeypatch.setenv("CRIBL_CLIENT_ID", "env_cid")
    monkeypatch.setenv("CRIBL_CLIENT_SECRET", "env_csec")

    cfg = load_config()

    assert cfg.base_url == "https://env.example.com"
    assert cfg.client_id == "env_cid"
    assert cfg.client_secret == "env_csec"


def test_load_config_auto_detects_cloud(monkeypatch, mocker):
    """When client_id and client_secret are provided, auth_type is 'cloud'."""
    mocker.patch(
        "cribl_cli.config.loader.load_rc",
        return_value=CriblRc(),
    )

    cfg = load_config(
        base_url="https://example.cribl.cloud",
        client_id="cid",
        client_secret="csec",
    )

    assert cfg.auth_type == "cloud"


def test_load_config_auto_detects_local(monkeypatch, mocker):
    """When only username and password are provided, auth_type is 'local'."""
    mocker.patch(
        "cribl_cli.config.loader.load_rc",
        return_value=CriblRc(),
    )

    cfg = load_config(
        base_url="https://localhost:9000",
        username="admin",
        password="pass",
    )

    assert cfg.auth_type == "local"


def test_load_config_raises_without_base_url(mocker):
    """ValueError is raised when no base URL is configured anywhere."""
    mocker.patch(
        "cribl_cli.config.loader.load_rc",
        return_value=CriblRc(),
    )

    with pytest.raises(ValueError, match="No base URL configured"):
        load_config()
