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

For edge deployments, inspect individual nodes:

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
