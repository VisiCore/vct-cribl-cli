"""System metrics endpoints."""
from __future__ import annotations

from typing import Any

import httpx


def get_metrics(
    client: httpx.Client,
    *,
    name: str | None = None,
    filter_expr: str | None = None,
    earliest: str | None = None,
    latest: str | None = None,
    buckets: int | None = None,
) -> httpx.Response:
    """Fetch the raw metrics store (every series). Returns the response so the
    caller can save a very large body straight to a file.

    Parameter names are the documented ones: ``metricNameFilter``,
    ``filterExpr``, ``earliest``, ``latest``, ``numBuckets``.
    """
    params: dict[str, Any] = {}
    if name is not None:
        params["metricNameFilter"] = name
    if filter_expr is not None:
        params["filterExpr"] = filter_expr
    if earliest is not None:
        params["earliest"] = earliest
    if latest is not None:
        params["latest"] = latest
    if buckets is not None:
        params["numBuckets"] = buckets
    resp = client.get("/api/v1/system/metrics", params=params)
    resp.raise_for_status()
    return resp


def build_metrics_query(
    aggregations: list[str],
    *,
    where: str | None = None,
    split_by: list[str] | None = None,
    earliest_seconds: int = 900,
    window_seconds: int | None = None,
) -> dict[str, Any]:
    """Body for ``POST /system/metrics/query``.

    Without ``window_seconds`` the result is one cumulative row per split
    value; with it, one row per time window. ``earliest`` is sent as
    ``"<n>s"``, the relative form this endpoint returns data for.
    """
    aggs: dict[str, Any] = {"aggregations": list(aggregations)}
    if window_seconds:
        aggs["timeWindowSeconds"] = window_seconds
    else:
        aggs["cumulative"] = True
    if split_by:
        aggs["splitBys"] = list(split_by)
    payload: dict[str, Any] = {"aggs": aggs, "earliest": f"{earliest_seconds}s"}
    if where:
        payload["where"] = where
    return payload


def query_metrics(client: httpx.Client, payload: dict[str, Any]) -> Any:
    """POST a metric query to /api/v1/system/metrics/query.

    Args:
        client: An authenticated httpx client.
        payload: Query body with ``where``, ``aggs``, ``earliest``, ``latest``.
    """
    resp = client.post("/api/v1/system/metrics/query", json=payload)
    resp.raise_for_status()
    return resp.json()
