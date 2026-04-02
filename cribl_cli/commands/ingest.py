"""Daily ingest dashboard — replicates the Workspace Home 'Daily Ingest' panels."""
from __future__ import annotations

import json as _json
import math
import time
from typing import Any

import click

from cribl_cli.api.client import get_client
from cribl_cli.api.endpoints.metrics import query_metrics
from cribl_cli.output.formatter import format_output
from cribl_cli.utils.errors import handle_error


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _format_count(n: float) -> str:
    """Human-friendly count: 1234567 -> 1.23M."""
    if n >= 1_000_000_000:
        return f"{n / 1_000_000_000:.1f}B"
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return str(int(n))


def _format_bytes(n: float) -> str:
    """Human-friendly bytes."""
    if n == 0:
        return "0 B"
    units = ["B", "KB", "MB", "GB", "TB"]
    i = int(min(len(units) - 1, math.log(abs(n), 1024)))
    return f"{n / (1024 ** i):.1f} {units[i]}"


def _pct_diff(a: float, b: float) -> str:
    """Percentage difference string."""
    if a == 0:
        return "N/A"
    pct = ((b - a) / a) * 100
    arrow = "+" if pct >= 0 else ""
    return f"{arrow}{pct:.2f}%"


def _build_totals_query(where: str, earliest: str = "86400s") -> dict[str, Any]:
    """Build a cumulative totals query (for the bar chart / counters)."""
    now_ms = int(time.time() * 1000)
    return {
        "where": where,
        "aggs": {
            "aggregations": [
                'sum("total.in_events").as("eventsIn")',
                'sum("total.out_events").as("eventsOut")',
                'sum("total.in_bytes").as("bytesIn")',
                'sum("total.out_bytes").as("bytesOut")',
            ],
            "cumulative": True,
        },
        "earliest": earliest,
        "latest": now_ms,
    }


def _build_counter_query(where: str, earliest: str = "86400s") -> dict[str, Any]:
    """Build a counter query (single aggregate, no time bucketing)."""
    now_ms = int(time.time() * 1000)
    return {
        "aggs": {
            "aggregations": [
                'sum("total.in_bytes").as("bytesIn")',
                'sum("total.out_bytes").as("bytesOut")',
                'sum("total.in_events").as("eventsIn")',
                'sum("total.out_events").as("eventsOut")',
            ],
            "timeWindowSeconds": -1,
        },
        "earliest": earliest,
        "latest": now_ms,
        "where": where,
    }


def _extract_counters(data: Any) -> dict[str, float]:
    """Sum metric values across all time buckets in a metrics response.

    The API returns ``{"results": [{"eventsIn": ..., ...}, ...]}`` with one
    entry per time window.  We sum across all buckets to get the daily totals.
    """
    results = []
    if isinstance(data, dict):
        results = data.get("results", data.get("items", []))
    elif isinstance(data, list):
        results = data

    events_in = 0.0
    events_out = 0.0
    bytes_in = 0.0
    bytes_out = 0.0
    for item in results:
        if isinstance(item, dict):
            events_in += item.get("eventsIn", 0) or 0
            events_out += item.get("eventsOut", 0) or 0
            bytes_in += item.get("bytesIn", 0) or 0
            bytes_out += item.get("bytesOut", 0) or 0
    return {
        "eventsIn": events_in,
        "eventsOut": events_out,
        "bytesIn": bytes_in,
        "bytesOut": bytes_out,
    }


# ---------------------------------------------------------------------------
# Command group
# ---------------------------------------------------------------------------

@click.group("ingest", help="Daily ingest dashboard and metrics.")
def ingest_group():
    pass


