"""FinOps commands — credit consumption tracking and license utilization."""
from __future__ import annotations

import json as _json
import math
from datetime import datetime, timezone
from typing import Any

import click

from cribl_cli.api.client import get_client
from cribl_cli.api.endpoints.license_usage import get_license_usage
from cribl_cli.output.formatter import format_output
from cribl_cli.utils.errors import handle_error


def _format_bytes(n: float) -> str:
    if n == 0:
        return "0 B"
    units = ["B", "KB", "MB", "GB", "TB"]
    i = int(min(len(units) - 1, math.log(abs(n), 1024)))
    return f"{n / (1024 ** i):.1f} {units[i]}"


def _get_license_quota(client) -> float:
    """Fetch license quota in GB/day."""
    resp = client.get("/api/v1/system/licenses")
    resp.raise_for_status()
    data = resp.json()
    items = data.get("items", [])
    for lic in items:
        quota = lic.get("quota", 0)
        if quota > 0:
            return float(quota)
    return 0.0


def _build_summary(items: list[dict], quota_gb_day: float) -> dict[str, Any]:
    """Build consumption summary from daily license-usage records."""
    if not items:
        return {}

    total_in = sum(i.get("inBytes", 0) for i in items)
    total_out = sum(i.get("outBytes", 0) for i in items)
    total_in_gb = total_in / 1073741824
    total_out_gb = total_out / 1073741824
    days = len(items)
    avg_daily_gb = total_in_gb / days

    # Date range
    first_ts = items[0].get("startTime", 0) / 1000
    last_ts = items[-1].get("startTime", 0) / 1000
    first_date = datetime.fromtimestamp(first_ts, tz=timezone.utc).strftime("%Y-%m-%d")
    last_date = datetime.fromtimestamp(last_ts, tz=timezone.utc).strftime("%Y-%m-%d")

    # Annual projection
    projected_annual_gb = avg_daily_gb * 365
    annual_quota_gb = quota_gb_day * 365

    # Utilization
    daily_utilization_pct = (avg_daily_gb / quota_gb_day * 100) if quota_gb_day > 0 else 0
    annual_utilization_pct = (projected_annual_gb / annual_quota_gb * 100) if annual_quota_gb > 0 else 0

    # Status
    if annual_utilization_pct > 90:
        status = "OVER"
    elif annual_utilization_pct > 70:
        status = "AT RISK"
    elif annual_utilization_pct > 0:
        status = "ON TRACK"
    else:
        status = "NO QUOTA"

    # Monthly breakdown
    monthly: dict[str, dict[str, float]] = {}
    for item in items:
        ts = item.get("startTime", 0) / 1000
        month_key = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m")
        if month_key not in monthly:
            monthly[month_key] = {"in_gb": 0, "out_gb": 0, "days": 0}
        monthly[month_key]["in_gb"] += item.get("inBytes", 0) / 1073741824
        monthly[month_key]["out_gb"] += item.get("outBytes", 0) / 1073741824
        monthly[month_key]["days"] += 1

    monthly_list = []
    for month, vals in sorted(monthly.items()):
        avg = vals["in_gb"] / vals["days"] if vals["days"] > 0 else 0
        monthly_list.append({
            "month": month,
            "in_gb": round(vals["in_gb"], 2),
            "out_gb": round(vals["out_gb"], 2),
            "days": vals["days"],
            "avg_daily_gb": round(avg, 2),
            "utilization_pct": round((avg / quota_gb_day * 100) if quota_gb_day > 0 else 0, 2),
        })

    # Edge breakdown
    edge_in = sum(i.get("edge", {}).get("inBytes", 0) for i in items)
    stream_in = total_in - edge_in
    stream_in_gb = stream_in / 1073741824
    edge_in_gb = edge_in / 1073741824

    # Estimated credits (published Cribl Cloud rates)
    est_stream_credits = stream_in_gb * 0.32
    est_edge_credits = edge_in_gb * 0.26
    est_total_credits = est_stream_credits + est_edge_credits

    return {
        "date_range": {"start": first_date, "end": last_date, "days": days},
        "license": {
            "quota_gb_day": quota_gb_day,
            "annual_quota_gb": round(annual_quota_gb, 0),
        },
        "consumption": {
            "total_in_gb": round(total_in_gb, 2),
            "total_out_gb": round(total_out_gb, 2),
            "avg_daily_in_gb": round(avg_daily_gb, 2),
            "stream_in_gb": round(stream_in_gb, 2),
            "edge_in_gb": round(edge_in_gb, 2),
        },
        "estimated_credits": {
            "stream_credits": round(est_stream_credits, 0),
            "edge_credits": round(est_edge_credits, 0),
            "total_ingest_credits": round(est_total_credits, 0),
            "note": "Ingest only (Stream 0.32/GB, Edge 0.26/GB). Does not include infrastructure, Search compute, or Lake storage.",
        },
        "projection": {
            "projected_annual_gb": round(projected_annual_gb, 0),
            "annual_utilization_pct": round(annual_utilization_pct, 2),
            "daily_utilization_pct": round(daily_utilization_pct, 2),
            "status": status,
        },
        "monthly": monthly_list,
    }


