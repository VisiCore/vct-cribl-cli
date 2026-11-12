"""Main CLI setup: builds the Click command tree with all commands."""

from __future__ import annotations

from typing import Any

import click

from cribl_cli.api.client import (
    DEFAULT_TIMEOUT,
    create_client,
    create_management_client,
    set_client,
    set_management_client,
    set_config_error,
)
from cribl_cli.config.loader import load_config


class CriblCLI(click.Group):
    """Root Click group. Its callback initialises the API clients before
    every command except ``config`` (which must work without credentials)."""

    @staticmethod
    def init_clients(ctx: click.Context) -> None:
        """Load config and build the API clients for this invocation.

        A config problem is recorded rather than raised, so the error surfaces
        (as clean JSON) only when a command actually asks for a client.
        """
        params = ctx.params
        try:
            cfg = load_config(
                profile=params.get("profile"),
                base_url=params.get("base_url"),
                client_id=params.get("client_id"),
                client_secret=params.get("client_secret"),
            )
            dry_run = params.get("dry_run", False)
            verbose = params.get("verbose", False)
            timeout = params.get("timeout") or DEFAULT_TIMEOUT
            set_client(create_client(cfg, dry_run=dry_run, verbose=verbose, timeout=timeout))
            set_management_client(
                create_management_client(cfg, dry_run=dry_run, verbose=verbose, timeout=timeout)
            )
            ctx.ensure_object(dict)
            ctx.obj["_config"] = cfg
        except Exception as exc:
            set_config_error(str(exc))


@click.group(cls=CriblCLI, context_settings={"help_option_names": ["-h", "--help"]})
@click.option("-p", "--profile", default=None, help="Configuration profile name.")
@click.option("--base-url", default=None, help="Cribl base URL override.")
@click.option("--client-id", default=None, help="OAuth client ID override.")
@click.option("--client-secret", default=None, help="OAuth client secret override.")
@click.option("--verbose", is_flag=True, help="Log HTTP requests to stderr.")
@click.option("--dry-run", is_flag=True, help="Preview mode — log requests without sending.")
@click.option(
    "--timeout", type=click.FloatRange(min=1), default=None, envvar="CRIBL_TIMEOUT",
    help=f"Seconds to wait for each API request (default: {DEFAULT_TIMEOUT:g}; env CRIBL_TIMEOUT).",
)
@click.option("--fields", default=None, help="Comma-separated list of fields to include in output.")
@click.pass_context
def cli(ctx: click.Context, **kwargs: Any) -> None:
    """Cribl CLI — command-line interface for the Cribl Cloud REST API."""
    ctx.ensure_object(dict)
    ctx.obj.update(kwargs)
    # Click sets invoked_subcommand before running this callback.
    if ctx.invoked_subcommand != "config":
        CriblCLI.init_clients(ctx)


def _register_commands() -> None:
    """Register all command groups on the CLI."""
    # Hand-written commands
    from cribl_cli.commands.config_cmd import config_group
    from cribl_cli.commands.workers import workers_group
    from cribl_cli.commands.groups import groups_group
    from cribl_cli.commands.sources import sources_group
    from cribl_cli.commands.destinations import destinations_group
    from cribl_cli.commands.metrics import metrics_group
    from cribl_cli.commands.search import search_group
    from cribl_cli.commands.notebooks import notebooks_group
    from cribl_cli.commands.pipelines import pipelines_group
    from cribl_cli.commands.routes import routes_group
    from cribl_cli.commands.jobs import jobs_group
    from cribl_cli.commands.version import version_group
    from cribl_cli.commands.system import system_group
    from cribl_cli.commands.edge import edge_group
    from cribl_cli.commands.kms import kms_group
    from cribl_cli.commands.preview import preview_group
    from cribl_cli.commands.logger import logger_group
    from cribl_cli.commands.profiler import profiler_group
    from cribl_cli.commands.health import health_group
    from cribl_cli.commands.overview import overview_group
    from cribl_cli.commands.alerts import alerts_group
    from cribl_cli.commands.packs import packs_group
    from cribl_cli.commands.license_usage import license_usage_group
    from cribl_cli.commands.billing import billing_group
    from cribl_cli.commands.ingest import ingest_group
    from cribl_cli.commands.finops import finops_group
    from cribl_cli.commands.apps import apps_group
    from cribl_cli.commands.api import api_cmd, api_spec_group

    for group in [
        config_group, workers_group, groups_group, sources_group, destinations_group,
        metrics_group, search_group, notebooks_group, pipelines_group,
        routes_group, jobs_group, version_group, system_group, edge_group,
        kms_group, preview_group, logger_group, profiler_group, health_group,
        overview_group, alerts_group, packs_group, license_usage_group,
        billing_group, ingest_group, finops_group, apps_group, api_cmd, api_spec_group,
    ]:
        cli.add_command(group)

    # Factory-generated CRUD commands
    from cribl_cli.commands.registry import REGISTRY
    from cribl_cli.commands.command_factory import register_crud_command

    for reg in REGISTRY:
        register_crud_command(cli, reg)


_register_commands()