@ingest_group.command("dashboard", help="Show Daily Ingest dashboard (replicates Workspace Home panels).")
@click.option("--hours", default=24, type=int, help="Lookback window in hours (default: 24).")
@click.option("--json", "as_json", is_flag=True, help="Output as structured JSON.")
@click.option("--table", "use_table", is_flag=True, help="Output as table.")
def ingest_dashboard(hours, as_json, use_table):
    """Replicate the Daily Ingest dashboard panels from Workspace Home."""
    try:
        client = get_client()
        earliest = f"{hours * 3600}s"

        # --- Stream worker totals ---
        stream_query = _build_counter_query(
            '(has_no_dimensions) && (__dist_mode=="worker")', earliest
        )
        stream_data = query_metrics(client, stream_query)
        stream = _extract_counters(stream_data)

        # --- Edge totals ---
        edge_query = _build_counter_query(
            '(has_no_dimensions) && (__dist_mode=="managed-edge")', earliest
        )
        edge_data = query_metrics(client, edge_query)
        edge = _extract_counters(edge_data)

        # --- Search worker totals ---
        search_query = _build_counter_query(
            '(__dist_mode=="worker") && (__worker_group=="search")', earliest
        )
        search_data = query_metrics(client, search_query)
        search = _extract_counters(search_data)

        # --- Aggregate totals across all sources ---
        total_events_in = stream["eventsIn"] + edge["eventsIn"] + search["eventsIn"]
        total_events_out = stream["eventsOut"] + edge["eventsOut"] + search["eventsOut"]
        total_bytes_in = stream["bytesIn"] + edge["bytesIn"] + search["bytesIn"]
        total_bytes_out = stream["bytesOut"] + edge["bytesOut"] + search["bytesOut"]

        events_diff = total_events_out - total_events_in
        bytes_diff = total_bytes_out - total_bytes_in

        report = {
            "period_hours": hours,
            "totals": {
                "events_in": total_events_in,
                "events_out": total_events_out,
                "events_difference": events_diff,
                "events_difference_pct": _pct_diff(total_events_in, total_events_out),
                "bytes_in": total_bytes_in,
                "bytes_out": total_bytes_out,
                "bytes_difference": bytes_diff,
                "bytes_difference_pct": _pct_diff(total_bytes_in, total_bytes_out),
            },
            "breakdown": {
                "stream": {
                    "events_in": stream["eventsIn"],
                    "events_out": stream["eventsOut"],
                    "bytes_in": stream["bytesIn"],
                    "bytes_out": stream["bytesOut"],
                },
                "edge": {
                    "events_in": edge["eventsIn"],
                    "events_out": edge["eventsOut"],
                    "bytes_in": edge["bytesIn"],
                    "bytes_out": edge["bytesOut"],
                },
                "search": {
                    "events_in": search["eventsIn"],
                    "events_out": search["eventsOut"],
                    "bytes_in": search["bytesIn"],
                    "bytes_out": search["bytesOut"],
                },
            },
        }

        if as_json:
            click.echo(_json.dumps(report, indent=2))
            return

        if use_table:
            rows = [
                {
                    "source": "Stream",
                    "events_in": _format_count(stream["eventsIn"]),
                    "events_out": _format_count(stream["eventsOut"]),
                    "bytes_in": _format_bytes(stream["bytesIn"]),
                    "bytes_out": _format_bytes(stream["bytesOut"]),
                },
                {
                    "source": "Edge",
                    "events_in": _format_count(edge["eventsIn"]),
                    "events_out": _format_count(edge["eventsOut"]),
                    "bytes_in": _format_bytes(edge["bytesIn"]),
                    "bytes_out": _format_bytes(edge["bytesOut"]),
                },
                {
                    "source": "Search",
                    "events_in": _format_count(search["eventsIn"]),
                    "events_out": _format_count(search["eventsOut"]),
                    "bytes_in": _format_bytes(search["bytesIn"]),
                    "bytes_out": _format_bytes(search["bytesOut"]),
                },
            ]
            click.echo(format_output(rows, table=True))
            return

        # Default: human-readable text report
        lines: list[str] = []
        lines.append(f"Daily Ingest Dashboard — last {hours}h")
        lines.append("=" * 60)
        lines.append("")

        lines.append("--- Totals " + "-" * 49)
        lines.append(f"  Events In:     {_format_count(total_events_in):>12}")
        lines.append(f"  Events Out:    {_format_count(total_events_out):>12}")
        lines.append(f"  Events Diff:   {_format_count(abs(events_diff)):>12}  ({_pct_diff(total_events_in, total_events_out)})")
        lines.append(f"  Bytes In:      {_format_bytes(total_bytes_in):>12}")
        lines.append(f"  Bytes Out:     {_format_bytes(total_bytes_out):>12}")
        lines.append(f"  Bytes Diff:    {_format_bytes(abs(bytes_diff)):>12}  ({_pct_diff(total_bytes_in, total_bytes_out)})")

        lines.append("")
        lines.append("--- Breakdown by Source " + "-" * 37)
        hdr = f"  {'SOURCE':<12} {'EVENTS IN':>12} {'EVENTS OUT':>12} {'BYTES IN':>12} {'BYTES OUT':>12}"
        lines.append(hdr)
        for label, counters in [("Stream", stream), ("Edge", edge), ("Search", search)]:
            lines.append(
                f"  {label:<12} "
                f"{_format_count(counters['eventsIn']):>12} "
                f"{_format_count(counters['eventsOut']):>12} "
                f"{_format_bytes(counters['bytesIn']):>12} "
                f"{_format_bytes(counters['bytesOut']):>12}"
            )

        lines.append("")
        click.echo("\n".join(lines))

    except Exception as e:
        handle_error(e)


@ingest_group.command("query", help="Run a raw metrics query against /api/v1/system/metrics/query.")
@click.argument("json_body")
@click.option("--table", "use_table", is_flag=True, help="Output as table.")
def ingest_query(json_body, use_table):
    """Submit a raw metric query. JSON_BODY is the query payload as a JSON string."""
    try:
        client = get_client()
        payload = _json.loads(json_body)
        data = query_metrics(client, payload)
        click.echo(format_output(data, table=use_table))
    except _json.JSONDecodeError as e:
        raise click.BadParameter(f"Invalid JSON: {e}") from e
    except Exception as e:
        handle_error(e)
