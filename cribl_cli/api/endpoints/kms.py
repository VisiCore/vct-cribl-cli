"""Key Management Service (KMS) configuration and health."""
from __future__ import annotations

from typing import Any

import httpx


def get_kms_config(client: httpx.Client, group: str) -> Any:
    """Get KMS configuration for a worker group."""
    resp = client.get(f"/api/v1/m/{group}/system/kms")
    resp.raise_for_status()
    return resp.json()


def update_kms_config(client: httpx.Client, group: str, data: dict[str, Any]) -> Any:
    """Update KMS configuration for a worker group."""
    resp = client.patch(f"/api/v1/m/{group}/system/kms", json=data)
    resp.raise_for_status()
    return resp.json()


def get_kms_health(client: httpx.Client, group: str) -> Any:
    """Get KMS health status for a worker group."""
    resp = client.get(f"/api/v1/m/{group}/system/kms/health")
    resp.raise_for_status()
    return resp.json()
