"""Tests for the generic CRUD endpoint factory across all four scopes."""

from __future__ import annotations

from unittest.mock import MagicMock

import httpx

from cribl_cli.api.endpoint_factory import EndpointConfig, Endpoints


def _mock_response(json_data):
    resp = MagicMock(spec=httpx.Response)
    resp.json.return_value = json_data
    resp.raise_for_status.return_value = None
    return resp


def _make_client():
    return MagicMock(spec=httpx.Client)


# ---------------------------------------------------------------------------
# Scope URL construction — list
# ---------------------------------------------------------------------------


def test_group_scope_list():
    """Group scope builds /api/v1/m/{group}/{path}."""
    client = _make_client()
    client.get.return_value = _mock_response({"items": []})

    ep = Endpoints(EndpointConfig(scope="group", path="system/parsers"))
    ep.list(client, "default")

    client.get.assert_called_once()
    url_arg = client.get.call_args[0][0]
    assert url_arg == "/api/v1/m/default/system/parsers"


def test_global_scope_list():
    """Global scope builds /api/v1/{path}."""
    client = _make_client()
    client.get.return_value = _mock_response({"items": []})

    ep = Endpoints(EndpointConfig(scope="global", path="system/users"))
    ep.list(client, "_global_")

    url_arg = client.get.call_args[0][0]
    assert url_arg == "/api/v1/system/users"


def test_search_scope_list():
    """Search scope builds /api/v1/m/{group}/search/{path}."""
    client = _make_client()
    client.get.return_value = _mock_response({"items": []})

    ep = Endpoints(EndpointConfig(scope="search", path="macros"))
    ep.list(client, "default_search")

    url_arg = client.get.call_args[0][0]
    assert url_arg == "/api/v1/m/default_search/search/macros"


def test_lake_scope_list():
    """Lake scope builds /api/v1/products/lake/lakes/{id}/{path}."""
    client = _make_client()
    client.get.return_value = _mock_response({"items": []})

    ep = Endpoints(EndpointConfig(scope="lake", path="datasets"))
    ep.list(client, "lake-abc")

    url_arg = client.get.call_args[0][0]
    assert url_arg == "/api/v1/products/lake/lakes/lake-abc/datasets"


# ---------------------------------------------------------------------------
# get — by ID and singleton
# ---------------------------------------------------------------------------


def test_get_by_id():
    """get appends /{id} to the base URL."""
    client = _make_client()
    client.get.return_value = _mock_response({"items": [{"id": "p1"}]})

    ep = Endpoints(EndpointConfig(scope="group", path="system/parsers"))
    result = ep.get(client, "default", "p1")

    url_arg = client.get.call_args[0][0]
    assert url_arg == "/api/v1/m/default/system/parsers/p1"
    assert result == {"items": [{"id": "p1"}]}


def test_singleton_get():
    """Singleton endpoints omit the ID from the URL."""
    client = _make_client()
    client.get.return_value = _mock_response({"auth": "saml"})

    ep = Endpoints(EndpointConfig(scope="global", path="system/auth", singleton=True))
    result = ep.get(client, "_global_", "ignored")

    url_arg = client.get.call_args[0][0]
    assert url_arg == "/api/v1/system/auth"


# ---------------------------------------------------------------------------
# create / update / delete
# ---------------------------------------------------------------------------


def test_create_posts_data():
    """create POSTs the data dict to the base URL."""
    client = _make_client()
    client.post.return_value = _mock_response({"items": [{"id": "new"}]})

    ep = Endpoints(EndpointConfig(scope="group", path="system/parsers"))
    body = {"id": "new", "type": "syslog"}
    ep.create(client, "default", body)

    client.post.assert_called_once()
    url_arg = client.post.call_args[0][0]
    assert url_arg == "/api/v1/m/default/system/parsers"
    assert client.post.call_args[1]["json"] == body


def test_update_patches_data():
    """update PATCHes data to the URL with /{id}."""
    client = _make_client()
    client.patch.return_value = _mock_response({"items": [{"id": "p1"}]})

    ep = Endpoints(EndpointConfig(scope="group", path="system/parsers"))
    updates = {"name": "updated-parser"}
    ep.update(client, "default", "p1", updates)

    client.patch.assert_called_once()
    url_arg = client.patch.call_args[0][0]
    assert url_arg == "/api/v1/m/default/system/parsers/p1"
    assert client.patch.call_args[1]["json"] == updates


def test_update_singleton_patches_without_id():
    """Singleton update PATCHes to the base URL without an ID suffix."""
    client = _make_client()
    client.patch.return_value = _mock_response({"updated": True})

    ep = Endpoints(EndpointConfig(scope="global", path="system/auth", singleton=True))
    updates = {"method": "saml"}
    ep.update(client, "_global_", "ignored", updates)

    url_arg = client.patch.call_args[0][0]
    assert url_arg == "/api/v1/system/auth"


def test_delete_by_id():
    """delete sends DELETE to the URL with /{id}."""
    client = _make_client()
    client.delete.return_value = _mock_response({"items": []})

    ep = Endpoints(EndpointConfig(scope="group", path="system/parsers"))
    ep.delete(client, "default", "p1")

    client.delete.assert_called_once()
    url_arg = client.delete.call_args[0][0]
    assert url_arg == "/api/v1/m/default/system/parsers/p1"
