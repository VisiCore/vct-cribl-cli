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

## Workflow Skills

Agent workflow guides are in `skills/` — each `SKILL.md` teaches how to compose commands for common tasks. See `skills/cribl-shared/SKILL.md` for the base skill (auth, flags, output).
