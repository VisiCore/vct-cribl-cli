"""Tests for notebook sharing commands: acl, share, unshare."""

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


NB = "notebook-abc"


@patch("cribl_cli.commands.notebooks.get_client")
def test_acl_lists_members_and_teams(mock_get_client):
    """acl issues one GET for members and one for teams and merges them."""
    client = MagicMock(spec=httpx.Client)
    mock_get_client.return_value = client
    client.get.side_effect = [
        _mock_response({"items": [{"user": "auth0|x", "perms": []}], "count": 1}),
        _mock_response({"items": [{"team": "test-for-editor", "perms": []}], "count": 1}),
    ]

    result = CliRunner().invoke(cli, ["notebooks", "acl", NB])

    assert result.exit_code == 0
    assert "test-for-editor" in result.output
    assert "auth0|x" in result.output
    urls = [c.args[0] for c in client.get.call_args_list]
    assert urls == [
        f"/api/v1/m/default_search/search/notebooks/{NB}/acl",
        f"/api/v1/m/default_search/search/notebooks/{NB}/acl/teams",
    ]


@patch("cribl_cli.commands.notebooks.get_client")
def test_share_team_read(mock_get_client):
    """share --team --permission read posts NotebookBase to acl/teams/apply."""
    client = MagicMock(spec=httpx.Client)
    mock_get_client.return_value = client
    client.post.return_value = _mock_response({"items": [], "count": 0})

    result = CliRunner().invoke(
        cli, ["notebooks", "share", NB, "test-for-editor", "--team", "--permission", "read"]
    )

    assert result.exit_code == 0
    url = client.post.call_args.args[0]
    body = client.post.call_args.kwargs["json"]
    assert url == f"/api/v1/m/default_search/search/notebooks/{NB}/acl/teams/apply"
    assert body == {"add": {"NotebookBase": ["test-for-editor"]}}


@patch("cribl_cli.commands.notebooks.get_client")
def test_share_member_defaults_maintainer(mock_get_client):
    """share (no --team) defaults to Maintainer and posts to acl/apply."""
    client = MagicMock(spec=httpx.Client)
    mock_get_client.return_value = client
    client.post.return_value = _mock_response({"items": [], "count": 0})

    result = CliRunner().invoke(cli, ["notebooks", "share", NB, "auth0|123"])

    assert result.exit_code == 0
    url = client.post.call_args.args[0]
    body = client.post.call_args.kwargs["json"]
    assert url == f"/api/v1/m/default_search/search/notebooks/{NB}/acl/apply"
    assert body == {"add": {"NotebookMaintain": ["auth0|123"]}}


@patch("cribl_cli.commands.notebooks.get_client")
def test_unshare_removes_only_held_policy(mock_get_client):
    """unshare looks up the held policy and revokes exactly that via the rm key."""
    client = MagicMock(spec=httpx.Client)
    mock_get_client.return_value = client
    client.get.return_value = _mock_response({
        "items": [{"team": "test-for-editor", "perms": [{"policy": "NotebookBase"}]}],
        "count": 1,
    })
    client.post.return_value = _mock_response({"items": [], "count": 0})

    result = CliRunner().invoke(
        cli, ["notebooks", "unshare", NB, "test-for-editor", "--team"]
    )

    assert result.exit_code == 0
    body = client.post.call_args.kwargs["json"]
    assert body == {"rm": {"NotebookBase": ["test-for-editor"]}}


@patch("cribl_cli.commands.notebooks.get_client")
def test_unshare_noop_when_no_grant(mock_get_client):
    """unshare on a principal with no grant is a clean no-op (no POST)."""
    client = MagicMock(spec=httpx.Client)
    mock_get_client.return_value = client
    client.get.return_value = _mock_response({"items": [], "count": 0})

    result = CliRunner().invoke(
        cli, ["notebooks", "unshare", NB, "test-for-editor", "--team"]
    )

    assert result.exit_code == 0
    assert "No existing grant" in result.output
    client.post.assert_not_called()
