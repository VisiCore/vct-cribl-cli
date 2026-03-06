# Cribl CLI — Developer Guide

TypeScript/Node.js CLI for the Cribl Cloud REST API. Uses ESM modules (`"type": "module"`), Commander.js v12 for CLI framework, axios for HTTP, vitest + nock for testing.

## Quick Commands

```bash
npm run build        # tsc — compile TypeScript
npm run dev -- <cmd> # tsx — run without building (e.g. npm run dev -- workers list)
npm test             # vitest run — unit tests
npm run test:watch   # vitest — watch mode
npm run lint         # tsc --noEmit — type check only
```

## Architecture

```
bin/cribl.ts                  → Entry point (#!/usr/bin/env node)
src/cli.ts                    → Commander program setup, registers all 68 command groups
src/config/                   → Config loading (CLI flags > env vars > ~/.criblrc profiles)
src/auth/oauth.ts             → OAuth2 cloud + local auth with token caching
src/api/client.ts             → Axios client with auth interceptor (getClient singleton)
src/api/types.ts              → Shared API response types (ListResponse, etc.)
src/api/endpoints/            → One file per API resource (CRUD functions)
src/commands/                 → One file per command group (Commander registration)
src/output/formatter.ts       → JSON (default) + --table mode (cli-table3)
src/utils/errors.ts           → handleError() — formats errors to stderr as JSON
src/utils/pagination.ts       → Pagination helpers
src/utils/group-resolver.ts   → resolveGroup() — defaults to first worker group if -g omitted
```

## How to Add a New Command Group

1. **Types** — Add any new types to `src/api/types.ts` if needed
2. **Endpoint file** — Create `src/api/endpoints/<resource>.ts` with CRUD functions:
   - `list<Resource>(client, group)` → `GET /api/v1/m/{group}/<resource>`
   - `get<Resource>(client, group, id)` → `GET /api/v1/m/{group}/<resource>/{id}`
   - `create<Resource>(client, group, data)` → `POST /api/v1/m/{group}/<resource>`
   - `update<Resource>(client, group, id, data)` → `PATCH /api/v1/m/{group}/<resource>/{id}`
   - `delete<Resource>(client, group, id)` → `DELETE /api/v1/m/{group}/<resource>/{id}`
3. **Command file** — Create `src/commands/<resource>.ts` with `registerXCommand(program)`:
   - Each subcommand: `list`, `get`, `create`, `update`, `delete`
   - Use `resolveGroup()` for group-scoped resources
   - Use `formatOutput()` for JSON/table output
   - Wrap actions in try/catch with `handleError()`
4. **Register** — Add import + `registerXCommand(program)` call in `src/cli.ts`
5. **Tests** — Add nock-based tests in `test/unit/`

## API Endpoint Patterns

| Scope | URL Pattern | Examples |
|-------|-------------|----------|
| **Global** (no group) | `/api/v1/<resource>` | users, roles, system, licenses, teams, policies |
| **Group-scoped** | `/api/v1/m/{group}/<resource>` | pipelines, routes, sources, destinations, packs, lookups, secrets, version, credentials |
| **Search-scoped** | `/api/v1/m/{search_group}/search/<resource>` | datasets, dashboards, notebooks, saved searches, search jobs |

## Key Gotchas

- **Cloud OAuth audience** must be `https://api.cribl.cloud` (not the org-specific URL)
- Root command uses `enablePositionalOptions()` — required for `-g` option on subcommands
- Config command uses `passThroughOptions()` to avoid option name conflicts with root
- Config set/show uses `-n, --name` (not `--profile`) to avoid conflict with root `-p, --profile`
- `preAction` hook walks the parent chain to skip auth init for `config` subcommands
- `getClient()` is a singleton — the `preAction` hook initializes it before command execution
- Source/destination `create` commands accept `--type`/`--id` flags OR `--json-config` for full JSON

## Test Patterns

- **Unit tests**: vitest + nock for HTTP mocking
- Config tests mock `node:fs` to isolate from real `~/.criblrc`
- Integration tests gated behind `CRIBL_INTEGRATION_TEST=true` env var
- Test fixtures in `test/fixtures/`
- Nock interceptors match against `https://test.cribl.cloud` base URL

## Answering Questions About Nodes

When the user asks about CPU, memory, disk, load, or network for a Cribl node (Edge or hybrid worker), use the CLI to fetch live data. These commands work for **any managed node** — Edge nodes, hybrid workers, etc.

```bash
# List all managed nodes (Edge + hybrid workers)
npx tsx bin/cribl.ts edge nodes

# Filter to a specific fleet
npx tsx bin/cribl.ts edge nodes -f pi

# Get system summary (CPU%, memory, disk, load avg, uptime) by hostname
npx tsx bin/cribl.ts edge system-info <hostname>

# Get full raw JSON (per-CPU times, network interfaces, all details)
npx tsx bin/cribl.ts edge system-info-raw <hostname>

# Get sources/inputs running on a node
npx tsx bin/cribl.ts edge inputs <hostname>

# Get destinations/outputs on a node
npx tsx bin/cribl.ts edge outputs <hostname>

# Historical metrics (CPU, memory, disk, load) — time series
npx tsx bin/cribl.ts edge metrics <hostname> -d 1h        # last hour (default)
npx tsx bin/cribl.ts edge metrics <hostname> -d 15m       # last 15 min
npx tsx bin/cribl.ts edge metrics <hostname> -d 4h        # last 4 hours
# Durations: 5m, 10m, 15m, 30m, 1h, 4h, 12h, 1d

# Summary (min/max/avg) instead of full time series
npx tsx bin/cribl.ts edge metrics <hostname> -d 1h --summary
```

**How to answer node questions:**

1. If the user names a host, run `edge system-info <hostname>` for a current snapshot
2. If unclear which node, run `edge nodes` to list them and ask or infer
3. For trend/spike questions ("any CPU spikes?", "memory usage over time"), use `edge metrics <hostname> -d <duration> --summary` to get min/max/avg, or without `--summary` for the full minute-by-minute time series
4. The `--summary` output shows min/max/avg for CPU%, memory%, disk%, and load avg — a max CPU much higher than avg indicates spikes
5. For deeper analysis (per-core breakdown, network interface details), use `system-info-raw`
6. Hostnames are case-insensitive — `pi5-cribl` and `Pi5-Cribl` both work
7. Data resolution is 1 minute. Available history depends on node uptime and metrics retention

## Workflow Skills

Agent workflow guides are in `skills/` — each `SKILL.md` teaches how to compose commands for common tasks. See `skills/cribl-shared/SKILL.md` for the base skill (auth, flags, output).
