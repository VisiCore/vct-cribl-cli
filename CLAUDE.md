# CLAUDE.md

## Quick Reference

- **Install:** `pip install -e ".[dev]"` (editable with dev deps)
- **Run:** `bin/cribl <command>` or `python -m cribl_cli <command>`
- **Test:** `pytest` (unit only) or `pytest -m integration` (needs `CRIBL_INTEGRATION_TEST=true` + live credentials)
- **Python:** 3.10+
- **Deps:** click, httpx, tabulate | Dev: pytest, responses, pytest-mock

## Architecture

Python CLI built with Click. Two kinds of commands:

1. **Hand-written (28):** `cribl_cli/commands/*.py` — complex operations
   (workers, groups export/import, routes, search, edge, health report,
   ingest dashboard, billing, finops, etc.)
2. **Factory-generated (76):** Declared in `commands/registry.py`, built by `commands/command_factory.py` — standard CRUD

Key modules:

- `cli.py` — Click group (`CriblCLI`), registers all commands, skips auth for `config` subcommand
- `api/client.py` — httpx client with `AuthTransport` and `DryRunTransport`
- `api/endpoint_factory.py` — generic CRUD for four scope types (group/global/search/lake)
- `config/loader.py` — loads `~/.criblrc` JSON profiles; priority: CLI flags > env vars > profile
- `auth/oauth.py` — OAuth2 cloud auth (audience: `https://api.cribl.cloud`) + local auth
- `output/formatter.py` — JSON (default) or `--table` (tabulate)

## API Scopes

| Scope    | URL pattern                                         |
|----------|-----------------------------------------------------|
| `group`  | `/api/v1/m/{group}/{path}`                          |
| `global` | `/api/v1/{path}`                                    |
| `search` | `/api/v1/m/{group}/search/{path}`                   |
| `lake`   | `/api/v1/products/lake/lakes/{lakeId}/{path}`       |

## CLI Commands

Worker groups are listed and managed via `workers` (there is no `groups list`).
The `groups` command is separate: it exports and imports an entire worker group's
or edge fleet's config. Both are the same API object — a fleet is a group with
`isFleet: true`.

**Hand-written commands:** alerts, api, api-spec, apps, billing, config, destinations, edge, finops,
groups, health (check, report, cpu), ingest (dashboard, query), jobs, kms,
license-usage, logger, metrics, notebooks, overview, packs, pipelines, preview,
profiler, routes, search, sources, system, version, workers

**Key subcommands:**

- `apps list|get|check|install|upgrade|uninstall|backend-status|endpoints|invoke` —
  App Platform. `install`/`upgrade`/`check` accept a local `.tgz`/`.crbl` (staged via
  `PUT /apps` first), an `https://` URL, or `git+<repo>`. `invoke <app> <endpoint>` calls
  `/api/v1/a/{app}/endpoints/{name}`. Apps are global (no `-g`).
- `workers list` — list every group, fleets included (`--type stream|edge|search|outpost` narrows it); `workers nodes` — list Stream worker nodes (supports `-g`; `--all` adds Edge nodes)
- `edge nodes` — list individual edge nodes (supports `-f` fleet filter)
- `groups export <group>` — pull all config for one worker group or edge fleet
  (JSON to stdout, or `--out-dir` for one file per resource type); `groups import
  <group>` — push it back (see Safety Rules)
- `notebooks acl <id>` — list a notebook's explicit member + team sharing grants;
  `notebooks share <id> <principal> [--team] [--permission maintainer|read]` —
  grant access; `notebooks unshare <id> <principal> [--team]` — revoke it.
  Members are internal ids (`auth0|…`, not emails); teams use `--team`. Empty ACLs
  mean no explicit grants — access is then via product roles (Search Admins inherit
  Maintainer on every notebook), which `acl` does not list.

**Factory-generated commands (standard CRUD):** ai-settings, alert-history,
alert-monitors, alert-silences, appscope, auth-settings, banners, certificates,
collector-types, collectors, conditions, credentials, dashboard-categories,
dashboards, dataset-provider-types, dataset-providers, dataset-rulesets,
datasets, datatype-rulesets, datatypes, db-connections, dsd-connections,
encryption-keys, event-breakers, executors, feature-flags, federated-search-
engines, functions, git-settings, global-vars, grok, hmac-functions, iometrics,
lake-datasets, lakehouse-config-profiles, lakehouse-dataset-access, lakehouse-
monitors, lakehouse-shared-configs, licenses, local-search-engines, local-
search-sources, lookups, macros, mcp-servers, mdt-devices, messages, notebook-
templates, notification-targets, notifications, outposts, parquet-schemas,
parsers, policies, private-keys, processes, profiler-captures, projects,
protobuf-libs, provisioning-tokens, regex, roles, samples, saved-searches,
schemas, scripts, sds-rules, sds-rulesets, secret-folders, secret-stores,
secrets, storage-locations, subscriptions, teams, trust-policies, usage-groups,
users

## Safety Rules

- **Never replace the route table wholesale from `routes`.** `routes create`
  fetches existing routes, inserts before the catch-all, then updates. The one
  deliberate exception is `groups import --with-routes` — a high-risk, explicit
  opt-in that replaces the whole table via `replace_route_table()`.
- **Always confirm before deploying.** `version deploy` and `workers deploy` push
  config to live workers and require `--yes`; so do `system restart|reload|upgrade`.
