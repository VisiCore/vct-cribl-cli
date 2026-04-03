# Command Reference

All commands output JSON by default. Use `--table` where supported for tabular output.

## Table of Contents

- [config](#config) — Profile management
- [workers](#workers) — Worker groups and deployment
- [sources](#sources) — Source/input management
- [destinations](#destinations) — Destination/output management
- [pipelines](#pipelines) — Pipeline management
- [routes](#routes) — Route table management
- [search](#search) — Search jobs
- [notebooks](#notebooks) — Notebook management
- [edge](#edge) — Edge node and fleet operations
- [jobs](#jobs) — Job and collector management
- [version](#version) — Version control and deployment
- [system](#system) — System info and management
- [metrics](#metrics) — System metrics
- [kms](#kms) — Key Management Service
- [preview](#preview) — Pipeline preview
- [logger](#logger) — Logger configuration
- [profiler](#profiler) — Profiler management
- [health](#health) — Health checks, reports, and CPU monitoring
- [overview](#overview) — Environment summaries
- [ingest](#ingest) — Daily ingest dashboard and metrics
- [billing](#billing) — Billing, consumption, and invoices
- [finops](#finops) — FinOps consumption tracking
- [license-usage](#license-usage) — Daily license usage metrics
- [alerts](#alerts) — Scheduled saved search alerts
- [packs](#packs) — Pack management
- [Factory-generated commands](#factory-generated-commands) — CRUD for 52 resource types

---

## config

Manage CLI configuration profiles. Does not require authentication.

```bash
cribl config set -p <name> --base-url <url> [options]   # Save a profile
cribl config show [-p <name>]                            # Show profile (redacts secrets)
cribl config use <name>                                  # Switch active profile
```

| Subcommand | Options |
|---|---|
| `set` | `-p, --profile` (default: "default"), `--base-url` (required), `--auth-type` (cloud\|local), `--client-id`, `--client-secret`, `--username`, `--password` |
| `show` | `-p, --profile` |
| `use` | `PROFILE` (argument) |

---

## workers

Manage worker groups, deploy configs, and spin up Docker workers.

```bash
cribl workers list [--table]
cribl workers get <group_id> [--table]
cribl workers deploy <group>
cribl workers add <group> --token <token> [options]
cribl workers rm <container_name>
```

| Subcommand | Options |
|---|---|
| `list` | `--table` |
| `get` | `GROUP_ID`, `--table` |
| `deploy` | `GROUP` — deploys committed config to workers |
| `add` | `GROUP`, `--token` (required), `--version`, `--port` (default: 9000), `--name`, `--dry-run`, `--image` (default: "cribl/cribl") |
| `rm` | `CONTAINER_NAME` — stops and removes Docker container |

---

## sources

Manage sources (inputs) for a worker group.

```bash
cribl sources list -g <group> [--table]
cribl sources get <source_id> -g <group>
cribl sources create --type file --id my_src --path /var/log -g <group>
cribl sources update <source_id> '<json>' -g <group>
cribl sources delete <source_id> -g <group>
```

| Subcommand | Options |
|---|---|
| `list` | `-g, --group`, `--table` |
| `get` | `SOURCE_ID`, `-g, --group`, `--table` |
| `create` | `-t, --type`, `--id`, `--port`, `--path` (file sources), `--filenames` (comma-separated globs, default: "\*"), `--description`, `--send-to-routes/--no-send-to-routes`, `--json-config`, `-g, --group` |
| `update` | `SOURCE_ID`, `JSON_CONFIG` (merge patch), `-g, --group` |
| `delete` | `SOURCE_ID`, `-g, --group` |

For file sources, `--path` is required and `--filenames` defaults to `"*"`.

---

## destinations

Manage destinations (outputs) for a worker group.

```bash
cribl destinations list -g <group> [--table]
cribl destinations get <dest_id> -g <group>
cribl destinations create --type splunk --id my_dest -g <group>
cribl destinations update <dest_id> '<json>' -g <group>
cribl destinations delete <dest_id> -g <group>
```

| Subcommand | Options |
|---|---|
| `list` | `-g, --group`, `--table` |
| `get` | `DESTINATION_ID`, `-g, --group`, `--table` |
| `create` | `-t, --type`, `--id`, `--port`, `--json-config`, `-g, --group` |
| `update` | `DESTINATION_ID`, `JSON_CONFIG`, `-g, --group` |
| `delete` | `DESTINATION_ID`, `-g, --group` |

---

## pipelines

Manage pipelines for a worker group.

```bash
cribl pipelines list -g <group> [--table]
cribl pipelines get <pipeline_id> -g <group>
cribl pipelines create '<json>' -g <group>
cribl pipelines update <pipeline_id> '<json>' -g <group>
cribl pipelines delete <pipeline_id> -g <group>
cribl pipelines clone <pipeline_id> --source-group <src> --dest-group <dst>
```

| Subcommand | Options |
|---|---|
| `list` | `-g, --group`, `--table` |
| `get` | `PIPELINE_ID`, `-g, --group`, `--table` |
| `create` | `JSON_CONFIG`, `-g, --group` |
| `update` | `PIPELINE_ID`, `JSON_CONFIG`, `-g, --group` |
| `delete` | `PIPELINE_ID`, `-g, --group` |
| `clone` | `PIPELINE_ID`, `--source-group` (required), `--dest-group` (required) |

---

## routes

Manage the route table. Routes are inserted before the catch-all rule automatically.

```bash
cribl routes list -g <group> [--table]
cribl routes get <route_id> -g <group>
cribl routes create --id my_route --input my_source --pipeline my_pipe --output my_dest -g <group>
cribl routes update <route_id> '<json>' -g <group>
cribl routes delete <route_id> -g <group>
```

| Subcommand | Options |
|---|---|
| `list` | `-g, --group`, `--table` |
| `get` | `ROUTE_ID`, `-g, --group`, `--table` |
| `create` | `JSON_CONFIG` (optional), `--id`, `--input` (auto-builds `__inputId` filter), `--pipeline`, `--output`, `--filter` (overrides --input), `--description`, `-g, --group` |
| `update` | `ROUTE_ID`, `JSON_CONFIG`, `-g, --group` |
| `delete` | `ROUTE_ID`, `-g, --group` |

The `--input` flag automatically resolves the source type from the API and builds a `__inputId=='<type>:<id>'` filter expression.

---

## search

Submit and manage search jobs. All search commands default to the `default_search` group.

```bash
cribl search run -q "dataset=='default_catch_all'" --earliest "-1h" --latest "now" --poll
cribl search jobs [--table]
cribl search results <job_id> [--table]
cribl search saved [--table]
cribl search timeline <job_id>
cribl search field-summary <job_id>
cribl search job-logs <job_id>
cribl search job-metrics <job_id>
cribl search job-diag <job_id>
```

| Subcommand | Options |
|---|---|
| `run` | `-q, --query` (required), `--earliest`, `--latest`, `-g, --group`, `--poll` (wait for completion) |
| `jobs` | `-g, --group`, `--table` |
| `results` | `JOB_ID`, `-g, --group`, `--table` |
| `saved` | `-g, --group`, `--table` |
| `timeline` | `JOB_ID`, `-g, --group` |
| `field-summary` | `JOB_ID`, `-g, --group` |
| `job-logs` | `JOB_ID`, `-g, --group` |
| `job-metrics` | `JOB_ID`, `-g, --group` |
| `job-diag` | `JOB_ID`, `-g, --group` |

With `--poll`, the `run` command waits for the job to complete (polling every 2 seconds), then outputs results. The results endpoint returns NDJSON which is parsed into `{meta, items}`.

---

## notebooks

Manage Cribl Search notebooks. Defaults to `default_search` group.

```bash
cribl notebooks list [--table]
cribl notebooks get <notebook_id>
cribl notebooks create --name "My Notebook" --markdown "## Hello"
cribl notebooks add <notebook_id> '<query_json>'
cribl notebooks delete <notebook_id>
```

| Subcommand | Options |
|---|---|
| `list` | `-g, --group`, `--table` |
| `get` | `NOTEBOOK_ID`, `-g, --group`, `--table` |
| `create` | `--name` (required), `--description`, `--markdown` (initial content), `-g, --group` |
| `add` | `NOTEBOOK_ID`, `QUERY_JSON`, `-g, --group` |
| `delete` | `NOTEBOOK_ID`, `-g, --group` |

Notebooks are created with proper `info` blocks (timestamps, identity from JWT token) and `sections` with `type: "markdown.default"`.

---

## edge

Edge node and fleet operations — system info, file inspection, log scanning, metrics.

### Fleet-scoped commands

```bash
cribl edge nodes [-f <fleet>] [--table]
cribl edge containers -f <fleet> [--table]
cribl edge processes -f <fleet> [--table]
cribl edge logs -f <fleet>
cribl edge metadata -f <fleet> [--table]
cribl edge events -f <fleet> [--table]
cribl edge files <path> -f <fleet> [--table]
cribl edge kube-logs -f <fleet> [--table]
```

### Node-scoped commands

```bash
cribl edge system-info <node>
cribl edge system-info-raw <node>
cribl edge inputs <node> [--table]
cribl edge outputs <node> [--table]
cribl edge fileinspect <node> <path>
cribl edge node-ls <node> <path> [--stats] [--table]
cribl edge file-search <node> <path> -q <query> [-l <limit>]
cribl edge metrics <node> [-d <duration>] [--summary] [--table]
```

### Log scanning

```bash
cribl edge errors [-f <fleet>] [-l <limit>] [-q <query>]
cribl edge heartbeats [-f <fleet>] [--threshold <seconds>] [--table]
```

| Subcommand | Key options |
|---|---|
| `errors` | `-f, --fleet`, `-l, --limit` (default: 20), `-q, --query` (default: "error") — scans cribl.log across all nodes for errors |
| `heartbeats` | `-f, --fleet`, `--threshold` (default: 300s) — checks node health: heartbeat, disk, memory, CPU |
| `fileinspect` | `NODE`, `PATH` — stat, hashes (MD5/SHA256), head, hexdump. Edge nodes only. |
| `metrics` | `NODE`, `-d, --duration` (5m\|10m\|15m\|30m\|1h\|4h\|12h\|1d), `--summary` — CPU, memory, disk over time |
| `system-info` | `NODE` — formatted summary: CPU, memory, disk, network, OS |

---

## jobs

Manage jobs and collectors.

```bash
cribl jobs list -g <group> [--table]
cribl jobs get <job_id> -g <group>
cribl jobs run <collector_id> -g <group>
cribl jobs cancel <job_id> -g <group>
cribl jobs pause <job_id> -g <group>
cribl jobs resume <job_id> -g <group>
cribl jobs list-configs -g <group> [--table]
```

---

## version

Version control and deployment. The `deploy` subcommand pushes config to live workers.

```bash
cribl version info -g <group>
cribl version status -g <group>
cribl version diff -g <group>
cribl version commit -m "message" -g <group>
cribl version push -g <group>
cribl version sync -g <group>
cribl version branches -g <group> [--table]
cribl version current-branch -g <group>
cribl version deploy -g <group> -m "message" --yes
```

The `deploy` command requires `--yes` to confirm. It commits pending changes and deploys to live workers.

---

## system

System information and management.

```bash
cribl system info [--table]
cribl system settings [--table]
cribl system health [--table]
cribl system instance [--table]
cribl system worker-health -g <group> [--table]
cribl system logs [--limit <n>] [--table]
cribl system log <log_type> [--table]
cribl system diag
cribl system diag-send
cribl system restart
cribl system reload
cribl system upgrade
```

---

## metrics

```bash
cribl metrics get [--filter <expr>] [--table]
```

---

## kms

Key Management Service configuration.

```bash
cribl kms config -g <group> [--table]
cribl kms update '<json>' -g <group>
cribl kms health -g <group> [--table]
```

---

## preview

Pipeline preview — test a pipeline against sample data.

```bash
cribl preview run '<json_config>' -g <group>
```

---

## logger

Logger configuration for a worker group.

```bash
cribl logger get -g <group> [--table]
cribl logger set '<json>' -g <group>
```

---

## profiler

```bash
cribl profiler get -g <group> [--table]
cribl profiler start -g <group>
cribl profiler stop -g <group>
```

---

## health

Health checks, comprehensive reports, and CPU spike detection.

```bash
cribl health check -g <group> [--table] [--all]
cribl health report [-g <group>] [--json] [--skip-errors] [--error-limit <n>]
cribl health cpu [-g <group>] [--hours <n>] [--threshold <pct>] [--json] [--table]
```

| Subcommand | Options |
|---|---|
| `check` | `-g, --group`, `--table`, `--all` — show unhealthy (or all) sources and destinations |
| `report` | `-g, --group`, `--json`, `--skip-errors`, `--error-limit` (default: 10) — comprehensive report: nodes, capacity alerts, versions, unhealthy IO, config drift, errors |
| `cpu` | `-g, --group`, `--hours` (default: 24), `--threshold` (default: 80), `--json`, `--table` — per-node CPU spike detection |

---

## overview

High-level environment summaries.

```bash
cribl overview summary [--json]
cribl overview sources -g <group> [--table]
cribl overview destinations -g <group> [--table]
```

`overview summary` outputs a text summary of all groups, nodes, sources, and destinations. Use `--json` for machine-readable output.

---

## ingest

Daily ingest dashboard and raw metric queries.

```bash
cribl ingest dashboard [--hours <n>] [--json] [--table]
cribl ingest query '<json_body>' [--table]
```

| Subcommand | Options |
|---|---|
| `dashboard` | `--hours` (default: 24), `--json`, `--table` — daily ingest totals (events/bytes in/out) by source (Stream, Edge, Search) |
| `query` | `JSON_BODY`, `--table` — run a raw metric query against `/api/v1/system/metrics/query` |

---

## billing

Billing, consumption, and invoice management (cloud only). All consumption subcommands require `--start` and `--end` dates (ISO 8601).

```bash
cribl billing products-stats --start <date> --end <date> [--table]
cribl billing credits-summary --start <date> --end <date> [--table]
cribl billing cumulative --start <date> --end <date> [--table]
cribl billing products-breakdown --start <date> --end <date> [--table]
cribl billing product <slug> --start <date> --end <date> [--table]
cribl billing invoices [--table]
cribl billing invoice <invoice_id> [--table]
```

| Subcommand | Options |
|---|---|
| `products-stats` | `--start`, `--end`, `--window` (default: monthly), `--table` |
| `credits-summary` | `--start`, `--end`, `--window`, `--table` |
| `cumulative` | `--start`, `--end`, `--window`, `--table` |
| `products-breakdown` | `--start`, `--end`, `--window`, `--table` |
| `product` | `PRODUCT_SLUG` (stream\|search\|edge\|lakehouse\|lake\|infrastructure\|other), `--start`, `--end`, `--window`, `--table` |
| `invoices` | `--table` |
| `invoice` | `INVOICE_ID`, `--table` |

---

## finops

FinOps credit consumption tracking and license utilization.

```bash
cribl finops summary [--json] [--table]
```

| Subcommand | Options |
|---|---|
| `summary` | `--json`, `--table` — annual consumption summary with on-track/over/under status, monthly breakdown, estimated credits |

---

## license-usage

Daily license usage metrics (up to 90 days).

```bash
cribl license-usage get [--start <date>] [--end <date>] [--table]
```

| Subcommand | Options |
|---|---|
| `get` | `--start` (ISO 8601), `--end` (ISO 8601), `--table` |

---

## alerts

Alerts (scheduled saved searches). Hand-written command that filters notifications to show only scheduled alert items.

```bash
cribl alerts list [-g <group>] [--table]
```

---

## packs

Pack management — export, install, upgrade, delete.

```bash
cribl packs list -g <group> [--table]
cribl packs export <pack_id> -g <group> -o <output_path>
cribl packs install <source> -g <group>
cribl packs upgrade <pack_id> -g <group> [--source <url>]
cribl packs delete <pack_id> -g <group>
```

---

## Factory-generated commands

52 resource types with auto-generated CRUD subcommands. Each supports a subset of: `list`, `get`, `create`, `update`, `delete`.

### Group-scoped (use `-g, --group`)

| Command | Operations | API path |
|---|---|---|
| `parsers` | all | `system/parsers` |
| `schemas` | all | `schemas` |
| `regex` | all | `lib/regex` |
| `grok` | all | `lib/grok` |
| `event-breakers` | all | `lib/breakers` |
| `global-vars` | all | `lib/vars` |
| `db-connections` | all | `lib/db-connections` |
| `secrets` | all | `system/secrets` |
| `credentials` | all | `system/credentials` |
| `collectors` | all | `collectors` |
| `conditions` | all | `lib/conditions` |
| `parquet-schemas` | all | `lib/parquet-schemas` |
| `protobuf-libs` | all | `lib/protobuf-libs` |
| `sds-rules` | all | `lib/sds/rules` |
| `sds-rulesets` | all | `lib/sds/rulesets` |
| `appscope` | all | `lib/appscope` |
| `lookups` | all | `system/lookups` |
| `certificates` | list, get, create, delete | `system/certificates` |
| `samples` | list, get, create, delete | `system/samples` |
| `scripts` | list, get, create, delete | `system/scripts` |
| `executors` | list, get | `executors` |
| `hmac-functions` | list, get | `lib/hmac` |
| `functions` | list, get | `system/functions` |

### Global-scoped (no group needed)

| Command | Operations | API path |
|---|---|---|
| `users` | all | `system/users` |
| `roles` | all | `system/roles` |
| `teams` | all | `system/teams` |
| `policies` | all | `system/policies` |
| `banners` | all | `system/banners` |
| `encryption-keys` | all | `system/encryption-keys` |
| `notification-targets` | all | `system/notification-targets` |
| `workspaces` | all | `workspaces` |
| `messages` | list, get, create, delete | `system/messages` |
| `licenses` | list, get | `system/licenses` |
| `subscriptions` | list, get, create, update | `system/subscriptions` |
| `outposts` | list, get | `system/outposts` |
| `feature-flags` | list, get, update, delete | `system/feature-flags` |
| `ai-settings` | list, get, update, delete | `system/ai-settings` |
| `auth-settings` | get, update | `system/auth` (singleton) |
| `git-settings` | get, update | `system/git-settings` (singleton) |

### Search-scoped (default group: `default_search`)

| Command | Operations | API path |
|---|---|---|
| `macros` | all | `macros` |
| `dataset-providers` | all | `dataset-providers` |
| `dashboard-categories` | all | `dashboard-categories` |
| `trust-policies` | all | `trust-policies` |
| `datatypes` | all | `datatypes` |
| `datasets` | all | `datasets` |
| `dashboards` | list, get, create, delete | `dashboards` |
| `saved-searches` | all | `saved` |
| `notifications` | all | `notifications` |
| `alert-monitors` | all | `alert/monitors` |
| `usage-groups` | all | `usage-groups` |

### Lake-scoped (use `--lake`)

| Command | Operations | API path |
|---|---|---|
| `lake-datasets` | all | `datasets` |
| `storage-locations` | all | `storage-locations` |

### Factory command options

```bash
cribl <resource> list [-g <group>] [--table]
cribl <resource> get <id> [-g <group>] [--table]
cribl <resource> create '<json>' [-g <group>]
cribl <resource> update <id> '<json>' [-g <group>]
cribl <resource> delete <id> [-g <group>]
```

Update operations perform a merge patch: they fetch the existing resource, strip server-computed fields, merge your JSON, and submit the result.
