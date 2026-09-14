"""The former fleet-scoped edge commands must use per-node ``/w/{id}/edge/*``.

``/api/v1/m/{fleet}/fleet/{fleet}/<x>`` never existed on the leader; every
command that used it returned 404. containers/logs/metadata fan out across
nodes; events and kube-logs need a source / container id and are per node.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import httpx
from click.testing import CliRunner

from cribl_cli.cli import cli


def _mock_response(json_data, status_code=200):
    resp = MagicMock(spec=httpx.Response)
    resp.json.return_value = json_data
    resp.status_code = status_code
    resp.raise_for_status.return_value = None
    return resp


_GROUPS = {"items": [
    {"id": "default", "type": "stream"},
    {"id": "pi", "type": "edge", "isFleet": True},
    {"id": "other-fleet", "type": "edge", "isFleet": True},
]}


def _node(node_id, group, hostname, dist_mode="managed-edge"):
    return {"id": node_id, "group": group, "status": "healthy", "info": {
        "hostname": hostname, "cpus": 4, "totalmem": 8_000_000_000, "platform": "linux",
        "cribl": {"version": "4.16.1", "distMode": dist_mode}}}


_WORKERS = {"items": [
    _node("hybrid-1", "default", "hybrid-node", dist_mode="worker"),
    _node("edge-a", "pi", "pi5-cribl"),
    _node("edge-b", "other-fleet", "edge-b-host"),
]}

_METADATA = {"items": [{
    "timestamp": 1786654920.856,
    "cribl": {"version": "4.16.1-abc", "mode": "managed-edge", "tags": [], "group": "pi",
              "config_version": "1b78cb5"},
    "env": {"CRIBL_HOME": "/opt/cribl", "SECRET": "hidden"},
    "os": {"arch": "arm64", "cpu_count": 4, "cpu_type": "Cortex-A76", "hostname": "pi5-cribl"},
}], "count": 1}

_LOGS = {"items": [{
    "id": "0", "filePath": "/opt/cribl/log/cribl.log", "owner": 1000, "mode": "-rw-r--r--",
    "modTime": 1789417378.2, "size": 3_100_000,
    "processInfo": [{"pid": 1535, "process": "cribl"}],
}], "count": 1}

_CONTAINERS = {"items": [{"id": "c1", "name": "nginx"}], "count": 1}
_EVENTS = {"items": [{"_raw": "hello"}], "count": 1}
_KUBE = {"items": [{"line": "pod started"}], "count": 1}


def _client():
    client = MagicMock(spec=httpx.Client)
    client.calls = []
    table = {
        "/api/v1/master/workers": _WORKERS,
        "/api/v1/master/groups": _GROUPS,
        "/api/v1/w/edge-a/edge/metadata": _METADATA,
        "/api/v1/w/edge-b/edge/metadata": _METADATA,
        "/api/v1/w/edge-a/edge/logs": _LOGS,
        "/api/v1/w/edge-a/edge/containers": _CONTAINERS,
        "/api/v1/w/edge-b/edge/containers": _CONTAINERS,
        "/api/v1/w/edge-a/edge/events/in_system_state": _EVENTS,
        "/api/v1/w/edge-a/edge/kube-logs/c1": _KUBE,
    }

    def _get(url, **kwargs):
        client.calls.append((url, kwargs.get("params")))
        if url in table:
            return _mock_response(table[url])
        raise AssertionError(f"unexpected GET {url}")

    client.get.side_effect = _get
    return client


def _run(client, *args):
    with patch("cribl_cli.commands.edge.get_client", return_value=client):
        result = CliRunner().invoke(cli, ["edge", *args], catch_exceptions=False)
    assert result.exit_code == 0, result.output
    assert not any("/fleet/" in u for u, _ in client.calls)
    return json.loads(result.output)


def test_metadata_summary_omits_env():
    rows = _run(_client(), "metadata", "pi5-cribl")
    assert rows == [{
        "hostname": "pi5-cribl", "version": "4.16.1-abc", "mode": "managed-edge", "fleet": "pi",
        "config_version": "1b78cb5", "tags": [], "arch": "arm64", "cpu": "Cortex-A76", "cpus": 4,
        "cribl_home": "/opt/cribl", "timestamp": 1786654920.856,
    }]


def test_metadata_raw_includes_env():
    rows = _run(_client(), "metadata", "pi5-cribl", "--raw")
    assert rows[0]["env"]["SECRET"] == "hidden"


def test_metadata_fans_out_across_all_edge_nodes():
    client = _client()
    rows = _run(client, "metadata")
    urls = [u for u, _ in client.calls]
    assert "/api/v1/w/edge-a/edge/metadata" in urls
    assert "/api/v1/w/edge-b/edge/metadata" in urls
    assert "/api/v1/w/hybrid-1/edge/metadata" not in urls
    assert len(rows) == 2


def test_logs_flattens_process_info():
    rows = _run(_client(), "logs", "-f", "pi")
    assert rows == [{
        "hostname": "pi5-cribl", "path": "/opt/cribl/log/cribl.log", "size": "2.96 MB",
        "mode": "-rw-r--r--", "owner": 1000, "mod_time": 1789417378.2, "processes": "cribl(1535)",
    }]


def test_containers_tags_hostname():
    rows = _run(_client(), "containers", "-f", "pi")
    assert rows == [{"hostname": "pi5-cribl", "id": "c1", "name": "nginx"}]


def test_events_requires_source_and_passes_limit():
    client = _client()
    rows = _run(client, "events", "pi5-cribl", "in_system_state", "-l", "5")
    assert ("/api/v1/w/edge-a/edge/events/in_system_state", {"limit": 5}) in client.calls
    assert rows == [{"_raw": "hello"}]


def test_kube_logs_by_container():
    client = _client()
    rows = _run(client, "kube-logs", "pi5-cribl", "c1")
    assert any(u == "/api/v1/w/edge-a/edge/kube-logs/c1" for u, _ in client.calls)
    assert rows == [{"line": "pod started"}]


def test_files_command_removed():
    result = CliRunner().invoke(cli, ["edge", "files", "/"])
    assert result.exit_code != 0
    assert "No such command" in result.output
