"""Tests for --dry-run flag: logs request details and exits cleanly."""

from __future__ import annotations

import json

import httpx
import pytest

from cribl_cli.api.client import DryRunTransport
from cribl_cli.utils.errors import DryRunAbort


def test_dry_run_raises_dry_run_abort(capsys):
    """DryRunTransport writes a write request's JSON to stderr and raises DryRunAbort."""
    sent = []
    inner = httpx.MockTransport(lambda req: sent.append(req) or httpx.Response(200))
    transport = DryRunTransport(inner)

    request = httpx.Request("DELETE", "https://cribl.example.com/api/v1/things/x")

    with pytest.raises(DryRunAbort):
        transport.handle_request(request)

    captured = capsys.readouterr()
    info = json.loads(captured.err)
    assert info["dry_run"] is True
    assert info["method"] == "DELETE"
    assert "cribl.example.com/api/v1/things/x" in info["url"]
    assert sent == []  # the write never reached the wire


def test_dry_run_sends_reads(capsys):
    """Reads pass through so a command can reach (and show) its write."""
    sent = []
    inner = httpx.MockTransport(lambda req: sent.append(req) or httpx.Response(200, json={"ok": 1}))
    transport = DryRunTransport(inner)

    resp = transport.handle_request(
        httpx.Request("GET", "https://cribl.example.com/api/v1/things")
    )

    assert resp.status_code == 200
    assert len(sent) == 1
    assert "(read, sent)" in capsys.readouterr().err


def test_dry_run_get_then_patch_shows_the_patch(capsys):
    """A merge-on-update (GET then PATCH) logs the PATCH body, not just the GET."""
    inner = httpx.MockTransport(lambda req: httpx.Response(200, json={"id": "p1"}))
    client = httpx.Client(base_url="https://cribl.example.com", transport=DryRunTransport(inner))

    client.get("/api/v1/m/default/pipelines/p1")
    with pytest.raises(DryRunAbort):
        client.patch("/api/v1/m/default/pipelines/p1", json={"id": "p1", "conf": {}})

    err = capsys.readouterr().err
    info = json.loads(err[err.index("{"):])
    assert info["method"] == "PATCH"
    assert info["body"] == {"id": "p1", "conf": {}}


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
        "POST",
        "https://cribl.example.com/api/v1/things",
        headers={"Authorization": "Bearer test-token"},
    )

    with pytest.raises(DryRunAbort):
        transport.handle_request(request)

    captured = capsys.readouterr()
    info = json.loads(captured.err)
    assert "headers" in info
    assert info["headers"]["authorization"] == "Bearer test-token"
