"""Lookup file content: download the file, and upload a new one.

The CRUD endpoints for the lookup *object* come from the endpoint factory
(``system/lookups``). These cover the file itself, which the API handles
separately: the content is read from ``/content`` and a new file is first
staged with a PUT, then attached to the lookup object.
"""
from __future__ import annotations

from typing import Any
from urllib.parse import quote

import httpx

from cribl_cli.utils.validation import merge_update


def _content_type(filename: str) -> str:
    return "text/csv" if filename.lower().endswith(".csv") else "application/octet-stream"


def download_lookup(client: httpx.Client, group: str, lookup_id: str) -> bytes:
    """Return the lookup file's bytes exactly as stored.

    ``raw=true`` matters: without it the endpoint returns the rows as paginated
    JSON, not the file.
    """
    resp = client.get(
        f"/api/v1/m/{group}/system/lookups/{quote(lookup_id, safe='')}/content",
        params={"raw": "true"},
    )
    resp.raise_for_status()
    return resp.content


def stage_lookup_file(client: httpx.Client, group: str, filename: str, content: bytes) -> dict[str, Any]:
    """Upload file bytes to a temporary file; returns ``{filename, rows, size}``."""
    resp = client.put(
        f"/api/v1/m/{group}/system/lookups",
        params={"filename": filename},
        content=content,
        headers={"Content-Type": _content_type(filename)},
    )
    resp.raise_for_status()
    return resp.json()


def upload_lookup(
    client: httpx.Client, group: str, lookup_id: str, content: bytes
) -> dict[str, Any]:
    """Create the lookup, or replace its file if it already exists.

    Returns ``{"action": "created"|"updated", "staged": {...}, "lookup": {...}}``.
    """
    # Looked up before staging so a dry run shows the staging PUT as its first write.
    base = f"/api/v1/m/{group}/system/lookups"
    one = f"/api/v1/m/{group}/system/lookups/{quote(lookup_id, safe='')}"
    current = client.get(one)
    existing = None
    if current.status_code != 404:
        current.raise_for_status()
        items = current.json().get("items") or []
        existing = items[0] if items else None

    staged = stage_lookup_file(client, group, lookup_id, content)
    file_info = {"filename": staged["filename"]}
    if existing is None:
        resp = client.post(base, json={"id": lookup_id, "fileInfo": file_info})
        action = "created"
    else:
        resp = client.patch(one, json=merge_update(existing, {"fileInfo": file_info}))
        action = "updated"
    resp.raise_for_status()
    items = resp.json().get("items") or []
    return {"action": action, "staged": staged, "lookup": items[0] if items else resp.json()}
