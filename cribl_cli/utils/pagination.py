"""Offset/limit pagination helper."""

from __future__ import annotations

from typing import Any

import httpx


def paginated_get(
    client: httpx.Client,
    url: str,
    *,
    fetch_all: bool = False,
    limit: int = 100,
    params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    base_params = dict(params or {})

    if not fetch_all:
        base_params.setdefault("limit", limit)
        resp = client.get(url, params=base_params)
        resp.raise_for_status()
        return resp.json()

    all_items: list = []
    offset = 0
    while True:
        p = {**base_params, "limit": limit, "offset": offset}
        resp = client.get(url, params=p)
        resp.raise_for_status()
        data = resp.json()
        items = data.get("items", [])
        all_items.extend(items)
        if len(items) < limit:
            break
        offset += limit

    return {"items": all_items, "count": len(all_items)}
