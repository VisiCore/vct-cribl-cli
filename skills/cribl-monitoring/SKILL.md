---
name: cribl-monitoring
description: "Health checks, metrics, and system monitoring for Cribl"
requires:
  skills: ["cribl-shared"]
---

# Cribl CLI — Monitoring & Health Checks

Monitor Cribl system health, worker status, metrics, and edge nodes.

## System Health

```bash
# Quick health check
cribl system health

# System information (version, build, etc.)
cribl system info

# System settings
cribl system settings

# Instance information
cribl system instance

# Worker health specifically
cribl system worker-health
```

## Worker Groups

```bash
# List all worker groups with status
cribl workers list --table

# Get details for a specific group
cribl workers get my_group
```

## Metrics

```bash
# Get all system metrics
cribl metrics get

# Filter metrics
cribl metrics get --filter "name=='total.in_events'"

# Get specific metric names
cribl metrics get --names total.in_events,total.out_events
```

## Edge Node Monitoring

### List all edge nodes

```bash
# List all edge nodes across all fleets
cribl edge nodes

# List nodes in a specific fleet
cribl edge nodes -f pi

# Table view
cribl edge nodes --table
```

### Node system info (CPU, memory, disk)

Use hostname or node ID — the CLI resolves hostnames automatically:

```bash
# Get formatted system summary for a node
cribl edge system-info pi5-cribl

# Get raw JSON (full detail including per-CPU times, network interfaces, etc.)
cribl edge system-info-raw pi5-cribl
```

Example output from `system-info`:
```json
{
  "hostname": "pi5-cribl",
  "os": "Linux arm64 6.12.47+rpt-rpi-2712",
  "uptime": "7h 24m",
  "cpu": { "cores": 4, "model": "Cortex-A76", "user_pct": "3.93%", "sys_pct": "0.43%", "idle_pct": "95.64%" },
  "load_avg": { "1min": 0.29, "5min": 0.31, "15min": 0.27 },
  "memory": { "total": "7.87 GB", "free": "6.41 GB", "used": "1.46 GB", "used_pct": "18.6%" },
  "disk": { "total": "116.63 GB", "used": "7.14 GB", "available": "104.68 GB", "used_pct": "6.1%" }
}
```

### Node inputs/outputs

```bash
# What sources are running on a node
cribl edge inputs pi5-cribl

# What destinations are configured
cribl edge outputs pi5-cribl
```

### Fleet-scoped edge commands

```bash
# List containers on edge nodes
cribl edge containers -f my_fleet

# List processes
cribl edge processes -f my_fleet

# Get logs
cribl edge logs -f my_fleet

# Get metadata
cribl edge metadata -f my_fleet
```

### Answering questions about edge nodes

When the user asks about CPU, memory, disk, or network for an edge node:

1. If the user mentions a hostname, use `cribl edge system-info <hostname>`
2. If unclear which node, run `cribl edge nodes` to list them
3. For raw data with per-CPU breakdowns and network interfaces, use `cribl edge system-info-raw <hostname>`
4. For inputs/outputs, use `cribl edge inputs/outputs <hostname>`

## Health Check Scripts

### Simple health check

```bash
#!/bin/bash
if cribl system health | jq -e '.status == "healthy"' > /dev/null 2>&1; then
  echo "OK: Cribl is healthy"
  exit 0
else
  echo "CRITICAL: Cribl health check failed"
  exit 2
fi
```

### Worker group monitoring

```bash
#!/bin/bash
cribl workers list | jq -r '.[] | "\(.id): \(.workerCount) workers"'
```

### Comprehensive status check

```bash
#!/bin/bash
echo "=== System Health ==="
cribl system health

echo "=== Worker Groups ==="
cribl workers list --table

echo "=== Deployment Status ==="
for group in $(cribl workers list | jq -r '.[].id'); do
  echo "--- $group ---"
  cribl version status -g "$group"
done
```

## Alerting Integration

### Check health in CI/CD

```bash
# Fail the pipeline if unhealthy
cribl system health | jq -e '.status == "healthy"' > /dev/null || exit 1
```

### Monitor via cron

```bash
# Add to crontab: */5 * * * * /path/to/check-cribl.sh
#!/bin/bash
if ! cribl system health | jq -e '.status == "healthy"' > /dev/null 2>&1; then
  echo "Cribl unhealthy at $(date)" | mail -s "Cribl Alert" ops@company.com
fi
```
