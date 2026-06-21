"""Export and import all config for a single worker group or edge fleet.

A worker group and an edge fleet are the same API object — an entry in
``/api/v1/master/groups`` whose config lives under ``/api/v1/m/{group}/…``
(a fleet is just one with ``isFleet: true``). This module pulls every
group-scoped resource for one such object (export) and pushes it back into
another (import).

Resource → endpoint mappings are sourced from ``commands/registry.py`` so the
two never drift. Sensitive resources (secrets, credentials, certificates) are
excluded by default; stream-only resources are skipped for edge fleets. Routes
(a single wholesale-replaced table) and packs (need their binary archive) get
special handling on import. Everything skipped or failed is reported in the
``_meta`` block — the export is never silently incomplete.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx

from cribl_cli.api.endpoint_factory import EndpointConfig, Endpoints
from cribl_cli.api.endpoints.routes import list_routes, replace_route_table
from cribl_cli.commands.registry import ALL_OPS, REGISTRY
from cribl_cli.utils.validation import deep_merge

# Group-scoped resources not declared in the registry (they have hand-written
# command modules), mapped to their API path under /api/v1/m/{group}/.
HANDWRITTEN_GENERIC: dict[str, str] = {
    "sources": "system/inputs",
    "destinations": "system/outputs",
    "pipelines": "pipelines",
    "packs": "packs",
}

# Excluded from a default export; opt in with include_sensitive=True.
SENSITIVE: frozenset[str] = frozenset({"secrets", "credentials", "certificates"})

# Not applicable to edge fleets (Stream-only), skipped when isFleet is True.
STREAM_ONLY: frozenset[str] = frozenset(
    {"collectors", "db-connections", "hmac-functions", "executors", "functions"}
)

# Server-managed fields stripped before any write.
SERVER_FIELDS: tuple[str, ...] = ("status", "notifications")

# Dependency order for import: library items first, then pipelines, then
# inputs/outputs/collectors, then notifications, then routes last. Names absent
# here fall back to alphabetical after the ordered ones. Mirrors the ordering
# used by the cribl-migration tool.
IMPORT_ORDER: tuple[str, ...] = (
    "packs",
    "lookups",
    "regex",
    "event-breakers",
    "parsers",
    "global-vars",
    "grok",
    "schemas",
    "parquet-schemas",
    "db-connections",
    "hmac-functions",
    "appscope",
    "conditions",
    "protobuf-libs",
    "sds-rules",
    "sds-rulesets",
    "samples",
    "scripts",
    "functions",
    "executors",
    "pipelines",
    "sources",
    "destinations",
    "collectors",
    "notifications",
    "alert-monitors",
    "routes",
)

# Informational caveats: object config is exported, file payloads are not.
BINARY_CAVEAT: tuple[str, ...] = (
    "packs (install archive .crbl not exported/imported)",
    "lookups (CSV/binary file contents not exported)",
)


def _registry_group_configs() -> dict[str, EndpointConfig]:
    return {
        reg.name: reg.endpoint
        for reg in REGISTRY
        if reg.endpoint.scope == "group" and "list" in reg.operations
    }


# name -> EndpointConfig for every generic (non-routes) group resource.
RESOURCE_CONFIGS: dict[str, EndpointConfig] = {
    **{name: EndpointConfig("group", path) for name, path in HANDWRITTEN_GENERIC.items()},
    **_registry_group_configs(),
}

# name -> write operations the API actually supports, sourced from the registry
# so it never drifts. apply() uses this to skip read-only resources (no create
# and no update) and to avoid PATCHing create-only ones. Hand-written generics
# (sources/destinations/pipelines/packs) support full CRUD.
RESOURCE_OPERATIONS: dict[str, frozenset[str]] = {
    **{name: frozenset(ALL_OPS) for name in HANDWRITTEN_GENERIC},
    **{reg.name: frozenset(reg.operations) for reg in REGISTRY if reg.endpoint.scope == "group"},
}


def _order_key(name: str) -> tuple[int, str]:
    try:
        return (IMPORT_ORDER.index(name), "")
    except ValueError:
        return (len(IMPORT_ORDER), name)


def plan_resources(
    is_fleet: bool, include_sensitive: bool, include_packs: bool = False, include_lookups: bool = False
) -> tuple[list[tuple[str, EndpointConfig]], dict[str, list[str]]]:
    """Return (included generic resources in dependency order, skipped-by-reason)."""
    included: list[tuple[str, EndpointConfig]] = []
    skipped: dict[str, list[str]] = {"sensitive": [], "stream_only": [], "omitted_by_default": []}

    for name in sorted(RESOURCE_CONFIGS, key=_order_key):
        if name in SENSITIVE and not include_sensitive:
            skipped["sensitive"].append(name)
        elif name in STREAM_ONLY and is_fleet:
            skipped["stream_only"].append(name)
        elif name in {"packs", "lookups"} and not (include_packs if name == "packs" else include_lookups):
            skipped["omitted_by_default"].append(name)
        else:
            included.append((name, RESOURCE_CONFIGS[name]))

    return included, skipped


def resolve_group_meta(client: httpx.Client, group_id: str) -> dict[str, Any]:
    """Look up a group/fleet entry in /master/groups to read its type and isFleet."""
    resp = client.get("/api/v1/master/groups")
    resp.raise_for_status()
    items = resp.json().get("items", [])
    for entry in items:
        if entry.get("id") == group_id:
            return entry
    available = ", ".join(e.get("id", "?") for e in items) or "(none)"
    raise ValueError(f"Group or fleet '{group_id}' not found. Available: {available}")


def collect(
    client: httpx.Client, group_id: str, *, include_sensitive: bool = False,
    include_packs: bool = False, include_lookups: bool = False
) -> dict[str, Any]:
    """Fetch every in-scope resource for one group/fleet into a single payload."""
    meta = resolve_group_meta(client, group_id)
    is_fleet = bool(meta.get("isFleet", False))
    included, skipped = plan_resources(is_fleet, include_sensitive, include_packs, include_lookups)

    resources: dict[str, Any] = {}
    exported: list[str] = []
    errors: dict[str, str] = {}

    for name, cfg in included:
        try:
            resources[name] = Endpoints(cfg).list(client, group_id)
            exported.append(name)
        except httpx.HTTPError as exc:
            errors[name] = f"HTTP Error: {exc}"
        except Exception as exc:  # noqa: BLE001 — report per-resource, keep going
            errors[name] = str(exc)

    # Routes: a single normalized table document, always part of an export.
    try:
        resources["routes"] = list_routes(client, group_id)
        exported.append("routes")
    except httpx.HTTPError as exc:
        errors["routes"] = f"HTTP Error: {exc}"
    except Exception as exc:  # noqa: BLE001
        errors["routes"] = str(exc)

    return {
        "group": group_id,
        "type": meta.get("type", "stream"),
        "isFleet": is_fleet,
        "resources": resources,
        "_meta": {
            "exported": exported,
            "skipped": {**skipped, "binary_content": list(BINARY_CAVEAT)},
            "errors": errors,
        },
    }


def _items(value: Any) -> list[dict[str, Any]]:
    """Normalize a list-endpoint payload to a list of resource dicts."""
    if isinstance(value, dict) and "items" in value:
        return [i for i in value["items"] if isinstance(i, dict)]
    if isinstance(value, list):
        return [i for i in value if isinstance(i, dict)]
    return []


def _strip(obj: dict[str, Any]) -> dict[str, Any]:
    """Drop server-computed fields before writing an object back.

    ``status`` and ``notifications`` are populated by the server and are not
    user-writable; sending them on a create/update can make the API reject the
    request, so they are removed from every payload we push.
    """
    out = dict(obj)
    for field in SERVER_FIELDS:
        out.pop(field, None)
    return out


def _upsert_item(
    client: httpx.Client, target_id: str, cfg: EndpointConfig, item: dict[str, Any],
    *, can_update: bool = True,
) -> str:
    """Create or merge-update a single resource.

    Returns 'created', 'updated', or 'skipped' (the resource already exists but
    its type has no update operation, so it is left untouched rather than
    PATCHed against an endpoint that would reject it).
    """
    endpoints = Endpoints(cfg)
    resource_id = item.get("id")
    incoming = _strip(item)

    if resource_id:
        try:
            existing = endpoints.get(client, target_id, resource_id)
        except httpx.HTTPStatusError as exc:
            if exc.response is not None and exc.response.status_code == 404:
                endpoints.create(client, target_id, incoming)
                return "created"
            raise
        if not can_update:
            return "skipped"
        if isinstance(existing, dict) and "items" in existing:
            existing = existing["items"][0] if existing["items"] else {}
        merged = deep_merge(_strip(existing) if isinstance(existing, dict) else {}, incoming)
        endpoints.update(client, target_id, resource_id, merged)
        return "updated"

    endpoints.create(client, target_id, incoming)
    return "created"


def _apply_routes(
    client: httpx.Client, target_id: str, routes_value: Any
) -> int:
    """Replace the target route table's items with the imported routes (opt-in)."""
    new_items = _items(routes_value)
    replace_route_table(client, target_id, new_items)
    return len(new_items)


