"""Billing, consumption, and invoice commands (cloud only)."""
from __future__ import annotations

import functools
from typing import Any, Callable

import click

from cribl_cli.api.client import get_management_client
from cribl_cli.api.endpoints import billing as billing_api
from cribl_cli.output.formatter import format_output
from cribl_cli.utils.errors import handle_error
from cribl_cli.utils.org import extract_org_id

PRODUCT_SLUGS = ["stream", "search", "edge", "lake", "guard", "lakehouse", "infrastructure", "other"]


def _get_cloud_context(ctx: click.Context) -> tuple[Any, str]:
    """Return (management_client, org_id) or raise for non-cloud users."""
    config = ctx.obj.get("_config")
    if config is None:
        raise RuntimeError("Configuration not available. Billing commands require a Cribl Cloud profile.")
    org_id = extract_org_id(config.base_url)
    client = get_management_client()
    return client, org_id


def _date_options(fn: Callable) -> Callable:
    """Shared date-range options for consumption subcommands."""
    @click.option("--start", "starting_on", required=True, help="Start date (ISO 8601, e.g. 2025-01-01T00:00:00Z).")
    @click.option("--end", "ending_before", required=True, help="End date (ISO 8601).")
    @click.option("--window", default="monthly", type=click.Choice(["monthly"]), help="Aggregation window.")
    @click.option("--table", "use_table", is_flag=True, help="Table output.")
    @click.pass_context
    @functools.wraps(fn)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        return fn(*args, **kwargs)
    return wrapper


@click.group("billing", help="Billing, consumption, and invoice management (cloud only).")
def billing_group():
    pass


@billing_group.command("products-stats", help="Consumption stats across all products.")
@_date_options
def products_stats(ctx: click.Context, starting_on: str, ending_before: str, window: str, use_table: bool) -> None:
    try:
        client, org_id = _get_cloud_context(ctx)
        data = billing_api.get_products_stats(client, org_id, starting_on=starting_on, ending_before=ending_before, window=window)
        click.echo(format_output(data, table=use_table))
    except Exception as e:
        handle_error(e)


@billing_group.command("credits-summary", help="Credits purchased, used, and average.")
@_date_options
def credits_summary(ctx: click.Context, starting_on: str, ending_before: str, window: str, use_table: bool) -> None:
    try:
        client, org_id = _get_cloud_context(ctx)
        data = billing_api.get_credits_summary(client, org_id, starting_on=starting_on, ending_before=ending_before, window=window)
        click.echo(format_output(data, table=use_table))
    except Exception as e:
        handle_error(e)


@billing_group.command("cumulative", help="Cumulative consumption over time.")
@_date_options
def cumulative(ctx: click.Context, starting_on: str, ending_before: str, window: str, use_table: bool) -> None:
    try:
        client, org_id = _get_cloud_context(ctx)
        data = billing_api.get_cumulative(client, org_id, starting_on=starting_on, ending_before=ending_before, window=window)
        click.echo(format_output(data, table=use_table))
    except Exception as e:
        handle_error(e)


@billing_group.command("products-breakdown", help="Consumption breakdown by product.")
@_date_options
def products_breakdown(ctx: click.Context, starting_on: str, ending_before: str, window: str, use_table: bool) -> None:
    try:
        client, org_id = _get_cloud_context(ctx)
        data = billing_api.get_products_breakdown(client, org_id, starting_on=starting_on, ending_before=ending_before, window=window)
        click.echo(format_output(data, table=use_table))
    except Exception as e:
        handle_error(e)


@billing_group.command("product", help="Consumption breakdown for a single product.")
@click.argument("product_slug", type=click.Choice(PRODUCT_SLUGS))
@_date_options
def product(ctx: click.Context, product_slug: str, starting_on: str, ending_before: str, window: str, use_table: bool) -> None:
    try:
        client, org_id = _get_cloud_context(ctx)
        data = billing_api.get_product_breakdown(client, org_id, product_slug, starting_on=starting_on, ending_before=ending_before, window=window)
        click.echo(format_output(data, table=use_table))
    except Exception as e:
        handle_error(e)


@billing_group.command("invoices", help="List all invoices.")
@click.option("--table", "use_table", is_flag=True, help="Table output.")
@click.pass_context
def invoices(ctx: click.Context, use_table: bool) -> None:
    try:
        client, org_id = _get_cloud_context(ctx)
        data = billing_api.list_invoices(client, org_id)
        click.echo(format_output(data, table=use_table))
    except Exception as e:
        handle_error(e)


@billing_group.command("invoice", help="Get a specific invoice.")
@click.argument("invoice_id")
@click.option("--table", "use_table", is_flag=True, help="Table output.")
@click.pass_context
def invoice(ctx: click.Context, invoice_id: str, use_table: bool) -> None:
    try:
        client, org_id = _get_cloud_context(ctx)
        data = billing_api.get_invoice(client, org_id, invoice_id)
        click.echo(format_output(data, table=use_table))
    except Exception as e:
        handle_error(e)


