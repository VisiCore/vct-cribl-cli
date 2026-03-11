"""Tests for --dry-run flag: logs request details and exits cleanly."""

from __future__ import annotations

import json

import httpx
import pytest

from cribl_cli.api.client import DryRunTransport
from cribl_cli.utils.errors import DryRunAbort


def test_dry_run_raises_dry_run_abort(capsys):
    """DryRunTransport writes request JSON to stderr and raises DryRunAbort."""
    inner = httpx.MockTransport(lambda req: httpx.Response(200))
    transport = DryRunTransport(inner)

    request = httpx.Request("GET", "https://cribl.example.com/api/v1/things")

    with pytest.raises(DryRunAbort):
        transport.handle_request(request)

    captured = capsys.readouterr()
    info = json.loads(captured.err)
    assert info["dry_run"] is True
    assert info["method"] == "GET"
    assert "cribl.example.com/api/v1/things" in info["url"]


def test_dry_run_includes_body(capsys):
    """DryRunTransport includes the JSON body in the logged output."""
    inner = httpx.MockTransport(lambda req: httpx.Response(200))
    transport = DryRunTransport(inner)

    body = {"id": "new-parser", "type": "syslog"}
    request = httpx.Request(
        "POST",
        "https://cribl.example.com/api/v1/m/default/system/parsers",
        json=body,
    )

    with pytest.raises(DryRunAbort):
        transport.handle_request(request)

    captured = capsys.readouterr()
    info = json.loads(captured.err)
    assert info["dry_run"] is True
    assert info["method"] == "POST"
    assert info["body"]["id"] == "new-parser"


def test_dry_run_logs_headers(capsys):
    """DryRunTransport includes request headers in the logged output."""
    inner = httpx.MockTransport(lambda req: httpx.Response(200))
    transport = DryRunTransport(inner)

    request = httpx.Request(
        "GET",
        "https://cribl.example.com/api/v1/things",
        headers={"Authorization": "Bearer test-token"},
    )

    with pytest.raises(DryRunAbort):
        transport.handle_request(request)

    captured = capsys.readouterr()
    info = json.loads(captured.err)
    assert "headers" in info
    assert info["headers"]["authorization"] == "Bearer test-token"