def apply(
    client: httpx.Client,
    target_id: str,
    payload: dict[str, Any],
    *,
    with_routes: bool = False,
    with_packs: bool = False,
    with_lookups: bool = False,
) -> dict[str, Any]:
    """Upsert every resource in *payload* into the target group/fleet."""
    resources: dict[str, Any] = payload.get("resources", {})
    report: dict[str, Any] = {
        "target": target_id,
        "created": [],
        "updated": [],
        "failed": {},
        "skipped": {},
    }

    meta = resolve_group_meta(client, target_id)
    is_fleet = bool(meta.get("isFleet", False))

    for name in sorted(resources, key=_order_key):
        value = resources[name]
        if name in STREAM_ONLY and is_fleet:
            report["skipped"][name] = f"skipped stream-only resource type for fleet '{target_id}'"
            continue

        if name == "routes":
            if not with_routes:
                report["skipped"]["routes"] = "route table is wholesale-replaced; pass --with-routes"
                continue
            try:
                count = _apply_routes(client, target_id, value)
                report["updated"].append(f"routes ({count} routes)")
            except httpx.HTTPError as exc:
                report["failed"]["routes"] = f"HTTP Error: {exc}"
            except Exception as exc:  # noqa: BLE001
                report["failed"]["routes"] = str(exc)
            continue

        if name in {"packs", "lookups"} and not (with_packs if name == "packs" else with_lookups):
            report["skipped"][name] = f"{name} skipped; pass --with-{name} to import their JSON configs"
            continue

        cfg = RESOURCE_CONFIGS.get(name)
        if cfg is None:
            report["skipped"][name] = "unknown resource type"
            continue

        ops = RESOURCE_OPERATIONS.get(name, frozenset(ALL_OPS))
        if "create" not in ops and "update" not in ops:
            report["skipped"][name] = "read-only resource type (not writable via API)"
            continue
        can_update = "update" in ops

        for item in _items(value):
            ref = f"{name}/{item.get('id', '?')}"
            try:
                outcome = _upsert_item(client, target_id, cfg, item, can_update=can_update)
                if outcome == "skipped":
                    report["skipped"][ref] = "exists; resource type has no update operation"
                else:
                    report[outcome].append(ref)
            except httpx.HTTPError as exc:
                report["failed"][ref] = f"HTTP Error: {exc}"
            except Exception as exc:  # noqa: BLE001
                report["failed"][ref] = str(exc)

    return report


