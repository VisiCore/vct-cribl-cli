"""Tests for the health report command."""
from __future__ import annotations

import json
import time
from unittest.mock import MagicMock, patch

import httpx
from click.testing import CliRunner

from cribl_cli.cli import cli


def _now_ms():
    return int(time.time() * 1000)


def _mock_response(json_data, status_code=200):
    resp = MagicMock(spec=httpx.Response)
    resp.json.return_value = json_data
    resp.status_code = status_code
    resp.raise_for_status.return_value = None
    return resp


# Shared fixtures
_GROUPS = {
    "items": [
        {"id": "default", "type": "stream"},
        {"id": "default_search", "type": "search"},
    ]
}

_WORKERS_EDGE = {
    "items": [
        {
            "id": "node-1",
            "group": "default",
            "status": "healthy",
            "disconnected": False,
            "lastMsgTime": _now_ms(),
            "info": {
                "hostname": "node1.example.com",
                "cpus": 4,
                "totalmem": 8000000000,
                "freemem": 5000000000,
                "totalDiskSpace": 50000000000,
                "freeDiskSpace": 30000000000,
                "platform": "linux",
                "cribl": {"version": "4.17.0", "distMode": "managed-edge"},
            },
        },
    ]
}

_WORKERS_ALL = {"items": _WORKERS_EDGE["items"]}

_HEALTHY_INPUTS = {"items": [{"id": "src1", "type": "syslog", "status": {"health": "Green"}}]}
_HEALTHY_OUTPUTS = {"items": [{"id": "dst1", "type": "splunk_hec", "status": {"health": "Green"}}]}
_UNHEALTHY_INPUTS = {
    "items": [
        {"id": "bad_src", "type": "http", "status": {"health": "Red", "message": "port conflict", "metrics": {}}},
        {"id": "ok_src", "type": "syslog", "status": {"health": "Green"}},
    ]
}

_WORKER_LOGS = {"items": [{"id": "cribl.log"}, {"id": "worker/0/cribl.log"}]}
_LOG_SEARCH = {"items": [{"events": [
    {"level": "error", "channel": "input:test", "time": "2026-03-23T10:00:00Z", "message": "connection error"},
]}]}
_LOG_SEARCH_EMPTY = {"items": []}


def _build_mock_client(inputs=None, outputs=None, logs=None, log_search=None,
                       workers_edge=None, workers_all=None, groups=None):
    """Build a mock client that returns different data based on URL."""
    client = MagicMock()
    inputs = inputs or _HEALTHY_INPUTS
    outputs = outputs or _HEALTHY_OUTPUTS
    logs = logs or _WORKER_LOGS
    log_search = log_search or _LOG_SEARCH_EMPTY
    workers_edge = workers_edge or _WORKERS_EDGE
    workers_all = workers_all or _WORKERS_ALL
    groups = groups or _GROUPS

    def fake_get(url, **kwargs):
        params = kwargs.get("params", {})
        if url == "/api/v1/master/groups":
            return _mock_response(groups)
        if url == "/api/v1/master/workers":
            if params.get("product") == "edge":
                return _mock_response(workers_edge)
            return _mock_response(workers_all)
        if "system/inputs" in url:
            return _mock_response(inputs)
        if "system/outputs" in url:
            return _mock_response(outputs)
        if "system/logs/" in url:
            return _mock_response(log_search)
        if "system/logs" in url:
            return _mock_response(logs)
        return _mock_response({})

    client.get = MagicMock(side_effect=fake_get)
    return client


@patch("cribl_cli.commands.health.get_client")
def test_report_all_healthy(mock_get_client):
    """All healthy — no alerts, clean output."""
    mock_get_client.return_value = _build_mock_client()
    runner = CliRunner()
    result = runner.invoke(cli, ["health", "report", "--skip-errors"], catch_exceptions=False)
    assert result.exit_code == 0
    assert "0 alert(s)" in result.output
    assert "All sources and destinations are healthy" in result.output


