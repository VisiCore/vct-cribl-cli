"""Cribl Packs Dispensary endpoints.

The Dispensary (https://packs.cribl.io) is a public catalog, separate from the
Cribl Cloud API. It needs no auth and no org-specific URL, so these calls use a
plain httpx request rather than the authenticated `get_client()`.

A pack's download URL is `{DISPENSARY_BASE}/dl/{name}/{version}/{name}-{version}.crbl`.
The listing also exposes a relative `Key` (which points at the `latest` build) as
a fallback when a pack omits a version.
"""
from __future__ import annotations

from typing import Any

import httpx

DISPENSARY_BASE = "https://packs.cribl.io"
_LISTING_PATH = "/api/v1/packs/dispensary"


def list_dispensary_packs() -> list[dict]:
    """Return all packs published in the Dispensary catalog."""
    resp = httpx.get(f"{DISPENSARY_BASE}{_LISTING_PATH}", timeout=30.0, follow_redirects=True)
    resp.raise_for_status()
    data = resp.json()
    if isinstance(data, dict):
        data = data.get("items", data)
    return data if isinstance(data, list) else []


def _download_url(name: str, version: str) -> str:
    return f"{DISPENSARY_BASE}/dl/{name}/{version}/{name}-{version}.crbl"


def resolve_dispensary_source(pack_id: str, version: str | None = None) -> str:
    """Resolve a Dispensary pack ID to a downloadable `.crbl` URL.

    Matches `pack_id` against the catalog (case-insensitively) and builds a
    pinned download URL from the requested or catalog version. Falls back to the
    pack's `Key` (the `latest` build) when no version is available.
    """
    packs = list_dispensary_packs()
    by_name = {str(p.get("name", "")): p for p in packs}

    pack = by_name.get(pack_id)
    if pack is None:
        # Case-insensitive fallback.
        lowered = pack_id.lower()
        pack = next((p for p in packs if str(p.get("name", "")).lower() == lowered), None)

    if pack is None:
        suggestions = [n for n in by_name if pack_id.lower() in n.lower()][:5]
        hint = f" Did you mean: {', '.join(suggestions)}?" if suggestions else ""
        raise ValueError(
            f"Pack '{pack_id}' not found in the Cribl Dispensary.{hint} "
            f"Browse with `cribl packs dispensary --search <term>`."
        )

    name = str(pack["name"])
    ver = version or pack.get("version")
    if ver:
        return _download_url(name, str(ver))

    key = pack.get("Key")
    if key:
        return f"{DISPENSARY_BASE}/{str(key).lstrip('/')}"

    raise ValueError(f"Pack '{name}' has no resolvable download URL in the Dispensary.")
