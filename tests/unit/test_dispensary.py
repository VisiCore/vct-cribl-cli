"""Tests for Dispensary pack resolution and the layered install_pack logic.

The Dispensary catalog is a public, unauthenticated listing. install_pack
resolves a bare pack ID against it, while files and URLs bypass it entirely.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import httpx
import pytest

from cribl_cli.api.endpoints import dispensary
from cribl_cli.api.endpoints.dispensary import (
    DISPENSARY_BASE,
    resolve_dispensary_source,
)
from cribl_cli.api.endpoints.packs import install_pack


SAMPLE_CATALOG = [
    {
        "name": "cribl-cisco-ftd-cleanup",
        "displayName": "Cisco FTD",
        "version": "1.1.16",
        "Key": "dl/cribl-cisco-ftd-cleanup/latest/cribl-cisco-ftd-cleanup-latest.crbl",
    },
    {
        "name": "MicrosoftDNSLogging",
        "displayName": "Microsoft DNS",
        "Key": "dl/MicrosoftDNSLogging/latest/MicrosoftDNSLogging-latest.crbl",
    },
]


def _mock_response(json_data):
    resp = MagicMock(spec=httpx.Response)
    resp.json.return_value = json_data
    resp.raise_for_status.return_value = None
    return resp


@pytest.fixture
def patched_catalog(monkeypatch):
    monkeypatch.setattr(dispensary, "list_dispensary_packs", lambda: SAMPLE_CATALOG)


# ---------------------------------------------------------------------------
# resolve_dispensary_source
# ---------------------------------------------------------------------------


def test_resolve_uses_catalog_version(patched_catalog):
    url = resolve_dispensary_source("cribl-cisco-ftd-cleanup")
    assert url == (
        f"{DISPENSARY_BASE}/dl/cribl-cisco-ftd-cleanup/1.1.16/"
        "cribl-cisco-ftd-cleanup-1.1.16.crbl"
    )


def test_resolve_pins_explicit_version(patched_catalog):
    url = resolve_dispensary_source("cribl-cisco-ftd-cleanup", version="1.0.0")
    assert url.endswith("/1.0.0/cribl-cisco-ftd-cleanup-1.0.0.crbl")


def test_resolve_case_insensitive(patched_catalog):
    url = resolve_dispensary_source("CRIBL-CISCO-FTD-CLEANUP")
    assert "cribl-cisco-ftd-cleanup-1.1.16.crbl" in url


def test_resolve_falls_back_to_key_when_no_version(patched_catalog):
    url = resolve_dispensary_source("MicrosoftDNSLogging")
    assert url == f"{DISPENSARY_BASE}/dl/MicrosoftDNSLogging/latest/MicrosoftDNSLogging-latest.crbl"


def test_resolve_unknown_pack_suggests(patched_catalog):
    with pytest.raises(ValueError, match="cribl-cisco-ftd-cleanup"):
        resolve_dispensary_source("cisco-ftd")


def test_resolve_unknown_pack_no_match(patched_catalog):
    with pytest.raises(ValueError, match="not found in the Cribl Dispensary"):
        resolve_dispensary_source("totally-unrelated-pack")


def test_list_dispensary_packs_unwraps_items(monkeypatch):
    monkeypatch.setattr(
        dispensary.httpx, "get", lambda *a, **k: _mock_response({"items": SAMPLE_CATALOG})
    )
    assert dispensary.list_dispensary_packs() == SAMPLE_CATALOG


# ---------------------------------------------------------------------------
# install_pack layered resolution
# ---------------------------------------------------------------------------


def test_install_resolves_bare_id_via_dispensary(monkeypatch):
    client = MagicMock(spec=httpx.Client)
    client.post.return_value = _mock_response({"ok": True})
    monkeypatch.setattr(
        "cribl_cli.api.endpoints.packs.resolve_dispensary_source",
        lambda src, ver: f"{DISPENSARY_BASE}/dl/{src}/{ver or 'x'}/file.crbl",
    )

    install_pack(client, "defaultHybrid", "cribl-cisco-ftd-cleanup")

    sent = client.post.call_args[1]["json"]["source"]
    assert sent == f"{DISPENSARY_BASE}/dl/cribl-cisco-ftd-cleanup/x/file.crbl"


def test_install_passes_url_through_untouched(monkeypatch):
    client = MagicMock(spec=httpx.Client)
    client.post.return_value = _mock_response({"ok": True})

    def _boom(*a, **k):
        raise AssertionError("dispensary should not be consulted for a URL")

    monkeypatch.setattr("cribl_cli.api.endpoints.packs.resolve_dispensary_source", _boom)

    url = "https://example.com/foo.crbl"
    install_pack(client, "defaultHybrid", url)
    assert client.post.call_args[1]["json"]["source"] == url