@patch("cribl_cli.commands.health.get_client")
def test_report_json_output(mock_get_client):
    """--json produces valid JSON with expected keys."""
    mock_get_client.return_value = _build_mock_client()
    runner = CliRunner()
    result = runner.invoke(cli, ["health", "report", "--json", "--skip-errors"], catch_exceptions=False)
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert "timestamp" in data
    assert "summary" in data
    assert "nodes" in data
    assert "capacity_alerts" in data
    assert "version_summary" in data
    assert "unhealthy_io" in data
    assert data["summary"]["total_nodes"] == 1
    assert data["summary"]["healthy_nodes"] == 1


@patch("cribl_cli.commands.health.get_client")
def test_report_capacity_alerts_disk(mock_get_client):
    """Nodes with disk >=80% produce alerts."""
    workers = {
        "items": [{
            "id": "node-full",
            "group": "default",
            "status": "healthy",
            "disconnected": False,
            "lastMsgTime": _now_ms(),
            "info": {
                "hostname": "full-disk-node",
                "cpus": 2,
                "totalmem": 8000000000,
                "freemem": 6000000000,
                "totalDiskSpace": 20000000000,
                "freeDiskSpace": 2000000000,  # 90% used
                "platform": "linux",
                "cribl": {"version": "4.17.0"},
            },
        }],
    }
    mock_get_client.return_value = _build_mock_client(
        workers_edge=workers, workers_all=workers
    )
    runner = CliRunner()
    result = runner.invoke(cli, ["health", "report", "--json", "--skip-errors"], catch_exceptions=False)
    data = json.loads(result.output)
    assert data["summary"]["capacity_alerts"] >= 1
    disk_alerts = [a for a in data["capacity_alerts"] if a["alert"] == "disk"]
    assert len(disk_alerts) == 1
    assert disk_alerts[0]["severity"] == "CRITICAL"


@patch("cribl_cli.commands.health.get_client")
def test_report_version_mismatch(mock_get_client):
    """Nodes on different versions are flagged."""
    workers = {
        "items": [
            {
                "id": "node-new", "group": "default", "status": "healthy",
                "disconnected": False, "lastMsgTime": 1774288000000,
                "info": {
                    "hostname": "new-node", "cpus": 4,
                    "totalmem": 8000000000, "freemem": 5000000000,
                    "totalDiskSpace": 50000000000, "freeDiskSpace": 30000000000,
                    "platform": "linux", "cribl": {"version": "4.17.0"},
                },
            },
            {
                "id": "node-old", "group": "default", "status": "healthy",
                "disconnected": False, "lastMsgTime": 1774288000000,
                "info": {
                    "hostname": "old-node", "cpus": 4,
                    "totalmem": 8000000000, "freemem": 5000000000,
                    "totalDiskSpace": 50000000000, "freeDiskSpace": 30000000000,
                    "platform": "linux", "cribl": {"version": "4.16.1"},
                },
            },
        ]
    }
    mock_get_client.return_value = _build_mock_client(
        workers_edge=workers, workers_all=workers
    )
    runner = CliRunner()
    result = runner.invoke(cli, ["health", "report", "--json", "--skip-errors"], catch_exceptions=False)
    data = json.loads(result.output)
    assert data["summary"]["version_mismatch"] is True
    assert data["version_summary"]["latest"] == "4.17.0"
    assert len(data["version_summary"]["nodes_needing_upgrade"]) == 1
    assert data["version_summary"]["nodes_needing_upgrade"][0]["hostname"] == "old-node"


