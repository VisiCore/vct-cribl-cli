"""Tests for the App Platform endpoint helpers and `apps` command registration."""

from __future__ import annotations

from unittest.mock import MagicMock

import httpx
import pytest
from click.testing import CliRunner

from cribl_cli.api.endpoints.apps import (
    install_app,
    invoke_endpoint,
    resolve_app_source,
    uninstall_app,
    upgrade_app,
)
from cribl_cli.cli import cli


def _mock_response(json_data, text=""):
    resp = MagicMock(spec=httpx.Response)
    resp.json.return_value = json_data
    resp.text = text
    resp.raise_for_status.return_value = None
    return resp


def _make_client():
    return MagicMock(spec=httpx.Client)


def test_apps_group_registered():
    runner = CliRunner()
    result = runner.invoke(cli, ["apps", "--help"])
    assert result.exit_code == 0
    for sub in ("install", "upgrade", "uninstall", "backend-status", "invoke", "check"):
        assert sub in result.output


def test_resolve_remote_sources_pass_through():
    client = _make_client()
    assert resolve_app_source(client, "https://example.com/app.tgz") == "https://example.com/app.tgz"
    assert resolve_app_source(client, "git+https://github.com/org/app.git") == "git+https://github.com/org/app.git"
    client.put.assert_not_called()


def test_resolve_local_archive_uploads_and_returns_source(tmp_path):
    pkg = tmp_path / "my-app-1.0.0.tgz"
    pkg.write_bytes(b"fake-archive")
    client = _make_client()
    client.put.return_value = _mock_response({"source": "staged/my-app-1.0.0.tgz"})

    src = resolve_app_source(client, str(pkg))

    assert src == "staged/my-app-1.0.0.tgz"
    client.put.assert_called_once()
    args, kwargs = client.put.call_args
    assert args[0] == "/api/v1/apps"
    assert kwargs["params"] == {"filename": "my-app-1.0.0.tgz"}
    assert kwargs["content"] == b"fake-archive"
    assert kwargs["headers"]["Content-Type"] == "application/octet-stream"


def test_resolve_missing_archive_raises():
    client = _make_client()
    with pytest.raises(FileNotFoundError):
        resolve_app_source(client, "/nowhere/app.tgz")


def test_resolve_unknown_source_raises():
    client = _make_client()
    with pytest.raises(ValueError):
        resolve_app_source(client, "not-a-package")


def test_install_posts_source_and_optional_fields(tmp_path):
    pkg = tmp_path / "app.tgz"
    pkg.write_bytes(b"x")
    client = _make_client()
    client.put.return_value = _mock_response({"source": "staged/app.tgz"})
    client.post.return_value = _mock_response({"items": [{"id": "my-app"}]})

    install_app(client, str(pkg), app_id="my-app", spec="1.2.3")

    client.post.assert_called_once()
    args, kwargs = client.post.call_args
    assert args[0] == "/api/v1/apps"
    assert kwargs["json"] == {"source": "staged/app.tgz", "id": "my-app", "spec": "1.2.3"}


def test_upgrade_patches_app_id():
    client = _make_client()
    client.patch.return_value = _mock_response({"items": [{"id": "my-app"}]})

    upgrade_app(client, "my-app", "https://example.com/app-2.tgz", minor=True)

    args, kwargs = client.patch.call_args
    assert args[0] == "/api/v1/apps/my-app"
    assert kwargs["json"] == {"source": "https://example.com/app-2.tgz", "minor": True}


def test_uninstall_deletes_app():
    client = _make_client()
    client.delete.return_value = _mock_response({"id": "my-app"})
    uninstall_app(client, "my-app")
    client.delete.assert_called_once_with("/api/v1/apps/my-app")


def test_invoke_endpoint_builds_app_scoped_url():
    client = _make_client()
    client.request.return_value = _mock_response({"ok": True}, text='{"ok": true}')

    invoke_endpoint(client, "my-app", "incidents", method="get", query={"irwinId": "abc"})

    client.request.assert_called_once_with(
        "GET", "/api/v1/a/my-app/endpoints/incidents", json=None, params={"irwinId": "abc"}
    )


def test_api_command_registered():
    runner = CliRunner()
    result = runner.invoke(cli, ["api", "--help"])
    assert result.exit_code == 0
    assert "--query" in result.output and "--data" in result.output
