"""HTTP client with auth interceptor and dry-run support."""

from __future__ import annotations

import json
import sys
from typing import Any

import httpx

from cribl_cli.auth.oauth import get_access_token
from cribl_cli.config.types import CriblConfig
from cribl_cli.utils.errors import DryRunAbort

_client: httpx.Client | None = None
_config_error: str | None = None


class AuthTransport(httpx.BaseTransport):
    """Transport wrapper that injects Bearer token into every request."""

    def __init__(self, transport: httpx.BaseTransport, config: CriblConfig) -> None:
        self._transport = transport
        self._config = config

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        token = get_access_token(self._config)
        request.headers["Authorization"] = f"Bearer {token}"
        return self._transport.handle_request(request)


class DryRunTransport(httpx.BaseTransport):
    """Transport that logs the request and aborts instead of sending."""

    def __init__(self, transport: httpx.BaseTransport) -> None:
        self._transport = transport

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        body: Any = None
        if request.content:
            try:
                body = json.loads(request.content)
            except (json.JSONDecodeError, UnicodeDecodeError):
                body = request.content.decode("utf-8", errors="replace")

        info = {
            "dry_run": True,
            "method": request.method,
            "url": str(request.url),
            "headers": dict(request.headers),
            "body": body,
        }
        sys.stderr.write(json.dumps(info, indent=2) + "\n")
        raise DryRunAbort()


def create_client(
    config: CriblConfig,
    *,
    dry_run: bool = False,
    verbose: bool = False,
) -> httpx.Client:
    transport: httpx.BaseTransport = httpx.HTTPTransport()
    transport = AuthTransport(transport, config)
    if dry_run:
        transport = DryRunTransport(transport)

    client = httpx.Client(
        base_url=config.base_url,
        transport=transport,
        timeout=30.0,
        event_hooks={
            "request": [_log_request] if verbose else [],
        },
    )
    return client


def _log_request(request: httpx.Request) -> None:
    sys.stderr.write(f">> {request.method} {request.url}\n")


def get_client() -> httpx.Client:
    if _client is None:
        if _config_error:
            raise RuntimeError(_config_error)
        raise RuntimeError("API client not initialized")
    return _client


def set_client(client: httpx.Client) -> None:
    global _client
    _client = client


def set_config_error(msg: str) -> None:
    global _config_error
    _config_error = msg
