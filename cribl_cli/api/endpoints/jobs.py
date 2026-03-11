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


def run_job(client: httpx.Client, group: str, job_id: str) -> Any:
    """Run (trigger) an existing job by its collector config ID."""
    resp = client.post(f"{_base(group)}/{job_id}/run")
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
    resp = client.get(f"/api/v1/m/{group}/collectors")
    resp.raise_for_status()
    return resp.json()
