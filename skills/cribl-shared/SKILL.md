---
name: cribl-shared
description: "Base skill for Cribl CLI: authentication, global flags, output handling, and group resolution"
---

# Cribl CLI — Shared Foundations

This skill covers authentication setup, global options, output handling, and group resolution that all other skills depend on.

## Authentication Setup

Before any command works, configure credentials:

```bash
# Cribl Cloud (OAuth2 — most common)
cribl config set \
  --base-url https://your-org.cribl.cloud \
  --client-id YOUR_CLIENT_ID \
  --client-secret YOUR_CLIENT_SECRET

# On-prem / local (username + password)
cribl config set \
  --base-url https://your-cribl:9000 \
  --username admin \
  --password YOUR_PASSWORD \
  --auth-type local
```

### Multiple Profiles

```bash
cribl config set -n prod --base-url https://prod.cribl.cloud --client-id ... --client-secret ...
cribl config set -n dev  --base-url https://dev.cribl.cloud  --client-id ... --client-secret ...
cribl config use prod
cribl config show          # verify active profile (secrets masked)
```

### Environment Variables (CI/CD)

```bash
export CRIBL_BASE_URL=https://your-org.cribl.cloud
export CRIBL_CLIENT_ID=your-client-id
export CRIBL_CLIENT_SECRET=your-client-secret
```

Priority: CLI flags > environment variables > `~/.criblrc` profile.

## Global Flags

| Flag | Description |
|------|-------------|
| `-p, --profile <name>` | Use a specific config profile |
| `--base-url <url>` | Override Cribl base URL |
| `--client-id <id>` | Override OAuth client ID |
| `--client-secret <secret>` | Override OAuth client secret |
| `--verbose` | Log HTTP requests/responses to stderr |
| `--table` | Format output as a table |

## Output Handling

- **JSON** (default): Structured JSON to stdout — pipe to `jq` for filtering
- **Table** (`--table`): Human-readable table format
- **Errors**: Written to stderr as JSON

```bash
# Parse JSON output
cribl workers list | jq '.[] | {id, workerCount}'

# Table for quick human inspection
cribl pipelines list -g default --table

# Capture errors separately
cribl sources list -g default 2>errors.json
```

## Group Resolution

Most commands accept `-g, --group <name>` for the worker group. If omitted, the CLI auto-resolves to the first available worker group.

```bash
# Explicit group
cribl pipelines list -g my_worker_group

# Auto-resolve (uses first group)
cribl pipelines list
```

To discover available groups:

```bash
cribl workers list
```

## Common Patterns

### Piping to jq

```bash
# List pipeline IDs
cribl pipelines list -g default | jq '.[].id'

# Find disabled sources
cribl sources list -g default | jq '.[] | select(.disabled == true)'

# Count items
cribl destinations list -g default | jq 'length'
```

### Verbose Debugging

```bash
# See HTTP traffic on stderr, results on stdout
cribl workers list --verbose 2>debug.log | jq .
```
