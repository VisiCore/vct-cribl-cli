"""Tests for license usage endpoint and CLI command."""
from __future__ import annotations

from unittest.mock import MagicMock

import httpx
from click.testing import CliRunner

from cribl_cli.api.endpoints.license_usage import get_license_usage
from cribl_cli.cli import cli


def _mock_response(json_data):
    resp = MagicMock(spec=httpx.Response)
    resp.json.return_value = json_data
    resp.raise_for_status.return_value = None
    return resp


def test_get_license_usage_url():
    client = MagicMock(spec=httpx.Client)
    client.get.return_value = _mock_response({"items": []})

    get_license_usage(client)

    client.get.assert_called_once_with("/api/v1/system/licenses/usage", params={})


def test_get_license_usage_with_dates():
    client = MagicMock(spec=httpx.Client)
    client.get.return_value = _mock_response({"items": []})

    get_license_usage(client, start="2025-01-01", end="2025-02-01")

    client.get.assert_called_once_with(
        "/api/v1/system/licenses/usage",
        params={"earliest": "2025-01-01", "latest": "2025-02-01"},
    )


def test_license_usage_command_exists():
    runner = CliRunner()
    result = runner.invoke(cli, ["license-usage", "--help"])
    assert result.exit_code == 0
    assert "get" in result.output
