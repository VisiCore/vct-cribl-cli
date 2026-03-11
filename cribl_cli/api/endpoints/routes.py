"""Route table management endpoints.

CRITICAL: Routes are stored as a single document (a route table with an
``items`` array). Individual routes are never addressed by their own URL.
When creating a new route, it is inserted *before* the catch-all route
(filter="true", final=True) so that the catch-all always remains last.
The entire table is then PATCHed back to the server.
"""
from __future__ import annotations

from typing import Any

import httpx


def _base(group: str) -> str:
    return f"/api/v1/m/{group}/routes"


def _is_catch_all(route: dict[str, Any]) -> bool:
    """Return True if a route looks like the default catch-all."""
    return route.get("filter") == "true" and route.get("final") is True


def _fetch_route_table(client: httpx.Client, group: str) -> dict[str, Any]:
    """Fetch the current route table.

    Handles two API response formats:
    - Stream groups: ``{"id": "default", "items": [...routes...]}``
    - Edge groups: ``{"items": [{"id": "default", "routes": [...]}], "count": 1}``

    Returns a normalised dict with ``"items"`` containing the routes array
    and ``"_edge_format"`` set to True if the edge-style wrapper was detected.
    """
    resp = client.get(_base(group))
    resp.raise_for_status()
    data = resp.json()

    # Detect edge-group format: items[0].routes
    items = data.get("items", [])
    if (
        items
        and isinstance(items[0], dict)
        and "routes" in items[0]
        and not any(isinstance(i, dict) and "filter" in i for i in items)
    ):
        # Edge format — unwrap
        wrapper = items[0]
        return {
            "id": wrapper.get("id", "default"),
            "items": wrapper.get("routes", []),
            "_edge_format": True,
        }

    return data


def _patch_route_table(
    client: httpx.Client, group: str, table: dict[str, Any]
) -> Any:
    """PATCH the full route table back to the server.

    Re-wraps into edge format if the table was originally fetched from an
    edge group (indicated by ``_edge_format``).
    """
    payload = dict(table)
    is_edge = payload.pop("_edge_format", False)
    if is_edge:
        # Edge groups require PATCH to /routes/{tableId} with the wrapped format
        table_id = payload.get("id", "default")
        edge_payload = {
            "id": table_id,
            "routes": payload["items"],
        }
        resp = client.patch(f"{_base(group)}/{table_id}", json=edge_payload)
    else:
        resp = client.patch(_base(group), json=payload)
    resp.raise_for_status()
    return resp.json()


def list_routes(client: httpx.Client, group: str) -> Any:
    """List the full route table for a worker group."""
    table = _fetch_route_table(client, group)
    # Strip internal flag before returning to caller
    result = {k: v for k, v in table.items() if not k.startswith("_")}
    return result


def get_route(client: httpx.Client, group: str, route_id: str) -> Any:
    """Get a single route by ID from the route table."""
    table = _fetch_route_table(client, group)
    items: list[dict[str, Any]] = table.get("items", [])
    for route in items:
        if route.get("id") == route_id:
            return route
    raise ValueError(f"Route '{route_id}' not found in route table")


def create_route(
    client: httpx.Client, group: str, data: dict[str, Any]
) -> Any:
    """Create a new route, inserting it before the catch-all.

    Fetches the existing route table, inserts the new route immediately
    before the catch-all entry (filter="true", final=True), then PATCHes
    the updated table. This ensures the catch-all always remains last.
    """
    table = _fetch_route_table(client, group)
    items: list[dict[str, Any]] = table.get("items", [])

    # Find the catch-all index; default to appending at the end.
    insert_idx = len(items)
    for idx, route in enumerate(items):
        if _is_catch_all(route):
            insert_idx = idx
            break

    items.insert(insert_idx, data)
    table["items"] = items
    return _patch_route_table(client, group, table)


def update_route(
    client: httpx.Client, group: str, route_id: str, data: dict[str, Any]
) -> Any:
    """Update an existing route by merging fields, then PATCH the table."""
    table = _fetch_route_table(client, group)
    items: list[dict[str, Any]] = table.get("items", [])

    found = False
    for route in items:
        if route.get("id") == route_id:
            route.update(data)
            found = True
            break

    if not found:
        raise ValueError(f"Route '{route_id}' not found in route table")

    table["items"] = items
    return _patch_route_table(client, group, table)


def delete_route(client: httpx.Client, group: str, route_id: str) -> Any:
    """Remove a route by ID from the table, then PATCH the table."""
    table = _fetch_route_table(client, group)
    items: list[dict[str, Any]] = table.get("items", [])

    new_items = [r for r in items if r.get("id") != route_id]
    if len(new_items) == len(items):
        raise ValueError(f"Route '{route_id}' not found in route table")

    table["items"] = new_items
    return _patch_route_table(client, group, table)
