"""Tests for RetryTransport — retries idempotent requests on 502/503/504."""

from __future__ import annotations

from unittest.mock import MagicMock, call, patch

import httpx

from cribl_cli.api.client import RetryTransport


def _mock_response(status_code):
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    return resp


def _make_request(method="GET", url="https://example.com/api"):
    return httpx.Request(method, url)


def test_retry_on_503_then_success():
    """Retries on 503, then returns 200."""
    inner = MagicMock()
    inner.handle_request.side_effect = [
        _mock_response(503),
        _mock_response(200),
    ]
    transport = RetryTransport(inner)
    request = _make_request("GET")

    with patch("cribl_cli.api.client.time.sleep"):
        response = transport.handle_request(request)

    assert response.status_code == 200
    assert inner.handle_request.call_count == 2


def test_no_retry_on_400():
    """400 is returned immediately without retrying."""
    inner = MagicMock()
    inner.handle_request.return_value = _mock_response(400)
    transport = RetryTransport(inner)
    request = _make_request("GET")

    response = transport.handle_request(request)

    assert response.status_code == 400
    assert inner.handle_request.call_count == 1


def test_no_retry_on_post():
    """POST with 503 is not retried (not idempotent)."""
    inner = MagicMock()
    inner.handle_request.return_value = _mock_response(503)
    transport = RetryTransport(inner)
    request = _make_request("POST")

    response = transport.handle_request(request)

    assert response.status_code == 503
    assert inner.handle_request.call_count == 1


def test_max_retries_exhausted():
    """All retry attempts fail — last response returned."""
    inner = MagicMock()
    inner.handle_request.return_value = _mock_response(502)
    transport = RetryTransport(inner)
    request = _make_request("GET")

    with patch("cribl_cli.api.client.time.sleep"):
        response = transport.handle_request(request)

    assert response.status_code == 502
    # 1 initial + 3 retries = 4 total calls
    assert inner.handle_request.call_count == 4


@patch("cribl_cli.api.client.time.sleep")
def test_backoff_timing(mock_sleep):
    """Verify exponential backoff: sleep(1), sleep(2), sleep(4)."""
    inner = MagicMock()
    inner.handle_request.return_value = _mock_response(504)
    transport = RetryTransport(inner)
    request = _make_request("DELETE")

    transport.handle_request(request)

    assert mock_sleep.call_args_list == [call(1), call(2), call(4)]


def test_retry_on_502_put():
    """PUT is idempotent — 502 is retried."""
    inner = MagicMock()
    inner.handle_request.side_effect = [
        _mock_response(502),
        _mock_response(200),
    ]
    transport = RetryTransport(inner)
    request = _make_request("PUT")

    with patch("cribl_cli.api.client.time.sleep"):
        response = transport.handle_request(request)

    assert response.status_code == 200


def test_no_retry_on_success():
    """200 response is returned immediately."""
    inner = MagicMock()
    inner.handle_request.return_value = _mock_response(200)
    transport = RetryTransport(inner)
    request = _make_request("GET")

    response = transport.handle_request(request)

    assert response.status_code == 200
    assert inner.handle_request.call_count == 1
