# Examples

Common workflows and usage patterns.

## Setup

```bash
# Configure a Cribl Cloud profile
cribl config set -p myorg \
  --base-url https://myorg.cribl.cloud \
  --client-id $CLIENT_ID \
  --client-secret $CLIENT_SECRET

cribl config use myorg

# Verify connectivity
cribl overview summary
```

## Worker group management

```bash
# List all worker groups
cribl workers list --table

# Deploy committed config to a group
cribl workers deploy pi

# Spin up a Docker worker
cribl workers add defaultHybrid --token $AUTH_TOKEN --port 9001

# Remove a Docker worker
cribl workers rm cribl-defaultHybrid-abcdef
```

## Source and destination management

```bash
# List sources for a group
cribl sources list -g pi --table

# Create a file monitoring source
cribl sources create --type file --id app_logs \
  --path /var/log/app \
  --filenames "*.log,*.json" \
  -g pi

# Create a TCP source
cribl sources create --type tcp --id syslog_input --port 514 -g pi

# View source details
cribl sources get app_logs -g pi

# Delete a source
cribl sources delete app_logs -g pi
```

## Pipeline and route workflow

```bash
# Create a pipeline
cribl pipelines create '{"id":"my_pipe","conf":{"functions":[]}}' -g pi

# Create a route with auto-resolved input filter
cribl routes create \
  --id my_route \
  --input app_logs \
  --pipeline my_pipe \
  --output splunk_out \
  -g pi

# List routes
cribl routes list -g pi --table

# Commit and deploy
cribl version commit -m "Add app_logs pipeline" -g pi
cribl version deploy -g pi -m "Deploy app_logs" --yes
```

## Search

```bash
# Run a search and wait for results
cribl search run \
  -q "dataset=='default_catch_all'" \
  --earliest "-24h" \
  --latest "now" \
  --poll

# Submit a search without waiting
cribl search run -q "dataset=='cribl_metrics'" --earliest "-1h"

# Check job status and fetch results separately
cribl search jobs --table
cribl search results <job_id> --table

# List saved searches
cribl search saved --table
```

## Notebooks

```bash
# Create a notebook with markdown
cribl notebooks create \
  --name "Investigation Notes" \
  --description "Security investigation 2026-03-11" \
  --markdown "## Findings\n\nNo issues found."

# List notebooks
cribl notebooks list --table

# Delete a notebook
cribl notebooks delete <notebook_id>
```

## Edge node operations

```bash
# List all edge nodes across fleets
cribl edge nodes --table

# Filter by fleet
cribl edge nodes -f pi --table

# Check node health (heartbeats, disk, memory, CPU)
cribl edge heartbeats -f pi --table

# Get system info for a specific node
cribl edge system-info pi5-cribl

# Inspect a file on an edge node (stat, hashes, head, hexdump)
cribl edge fileinspect pi5-cribl /var/log/syslog

# Browse files on a node
cribl edge node-ls pi5-cribl /opt/cribl/log --stats --table

# Search log files on a node
cribl edge file-search pi5-cribl /opt/cribl/log/cribl.log -q "error" -l 20

# Scan all nodes for errors
cribl edge errors -f pi -l 50

# View node metrics over time
cribl edge metrics pi5-cribl -d 4h --summary --table
```

## Environment overview

```bash
# Full environment summary (text)
cribl overview summary

# JSON output for scripting
cribl overview summary --json

# Source breakdown by type
cribl overview sources -g defaultHybrid --table

# Destination breakdown by type
cribl overview destinations -g pi --table
```

## Health checks

```bash
# Comprehensive health report (nodes, alerts, versions, errors)
cribl health report

# JSON output for scripting
cribl health report --json

# Scope to one group, skip error scanning for speed
cribl health report -g default --skip-errors

# Show unhealthy sources and destinations
cribl health check -g pi --table

# Show all items (including healthy)
cribl health check -g pi --table --all
```

## Version control

```bash
# Check for uncommitted changes
cribl version status -g pi

# View diff
cribl version diff -g pi

# Commit changes
cribl version commit -m "Updated routes" -g pi

# Deploy to workers (requires --yes)
cribl version deploy -g pi -m "Deploy route changes" --yes
```

## Dry-run mode

Preview any command without making changes:

```bash
# See what API call would be made
cribl --dry-run sources create --type file --id test_src --path /tmp -g pi

# Output (stderr):
# {"dry_run": true, "method": "POST", "url": "https://...", ...}
```

## Discovery — "Know your environment"

Common questions a Cribl admin asks when getting oriented or auditing an environment.

### Infrastructure & Topology

```bash
# What worker groups and fleets do I have?
cribl workers list --table

# What nodes are online and what are they running?
cribl edge nodes --table

# What version is each node on? Are any out of date?
cribl edge nodes | jq -r '.[] | [.hostname, .fleet, .version, .status] | @tsv'

# Are any nodes missing heartbeats or unhealthy?
cribl edge heartbeats -f Linux_Fleet --table

# What's the CPU/memory/disk usage on my edge nodes?
cribl edge system-info <node_id>
cribl edge metrics <node_id> -d 24h --summary --table
```

### Data Flow

```bash
# What sources exist in a worker group?
cribl sources list -g default --table

# What destinations are configured?
cribl destinations list -g default --table

# What routes are in place and where is data going?
cribl routes list -g default --table

# What pipelines are defined?
cribl pipelines list -g default | jq -r '.items[].id'

# What packs are installed?
cribl packs list -g default --table
```

### Health & Troubleshooting

```bash
# What sources or destinations are unhealthy?
cribl health check -g default --table

# Show everything (healthy + unhealthy)
cribl health check -g default --table --all

# Which sources are disabled?
cribl sources list -g default | jq '[.items[] | select(.disabled == true) | .id]'

# Which destinations are in Red health?
cribl destinations list -g default | jq '[.items[] | select(.status.health == "Red") | {id, type}]'

# Scan edge nodes for errors
cribl edge errors -f pi -l 50
```

### Security & Configuration

```bash
# Who are the users in my org?
cribl users list --table

# What roles exist?
cribl roles list --table

# What credentials are configured?
cribl credentials list -g default --table

# Are there uncommitted changes?
cribl version status -g default

# What git settings are in place?
cribl git-settings list -g default
```

### Capacity & Licensing

```bash
# What are my license details?
cribl licenses list

# Check system metrics (throughput, events/sec)
cribl metrics query -g default -m total

# What jobs are currently running?
cribl jobs list --table

# Environment summary (one-shot overview)
cribl overview summary
```

## Scripting with jq

```bash
# Get all source IDs for a group
cribl sources list -g pi | jq -r '.items[].id'

# Count events by dataset
cribl search run -q "dataset=='default_catch_all' | summarize count() by dataset" \
  --earliest "-1h" --poll | jq '.items'

# Get unhealthy node hostnames
cribl edge heartbeats -f pi | jq -r '.[] | select(.status != "healthy") | .hostname'
```
