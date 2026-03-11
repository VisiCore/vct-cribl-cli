"""Tests for worker group resolver."""

from __future__ import annotations

from unittest.mock import MagicMock

import httpx

from cribl_cli.utils.group_resolver import resolve_group


def _mock_response(json_data):
    resp = MagicMock(spec=httpx.Response)
    resp.json.return_value = json_data
    resp.raise_for_status.return_value = None
    return resp


def test_returns_provided_group():
    """When a group is explicitly provided, it is returned as-is."""
    client = MagicMock(spec=httpx.Client)

    result = resolve_group(client, "my-group")

    assert result == "my-group"
    client.get.assert_not_called()


def test_resolves_from_api():
    """When no group is provided, the first group from the API is used."""
    client = MagicMock(spec=httpx.Client)
    client.get.return_value = _mock_response({
        "items": [
            {"id": "prod-group", "name": "Production"},
            {"id": "dev-group", "name": "Development"},
        ]
    })

    result = resolve_group(client, None)

    assert result == "prod-group"
    client.get.assert_called_once_with("/api/v1/master/groups")


def test_defaults_to_default():
    """When the API returns no groups, 'default' is used as fallback."""
    client = MagicMock(spec=httpx.Client)
    client.get.return_value = _mock_response({"items": []})

    result = resolve_group(client, None)

    assert result == "default"
