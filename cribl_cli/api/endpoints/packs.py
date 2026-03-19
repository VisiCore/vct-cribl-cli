"""Pack management endpoints."""
from __future__ import annotations

from typing import Any

import httpx


def _base(group: str) -> str:
    return f"/api/v1/m/{group}/packs"


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


def install_pack(client: httpx.Client, group: str, source: str) -> Any:
    resp = client.post(_base(group), json={"source": source})
    resp.raise_for_status()
    return resp.json()


def upgrade_pack(
    client: httpx.Client, group: str, pack_id: str, source: str, mode: str
) -> Any:
    resp = client.patch(
        f"{_base(group)}/{pack_id}", json={"source": source, "mode": mode}
    )
    resp.raise_for_status()
    return resp.json()