def write_dir(result: dict[str, Any], out_dir: str | Path) -> Path:
    """Write one file per resource type under <out_dir>/<group>/, plus _meta.json.

    The directory and files are locked to owner-only permissions (0700/0600) so
    exports taken with --include-sensitive are not left world-readable, matching
    how the CLI protects ~/.criblrc.

    Any JSON left from a previous export of the same group is removed first, so a
    file written by an earlier --include-sensitive run (e.g. secrets.json) can't
    linger and get re-imported once the user re-exports without that flag.
    """
    base = Path(out_dir) / str(result.get("group", "group"))
    base.mkdir(parents=True, exist_ok=True)
    base.chmod(0o700)
    for stale in base.glob("*.json"):
        stale.unlink()
    for name, value in result.get("resources", {}).items():
        f = base / f"{name}.json"
        f.write_text(json.dumps(value, indent=2))
        f.chmod(0o600)
    meta = {k: v for k, v in result.items() if k != "resources"}
    meta_file = base / "_meta.json"
    meta_file.write_text(json.dumps(meta, indent=2))
    meta_file.chmod(0o600)
    return base


def read_input(path: str | Path) -> dict[str, Any]:
    """Read an export payload from a single JSON file or a write_dir() directory."""
    p = Path(path)
    if p.is_file():
        return json.loads(p.read_text())
    if not p.is_dir():
        raise ValueError(f"Input path not found: {path}")

    group_dir = p
    if not (p / "_meta.json").exists():
        subdirs = [c for c in p.iterdir() if c.is_dir()]
        if len(subdirs) == 1:
            group_dir = subdirs[0]
        elif len(subdirs) > 1:
            names = ", ".join(sorted(c.name for c in subdirs))
            raise ValueError(
                f"Ambiguous import directory '{path}': no _meta.json and multiple "
                f"group subdirectories ({names}). Point --in at a specific "
                f"<out-dir>/<group> directory."
            )

    resources: dict[str, Any] = {}
    meta: dict[str, Any] = {}
    for f in sorted(group_dir.glob("*.json")):
        data = json.loads(f.read_text())
        if f.name == "_meta.json":
            meta = data
        else:
            resources[f.stem] = data

    payload = {"resources": resources}
    payload.update({k: v for k, v in meta.items() if k != "resources"})
    return payload


def format_caveat(result: dict[str, Any]) -> str:
    """Build a concise human-readable caveat summary for stderr."""
    m = result.get("_meta", {})
    skipped = m.get("skipped", {})
    lines = [f"Exported {len(m.get('exported', []))} resource type(s) for '{result.get('group')}'."]
    if skipped.get("sensitive"):
        lines.append(f"  Excluded (sensitive, use --include-sensitive): {', '.join(skipped['sensitive'])}")
    if skipped.get("omitted_by_default"):
        lines.append(f"  Excluded (default): {', '.join(skipped['omitted_by_default'])} (use --include-packs/--include-lookups)")
    if skipped.get("stream_only"):
        lines.append(f"  Skipped (Stream-only, not on this fleet): {', '.join(skipped['stream_only'])}")
    if skipped.get("binary_content"):
        lines.append(f"  Not captured: {'; '.join(skipped['binary_content'])}")
    if m.get("errors"):
        lines.append(f"  Failed to fetch: {', '.join(m['errors'])}")
    return "\n".join(lines)