- **Writes need an explicit group.** `resolve_group(..., write=True)` refuses to
  guess when more than one group exists; reads still default to the first group.
- **`groups import` is staged, never deployed.** It upserts config but never
  auto-commits or deploys; routes are skipped unless `--with-routes`, and
  `--deploy` requires `--yes`. If any item fails, nothing is committed or
  deployed and the exit code is 1. An empty/malformed `routes` payload is
  refused rather than replacing the table with nothing. Review with
  `version status`/`diff` first.
- **`groups export` excludes secrets by default.** Secrets, certificates, and
  encryption keys are omitted unless `--include-sensitive` (credentials are
  workspace-wide, not part of a group); what was skipped or
  failed is always reported in the `_meta` block.
- Cloud OAuth audience is always `https://api.cribl.cloud`, not the org-specific URL.

## Conventions

- New CRUD resources go in `commands/registry.py` — only write a hand-written command file if the resource needs custom logic.
- Merge-on-update pattern: fetch existing object, strip server-only fields
  (`status`, `notifications`), deep-merge user updates (nested dicts are merged
  recursively, not replaced). Use `merge_update()` from `utils/validation.py` —
  never `{**existing, **updates}`.
- Route PATCHes send the fetched table back with only `routes` replaced, so
  table-level `groups` and `comments` survive.
- `--dry-run` sends reads (GET), then logs the first write to stderr and raises
  `DryRunAbort` (caught by error handler, exits 0).
- Commands that need the config read it with `config_from_context()` (honours
  `-p/--profile`), not a bare `load_config()`.
- Per-node fan-out (node metrics, log scans) goes through `map_concurrent()` in
  `utils/concurrency.py`; one failing or slow node must not block or abort the rest.
- Node metrics history is short (Stream workers keep ~10 minutes). Anything that
  reports over a time window must say what it actually covered — use
  `metrics_coverage()` (`covered_minutes`, `partial_window`).
- `--timeout` / `CRIBL_TIMEOUT` sets the per-request timeout (default 30s).
- Config tests mock the filesystem to avoid touching real `~/.criblrc`.
- `health check` lists unhealthy sources/destinations for a group (`-g`) or every
  group with nodes (`--all-groups`) as a JSON list (`[]` when none; notes go to
  stderr). Health is the leader's worst-across-nodes value (matches the UI's
  Critical/Warning counts); each item is then enriched from every node's own
  status with `nodes_affected` and a `message` giving the reason. A group with no
  connected nodes has no health data and is never reported healthy. `--summary`
  adds per-group counts; `--fail-on-unhealthy` exits 2 (unhealthy) or 3 (no nodes).
  The leader's single-item endpoint returns only its own (always Green) status, so
  `sources get` / `destinations get` take `status` from the list endpoint instead.
- **Never write a one-off HTTP script against the Cribl API.** If no dedicated
  command exists, find the endpoint with `cribl api-spec search <words>` (add
  `--missing` for ones without a command) and call it with `cribl api`:
  `cribl api GET /lib/jobs -g default`, `-d @body.json` or `-d @-` for a JSON
  body, `--upload FILE` for a binary body (lookup CSVs, `.crbl` packs), `-o FILE`
  to save a binary response, `-q k=v` (repeatable) for query parameters, and the
  global `--dry-run` to preview a write. Paths are written as in the API
  reference, relative to the API root; `-g` puts them under `/m/<group>/`.
- `cribl_cli/data/api_paths.json` is the API reference in compact form (refresh
  with `scripts/update_api_paths.py` after a Cribl upgrade). `tests/unit/
  test_api_coverage.py` fails if a command calls a path that is not in it, so
  check new endpoints with `api-spec search` before adding them.
- Registry scopes: `group`, `global`, `search` (`/m/<g>/search/...`), `lake`, and
  `searchgroup` (alerting: in the search group but outside `/search/`). Set
  `transfer=False` on a group resource that is a catalog or runtime state so
  `groups export` skips it.
- When a number must match the UI, use the endpoint the UI calls (check its
  network requests). Known ones: `/m/{g}/system/inputs|outputs` for health,
  `/m/{g}/lib/jobs` for configured collectors (`/collectors` lists only the
  collector types), `/system/settings/auth|git-settings` for those settings.
- `health report` aggregates nodes, capacity alerts, versions, unhealthy IO, and
  error logs into a single command. Supports `--json`, `--skip-errors`, and `-g`
  group filter.
- `ingest dashboard` shows daily ingest totals (events/bytes in/out) by source (Stream, Edge, Search). Supports `--json`, `--table`, and `--hours`.
- `ingest query` runs a raw metric query — accepts a JSON payload as argument.
- `dashboards/` contains Cribl Search dashboard definitions for Daily Ingest (overview, by source, by route). Deploy with `cribl dashboards create "$(cat dashboards/<file>.json)"`.
- `groups export`/`groups import` move a whole group's config; the resource list
  is derived from `commands/registry.py` group-scoped entries plus the
  hand-written sources/destinations/pipelines/packs/routes, so it never drifts.
  Export drops Cribl-shipped built-ins (`lib == "cribl"` or `destroyable` false)
  and pack-owned items (`id` prefixed `pack:`) — they list but 4xx/5xx on import,
  so only user-authored config is kept; the count is reported in `_meta.skipped.builtin`.
- When running CLI commands to read data, use default JSON output (no `--table`).
  JSON is structured and easier to parse. Only use `--table` if the user
  explicitly asks for it.
