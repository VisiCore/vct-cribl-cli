# cribl-cli

![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)
![License: MIT](https://img.shields.io/badge/license-MIT-green)
![Tests: 162 passing](https://img.shields.io/badge/tests-162%20passing-brightgreen)

Command-line interface for the Cribl Cloud REST API. Manage pipelines, routes,
sources, destinations, Edge fleets, search, health monitoring, FinOps billing,
and 70+ resources from your terminal.

## Requirements

- Python 3.10+

## Installation

```bash
# Clone and install in a virtual environment
git clone https://github.com/VisiCore/vct-cribl-cli.git
cd vct-cribl-cli
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Configuration

Configure authentication via `~/.criblrc` profiles, environment variables, or CLI flags.

### Using profiles (recommended)

```bash
# Create a profile for Cribl Cloud
cribl config set -p cloud \
  --base-url https://your-org.cribl.cloud \
  --client-id your-client-id \
  --client-secret your-client-secret

# Set it as default
cribl config use cloud

# Show the active profile
cribl config show
```

### Using environment variables

```bash
export CRIBL_BASE_URL=https://your-org.cribl.cloud
export CRIBL_CLIENT_ID=your-client-id
export CRIBL_CLIENT_SECRET=your-client-secret
```

See `.env.example` for all supported variables.

### CLI flag overrides

```bash
cribl --base-url https://your-org.cribl.cloud --client-id ... --client-secret ... workers list
```

## Usage

```bash
cribl <command> <subcommand> [options]
```

### Hand-written commands (29)

| Command | Description |
|---|---|
| `config` | Manage CLI configuration profiles |
| `workers` | Worker group management and deployment |
| `sources` | Source/input management |
| `destinations` | Destination/output management |
| `pipelines` | Pipeline management |
| `routes` | Route table management (insert-before-catch-all) |
| `search` | Search job submission, polling, and results |
| `notebooks` | Notebook management |
| `edge` | Edge node operations (system info, file inspect, errors, metrics) |
| `jobs` | Job management |
| `version` | Version and deployment management |
| `system` | System settings |
| `metrics` | Metrics queries |
| `kms` | KMS key management |
| `preview` | Pipeline preview |
| `logger` | Logger configuration |
| `profiler` | Profiler status (captures: `profiler-captures`) |
| `health` | Health checks, reports, and CPU spike detection |
| `overview` | Environment summary |
| `alerts` | Alerts (scheduled saved searches) |
| `packs` | Pack export, install, upgrade, delete |
| `apps` | App Platform: list, check, install, upgrade, uninstall, backend status, invoke endpoints |
| `ingest` | Ingest dashboards and metric queries |
| `billing` | Billing usage and cost tracking |
| `finops` | FinOps consumption tracking and dashboards |
| `license-usage` | Daily license throughput metrics |
| `groups` | Export and import a whole worker group's or fleet's config |
| `api` | Call any API endpoint with the CLI's auth (JSON or file body, upload, save to file) |
| `api-spec` | Search the bundled API reference and see which endpoints have a command |

<details>
<summary><strong>Factory-generated commands (76)</strong> — standard CRUD (list, get, create, update, delete)</summary>

`ai-settings`, `alert-history`, `alert-monitors`, `alert-silences`, `appscope`, `auth-settings`, `banners`,
`certificates`, `collector-types`, `collectors`, `conditions`, `credentials`, `dashboard-categories`,
`dashboards`, `dataset-provider-types`, `dataset-providers`, `dataset-rulesets`, `datasets`, `datatype-
rulesets`, `datatypes`, `db-connections`, `dsd-connections`, `encryption-keys`, `event-breakers`, `executors`,
`feature-flags`, `federated-search-engines`, `functions`, `git-settings`, `global-vars`, `grok`, `hmac-
functions`, `iometrics`, `lake-datasets`, `lakehouse-config-profiles`, `lakehouse-dataset-access`, `lakehouse-
monitors`, `lakehouse-shared-configs`, `licenses`, `local-search-engines`, `local-search-sources`, `lookups`,
`macros`, `mcp-servers`, `mdt-devices`, `messages`, `notebook-templates`, `notification-targets`,
`notifications`, `outposts`, `parquet-schemas`, `parsers`, `policies`, `private-keys`, `processes`, `profiler-
captures`, `projects`, `protobuf-libs`, `provisioning-tokens`, `regex`, `roles`, `samples`, `saved-searches`,
`schemas`, `scripts`, `sds-rules`, `sds-rulesets`, `secret-folders`, `secret-stores`, `secrets`, `storage-
locations`, `subscriptions`, `teams`, `trust-policies`, `usage-groups`, `users`

</details>

### Common examples

```bash
# List all worker groups
cribl workers list

# Deploy config to a group (--yes is required)
cribl workers deploy pi --yes

# List sources for a group
cribl sources list -g defaultHybrid --table

# Create a file source
cribl sources create --type file --id my_source --path /var/log --filenames "*.log" -g pi

# Run a search and wait for results
cribl search run -q "dataset=='default_catch_all'" --earliest "-1h" --latest "now" --poll

# List edge nodes in a fleet
cribl edge nodes -f pi

# Inspect a file on an edge node
cribl edge fileinspect pi5-cribl /var/log/syslog -f pi

# Scan edge nodes for errors
cribl edge errors -f pi

# Environment overview
cribl overview summary

# Health report across all groups
cribl health report

# CPU spike detection for a group
cribl health cpu -g defaultHybrid

# Daily ingest dashboard
cribl ingest dashboard

# FinOps consumption tracking
cribl finops consumption

# Dry-run mode (reads run; the first write is printed and aborted)
cribl --dry-run sources update my_src '{"description":"x"}' -g default
```

### Output formats

All commands default to JSON output. Use `--table` for tabular output where supported.

```bash
cribl workers list --table
cribl search results <job_id> --table
```

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run a specific test
pytest tests/unit/test_routes.py

# Skip integration tests (default)
pytest -m "not integration"

# Run integration tests (requires live Cribl instance)
CRIBL_INTEGRATION_TEST=true pytest -m integration
```

## Project structure

```text
cribl_cli/
  api/
    endpoints/     # Hand-written API endpoint modules
    client.py      # httpx client with auth interceptor
    endpoint_factory.py  # Generic CRUD endpoint factory
  auth/            # OAuth2 token management
  commands/        # CLI command implementations
    command_factory.py   # Auto-generates CRUD subcommands
    registry.py          # Declarative list of factory commands
  config/          # Profile and config loading
  output/          # JSON and table formatters
  utils/           # Error handling, pagination, group resolution
tests/
  unit/            # Unit tests (pytest + responses)
  integration/     # Integration tests (gated)
```

## Documentation

| Doc | Description |
|---|---|
| [Configuration](docs/configuration.md) | Profiles, environment variables, authentication, global flags |
| [Command Reference](docs/commands.md) | Every command, subcommand, option, and argument |
| [Architecture](docs/architecture.md) | Codebase structure, design patterns, developer guide |
| [Examples](docs/examples.md) | Common workflows and scripting patterns |

## Contributing

Contributions are welcome! Here's how to get started:

1. **Fork** the repo and clone your fork
2. Create a feature branch: `git checkout -b my-feature`
3. Install dev dependencies: `pip install -e ".[dev]"`
4. Make your changes
5. Run the tests: `pytest`
6. Commit and push to your fork
7. Open a **pull request** against `main`

### Guidelines

- All new commands should have corresponding unit tests
- Follow existing code patterns — use the command factory for standard CRUD, hand-written commands for anything with special logic
- Keep `--table` output support for any command that returns lists
- Run `pytest` before submitting — all 138 tests must pass
- Do not commit credentials, `.env` files, or `~/.criblrc` profiles

### Reporting issues

Open an issue at [github.com/VisiCore/vct-cribl-cli/issues](https://github.com/VisiCore/vct-cribl-cli/issues) with:

- What you expected vs what happened
- CLI command you ran
- Cribl version and deployment type (cloud/on-prem/hybrid)

## License

MIT
