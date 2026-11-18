"""Confirmation for commands that change live systems."""
from __future__ import annotations

import click


def dry_run_active() -> bool:
    """True when the global --dry-run flag is set for this invocation."""
    ctx = click.get_current_context(silent=True)
    return bool(ctx and ctx.find_root().params.get("dry_run"))


def require_yes(yes: bool, warning: str) -> None:
    """Exit 1 with WARNING unless --yes was passed.

    Under --dry-run nothing is sent (the first write is printed and aborted),
    so the preview does not need the confirmation.
    """
    if yes or dry_run_active():
        return
    click.echo(f"WARNING: {warning}", err=True)
    raise SystemExit(1)
