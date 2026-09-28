"""Cribl App Platform endpoints (`/api/v1/apps`).

Apps are global (not group-scoped). Installing from a local package is a two-step
flow: `PUT /apps?filename=...` stages the archive and returns a `source` token,
then `POST /apps` with that token installs it. URLs (`.tgz`, `.crbl`, `.tar.gz`)
and `git+` repository references are passed to `POST /apps` directly.
"""
from __future__ import annotations

import os
from typing import Any

import httpx

_BASE = "/api/v1/apps"

_ARCHIVE_SUFFIXES = (".tgz", ".tar.gz", ".crbl")


def _is_remote_source(source: str) -> bool:
    return source.startswith(("http://", "https://", "git+"))


def _upload_local_app(client: httpx.Client, path: str) -> str:
    """PUT a local app archive to /apps?filename=... and return the staged source token."""
    with open(path, "rb") as f:
        body = f.read()
    resp = client.put(
        _BASE,
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


def resolve_app_source(client: httpx.Client, source: str) -> str:
    """Turn a local archive path, URL, or `git+` reference into a `source` value for the API."""
    if _is_remote_source(source):
        return source
    if os.path.isfile(source):
        return _upload_local_app(client, source)
    if source.endswith(_ARCHIVE_SUFFIXES):
        raise FileNotFoundError(f"app package not found: {source}")
    raise ValueError(
        f"unrecognized app source {source!r}: expected a local .tgz/.crbl path, an https:// URL, or git+<repo>"
    )


def list_apps(client: httpx.Client) -> Any:
    resp = client.get(_BASE)
    resp.raise_for_status()
    return resp.json()


def get_app(client: httpx.Client, app_id: str) -> Any:
    resp = client.get(f"{_BASE}/{app_id}")
    resp.raise_for_status()
    return resp.json()


def install_app(
    client: httpx.Client,
    source: str,
    app_id: str | None = None,
    spec: str | None = None,
) -> Any:
    body: dict[str, Any] = {"source": resolve_app_source(client, source)}
    if app_id:
        body["id"] = app_id
    if spec:
        body["spec"] = spec
    resp = client.post(_BASE, json=body)
    resp.raise_for_status()
    return resp.json()


def upgrade_app(
    client: httpx.Client,
    app_id: str,
    source: str,
    spec: str | None = None,
    minor: bool = False,
) -> Any:
    body: dict[str, Any] = {"source": resolve_app_source(client, source)}
    if spec:
        body["spec"] = spec
    if minor:
        body["minor"] = True
    resp = client.patch(f"{_BASE}/{app_id}", json=body)
    resp.raise_for_status()
    return resp.json()


def uninstall_app(client: httpx.Client, app_id: str) -> Any:
    resp = client.delete(f"{_BASE}/{app_id}")
    resp.raise_for_status()
    return resp.json()


def preinstall_check(client: httpx.Client, source: str, spec: str | None = None) -> Any:
    body: dict[str, Any] = {"source": resolve_app_source(client, source)}
    if spec:
        body["spec"] = spec
    resp = client.post(f"{_BASE}/preinstall-check", json=body)
    resp.raise_for_status()
    return resp.json()


def get_backend_status(client: httpx.Client, app_id: str) -> Any:
    resp = client.get(f"{_BASE}/{app_id}/backend/status")
    resp.raise_for_status()
    return resp.json()


def list_backend_endpoints(client: httpx.Client, app_id: str) -> Any:
    resp = client.get(f"{_BASE}/{app_id}/backend/endpoints")
    resp.raise_for_status()
    return resp.json()


def redeploy_backend(client: httpx.Client, app_id: str) -> Any:
    resp = client.post(f"{_BASE}/{app_id}/backend/redeploy")
    resp.raise_for_status()
    return resp.json()


def list_app_proxies(client: httpx.Client, app_id: str) -> Any:
    resp = client.get(f"{_BASE}/{app_id}/proxies")
    resp.raise_for_status()
    return resp.json()


def list_app_policies(client: httpx.Client, app_id: str) -> Any:
    resp = client.get(f"{_BASE}/{app_id}/policies")
    resp.raise_for_status()
    return resp.json()


def invoke_endpoint(
    client: httpx.Client,
    app_id: str,
    endpoint: str,
    method: str = "GET",
    body: dict | None = None,
    query: dict[str, str] | None = None,
) -> httpx.Response:
    """Call a deployed backend endpoint (`/api/v1/a/{appId}/endpoints/{name}`) and return the raw response."""
    url = f"/api/v1/a/{app_id}/endpoints/{endpoint}"
    resp = client.request(method.upper(), url, json=body, params=query or None)
    resp.raise_for_status()
    return resp
