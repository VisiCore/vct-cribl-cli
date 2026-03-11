# cribl-cli

Command-line interface for the Cribl Cloud REST API. Manage worker groups, sources, destinations, pipelines, routes, search jobs, notebooks, edge nodes, and more from your terminal.

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
cribl config set cloud \
  --base-url https://your-org.cribl.cloud \
  --client-id your-client-id \
  --client-secret your-client-secret

# Set it as default
cribl config use cloud

# List profiles
cribl config list
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

### Hand-written commands (19)

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
| `profiler` | Profiler management |
| `health` | Health checks |
| `overview` | Environment summary |

### Factory-generated commands (~49)

Standard CRUD operations (list, get, create, update, delete) are auto-generated for resources like `parsers`, `schemas`, `lookups`, `users`, `roles`, `datasets`, `dashboards`, and many more. Run `cribl -h` for the full list.

### Common examples

```bash
# List all worker groups
cribl workers list

# Deploy config to a group
cribl workers deploy pi

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

# Dry-run mode (preview API calls without sending)
cribl --dry-run sources list -g default
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

```
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
- Run `pytest` before submitting — all 71 tests must pass
- Do not commit credentials, `.env` files, or `~/.criblrc` profiles

### Reporting issues

Open an issue at [github.com/VisiCore/vct-cribl-cli/issues](https://github.com/VisiCore/vct-cribl-cli/issues) with:
- What you expected vs what happened
- CLI command you ran
- Cribl version and deployment type (cloud/on-prem/hybrid)

## License

MIT
