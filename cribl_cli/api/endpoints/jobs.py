"""Job and collector management endpoints."""
from __future__ import annotations

from typing import Any

import httpx


def _base(group: str) -> str:
    return f"/api/v1/m/{group}/jobs"


def list_jobs(client: httpx.Client, group: str) -> Any:
    """List all jobs in a worker group."""
    resp = client.get(_base(group))
    resp.raise_for_status()
    return resp.json()


def get_job(client: httpx.Client, group: str, job_id: str) -> Any:
    """Get a specific job by ID."""
    resp = client.get(f"{_base(group)}/{job_id}")
    resp.raise_for_status()
    return resp.json()


def run_job(client: httpx.Client, group: str, job_id: str, mode: str = "run") -> Any:
    """Start a run of a saved collector (a config under lib/jobs).

    A run is a new job: ``POST /jobs`` naming the saved config. The body must
    carry ``type`` and ``run`` as well as the id (a bare ``{"id": ...}`` is
    rejected), so the config's type is read first.
    """
    cfg = client.get(f"/api/v1/m/{group}/lib/jobs/{job_id}")
    cfg.raise_for_status()
    data = cfg.json()
    items = data.get("items") if isinstance(data, dict) else None
    saved = items[0] if items else (data if isinstance(data, dict) else {})
    body = {"id": job_id, "type": saved.get("type", "collection"), "run": {"mode": mode}}
    resp = client.post(_base(group), json=body)
    resp.raise_for_status()
    return resp.json()


def cancel_job(client: httpx.Client, group: str, job_id: str) -> Any:
    """Cancel a running job."""
    resp = client.patch(f"{_base(group)}/{job_id}/cancel")
    resp.raise_for_status()
    return resp.json()


def pause_job(client: httpx.Client, group: str, job_id: str) -> Any:
    """Pause a running job."""
    resp = client.patch(f"{_base(group)}/{job_id}/pause")
    resp.raise_for_status()
    return resp.json()


def resume_job(client: httpx.Client, group: str, job_id: str) -> Any:
    """Resume a paused job."""
    resp = client.patch(f"{_base(group)}/{job_id}/resume")
    resp.raise_for_status()
    return resp.json()


def list_job_configs(client: httpx.Client, group: str) -> Any:
    """List all collector (job) configurations in a worker group."""
    # /lib/jobs holds the collectors a user has configured (what the UI lists
    # under Sources > Collectors). /collectors only lists the collector types.
    resp = client.get(f"/api/v1/m/{group}/lib/jobs")
    resp.raise_for_status()
    return resp.json()
