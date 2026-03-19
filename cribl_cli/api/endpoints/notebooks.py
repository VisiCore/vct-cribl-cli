"""Search notebook management endpoints."""
from __future__ import annotations

import uuid
from typing import Any

import httpx


def _base(group: str) -> str:
    return f"/api/v1/m/{group}/search/notebooks"


def list_notebooks(client: httpx.Client, group: str) -> Any:
    """List all notebooks in a worker group."""
    resp = client.get(_base(group))
    resp.raise_for_status()
    return resp.json()


def get_notebook(client: httpx.Client, group: str, notebook_id: str) -> Any:
    """Get a specific notebook by ID."""
    resp = client.get(f"{_base(group)}/{notebook_id}")
    resp.raise_for_status()
    return resp.json()


def create_notebook(
    client: httpx.Client, group: str, data: dict[str, Any]
) -> Any:
    """Create a new notebook.

    Generates a UUID for the notebook if ``id`` is not already present
    in the provided data.
    """
    if "id" not in data:
        data = {**data, "id": str(uuid.uuid4())}
    resp = client.post(_base(group), json=data)
    resp.raise_for_status()
    return resp.json()


def add_notebook_query(
    client: httpx.Client,
    group: str,
    notebook_id: str,
    query_data: dict[str, Any],
) -> Any:
    """Add a query section to an existing notebook.

    Fetches the notebook, appends a new query section, and PATCHes it back.
    """
    # Get existing notebook
    resp = client.get(f"{_base(group)}/{notebook_id}")
    resp.raise_for_status()
    notebook = resp.json()

    # Unwrap if wrapped in items
    if "items" in notebook and isinstance(notebook["items"], list):
        notebook = notebook["items"][0]

    # Build a query section
    import time as _time
    now = int(_time.time() * 1000)
    section = {
        "id": f"section-{uuid.uuid4()}",
        "type": "query.default",
        "variant": "query",
        "info": {"created": now, "modified": now},
        "config": query_data,
    }

    sections = notebook.get("sections", [])
    sections.append(section)
    notebook["sections"] = sections

    resp = client.patch(f"{_base(group)}/{notebook_id}", json=notebook)
    resp.raise_for_status()
    return resp.json()


def delete_notebook(client: httpx.Client, group: str, notebook_id: str) -> Any:
    """Delete a notebook by ID."""
    resp = client.delete(f"{_base(group)}/{notebook_id}")
    resp.raise_for_status()
    return resp.json()
