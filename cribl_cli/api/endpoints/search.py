"""Search job management endpoints."""
from __future__ import annotations

from typing import Any

import httpx


def _base(group: str) -> str:
    return f"/api/v1/m/{group}/search/jobs"


def run_search(client: httpx.Client, group: str, data: dict[str, Any]) -> Any:
    """Submit a new search job."""
    resp = client.post(_base(group), json=data)
    resp.raise_for_status()
    return resp.json()


def get_search_status(client: httpx.Client, group: str, job_id: str) -> Any:
    """Get the status of a search job."""
    resp = client.get(f"{_base(group)}/{job_id}")
    resp.raise_for_status()
    return resp.json()


def get_search_results(client: httpx.Client, group: str, job_id: str) -> Any:
    """Get the results of a completed search job.

    The results endpoint returns NDJSON (newline-delimited JSON).
    The first line is job metadata; subsequent lines are result rows.
    """
    import json as _json
    resp = client.get(f"{_base(group)}/{job_id}/results")
    resp.raise_for_status()
    lines = resp.text.strip().split("\n")
    parsed = [_json.loads(line) for line in lines if line.strip()]
    if not parsed:
        return {"items": []}
    # First line is metadata, rest are results
    meta = parsed[0]
    results = parsed[1:]
    return {"meta": meta, "items": results}


def get_search_timeline(client: httpx.Client, group: str, job_id: str) -> Any:
    """Get the timeline for a search job."""
    resp = client.get(f"{_base(group)}/{job_id}/timeline")
    resp.raise_for_status()
    return resp.json()


def get_search_field_summary(
    client: httpx.Client, group: str, job_id: str
) -> Any:
    """Get the field summary for a search job."""
    resp = client.get(f"{_base(group)}/{job_id}/field-summary")
    resp.raise_for_status()
    return resp.json()


def get_search_logs(client: httpx.Client, group: str, job_id: str) -> Any:
    """Get logs for a search job."""
    resp = client.get(f"{_base(group)}/{job_id}/logs")
    resp.raise_for_status()
    return resp.json()


def get_search_metrics(client: httpx.Client, group: str, job_id: str) -> Any:
    """Get metrics for a search job."""
    resp = client.get(f"{_base(group)}/{job_id}/metrics")
    resp.raise_for_status()
    return resp.json()


def get_search_diag(client: httpx.Client, group: str, job_id: str) -> Any:
    """Get diagnostics for a search job."""
    resp = client.get(f"{_base(group)}/{job_id}/diag")
    resp.raise_for_status()
    return resp.json()