@patch("cribl_cli.commands.health.get_client")
def test_report_unhealthy_sources(mock_get_client):
    """Red sources appear in the report."""
    mock_get_client.return_value = _build_mock_client(inputs=_UNHEALTHY_INPUTS)
    runner = CliRunner()
    result = runner.invoke(cli, ["health", "report", "--json", "--skip-errors"], catch_exceptions=False)
    data = json.loads(result.output)
    assert data["summary"]["unhealthy_sources"] == 1
    assert data["unhealthy_io"][0]["id"] == "bad_src"
    assert data["unhealthy_io"][0]["health"] == "Red"


@patch("cribl_cli.commands.health.get_client")
def test_report_skip_errors(mock_get_client):
    """--skip-errors omits errors from output and skips log API calls."""
    client = _build_mock_client()
    mock_get_client.return_value = client
    runner = CliRunner()
    result = runner.invoke(cli, ["health", "report", "--json", "--skip-errors"], catch_exceptions=False)
    data = json.loads(result.output)
    assert "errors" not in data

    # Verify no log scanning calls were made
    for call in client.get.call_args_list:
        url = call[0][0] if call[0] else ""
        assert "system/logs" not in url


@patch("cribl_cli.commands.health.get_client")
def test_report_with_errors(mock_get_client):
    """Without --skip-errors, errors are included."""
    mock_get_client.return_value = _build_mock_client(log_search=_LOG_SEARCH)
    runner = CliRunner()
    result = runner.invoke(cli, ["health", "report", "--json"], catch_exceptions=False)
    data = json.loads(result.output)
    assert "errors" in data
    assert len(data["errors"]) >= 1
    assert data["errors"][0]["message"] == "connection error"


@patch("cribl_cli.commands.health.get_client")
def test_report_group_filter(mock_get_client):
    """--group scopes to a specific group."""
    mock_get_client.return_value = _build_mock_client()
    runner = CliRunner()
    result = runner.invoke(
        cli, ["health", "report", "--json", "--skip-errors", "-g", "default"],
        catch_exceptions=False,
    )
    data = json.loads(result.output)
    assert data["summary"]["total_groups"] == 1
    for node in data["nodes"]:
        assert node["group"] == "default"


@patch("cribl_cli.commands.health.get_client")
def test_report_text_output(mock_get_client):
    """Default text output contains expected sections."""
    mock_get_client.return_value = _build_mock_client()
    runner = CliRunner()
    result = runner.invoke(cli, ["health", "report", "--skip-errors"], catch_exceptions=False)
    assert result.exit_code == 0
    assert "Cribl Health Report" in result.output
    assert "Node Health" in result.output
    assert "Capacity Alerts" in result.output
    assert "Version Summary" in result.output
    assert "Unhealthy Sources & Destinations" in result.output


@patch("cribl_cli.commands.health.get_client")
def test_report_disconnected_node(mock_get_client):
    """Disconnected node appears in capacity alerts."""
    workers = {
        "items": [{
            "id": "node-dead", "group": "default", "status": "unhealthy",
            "disconnected": True, "lastMsgTime": 1774200000000,
            "info": {
                "hostname": "dead-node", "cpus": 2,
                "totalmem": 4000000000, "freemem": 3000000000,
                "totalDiskSpace": 20000000000, "freeDiskSpace": 15000000000,
                "platform": "linux", "cribl": {"version": "4.17.0"},
            },
        }],
    }
    mock_get_client.return_value = _build_mock_client(
        workers_edge=workers, workers_all=workers
    )
    runner = CliRunner()
    result = runner.invoke(cli, ["health", "report", "--json", "--skip-errors"], catch_exceptions=False)
    data = json.loads(result.output)
    assert data["summary"]["healthy_nodes"] == 0
    disconnect_alerts = [a for a in data["capacity_alerts"] if a["alert"] == "disconnected"]
    assert len(disconnect_alerts) == 1
    assert disconnect_alerts[0]["severity"] == "CRITICAL"


# ---------------------------------------------------------------------------
# health cpu tests
# ---------------------------------------------------------------------------

