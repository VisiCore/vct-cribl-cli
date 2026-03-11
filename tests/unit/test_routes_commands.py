"""Tests for route table manipulation logic in the routes endpoint module.

The route table is a single document with an 'items' array. Creating a new route
inserts it before the catch-all (filter="true", final=True). Updating merges
fields. Deleting removes by ID. The full table is always PATCHed back.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import httpx
import pytest

from cribl_cli.api.endpoints.routes import (
    create_route,
    delete_route,
    get_route,
    list_routes,
    update_route,
)


def _mock_response(json_data):
    resp = MagicMock(spec=httpx.Response)
    resp.json.return_value = json_data
    resp.raise_for_status.return_value = None
    return resp


def _make_client():
    return MagicMock(spec=httpx.Client)


# ---------------------------------------------------------------------------
# Sample route tables
# ---------------------------------------------------------------------------

ROUTE_TABLE_WITH_CATCHALL = {
    "id": "default",
    "items": [
        {"id": "route-1", "filter": "source == 'syslog'", "pipeline": "syslog_pipe"},
        {"id": "route-2", "filter": "source == 'http'", "pipeline": "http_pipe"},
        {"id": "catch-all", "filter": "true", "final": True, "pipeline": "default"},
    ],
}

ROUTE_TABLE_WITHOUT_CATCHALL = {
    "id": "default",
    "items": [
        {"id": "route-1", "filter": "source == 'syslog'", "pipeline": "syslog_pipe"},
    ],
}


# ---------------------------------------------------------------------------
# create_route
# ---------------------------------------------------------------------------


def test_create_inserts_before_catchall():
    """New route is inserted before the catch-all entry."""
    client = _make_client()
    import copy
    table = copy.deepcopy(ROUTE_TABLE_WITH_CATCHALL)

    client.get.return_value = _mock_response(table)
    client.patch.return_value = _mock_response({"ok": True})

    new_route = {"id": "route-new", "filter": "source == 'kafka'", "pipeline": "kafka_pipe"}
    create_route(client, "default", new_route)

    # Verify PATCH was called
    client.patch.assert_called_once()
    patched_table = client.patch.call_args[1]["json"]
    items = patched_table["items"]

    # New route should be at index 2 (before catch-all which was at index 2)
    assert items[-1]["id"] == "catch-all"
    assert items[-1]["filter"] == "true"
    assert items[-2]["id"] == "route-new"


def test_create_appends_without_catchall():
    """When there is no catch-all, the new route is appended at the end."""
    client = _make_client()
    import copy
    table = copy.deepcopy(ROUTE_TABLE_WITHOUT_CATCHALL)

    client.get.return_value = _mock_response(table)
    client.patch.return_value = _mock_response({"ok": True})

    new_route = {"id": "route-new", "filter": "source == 'kafka'", "pipeline": "kafka_pipe"}
    create_route(client, "default", new_route)

    patched_table = client.patch.call_args[1]["json"]
    items = patched_table["items"]
    assert items[-1]["id"] == "route-new"


# ---------------------------------------------------------------------------
# update_route
# ---------------------------------------------------------------------------


def test_update_merges_route():
    """Updating a route merges new fields into the existing route dict."""
    client = _make_client()
    import copy
    table = copy.deepcopy(ROUTE_TABLE_WITH_CATCHALL)

    client.get.return_value = _mock_response(table)
    client.patch.return_value = _mock_response({"ok": True})

    update_route(client, "default", "route-1", {"pipeline": "new_syslog_pipe", "description": "updated"})

    patched_table = client.patch.call_args[1]["json"]
    route1 = next(r for r in patched_table["items"] if r["id"] == "route-1")
    assert route1["pipeline"] == "new_syslog_pipe"
    assert route1["description"] == "updated"
    # Original filter should be preserved
    assert route1["filter"] == "source == 'syslog'"


def test_update_raises_for_missing_route():
    """Updating a non-existent route ID raises ValueError."""
    client = _make_client()
    import copy
    table = copy.deepcopy(ROUTE_TABLE_WITH_CATCHALL)

    client.get.return_value = _mock_response(table)

    with pytest.raises(ValueError, match="not found"):
        update_route(client, "default", "nonexistent", {"pipeline": "x"})


# ---------------------------------------------------------------------------
# delete_route
# ---------------------------------------------------------------------------


def test_delete_removes_route():
    """Deleting a route removes it from the items array."""
    client = _make_client()
    import copy
    table = copy.deepcopy(ROUTE_TABLE_WITH_CATCHALL)

    client.get.return_value = _mock_response(table)
    client.patch.return_value = _mock_response({"ok": True})

    delete_route(client, "default", "route-1")

    patched_table = client.patch.call_args[1]["json"]
    ids = [r["id"] for r in patched_table["items"]]
    assert "route-1" not in ids
    assert "route-2" in ids
    assert "catch-all" in ids


def test_delete_raises_for_missing_route():
    """Deleting a non-existent route ID raises ValueError."""
    client = _make_client()
    import copy
    table = copy.deepcopy(ROUTE_TABLE_WITH_CATCHALL)

    client.get.return_value = _mock_response(table)

    with pytest.raises(ValueError, match="not found"):
        delete_route(client, "default", "nonexistent")


# ---------------------------------------------------------------------------
# get_route / list_routes
# ---------------------------------------------------------------------------


def test_get_route_found():
    """get_route returns the matching route dict."""
    client = _make_client()
    import copy
    table = copy.deepcopy(ROUTE_TABLE_WITH_CATCHALL)
    client.get.return_value = _mock_response(table)

    route = get_route(client, "default", "route-2")

    assert route["id"] == "route-2"
    assert route["pipeline"] == "http_pipe"


def test_get_route_not_found():
    """get_route raises ValueError for an unknown route ID."""
    client = _make_client()
    import copy
    table = copy.deepcopy(ROUTE_TABLE_WITH_CATCHALL)
    client.get.return_value = _mock_response(table)

    with pytest.raises(ValueError, match="not found"):
        get_route(client, "default", "no-such-route")


def test_list_routes_returns_table():
    """list_routes returns the full route table dict."""
    client = _make_client()
    import copy
    table = copy.deepcopy(ROUTE_TABLE_WITH_CATCHALL)
    client.get.return_value = _mock_response(table)

    result = list_routes(client, "default")

    assert result["id"] == "default"
    assert len(result["items"]) == 3
