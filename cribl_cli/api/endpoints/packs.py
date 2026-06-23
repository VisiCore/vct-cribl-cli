"""Pack management endpoints."""
from __future__ import annotations

import os
from typing import Any

import httpx

from cribl_cli.api.endpoints.dispensary import resolve_dispensary_source


def _base(group: str) -> str:
    return f"/api/v1/m/{group}/packs"


def _upload_local_pack(client: httpx.Client, group: str, path: str) -> str:
    """PUT a local .crbl to /packs?filename=... and return the server-side source key."""
    with open(path, "rb") as f:
        body = f.read()
    resp = client.put(
        _base(group),
        params={"filename": os.path.basename(path)},
        content=body,
        headers={"Content-Type": "application/octet-stream"},
    )
    resp.raise_for_status()
    data = resp.json()
    src = data.get("source") if isinstance(data, dict) else None
    if not src:
        raise RuntimeError(f"upload response missing 'source': {data!r}")
    return src


def list_packs(client: httpx.Client, group: str) -> Any:
    resp = client.get(_base(group))
    resp.raise_for_status()
    return resp.json()


def get_pack(client: httpx.Client, group: str, pack_id: str) -> Any:
    resp = client.get(f"{_base(group)}/{pack_id}")
    resp.raise_for_status()
    return resp.json()


def create_pack(client: httpx.Client, group: str, data: dict) -> Any:
    resp = client.post(_base(group), json=data)
    resp.raise_for_status()
    return resp.json()


def update_pack(client: httpx.Client, group: str, pack_id: str, data: dict) -> Any:
    resp = client.patch(f"{_base(group)}/{pack_id}", json=data)
    resp.raise_for_status()
    return resp.json()


def delete_pack(client: httpx.Client, group: str, pack_id: str) -> Any:
    resp = client.delete(f"{_base(group)}/{pack_id}")
    resp.raise_for_status()
    return resp.json()


def export_pack(client: httpx.Client, group: str, pack_id: str, mode: str) -> bytes:
    resp = client.get(f"{_base(group)}/{pack_id}/export", params={"mode": mode})
    resp.raise_for_status()
    return resp.content


def install_pack(
    client: httpx.Client, group: str, source: str, version: str | None = None
) -> Any:
    """Install a pack from a local .crbl, a URL, or a Dispensary pack ID.

    Resolution is layered: an existing file is uploaded; anything containing a
    scheme is treated as a URL; otherwise `source` is resolved as a Dispensary
    pack ID into a download URL.
    """
    if os.path.isfile(source):
        source = _upload_local_pack(client, group, source)
    elif "://" not in source:
        source = resolve_dispensary_source(source, version)
    resp = client.post(_base(group), json={"source": source})
    resp.raise_for_status()
    return resp.json()


def upgrade_pack(
    client: httpx.Client, group: str, pack_id: str, source: str, mode: str
) -> Any:
    if os.path.isfile(source):
        source = _upload_local_pack(client, group, source)
    resp = client.patch(
        f"{_base(group)}/{pack_id}", json={"source": source, "mode": mode}
    )
    resp.raise_for_status()
    return resp.json()
