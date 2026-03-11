"""Config management commands."""
from __future__ import annotations

import json

import click

from cribl_cli.config.loader import load_rc, save_rc
from cribl_cli.config.types import ProfileConfig


@click.group("config", help="Manage CLI configuration profiles.")
def config_group():
    pass


@config_group.command("set", help="Save a profile.")
@click.option("-p", "--profile", default="default", help="Profile name.")
@click.option("--base-url", required=True, help="Cribl base URL.")
@click.option("--auth-type", type=click.Choice(["cloud", "local"]), default="cloud")
@click.option("--client-id", default=None)
@click.option("--client-secret", default=None)
@click.option("--username", default=None)
@click.option("--password", default=None)
def config_set(profile, base_url, auth_type, client_id, client_secret, username, password):
    rc = load_rc()
    is_new = profile not in rc.profiles
    rc.profiles[profile] = ProfileConfig(
        base_url=base_url.rstrip("/"),
        auth_type=auth_type,
        client_id=client_id,
        client_secret=client_secret,
        username=username,
        password=password,
    )
    if is_new or len(rc.profiles) == 1:
        rc.active_profile = profile
    save_rc(rc)
    click.echo(json.dumps({"status": "ok", "profile": profile}, indent=2))


@config_group.command("show", help="Show profile configuration.")
@click.option("-p", "--profile", default=None, help="Profile name.")
def config_show(profile):
    rc = load_rc()
    name = profile or rc.active_profile
    p = rc.profiles.get(name)
    if not p:
        click.echo(json.dumps({"error": f"Profile '{name}' not found"}, indent=2), err=True)
        raise SystemExit(1)
    display = {
        "profile": name,
        "baseUrl": p.base_url,
        "authType": p.auth_type,
    }
    if p.client_id:
        display["clientId"] = p.client_id[:4] + "****"
    if p.client_secret:
        display["clientSecret"] = "****"
    if p.username:
        display["username"] = p.username
    if p.password:
        display["password"] = "****"
    click.echo(json.dumps(display, indent=2))


@config_group.command("use", help="Switch active profile.")
@click.argument("profile")
def config_use(profile):
    rc = load_rc()
    if profile not in rc.profiles:
        click.echo(json.dumps({"error": f"Profile '{profile}' not found"}, indent=2), err=True)
        raise SystemExit(1)
    rc.active_profile = profile
    save_rc(rc)
    click.echo(json.dumps({"status": "ok", "activeProfile": profile}, indent=2))
