"""License usage endpoint — daily throughput metrics for up to 90 days."""
from __future__ import annotations

from typing import Any

import httpx


def get_license_usage(
    client: httpx.Client,
    *,
    start: str | None = None,
    end: str | None = None,
) -> Any:
    params: dict[str, str] = {}
    if start:
        params["earliest"] = start
    if end:
        params["latest"] = end
    resp = client.get("/api/v1/system/licenses/usage", params=params)
    resp.raise_for_status()
    return resp.json()
