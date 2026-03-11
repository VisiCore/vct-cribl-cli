"""Worker group commands."""
from __future__ import annotations

import subprocess
from urllib.parse import urlparse

import click

from cribl_cli.api.client import get_client
from cribl_cli.api.endpoints.workers import list_worker_groups, get_worker_group, deploy_group
from cribl_cli.config.loader import load_config
from cribl_cli.output.formatter import format_output
from cribl_cli.utils.errors import handle_error


@click.group("workers", help="Manage worker groups.")
def workers_group():
    pass


@workers_group.command("list")
@click.option("--table", "use_table", is_flag=True)
def workers_list(use_table):
    try:
        client = get_client()
        data = list_worker_groups(client)
        click.echo(format_output(data, table=use_table))
    except Exception as e:
        handle_error(e)


@workers_group.command("get")
@click.argument("group_id")
@click.option("--table", "use_table", is_flag=True)
def workers_get(group_id, use_table):
    try:
        client = get_client()
        data = get_worker_group(client, group_id)
        click.echo(format_output(data, table=use_table))
    except Exception as e:
        handle_error(e)


@workers_group.command("deploy", help="Deploy committed config to a worker group.")
@click.argument("group")
def workers_deploy(group):
    try:
        client = get_client()
        data = deploy_group(client, group)
        click.echo(format_output(data))
    except Exception as e:
        handle_error(e)


@workers_group.command("add", help="Add a worker to a group via Docker.")
@click.argument("group")
@click.option("--token", required=True, help="Leader auth token (from Settings > Distributed Settings).")
@click.option("--version", "cribl_version", default=None, help="Cribl version tag (default: match leader).")
@click.option("--port", default=9000, type=int, help="Host port to map to container port 9000.")
@click.option("--name", "container_name", default=None, help="Container name (default: cribl-worker-<group>).")
@click.option("--dry-run", "show_only", is_flag=True, help="Print the docker command without running it.")
@click.option("--image", default="cribl/cribl", help="Docker image (default: cribl/cribl).")
def workers_add(group, token, cribl_version, port, container_name, show_only, image):
    """Spin up a new Cribl worker in Docker and connect it to a worker group.

    Requires the leader auth token from Settings > Distributed Settings in the Cribl UI.

    Examples:

      cribl workers add defaultHybrid --token <TOKEN>

      cribl workers add default --token <TOKEN> --version 4.16.1 --port 9420
    """
    try:
        # Resolve leader host from config
        cfg = load_config()
        parsed = urlparse(cfg.base_url)
        leader_host = parsed.hostname

        # Resolve version from leader if not specified
        if not cribl_version:
            client = get_client()
            resp = client.get("/api/v1/system/info")
            resp.raise_for_status()
            info = resp.json()
            items = info.get("items", [info])
            build = items[0].get("BUILD", {}) if items else {}
            full_version = build.get("VERSION", "")
            # VERSION is like "4.17.0-7e952fa7", we want just "4.17.0"
            cribl_version = full_version.split("-")[0] if full_version else "latest"
            click.echo(f"Detected leader version: {full_version} -> using image tag {cribl_version}", err=True)

        # Validate group exists
        client = get_client()
        wg_resp = client.get("/api/v1/master/groups")
        wg_resp.raise_for_status()
        group_ids = [g.get("id") for g in wg_resp.json().get("items", [])]
        if group not in group_ids:
            click.echo(f"Error: group '{group}' not found. Available: {', '.join(group_ids)}", err=True)
            raise SystemExit(1)

        # Build the docker command
        name = container_name or f"cribl-worker-{group}"
        master_url = f"tls://{token}@{leader_host}:4200?group={group}"
        full_image = f"{image}:{cribl_version}"

        cmd = [
            "docker", "run", "-d",
            "--name", name,
            "--restart", "unless-stopped",
            "-e", f"CRIBL_DIST_MASTER_URL={master_url}",
            "-e", "CRIBL_DIST_MODE=worker",
            "-p", f"{port}:9000",
            full_image,
        ]

        if show_only:
            # Print a copy-pasteable command
            parts = [
                "docker run -d",
                f'  --name "{name}"',
                "  --restart unless-stopped",
                f'  -e "CRIBL_DIST_MASTER_URL={master_url}"',
                '  -e "CRIBL_DIST_MODE=worker"',
                f"  -p {port}:9000",
                f"  {full_image}",
            ]
            click.echo(" \\\n".join(parts))
            return

        click.echo(f"Starting worker container '{name}' for group '{group}'...", err=True)
        click.echo(f"  Image:  {full_image}", err=True)
        click.echo(f"  Leader: {leader_host}:4200", err=True)
        click.echo(f"  Port:   {port} -> 9000", err=True)

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            click.echo(f"Error: {result.stderr.strip()}", err=True)
            raise SystemExit(1)

        container_id = result.stdout.strip()[:12]
        click.echo(f"  Container: {container_id}", err=True)
        click.echo("", err=True)

        # Wait for it to connect
        import time
        click.echo("Waiting for worker to connect...", err=True)
        for attempt in range(6):
            time.sleep(5)
            resp = client.get("/api/v1/master/workers", params={"product": "edge"})
            resp.raise_for_status()
            workers = resp.json().get("items", [])
            for w in workers:
                info = w.get("info", {})
                hostname = info.get("hostname", "")
                if container_id in hostname or container_id in w.get("id", ""):
                    status = w.get("status", "?")
                    click.echo(format_output({
                        "status": "ok",
                        "container": container_id,
                        "hostname": hostname,
                        "group": group,
                        "worker_status": status,
                    }))
                    return
                # Also match by checking new workers in the group
            # Check if any new worker appeared in this group
            group_workers = [w for w in workers if w.get("group") == group]
            for w in group_workers:
                last_msg = w.get("lastMsgTime", 0) / 1000
                if time.time() - last_msg < 30:
                    info = w.get("info", {})
                    hostname = info.get("hostname", w.get("id", "?"))
                    # Check if this looks like our container
                    if w.get("firstMsgTime", 0) / 1000 > time.time() - 60:
                        click.echo(format_output({
                            "status": "ok",
                            "container": container_id,
                            "hostname": hostname,
                            "group": group,
                            "worker_status": w.get("status", "?"),
                        }))
                        return

        # Timed out waiting - check docker logs for errors
        log_result = subprocess.run(
            ["docker", "logs", "--tail", "20", name],
            capture_output=True, text=True,
        )
        logs = log_result.stdout + log_result.stderr
        if "Unauthorized" in logs:
            click.echo("Error: Worker connected but was rejected (Unauthorized). Check your auth token.", err=True)
            raise SystemExit(1)
        elif "ENOTFOUND" in logs:
            click.echo(f"Error: Could not resolve {leader_host}. Check your base URL.", err=True)
            raise SystemExit(1)
        else:
            click.echo(f"Warning: Worker started but hasn't appeared in the leader yet. Check: docker logs {name}", err=True)
            click.echo(format_output({"status": "pending", "container": container_id, "group": group}))

    except SystemExit:
        raise
    except Exception as e:
        handle_error(e)


@workers_group.command("rm", help="Stop and remove a Docker worker container.")
@click.argument("container_name")
def workers_rm(container_name):
    """Stop and remove a Cribl worker Docker container."""
    try:
        click.echo(f"Stopping container '{container_name}'...", err=True)
        subprocess.run(["docker", "stop", container_name], capture_output=True, text=True)
        subprocess.run(["docker", "rm", container_name], capture_output=True, text=True)
        click.echo(format_output({"status": "removed", "container": container_name}))
    except Exception as e:
        handle_error(e)
