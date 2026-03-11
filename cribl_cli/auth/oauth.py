"""OAuth2 token management for Cribl Cloud and local auth."""

from __future__ import annotations

import time

import httpx

from cribl_cli.config.types import CriblConfig

_cached_token: dict | None = None  # {"token": str, "expires_at": float}


def clear_token_cache() -> None:
    global _cached_token
    _cached_token = None


def get_access_token(config: CriblConfig) -> str:
    global _cached_token
    if _cached_token and time.time() < _cached_token["expires_at"] - 60:
        return _cached_token["token"]

    if config.auth_type == "cloud":
        token, expires_in = _get_cloud_token(config)
    else:
        token, expires_in = _get_local_token(config)

    _cached_token = {"token": token, "expires_at": time.time() + expires_in}
    return token


def _get_cloud_token(config: CriblConfig) -> tuple[str, int]:
    resp = httpx.post(
        "https://login.cribl.cloud/oauth/token",
        json={
            "grant_type": "client_credentials",
            "client_id": config.client_id,
            "client_secret": config.client_secret,
            "audience": "https://api.cribl.cloud",
        },
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    return data["access_token"], data.get("expires_in", 3600)


def _get_local_token(config: CriblConfig) -> tuple[str, int]:
    resp = httpx.post(
        f"{config.base_url}/api/v1/auth/login",
        json={
            "username": config.username,
            "password": config.password,
        },
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    return data["token"], data.get("expiresIn", 3600)
