"""Tests for billing endpoints and CLI commands."""
from __future__ import annotations

from unittest.mock import MagicMock

import httpx
from click.testing import CliRunner

from cribl_cli.api.endpoints.billing import (
    get_credits_summary,
    get_cumulative,
    get_invoice,
    get_product_breakdown,
    get_products_breakdown,
    get_products_stats,
    list_invoices,
)
from cribl_cli.cli import cli


def _mock_response(json_data):
    resp = MagicMock(spec=httpx.Response)
    resp.json.return_value = json_data
    resp.raise_for_status.return_value = None
    return resp


# ---------------------------------------------------------------------------
# Endpoint URL construction
# ---------------------------------------------------------------------------

_ORG = "testorg"
_PARAMS = {"startingOn": "2025-01-01T00:00:00Z", "endingBefore": "2025-02-01T00:00:00Z", "window": "monthly"}
_BASE = f"/v5/organizations/{_ORG}/billing"


def test_get_products_stats_url():
    client = MagicMock(spec=httpx.Client)
    client.get.return_value = _mock_response({"data": []})

    get_products_stats(client, _ORG, starting_on="2025-01-01T00:00:00Z", ending_before="2025-02-01T00:00:00Z")

    client.get.assert_called_once_with(f"{_BASE}/consumption/products-stats", params=_PARAMS)


def test_get_credits_summary_url():
    client = MagicMock(spec=httpx.Client)
    client.get.return_value = _mock_response({"data": []})

    get_credits_summary(client, _ORG, starting_on="2025-01-01T00:00:00Z", ending_before="2025-02-01T00:00:00Z")

    client.get.assert_called_once_with(f"{_BASE}/consumption/credits-summary", params=_PARAMS)


def test_get_cumulative_url():
    client = MagicMock(spec=httpx.Client)
    client.get.return_value = _mock_response({"data": []})

    get_cumulative(client, _ORG, starting_on="2025-01-01T00:00:00Z", ending_before="2025-02-01T00:00:00Z")

    client.get.assert_called_once_with(f"{_BASE}/consumption/cumulative", params=_PARAMS)


def test_get_products_breakdown_url():
    client = MagicMock(spec=httpx.Client)
    client.get.return_value = _mock_response({"data": []})

    get_products_breakdown(client, _ORG, starting_on="2025-01-01T00:00:00Z", ending_before="2025-02-01T00:00:00Z")

    client.get.assert_called_once_with(f"{_BASE}/consumption/products-breakdown", params=_PARAMS)


def test_get_product_breakdown_url():
    client = MagicMock(spec=httpx.Client)
    client.get.return_value = _mock_response({"data": []})

    get_product_breakdown(client, _ORG, "stream", starting_on="2025-01-01T00:00:00Z", ending_before="2025-02-01T00:00:00Z")

    client.get.assert_called_once_with(f"{_BASE}/consumption/single-product-breakdown/stream", params=_PARAMS)


def test_list_invoices_url():
    client = MagicMock(spec=httpx.Client)
    client.get.return_value = _mock_response({"data": []})

    list_invoices(client, _ORG)

    client.get.assert_called_once_with(f"{_BASE}/invoices")


def test_get_invoice_url():
    client = MagicMock(spec=httpx.Client)
    client.get.return_value = _mock_response({"data": {}})

    get_invoice(client, _ORG, "inv-123")

    client.get.assert_called_once_with(f"{_BASE}/invoices/inv-123")


# ---------------------------------------------------------------------------
# CLI registration
# ---------------------------------------------------------------------------

def test_billing_command_exists():
    runner = CliRunner()
    result = runner.invoke(cli, ["billing", "--help"])
    assert result.exit_code == 0


def test_billing_subcommands():
    runner = CliRunner()
    result = runner.invoke(cli, ["billing", "--help"])
    for sub in ("products-stats", "credits-summary", "cumulative", "products-breakdown", "product", "invoices", "invoice"):
        assert sub in result.output, f"Expected '{sub}' in billing help"


def test_usage_groups_full_crud():
    runner = CliRunner()
    result = runner.invoke(cli, ["usage-groups", "--help"])
    assert result.exit_code == 0
    for sub in ("list", "get", "create", "update", "delete"):
        assert sub in result.output, f"Expected '{sub}' in usage-groups help"


def test_subscriptions_create_update():
    runner = CliRunner()
    result = runner.invoke(cli, ["subscriptions", "--help"])
    assert result.exit_code == 0
    for sub in ("list", "get", "create", "update"):
        assert sub in result.output, f"Expected '{sub}' in subscriptions help"
    assert "delete" not in result.output
