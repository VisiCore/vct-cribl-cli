# CLAUDE.md

## Quick Reference

- **Install:** `pip install -e ".[dev]"` (editable with dev deps)
- **Run:** `bin/cribl <command>` or `python -m cribl_cli <command>`
- **Test:** `pytest` (unit only) or `pytest -m integration` (needs `CRIBL_INTEGRATION_TEST=true` + live credentials)
- **Python:** 3.10+
- **Deps:** click, httpx, tabulate | Dev: pytest, responses, pytest-mock

## Architecture

Python CLI built with Click. Two kinds of commands:

1. **Hand-written (19):** `cribl_cli/commands/*.py` — complex operations (workers, routes, search, edge, etc.)
2. **Factory-generated (~49):** Declared in `commands/registry.py`, built by `commands/command_factory.py` — standard CRUD

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

## Safety Rules

- **Never replace the route table wholesale.** `routes create` fetches existing routes, inserts before the catch-all, then updates.
- **Always confirm before deploying.** `version deploy` pushes config to live workers.
- Cloud OAuth audience is always `https://api.cribl.cloud`, not the org-specific URL.

## Conventions

- New CRUD resources go in `commands/registry.py` — only write a hand-written command file if the resource needs custom logic.
- Merge-on-update pattern: fetch existing object, strip server-only fields (`status`, `notifications`), merge user updates.
- `--dry-run` logs request details to stderr and raises `DryRunAbort` (caught by error handler, exits 0).
- Config tests mock the filesystem to avoid touching real `~/.criblrc`.
