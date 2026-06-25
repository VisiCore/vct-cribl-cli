"""Tests for whole-group export/import (cribl_cli.utils.group_transfer)."""
from __future__ import annotations

from unittest.mock import MagicMock, patch
import httpx
from click.testing import CliRunner

from cribl_cli.cli import cli
from cribl_cli.utils.group_transfer import SENSITIVE, STREAM_ONLY, apply, collect, plan_resources, read_input, write_dir

def _mock_response(json_data, status_code=200):
    resp = MagicMock(spec=httpx.Response)
    resp.json.return_value = json_data
    resp.status_code = status_code
    resp.raise_for_status.return_value = None
    return resp

def _routing_get(group_entry, error_paths=None):
    error_paths = error_paths or {}
    def _get(url, *args, **kwargs):
        if url == "/api/v1/master/groups": return _mock_response({"items": [group_entry]})
        for needle, exc in error_paths.items():
            if url.endswith(needle): raise exc
        if url.endswith("/routes"): return _mock_response({"id": "default", "items": [{"id": "r1"}]})
        return _mock_response({"items": [{"id": "x"}]})
    return _get

def test_plan_resources_filtering():
    """Verify sensitive, stream-only, packs, and lookups are properly filtered/included."""
    inc, skip = plan_resources(is_fleet=False, include_sensitive=False)
    names = {n for n, _ in inc}
    assert not (names & SENSITIVE) and set(skip["sensitive"]) == set(SENSITIVE)
    assert "packs" not in names and "packs" in skip["omitted_by_default"]
    
    inc, skip = plan_resources(is_fleet=True, include_sensitive=True, include_packs=True)
    names = {n for n, _ in inc}
    assert SENSITIVE <= names and skip["sensitive"] == []
    assert not (names & STREAM_ONLY) and set(skip["stream_only"]) == set(STREAM_ONLY)
    assert "packs" in names and "packs" not in skip["omitted_by_default"]

def test_collect_aggregates_and_handles_errors():
    client = MagicMock(spec=httpx.Client)
    err = httpx.HTTPStatusError("500", request=MagicMock(), response=_mock_response({}, 500))
    client.get.side_effect = _routing_get({"id": "grp", "type": "stream", "isFleet": False}, {"lib/parsers": err})
    
    result = collect(client, "grp", include_packs=True)
    
    assert result["group"] == "grp" and "sources" in result["resources"] and "routes" in result["resources"]
    assert "parsers" in result["_meta"]["errors"] and "parsers" not in result["resources"]
    assert "packs" in result["resources"]

def test_collect_drops_builtin_items():
    """Cribl-shipped content (lib=='cribl' or destroyable is False) is filtered
    from an export so import doesn't choke on non-writable built-ins."""
    client = MagicMock(spec=httpx.Client)

    def _get(url, *args, **kwargs):
        if url == "/api/v1/master/groups":
            return _mock_response({"items": [{"id": "grp", "type": "stream", "isFleet": False}]})
        if url.endswith("/routes"):
            return _mock_response({"id": "default", "items": [{"id": "r1"}]})
        if url.endswith("/lib/parsers"):
            return _mock_response({"count": 4, "items": [
                {"id": "builtin", "lib": "cribl"},   # Cribl-shipped -> dropped
                {"id": "pack:foo"},                   # pack-owned -> dropped
                {"id": "mine", "lib": "custom"},
                {"id": "also-mine"},                  # no lib -> user content
            ]})
        if url.endswith("/collectors"):
            return _mock_response({"items": [
                {"id": "sys", "destroyable": False},  # built-in system object -> dropped
                {"id": "user", "destroyable": True},
            ]})
        return _mock_response({"items": []})

    client.get.side_effect = _get
    result = collect(client, "grp")

    parsers = result["resources"]["parsers"]
    assert {p["id"] for p in parsers["items"]} == {"mine", "also-mine"}
    assert parsers["count"] == 2  # wrapper count is corrected
    assert {c["id"] for c in result["resources"]["collectors"]["items"]} == {"user"}
    assert result["_meta"]["skipped"]["builtin"] == {"parsers": 2, "collectors": 1}

def test_write_read_roundtrip(tmp_path):
    result = {
        "group": "grp", "type": "stream", "isFleet": False,
        "resources": {"sources": {"items": [{"id": "s1"}]}},
        "_meta": {"exported": ["sources"], "skipped": {}, "errors": {}}
    }
    write_dir(result, tmp_path)
    payload = read_input(tmp_path)
    assert payload["group"] == "grp" and payload["resources"]["sources"] == {"items": [{"id": "s1"}]}

def test_write_dir_clears_stale_files(tmp_path):
    """Re-exporting removes JSON from a prior export (e.g. leftover secrets.json)."""
    result = {"group": "grp", "resources": {"sources": {"items": [{"id": "s1"}]}}, "_meta": {}}
    base = tmp_path / "grp"
    base.mkdir()
    (base / "secrets.json").write_text("{}")  # leftover from an earlier --include-sensitive run
    write_dir(result, tmp_path)
    assert not (base / "secrets.json").exists()
    assert (base / "sources.json").exists()

def test_apply_upserts_resources():
    client = MagicMock(spec=httpx.Client)
    not_found = _mock_response({}, 404)
    not_found.raise_for_status.side_effect = httpx.HTTPStatusError("404", request=MagicMock(), response=not_found)
    
    def _mock_get(url, *args, **kwargs):
        if url == "/api/v1/master/groups":
            return _mock_response({"items": [{"id": "target", "isFleet": False}]})
        return not_found

    client.get.side_effect = _mock_get
    client.post.return_value = _mock_response({"id": "p1"})
    
    payload = {"resources": {"parsers": {"items": [{"id": "p1", "type": "x"}]}, "packs": {"items": [{"id": "pack1"}]}}}
    
    # 1. Packs skipped by default
    report = apply(client, "target", payload)
    assert "parsers/p1" in report["created"] and client.post.call_count == 1
    assert "packs" in report["skipped"]
    
    # 2. Packs included with flag
    report2 = apply(client, "target", payload, with_packs=True)
    assert "packs/pack1" in report2["created"]

def test_apply_respects_resource_operations():
    """Read-only types are skipped; create-only types never PATCH an existing item."""
    client = MagicMock(spec=httpx.Client)

    def _mock_get(url, *args, **kwargs):
        if url == "/api/v1/master/groups":
            return _mock_response({"items": [{"id": "target", "isFleet": False}]})
        return _mock_response({"id": "s1"})  # every resource GET reports "exists"

    client.get.side_effect = _mock_get

    payload = {"resources": {
        "executors": {"items": [{"id": "e1"}]},  # list/get only -> read-only
        "scripts": {"items": [{"id": "s1"}]},     # create-only, already exists
    }}

    report = apply(client, "target", payload)

    assert "executors" in report["skipped"]          # whole type skipped
    assert "scripts/s1" in report["skipped"]          # existing create-only item left alone
    assert report["updated"] == [] and report["failed"] == {}
    client.patch.assert_not_called()


@patch("cribl_cli.commands.groups.get_client")
def test_import_deploy_requires_yes(mock_get_client):
    mock_get_client.return_value = MagicMock(spec=httpx.Client)
    assert CliRunner().invoke(cli, ["groups", "import", "grp", "--deploy"], input="{}").exit_code != 0
