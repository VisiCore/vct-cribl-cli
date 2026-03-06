# cribl-cli

A command-line interface for the Cribl Cloud REST API. Manage worker groups, pipelines, routes, search, and more directly from your terminal.

## Why a CLI Instead of MCP?

Cribl publishes an [MCP server](https://docs.cribl.io/copilot/cribl-mcp-server/) you can set up for AI assistants. MCP is great for discovery — an agent can browse available tools and figure out what to call. But once you know *what* you need, a CLI is simpler, faster, and more useful.

**A CLI is just a shell command.** Any AI agent with terminal access (Claude Code, Cursor, Windsurf, etc.) can call it directly — no protocol layer, no JSON-RPC, no server to run. The agent runs `cribl sources list -g prod`, gets JSON back, and moves on. That's it. No handshake, no tool registration, no schema negotiation.

**CLIs work for humans too.** MCP only works inside an AI host. A CLI works everywhere — shell scripts, cron jobs, CI/CD pipelines, `jq` pipelines, and your terminal. One tool, every context.

**Debugging is trivial.** When something breaks, you re-run the command and see exactly what happened. With MCP, you're digging through protocol logs to figure out what the agent sent and what the server returned.

For a deeper take on this, see [Why CLIs Beat MCP for AI Agents](https://medium.com/@rentierdigital/why-clis-beat-mcp-for-ai-agents-and-how-to-build-your-own-cli-army-6c27b0aec969).

```bash
# AI agent or human — same command, same output
cribl sources list -g prod | jq '.[].id'

# Automate in CI/CD
cribl version deploy -g prod "Deploy from GitHub Actions"

# Monitor in cron
cribl system health | jq -e '.status == "healthy"' || alert "Cribl down"
```

## Quick Start

```bash
npm install
npm run build

# Configure credentials (Cribl Cloud)
node dist/bin/cribl.js config set \
  --base-url https://your-org.cribl.cloud \
  --client-id YOUR_CLIENT_ID \
  --client-secret YOUR_CLIENT_SECRET

# List worker groups
node dist/bin/cribl.js workers list

# Formatted table output
node dist/bin/cribl.js workers list --table

# Pipe JSON to jq
node dist/bin/cribl.js pipelines list -g default | jq '.[].id'
```

## Authentication

### Cribl Cloud (OAuth2)

```bash
cribl config set \
  --base-url https://your-org.cribl.cloud \
  --client-id YOUR_CLIENT_ID \
  --client-secret YOUR_CLIENT_SECRET
```

Or via environment variables:

```bash
export CRIBL_BASE_URL=https://your-org.cribl.cloud
export CRIBL_CLIENT_ID=your-client-id
export CRIBL_CLIENT_SECRET=your-client-secret
```

### On-Prem / Local

```bash
cribl config set \
  --base-url https://your-cribl:9000 \
  --username admin \
  --password YOUR_PASSWORD \
  --auth-type local
```

### Profiles

Credentials are stored in `~/.criblrc`. You can manage multiple environments:

```bash
cribl config set -n prod --base-url https://prod.cribl.cloud --client-id ... --client-secret ...
cribl config set -n dev --base-url https://dev.cribl.cloud --client-id ... --client-secret ...
cribl config use prod
cribl config show
```

Config priority: CLI flags > environment variables > `~/.criblrc` profile.

## Commands

The CLI covers the full Cribl API across 30+ command groups. Here's a summary — see [docs/commands.md](docs/commands.md) for the complete reference.

| Group | What it does |
|---|---|
| `config` | Manage CLI profiles and credentials |
| `workers` | List/deploy worker groups |
| `sources` | CRUD source configurations |
| `destinations` | CRUD destination configurations |
| `pipelines` | CRUD pipelines, clone between groups |
| `routes` | CRUD routes (auto-inserts before catch-all) |
| `packs` | Manage and export packs |
| `lookups` | Manage lookup tables |
| `search` | Run queries, manage jobs, get results |
| `datasets` | List search datasets |
| `notebooks` | Manage search notebooks |
| `dashboards` | CRUD dashboards |
| `alerts` | List alert notifications |
| `jobs` | Run, cancel, pause, resume jobs |
| `users` / `roles` | Manage users and RBAC roles |
| `secrets` | Manage secrets |
| `version` | Commit, push, deploy, branch management |
| `system` | Health, info, settings, instance details |
| `metrics` | Query system metrics |
| `edge` | Edge node management — [see guide](docs/edge.md) |
| `event-breakers` | List/get event breaker rulesets |
| `parsers` | List/get parsers |
| `global-vars` | CRUD global variables |
| `schemas` | List/get schemas |
| `regex` | List/get regex patterns |
| `grok` | List/get grok patterns |
| `db-connections` | CRUD database connections |
| `functions` | List/get pipeline functions |
| `certificates` | Manage certificates |
| `credentials` | CRUD credentials |
| `samples` | List/get sample data |
| `scripts` | Manage scripts |
| `licenses` | List/get licenses |
| `teams` | CRUD teams |
| `policies` | CRUD RBAC policies |
| `notification-targets` | CRUD notification targets |

## Global Options

| Flag | Description |
|---|---|
| `-p, --profile <name>` | Use a specific config profile |
| `--base-url <url>` | Override Cribl base URL |
| `--client-id <id>` | Override OAuth client ID |
| `--client-secret <secret>` | Override OAuth client secret |
| `--verbose` | Log HTTP requests/responses to stderr |
| `--table` | Format output as a table (available on most commands) |

## Output

- **JSON** (default): Structured JSON to stdout, suitable for piping to `jq`
- **Table** (`--table`): Human-readable table format
- **Errors**: Written to stderr as JSON

```bash
# JSON output piped to jq
cribl workers list | jq '.[] | {id, type, workerCount}'

# Table output
cribl pipelines list -g default --table

# Verbose mode shows HTTP traffic on stderr
cribl workers list --verbose 2>debug.log
```

## Development

```bash
npm install
npm run build        # Compile TypeScript
npm run dev -- workers list   # Run via tsx (no build needed)
npm test             # Run unit tests
npm run test:watch   # Watch mode
npm run lint         # Type check
```

## Project Structure

```
bin/cribl.ts                  # Entry point
src/
  cli.ts                      # Commander program setup
  config/                     # Config loading + types
  auth/oauth.ts               # OAuth2 + token caching
  api/
    client.ts                 # Axios client with auth interceptor
    types.ts                  # API response types
    endpoints/                # One file per API resource
  commands/                   # One file per command group
  output/formatter.ts         # JSON + table formatting
  utils/                      # Errors, pagination, group resolver
test/
  unit/                       # Unit tests (vitest + nock)
  integration/                # Live API tests (CRIBL_INTEGRATION_TEST=true)
  fixtures/                   # Mock API responses
```

## License

MIT
