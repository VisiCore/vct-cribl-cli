"""Tests for offset/limit pagination helper."""

from __future__ import annotations

from unittest.mock import MagicMock

import httpx

from cribl_cli.utils.pagination import paginated_get


def _mock_response(json_data):
    """Create a mock httpx.Response that returns json_data."""
    resp = MagicMock(spec=httpx.Response)
    resp.json.return_value = json_data
    resp.raise_for_status.return_value = None
    return resp


# ---------------------------------------------------------------------------
# Single page (fetch_all=False)
# ---------------------------------------------------------------------------


def test_single_page():
    """When fetch_all is False, a single GET is made and the response returned."""
    client = MagicMock(spec=httpx.Client)
    payload = {"items": [{"id": "a"}, {"id": "b"}], "count": 2}
    client.get.return_value = _mock_response(payload)

    result = paginated_get(client, "/api/v1/things")

    assert result == payload
    client.get.assert_called_once()


# ---------------------------------------------------------------------------
# Multi page (fetch_all=True)
# ---------------------------------------------------------------------------


def test_multi_page():
    """When fetch_all is True, multiple pages are collected until a partial page."""
    client = MagicMock(spec=httpx.Client)

    page1 = {"items": [{"id": f"item-{i}"} for i in range(100)]}
    page2 = {"items": [{"id": f"item-{i}"} for i in range(100, 150)]}

    client.get.side_effect = [
        _mock_response(page1),
        _mock_response(page2),
    ]

    result = paginated_get(client, "/api/v1/things", fetch_all=True, limit=100)

    assert len(result["items"]) == 150
    assert result["count"] == 150
    assert client.get.call_count == 2


def test_fetch_all_single_page():
    """fetch_all=True with fewer items than limit stops after one page."""
    client = MagicMock(spec=httpx.Client)
    payload = {"items": [{"id": "only-one"}]}
    client.get.return_value = _mock_response(payload)

    result = paginated_get(client, "/api/v1/things", fetch_all=True, limit=100)

    assert result["items"] == [{"id": "only-one"}]
    assert result["count"] == 1
    client.get.assert_called_once()


def test_fetch_all_collects_all_pages():
    """Verify that all items across three pages are collected."""
    client = MagicMock(spec=httpx.Client)

    pages = [
        {"items": [{"id": f"p1-{i}"} for i in range(10)]},
        {"items": [{"id": f"p2-{i}"} for i in range(10)]},
        {"items": [{"id": f"p3-{i}"} for i in range(5)]},  # partial = last page
    ]
    client.get.side_effect = [_mock_response(p) for p in pages]

    result = paginated_get(client, "/api/v1/things", fetch_all=True, limit=10)

    assert len(result["items"]) == 25
    assert result["count"] == 25
    assert client.get.call_count == 3


def test_params_forwarded():
    """Extra params dict is forwarded on every request."""
    client = MagicMock(spec=httpx.Client)
    payload = {"items": []}
    client.get.return_value = _mock_response(payload)

    paginated_get(client, "/api/v1/things", params={"filter": "active"})

    call_kwargs = client.get.call_args
    assert "filter" in call_kwargs.kwargs.get("params", call_kwargs[1].get("params", {}))
