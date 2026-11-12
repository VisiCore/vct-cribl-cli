"""Regression tests for the safety and correctness fixes from the code review."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx
import pytest
from click.testing import CliRunner

from cribl_cli.api.endpoints.billing import get_product_usage_breakdown
from cribl_cli.api.endpoints.routes import update_route
from cribl_cli.cli import cli
from cribl_cli.commands.finops import _build_summary
from cribl_cli.commands.health import _build_version_summary
from cribl_cli.config.loader import load_rc
from cribl_cli.utils.errors import _extract_http_error_detail
from cribl_cli.utils.group_resolver import resolve_group
from cribl_cli.utils.group_transfer import apply
from cribl_cli.utils.org import extract_org_id
from cribl_cli.utils.validation import merge_update


def _resp(json_data):
    resp = MagicMock(spec=httpx.Response)
    resp.json.return_value = json_data
    resp.raise_for_status.return_value = None
    return resp


def _client():
    return MagicMock(spec=httpx.Client)


def _invoke(args, **kwargs):
    """Run the CLI without touching the real ~/.criblrc."""
    with patch("cribl_cli.cli.load_config", side_effect=ValueError("no config in tests")):
        return CliRunner().invoke(cli, args, **kwargs)


# ---------------------------------------------------------------------------
# Merge-on-update
# ---------------------------------------------------------------------------


def test_merge_update_keeps_nested_siblings_and_strips_server_fields():
    existing = {
        "id": "p1",
        "status": {"health": "Green"},
        "notifications": [],
        "conf": {"description": "old", "functions": [{"id": "eval"}]},
    }

    merged = merge_update(existing, {"conf": {"description": "new"}})

    assert merged == {"id": "p1", "conf": {"description": "new", "functions": [{"id": "eval"}]}}
    assert "status" in existing  # input is not mutated


@pytest.mark.parametrize("existing,updates", [({}, ["x"]), ("not-a-dict", {})])
def test_merge_update_rejects_non_objects(existing, updates):
    with pytest.raises(ValueError):
        merge_update(existing, updates)


@pytest.mark.parametrize(
    "module,args",
    [
        ("pipelines", ["pipelines", "update", "x1"]),
        ("sources", ["sources", "update", "x1"]),
        ("destinations", ["destinations", "update", "x1"]),
        ("packs", ["packs", "update", "x1"]),
    ],
)
def test_update_commands_deep_merge(module, args):
    """A partial nested update must not drop the keys it did not mention."""
    client = _client()
    client.get.return_value = _resp(
        {"items": [{"id": "x1", "status": {"health": "Green"}, "conf": {"keep": [1, 2], "description": "old"}}]}
    )
    client.patch.return_value = _resp({})

    with patch(f"cribl_cli.commands.{module}.get_client", return_value=client):
        result = _invoke(args + ['{"conf": {"description": "new"}}', "-g", "default"])

    assert result.exit_code == 0, result.output
    body = client.patch.call_args.kwargs["json"]
    assert body["conf"] == {"keep": [1, 2], "description": "new"}
    assert "status" not in body


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


def test_route_patch_keeps_table_groups_and_comments():
    client = _client()
    client.get.return_value = _resp({
        "items": [{
            "id": "default",
            "groups": {"g1": {"name": "Firewalls"}},
            "comments": [{"id": "c1", "comment": "note"}],
            "routes": [{"id": "r1", "filter": "true", "final": True, "pipeline": "main"}],
        }],
        "count": 1,
    })
    client.patch.return_value = _resp({})

    update_route(client, "default", "r1", {"description": "changed"})

    url = client.patch.call_args.args[0]
    body = client.patch.call_args.kwargs["json"]
    assert url == "/api/v1/m/default/routes/default"
    assert body["groups"] == {"g1": {"name": "Firewalls"}}
    assert body["comments"] == [{"id": "c1", "comment": "note"}]
    assert body["routes"][0]["description"] == "changed"
    assert not any(k.startswith("_") for k in body)


@pytest.mark.parametrize("routes_value", [{}, {"items": []}, [], None, "oops"])
def test_import_never_replaces_route_table_with_nothing(routes_value):
    client = _client()
    client.get.return_value = _resp({"items": [{"id": "grp"}]})

    report = apply(client, "grp", {"resources": {"routes": routes_value}}, with_routes=True)

    assert "routes" in report["failed"]
    client.patch.assert_not_called()


# ---------------------------------------------------------------------------
# groups import: failures stop commit/deploy
# ---------------------------------------------------------------------------


@patch("cribl_cli.commands.groups.deploy_group")
@patch("cribl_cli.commands.groups.commit_version")
@patch("cribl_cli.commands.groups.apply")
@patch("cribl_cli.commands.groups.get_client")
def test_import_with_failures_does_not_commit_or_deploy(mock_client, mock_apply, mock_commit, mock_deploy):
    mock_client.return_value = _client()
    mock_apply.return_value = {
        "target": "grp", "created": ["pipelines/a"], "updated": [],
        "failed": {"sources/b": "HTTP Error: 400"}, "skipped": {},
    }

    result = _invoke(["groups", "import", "grp", "--deploy", "--yes"], input="{}")

    assert result.exit_code == 1
    mock_commit.assert_not_called()
    mock_deploy.assert_not_called()


@patch("cribl_cli.commands.groups.deploy_group")
@patch("cribl_cli.commands.groups.commit_version")
@patch("cribl_cli.commands.groups.apply")
@patch("cribl_cli.commands.groups.get_client")
def test_import_clean_still_commits_and_deploys(mock_client, mock_apply, mock_commit, mock_deploy):
    mock_client.return_value = _client()
    mock_apply.return_value = {"target": "grp", "created": [], "updated": [], "failed": {}, "skipped": {}}

    result = _invoke(["groups", "import", "grp", "--deploy", "--yes"], input="{}")

    assert result.exit_code == 0, result.output
    mock_commit.assert_called_once()
    mock_deploy.assert_called_once()


# ---------------------------------------------------------------------------
# Confirmation flags
# ---------------------------------------------------------------------------


@patch("cribl_cli.commands.workers.deploy_group")
@patch("cribl_cli.commands.workers.get_client")
def test_workers_deploy_requires_yes(mock_client, mock_deploy):
    mock_client.return_value = _client()
    mock_deploy.return_value = {}

    assert _invoke(["workers", "deploy", "grp"]).exit_code == 1
    mock_deploy.assert_not_called()

    assert _invoke(["workers", "deploy", "grp", "--yes"]).exit_code == 0
    mock_deploy.assert_called_once()


@pytest.mark.parametrize("args,path", [
    (["restart"], "/api/v1/system/settings/restart"),
    (["reload"], "/api/v1/system/settings/reload"),
    (["upgrade", "4.21.0"], "/api/v1/system/settings/upgrade/4.21.0"),
])
def test_system_disruptive_commands_require_yes(args, path):
    client = _client()
    client.post.return_value = _resp({})

    with patch("cribl_cli.commands.system.get_client", return_value=client):
        assert _invoke(["system", *args]).exit_code == 1
        client.post.assert_not_called()
        assert _invoke(["system", *args, "--yes"]).exit_code == 0
        client.post.assert_called_once()
        assert client.post.call_args.args[0] == path


# ---------------------------------------------------------------------------
# Group resolution for writes
# ---------------------------------------------------------------------------


def test_write_without_group_fails_when_several_groups_exist():
    client = _client()
    client.get.return_value = _resp({"items": [{"id": "default"}, {"id": "defaultHybrid"}]})

    with pytest.raises(ValueError, match="default, defaultHybrid"):
        resolve_group(client, None, write=True)


def test_write_without_group_uses_the_only_group():
    client = _client()
    client.get.return_value = _resp({"items": [{"id": "only"}]})

    assert resolve_group(client, None, write=True) == "only"


def test_delete_without_group_sends_nothing():
    client = _client()
    client.get.return_value = _resp({"items": [{"id": "a"}, {"id": "b"}]})

    with patch("cribl_cli.commands.pipelines.get_client", return_value=client):
        result = _invoke(["pipelines", "delete", "p1"])

    assert result.exit_code == 1
    client.delete.assert_not_called()


# ---------------------------------------------------------------------------
# Singleton update (auth-settings, git-settings)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("cmd,path", [("auth-settings", "system/settings/auth"), ("git-settings", "system/settings/git-settings")])
def test_singleton_update_takes_only_json(cmd, path):
    client = _client()
    client.get.return_value = _resp({"type": "local", "nested": {"a": 1}})
    client.patch.return_value = _resp({})

    with patch("cribl_cli.commands.command_factory.get_client", return_value=client):
        result = _invoke([cmd, "update", '{"nested": {"b": 2}}'])

    assert result.exit_code == 0, result.output
    assert client.patch.call_args.args[0] == f"/api/v1/{path}"
    assert client.patch.call_args.kwargs["json"] == {"type": "local", "nested": {"a": 1, "b": 2}}


def test_non_singleton_update_still_takes_id_then_json():
    client = _client()
    client.get.return_value = _resp({"items": [{"id": "u1", "first": "A"}]})
    client.patch.return_value = _resp({})

    with patch("cribl_cli.commands.command_factory.get_client", return_value=client):
        result = _invoke(["users", "update", "u1", '{"first": "B"}'])

    assert result.exit_code == 0, result.output
    assert client.patch.call_args.args[0] == "/api/v1/system/users/u1"
    assert client.patch.call_args.kwargs["json"] == {"id": "u1", "first": "B"}


# ---------------------------------------------------------------------------
# -p/--profile honoured by commands that read the config themselves
# ---------------------------------------------------------------------------


@patch("cribl_cli.commands.workers.get_client")
@patch("cribl_cli.commands.workers.load_config")
def test_workers_add_uses_the_invocation_config(mock_bare_load, mock_client):
    """The leader host comes from the profile the CLI was started with."""
    mock_bare_load.return_value = MagicMock(base_url="https://active-profile.cribl.cloud")
    chosen = MagicMock(base_url="https://chosen-profile.cribl.cloud")
    client = _client()
    client.get.return_value = _resp({"items": [{"id": "default"}]})
    mock_client.return_value = client

    with patch("cribl_cli.cli.load_config", return_value=chosen), \
         patch("cribl_cli.cli.create_client"), patch("cribl_cli.cli.create_management_client"), \
         patch("cribl_cli.cli.set_client"), patch("cribl_cli.cli.set_management_client"):
        result = CliRunner().invoke(
            cli,
            ["-p", "chosen", "workers", "add", "default", "--token", "t", "--version", "4.10.0", "--dry-run"],
        )

    assert result.exit_code == 0, result.output
    assert "chosen-profile.cribl.cloud" in result.output
    assert "active-profile" not in result.output


# ---------------------------------------------------------------------------
# Smaller correctness fixes
# ---------------------------------------------------------------------------


def test_version_summary_sorts_numerically():
    nodes = [
        {"hostname": "old", "version": "4.9.3", "group": "g"},
        {"hostname": "new", "version": "4.10.0-abc123", "group": "g"},
    ]

    summary = _build_version_summary(nodes)

    assert summary["latest"] == "4.10.0-abc123"
    assert [n["hostname"] for n in summary["nodes_needing_upgrade"]] == ["old"]


@pytest.mark.parametrize(
    "url,expected",
    [
        ("https://main-acme-prod-x1y2z3a.cribl.cloud", "acme-prod-x1y2z3a"),
        ("https://acme-prod-x1y2z3a.cribl.cloud", "acme-prod-x1y2z3a"),
        ("https://my-ws-acme-prod-x1y2z3a.cribl.cloud", "acme-prod-x1y2z3a"),
        ("https://myorg.cribl.cloud", "myorg"),
        ("https://test-org.cribl.cloud", "test-org"),
    ],
)
def test_extract_org_id_shapes(url, expected):
    assert extract_org_id(url) == expected


def test_billing_unset_aggregation_profile_falls_back_to_default():
    client = _client()
    client.get.return_value = _resp({})

    get_product_usage_breakdown(
        client, "org", "stream", starting_on="a", ending_before="b", aggregation_profile=None
    )

    assert client.get.call_args.kwargs["params"]["aggregationProfile"] == "default"


@patch("cribl_cli.commands.search.time.sleep")
@patch("cribl_cli.commands.search.get_search_results")
@patch("cribl_cli.commands.search.get_search_status")
@patch("cribl_cli.commands.search.run_search")
@patch("cribl_cli.commands.search.get_client")
def test_search_poll_stops_on_canceled(mock_client, mock_run, mock_status, mock_results, _sleep):
    mock_client.return_value = _client()
    mock_run.return_value = {"id": "job1"}
    mock_status.return_value = {"items": [{"status": "canceled"}]}

    result = _invoke(["search", "run", "-q", "x", "--poll"])

    assert result.exit_code == 1
    assert mock_status.call_count == 1
    mock_results.assert_not_called()


@patch("cribl_cli.commands.search.time.sleep")
@patch("cribl_cli.commands.search.get_search_results")
@patch("cribl_cli.commands.search.get_search_status")
@patch("cribl_cli.commands.search.run_search")
@patch("cribl_cli.commands.search.get_client")
def test_search_poll_timeout(mock_client, mock_run, mock_status, mock_results, _sleep):
    mock_client.return_value = _client()
    mock_run.return_value = {"id": "job1"}
    mock_status.return_value = {"status": "running"}

    with patch("cribl_cli.commands.search.time.monotonic", side_effect=[0, 1, 2, 99]):
        result = _invoke(["search", "run", "-q", "x", "--poll", "--timeout", "5"])

    assert result.exit_code == 1
    assert "Timed out" in result.output
    mock_results.assert_not_called()


def test_finops_summary_with_no_usage_data():
    client = _client()
    client.get.return_value = _resp({"items": []})
    assert _build_summary([], 5) == {}

    with patch("cribl_cli.commands.finops.get_client", return_value=client):
        result = _invoke(["finops", "summary"])

    assert result.exit_code == 0, result.output
    assert "No license usage data" in result.output


@pytest.mark.parametrize("text", ["{not json", "[]"])
def test_unreadable_rc_is_an_error_not_an_empty_config(text):
    path = MagicMock(spec=Path)
    path.read_text.return_value = text

    with pytest.raises(ValueError, match="left untouched"):
        load_rc(path=path)


def test_config_set_refuses_to_overwrite_a_corrupt_rc():
    with patch("cribl_cli.commands.config_cmd.load_rc", side_effect=ValueError("bad rc")), \
         patch("cribl_cli.commands.config_cmd.save_rc") as mock_save:
        result = CliRunner().invoke(cli, ["config", "set", "--base-url", "https://x.cribl.cloud"])

    assert result.exit_code == 1
    mock_save.assert_not_called()


def test_error_detail_handles_non_object_json_body():
    request = httpx.Request("GET", "https://cribl.example.com/x")
    response = httpx.Response(400, json=["bad", "request"], request=request)
    err = httpx.HTTPStatusError("boom", request=request, response=response)

    assert _extract_http_error_detail(err) == {"status": 400, "detail": ["bad", "request"]}


# ---------------------------------------------------------------------------
# Metrics window, concurrency, timeout, search jobs
# ---------------------------------------------------------------------------


def test_metrics_coverage_flags_a_short_history():
    from cribl_cli.api.endpoints.edge_nodes import metrics_coverage

    ten_minutes = [{"time": f"2026-01-01T00:{m:02d}:00+00:00"} for m in range(10)]

    short = metrics_coverage(ten_minutes, 6 * 3600)
    assert short["covered_minutes"] == 10.0 and short["partial"] is True
    assert short["requested_minutes"] == 360.0

    full = metrics_coverage(ten_minutes, 600)
    assert full["partial"] is False

    assert metrics_coverage([], 600) == {
        "requested_minutes": 10.0, "covered_minutes": 0, "from": None, "to": None, "partial": True,
    }


def test_map_concurrent_keeps_order_and_isolates_failures():
    from cribl_cli.utils.concurrency import map_concurrent

    def fn(x):
        if x == 2:
            raise RuntimeError("boom")
        return x * 10

    out = map_concurrent(fn, [1, 2, 3])

    assert [(i, r) for i, r, _ in out] == [(1, 10), (2, None), (3, 30)]
    assert out[0][2] is None and isinstance(out[1][2], RuntimeError)
    assert map_concurrent(fn, []) == []


def _cpu_client(points_by_node, fail=()):
    """Client whose /master/workers lists the nodes and /w/<id>/system/metrics returns their points."""
    def fake_get(url, **kwargs):
        if url == "/api/v1/master/workers":
            return _resp({"items": [
                {"id": nid, "group": "g", "status": "healthy",
                 "info": {"hostname": nid, "freemem": 1, "totalmem": 2}}
                for nid in list(points_by_node) + list(fail)
            ]})
        for nid in fail:
            if f"/w/{nid}/" in url:
                raise httpx.ReadTimeout("timed out")
        for nid, minutes in points_by_node.items():
            if f"/w/{nid}/" in url:
                return _resp({"results": {"metrics": [
                    {"_time": [{"val": 1_800_000_000 + 60 * m}], "system.cpu_perc": [{"val": 5.0}]}
                    for m in range(minutes)
                ]}})
        raise AssertionError(url)
    client = _client()
    client.get.side_effect = fake_get
    return client


def test_health_cpu_reports_real_coverage_and_node_errors():
    client = _cpu_client({"short": 10, "full": 60}, fail=("slow",))

    with patch("cribl_cli.commands.health.get_client", return_value=client):
        result = _invoke(["health", "cpu", "--hours", "1", "--json"])

    assert result.exit_code == 0, result.output
    rows = {r["hostname"]: r for r in json.loads(result.output)}
    assert rows["short"]["covered_minutes"] == 10.0 and rows["short"]["partial_window"] is True
    assert rows["full"]["covered_minutes"] == 60.0 and rows["full"]["partial_window"] is False
    assert rows["slow"]["status"] == "error" and "timed out" in rows["slow"]["error"]


def test_health_cpu_text_says_when_the_window_is_partial():
    client = _cpu_client({"short": 10})

    with patch("cribl_cli.commands.health.get_client", return_value=client):
        result = _invoke(["health", "cpu", "--hours", "6"])

    assert "10m (partial)" in result.output
    assert "less history than the 6h requested" in result.output


def test_timeout_option_reaches_the_http_clients():
    with patch("cribl_cli.cli.load_config", return_value=MagicMock()), \
         patch("cribl_cli.cli.create_client") as mk, patch("cribl_cli.cli.create_management_client") as mk_mgmt, \
         patch("cribl_cli.cli.set_client"), patch("cribl_cli.cli.set_management_client"), \
         patch("cribl_cli.commands.workers.get_client", side_effect=RuntimeError("stop")):
        CliRunner().invoke(cli, ["--timeout", "90", "workers", "list"])
        assert mk.call_args.kwargs["timeout"] == 90
        assert mk_mgmt.call_args.kwargs["timeout"] == 90

        CliRunner().invoke(cli, ["workers", "list"])
        assert mk.call_args.kwargs["timeout"] == 30.0

        CliRunner().invoke(cli, ["workers", "list"], env={"CRIBL_TIMEOUT": "45"})
        assert mk.call_args.kwargs["timeout"] == 45


def _jobs_client(n):
    client = _client()
    client.get.return_value = _resp({"items": [
        {"id": f"j{i}", "status": "failed" if i == 3 else "completed", "timeCreated": i,
         "query": "q", "stages": ["x" * 1000]}
        for i in range(n)
    ], "count": n})
    return client


def test_search_jobs_defaults_to_a_recent_summary():
    with patch("cribl_cli.commands.search.get_client", return_value=_jobs_client(120)):
        result = _invoke(["search", "jobs"])

    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data["count"] == 50 and data["total"] == 120
    assert data["items"][0]["id"] == "j119"  # newest first
    assert "stages" not in data["items"][0]
    assert "Showing the 50 most recent of 120" in result.stderr


def test_search_jobs_full_status_and_no_limit():
    with patch("cribl_cli.commands.search.get_client", return_value=_jobs_client(120)):
        everything = json.loads(_invoke(["search", "jobs", "--limit", "0", "--full"]).stdout)
        failed = json.loads(_invoke(["search", "jobs", "--status", "failed"]).stdout)

    assert everything["count"] == 120 and "stages" in everything["items"][0]
    assert failed["total"] == 1 and failed["items"][0]["id"] == "j3"


# ---------------------------------------------------------------------------
# Issues found by the Opus 4.6 usability runs
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "src_type,expected",
    [("criblmetrics", "cribl:CriblMetrics"), ("cribl", "cribl:CriblMetrics"), ("syslog", "syslog:CriblMetrics")],
)
def test_route_input_filter_uses_the_real_input_id_prefix(src_type, expected):
    client = _client()

    def fake_get(url, **kwargs):
        if url.endswith("/system/inputs/CriblMetrics"):
            return _resp({"items": [{"id": "CriblMetrics", "type": src_type}]})
        return _resp({"items": [{"id": "default", "routes": [{"id": "all", "filter": "true", "final": True}]}]})

    client.get.side_effect = fake_get
    client.patch.return_value = _resp({})

    with patch("cribl_cli.commands.routes.get_client", return_value=client):
        result = _invoke(["routes", "create", "--id", "r", "--input", "CriblMetrics",
                          "--pipeline", "main", "--output", "default", "-g", "default"])

    assert result.exit_code == 0, result.output
    new_route = client.patch.call_args.kwargs["json"]["routes"][0]
    assert new_route["filter"] == f"__inputId=='{expected}'"


def test_health_cpu_makes_one_metrics_call_per_node_and_reports_its_window():
    client = _cpu_client({"n1": 10})
    # No freemem in the listing: the health report would look memory up per node.
    listing = client.get.side_effect("/api/v1/master/workers").json.return_value
    listing["items"][0]["info"].pop("freemem")
    inner = client.get.side_effect
    client.get.side_effect = lambda url, **kw: _resp(listing) if url == "/api/v1/master/workers" else inner(url, **kw)

    with patch("cribl_cli.commands.health.get_client", return_value=client):
        result = _invoke(["health", "cpu", "--hours", "6", "--threshold", "70", "--json"])

    metric_calls = [c for c in client.get.call_args_list if "/system/metrics" in c.args[0]]
    assert len(metric_calls) == 1
    row = json.loads(result.output)[0]
    assert row["threshold_pct"] == 70 and row["requested_hours"] == 6
    assert row["from"] and row["to"]


def test_timeout_error_points_at_the_timeout_option(capsys):
    from cribl_cli.utils.errors import handle_error

    with pytest.raises(SystemExit):
        handle_error(httpx.ReadTimeout("The read operation timed out"))

    payload = json.loads(capsys.readouterr().err)
    assert "--timeout" in payload["hint"] and "CRIBL_TIMEOUT" in payload["hint"]


def test_lake_commands_default_to_the_default_lake():
    client = _client()
    client.get.return_value = _resp({"items": []})

    with patch("cribl_cli.commands.command_factory.get_client", return_value=client):
        result = _invoke(["lake-datasets", "list"])

    assert result.exit_code == 0, result.output
    assert client.get.call_args.args[0] == "/api/v1/products/lake/lakes/default/datasets"


def test_workers_list_type_filter():
    client = _client()
    client.get.return_value = _resp({"items": [
        {"id": "default", "type": "stream"}, {"id": "fleet", "type": "edge"}, {"id": "legacy"},
    ], "count": 3})

    with patch("cribl_cli.commands.workers.get_client", return_value=client):
        edge = json.loads(_invoke(["workers", "list", "--type", "edge"]).output)
        stream = json.loads(_invoke(["workers", "list", "--type", "stream"]).output)
        everything = json.loads(_invoke(["workers", "list"]).output)

    assert [g["id"] for g in edge["items"]] == ["fleet"] and edge["count"] == 1
    assert [g["id"] for g in stream["items"]] == ["default", "legacy"]
    assert everything["count"] == 3


def test_workers_nodes_all_includes_edge_nodes():
    def fake_get(url, **kwargs):
        if url == "/api/v1/master/groups":
            return _resp({"items": [{"id": "wg", "type": "stream"}, {"id": "fleet", "type": "edge"}]})
        return _resp({"items": [
            {"id": "w1", "group": "wg", "info": {"hostname": "worker"}},
            {"id": "e1", "group": "fleet", "info": {"hostname": "edge"}},
        ]})
    client = _client()
    client.get.side_effect = fake_get

    with patch("cribl_cli.commands.workers.get_client", return_value=client):
        only_workers = json.loads(_invoke(["workers", "nodes"]).output)
        all_nodes = json.loads(_invoke(["workers", "nodes", "--all"]).output)

    assert [n["hostname"] for n in only_workers] == ["worker"]
    assert [n["hostname"] for n in all_nodes] == ["worker", "edge"]


def test_pipelines_list_no_packs():
    client = _client()
    client.get.return_value = _resp({"items": [{"id": "main"}, {"id": "pack:HelloPacks"}], "count": 2})

    with patch("cribl_cli.commands.pipelines.get_client", return_value=client):
        data = json.loads(_invoke(["pipelines", "list", "-g", "default", "--no-packs"]).output)

    assert data == {"items": [{"id": "main"}], "count": 1}


def _hc_client(nodes_by_group, inputs, outputs, per_node=None, fail_nodes=()):
    """Fake leader: groups, nodes, a group's inputs/outputs, and each node's own view."""
    per_node = per_node or {}

    def fake_get(url, **kwargs):
        if url == "/api/v1/master/groups":
            return _resp({"items": [{"id": g, "type": "stream"} for g in nodes_by_group]})
        if url == "/api/v1/master/workers":
            return _resp({"items": [
                {"id": n, "group": g, "status": "healthy", "info": {"hostname": n}}
                for g, ns in nodes_by_group.items() for n in ns
            ]})
        if "/api/v1/w/" in url:
            node = url.split("/api/v1/w/")[1].split("/")[0]
            if node in fail_nodes:
                raise httpx.ReadTimeout("timed out")
            kind = "inputs" if url.endswith("inputs") else "outputs"
            return _resp({"items": per_node.get(node, {}).get(kind, [])})
        if url.endswith("/system/inputs"):
            return _resp({"items": inputs})
        if url.endswith("/system/outputs"):
            return _resp({"items": outputs})
        raise AssertionError(url)

    client = _client()
    client.get.side_effect = fake_get
    return client


def _item(id_, health=None, **extra):
    return {"id": id_, "type": "syslog", **({"status": {"health": health}} if health else {}), **extra}


def _hc(args, client):
    with patch("cribl_cli.commands.health.get_client", return_value=client):
        return _invoke(["health", "check", *args])


def test_health_check_lists_unhealthy_items_with_the_nodes_they_are_on():
    client = _hc_client(
        {"default": ["n1", "n2", "n3"]},
        inputs=[_item("ok", "Green"), _item("off", "Red", disabled=True)],
        outputs=[_item("warn", "Yellow"), _item("down", "Red")],
        per_node={
            "n1": {"outputs": [_item("warn", "Green"), _item("down", "Red")]},
            "n2": {"outputs": [_item("warn", "Yellow"), _item("down", "Red")]},
            "n3": {"outputs": [_item("warn", "Green"), _item("down", "Red")]},
        },
    )

    result = _hc(["-g", "default"], client)

    rows = {r["id"]: r for r in json.loads(result.stdout)}
    assert set(rows) == {"warn", "down"}  # disabled Red item is not reported
    assert rows["warn"]["nodes_affected"] == ["n2"] and rows["warn"]["nodes_total"] == 3
    assert rows["down"]["nodes_affected"] == ["n1", "n2", "n3"]
    assert rows["down"]["kind"] == "destination" and rows["down"]["group"] == "default"
    assert "default: 2 unhealthy (1 active sources, 2 active destinations, 3 node(s))" in result.stderr


def test_health_check_healthy_group_prints_an_empty_json_list():
    client = _hc_client({"default": ["n1"]}, inputs=[_item("a", "Green")], outputs=[_item("b", "Green")])

    result = _hc(["-g", "default"], client)

    assert result.exit_code == 0
    assert json.loads(result.stdout) == []
    assert "default: all healthy" in result.stderr


def test_health_check_group_without_nodes_is_not_reported_healthy():
    """The leader says Green for a group nothing is running; the UI calls that No Metrics."""
    client = _hc_client({"empty": []}, inputs=[_item("a", "Green")], outputs=[_item("b", "Green")])

    result = _hc(["-g", "empty", "--summary"], client)

    data = json.loads(result.stdout)
    assert data["healthy"] is None and data["nodes"] == 0
    assert data["summary"]["sources"]["no_metrics"] == 1 and data["summary"]["sources"]["healthy"] == 0
    assert "no connected nodes" in result.stderr
    assert "all healthy" not in result.stderr


def test_health_check_summary_counts_match_the_ui_buckets():
    client = _hc_client(
        {"default": ["n1"]},
        inputs=[_item("g", "Green"), _item("r", "Red"), _item("y", "Yellow"),
                _item("d", "Green", disabled=True), _item("none")],
        outputs=[],
    )

    data = json.loads(_hc(["-g", "default", "--summary", "--no-by-node"], client).stdout)

    assert data["healthy"] is False
    assert data["summary"]["sources"] == {
        "total": 5, "disabled": 1, "healthy": 1, "warning": 1, "critical": 1, "no_metrics": 1,
    }
    assert "nodes_affected" not in data["unhealthy"][0]


def test_health_check_exit_codes_for_scripts():
    bad = _hc_client({"g": ["n1"]}, inputs=[_item("r", "Red")], outputs=[])
    good = _hc_client({"g": ["n1"]}, inputs=[_item("a", "Green")], outputs=[])
    empty = _hc_client({"g": []}, inputs=[_item("a", "Green")], outputs=[])

    assert _hc(["-g", "g"], bad).exit_code == 0
    assert _hc(["-g", "g", "--fail-on-unhealthy"], bad).exit_code == 2
    assert _hc(["-g", "g", "--fail-on-unhealthy"], good).exit_code == 0
    assert _hc(["-g", "g", "--fail-on-unhealthy"], empty).exit_code == 3


def test_health_check_all_groups_skips_groups_without_nodes():
    client = _hc_client({"a": ["n1"], "b": [], "c": ["n2"]}, inputs=[_item("r", "Red")], outputs=[])

    result = _hc(["--all-groups", "--no-by-node"], client)

    assert [(r["group"], r["id"]) for r in json.loads(result.stdout)] == [("a", "r"), ("c", "r")]
    assert "Skipping 1 group(s) with no connected nodes" in result.stderr


def test_health_check_survives_an_unreachable_node():
    client = _hc_client(
        {"g": ["n1", "slow"]}, inputs=[_item("r", "Red")], outputs=[],
        per_node={"n1": {"inputs": [_item("r", "Red")]}}, fail_nodes=("slow",),
    )

    result = _hc(["-g", "g"], client)

    row = json.loads(result.stdout)[0]
    assert result.exit_code == 0 and row["nodes_affected"] == ["n1"]
    assert "Could not read per-node status from: slow" in result.stderr


def test_health_check_without_group_says_which_group_it_checked():
    client = _hc_client({"first": ["n1"], "second": ["n2"]}, inputs=[], outputs=[])

    assert "No -g given; checking 'first'." in _hc([], client).stderr


def test_health_check_table_hides_an_empty_message_column():
    client = _hc_client({"default": ["n1", "n2"]}, inputs=[_item("s1", "Red")], outputs=[],
                        per_node={"n1": {"inputs": [_item("s1", "Red")]}, "n2": {"inputs": [_item("s1", "Green")]}})

    result = _hc(["-g", "default", "--table"], client)

    assert "s1" in result.stdout and "message" not in result.stdout
    assert "1/2: n1" in result.stdout


def test_health_check_explains_why_using_the_nodes_own_status():
    listener_down = {"health": "Red", "metrics": {"items": [
        {"name": "UDP", "address": "0.0.0.0:514", "status": {
            "health": "Red", "error": {"message": "Initialization error: bind EACCES 0.0.0.0:514",
                                       "details": {"error": {"message": "bind EACCES 0.0.0.0:514"}}}}},
        {"name": "TCP", "address": "0.0.0.0:514", "status": {"health": "Green"}},
    ]}}
    dns = {"health": "Red", "error": {"message": "Failed to resolve any hosts.", "details": {"error": {
        "message": "Failed to resolve any hosts.", "hint": "Check your dns settings."}}}}
    init = {"health": "Red", "error": {"message": "error initializing", "details": {"error": {"message": "No Bucket."}}}}
    client = _hc_client(
        {"g": ["n1"]},
        inputs=[_item("syslog", "Red"), _item("ghost", "Red")],
        outputs=[_item("http", "Red"), _item("s3", "Red")],
        per_node={"n1": {
            "inputs": [{"id": "syslog", "status": listener_down}, _item("ghost", "Green")],
            "outputs": [{"id": "http", "status": dns}, {"id": "s3", "status": init}],
        }},
    )

    rows = {r["id"]: r for r in json.loads(_hc(["-g", "g"], client).stdout)}

    assert rows["syslog"]["message"] == "UDP 0.0.0.0:514: Initialization error: bind EACCES 0.0.0.0:514"
    assert rows["http"]["message"] == "Failed to resolve any hosts. (Check your dns settings.)"
    assert rows["s3"]["message"] == "error initializing: No Bucket."
    # Leader says Red, the only node says Green: say so instead of guessing.
    assert rows["ghost"]["nodes_affected"] == [] and "all 1 node(s) report this item healthy" in rows["ghost"]["message"]


def test_health_check_counts_the_default_pointer_destination_as_healthy():
    client = _hc_client({"g": ["n1"]}, inputs=[], outputs=[{"id": "default", "type": "default", "status": {}}])

    data = json.loads(_hc(["-g", "g", "--summary"], client).stdout)

    assert data["summary"]["destinations"]["healthy"] == 1 and data["summary"]["destinations"]["no_metrics"] == 0


def test_health_check_reason_falls_back_to_endpoint_error_counts():
    from cribl_cli.commands.health import _status_reason

    status = {"health": "Yellow", "metrics": {"items": [
        {"name": "a:8088", "status": {"health": 0, "metrics": {"errorCount": 1}}},
        {"name": "b:8088", "status": {"health": 0, "metrics": {"errorCount": 0}}},
    ]}}

    assert _status_reason(status) == "a:8088: 1 send error(s)"
    assert _status_reason({"health": "Green"}) == "" and _status_reason(None) == ""


# ---------------------------------------------------------------------------
# Alignment with what the UI requests
# ---------------------------------------------------------------------------


def test_api_command_sends_every_repeated_query_parameter():
    """The UI sends filter=... twice; a dict would silently keep only the last."""
    client = _client()
    client.request.return_value = MagicMock(status_code=200, json=lambda: {})

    with patch("cribl_cli.commands.api.get_client", return_value=client):
        result = _invoke(["api", "GET", "/api/v1/x", "-q", "filter=a", "-q", "filter=b", "-q", "limit=1"])

    assert result.exit_code == 0, result.output
    assert client.request.call_args.kwargs["params"] == [("filter", "a"), ("filter", "b"), ("limit", "1")]


@pytest.mark.parametrize("cmd,module,path", [
    ("sources", "sources", "system/inputs"), ("destinations", "destinations", "system/outputs"),
])
def test_get_shows_the_aggregated_status_not_the_leaders_own(cmd, module, path):
    def fake_get(url, **kwargs):
        if url.endswith(f"{path}/x1"):  # single item: leader's own view, always Green
            return _resp({"items": [{"id": "x1", "type": "t", "status": {"health": "Green"}}]})
        return _resp({"items": [{"id": "other", "status": {"health": "Green"}},
                                {"id": "x1", "type": "t", "status": {"health": "Red"}}]})
    client = _client()
    client.get.side_effect = fake_get

    with patch(f"cribl_cli.commands.{module}.get_client", return_value=client):
        data = json.loads(_invoke([cmd, "get", "x1", "-g", "default"]).output)

    assert data["status"]["health"] == "Red"


def test_jobs_list_configs_reads_the_saved_collectors():
    client = _client()
    client.get.return_value = _resp({"items": [], "count": 0})

    with patch("cribl_cli.commands.jobs.get_client", return_value=client):
        _invoke(["jobs", "list-configs", "-g", "default"])

    assert client.get.call_args.args[0] == "/api/v1/m/default/lib/jobs"


def test_health_check_ignores_disconnected_nodes_and_counts_collectors():
    client = _hc_client({"g": ["gone"]}, inputs=[_item("a", "Green")], outputs=[])
    inner = client.get.side_effect

    def fake_get(url, **kwargs):
        if url == "/api/v1/master/workers":
            return _resp({"items": [{"id": "gone", "group": "g", "disconnected": True, "info": {"hostname": "gone"}}]})
        if url.endswith("/lib/jobs"):
            return _resp({"items": [{"id": "c1", "type": "collection"}, {"id": "c2", "type": "collection"},
                                    {"id": "s1", "type": "executor"}]})
        return inner(url, **kwargs)
    client.get.side_effect = fake_get

    data = json.loads(_hc(["-g", "g", "--summary"], client).stdout)

    assert data["nodes"] == 0 and data["healthy"] is None  # its only node is disconnected
    assert data["summary"]["collectors"] == {"total": 2}


def test_collectors_command_manages_saved_collectors():
    """`collectors` must use lib/jobs: /collectors only lists the collector types."""
    client = _client()
    client.get.return_value = _resp({"items": [{"id": "c1", "ttl": "4h", "collector": {"conf": {"a": 1}}}]})
    client.patch.return_value = _resp({})

    with patch("cribl_cli.commands.command_factory.get_client", return_value=client):
        _invoke(["collectors", "list", "-g", "g"])
        assert client.get.call_args.args[0] == "/api/v1/m/g/lib/jobs"
        result = _invoke(["collectors", "update", "c1", '{"collector": {"conf": {"b": 2}}}', "-g", "g"])

    assert result.exit_code == 0, result.output
    assert client.patch.call_args.args[0] == "/api/v1/m/g/lib/jobs/c1"
    assert client.patch.call_args.kwargs["json"]["collector"]["conf"] == {"a": 1, "b": 2}


def test_registry_paths_match_the_documented_api():
    """Paths confirmed against the tenant's OpenAPI spec and a live GET."""
    from cribl_cli.commands.registry import REGISTRY

    by_name = {r.name: r for r in REGISTRY}
    expected = {
        "protobuf-libs": ("group", "lib/protobuf-libraries"),
        "functions": ("group", "functions"),
        "encryption-keys": ("group", "system/keys"),
        "collectors": ("group", "lib/jobs"),
        "credentials": ("global", "system/credentials"),
        "outposts": ("global", "master/outposts"),
        "feature-flags": ("global", "settings/features"),
        "ai-settings": ("global", "ai/settings/features"),
        "auth-settings": ("global", "system/settings/auth"),
        "git-settings": ("global", "system/settings/git-settings"),
    }
    for name, (scope, path) in expected.items():
        assert (by_name[name].endpoint.scope, by_name[name].endpoint.path) == (scope, path), name
    # Read-only in the API: no write subcommands that could only 404.
    for name in ("protobuf-libs", "functions", "credentials", "outposts", "feature-flags", "ai-settings"):
        assert set(by_name[name].operations) == {"list", "get"}, name


def test_encryption_keys_are_left_out_of_a_default_group_export():
    from cribl_cli.utils.group_transfer import plan_resources

    included, skipped = plan_resources(is_fleet=False, include_sensitive=False)

    assert "encryption-keys" in skipped["sensitive"]
    assert "encryption-keys" not in [name for name, _ in included]


def test_jobs_run_starts_a_job_from_the_saved_collector():
    """There is no /jobs/{id}/run: a run is POST /jobs naming the saved config."""
    client = _client()
    client.get.return_value = _resp({"items": [{"id": "c1", "type": "collection"}]})
    client.post.return_value = _resp({"items": [{"id": "1.2.adhoc.c1"}]})

    with patch("cribl_cli.commands.jobs.get_client", return_value=client):
        result = _invoke(["jobs", "run", "c1", "-g", "g", "--mode", "preview"])

    assert result.exit_code == 0, result.output
    assert client.get.call_args.args[0] == "/api/v1/m/g/lib/jobs/c1"
    assert client.post.call_args.args[0] == "/api/v1/m/g/jobs"
    assert client.post.call_args.kwargs["json"] == {"id": "c1", "type": "collection", "run": {"mode": "preview"}}
