"""Tests for the saved-searches factory-generated CRUD command."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx
from click.testing import CliRunner

from cribl_cli.cli import cli


def _mock_response(json_data, status_code=200):
    resp = MagicMock(spec=httpx.Response)
    resp.json.return_value = json_data
    resp.status_code = status_code
    resp.raise_for_status.return_value = None
    return resp


@patch("cribl_cli.commands.command_factory.get_client")
def test_saved_searches_list(mock_get_client):
    """saved-searches list calls GET on the search/saved endpoint."""
    client = MagicMock(spec=httpx.Client)
    mock_get_client.return_value = client
    client.get.return_value = _mock_response({
        "items": [{"id": "my_search", "name": "My Search"}],
        "count": 1,
    })

    runner = CliRunner()
    result = runner.invoke(cli, ["saved-searches", "list"])

    assert result.exit_code == 0
    assert "my_search" in result.output
    client.get.assert_called_once()
    url = client.get.call_args[0][0]
    assert url == "/api/v1/m/default_search/search/saved"


@patch("cribl_cli.commands.command_factory.get_client")
def test_saved_searches_get(mock_get_client):
    """saved-searches get retrieves a single saved search by ID."""
    client = MagicMock(spec=httpx.Client)
    mock_get_client.return_value = client
    client.get.return_value = _mock_response({
        "items": [{"id": "my_search", "name": "My Search", "query": "dataset=test"}],
    })

    runner = CliRunner()
    result = runner.invoke(cli, ["saved-searches", "get", "my_search"])

    assert result.exit_code == 0
    assert "my_search" in result.output
    url = client.get.call_args[0][0]
    assert url == "/api/v1/m/default_search/search/saved/my_search"


@patch("cribl_cli.commands.command_factory.get_client")
def test_saved_searches_create(mock_get_client):
    """saved-searches create POSTs a new saved search."""
    client = MagicMock(spec=httpx.Client)
    mock_get_client.return_value = client
    client.post.return_value = _mock_response({
        "items": [{"id": "new_search", "name": "New Search"}],
    })

    runner = CliRunner()
    body = '{"id": "new_search", "name": "New Search", "query": "dataset=test"}'
    result = runner.invoke(cli, ["saved-searches", "create", body])

    assert result.exit_code == 0
    client.post.assert_called_once()
    url = client.post.call_args[0][0]
    assert url == "/api/v1/m/default_search/search/saved"


@patch("cribl_cli.commands.command_factory.get_client")
def test_saved_searches_update(mock_get_client):
    """saved-searches update does merge-on-update (GET then PATCH)."""
    client = MagicMock(spec=httpx.Client)
    mock_get_client.return_value = client

    existing = {
        "items": [{
            "id": "my_search",
            "name": "My Search",
            "query": "dataset=test",
            "schedule": {"cronSchedule": "0 * * * *", "enabled": True},
        }],
    }
    updated = {
        "items": [{
            "id": "my_search",
            "name": "My Search",
            "query": "dataset=test",
            "schedule": {"cronSchedule": "*/5 * * * *", "enabled": True},
        }],
    }
    client.get.return_value = _mock_response(existing)
    client.patch.return_value = _mock_response(updated)

    runner = CliRunner()
    result = runner.invoke(cli, [
        "saved-searches", "update", "my_search",
        '{"schedule": {"cronSchedule": "*/5 * * * *", "enabled": true}}',
    ])

    assert result.exit_code == 0
    client.get.assert_called_once()
    client.patch.assert_called_once()
    patch_url = client.patch.call_args[0][0]
    assert patch_url == "/api/v1/m/default_search/search/saved/my_search"
    # Verify merge happened — merged body should contain original fields + update
    merged = client.patch.call_args[1]["json"]
    assert merged["name"] == "My Search"
    assert merged["schedule"]["cronSchedule"] == "*/5 * * * *"


@patch("cribl_cli.commands.command_factory.get_client")
def test_saved_searches_delete(mock_get_client):
    """saved-searches delete sends DELETE to the correct URL."""
    client = MagicMock(spec=httpx.Client)
    mock_get_client.return_value = client
    client.delete.return_value = _mock_response({"items": []})

    runner = CliRunner()
    result = runner.invoke(cli, ["saved-searches", "delete", "my_search"])

    assert result.exit_code == 0
    client.delete.assert_called_once()
    url = client.delete.call_args[0][0]
    assert url == "/api/v1/m/default_search/search/saved/my_search"


@patch("cribl_cli.commands.command_factory.get_client")
def test_saved_searches_custom_group(mock_get_client):
    """saved-searches list with -g uses the specified search group."""
    client = MagicMock(spec=httpx.Client)
    mock_get_client.return_value = client
    client.get.return_value = _mock_response({"items": [], "count": 0})

    runner = CliRunner()
    result = runner.invoke(cli, ["saved-searches", "list", "-g", "my_search_group"])

    assert result.exit_code == 0
    url = client.get.call_args[0][0]
    assert url == "/api/v1/m/my_search_group/search/saved"


def test_saved_searches_help():
    """saved-searches --help lists all CRUD subcommands."""
    runner = CliRunner()
    result = runner.invoke(cli, ["saved-searches", "--help"])

    assert result.exit_code == 0
    for sub in ("list", "get", "create", "update", "delete"):
        assert sub in result.output


def test_singular_saved_search_help_text():
    """Singular form in help text should be 'saved search', not 'saved searche'."""
    runner = CliRunner()
    result = runner.invoke(cli, ["saved-searches", "--help"])

    assert "saved search" in result.output
    assert "saved searche." not in result.output
