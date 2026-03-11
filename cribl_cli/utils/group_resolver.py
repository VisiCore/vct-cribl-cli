"""Resolve worker group from API when not explicitly provided."""

from __future__ import annotations

import httpx


def resolve_group(client: httpx.Client, group: str | None = None) -> str:
    if group:
        return group
    resp = client.get("/api/v1/master/groups")
    resp.raise_for_status()
    data = resp.json()
    items = data.get("items", [])
    if items:
        return items[0].get("id", "default")
    return "default"
