"""System metrics endpoint."""
from __future__ import annotations

from typing import Any

import httpx


def get_metrics(
    client: httpx.Client, filter_expr: str | None = None
) -> Any:
    """Get system metrics, optionally filtered.

    Args:
        client: An authenticated httpx client.
        filter_expr: Optional filter expression to narrow results.
    """
    params: dict[str, str] = {}
    if filter_expr is not None:
        params["filter"] = filter_expr
    resp = client.get("/api/v1/system/metrics", params=params)
    resp.raise_for_status()
    return resp.json()
