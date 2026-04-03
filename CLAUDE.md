# CLAUDE.md

## Quick Reference

- **Install:** `pip install -e ".[dev]"` (editable with dev deps)
- **Run:** `bin/cribl <command>` or `python -m cribl_cli <command>`
- **Test:** `pytest` (unit only) or `pytest -m integration` (needs `CRIBL_INTEGRATION_TEST=true` + live credentials)
- **Python:** 3.10+
- **Deps:** click, httpx, tabulate | Dev: pytest, responses, pytest-mock

## Architecture

Python CLI built with Click. Two kinds of commands:

1. **Hand-written (25):** `cribl_cli/commands/*.py` — complex operations (workers, routes, search, edge, health report, ingest dashboard, billing, finops, etc.)
2. **Factory-generated (52):** Declared in `commands/registry.py`, built by `commands/command_factory.py` — standard CRUD

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

Worker groups are managed via `workers`, not `groups`.

**Hand-written commands:** alerts, billing, config, destinations, edge, finops, health (check, report, cpu), ingest (dashboard, query), jobs, kms, license-usage, logger, metrics, notebooks, overview, packs, pipelines, preview, profiler, routes, search, sources, system, version, workers

**Factory-generated commands (standard CRUD):** ai-settings, alert-monitors, appscope, auth-settings, banners, certificates, collectors, conditions, credentials, dashboard-categories, dashboards, dataset-providers, datasets, datatypes, db-connections, encryption-keys, event-breakers, executors, feature-flags, functions, git-settings, global-vars, grok, hmac-functions, lake-datasets, licenses, lookups, macros, messages, notification-targets, notifications, outposts, parquet-schemas, parsers, policies, protobuf-libs, regex, roles, samples, saved-searches, schemas, scripts, sds-rules, sds-rulesets, secrets, storage-locations, subscriptions, teams, trust-policies, usage-groups, users, workspaces

## Safety Rules

- **Never replace the route table wholesale.** `routes create` fetches existing routes, inserts before the catch-all, then updates.
- **Always confirm before deploying.** `version deploy` pushes config to live workers.
- Cloud OAuth audience is always `https://api.cribl.cloud`, not the org-specific URL.

## Conventions

- New CRUD resources go in `commands/registry.py` — only write a hand-written command file if the resource needs custom logic.
- Merge-on-update pattern: fetch existing object, strip server-only fields (`status`, `notifications`), deep-merge user updates (nested dicts are merged recursively, not replaced).
- `--dry-run` logs request details to stderr and raises `DryRunAbort` (caught by error handler, exits 0).
- Config tests mock the filesystem to avoid touching real `~/.criblrc`.
- `health report` aggregates nodes, capacity alerts, versions, unhealthy IO, and error logs into a single command. Supports `--json`, `--skip-errors`, and `-g` group filter.
- `ingest dashboard` shows daily ingest totals (events/bytes in/out) by source (Stream, Edge, Search). Supports `--json`, `--table`, and `--hours`.
- `ingest query` runs a raw metric query — accepts a JSON payload as argument.
- `dashboards/` contains Cribl Search dashboard definitions for Daily Ingest (overview, by source, by route). Deploy with `cribl dashboards create "$(cat dashboards/<file>.json)"`.
- When running CLI commands to read data, use default JSON output (no `--table`). JSON is structured and easier to parse. Only use `--table` if the user explicitly asks for it.
