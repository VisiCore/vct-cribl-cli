"""Tests for error classes and handle_error behaviour."""

from __future__ import annotations

import json

import pytest

from cribl_cli.utils.errors import CriblApiError, DryRunAbort, handle_error


def test_cribl_api_error_attributes():
    """CriblApiError stores status, message, and optional detail."""
    err = CriblApiError(status=404, message="Not found", detail="resource xyz missing")

    assert err.status == 404
    assert err.message == "Not found"
    assert err.detail == "resource xyz missing"
    assert str(err) == "Not found"


def test_cribl_api_error_no_detail():
    """CriblApiError works with detail=None (default)."""
    err = CriblApiError(status=500, message="Internal error")

    assert err.detail is None


def test_handle_error_api_error_exits_1(capsys):
    """handle_error with CriblApiError writes JSON to stderr and exits 1."""
    err = CriblApiError(status=403, message="Forbidden", detail="insufficient scope")

    with pytest.raises(SystemExit) as exc_info:
        handle_error(err)

    assert exc_info.value.code == 1
    captured = capsys.readouterr()
    payload = json.loads(captured.err)
    assert payload["error"] == "Forbidden"
    assert payload["status"] == 403
    assert payload["detail"] == "insufficient scope"


def test_handle_error_dry_run_exits_0():
    """handle_error with DryRunAbort exits 0 (success)."""
    err = DryRunAbort()

    with pytest.raises(SystemExit) as exc_info:
        handle_error(err)

    assert exc_info.value.code == 0


def test_handle_error_generic_error(capsys):
    """handle_error with a generic Exception writes error JSON and exits 1."""
    err = RuntimeError("something went wrong")

    with pytest.raises(SystemExit) as exc_info:
        handle_error(err)

    assert exc_info.value.code == 1
    captured = capsys.readouterr()
    payload = json.loads(captured.err)
    assert payload["error"] == "something went wrong"
    assert "status" not in payload
