"""Keep the CLI honest against the bundled API reference.

`cribl_cli/data/api_paths.json` is Cribl's API reference in compact form
(regenerate with scripts/update_api_paths.py). These tests fail when a command
is pointed at a path the API does not have, or when coverage goes backwards.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import click
import httpx
import pytest
from click.testing import CliRunner

from cribl_cli.cli import cli
from cribl_cli.commands.api import build_path
from cribl_cli.utils.api_index import cli_endpoints, coverage, load_operations, normalize

# Endpoints the CLI calls that the reference does not list. Each one is either
# confirmed working against a live system or a known problem awaiting a fix --
# adding to this list should be a deliberate decision, not a way to go green.
KNOWN_UNDOCUMENTED = {
    # Confirmed working, just not in the reference:
    ("GET", "/edge/events/{}"),            # per-source events on an Edge node
    ("GET", "/edge/kube-logs/{}"),         # per-container logs on an Edge node
    ("GET", "/search/notebooks/{}/{}"),    # .../acl and .../acl/teams (path built from a variable)
    ("POST", "/search/notebooks/{}/{}"),   # .../acl/apply and .../acl/teams/apply
    ("PATCH", "/routes"),                  # legacy flat route table; wrapped tables use /routes/{id}
    ("GET", "/{}"),                        # health check: /system/inputs|outputs built from a variable
}

# Raise this when coverage grows; it must never need lowering.
MIN_COVERED = 480


def test_every_command_calls_a_documented_endpoint():
    unknown = set(coverage()["unknown"])
    # Group resources are also offered inside packs (-P); the reference only
    # documents some of those pack paths, so they are not held against a command.
    unknown = {k for k in unknown if not k[1].startswith("/p/{}")}

    surprises = unknown - KNOWN_UNDOCUMENTED
    assert not surprises, (
        "These commands call paths the API reference does not list (typo or renamed "
        f"endpoint?): {sorted(surprises)}. Find the right path with `cribl api-spec search`."
    )
    stale = KNOWN_UNDOCUMENTED - unknown
    assert not stale, f"No longer called or now documented; remove from KNOWN_UNDOCUMENTED: {sorted(stale)}"


def test_coverage_does_not_go_backwards():
    report = coverage()
    assert len(report["covered"]) >= MIN_COVERED, (
        f"Only {len(report['covered'])} documented endpoints have a command (was {MIN_COVERED})."
    )
    assert len(report["covered"]) + len(report["missing"]) == len({
        (op["method"], normalize(op["path"])) for op in load_operations()
    })


def test_index_has_only_reference_data():
    ops = load_operations()
    assert len(ops) > 900
    assert all(set(op) == {"method", "path", "tag", "summary"} for op in ops)
    assert all(op["path"].startswith("/") and "://" not in op["path"] for op in ops)


def test_normalize_makes_request_and_reference_paths_comparable():
    assert normalize("/api/v1/m/{group}/lib/jobs?limit=1") == "/lib/jobs"
    assert normalize("/api/v1/m/{group}/lib/jobs/{id}") == normalize("/lib/jobs/{id}") == "/lib/jobs/{}"
    assert normalize("/api/v1/w/{node}/system/info") == "/system/info"
    assert ("GET", "/lib/jobs") in cli_endpoints()


# ---------------------------------------------------------------------------
# cribl api
# ---------------------------------------------------------------------------


def test_build_path_accepts_reference_style_and_full_paths():
    assert build_path("/system/users") == "/api/v1/system/users"
    assert build_path("/pipelines", "default") == "/api/v1/m/default/pipelines"
    assert build_path("/api/v1/system/users") == "/api/v1/system/users"
    assert build_path("/static/swagger/openapi.json") == "/static/swagger/openapi.json"
    with pytest.raises(click.BadParameter):
        build_path("/api/v1/pipelines", "default")
    with pytest.raises(click.BadParameter):
        build_path("pipelines")


def _api(args, response=None, **kwargs):
    client = MagicMock(spec=httpx.Client)
    client.request.return_value = response or httpx.Response(200, json={"ok": True})
    with patch("cribl_cli.cli.load_config", side_effect=ValueError("no config in tests")), \
         patch("cribl_cli.commands.api.get_client", return_value=client):
        result = CliRunner().invoke(cli, ["api", *args], **kwargs)
    return result, client


def test_api_group_option_and_body_from_file(tmp_path):
    body = tmp_path / "body.json"
    body.write_text('{"id": "r1"}')

    result, client = _api(["POST", "/lib/regex", "-g", "default", "-d", f"@{body}"])

    assert result.exit_code == 0, result.output
    call = client.request.call_args
    assert call.args == ("POST", "/api/v1/m/default/lib/regex")
    assert call.kwargs["json"] == {"id": "r1"}


def test_api_body_from_stdin():
    result, client = _api(["PATCH", "/system/settings/conf", "-d", "@-"], input='{"a": 1}')

    assert result.exit_code == 0, result.output
    assert client.request.call_args.kwargs["json"] == {"a": 1}


def test_api_upload_sends_raw_bytes(tmp_path):
    f = tmp_path / "hosts.csv"
    f.write_bytes(b"host,owner\nweb1,ops\n")

    result, client = _api(["PUT", "/system/lookups", "-g", "default", "-q", "filename=hosts.csv", "--upload", str(f)])

    assert result.exit_code == 0, result.output
    kwargs = client.request.call_args.kwargs
    assert kwargs["content"] == b"host,owner\nweb1,ops\n"
    assert kwargs["headers"]["Content-Type"] == "application/octet-stream"
    assert kwargs["params"] == [("filename", "hosts.csv")]
    assert "json" not in kwargs


def test_api_output_saves_binary_response(tmp_path):
    out = tmp_path / "pack.crbl"
    payload = bytes(range(256))

    result, _ = _api(["GET", "/packs/p1/export", "-g", "default", "-o", str(out)],
                     response=httpx.Response(200, content=payload))

    assert result.exit_code == 0, result.output
    assert out.read_bytes() == payload
    assert json.loads(result.output) == {"saved": str(out), "bytes": 256, "status": 200}


def test_api_rejects_data_and_upload_together(tmp_path):
    f = tmp_path / "x.bin"
    f.write_bytes(b"x")

    result, client = _api(["POST", "/x", "-d", "{}", "--upload", str(f)])

    assert result.exit_code != 0
    client.request.assert_not_called()


def test_api_exits_1_on_http_error_but_prints_the_body():
    result, _ = _api(["GET", "/nope"], response=httpx.Response(404, json={"message": "not found"}))

    assert result.exit_code == 1
    assert "not found" in result.output


# ---------------------------------------------------------------------------
# cribl api-spec
# ---------------------------------------------------------------------------


def _spec(args):
    with patch("cribl_cli.cli.load_config", side_effect=ValueError("no config in tests")):
        return CliRunner().invoke(cli, ["api-spec", *args])


def test_api_spec_search_matches_all_words_and_gives_the_call():
    result = _spec(["search", "lookups", "upload", "--limit", "0"])

    data = json.loads(result.stdout)
    assert data["total"] >= 1
    assert all("lookups" in (r["path"] + r["summary"]).lower() for r in data["items"])
    row = next(r for r in data["items"] if r["method"] == "PUT" and r["path"] == "/system/lookups")
    assert row["call"] == "cribl api PUT /system/lookups"


def test_api_spec_search_filters_and_reports_commands():
    covered = json.loads(_spec(["search", "--tag", "pipelines", "--method", "GET", "--limit", "0"]).stdout)
    assert covered["items"] and all(r["tag"] == "pipelines" and r["method"] == "GET" for r in covered["items"])
    assert any(r["has_command"] for r in covered["items"])

    missing = json.loads(_spec(["search", "--missing", "--limit", "0"]).stdout)
    assert missing["items"] and not any(r["has_command"] for r in missing["items"])


def test_api_spec_search_limit_notes_truncation():
    result = _spec(["search", "system", "--limit", "3"])

    data = json.loads(result.stdout)
    assert data["count"] == 3 and data["total"] > 3
    assert "Showing 3 of" in result.stderr


def test_api_spec_tags_counts_add_up():
    rows = json.loads(_spec(["tags"]).stdout)

    assert sum(r["endpoints"] for r in rows) == len(load_operations())
    assert all(0 <= r["with_command"] <= r["endpoints"] for r in rows)