@billing_group.command("product-usage", help="Usage breakdown for a single product.")
@click.argument("product_slug", type=click.Choice(PRODUCT_SLUGS))
@click.option("--aggregation-profile", default=None, help="Aggregation profile.")
@_date_options
def product_usage(ctx: click.Context, product_slug: str, aggregation_profile: str | None, starting_on: str, ending_before: str, window: str, use_table: bool) -> None:
    try:
        client, org_id = _get_cloud_context(ctx)
        data = billing_api.get_product_usage_breakdown(
            client, org_id, product_slug,
            starting_on=starting_on, ending_before=ending_before, window=window,
            aggregation_profile=aggregation_profile,
        )
        click.echo(format_output(data, table=use_table))
    except Exception as e:
        handle_error(e)


@billing_group.command("product-usage-groups", help="Usage breakdown by group key (e.g. worker group) for a product.")
@click.argument("product_slug", type=click.Choice(PRODUCT_SLUGS))
@click.option("--group-key", default="workerGroup", help="Key to group by (default: workerGroup).")
@click.option("--units", default="credits", type=click.Choice(["credits", "bytes", "events"]), help="Unit of measure.")
@click.option("--values-limit", default=10, type=int, help="Max groups to return (default: 10).")
@_date_options
def product_usage_groups(ctx: click.Context, product_slug: str, group_key: str, units: str, values_limit: int, starting_on: str, ending_before: str, window: str, use_table: bool) -> None:
    try:
        client, org_id = _get_cloud_context(ctx)
        data = billing_api.get_product_usage_group_breakdown(
            client, org_id, product_slug,
            starting_on=starting_on, ending_before=ending_before, window=window,
            group_key=group_key, units=units, values_limit=values_limit,
        )
        click.echo(format_output(data, table=use_table))
    except Exception as e:
        handle_error(e)


@billing_group.command("product-credits", help="Credit summary for a single product.")
@click.argument("product_slug", type=click.Choice(PRODUCT_SLUGS))
@click.option("--start", "starting_on", required=True, help="Start date (ISO 8601).")
@click.option("--end", "ending_before", required=True, help="End date (ISO 8601).")
@click.option("--table", "use_table", is_flag=True, help="Table output.")
@click.pass_context
def product_credits(ctx: click.Context, product_slug: str, starting_on: str, ending_before: str, use_table: bool) -> None:
    try:
        client, org_id = _get_cloud_context(ctx)
        data = billing_api.get_product_credits_summary(
            client, org_id, product_slug,
            starting_on=starting_on, ending_before=ending_before,
        )
        click.echo(format_output(data, table=use_table))
    except Exception as e:
        handle_error(e)


@billing_group.command("credits-stats", help="Credit stats (purchased, consumed, remaining).")
@_date_options
def credits_stats(ctx: click.Context, starting_on: str, ending_before: str, window: str, use_table: bool) -> None:
    try:
        client, org_id = _get_cloud_context(ctx)
        data = billing_api.get_credits_stats(client, org_id, starting_on=starting_on, ending_before=ending_before, window=window)
        click.echo(format_output(data, table=use_table))
    except Exception as e:
        handle_error(e)


@billing_group.command("credits-timeseries", help="Credit consumption over time (timeseries).")
@click.option("--aggregation-profile", default=None, help="Aggregation profile.")
@click.option("--max-projections", default=None, type=int, help="Max projection data points.")
@_date_options
def credits_timeseries(ctx: click.Context, aggregation_profile: str | None, max_projections: int | None, starting_on: str, ending_before: str, window: str, use_table: bool) -> None:
    try:
        client, org_id = _get_cloud_context(ctx)
        data = billing_api.get_credits_timeseries(
            client, org_id,
            starting_on=starting_on, ending_before=ending_before, window=window,
            aggregation_profile=aggregation_profile, max_projections=max_projections,
        )
        click.echo(format_output(data, table=use_table))
    except Exception as e:
        handle_error(e)


@billing_group.command("usage-timeseries", help="Usage consumption over time (timeseries).")
@click.option("--aggregation-profile", default=None, help="Aggregation profile.")
@_date_options
def usage_timeseries(ctx: click.Context, aggregation_profile: str | None, starting_on: str, ending_before: str, window: str, use_table: bool) -> None:
    try:
        client, org_id = _get_cloud_context(ctx)
        data = billing_api.get_usage_timeseries(
            client, org_id,
            starting_on=starting_on, ending_before=ending_before, window=window,
            aggregation_profile=aggregation_profile,
        )
        click.echo(format_output(data, table=use_table))
    except Exception as e:
        handle_error(e)
