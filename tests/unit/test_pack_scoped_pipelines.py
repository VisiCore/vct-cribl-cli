"""Pack-scoping for the hand-written pipelines and preview endpoints.

These modules build their own URLs (separate from the CRUD factory), so the
/p/{pack}/ segment is verified independently here.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import httpx

from cribl_cli.api.endpoints.pipelines import (
    create_pipeline,
    delete_pipeline,
    get_pipeline,
    list_pipelines,
    update_pipeline,
)
from cribl_cli.api.endpoints.preview import run_preview


def _mock_response(json_data):
    resp = MagicMock(spec=httpx.Response)
    resp.json.return_value = json_data
    resp.raise_for_status.return_value = None
    return resp


def _make_client():
    return MagicMock(spec=httpx.Client)


def test_pipelines_list_with_pack():
    client = _make_client()
    client.get.return_value = _mock_response({"items": []})

    list_pipelines(client, "default", pack="my-pack")

    assert client.get.call_args[0][0] == "/api/v1/m/default/p/my-pack/pipelines"


def test_pipelines_list_without_pack():
    client = _make_client()
    client.get.return_value = _mock_response({"items": []})

    list_pipelines(client, "default")

    assert client.get.call_args[0][0] == "/api/v1/m/default/pipelines"


def test_pipelines_crud_with_pack():
    client = _make_client()
    client.get.return_value = _mock_response({})
    client.post.return_value = _mock_response({})
    client.patch.return_value = _mock_response({})
    client.delete.return_value = _mock_response({})

    get_pipeline(client, "default", "p1", pack="my-pack")
    create_pipeline(client, "default", {"id": "p1"}, pack="my-pack")
    update_pipeline(client, "default", "p1", {"name": "x"}, pack="my-pack")
    delete_pipeline(client, "default", "p1", pack="my-pack")

    base = "/api/v1/m/default/p/my-pack/pipelines"
    assert client.get.call_args[0][0] == f"{base}/p1"
    assert client.post.call_args[0][0] == base
    assert client.patch.call_args[0][0] == f"{base}/p1"
    assert client.delete.call_args[0][0] == f"{base}/p1"


def test_preview_with_pack():
    client = _make_client()
    client.post.return_value = _mock_response({})

    run_preview(client, "default", {"sample": "x"}, pack="my-pack")

    assert client.post.call_args[0][0] == "/api/v1/m/default/p/my-pack/preview"


def test_preview_without_pack():
    client = _make_client()
    client.post.return_value = _mock_response({})

    run_preview(client, "default", {"sample": "x"})

    assert client.post.call_args[0][0] == "/api/v1/m/default/preview"
