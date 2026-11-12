"""Resolve worker group from API when not explicitly provided."""

from __future__ import annotations

import httpx


def resolve_group(
    client: httpx.Client, group: str | None = None, *, write: bool = False
) -> str:
    """Return the worker group to act on.

    An explicit *group* is always used as-is. Without one, read commands fall
    back to the first group the API lists. Commands that change something pass
    ``write=True``: they only fall back when there is exactly one group, and
    otherwise fail, so a forgotten ``-g`` can never send a change to whichever
    group happens to be listed first.
    """
    if group:
        return group
    resp = client.get("/api/v1/master/groups")
    resp.raise_for_status()
    data = resp.json()
    items = data.get("items", [])
    if write and len(items) > 1:
        ids = ", ".join(str(g.get("id", "?")) for g in items if isinstance(g, dict))
        raise ValueError(
            f"No worker group given and {len(items)} exist ({ids}). "
            "Pass -g/--group to choose the group this change applies to."
        )
    if items:
        return items[0].get("id", "default")
    return "default"