@click.group("finops", help="FinOps credit consumption and license utilization.")
def finops_group():
    pass


@finops_group.command("summary", help="Annual consumption summary with on-track/over/under status.")
@click.option("--json", "as_json", is_flag=True, help="Output as structured JSON.")
@click.option("--table", "use_table", is_flag=True, help="Output monthly breakdown as table.")
def finops_summary(as_json, use_table):
    """Show license consumption tracking — projected annual usage vs quota."""
    try:
        client = get_client()
        quota = _get_license_quota(client)
        usage = get_license_usage(client)
        items = usage.get("items", [])
        summary = _build_summary(items, quota)

        if as_json:
            click.echo(_json.dumps(summary, indent=2))
            return

        if use_table:
            click.echo(format_output(summary["monthly"], table=True))
            return

        # Text report
        proj = summary["projection"]
        cons = summary["consumption"]
        lic = summary["license"]
        dr = summary["date_range"]

        lines: list[str] = []
        lines.append(f"FinOps Consumption Report — {dr['start']} to {dr['end']} ({dr['days']} days)")
        lines.append("=" * 65)

        # Status banner
        status = proj["status"]
        if status == "OVER":
            banner = "!! OVER CONSUMPTION — projected to exceed annual quota"
        elif status == "AT RISK":
            banner = "!  AT RISK — trending above 70% of annual quota"
        elif status == "ON TRACK":
            banner = "   ON TRACK — consumption within expected range"
        else:
            banner = "   NO QUOTA — unable to determine license quota"
        lines.append(f"  Status: {banner}")

        lines.append("")
        lines.append("--- License " + "-" * 53)
        lines.append(f"  Daily Quota:         {lic['quota_gb_day']:>10,.0f} GB/day")
        lines.append(f"  Annual Quota:        {lic['annual_quota_gb']:>10,.0f} GB/year")

        lines.append("")
        lines.append("--- Consumption " + "-" * 49)
        lines.append(f"  Total In:            {cons['total_in_gb']:>10,.1f} GB")
        lines.append(f"  Total Out:           {cons['total_out_gb']:>10,.1f} GB")
        lines.append(f"  Avg Daily In:        {cons['avg_daily_in_gb']:>10,.2f} GB/day")
        lines.append(f"  Stream In:           {cons['stream_in_gb']:>10,.1f} GB")
        lines.append(f"  Edge In:             {cons['edge_in_gb']:>10,.1f} GB")

        lines.append("")
        lines.append("--- Throughput Projection " + "-" * 40)
        lines.append(f"  Projected Annual:    {proj['projected_annual_gb']:>10,.0f} GB")
        lines.append(f"  Throughput Util:     {proj['annual_utilization_pct']:>10.2f}%")

        cred = summary["estimated_credits"]
        lines.append("")
        lines.append("--- Estimated Credits (ingest only) " + "-" * 29)
        lines.append(f"  Stream (0.32/GB):    {cred['stream_credits']:>10,.0f} credits")
        lines.append(f"  Edge   (0.26/GB):    {cred['edge_credits']:>10,.0f} credits")
        lines.append(f"  Total Ingest:        {cred['total_ingest_credits']:>10,.0f} credits")
        lines.append(f"  (excludes infrastructure, Search compute, Lake storage)")

        lines.append("")
        lines.append("--- Monthly Breakdown " + "-" * 43)
        hdr = f"  {'MONTH':<10} {'IN (GB)':>10} {'OUT (GB)':>10} {'AVG/DAY':>10} {'UTIL %':>8}"
        lines.append(hdr)
        for m in summary["monthly"]:
            lines.append(
                f"  {m['month']:<10} {m['in_gb']:>10,.1f} {m['out_gb']:>10,.1f} "
                f"{m['avg_daily_gb']:>10,.2f} {m['utilization_pct']:>7.2f}%"
            )

        lines.append("")
        click.echo("\n".join(lines))

    except Exception as e:
        handle_error(e)