_METRICS_SPIKE = {
    "results": {
        "metrics": [
            {
                "_time": [{"val": 1774288000}],
                "system.cpu_perc": [{"val": 92.5}],
                "system.free_mem": [{"val": 2000000000}],
                "system.total_mem": [{"val": 8000000000}],
                "system.disk_used": [{"val": 20000000000}],
                "system.total_disk": [{"val": 50000000000}],
                "system.load_avg": [{"val": 3.2}],
            },
            {
                "_time": [{"val": 1774288300}],
                "system.cpu_perc": [{"val": 45.0}],
                "system.free_mem": [{"val": 4000000000}],
                "system.total_mem": [{"val": 8000000000}],
                "system.disk_used": [{"val": 20000000000}],
                "system.total_disk": [{"val": 50000000000}],
                "system.load_avg": [{"val": 1.5}],
            },
        ]
    }
}

_METRICS_NORMAL = {
    "results": {
        "metrics": [
            {
                "_time": [{"val": 1774288000}],
                "system.cpu_perc": [{"val": 25.0}],
                "system.free_mem": [{"val": 6000000000}],
                "system.total_mem": [{"val": 8000000000}],
                "system.disk_used": [{"val": 10000000000}],
                "system.total_disk": [{"val": 50000000000}],
                "system.load_avg": [{"val": 0.5}],
            },
        ]
    }
}


def _build_cpu_mock_client(metrics_data=None):
    """Build a mock client for health cpu tests."""
    client = MagicMock()
    metrics_data = metrics_data or _METRICS_NORMAL

    def fake_get(url, **kwargs):
        params = kwargs.get("params", {})
        if url == "/api/v1/master/workers":
            if params.get("product") == "edge":
                return _mock_response(_WORKERS_EDGE)
            return _mock_response(_WORKERS_ALL)
        if "system/metrics" in url:
            return _mock_response(metrics_data)
        return _mock_response({})

    client.get = MagicMock(side_effect=fake_get)
    return client


@patch("cribl_cli.commands.health.get_client")
def test_cpu_no_spikes(mock_get_client):
    """Normal CPU — no spikes flagged."""
    mock_get_client.return_value = _build_cpu_mock_client(_METRICS_NORMAL)
    runner = CliRunner()
    result = runner.invoke(cli, ["health", "cpu"], catch_exceptions=False)
    assert result.exit_code == 0
    assert "No nodes exceeded" in result.output


@patch("cribl_cli.commands.health.get_client")
def test_cpu_with_spike(mock_get_client):
    """Node spiking above threshold is flagged."""
    mock_get_client.return_value = _build_cpu_mock_client(_METRICS_SPIKE)
    runner = CliRunner()
    result = runner.invoke(cli, ["health", "cpu", "--threshold", "80"], catch_exceptions=False)
    assert result.exit_code == 0
    assert "1 node(s) spiking" in result.output
    assert "node1.example.com" in result.output


@patch("cribl_cli.commands.health.get_client")
def test_cpu_json_output(mock_get_client):
    """--json produces valid JSON with expected fields."""
    mock_get_client.return_value = _build_cpu_mock_client(_METRICS_SPIKE)
    runner = CliRunner()
    result = runner.invoke(cli, ["health", "cpu", "--json"], catch_exceptions=False)
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert len(data) == 1
    assert data[0]["hostname"] == "node1.example.com"
    assert data[0]["status"] == "spike"
    assert data[0]["max_cpu"] == 92.5
    assert data[0]["spikes"] == 1


@patch("cribl_cli.commands.health.get_client")
def test_cpu_custom_threshold(mock_get_client):
    """Low threshold flags even moderate CPU."""
    mock_get_client.return_value = _build_cpu_mock_client(_METRICS_NORMAL)
    runner = CliRunner()
    result = runner.invoke(cli, ["health", "cpu", "--threshold", "20"], catch_exceptions=False)
    assert result.exit_code == 0
    assert "1 node(s) spiking" in result.output
