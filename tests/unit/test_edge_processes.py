"""``edge processes`` must hit the per-node endpoint, not a fleet-level one.

The leader serves process listings only at ``/api/v1/w/{nodeId}/edge/processes``;
the ``/api/v1/m/{fleet}/fleet/{fleet}/processes`` path the command used to call
returns 404 unconditionally.
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


_GROUPS = {
    "items": [
        {"id": "default", "type": "stream"},
        {"id": "pi", "type": "edge", "isFleet": True},
        {"id": "other-fleet", "type": "edge", "isFleet": True},
    ]
}


def _node(node_id, group, hostname, dist_mode="managed-edge"):
    return {
        "id": node_id,
        "group": group,
        "status": "healthy",
        "info": {
            "hostname": hostname,
            "cpus": 4,
            "totalmem": 8_000_000_000,
            "platform": "linux",
            "cribl": {"version": "4.16.1", "distMode": dist_mode},
        },
    }


_WORKERS = {
    "items": [
        _node("hybrid-1", "default", "hybrid-node", dist_mode="worker"),
        _node("edge-a", "pi", "pi5-cribl"),
        _node("edge-b", "other-fleet", "edge-b-host"),
    ]
}


def _proc(pid, comm, service=None):
    return {
        "id": str(pid),
        "pid": pid,
        "ppid": 1,
        "uid": 1000,
        "service": service,
        "cpu": 5.7,
        "mem_percent": 3.8,
        "mem_bytes": 319930368,
        "stat": {"comm": comm, "state": "S", "num_threads": 12},
        "cmdline": {"args": ["/opt/cribl/bin/cribl", "server"]},
        "environ": {"SECRET": "should-not-appear-in-summary"},
    }


_PROCS = {
    "edge-a": {"items": [_proc(16240, "cribl", "cribl-edge")], "count": 1},
    "edge-b": {"items": [_proc(42, "sshd")], "count": 1},
}


def _client():
    client = MagicMock(spec=httpx.Client)
    client.calls = []

    def _get(url, **kwargs):
        client.calls.append(url)
        if url == "/api/v1/master/workers":
            return _mock_response(_WORKERS)
        if url == "/api/v1/master/groups":
            return _mock_response(_GROUPS)
        for node_id, payload in _PROCS.items():
            if url == f"/api/v1/w/{node_id}/edge/processes":
                return _mock_response(payload)
        raise AssertionError(f"unexpected GET {url}")

    client.get.side_effect = _get
    return client


@patch("cribl_cli.commands.edge.get_client")
def test_processes_by_node_uses_per_node_endpoint(mock_get_client):
    client = _client()
    mock_get_client.return_value = client
    result = CliRunner().invoke(cli, ["edge", "processes", "pi5-cribl"], catch_exceptions=False)

    assert result.exit_code == 0, result.output
    assert "/api/v1/w/edge-a/edge/processes" in client.calls
    assert not any("/fleet/" in u for u in client.calls)
    rows = json.loads(result.output)
    assert rows == [
        {
            "hostname": "pi5-cribl",
            "pid": 16240,
            "ppid": 1,
            "command": "cribl",
            "state": "S",
            "uid": 1000,
            "service": "cribl-edge",
            "cpu_pct": 5.7,
            "mem_pct": 3.8,
            "mem": "305.11 MB",
            "threads": 12,
            "cmdline": "/opt/cribl/bin/cribl server",
        }
    ]


@patch("cribl_cli.commands.edge.get_client")
def test_processes_by_fleet_fans_out_to_each_edge_node(mock_get_client):
    client = _client()
    mock_get_client.return_value = client
    result = CliRunner().invoke(cli, ["edge", "processes", "-f", "pi"], catch_exceptions=False)

    assert result.exit_code == 0, result.output
    assert "/api/v1/w/edge-a/edge/processes" in client.calls
    assert "/api/v1/w/edge-b/edge/processes" not in client.calls
    assert [r["hostname"] for r in json.loads(result.output)] == ["pi5-cribl"]


@patch("cribl_cli.commands.edge.get_client")
def test_processes_without_filter_covers_all_edge_nodes_only(mock_get_client):
    client = _client()
    mock_get_client.return_value = client
    result = CliRunner().invoke(cli, ["edge", "processes"], catch_exceptions=False)

    assert result.exit_code == 0, result.output
    assert "/api/v1/w/hybrid-1/edge/processes" not in client.calls
    assert sorted(r["hostname"] for r in json.loads(result.output)) == ["edge-b-host", "pi5-cribl"]


@patch("cribl_cli.commands.edge.get_client")
def test_processes_raw_returns_untrimmed_payload(mock_get_client):
    client = _client()
    mock_get_client.return_value = client
    result = CliRunner().invoke(cli, ["edge", "processes", "pi5-cribl", "--raw"], catch_exceptions=False)

    assert result.exit_code == 0, result.output
    rows = json.loads(result.output)
    assert rows[0]["environ"]["SECRET"] == "should-not-appear-in-summary"
    assert rows[0]["stat"]["comm"] == "cribl"


@patch("cribl_cli.commands.edge.get_client")
def test_processes_skips_hybrid_worker_by_name(mock_get_client):
    client = _client()
    mock_get_client.return_value = client
    result = CliRunner().invoke(cli, ["edge", "processes", "hybrid-node"], catch_exceptions=False)

    assert result.exit_code == 0, result.output
    assert "/api/v1/w/hybrid-1/edge/processes" not in client.calls
    assert "hybrid workers do not expose processes" in result.output
    assert json.loads(result.output.splitlines()[-1]) == []
