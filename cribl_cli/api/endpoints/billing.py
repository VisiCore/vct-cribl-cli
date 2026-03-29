"""Management plane billing endpoints (cloud only, v5 API)."""
from __future__ import annotations

from typing import Any

import httpx

_BASE = "/v5/organizations"


def _consumption_url(org_id: str, path: str) -> str:
    return f"{_BASE}/{org_id}/billing/consumption/{path}"


def _consumption_params(starting_on: str, ending_before: str, window: str) -> dict[str, str]:
    return {"startingOn": starting_on, "endingBefore": ending_before, "window": window}


def get_products_stats(
    client: httpx.Client, org_id: str, *, starting_on: str, ending_before: str, window: str = "monthly",
) -> Any:
    resp = client.get(
        _consumption_url(org_id, "products-stats"),
        params=_consumption_params(starting_on, ending_before, window),
    )
    resp.raise_for_status()
    return resp.json()


def get_credits_summary(
    client: httpx.Client, org_id: str, *, starting_on: str, ending_before: str, window: str = "monthly",
) -> Any:
    resp = client.get(
        _consumption_url(org_id, "credits-summary"),
        params=_consumption_params(starting_on, ending_before, window),
    )
    resp.raise_for_status()
    return resp.json()


def get_cumulative(
    client: httpx.Client, org_id: str, *, starting_on: str, ending_before: str, window: str = "monthly",
) -> Any:
    resp = client.get(
        _consumption_url(org_id, "cumulative"),
        params=_consumption_params(starting_on, ending_before, window),
    )
    resp.raise_for_status()
    return resp.json()


def get_products_breakdown(
    client: httpx.Client, org_id: str, *, starting_on: str, ending_before: str, window: str = "monthly",
) -> Any:
    resp = client.get(
        _consumption_url(org_id, "products-breakdown"),
        params=_consumption_params(starting_on, ending_before, window),
    )
    resp.raise_for_status()
    return resp.json()


def get_product_breakdown(
    client: httpx.Client, org_id: str, product_slug: str, *, starting_on: str, ending_before: str, window: str = "monthly",
) -> Any:
    resp = client.get(
        _consumption_url(org_id, f"single-product-breakdown/{product_slug}"),
        params=_consumption_params(starting_on, ending_before, window),
    )
    resp.raise_for_status()
    return resp.json()


def list_invoices(client: httpx.Client, org_id: str) -> Any:
    resp = client.get(f"{_BASE}/{org_id}/billing/invoices")
    resp.raise_for_status()
    return resp.json()


def get_invoice(client: httpx.Client, org_id: str, invoice_id: str) -> Any:
    resp = client.get(f"{_BASE}/{org_id}/billing/invoices/{invoice_id}")
    resp.raise_for_status()
    return resp.json()
