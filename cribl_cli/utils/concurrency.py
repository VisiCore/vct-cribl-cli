"""Run per-node API calls concurrently."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, Iterable

# Enough to cover a typical fleet in one pass without hammering the leader.
DEFAULT_WORKERS = 8


def map_concurrent(
    fn: Callable[[Any], Any], items: Iterable[Any], max_workers: int = DEFAULT_WORKERS
) -> list[tuple[Any, Any, Exception | None]]:
    """Call ``fn(item)`` for every item on a thread pool.

    Returns ``(item, result, error)`` tuples in the same order as *items*.
    A failing call never aborts the others: its exception is returned in the
    tuple (with ``result`` None) so the caller can report it per item.
    The shared ``httpx.Client`` is thread-safe, so *fn* may use it directly.
    """
    items = list(items)
    if not items:
        return []

    def _call(item: Any) -> tuple[Any, Any, Exception | None]:
        try:
            return item, fn(item), None
        except Exception as exc:  # noqa: BLE001 — reported per item by the caller
            return item, None, exc

    with ThreadPoolExecutor(max_workers=min(max_workers, len(items))) as pool:
        return list(pool.map(_call, items))
