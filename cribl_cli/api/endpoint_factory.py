"""Generic CRUD endpoint factory for Cribl API resources."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

import httpx

from cribl_cli.utils.group_resolver import resolve_group

Scope = Literal["group", "global", "search", "lake"]


@dataclass
class EndpointConfig:
    scope: Scope
    path: str
    singleton: bool = False


def _build_base_url(scope: Scope, path: str, group: str) -> str:
    if scope == "global":
        return f"/api/v1/{path}"
    if scope == "search":
        return f"/api/v1/m/{group}/search/{path}"
    if scope == "lake":
        return f"/api/v1/products/lake/lakes/{group}/{path}"
    # group scope
    return f"/api/v1/m/{group}/{path}"


def resolve_group_for_scope(
    client: httpx.Client, scope: Scope, group: str | None = None
) -> str:
    if scope == "global":
        return "_global_"
    if scope == "search":
        return group or "default_search"
    if scope == "lake":
        return group or ""
    return resolve_group(client, group)


class Endpoints:
    """Generic CRUD operations for a Cribl API resource."""

    def __init__(self, config: EndpointConfig) -> None:
        self._config = config

    def list(self, client: httpx.Client, group: str, **params: Any) -> Any:
        url = _build_base_url(self._config.scope, self._config.path, group)
        resp = client.get(url, params=params or None)
        resp.raise_for_status()
        return resp.json()

    def get(self, client: httpx.Client, group: str, resource_id: str) -> Any:
        if self._config.singleton:
            url = _build_base_url(self._config.scope, self._config.path, group)
        else:
            url = f"{_build_base_url(self._config.scope, self._config.path, group)}/{resource_id}"
        resp = client.get(url)
        resp.raise_for_status()
        return resp.json()

    def create(self, client: httpx.Client, group: str, data: dict) -> Any:
        url = _build_base_url(self._config.scope, self._config.path, group)
        resp = client.post(url, json=data)
        resp.raise_for_status()
        return resp.json()

    def update(
        self, client: httpx.Client, group: str, resource_id: str, data: dict
    ) -> Any:
        if self._config.singleton:
            url = _build_base_url(self._config.scope, self._config.path, group)
        else:
            url = f"{_build_base_url(self._config.scope, self._config.path, group)}/{resource_id}"
        resp = client.patch(url, json=data)
        resp.raise_for_status()
        return resp.json()

    def delete(self, client: httpx.Client, group: str, resource_id: str) -> Any:
        url = f"{_build_base_url(self._config.scope, self._config.path, group)}/{resource_id}"
        resp = client.delete(url)
        resp.raise_for_status()
        return resp.json()


def create_endpoints(config: EndpointConfig) -> Endpoints:
    return Endpoints(config)
