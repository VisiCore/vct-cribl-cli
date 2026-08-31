"""Nodes are classified by their group's product type, not the ?product= param.

The leader ignores ``?product=`` on ``/api/v1/master/workers`` and returns every
connected node whatever value is passed, so ``workers nodes`` and ``edge nodes``
must resolve each node's product from the type of the group it reports into.
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
        {"id": "hybrid-group", "type": "stream"},
        {"id": "edge-fleet", "type": "edge", "isFleet": True},
        {"id": "empty-fleet", "type": "edge", "isFleet": True},
        {"id": "search-group", "type": "search"},
    ]
}


def _node(node_id, group, hostname):
    return {
        "id": node_id,
        "group": group,
        "status": "healthy",
        "info": {
            "hostname": hostname,
            "cpus": 4,
            "totalmem": 8_000_000_000,
            "platform": "linux",
            "cribl": {"version": "4.19.2"},
        },
    }


# The leader returns all of these regardless of ?product=
_ALL_WORKERS = {
    "items": [
        _node("n1", "default", "stream-node-1"),
        _node("n2", "hybrid-group", "hybrid-node-1"),
        _node("n3", "edge-fleet", "edge-node-1"),
        _node("n4", "search-group", "search-node-1"),
    ]
}


def _client_for(workers=_ALL_WORKERS, groups=_GROUPS, groups_fails=False):
    client = MagicMock(spec=httpx.Client)

    def _get(url, **kwargs):
        if url == "/api/v1/master/workers":
            return _mock_response(workers)
        if url == "/api/v1/master/groups":
            if groups_fails:
                raise httpx.HTTPError("boom")
            return _mock_response(groups)
        raise AssertionError(f"unexpected GET {url}")

    client.get.side_effect = _get
    return client


def _hostnames(output):
    return sorted(n["hostname"] for n in json.loads(output))


@patch("cribl_cli.commands.workers.get_client")
def test_workers_nodes_excludes_edge_and_search(mock_get_client):
    """workers nodes returns only nodes in stream-type groups."""
    mock_get_client.return_value = _client_for()
    result = CliRunner().invoke(cli, ["workers", "nodes"], catch_exceptions=False)

    assert result.exit_code == 0
    assert _hostnames(result.output) == ["hybrid-node-1", "stream-node-1"]


@patch("cribl_cli.commands.edge.get_client")
def test_edge_nodes_excludes_stream_and_search(mock_get_client):
    """edge nodes returns only nodes in edge-type fleets."""
    mock_get_client.return_value = _client_for()
    result = CliRunner().invoke(cli, ["edge", "nodes"], catch_exceptions=False)

    assert result.exit_code == 0
    assert _hostnames(result.output) == ["edge-node-1"]


@patch("cribl_cli.commands.workers.get_client")
def test_workers_nodes_rejects_edge_fleet_filter(mock_get_client):
    """-g naming an edge fleet yields nothing, rather than leaking an edge node."""
    mock_get_client.return_value = _client_for()
    result = CliRunner().invoke(cli, ["workers", "nodes", "-g", "edge-fleet"], catch_exceptions=False)

    assert result.exit_code == 0
    assert json.loads(result.output) == []


@patch("cribl_cli.commands.edge.get_client")
def test_edge_nodes_rejects_stream_group_filter(mock_get_client):
    """-f naming a stream group yields nothing, rather than leaking workers."""
    mock_get_client.return_value = _client_for()
    result = CliRunner().invoke(cli, ["edge", "nodes", "-f", "default"], catch_exceptions=False)

    assert result.exit_code == 0
    assert json.loads(result.output) == []


@patch("cribl_cli.commands.edge.get_client")
def test_edge_nodes_filters_to_named_fleet(mock_get_client):
    """-f on a real edge fleet still narrows to that fleet."""
    mock_get_client.return_value = _client_for()
    result = CliRunner().invoke(cli, ["edge", "nodes", "-f", "edge-fleet"], catch_exceptions=False)

    assert result.exit_code == 0
    assert _hostnames(result.output) == ["edge-node-1"]


@patch("cribl_cli.commands.workers.get_client")
def test_falls_back_to_unfiltered_when_groups_unavailable(mock_get_client):
    """A failing /master/groups degrades to the full list, not an empty one."""
    mock_get_client.return_value = _client_for(groups_fails=True)
    result = CliRunner().invoke(cli, ["workers", "nodes"], catch_exceptions=False)

    assert result.exit_code == 0
    assert len(json.loads(result.output)) == 4


@patch("cribl_cli.commands.workers.get_client")
def test_no_product_param_is_sent(mock_get_client):
    """The ignored ?product= param is gone — we must not imply it filters."""
    client = _client_for()
    mock_get_client.return_value = client
    CliRunner().invoke(cli, ["workers", "nodes"], catch_exceptions=False)

    worker_calls = [c for c in client.get.call_args_list if c.args[0] == "/api/v1/master/workers"]
    assert worker_calls
    for call in worker_calls:
        assert "product" not in (call.kwargs.get("params") or {})
